# Last reviewed: 2025-04-30 07:34:44 UTC (User: Teeksss)
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete, and_

from ..models.document_version import DocumentVersion

logger = logging.getLogger(__name__)

class DocumentVersionRepository:
    """Belge versiyonu repository sınıfı"""
    
    async def create_document_version(self, db: AsyncSession, document_version: DocumentVersion) -> DocumentVersion:
        """
        Yeni bir belge versiyonu oluşturur
        
        Args:
            db: Veritabanı oturumu
            document_version: Belge versiyonu nesnesi
            
        Returns:
            DocumentVersion: Oluşturulan belge versiyonu
        """
        try:
            db.add(document_version)
            await db.flush()
            await db.commit()
            await db.refresh(document_version)
            return document_version
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating document version: {str(e)}")
            raise
    
    async def get_document_versions(self, db: AsyncSession, document_id: str) -> List[DocumentVersion]:
        """
        Belgeye ait tüm versiyonları getirir
        
        Args:
            db: Veritabanı oturumu
            document_id: Belge ID'si
            
        Returns:
            List[DocumentVersion]: Belge versiyonları listesi
        """
        try:
            stmt = select(DocumentVersion).where(DocumentVersion.document_id == document_id).order_by(DocumentVersion.version_number.desc())
            result = await db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting document versions: {str(e)}")
            return []
    
    async def get_document_version(self, db: AsyncSession, document_id: str, version_number: int) -> Optional[DocumentVersion]:
        """
        Belirli bir belge versiyonunu getirir
        
        Args:
            db: Veritabanı oturumu
            document_id: Belge ID'si
            version_number: Versiyon numarası
            
        Returns:
            Optional[DocumentVersion]: Belge versiyonu veya None
        """
        try:
            stmt = select(DocumentVersion).where(
                and_(
                    DocumentVersion.document_id == document_id,
                    DocumentVersion.version_number == version_number
                )
            )
            result = await db.execute(stmt)
            return result.scalars().first()
        except Exception as e:
            logger.error(f"Error getting document version: {str(e)}")
            return None
    
    async def delete_document_versions(self, db: AsyncSession, document_id: str) -> int:
        """
        Belgeye ait tüm versiyonları siler
        
        Args:
            db: Veritabanı oturumu
            document_id: Belge ID'si
            
        Returns:
            int: Silinen versiyon sayısı
        """
        try:
            stmt = delete(DocumentVersion).where(DocumentVersion.document_id == document_id)
            result = await db.execute(stmt)
            await db.commit()
            return result.rowcount
        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting document versions: {str(e)}")
            return 0