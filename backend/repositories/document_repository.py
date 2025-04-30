# Last reviewed: 2025-04-30 05:56:23 UTC (User: Teeksss)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, and_, desc, func, text
from typing import List, Dict, Any, Optional, Tuple
import uuid
import hashlib
import os
from datetime import datetime, timezone

from ..models.document import Document
from ..models.user import User
from ..models.organization import Organization
from ..core.exceptions import NotFoundError, PermissionError, ErrorCode, ConflictError

class DocumentRepository:
    """Belge repository sınıfı"""
    
    async def create_document(
        self, 
        db: AsyncSession, 
        title: str,
        content: str,
        file_path: Optional[str] = None,
        file_name: Optional[str] = None,
        file_type: Optional[str] = None,
        file_size: Optional[int] = None,
        file_hash: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: str = None,
        organization_id: str = None
    ) -> Document:
        """Yeni bir belge oluşturur"""
        # Eğer file_hash sağlanmışsa, aynı hash'e sahip bir belge olup olmadığını kontrol et
        if file_hash:
            duplicate_doc = await self.get_document_by_hash(db, file_hash, organization_id)
            if duplicate_doc:
                raise ConflictError(
                    message="Duplicate document detected",
                    error_code=ErrorCode.RESOURCE_ALREADY_EXISTS,
                    detail=f"A document with the same content already exists: {duplicate_doc.title}"
                )
        
        # Belge nesnesi oluştur
        document = Document(
            title=title,
            content=content,
            file_path=file_path,
            file_name=file_name,
            file_type=file_type,
            file_size=file_size,
            file_hash=file_hash,
            metadata=metadata or {},
            user_id=user_id,
            organization_id=organization_id
        )
        
        db.add(document)
        await db.commit()
        await db.refresh(document)
        
        return document
    
    async def get_document_by_id(
        self, 
        db: AsyncSession, 
        document_id: str,
        check_owner: bool = False,
        user_id: Optional[str] = None
    ) -> Document:
        """ID'ye göre belge getirir"""
        stmt = select(Document).filter(Document.id == document_id)
        result = await db.execute(stmt)
        document = result.scalars().first()
        
        if not document:
            raise NotFoundError(
                message="Document not found",
                detail=f"Document with ID {document_id} not found"
            )
        
        # Eğer sahip kontrolü isteniyorsa ve kullanıcı belgenin sahibi değilse
        if check_owner and user_id and document.user_id != user_id:
            raise PermissionError(
                message="Permission denied",
                error_code=ErrorCode.INSUFFICIENT_PRIVILEGES,
                detail="You don't have permission to access this document"
            )
        
        return document
    
    async def get_document_by_hash(
        self,
        db: AsyncSession,
        file_hash: str,
        organization_id: Optional[str] = None
    ) -> Optional[Document]:
        """Hash'e göre belge getirir"""
        query = select(Document).filter(Document.file_hash == file_hash)
        
        # Organizasyona göre filtrele
        if organization_id:
            query = query.filter(Document.organization_id == organization_id)
        
        result = await db.execute(query)
        return result.scalars().first()
    
    async def update_document(
        self, 
        db: AsyncSession, 
        document_id: str, 
        title: Optional[str] = None,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        check_owner: bool = False,
        user_id: Optional[str] = None
    ) -> Document:
        """Belge günceller"""
        # Belgeyi getir
        document = await self.get_document_by_id(db, document_id, check_owner, user_id)
        
        # Güncellenecek alanları ayarla
        if title is not None:
            document.title = title
        
        if content is not None:
            document.content = content
        
        if metadata is not None:
            # Mevcut metadata'yı güncelle
            current_metadata = document.metadata or {}
            current_metadata.update(metadata)
            document.metadata = current_metadata
        
        # Güncelleme zamanını ayarla
        document.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        await db.refresh(document)
        
        return document
    
    async def delete_document(
        self, 
        db: AsyncSession, 
        document_id: str,
        check_owner: bool = False,
        user_id: Optional[str] = None,
        force: bool = False  # Süper kullanıcılar için zorunlu silme
    ) -> bool:
        """Belge siler"""
        # Belgeyi getir
        document = await self.get_document_by_id(db, document_id, check_owner and not force, user_id)
        
        # Fiziksel dosyayı sil
        if document.file_path and os.path.exists(document.file_path):
            os.remove(document.file_path)
        
        # Veritabanından belgeyi sil
        await db.delete(document)
        await db.commit()
        
        return True
    
    async def list_documents(
        self, 
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        search_term: Optional[str] = None,
        file_type: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """Belgeleri listeler"""
        # Ana sorgu
        query = select(Document)
        count_query = select(func.count(Document.id))
        
        # Filtreleri uygula
        if user_id:
            query = query.filter(Document.user_id == user_id)
            count_query = count_query.filter(Document.user_id == user_id)
            
        if organization_id:
            query = query.filter(Document.organization_id == organization_id)
            count_query = count_query.filter(Document.organization_id == organization_id)
            
        if search_term:
            search = f"%{search_term}%"
            query = query.filter(
                or_(
                    Document.title.ilike(search),
                    Document.content.ilike(search),
                    Document.file_name.ilike(search)
                )
            )
            count_query = count_query.filter(
                or_(
                    Document.title.ilike(search),
                    Document.content.ilike(search),
                    Document.file_name.ilike(search)
                )
            )
            
        if file_type:
            query = query.filter(Document.file_type == file_type)
            count_query = count_query.filter(Document.file_type == file_type)
        
        # Sıralama
        if sort_order.lower() == "asc":
            query = query.order_by(getattr(Document, sort_by))
        else:
            query = query.order_by(desc(getattr(Document, sort_by)))
            
        # Toplam belge sayısını al
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Sayfalama
        query = query.offset(skip).limit(limit)
        
        # Belgeleri getir
        result = await db.execute(query)
        documents = result.scalars().all()
        
        return {
            "total": total,
            "items": [doc for doc in documents],
            "page": skip // limit + 1 if limit > 0 else 1,
            "page_size": limit
        }
    
    async def calculate_file_hash(self, file_path: str) -> str:
        """Dosya hash'ini hesaplar (SHA-256)"""
        sha256_hash = hashlib.sha256()
        
        # Dosyayı bloklara ayırarak hash hesapla
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
                
        return sha256_hash.hexdigest()