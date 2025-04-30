# Last reviewed: 2025-04-30 06:25:07 UTC (User: Teeksss)
from typing import List, Dict, Any, Optional, Union
import os
import asyncio
import logging
import uuid
from datetime import datetime, timezone
import json
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchRequest,
    SearchResult
)

logger = logging.getLogger(__name__)

class QdrantAdapter:
    """Qdrant vektör veritabanı adaptörü."""
    
    def __init__(self):
        """Qdrant bağlantısını ve koleksiyonları başlatır"""
        self.qdrant_host = os.environ.get("QDRANT_HOST", "localhost")
        self.qdrant_port = int(os.environ.get("QDRANT_PORT", "6333"))
        self.collection_name = os.environ.get("QDRANT_COLLECTION", "rag_segments")
        self.vector_size = int(os.environ.get("VECTOR_SIZE", "1536"))  # OpenAI ada değeri
        self.client = self._initialize_client()
        
    def _initialize_client(self) -> Optional[QdrantClient]:
        """QdrantClient'ı başlatır"""
        try:
            client = QdrantClient(
                host=self.qdrant_host,
                port=self.qdrant_port
            )
            
            # Koleksiyonun varlığını kontrol et
            collections = client.get_collections().collections
            collection_exists = any(c.name == self.collection_name for c in collections)
            
            if not collection_exists:
                # Koleksiyon yoksa oluştur
                client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
                
            return client
            
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant client: {str(e)}")
            return None
    
    async def upsert_vectors(self, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Belge segmentlerini Qdrant'a ekler
        
        Args:
            segments: Segment vektörleri ve metadata'ları
            
        Returns:
            Dict[str, Any]: Ekleme sonucu
        """
        if not self.client:
            return {"success": False, "error": "Qdrant client not available"}
            
        try:
            # Qdrant'a eklenecek noktaları hazırla
            points = []
            
            for segment in segments:
                segment_id = segment["id"]
                vector = segment["vector"]
                payload = {
                    "document_id": segment["document_id"],
                    "content": segment["content"][:10000],  # Maksimum karakter sınırı
                    "metadata": segment["metadata"]
                }
                
                # Point yapısı oluştur
                points.append(PointStruct(
                    id=segment_id,
                    vector=vector,
                    payload=payload
                ))
                
            # Toplu ekleme yap
            if points:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, 
                    lambda: self.client.upsert(
                        collection_name=self.collection_name,
                        points=points
                    )
                )
                
            return {
                "success": True,
                "segments_count": len(points),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error upserting vectors to Qdrant: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def search_vectors(self, 
                          query_vector: List[float], 
                          limit: int = 10,
                          filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Qdrant'ta vektör araması yapar
        
        Args:
            query_vector: Sorgu vektörü
            limit: Maksimum sonuç sayısı
            filters: Metadata filtreleri
            
        Returns:
            List[Dict[str, Any]]: Arama sonuçları
        """
        if not self.client or not query_vector:
            return []
            
        try:
            # Filtreleri dönüştür
            qdrant_filter = None
            if filters:
                filter_conditions = []
                
                for key, value in filters.items():
                    if key == "organization_id" and value:
                        filter_conditions.append(
                            FieldCondition(
                                key="metadata.organization_id",
                                match=MatchValue(value=value)
                            )
                        )
                    # Diğer özel filtreler eklenebilir
                
                if filter_conditions:
                    qdrant_filter = Filter(
                        must=filter_conditions
                    )
            
            # Arama yap
            loop = asyncio.get_event_loop()
            search_results = await loop.run_in_executor(
                None, 
                lambda: self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=limit,
                    query_filter=qdrant_filter,
                    with_payload=True
                )
            )
            
            # Sonuçları dönüştür
            results = []
            
            for result in search_results:
                score = result.score
                payload = result.payload
                
                document_id = payload.get("document_id", "")
                content = payload.get("content", "")
                metadata = payload.get("metadata", {})
                
                # Sonuç objesini oluştur
                results.append({
                    "document_id": document_id,
                    "content": content,
                    "score": score,
                    "metadata": metadata
                })
                
            return results
            
        except Exception as e:
            logger.error(f"Error searching vectors in Qdrant: {str(e)}")
            return []
    
    async def delete_vectors(self, segment_ids: List[str]) -> Dict[str, Any]:
        """
        Belge segmentlerini siler
        
        Args:
            segment_ids: Silinecek segment ID'leri
            
        Returns:
            Dict[str, Any]: Silme sonucu
        """
        if not self.client:
            return {"success": False, "error": "Qdrant client not available"}
            
        try:
            # Segmentleri sil
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, 
                lambda: self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=segment_ids
                )
            )
            
            return {
                "success": True,
                "deleted_count": len(segment_ids)
            }
            
        except Exception as e:
            logger.error(f"Error deleting vectors from Qdrant: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def delete_document_vectors(self, document_id: str) -> Dict[str, Any]:
        """
        Belgeye ait tüm vektörleri siler
        
        Args:
            document_id: Belge ID'si
            
        Returns:
            Dict[str, Any]: Silme sonucu
        """
        if not self.client:
            return {"success": False, "error": "Qdrant client not available"}
            
        try:
            # Belgeye ait tüm segmentleri sil
            document_filter = Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id)
                    )
                ]
            )
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                lambda: self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=document_filter
                )
            )
            
            return {
                "success": True,
                "document_id": document_id,
                "deleted_count": result.status.get("deleted", 0)
            }
            
        except Exception as e:
            logger.error(f"Error deleting document vectors from Qdrant: {str(e)}")
            return {"success": False, "error": str(e)}