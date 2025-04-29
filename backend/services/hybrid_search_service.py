# Last reviewed: 2025-04-29 12:43:06 UTC (User: TeeksssKullanıcı Davranışları İzleme)
import logging
import asyncio
import time
import os
from typing import Dict, List, Any, Optional, Tuple, Union
from enum import Enum
from datetime import datetime
import numpy as np

from ..services.vector_service import VectorService
from ..repositories.document_repository import DocumentRepository
from ..services.full_text_search import FullTextSearchService
from ..utils.ranking import RankingUtils
from ..db.session import get_db, SessionLocal

logger = logging.getLogger(__name__)

class SearchMethod(Enum):
    """Arama yöntemleri"""
    VECTOR = "vector"  # Vektör araması
    FULL_TEXT = "full_text"  # Tam metin araması
    HYBRID = "hybrid"  # Hibrit arama (hem vektör hem tam metin)
    HYBRID_RERANK = "hybrid_rerank"  # Hibrit arama + yeniden sıralama

class HybridSearchService:
    """
    Vektör araması ve tam metin aramasını birleştiren hibrit arama servisi.
    
    Özellikler:
    - Semantik vektör araması
    - BM25 tam metin araması
    - Hybrid RRF (Reciprocal Rank Fusion) ile sonuçları birleştirir
    - Re-ranking ile sonuçları iyileştirir
    - Her iki arama yöntemi için ağırlık ayarlama
    """
    
    def __init__(self, vector_weight: float = 0.7, use_reranking: bool = True):
        """
        Args:
            vector_weight: Vektör araması sonuçlarının ağırlığı (0-1)
            use_reranking: Yeniden sıralama kullan
        """
        self.vector_service = VectorService()
        self.document_repo = DocumentRepository()
        self.full_text_service = FullTextSearchService()
        self.ranking_utils = RankingUtils()
        
        # Arama ağırlığı (vektör vs. tam metin)
        self.vector_weight = max(0.0, min(1.0, vector_weight))
        self.full_text_weight = 1.0 - self.vector_weight
        
        # Yeniden sıralama kullan mı?
        self.use_reranking = use_reranking
        
        # Varsayılan arama yöntemi
        self.default_method = SearchMethod.HYBRID
    
    async def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        method: Optional[SearchMethod] = None,
        limit: int = 10,
        offset: int = 0,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Hibrit arama yapar
        
        Args:
            query: Arama sorgusu
            filters: Filtreler
            method: Arama yöntemi
            limit: Sonuç limiti
            offset: Sonuç offseti
            user_id: Kullanıcı ID'si
            
        Returns:
            Dict: Arama sonuçları
        """
        search_start = time.time()
        method = method or self.default_method
        filters = filters or {}
        
        # Yöntem belirtilmemişse veya hibrit isteniyorsa
        if method == SearchMethod.HYBRID or method == SearchMethod.HYBRID_RERANK:
            results = await self._hybrid_search(query, filters, limit, offset, user_id, method)
        elif method == SearchMethod.VECTOR:
            results = await self._vector_search(query, filters, limit, offset, user_id)
        elif method == SearchMethod.FULL_TEXT:
            results = await self._full_text_search(query, filters, limit, offset, user_id)
        else:
            raise ValueError(f"Unsupported search method: {method}")
        
        # Toplam süreyi hesapla
        search_time = time.time() - search_start
        results["search_time"] = search_time
        results["search_method"] = method.value
        
        return results
    
    async def _hybrid_search(
        self,
        query: str,
        filters: Dict[str, Any],
        limit: int,
        offset: int,
        user_id: Optional[str],
        method: SearchMethod
    ) -> Dict[str, Any]:
        """
        Hibrit arama (vektör + tam metin)
        
        Args:
            query: Arama sorgusu
            filters: Filtreler
            limit: Sonuç limiti
            offset: Sonuç offseti
            user_id: Kullanıcı ID'si
            method: Arama yöntemi
            
        Returns:
            Dict: Arama sonuçları
        """
        # Her iki arama yöntemini paralel çalıştır
        search_tasks = [
            self._vector_search(query, filters, limit * 2, 0, user_id),  # Daha fazla sonuç al (birleştirme için)
            self._full_text_search(query, filters, limit * 2, 0, user_id)
        ]
        
        # Sonuçları bekle
        search_results = await asyncio.gather(*search_tasks)
        
        vector_results = search_results[0]
        full_text_results = search_results[1]
        
        # Sonuçları birleştir ve sırala
        merged_results = await self._merge_search_results(
            vector_results["results"],
            full_text_results["results"],
            self.vector_weight,
            self.full_text_weight
        )
        
        # Birleştirilmiş sonuçlarda sayfalama yap
        paginated_results = merged_results[offset:offset+limit]
        
        # HybridRerank modunda ise, son sonuçları yeniden sırala
        if method == SearchMethod.HYBRID_RERANK and self.use_reranking:
            paginated_results = await self._rerank_results(query, paginated_results, user_id)
        
        # Sonuçları zenginleştir (ek alanlar ekle)
        enriched_results = await self._enrich_search_results(paginated_results, query, user_id)
        
        return {
            "query": query,
            "results": enriched_results,
            "total": len(merged_results),
            "limit": limit,
            "offset": offset,
            "filters": filters,
            "vector_time": vector_results["search_time"],
            "full_text_time": full_text_results["search_time"],
            "vector_count": len(vector_results["results"]),
            "full_text_count": len(full_text_results["results"])
        }
    
    async def _vector_search(
        self,
        query: str,
        filters: Dict[str, Any],
        limit: int,
        offset: int,
        user_id: Optional[str]
    ) -> Dict[str, Any]:
        """
        Vektör tabanlı arama yapar
        
        Args:
            query: Arama sorgusu
            filters: Filtreler
            limit: Sonuç limiti
            offset: Sonuç offseti
            user_id: Kullanıcı ID'si
            
        Returns:
            Dict: Arama sonuçları
        """
        search_start = time.time()
        
        # Sorgu embeddingini oluştur
        query_embedding = await self.vector_service.create_embedding(query)
        
        # Vektör araması yap
        search_results = await self.vector_service.search(
            embedding=query_embedding,
            filters=filters,
            top_k=limit + offset
        )
        
        # Sonuçları dokümanlarla birleştir
        async with SessionLocal() as db:
            document_ids = []
            for item in search_results:
                metadata = item["metadata"]
                if "document_id" in metadata:
                    document_ids.append(int(metadata["document_id"]))
            
            # Belirtilen dokümanları getir
            documents = await self.document_repo.get_documents_by_ids(db, document_ids)
            
            # Yetki filtresi: private dokümanları filtrele
            if user_id:
                documents = [
                    doc for doc in documents if
                    doc["is_public"] or doc["owner_id"] == user_id or
                    await self.document_repo.check_user_permission(db, doc["id"], user_id, "read")
                ]
        
        # Sonuçları birleştir
        results = []
        for rank, item in enumerate(search_results):
            metadata = item["metadata"]
            if "document_id" in metadata:
                doc_id = int(metadata["document_id"])
                
                # Eşleşen dokümanı bul
                doc = next((d for d in documents if d["id"] == doc_id), None)
                if doc:
                    # Özet ve içerik bölümünü ekle
                    context = metadata.get("text", "")
                    chunk_start = metadata.get("chunk_start", 0)
                    
                    results.append({
                        "id": doc_id,
                        "document_id": doc_id,
                        "title": doc["title"],
                        "source_type": doc["source_type"],
                        "score": float(item["score"]),  # Benzerlik skoru
                        "context": context,
                        "context_position": chunk_start,
                        "rank": rank,
                        "search_method": "vector",
                        "is_owner": doc["owner_id"] == user_id if user_id else False,
                        "is_public": doc["is_public"],
                        "created_at": doc["created_at"]
                    })
        
        # Ofset ve limit uygula
        results = results[offset:offset+limit]
        
        search_time = time.time() - search_start
        
        return {
            "query": query,
            "results": results,
            "total": len(search_results),
            "limit": limit,
            "offset": offset,
            "filters": filters,
            "search_time": search_time,
            "search_method": "vector"
        }
    
    async def _full_text_search(
        self,
        query: str,
        filters: Dict[str, Any],
        limit: int,
        offset: int,
        user_id: Optional[str]
    ) -> Dict[str, Any]:
        """
        Tam metin araması yapar
        
        Args:
            query: Arama sorgusu
            filters: Filtreler
            limit: Sonuç limiti
            offset: Sonuç offseti
            user_id: Kullanıcı ID'si
            
        Returns:
            Dict: Arama sonuçları
        """
        search_start = time.time()
        
        # Tam metin araması yap
        async with SessionLocal() as db:
            search_results = await self.full_text_service.search(
                db=db,
                query=query,
                filters=filters,
                limit=limit + offset,
                offset=0,
                user_id=user_id
            )
        
        # Sonuçları işle
        results = []
        for rank, item in enumerate(search_results["results"]):
            # Özet ve içerik bölümünü ekle
            context = item.get("highlight", item.get("content_snippet", ""))
            
            results.append({
                "id": item["document_id"],
                "document_id": item["document_id"],
                "title": item["title"],
                "source_type": item.get("source_type", "unknown"),
                "score": float(item["score"]),  # BM25 skoru
                "context": context,
                "context_position": 0,  # Tam metin aramada pozisyon bilgisi yok
                "rank": rank,
                "search_method": "full_text",
                "is_owner": item.get("is_owner", False),
                "is_public": item.get("is_public", True),
                "created_at": item.get("created_at", None)
            })
        
        # Ofset ve limit uygula
        results = results[offset:offset+limit]
        
        search_time = time.time() - search_start
        
        return {
            "query": query,
            "results": results,
            "total": search_results["total"],
            "limit": limit,
            "offset": offset,
            "filters": filters,
            "search_time": search_time,
            "search_method": "full_text"
        }
    
    async def _merge_search_results(
        self,
        vector_results: List[Dict[str, Any]],
        full_text_results: List[Dict[str, Any]],
        vector_weight: float,
        full_text_weight: float
    ) -> List[Dict[str, Any]]:
        """
        İki arama sonucunu birleştirir ve sıralar
        
        Args:
            vector_results: Vektör arama sonuçları
            full_text_results: Tam metin arama sonuçları
            vector_weight: Vektör arama ağırlığı
            full_text_weight: Tam metin arama ağırlığı
            
        Returns:
            List[Dict[str, Any]]: Birleştirilmiş sonuçlar
        """
        # Birleştirilmiş sonuçlar için sözlük
        merged_dict = {}
        
        # Vektör sonuçlarını ekle
        for item in vector_results:
            doc_id = item["document_id"]
            
            if doc_id not in merged_dict:
                merged_dict[doc_id] = item.copy()
                merged_dict[doc_id]["original_scores"] = {
                    "vector": item["score"],
                    "full_text": 0.0
                }
                
                # Birleştirilmiş skor (şimdilik sadece vektör)
                merged_dict[doc_id]["combined_score"] = item["score"] * vector_weight
                merged_dict[doc_id]["search_method"] = "hybrid"
            
        # Tam metin sonuçlarını ekle/güncelle
        for item in full_text_results:
            doc_id = item["document_id"]
            
            if doc_id in merged_dict:
                # Doküman zaten vektör sonuçlarından eklenmiş
                merged_dict[doc_id]["original_scores"]["full_text"] = item["score"]
                
                # Tam metin arama skorunu ekle
                merged_dict[doc_id]["combined_score"] += item["score"] * full_text_weight
                
                # Bağlam bilgisini güncelle (tam metin araması daha iyi bağlam sunar)
                if item.get("context"):
                    merged_dict[doc_id]["context"] = item["context"]
            else:
                # Yeni bir doküman ekle
                merged_dict[doc_id] = item.copy()
                merged_dict[doc_id]["original_scores"] = {
                    "vector": 0.0,
                    "full_text": item["score"]
                }
                
                # Birleştirilmiş skor (sadece tam metin)
                merged_dict[doc_id]["combined_score"] = item["score"] * full_text_weight
                merged_dict[doc_id]["search_method"] = "hybrid"
        
        # Sözlükten liste oluştur
        merged_list = list(merged_dict.values())
        
        # Birleştirilmiş skora göre sırala
        merged_list.sort(key=lambda x: x["combined_score"], reverse=True)
        
        # Rankları güncelle
        for i, item in enumerate(merged_list):
            item["rank"] = i
            
            # Ana skoru güncelle
            item["score"] = item["combined_score"]
        
        return merged_list
    
    async def _rerank_results(
        self,
        query: str,
        results: List[Dict[str, Any]],
        user_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Arama sonuçlarını yeniden sıralar (ince ayar)
        
        Args:
            query: Arama sorgusu
            results: Arama sonuçları
            user_id: Kullanıcı ID'si
            
        Returns:
            List[Dict[str, Any]]: Yeniden sıralanmış sonuçlar
        """
        if not results:
            return results
            
        try:
            # Yeniden sıralama modeli kullan
            reranked_results = await self.ranking_utils.rerank_results(
                query=query,
                results=results,
                context_field="context"
            )
            
            # Kullanıcı etkileşimlerine göre kişiselleştir
            if user_id:
                personalized_results = await self.ranking_utils.personalize_results(
                    results=reranked_results,
                    user_id=user_id
                )
                return personalized_results
            
            return reranked_results
            
        except Exception as e:
            logger.error(f"Reranking error: {e}")
            return results  # Hata durumunda orijinal sonuçları döndür
    
    async def _enrich_search_results(
        self,
        results: List[Dict[str, Any]],
        query: str,
        user_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Arama sonuçlarını zenginleştirir
        
        Args:
            results: Arama sonuçları
            query: Arama sorgusu
            user_id: Kullanıcı ID'si
            
        Returns:
            List[Dict[str, Any]]: Zenginleştirilmiş sonuçlar
        """
        if not results:
            return results
            
        try:
            # Doküman ID'lerini topla
            doc_ids = [result["document_id"] for result in results]
            
            # Dokümanların etiketlerini getir
            async with SessionLocal() as db:
                tags_by_document = await self.document_repo.get_tags_for_documents(db, doc_ids)
            
            # Sonuçları güncelle
            for result in results:
                doc_id = result["document_id"]
                
                # Etiketleri ekle
                if doc_id in tags_by_document:
                    result["tags"] = tags_by_document[doc_id]
                else:
                    result["tags"] = []
                
                # Özet oluşturma
                if not result.get("snippet") and result.get("context"):
                    # Context'ten özet oluştur
                    result["snippet"] = self._create_snippet(result["context"], query, max_length=160)
            
            return results
                
        except Exception as e:
            logger.error(f"Result enrichment error: {e}")
            return results  # Hata durumunda orijinal sonuçları döndür
    
    def _create_snippet(self, text: str, query: str, max_length: int = 160) -> str:
        """
        Metin içinde sorgu terimlerini içeren bir özet oluşturur
        
        Args:
            text: Metin
            query: Sorgu
            max_length: Maksimum özet uzunluğu
            
        Returns:
            str: Özet
        """
        if not text:
            return ""
            
        # Metni temizle
        text = text.replace("\n", " ").replace("\r", " ")
        text = " ".join(text.split())
        
        # Çok uzunsa kısalt
        if len(text) <= max_length:
            return text
            
        # Sorgu terimlerini bul
        query_terms = set(query.lower().split())
        
        # En iyi eşleşen cümleyi bul
        sentences = text.split(". ")
        best_sentence = None
        best_score = -1
        
        for sentence in sentences:
            if not sentence.strip():
                continue
                
            # Sorgu terimleri ile eşleşme skoru
            score = 0
            sentence_lower = sentence.lower()
            for term in query_terms:
                if term in sentence_lower:
                    score += 1
            
            if score > best_score:
                best_score = score
                best_sentence = sentence
        
        # Eğer hiçbir cümlede eşleşme yoksa, metni kısalt
        if best_score == 0 or not best_sentence:
            return text[:max_length-3] + "..."
            
        # En iyi cümle çok uzunsa kısalt
        if len(best_sentence) > max_length:
            return best_sentence[:max_length-3] + "..."
            
        return best_sentence