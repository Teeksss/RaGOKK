# Last reviewed: 2025-04-30 06:34:07 UTC (User: Teeksss)
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, timezone

from ..db.base_class import Base

class RAGFeedback(Base):
    """RAG kullanıcı geri bildirimi modeli"""
    __tablename__ = "rag_feedback"
    
    # Birincil anahtar
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # İlişkiler
    query_id = Column(String(36), ForeignKey("queries.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Derecelendirme bilgileri
    rating = Column(Integer, nullable=False)
    feedback = Column(Text, nullable=True)
    feedback_type = Column(String(50), nullable=False, default="answer_quality")
    
    # Metadata (sorgulanan belgeler, retrievers, yanıtlar vb.)
    metadata = Column(JSON, nullable=True)
    
    # İlişki referansları
    query = relationship("Query", back_populates="feedback")
    user = relationship("User", back_populates="feedback")
    
    # Zaman damgaları
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # İndeksler
    __table_args__ = (
        Index("idx_feedback_query", query_id),
        Index("idx_feedback_user", user_id),
        Index("idx_feedback_rating", rating),
        Index("idx_feedback_type", feedback_type),
        Index("idx_feedback_created", created_at),
    )
    
    def __repr__(self):
        return f"<RAGFeedback(id={self.id}, query_id={self.query_id}, rating={self.rating})>"