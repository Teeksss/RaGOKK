# Last reviewed: 2025-04-30 06:34:07 UTC (User: Teeksss)
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models.feedback import RAGFeedback
from ..schemas.feedback import FeedbackCreate, FeedbackResponse

logger = logging.getLogger(__name__)

class RAGFeedbackService:
    """
    RAG Feedback Logging servisi.
    
    Sorguların ve yanıtların kalitesini izlemek ve analiz etmek için kullanıcı geri bildirimlerini kaydeder.
    """
    
    async def log_feedback(
        self,
        db: AsyncSession,
        query_id: str,
        user_id: Optional[str],
        rating: int,
        feedback_text: Optional[str] = None,
        feedback_type: str = "answer_quality",
        query_data: Optional[Dict[str, Any]] = None
    ) -> RAGFeedback:
        """
        Kullanıcı geri bildirimini kaydeder
        
        Args:
            db: Veritabanı oturumu
            query_id: Sorgu ID'si
            user_id: Kullanıcı ID'si
            rating: Derecelendirme (1-5)
            feedback_text: Geri bildirim metni (opsiyonel)
            feedback_type: Geri bildirim türü
            query_data: Sorgu ile ilgili ek veriler
            
        Returns:
            RAGFeedback: Kaydedilen geri bildirim
        """
        try:
            # Geri bildirim nesnesi oluştur
            feedback = RAGFeedback(
                id=str(uuid.uuid4()),
                query_id=query_id,
                user_id=user_id,
                rating=rating,
                feedback=feedback_text,
                feedback_type=feedback_type,
                metadata=query_data or {},
                created_at=datetime.now(timezone.utc)
            )
            
            # Veritabanına kaydet
            db.add(feedback)
            await db.commit()
            await db.refresh(feedback)
            
            # Geri bildirim analitiği ekle
            await self._analyze_feedback(db, feedback)
            
            return feedback
            
        except Exception as e:
            logger.error(f"Error logging feedback: {str(e)}")
            await db.rollback()
            raise
    
    async def get_feedback(
        self,
        db: AsyncSession,
        feedback_id: str
    ) -> Optional[RAGFeedback]:
        """
        Belirli bir geri bildirimi getirir
        
        Args:
            db: Veritabanı oturumu
            feedback_id: Geri bildirim ID'si
            
        Returns:
            Optional[RAGFeedback]: Geri bildirim veya None
        """
        stmt = select(RAGFeedback).filter(RAGFeedback.id == feedback_id)
        result = await db.execute(stmt)
        return result.scalars().first()
    
    async def get_query_feedback(
        self,
        db: AsyncSession,
        query_id: str
    ) -> List[RAGFeedback]:
        """
        Belirli bir sorgu için tüm geri bildirimleri getirir
        
        Args:
            db: Veritabanı oturumu
            query_id: Sorgu ID'si
            
        Returns:
            List[RAGFeedback]: Geri bildirim listesi
        """
        stmt = select(RAGFeedback).filter(RAGFeedback.query_id == query_id)
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def get_user_feedback(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int = 50
    ) -> List[RAGFeedback]:
        """
        Belirli bir kullanıcının geri bildirimlerini getirir
        
        Args:
            db: Veritabanı oturumu
            user_id: Kullanıcı ID'si
            limit: Maksimum geri bildirim sayısı
            
        Returns:
            List[RAGFeedback]: Geri bildirim listesi
        """
        stmt = select(RAGFeedback).filter(RAGFeedback.user_id == user_id).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def _analyze_feedback(self, db: AsyncSession, feedback: RAGFeedback):
        """
        Geri bildirimi analiz eder ve gerekli aksiyonları alır
        
        Args:
            db: Veritabanı oturumu
            feedback: Geri bildirim
        """
        # Düşük puanları günlüğe kaydet
        if feedback.rating <= 2:
            logger.warning(f"Low rating feedback received: {feedback.id}, Query: {feedback.query_id}, Rating: {feedback.rating}")
            
            # Gelecekte: Otomatik iyileştirme için düşük puanlı yanıtları analiz et
            
        # Gelecekteki iyileştirmeler:
        # 1. Sürekli düşük puan alan sorgu türlerini tanımlama
        # 2. Geri bildirim tabanlı model/retriever ince ayarı
        # 3. Kullanıcı tercihleri öğrenme