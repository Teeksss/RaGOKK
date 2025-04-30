# Last reviewed: 2025-04-30 07:30:01 UTC (User: Teeksss)
from typing import Dict, Any, List, Optional, Tuple
import logging
import uuid
from datetime import datetime, timezone
import json
import random

from sqlalchemy.ext.asyncio import AsyncSession
from ..models.prompt_test import PromptTest, PromptTestResult
from ..repositories.prompt_test_repository import PromptTestRepository
from ..services.llm_service import LLMService
from ..services.query_rewriter import QueryRewriter
from ..services.multi_vector_retriever import MultiVectorRetriever
from ..services.prompt_engine import PromptEngine

logger = logging.getLogger(__name__)

class PromptABTester:
    """
    Prompt şablonları için A/B test servisi.
    
    Farklı şablonları aynı sorgu üzerinde test eder ve karşılaştırır.
    """
    
    def __init__(self):
        """Servis başlangıç ayarları"""
        self.prompt_test_repository = PromptTestRepository()
        self.llm_service = LLMService()
        self.query_rewriter = QueryRewriter()
        self.multi_vector_retriever = MultiVectorRetriever()
        self.prompt_engine = PromptEngine()
    
    async def create_ab_test(self, 
                        db: AsyncSession, 
                        user_id: str,
                        organization_id: Optional[str],
                        name: str,
                        description: str,
                        prompt_template_ids: List[str],
                        test_queries: List[str]) -> Dict[str, Any]:
        """
        Yeni bir A/B test oluşturur
        
        Args:
            db: Veritabanı oturumu
            user_id: Test oluşturan kullanıcı ID
            organization_id: Organizasyon ID
            name: Test adı
            description: Test açıklaması
            prompt_template_ids: Test edilecek şablon ID'leri
            test_queries: Test sorguları
            
        Returns:
            Dict[str, Any]: Oluşturulan test bilgisi
        """
        try:
            # Test nesnesi oluştur
            test = PromptTest(
                id=str(uuid.uuid4()),
                user_id=user_id,
                organization_id=organization_id,
                name=name,
                description=description,
                prompt_template_ids=prompt_template_ids,
                test_queries=test_queries,
                status="created",
                created_at=datetime.now(timezone.utc),
                results={}
            )
            
            # Veritabanına kaydet
            created_test = await self.prompt_test_repository.create_prompt_test(db, test)
            
            return {
                "success": True,
                "test": created_test.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Error creating A/B test: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def run_ab_test(self, 
                     db: AsyncSession, 
                     test_id: str) -> Dict[str, Any]:
        """
        A/B testi çalıştırır
        
        Args:
            db: Veritabanı oturumu
            test_id: Test ID
            
        Returns:
            Dict[str, Any]: Test sonuçları
        """
        try:
            # Testi getir
            test = await self.prompt_test_repository.get_prompt_test_by_id(db, test_id)
            if not test:
                return {"success": False, "error": "Test not found"}
            
            # Testlerin başladığını güncelle
            test.status = "running"
            await self.prompt_test_repository.update_prompt_test_status(db, test_id, "running")
            
            # Her sorgu için her şablonu test et
            results = {}
            
            for query_idx, query in enumerate(test.test_queries):
                query_results = {}
                
                # Sorguyu iyileştir (sorgu öncesi)
                rewritten_query_result = await self.query_rewriter.rewrite_query(query)
                final_query = rewritten_query_result["rewritten_query"] if rewritten_query_result["improved"] else query
                
                # Arama sonuçlarını getir (tüm şablonlar için ortak)
                search_results = await self.multi_vector_retriever.search(
                    query_text=final_query,
                    limit=5,
                    organization_id=test.organization_id,
                    search_type="hybrid"
                )
                
                # Her şablon için test yap
                for template_id in test.prompt_template_ids:
                    # Şablonu getir
                    prompt_template = await self.prompt_engine.get_prompt_template_by_id(db, template_id)
                    
                    if not prompt_template:
                        query_results[template_id] = {
                            "error": f"Template {template_id} not found",
                            "success": False
                        }
                        continue
                    
                    # LLM yanıtı oluştur
                    start_time = datetime.now(timezone.utc)
                    
                    answer, tokens_info = await self.generate_prompt_answer(
                        query=final_query,
                        search_results=search_results["results"],
                        prompt_template=prompt_template
                    )
                    
                    end_time = datetime.now(timezone.utc)
                    processing_time = (end_time - start_time).total_seconds() * 1000
                    
                    # Sonuçları kaydet
                    query_results[template_id] = {
                        "template_id": template_id,
                        "template_name": prompt_template.name,
                        "answer": answer,
                        "tokens": tokens_info,
                        "processing_time_ms": processing_time,
                        "success": True
                    }
                
                # Sorgu sonuçlarını kaydet
                results[f"query_{query_idx+1}"] = {
                    "original_query": query,
                    "final_query": final_query,
                    "rewritten": rewritten_query_result["improved"],
                    "template_results": query_results
                }
                
                # Test sonuçlarını güncelle
                test.results = results
                await self.prompt_test_repository.update_prompt_test_results(db, test_id, results)
            
            # Test tamamlandı
            test.status = "completed"
            test.completed_at = datetime.now(timezone.utc)
            await self.prompt_test_repository.update_prompt_test_status(db, test_id, "completed", test.completed_at)
            
            return {
                "success": True,
                "test_id": test_id,
                "results": results,
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"Error running A/B test: {str(e)}")
            # Hata durumunda test statüsünü güncelle
            await self.prompt_test_repository.update_prompt_test_status(db, test_id, "failed")
            return {"success": False, "error": str(e)}
    
    async def generate_prompt_answer(self, 
                                query: str, 
                                search_results: List[Dict[str, Any]],
                                prompt_template: Any) -> Tuple[str, Dict[str, int]]:
        """
        Belirli bir prompt şablonu kullanarak yanıt oluşturur
        
        Args:
            query: Kullanıcı sorusu
            search_results: Arama sonuçları
            prompt_template: Prompt şablonu
            
        Returns:
            Tuple[str, Dict[str, int]]: Yanıt ve token bilgileri
        """
        try:
            # Bağlam oluştur
            context_parts = []
            for idx, result in enumerate(search_results):
                content = result.get("content", "")
                if content:
                    context_parts.append(f"[{idx+1}] {content}")
            
            context = "\n\n".join(context_parts)
            
            # Şablonu doldur
            prompt = prompt_template.template.replace("{{query}}", query).replace("{{context}}", context)
            
            # LLM yanıtı oluştur
            response = await self.llm_service.generate_text(prompt)
            
            # Token bilgileri
            tokens_info = {
                "prompt_tokens": response.get("usage", {}).get("prompt_tokens", 0),
                "completion_tokens": response.get("usage", {}).get("completion_tokens", 0),
                "total_tokens": response.get("usage", {}).get("total_tokens", 0)
            }
            
            # Yanıtı döndür
            return response.get("text", ""), tokens_info
            
        except Exception as e:
            logger.error(f"Error generating prompt answer: {str(e)}")
            return f"Error: {str(e)}", {"error": str(e)}
    
    async def get_test_results(self, 
                          db: AsyncSession, 
                          test_id: str) -> Dict[str, Any]:
        """
        Test sonuçlarını getirir
        
        Args:
            db: Veritabanı oturumu
            test_id: Test ID
            
        Returns:
            Dict[str, Any]: Test sonuçları
        """
        try:
            # Testi getir
            test = await self.prompt_test_repository.get_prompt_test_by_id(db, test_id)
            if not test:
                return {"success": False, "error": "Test not found"}
            
            # Test henüz tamamlanmadıysa kontrol et
            if test.status == "running":
                return {
                    "success": True,
                    "status": "running",
                    "test_id": test_id,
                    "results": test.results or {},
                    "progress": len(test.results.keys()) / len(test.test_queries) if test.results else 0
                }
            
            # Test tamamlandıysa sonuçları analiz et
            if test.status == "completed":
                analysis = self._analyze_test_results(test.results, test.prompt_template_ids)
                
                return {
                    "success": True,
                    "status": "completed",
                    "test_id": test_id,
                    "results": test.results,
                    "analysis": analysis,
                    "created_at": test.created_at.isoformat(),
                    "completed_at": test.completed_at.isoformat() if test.completed_at else None
                }
            
            # Diğer durumlar
            return {
                "success": True,
                "status": test.status,
                "test_id": test_id,
                "results": test.results or {}
            }
            
        except Exception as e:
            logger.error(f"Error getting test results: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _analyze_test_results(self, 
                          results: Dict[str, Any],
                          template_ids: List[str]) -> Dict[str, Any]:
        """
        Test sonuçlarını analiz eder
        
        Args:
            results: Test sonuçları
            template_ids: Şablon ID'leri
            
        Returns:
            Dict[str, Any]: Analiz sonuçları
        """
        try:
            # Her şablon için metrikleri hesapla
            template_metrics = {}
            for template_id in template_ids:
                template_metrics[template_id] = {
                    "avg_tokens": 0,
                    "avg_processing_time": 0,
                    "success_count": 0,
                    "total_count": 0
                }
            
            # Tüm sorgu sonuçlarını döngüle
            total_queries = len(results)
            for query_key, query_data in results.items():
                template_results = query_data.get("template_results", {})
                
                for template_id, template_result in template_results.items():
                    if template_id not in template_metrics:
                        continue
                        
                    # Başarılı mı?
                    if template_result.get("success", False):
                        template_metrics[template_id]["success_count"] += 1
                        
                        # Token ve işlem süresi toplamını güncelle
                        tokens = template_result.get("tokens", {}).get("total_tokens", 0)
                        processing_time = template_result.get("processing_time_ms", 0)
                        
                        template_metrics[template_id]["avg_tokens"] += tokens
                        template_metrics[template_id]["avg_processing_time"] += processing_time
                    
                    template_metrics[template_id]["total_count"] += 1
            
            # Ortalamalar hesapla
            for template_id, metrics in template_metrics.items():
                if metrics["total_count"] > 0:
                    metrics["avg_tokens"] = round(metrics["avg_tokens"] / metrics["total_count"], 2)
                    metrics["avg_processing_time"] = round(metrics["avg_processing_time"] / metrics["total_count"], 2)
                    metrics["success_rate"] = round(metrics["success_count"] / metrics["total_count"] * 100, 2)
                else:
                    metrics["avg_tokens"] = 0
                    metrics["avg_processing_time"] = 0
                    metrics["success_rate"] = 0
            
            # En iyi şablonu bul
            best_template = None
            best_success_rate = -1
            
            for template_id, metrics in template_metrics.items():
                if metrics["success_rate"] > best_success_rate:
                    best_success_rate = metrics["success_rate"]
                    best_template = template_id
            
            return {
                "template_metrics": template_metrics,
                "best_template": best_template,
                "total_queries": total_queries
            }
            
        except Exception as e:
            logger.error(f"Error analyzing test results: {str(e)}")
            return {"error": str(e)}