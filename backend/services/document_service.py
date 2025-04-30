# Last reviewed: 2025-04-30 05:49:14 UTC (User: Teeksss)
import os
import io
import hashlib
from typing import Dict, List, Any, Optional, BinaryIO, Union
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
import logging
import uuid
from datetime import datetime, timezone

from ..models.document import Document, DocumentChunk
from ..services.document_chunking import SmartDocumentChunker
from ..repositories.document_repository import DocumentRepository
from ..core.config import settings
from ..core.exceptions import NotFoundError, ValidationError, ConflictError, FileError, ErrorCode

logger = logging.getLogger(__name__)

class DocumentService:
    """Belge işlemleri servisi"""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize document service
        
        Args:
            db: Veritabanı oturumu
        """
        self.db = db
        self.document_repository = DocumentRepository()
        self.document_chunker = SmartDocumentChunker()
        self.storage_path = settings.DOCUMENT_STORAGE_PATH
        
        # Depolama dizinini oluştur
        os.makedirs(self.storage_path, exist_ok=True)
    
    async def upload_document(
        self, 
        file: UploadFile,
        title: str,
        description: Optional[str] = None,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        is_public: bool = False,
        shared_with_organization: bool = True,
        apply_ocr: bool = False,
        ocr_language: Optional[str] = None,
        check_duplicates: bool = True
    ) -> Document:
        """
        Yeni bir belge yükle
        
        Args:
            file: Yüklenecek dosya
            title: Belge başlığı
            description: Belge açıklaması (opsiyonel)
            user_id: Belgeyi yükleyen kullanıcı ID (opsiyonel)
            organization_id: Belgenin ait olduğu organizasyon ID (opsiyonel)
            metadata: Ek metadata (opsiyonel)
            tags: Etiketler (opsiyonel)
            is_public: Herkese açık mı (default: False)
            shared_with_organization: Organizasyon içinde paylaşımlı mı (default: True)
            apply_ocr: OCR uygulansın mı (default: False)
            ocr_language: OCR dili (opsiyonel)
            check_duplicates: Yinelenen dosya kontrolü yapsın mı (default: True)
            
        Returns:
            Document: Yüklenen belge
            
        Raises:
            FileError: Dosya işleme hatası
            ValidationError: Doğrulama hatası
            ConflictError: Yinelenen dosya hatası
        """
        try:
            # Dosya türünü belirle
            file_type = file.content_type or os.path.splitext(file.filename)[1].lstrip('.')
            
            # Dosya boyutunu al
            # FastAPI'nin upload_file nesnesi bir konum içerir, ama doğrudan boyutu yoktur
            file_content = await file.read()
            file_size = len(file_content)
            
            # Dosyayı başa sar (okuma sonrası)
            await file.seek(0)
            
            # Dosya hash'ini hesapla
            file_hash = hashlib.sha256(file_content).hexdigest()
            
            # Yinelenen dosya kontrolü
            if check_duplicates:
                duplicate = await self._check_duplicate_file(file_hash, organization_id)
                if duplicate:
                    raise ConflictError(
                        message="Duplicate document detected",
                        error_code=ErrorCode.RESOURCE_ALREADY_EXISTS,
                        detail=f"This file has already been uploaded as '{duplicate.title}'"
                    )
            
            # Dosyayı kaydet
            unique_filename = f"{str(uuid.uuid4())}{os.path.splitext(file.filename)[1]}"
            file_path = os.path.join(self.storage_path, unique_filename)
            
            # Dosyayı disk'e kaydet
            with open(file_path, "wb") as buffer:
                buffer.write(file_content)
            
            # Belge nesnesini oluştur
            document = Document(
                title=title,
                description=description,
                source_type="upload",
                file_type=file_type,
                file_path=file_path,
                file_size=file_size,
                file_hash=file_hash,
                user_id=user_id,
                organization_id=organization_id,
                metadata=metadata,
                tags=tags,
                is_public=is_public,
                shared_with_organization=shared_with_organization,
                ocr_applied=False  # OCR işlemi henüz uygulanmadı
            )
            
            self.db.add(document)
            await self.db.flush()  # ID almak için flush
            
            # Belge içeriğini analiz et ve parçalara ayır
            file_content_io = io.BytesIO(file_content)
            file_content_str = await self._extract_text_from_file(
                file_content_io, 
                file_type, 
                apply_ocr=apply_ocr, 
                ocr_language=ocr_language
            )
            
            # Belgeyi parçalara ayır
            chunks = self.document_chunker.split_document(
                content=file_content_str,
                file_extension=file_type,
                metadata={"document_id": str(document.id), "title": title}
            )
            
            # OCR uygulandıysa güncelle
            if apply_ocr:
                document.ocr_applied = True
                document.ocr_language = ocr_language or "auto"
            
            # Belge parçalarını oluştur
            total_tokens = 0
            for i, chunk in enumerate(chunks):
                chunk_content = chunk["content"]
                chunk_metadata = chunk.get("metadata", {})
                
                # Token sayısını hesapla (basit yaklaşım)
                tokens_count = len(chunk_content.split())
                total_tokens += tokens_count
                
                # Parça nesnesini oluştur
                document_chunk = DocumentChunk(
                    document_id=document.id,
                    chunk_index=i,
                    content=chunk_content,
                    metadata=chunk_metadata,
                    tokens_count=tokens_count
                )
                
                self.db.add(document_chunk)
            
            # Belge bilgilerini güncelle
            document.chunks_count = len(chunks)
            document.total_tokens = total_tokens
            document.indexed = True
            document.indexed_at = datetime.now(timezone.utc)
            
            # Veritabanına kaydet
            await self.db.commit()
            await self.db.refresh(document)
            
            return document
            
        except ConflictError:
            await self.db.rollback()
            raise
            
        except ValidationError:
            await self.db.rollback()
            raise
            
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Database integrity error during document upload: {str(e)}")
            
            # Duplicate key hatası kontrolü
            if "duplicate key" in str(e).lower() and "file_hash" in str(e).lower():
                raise ConflictError(
                    message="Duplicate document detected",
                    error_code=ErrorCode.RESOURCE_ALREADY_EXISTS,
                    detail="This file has already been uploaded"
                )
            
            raise FileError(
                message="Failed to save document",
                error_code=ErrorCode.FILE_UPLOAD_ERROR,
                detail=f"Database error: {str(e)}"
            )
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error uploading document: {str(e)}")
            
            # Kaydedilmiş dosyayı temizle
            if 'file_path' in locals() and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
            
            raise FileError(
                message="Failed to process document",
                error_code=ErrorCode.FILE_UPLOAD_ERROR,
                detail=str(e)
            )
    
    async def _check_duplicate_file(
        self, file_hash: str, organization_id: Optional[str] = None
    ) -> Optional[Document]:
        """
        Yinelenen dosyaları kontrol et
        
        Args:
            file_hash: Dosya hash'i
            organization_id: Organizasyon ID
            
        Returns:
            Optional[Document]: Yinelenen belge ve