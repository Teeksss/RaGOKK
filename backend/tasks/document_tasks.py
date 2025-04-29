# Last reviewed: 2025-04-29 12:35:57 UTC (User: TeeksssVisual Diff)
from celery import shared_task, Task
import logging
import os
import json
import time
from typing import Dict, Any, Optional, List, Union
import traceback
from datetime import datetime, timedelta

from ..db.session import SessionLocal, engine
from ..repositories.document_repository import DocumentRepository
from ..services.document_processor import DocumentProcessor
from ..services.vector_service import VectorService
from ..utils.security_scanner import SecurityScanner

logger = logging.getLogger(__name__)

class BaseTask(Task):
    """Hata işleme ile temel görev sınıfı"""
    
    _document_repository = None
    _document_processor = None
    _vector_service = None
    _security_scanner = None
    
    @property
    def document_repository(self) -> DocumentRepository:
        if self._document_repository is None:
            self._document_repository = DocumentRepository()
        return self._document_repository
    
    @property
    def document_processor(self) -> DocumentProcessor:
        if self._document_processor is None:
            self._document_processor = DocumentProcessor()
        return self._document_processor
    
    @property
    def vector_service(self) -> VectorService:
        if self._vector_service is None:
            self._vector_service = VectorService()
        return self._vector_service
    
    @property
    def security_scanner(self) -> SecurityScanner:
        if self._security_scanner is None:
            self._security_scanner = SecurityScanner()
        return self._security_scanner
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Görev başarısız olduğunda çağrılır"""
        logger.error(f"Task {task_id} failed: {exc}")
        
        # Argümanlardan doküman ID'sini kontrol et
        document_id = None
        if 'document_id' in kwargs:
            document_id = kwargs['document_id']
        elif args and len(args) > 0 and isinstance(args[0], int):
            document_id = args[0]
        
        if document_id:
            try:
                # Dokümanın durumunu güncelle
                with SessionLocal() as db:
                    self.document_repository.update_document_status(
                        db=db, 
                        document_id=document_id, 
                        status="error", 
                        error_message=str(exc)
                    )
                    db.commit()
            except Exception as e:
                logger.error(f"Failed to update document status: {e}")
        
        super().on_failure(exc, task_id, args, kwargs, einfo)

@shared_task(bind=True, base=BaseTask, name="backend.tasks.document_tasks.process_uploaded_document")
def process_uploaded_document(self, document_id: int, file_path: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Yüklenen dokümanı işler
    
    Args:
        document_id: Doküman ID
        file_path: Dosya yolu
        options: İşleme seçenekleri
        
    Returns:
        Dict: İşleme sonuçları
    """
    logger.info(f"Processing document {document_id}, file: {file_path}")
    
    options = options or {}
    start_time = time.time()
    result = {
        "document_id": document_id,
        "success": False,
        "processing_time": 0,
        "metadata": {}
    }
    
    try:
        # Veritabanı oturumu
        with SessionLocal() as db:
            # Dokümanı getir
            document = self.document_repository.get_document_by_id(db, document_id)
            
            if not document:
                raise ValueError(f"Document {document_id} not found")
            
            # Doküman işleme durumunu güncelle
            self.document_repository.update_document_status(db, document_id, "processing")
            db.commit()
            
            # Dosyayı oku
            with open(file_path, "rb") as f:
                file_content = f.read()
            
            # Güvenlik taraması
            if options.get("scan_security", True):
                scan_result = self.security_scanner.scan_file(file_content, os.path.basename(file_path))
                
                if scan_result.status != "clean":
                    error_message = f"Security scan failed: {scan_result.status} - {scan_result.details.get('reason')}"
                    logger.warning(error_message)
                    
                    # Doküman durumunu güncelle
                    self.document_repository.update_document_status(
                        db, document_id, "error", error_message=error_message
                    )
                    db.commit()
                    
                    result["error"] = error_message
                    return result
            
            # Dokümanı işle
            processing_result = self.document_processor.process_document(file_path)
            
            # İçeriği ve metadatayı çıkar
            content = processing_result.get("content", "")
            metadata = processing_result.get("metadata", {})
            
            # Dokümanı güncelle
            self.document_repository.update_document(
                db=db,
                document_id=document_id,
                content=content,
                metadata=json.dumps(metadata),
                is_processed=True
            )
            
            # Doküman işleme durumunu güncelle
            self.document_repository.update_document_status(db, document_id, "processed")
            db.commit()
            
            # Embedding'leri oluştur (asenkron, bunu beklemeyiz)
            if options.get("generate_embeddings", True):
                generate_document_embeddings.delay(document_id)
            
            # Sonucu hazırla
            processing_time = time.time() - start_time
            result.update({
                "success": True,
                "processing_time": processing_time,
                "metadata": metadata,
                "content_length": len(content),
                "word_count": metadata.get("word_count", 0),
                "language": metadata.get("language", "unknown")
            })
            
            logger.info(f"Document {document_id} processed successfully in {processing_time:.2f} seconds")
            return result
            
    except Exception as e:
        error_message = f"Error processing document {document_id}: {str(e)}"
        logger.error(error_message)
        logger.error(traceback.format_exc())
        
        try:
            with SessionLocal() as db:
                self.document_repository.update_document_status(
                    db, document_id, "error", error_message=error_message
                )
                db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update document status: {db_error}")
        
        result["error"] = str(e)
        result["processing_time"] = time.time() - start_time
        return result

@shared_task(bind=True, base=BaseTask, name="backend.tasks.document_tasks.generate_document_embeddings")
def generate_document_embeddings(self, document_id: int, force: bool = False) -> Dict[str, Any]:
    """
    Doküman için embedding vektörleri oluşturur
    
    Args:
        document_id: Doküman ID
        force: Mevcut embedding'leri yeniden oluştur
        
    Returns:
        Dict: İşlem sonuçları
    """
    logger.info(f"Generating embeddings for document {document_id}")
    start_time = time.time()
    result = {
        "document_id": document_id,
        "success": False,
    }
    
    try:
        # Veritabanı oturumu
        with SessionLocal() as db:
            # Dokümanı getir
            document = self.document_repository.get_document_by_id(db, document_id)
            
            if not document:
                raise ValueError(f"Document {document_id} not found")
            
            if not document.content:
                raise ValueError(f"Document {document_id} has no content")
            
            # Metadata'yı parse et
            try:
                metadata = json.loads(document.metadata) if document.metadata else {}
            except:
                metadata = {}
            
            # Doküman durumunu güncelle
            self.document_repository.update_document_status(db, document_id, "generating_embeddings")
            db.commit()
            
            # Embedding'leri oluştur
            chunks = self.document_processor.chunk_document(document.content, metadata)
            chunk_count = len(chunks)
            
            # Vektörleri oluştur ve vektör veritabanına kaydet
            vectors = []
            for i, chunk in enumerate(chunks):
                # İlerleme durumunu güncelle
                if i % 20 == 0 or i == chunk_count - 1:
                    progress = (i + 1) / chunk_count * 100
                    self.document_repository.update_document_status(
                        db, 
                        document_id, 
                        "generating_embeddings", 
                        progress=progress
                    )
                    db.commit()
                
                # Vektör oluştur
                chunk_text = chunk.get("text", "")
                chunk_metadata = chunk.get("metadata", {})
                chunk_metadata["document_id"] = document_id
                
                # Vektörü hesapla
                embedding = self.vector_service.create_embedding(chunk_text)
                
                # Vektör veritabanına kaydet
                self.vector_service.store_vector(
                    embedding=embedding,
                    text=chunk_text,
                    metadata=chunk_metadata
                )
                
                vectors.append({
                    "text": chunk_text[:100] + "..." if len(chunk_text) > 100 else chunk_text,
                    "metadata": chunk_metadata
                })
            
            # Doküman durumunu güncelle
            self.document_repository.update_document_status(db, document_id, "indexed")
            
            # Embedding sayısını metadata'ya ekle
            metadata["embedding_count"] = chunk_count
            metadata["last_embedded"] = datetime.utcnow().isoformat()
            
            # Dokümanı güncelle
            self.document_repository.update_document(
                db=db,
                document_id=document_id,
                metadata=json.dumps(metadata)
            )
            db.commit()
            
            # Sonucu hazırla
            processing_time = time.time() - start_time
            result.update({
                "success": True,
                "processing_time": processing_time,
                "chunk_count": chunk_count,
                "vector_dim": self.vector_service.embedding_dimension
            })
            
            logger.info(f"Generated {chunk_count} embeddings for document {document_id}")
            return result
            
    except Exception as e:
        error_message = f"Error generating embeddings for document {document_id}: {str(e)}"
        logger.error(error_message)
        logger.error(traceback.format_exc())
        
        try:
            with SessionLocal() as db:
                self.document_repository.update_document_status(
                    db, document_id, "embedding_error", error_message=error_message
                )
                db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update document status: {db_error}")
        
        result["error"] = str(e)
        return result

@shared_task(bind=True, base=BaseTask, name="backend.tasks.document_tasks.batch_process_documents")
def batch_process_documents(self, document_ids: List[int], options: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Çoklu dokümanları işler
    
    Args:
        document_ids: Doküman ID'leri listesi
        options: İşleme seçenekleri
        
    Returns:
        Dict: İşlem sonuçları
    """
    logger.info(f"Batch processing {len(document_ids)} documents")
    start_time = time.time()
    options = options or {}
    
    results = {
        "total": len(document_ids),
        "successful": 0,
        "failed": 0,
        "skipped": 0,
        "document_results": []
    }
    
    for document_id in document_ids:
        try:
            with SessionLocal() as db:
                document = self.document_repository.get_document_by_id(db, document_id)
                
                if not document:
                    logger.warning(f"Document {document_id} not found, skipping")
                    results["skipped"] += 1
                    continue
                
                # Doküman zaten işlendiyse atla (force değilse)
                if document.is_processed and not options.get("force", False):
                    logger.info(f"Document {document_id} already processed, skipping")
                    results["skipped"] += 1
                    continue
                
                # Yeni bir görev planla (asenkron çalıştır)
                file_path = document.metadata.get("file_path") if document.metadata else None
                if not file_path:
                    logger.warning(f"Document {document_id} has no file path, skipping")
                    results["skipped"] += 1
                    continue
                
                # Görevi planla
                process_uploaded_document.delay(document_id, file_path, options)
                results["successful"] += 1
                
        except Exception as e:
            logger.error(f"Error scheduling document {document_id}: {e}")
            results["failed"] += 1
            results["document_results"].append({
                "document_id": document_id,
                "status": "error",
                "error": str(e)
            })
    
    results["processing_time"] = time.time() - start_time
    return results