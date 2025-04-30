# Last reviewed: 2025-04-30 06:57:19 UTC (User: Teeksss)
from typing import Dict, Any, List, Optional, Tuple
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from .multimodal_processor import MultimodalProcessor
from .vector_service import VectorService
from .query_processor import QueryProcessor
from .document_processor import DocumentProcessorService
from ..repositories.document_repository import DocumentRepository

logger = logging.getLogger(__name__)

class MultimodalRAG:
    """
    Multimodal RAG servisi.
    
    Belgelerdeki metin ve görsel içerikleri kullanarak sorguları yanıtlar.
    """
    
    def __init__(self):
        """Servis başlangıç ayarları"""
        self.multimodal_processor = MultimodalProcessor()
        self.vector_service = VectorService()
        self.query_processor = QueryProcessor()
        self.document_processor = DocumentProcessorService()
        self.document_repository = DocumentRepository()
    
    async def process_multimodal_query(self, 
                                     db: AsyncSession,
                                     query: str,
                                     document_ids: Optional[List[str]] = None,
                                     user_id: Optional[str] = None,
                                     organization_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Multimodal belgelerde sorgulama yapar
        
        Args:
            db: Veritabanı oturumu
            query: Kullanıcı sorgusu
            document_ids: Belirli belge ID'leri (filtreleme için)
            user_id: Kullanıcı ID
            organization_id: Organizasyon ID
            
        Returns:
            Dict[str, Any]: İşleme sonucu ve yanıt
        """
        try:
            start_time = datetime.now(timezone.utc)
            
            # Sorgu için belge bilgilerini getir
            documents = []
            if document_ids:
                for doc_id in document_ids:
                    doc = await self.document_repository.get_document_by_id(db, doc_id)
                    documents.append(doc)
            
            # Text-based RAG sürecini gerçekleştir
            text_rag_result = await self._perform_text_rag(
                db, query, document_ids, user_id, organization_id
            )
            
            # VLM tabanlı işleme - şu anda yalnızca belirli belge ID'leri belirtildiğinde
            multimodal_info = {}
            if document_ids:
                multimodal_info = await self._process_visual_content(
                    db, documents, query
                )
            
            # İşlem süresi
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            # Sonuçları birleştir
            result = {
                "query": query,
                "text_rag_result": text_rag_result,
                "multimodal_info": multimodal_info,
                "processing_time_ms": processing_time,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing multimodal query: {str(e)}")
            
            return {
                "query": query,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def _perform_text_rag(self, 
                             db: AsyncSession,
                             query: str,
                             document_ids: Optional[List[str]] = None,
                             user_id: Optional[str] = None,
                             organization_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Standart text-based RAG işlemini gerçekleştirir
        
        Args:
            db: Veritabanı oturumu
            query: Kullanıcı sorgusu
            document_ids: Belirli belge ID'leri (filtreleme için)
            user_id: Kullanıcı ID
            organization_id: Organizasyon ID
            
        Returns:
            Dict[str, Any]: RAG işlem sonucu
        """
        try:
            # Benzer belgeleri ara
            filters = {}
            
            # Belirli belgelerle sınırla
            if document_ids:
                filters["document_id"] = document_ids
            
            search_results = await self.vector_service.search(
                query_text=query,
                limit=10,
                organization_id=organization_id,
                filters=filters
            )
            
            # LLM yanıtı oluştur
            answer, tokens_info = await self.query_processor.generate_answer(
                query=query,
                search_results=search_results
            )
            
            return {
                "answer": answer,
                "sources": search_results,
                "tokens": tokens_info
            }
            
        except Exception as e:
            logger.error(f"Error in text RAG: {str(e)}")
            
            return {
                "error": str(e)
            }
    
    async def _process_visual_content(self, 
                                   db: AsyncSession,
                                   documents: List[Any],
                                   query: str) -> Dict[str, Any]:
        """
        Belgelerdeki görsel içeriği işler
        
        Args:
            db: Veritabanı oturumu
            documents: Belge nesneleri listesi
            query: Kullanıcı sorgusu
            
        Returns:
            Dict[str, Any]: İşleme sonuçları
        """
        try:
            visual_results = {}
            
            # Her belge için görsel içeriği işle
            for doc in documents:
                # Sadece PDF belgelerini işle (şimdilik)
                if doc.file_type == 'pdf':
                    doc_result = await self.multimodal_processor.process_document_images(
                        document_id=str(doc.id),
                        document_path=doc.file_path,
                        query=query
                    )
                    
                    # Sonuçları kaydet
                    visual_results[str(doc.id)] = {
                        "document_title": doc.title,
                        "file_type": doc.file_type,
                        "processing_result": doc_result
                    }
            
            return {
                "visual_content": visual_results,
                "processed_documents": len(visual_results)
            }
            
        except Exception as e:
            logger.error(f"Error processing visual content: {str(e)}")
            
            return {
                "error": str(e)
            }