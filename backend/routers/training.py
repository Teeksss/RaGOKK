# Last reviewed: 2025-04-29 08:20:31 UTC (User: Teekssstüm)
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status, BackgroundTasks
from typing import List, Dict, Optional, Any
import os
import uuid
import json
import time
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.async_database import get_db
from ..auth import get_current_active_user, require_admin
from ..models.evaluation_models import (
    EvaluationRequest, EvaluationResult, 
    FineTuningRequest, ModelInfo
)
from ..training.fine_tuning import fine_tuning_manager, TrainingExample
from ..evaluation.ragas_evaluator import RAGEvaluator
from ..utils.llm_manager import llm_manager
from ..utils.logger import get_logger
from ..utils.retrieval_system import retrieval_system
from ..websockets.background_tasks import manager as task_manager

router = APIRouter()
logger = get_logger(__name__)

# RAGAS evaluator singleton
evaluator = RAGEvaluator()

@router.post("/evaluate", response_model=Dict, tags=["Training & Evaluation"])
async def evaluate_rag(
    request: EvaluationRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)  # Sadece admin
):
    """RAG pipeline'ını değerlendirir (RAGAS)"""
    # WebSocket task oluştur
    task_id = task_manager.create_task(
        user_id=current_user.id,
        task_type="evaluate",
        description="RAG Pipeline Değerlendirmesi"
    )
    
    # Background task başlat
    try:
        # İlerleme güncellemesi
        await task_manager.update_task(task_id, progress=10)
        
        # Örnekler yoksa rastgele örnekler oluştur
        examples = request.examples
        if not examples:
            # İlerleme güncellemesi
            await task_manager.update_task(task_id, progress=20, 
                                          status="Örnekler hazırlanıyor...")
            
            # Random samples oluştur
            examples = await generate_evaluation_samples(
                size=request.sample_size or 5,
                db=db
            )
            
        # İlerleme güncellemesi
        await task_manager.update_task(task_id, progress=30, 
                                      status="Değerlendirme başlatıldı")
        
        # Değerlendirmeyi başlat
        all_metrics = {}
        detailed_results = []
        
        total = len(examples)
        for i, example in enumerate(examples):
            # İlerleme güncelle
            progress = 30 + int((i / total) * 60)
            await task_manager.update_task(task_id, progress=progress, 
                                          status=f"Örnek değerlendiriliyor: {i+1}/{total}")
            
            # Soruyu işle
            question = example["question"]
            ground_truth = example.get("ground_truth")
            contexts = example.get("contexts", [])
            
            # RAG pipeline çalıştır
            if not contexts:
                # Retriever çalıştır
                retrieved_docs = await retrieval_system.retrieve(
                    query=question,
                    search_type="hybrid",
                    top_k=5
                )
                contexts = [doc["text"] for doc in retrieved_docs]
            
            # Generator çalıştır
            model_name = request.model_name
            answer = await llm_manager.generate_from_template(
                "qa", query=question, context="\n\n".join(contexts)
            )
            
            # Değerlendir
            metrics = await evaluator.evaluate_sample(
                question=question,
                answer=answer,
                ground_truth=ground_truth,
                contexts=contexts,
                metrics=request.metrics
            )
            
            # Sonuçları birleştir
            for k, v in metrics.items():
                if k not in all_metrics:
                    all_metrics[k] = []
                all_metrics[k].append(v)
            
            # Detaylı sonuçlar
            detailed_results.append({
                "question": question,
                "ground_truth": ground_truth,
                "model_answer": answer,
                "contexts": contexts,
                "metrics": metrics
            })
        
        # Ortalamaları hesapla
        average_metrics = {}
        for k, values in all_metrics.items():
            average_metrics[k] = sum(values) / len(values)
        
        # Sonucu oluştur
        result = {
            "metrics": average_metrics,
            "detailed_results": detailed_results,
            "timestamp": datetime.utcnow().isoformat(),
            "model_name": request.model_name or "default"
        }
        
        # Task tamamlandı
        await task_manager.update_task(task_id, progress=100, 
                                      status="completed", 
                                      result=average_metrics)
        
        return result
        
    except Exception as e:
        # Hata durumunda
        logger.error(f"RAG evaluation error: {e}", exc_info=True)
        await task_manager.update_task(task_id, status="failed", 
                                      error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG evaluation failed: {str(e)}"
        )


@router.post("/fine-tune", response_model=Dict, tags=["Training & Evaluation"])
async def fine_tune_model(
    request: FineTuningRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)  # Sadece admin
):
    """Modeli fine-tune eder"""
    # WebSocket task oluştur
    task_id = task_manager.create_task(
        user_id=current_user.id,
        task_type="fine-tune",
        description=f"Model Fine-tuning: {request.output_model_name or request.model_name}"
    )
    
    # Background task başlat
    try:
        # Config oluştur
        output_dir = os.path.join("finetuned-models", 
                                 f"{request.output_model_name or 'model-'+ str(uuid.uuid4())[:8]}")
        
        from ..training.fine_tuning import FineTuningConfig
        config = FineTuningConfig(
            model_name=request.model_name,
            output_dir=output_dir,
            epochs=request.epochs or 3,
            batch_size=request.batch_size or 8,
            learning_rate=request.learning_rate or 3e-5,
            use_peft=request.use_lora,
            use_lora=request.use_lora,
            use_8bit=request.use_8bit
        )
        
        # Eğitim örneklerini dönüştür
        training_examples = [
            TrainingExample(
                question=example.question,
                context=example.context,
                answer=example.answer
            ) for example in request.examples
        ]
        
        # Fine-tuning başlat (asenkron)
        result_dir = await fine_tuning_manager.fine_tune(
            examples=training_examples,
            config=config,
            task_id=task_id,
            user_id=current_user.id
        )
        
        # Model bilgilerini kaydet (production'da bir veritabanına kaydedilmelidir)
        model_info = {
            "id": str(uuid.uuid4()),
            "name": request.output_model_name or os.path.basename(output_dir),
            "base_model": request.model_name,
            "type": "fine-tuned",
            "created_at": datetime.utcnow().isoformat(),
            "owner": current_user.username,
            "parameters": {
                "epochs": request.epochs,
                "learning_rate": request.learning_rate,
                "batch_size": request.batch_size,
                "use_lora": request.use_lora,
                "use_8bit": request.use_8bit,
                "num_examples": len(request.examples)
            },
            "path": result_dir
        }
        
        # Veritabanına kaydet (örnek - gerçek implementasyon farklı olabilir)
        # await save_model_info(db, model_info)
        
        return {
            "message": "Fine-tuning başarıyla başladı",
            "task_id": task_id,
            "model_info": model_info
        }
        
    except Exception as e:
        # Hata durumunda
        logger.error(f"Fine-tuning error: {e}", exc_info=True)
        await task_manager.update_task(task_id, status="failed", 
                                      error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fine-tuning failed: {str(e)}"
        )


@router.get("/models", response_model=List[ModelInfo], tags=["Training & Evaluation"])
async def list_models(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Kaydedilmiş modelleri listeler"""
    try:
        # Gerçek veritabanı sorgusu yerine dosya sisteminden okuyoruz
        models_dir = "finetuned-models"
        
        if not os.path.exists(models_dir):
            return []
        
        models = []
        for model_name in os.listdir(models_dir):
            model_path = os.path.join(models_dir, model_name)
            
            if os.path.isdir(model_path):
                # Model bilgilerini config.json'dan oku
                config_path = os.path.join(model_path, "config.json")
                if os.path.exists(config_path):
                    with open(config_path, "r") as f:
                        config = json.load(f)
                else:
                    config = {}
                
                # Model boyutu hesapla
                size_bytes = 0
                for dirpath, _, filenames in os.walk(model_path):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        size_bytes += os.path.getsize(fp)
                
                # Model info oluştur
                models.append(ModelInfo(
                    id=model_name,
                    name=model_name,
                    base_model=config.get("_name_or_path", "unknown"),
                    type="fine-tuned",
                    created_at=datetime.fromtimestamp(
                        os.path.getctime(model_path)
                    ).isoformat(),
                    size_kb=int(size_bytes / 1024),
                    parameters=config,
                    is_active=True
                ))
        
        return models
        
    except Exception as e:
        logger.error(f"List models error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list models: {str(e)}"
        )


async def generate_evaluation_samples(size: int, db: AsyncSession) -> List[Dict]:
    """Değerlendirme için rastgele örnekler oluşturur"""
    try:
        # Gerçek uygulamada daha karmaşık bir mantık olabilir
        # Örneğin veritabanından sorular çekilebilir
        
        # Basit örnek sorular
        questions = [
            "Projenin güvenlik özellikleri nelerdir?",
            "Elasticsearch optimizasyonları nasıl yapılır?",
            "Veri kaynaklarına nasıl veri ekleyebilirim?",
            "Fine-tuning nedir ve nasıl kullanılır?",
            "WebSocket ile arka plan görev takibi nasıl çalışır?",
            "Docker ile projeyi nasıl çalıştırabilirim?",
            "Veritabanı havuzlama neden önemlidir?",
            "Native async veritabanı sürücüleri nedir?",
            "LLM optimizasyonu için hangi teknikler kullanılabilir?",
            "RAG pipeline'ını nasıl değerlendirebilirim?"
        ]
        
        # Daha fazla soru gerekirse rastgele oluştur
        if len(questions) < size:
            for i in range(size - len(questions)):
                questions.append(f"Test soru #{i+1}")
        
        # Örnekleri oluştur
        samples = []
        for i in range(min(size, len(questions))):
            samples.append({
                "question": questions[i],
                "ground_truth": None,  # Gerçek referans cevap olmadan
                "contexts": []  # Retriever tarafından doldurulacak
            })
        
        return samples
        
    except Exception as e:
        logger.error(f"Sample generation error: {e}", exc_info=True)
        raise