# Last reviewed: 2025-04-29 08:07:22 UTC (User: TeeksssNative)
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import asyncio
from pydantic import BaseModel

try:
    from ragas import evaluate
    from ragas.metrics import (
        faithfulness, answer_relevancy, 
        context_precision, context_recall,
        answer_correctness, answer_similarity
    )
    RAGAS_AVAILABLE = True
except ImportError:
    RAGAS_AVAILABLE = False

from ..utils.logger import get_logger
from ..utils.config import RAGAS_METRICS
from ..models.data_models import DocumentSnippet
from ..models.evaluation_models import EvaluationResult, EvaluationItem

logger = get_logger(__name__)

class RAGEvaluator:
    def __init__(self):
        self._check_ragas_available()
        self.metrics_map = {
            "faithfulness": faithfulness if RAGAS_AVAILABLE else None,
            "answer_relevancy": answer_relevancy if RAGAS_AVAILABLE else None,
            "context_precision": context_precision if RAGAS_AVAILABLE else None,
            "context_recall": context_recall if RAGAS_AVAILABLE else None,
            "answer_correctness": answer_correctness if RAGAS_AVAILABLE else None,
            "answer_similarity": answer_similarity if RAGAS_AVAILABLE else None,
        }
    
    def _check_ragas_available(self):
        if not RAGAS_AVAILABLE:
            logger.warning("RAGAS kütüphanesi yüklü değil! Değerlendirme yapılamayacak.")
            logger.warning("Lütfen 'pip install ragas' komutunu çalıştırın.")
    
    async def evaluate_sample(
        self, 
        question: str, 
        answer: str, 
        ground_truth: str,
        contexts: List[str],
        metrics: Optional[List[str]] = None
    ) -> Dict[str, float]:
        """
        Bir soru-cevap örneğini değerlendirir.
        
        Args:
            question: Soru metni
            answer: Model yanıtı
            ground_truth: Referans yanıt
            contexts: Kullanılan bağlamlar (retriever tarafından getirilen)
            metrics: Kullanılacak metrikler listesi
            
        Returns:
            Dict[str, float]: Metrik sonuçları
        """
        if not RAGAS_AVAILABLE:
            logger.error("RAGAS kütüphanesi yüklü değil, değerlendirme yapılamıyor.")
            return {"error": "RAGAS kütüphanesi yüklü değil"}
            
        if not metrics:
            metrics = RAGAS_METRICS
        
        # RAGAS değerlendirme için veriyi hazırla
        # Not: RAGAS senkron çalıştığı için bu async fonksiyon içinde
        # asyncio.to_thread kullanacağız (CPU-bound task)
        
        result_dict = {}
        
        # Geçersiz metrik isteği?
        metrics = [m for m in metrics if m in self.metrics_map]
        if not metrics:
            logger.warning("Geçerli metrik belirtilmedi.")
            return {"error": "No valid metrics specified"}
        
        try:
            # Veri çerçevesi oluştur
            data = {
                "question": [question],
                "answer": [answer],
                "contexts": [contexts]
            }
            
            # Ground truth (doğru yanıt) varsa ekle
            if ground_truth:
                data["ground_truth"] = [ground_truth]
            
            # Her metriği asenkron değerlendir
            logger.info(f"Evaluation başlatılıyor - question: '{question[:30]}...'")
            
            # RAGAS'ın değerlendirme fonksiyonu CPU-bound ve senkron,
            # bu nedenle thread pool'da çalıştıralım
            async def evaluate_metric(metric_name):
                metric = self.metrics_map.get(metric_name)
                if not metric:
                    return None
                
                # Metriğin ground_truth gerektirip gerektirmediğini kontrol et
                requires_ground_truth = metric_name in ["answer_correctness", "answer_similarity"]
                if requires_ground_truth and "ground_truth" not in data:
                    logger.warning(f"{metric_name} ground_truth gerektiriyor ama sağlanmamış.")
                    return None
                
                try:
                    # Metriği thread pool'da değerlendir
                    result = await asyncio.to_thread(
                        evaluate, 
                        data, 
                        metrics=[metric]
                    )
                    score = result.get(metric_name)
                    if score is not None:
                        # Tek değer varsa numpy -> float dönüşümü yap
                        if hasattr(score, 'iloc') and len(score) > 0:
                            return float(score.iloc[0])
                        return float(score)
                    return None
                except Exception as e:
                    logger.error(f"{metric_name} değerlendirme hatası: {e}", exc_info=True)
                    return None
            
            # Tüm metrikleri paralel değerlendir
            metric_tasks = [evaluate_metric(metric_name) for metric_name in metrics]
            metric_results = await asyncio.gather(*metric_tasks)
            
            # Sonuçları dictionary'e yükle
            for metric_name, result in zip(metrics, metric_results):
                if result is not None:
                    result_dict[metric_name] = result
            
            logger.info(f"Evaluation tamamlandı - sonuçlar: {result_dict}")
            return result_dict
            
        except Exception as e:
            logger.error(f"RAGAS evaluation error: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def evaluate_batch(
        self, 
        samples: List[Dict],
        metrics: Optional[List[str]] = None,
        progress_callback = None
    ) -> Dict[str, float]:
        """
        Birden fazla soru-cevap çiftini değerlendirir ve ortalama değerleri döndürür.
        
        Args:
            samples: Değerlendirilecek örnekler listesi
                Her örnek: {"question": str, "answer": str, "ground_truth": str, "contexts": List[str]}
            metrics: Kullanılacak metrikler listesi
            progress_callback: İlerleme bildirimi için callback fonksiyonu
            
        Returns:
            Dict[str, float]: Ortalama metrik sonuçları
        """
        if not RAGAS_AVAILABLE:
            logger.error("RAGAS kütüphanesi yüklü değil, değerlendirme yapılamıyor.")
            return {"error": "RAGAS kütüphanesi yüklü değil"}
            
        if not samples:
            logger.warning("Değerlendirilecek örnek yok.")
            return {}
            
        if not metrics:
            metrics = RAGAS_METRICS
            
        # Tüm sonuçları topla
        all_results = []
        detailed_results = []
        
        total_samples = len(samples)
        processed = 0
        
        for sample in samples:
            # Her örneği değerlendir
            try:
                question = sample.get("question", "")
                answer = sample.get("answer", "")
                ground_truth = sample.get("ground_truth", "")
                contexts = sample.get("contexts", [])
                
                result = await self.evaluate_sample(
                    question=question,
                    answer=answer,
                    ground_truth=ground_truth,
                    contexts=contexts,
                    metrics=metrics
                )
                
                if "error" not in result:
                    all_results.append(result)
                    # Detaylı sonuç
                    detailed_results.append({
                        "question": question,
                        "answer": answer,
                        "metrics": result
                    })
                    
                processed += 1
                if progress_callback