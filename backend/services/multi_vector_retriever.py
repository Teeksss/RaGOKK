# Last reviewed: 2025-04-30 06:23:58 UTC (User: Teeksss)
from typing import List, Dict, Any, Optional, Union
import numpy as np
import logging
from datetime import datetime, timezone
import asyncio
import math
import os
import json

logger = logging.getLogger(__name__)

class MultiVectorRetriever:
    """
    Multi-Vector Retriever sınıfı.
    Dense ve Sparse (lexical) yöntemleri birleştirir.
    """
    
    def __init__(self, 
                dense_weight: float = 0.6, 
                sparse_weight: float = 0.4,
                use_rrf: bool = True,
                rrf_k: int = 60):
        """
        Args:
            dense_weight: Dense retrieval sonuçlarının ağırlığı (0-1)
            sparse_weight: Sparse retrieval sonuçlarının ağırlığı (0-1)
            use_rrf: Reciprocal Rank Fusion kullan
            rrf_k: RRF k sabiti
        """
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight
        self.use_rrf = use_rrf
        self.rrf_k = rrf_k
        
        # Dense retriever (vektör tabanlı)
        from .vector_service import VectorService
        self.dense_retriever = VectorService()
        
        # Sparse retriever (BM25/ElasticSearch)
        from .sparse_retriever import SparseRetriever
        self.sparse_retriever = SparseRetriever()
        
        # Her iki retriever'ın çalışıp çalışmadığını kontrol et
        self.dense_available = self._check_dense_availability()
        self.sparse_available = self._check_sparse_availability()
        
    def _check_dense_availability(self) -> bool:
        """Dense retriever'ın kullanılabilirliğini kontrol eder"""
        return self.dense_retriever is not None
        
    def _check_sparse_availability(self) -> bool:
        """Sparse retriever'ın kullanılabilirliğini kontrol eder"""
        return self.sparse_retriever is not None
    
    async def search(self, 
                   query_text: str,
                   limit: int = 10,
                   organization_id: Optional[str] = None,
                   filters: Optional[Dict[str, Any]] = None,
                   search_type: str = "hybrid") -> Dict[str, Any]:
        """
        Metin tabanlı arama yapar
        
        Args:
            query_text: Arama sorgusu
            limit: Maksimum sonuç sayısı
            organization_id: Organizasyon ID
            filters: Metadata filtreleri
            search_type: Arama türü ('hybrid', 'dense', 'sparse')
            
        Returns:
            Dict[str, Any]: Arama sonuçları ve performans metrikleri
        """
        start_time = datetime.now(timezone.utc)
        
        # Arama tipini kontrol et
        if search_type not in ["hybrid", "dense", "sparse"]:
            search_type = "hybrid"
            
        # Hybrid arama, her iki retriever'ı da kullanabilir durumdaysa
        if search_type == "hybrid" and self.dense_available and self.sparse_available:
            results = await self._hybrid_search(query_text, limit, organization_id, filters)
        # Dense arama sadece dense retriever 
        elif (search_type == "dense" or not self.sparse_available) and self.dense_available:
            results = await self._dense_search(query_text, limit, organization_id, filters)
        # Sparse arama sadece sparse retriever
        elif (search_type == "sparse" or not self.dense_available) and self.sparse_available:
            results = await self._sparse_search(query_text, limit, organization_id, filters)
        # Fallback: En az biri çalışıyor olmalı
        else:
            if self.dense_available:
                results = await self._dense_search(query_text, limit, organization_id, filters)
            elif self.sparse_available:
                results = await self._sparse_search(query_text, limit, organization_id, filters)
            else:
                return {
                    "results": [],
                    "query": query_text,
                    "count": 0,
                    "search_type": "none",
                    "error": "No retriever available"
                }
        
        # Performans metrikleri ekle
        end_time = datetime.now(timezone.utc)
        processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        # Sonuç ve ek bilgileri döndür
        return {
            "results": results,
            "query": query_text,
            "count": len(results),
            "search_type": search_type,
            "processing_time_ms": processing_time_ms,
            "most_effective_retriever": self._get_most_effective_retriever(results),
            "hybrid_method": "rrf" if self.use_rrf else "weighted"
        }
    
    async def _dense_search(self, 
                          query_text: str, 
                          limit: int,
                          organization_id: Optional[str] = None,
                          filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Dense (vektor) arama yapar"""
        results = await self.dense_retriever.search(
            query_text=query_text,
            limit=limit,
            organization_id=organization_id,
            filters=filters
        )
        
        # Her sonuca retriever bilgisi ekle
        for result in results:
            result["retriever"] = "dense"
            
        return results
    
    async def _sparse_search(self, 
                           query_text: str, 
                           limit: int,
                           organization_id: Optional[str] = None,
                           filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Sparse (BM25) arama yapar"""
        results = await self.sparse_retriever.search(
            query_text=query_text,
            limit=limit,
            organization_id=organization_id,
            filters=filters
        )
        
        # Her sonuca retriever bilgisi ekle
        for result in results:
            result["retriever"] = "sparse"
            
        return results
    
    async def _hybrid_search(self, 
                           query_text: str, 
                           limit: int,
                           organization_id: Optional[str] = None,
                           filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Hybrid arama (dense + sparse fusion)"""
        # Her iki sorguyu paralel yürüt
        dense_task = asyncio.create_task(self._dense_search(
            query_text=query_text,
            limit=limit*2,  # Birleştirmeden sonra filtrelemek için daha fazla sonuç al
            organization_id=organization_id,
            filters=filters
        ))
        
        sparse_task = asyncio.create_task(self._sparse_search(
            query_text=query_text,
            limit=limit*2,  # Birleştirmeden sonra filtrelemek için daha fazla sonuç al
            organization_id=organization_id,
            filters=filters
        ))
        
        # Her iki sonucu bekle
        dense_results, sparse_results = await asyncio.gather(dense_task, sparse_task)
        
        # Hybrid sıralama: RRF veya ağırlıklı birleştirme
        if self.use_rrf:
            merged_results = self._reciprocal_rank_fusion(dense_results, sparse_results)
        else:
            merged_results = self._weighted_merge(dense_results, sparse_results)
            
        # Sınırla
        return merged_results[:limit]
    
    def _reciprocal_rank_fusion(self, dense_results: List[Dict[str, Any]], sparse_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Reciprocal Rank Fusion algoritması ile sonuçları birleştirir
        RRF skor = sum(1 / (k + rank_i)) for each retriever
        """
        # Tüm belge ID'leri
        all_doc_ids = set()
        for result in dense_results:
            all_doc_ids.add(result.get("metadata", {}).get("segment_id"))
        for result in sparse_results:
            all_doc_ids.add(result.get("metadata", {}).get("segment_id"))
            
        # Rank haritaları oluştur
        dense_ranks = {}
        for i, result in enumerate(dense_results):
            doc_id = result.get("metadata", {}).get("segment_id")
            dense_ranks[doc_id] = i + 1  # ranks start at 1
        
        sparse_ranks = {}
        for i, result in enumerate(sparse_results):
            doc_id = result.get("metadata", {}).get("segment_id")
            sparse_ranks[doc_id] = i + 1  # ranks start at 1
            
        # RRF skorlarını hesapla
        rrf_scores = {}
        k = self.rrf_k  # RRF sabiti
        
        for doc_id in all_doc_ids:
            # Belge her iki sıralamada da varsa
            dense_rank = dense_ranks.get(doc_id, float('inf'))
            sparse_rank = sparse_ranks.get(doc_id, float('inf'))
            
            rrf_score = 0
            if dense_rank != float('inf'):
                rrf_score += 1.0 / (k + dense_rank)
            if sparse_rank != float('inf'):
                rrf_score += 1.0 / (k + sparse_rank)
                
            rrf_scores[doc_id] = rrf_score
        
        # Sonuçları birleştir
        merged_results = []
        doc_id_to_result = {}
        
        # Belge ID'ye göre sonuç erişimi için harita oluştur
        for result in dense_results:
            doc_id = result.get("metadata", {}).get("segment_id")
            doc_id_to_result[doc_id] = result
            
        for result in sparse_results:
            doc_id = result.get("metadata", {}).get("segment_id")
            if doc_id not in doc_id_to_result:
                doc_id_to_result[doc_id] = result
        
        # RRF skorlarına göre sırala ve sonuçları oluştur
        sorted_doc_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        
        for doc_id in sorted_doc_ids:
            if doc_id in doc_id_to_result:
                result = doc_id_to_result[doc_id].copy()
                
                # Hangi retriever'ların eşleştiğini göster
                match_sources = []
                if doc_id in dense_ranks:
                    match_sources.append("dense")
                if doc_id in sparse_ranks:
                    match_sources.append("sparse")
                    
                # Sonuca RRF skoru ekle
                result["score"] = rrf_scores[doc_id]  # Original score ile değiştir
                result["retriever"] = "+".join(match_sources)
                result["rrf_score"] = rrf_scores[doc_id]
                
                merged_results.append(result)
                
        return merged_results
    
    def _weighted_merge(self, dense_results: List[Dict[str, Any]], sparse_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ağırlıklı birleştirme algoritması"""
        # Segment ID -> sonuç eşlemesi
        result_map = {}
        
        # Dense sonuçları ekle
        for result in dense_results:
            doc_id = result.get("metadata", {}).get("segment_id")
            if doc_id:
                result_map[doc_id] = {
                    "result": result,
                    "dense_score": result.get("score", 0) * self.dense_weight,
                    "sparse_score": 0,
                    "sources": ["dense"]
                }
                
        # Sparse sonuçları ekle/birleştir
        for result in sparse_results:
            doc_id = result.get("metadata", {}).get("segment_id")
            if not doc_id:
                continue
                
            if doc_id in result_map:
                # Mevcut sonuca sparse skoru ekle
                result_map[doc_id]["sparse_score"] = result.get("score", 0) * self.sparse_weight
                result_map[doc_id]["sources"].append("sparse")
            else:
                # Yeni sparse sonucu
                result_map[doc_id] = {
                    "result": result,
                    "dense_score": 0,
                    "sparse_score": result.get("score", 0) * self.sparse_weight,
                    "sources": ["sparse"]
                }
                
        # Toplam skorları hesapla ve sonuçları birleştir
        merged_results = []
        
        for doc_id, data in result_map.items():
            result_copy = data["result"].copy()
            
            # Toplam skoru hesapla
            total_score = data["dense_score"] + data["sparse_score"]
            
            # Sonuca ek bilgiler ekle
            result_copy["score"] = total_score
            result_copy["retriever"] = "+".join(data["sources"])
            result_copy["dense_score"] = data["dense_score"] / self.dense_weight if "dense" in data["sources"] else 0
            result_copy["sparse_score"] = data["sparse_score"] / self.sparse_weight if "sparse" in data["sources"] else 0
            
            merged_results.append(result_copy)
            
        # Skora göre sırala
        merged_results.sort(key=lambda x: x["score"], reverse=True)
        
        return merged_results
    
    def _get_most_effective_retriever(self, results: List[Dict[str, Any]]) -> str:
        """Hangi retriever'ın daha etkili olduğunu belirle"""
        if not results:
            return "none"
            
        dense_count = 0
        sparse_count = 0
        hybrid_count = 0
        
        for result in results[:min(5, len(results))]:  # İlk 5 sonucu değerlendir
            retriever = result.get("retriever", "")
            
            if retriever == "dense":
                dense_count += 1
            elif retriever == "sparse":
                sparse_count += 1
            elif "+" in retriever:
                hybrid_count += 1
        
        # En çok hangi retriever'ın sonucu kullanıldı
        if hybrid_count > dense_count and hybrid_count > sparse_count:
            return "hybrid"
        elif dense_count > sparse_count:
            return "dense"
        elif sparse_count > dense_count:
            return "sparse"
        else:
            return "equal"