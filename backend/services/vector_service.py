# Last reviewed: 2025-04-30 06:23:58 UTC (User: Teeksss)
from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np
from numpy.linalg import norm
import json
import logging
from datetime import datetime, timezone
import asyncio
import os

logger = logging.getLogger(__name__)

class VectorService:
    """
    Vektör veri tabanı hizmet sınıfı.
    Belge segmentlerinin vektörlerini oluşturur, kaydeder ve sorgular.
    """
    
    def __init__(self, 
                vector_db_type: str = os.environ.get('VECTOR_DB_TYPE', 'qdrant'),
                min_similarity_score: float = 0.7):
        """
        Args:
            vector_db_type: Kullanılacak vektör veritabanı türü ('qdrant', 'weaviate', 'pinecone', 'pgvector')
            min_similarity_score: Minimum benzerlik skoru (filtreleme için)
        """
        self.vector_db_type = vector_db_type
        self.min_similarity_score = min_similarity_score
        self.embedding_model = os.environ.get('EMBEDDING_MODEL', 'text-embedding-ada-002')
        self.vector_db = self._initialize_vector_db(vector_db_type)
        
    def _initialize_vector_db(self, db_type: str) -> Any:
        """Belirtilen vektör veritabanı adaptörünü başlatır"""
        try:
            if db_type == 'qdrant':
                from .vector_dbs.qdrant_adapter import QdrantAdapter
                return QdrantAdapter()
            elif db_type == 'weaviate':
                from .vector_dbs.weaviate_adapter import WeaviateAdapter
                return WeaviateAdapter()
            elif db_type == 'pinecone':
                from .vector_dbs.pinecone_adapter import PineconeAdapter
                return PineconeAdapter()
            elif db_type == 'pgvector':
                from .vector_dbs.pgvector_adapter import PGVectorAdapter
                return PGVectorAdapter()
            else:
                logger.warning(f"Unsupported vector DB type: {db_type}, falling back to Qdrant")
                from .vector_dbs.qdrant_adapter import QdrantAdapter
                return QdrantAdapter()
        except Exception as e:
            logger.error(f"Error initializing vector DB: {str(e)}")
            # In-memory fallback
            return None
    
    async def save_document_segments(self, document_id: str, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Belge segmentlerini vektör veritabanına kaydeder
        
        Args:
            document_id: Belge ID'si
            segments: Segment içerikleri ve metadata
            
        Returns:
            Dict[str, Any]: Kayıt sonucu
        """
        if not segments:
            return {"success": False, "error": "No segments to save"}
            
        try:
            segment_vectors = []
            
            # Her segment için vektör oluştur
            for segment in segments:
                segment_text = segment["content"]
                segment_metadata = segment["metadata"]
                
                # Embeddings oluştur
                vector = await self._create_embedding(segment_text)
                
                if vector is not None:
                    # Vektör ve metadata'yı birlikte sakla
                    segment_vectors.append({
                        "id": segment_metadata["segment_id"],
                        "vector": vector,
                        "metadata": segment_metadata,
                        "content": segment_text,
                        "document_id": document_id
                    })
            
            # Vektör veritabanına toplu olarak kaydet
            if segment_vectors:
                result = await self.vector_db.upsert_vectors(segment_vectors)
                
                return {
                    "success": True,
                    "document_id": document_id,
                    "segments_count": len(segment_vectors),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            else:
                return {"success": False, "error": "Failed to create embeddings"}
                
        except Exception as e:
            logger.error(f"Error saving document segments: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def search(self, 
                   query_text: str,
                   limit: int = 10,
                   organization_id: Optional[str] = None,
                   filters: Optional[Dict[str, Any]] = None,
                   min_score: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Belge segmentleri içinde benzerlik araması yapar
        
        Args:
            query_text: Arama sorgusu
            limit: Maksimum sonuç sayısı
            organization_id: Belirli bir organizasyona filtre uygula
            filters: Ek metadata filtreleri
            min_score: Minimum benzerlik skoru (varsayılandan farklı)
            
        Returns:
            List[Dict[str, Any]]: Benzer segment sonuçları ve skorları
        """
        if not query_text:
            return []
            
        try:
            # Sorgu vektörü oluştur
            query_vector = await self._create_embedding(query_text)
            
            if query_vector is None:
                return []
                
            # Filtreleri ayarla
            query_filters = filters or {}
            if organization_id:
                query_filters["organization_id"] = organization_id
            
            # Minimum skoru ayarla
            filter_score = min_score if min_score is not None else self.min_similarity_score
            
            # Vektör veritabanında benzerlik arama
            raw_results = await self.vector_db.search_vectors(
                query_vector=query_vector,
                limit=limit * 2,  # Filtreleme sonrası istenen sayıya ulaşabilmek için daha fazla sonuç al
                filters=query_filters
            )
            
            # Sonuçları skora göre filtrele ve sırala
            filtered_results = [
                result for result in raw_results
                if result["score"] >= filter_score
            ]
            
            # En iyi sonuçları al
            top_results = filtered_results[:limit] if len(filtered_results) > limit else filtered_results
            
            # Debug info
            logger.debug(f"Search: found {len(raw_results)} raw results, {len(filtered_results)} filtered results, returning top {len(top_results)}")
            
            # Sonuçları zenginleştir
            enriched_results = []
            for result in top_results:
                # Orijinal sonuç verilerini koru
                enriched_result = {
                    "document_id": result.get("document_id", ""),
                    "content": result.get("content", ""),
                    "score": result.get("score", 0.0),
                    "metadata": result.get("metadata", {})
                }
                
                # Formatlı benzerlik skoru ekle
                score = result.get("score", 0)
                enriched_result["similarity_percentage"] = round(score * 100, 1)
                
                # Önce içeriği kısalt ve sonucu ekle
                content = result.get("content", "")
                if content:
                    preview_length = 200  # Karakter
                    enriched_result["content_snippet"] = (
                        content[:preview_length] + "..." 
                        if len(content) > preview_length else content
                    )
                
                enriched_results.append(enriched_result)
                
            return enriched_results
            
        except Exception as e:
            logger.error(f"Error searching vectors: {str(e)}")
            return []
    
    async def _create_embedding(self, text: str) -> Optional[List[float]]:
        """Metinden embedding vektörü oluşturur"""
        if not text:
            return None
            
        try:
            # OpenAI embeddings (üretim ortamı)
            from openai import AsyncOpenAI
            
            client = AsyncOpenAI()
            
            response = await client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            
            # Vektörü döndür
            if response and response.data and len(response.data) > 0:
                return response.data[0].embedding
            return None
                
        except ImportError:
            logger.warning("OpenAI not available. Using fallback embedding method.")
            # Basit fallback: sentence-transformers kullan
            try:
                from sentence_transformers import SentenceTransformer
                
                model = SentenceTransformer('all-MiniLM-L6-v2')
                embedding = model.encode(text)
                
                return embedding.tolist()
                
            except ImportError:
                logger.warning("SentenceTransformer not available. Using mock embeddings.")
                # Test/geliştirme için mock embeddings
                import random
                mock_vector = [random.uniform(-1, 1) for _ in range(384)]  # 384 boyutlu mock
                return mock_vector
                
        except Exception as e:
            logger.error(f"Error creating embedding: {str(e)}")
            return None