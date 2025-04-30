# Last reviewed: 2025-04-30 07:11:25 UTC (User: Teeksss)
from typing import List, Optional, Dict, Any
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete, func

from ..models.qa_pairs import QAPair

logger = logging.getLogger(__name__)

class QAPairsRepository:
    """QA çiftleri repository sınıfı"""
    
    async def create_qa_pair(self, db: AsyncSession, qa_pair: QAPair) -> QAPair:
        """
        Yeni bir QA çifti oluşturur
        
        Args:
            db: Veritabanı oturumu
            qa_pair: QA çifti nesnesi
            
        Returns:
            QAPair: Oluşturulan QA çifti
        """
        try:
            db.add(qa_pair)
            await db.commit()
            await db.refresh(qa_pair)
            return qa_pair
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating QA pair: {str(e)}")
            raise
    
    async def get_qa_pairs_by_document_id(self, db: AsyncSession, document_id: str) -> List[QAPair]:
        """
        Belgeye ait QA çiftlerini getirir
        
        Args:
            db: Veritabanı oturumu
            document_id: Belge ID'si
            
        Returns:
            List[QAPair]: QA çiftleri listesi
        """
        try:
            stmt = select(QAPair).filter(QAPair.document_id == document_id).order_by(QAPair.segment_index)
            result = await db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting QA pairs for document {document_id}: {str(e)}")
            return []
    
    async def get_qa_pair_by_id(self, db: AsyncSession, qa_pair_id: str) -> Optional[QAPair]:
        """
        ID'ye göre QA çifti getirir
        
        Args:
            db: Veritabanı oturumu
            qa_pair_id: QA çifti ID'si
            
        Returns:
            Optional[QAPair]: QA çifti veya None
        """
        try:
            stmt = select(QAPair).filter(QAPair.id == qa_pair_id)
            result = await db.execute(stmt)
            return result.scalars().first()
        except Exception as e:
            logger.error(f"Error getting QA pair {qa_pair_id}: {str(e)}")
            return None
    
    async def update_qa_pair(self, db: AsyncSession, qa_pair_id: str, **kwargs) -> Optional[QAPair]:
        """
        QA çiftini günceller
        
        Args:
            db: Veritabanı oturumu
            qa_pair_id: QA çifti ID'si
            **kwargs: Güncellenecek alanlar
            
        Returns:
            Optional[QAPair]: Güncellenen QA çifti veya None
        """
        try:
            stmt = update(QAPair).where(QAPair.id == qa_pair_id).values(**kwargs).returning(QAPair)
            result = await db.execute(stmt)
            await db.commit()
            return result.scalars().first()
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating QA pair {qa_pair_id}: {str(e)}")
            return None
    
    async def delete_qa_pair(self, db: AsyncSession, qa_pair_id: str) -> bool:
        """
        QA çiftini siler
        
        Args:
            db: Veritabanı oturumu
            qa_pair_id: QA çifti ID'si
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            stmt = delete(QAPair).where(QAPair.id == qa_pair_id)
            await db.execute(stmt)
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting QA pair {qa_pair_id}: {str(e)}")
            return False
    
    async def delete_qa_pairs_by_document_id(self, db: AsyncSession, document_id: str) -> int:
        """
        Belgeye ait tüm QA çiftlerini siler
        
        Args:
            db: Veritabanı oturumu
            document_id: Belge ID'si
            
        Returns:
            int: Silinen QA çifti sayısı
        """
        try:
            stmt = delete(QAPair).where(QAPair.document_id == document_id).returning(func.count())
            result = await db.execute(stmt)
            await db.commit()
            count = result.scalar()
            return count or 0
        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting QA pairs for document {document_id}: {str(e)}")
            return 0