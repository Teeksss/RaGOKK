# Last reviewed: 2025-04-30 07:11:25 UTC (User: Teeksss)
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, JSON, Boolean, Float, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, timezone

from ..db.base_class import Base

class QAPair(Base):
    """Soru-Cevap çifti modeli"""
    __tablename__ = "qa_pairs"
    
    # Birincil anahtar
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # İlişkiler
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # Soru-Cevap içeriği
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    
    # Segment bilgisi
    segment_id = Column(String(100), nullable=True)
    segment_index = Column(Integer, nullable=True)
    page_number = Column(Integer, nullable=True)
    
    # Metadata
    difficulty = Column(String(10), nullable=False, default="medium")  # easy, medium, hard
    question_type = Column(String(20), nullable=False, default="factual")  # factual, conceptual, analytical
    metadata = Column(JSON, nullable=True)
    
    # İlişki tanımları
    document = relationship("Document", back_populates="qa_pairs")
    
    # Zaman damgaları
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=True)
    
    # İndeksler
    __table_args__ = (
        Index("idx_qa_document_id", document_id),
        Index("idx_qa_segment_id", segment_id),
        Index("idx_qa_difficulty", difficulty),
        Index("idx_qa_question_type", question_type),
    )
    
    def to_dict(self) -> dict:
        """Dict temsilini döndürür"""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "question": self.question,
            "answer": self.answer,
            "segment_id": self.segment_id,
            "segment_index": self.segment_index,
            "page_number": self.page_number,
            "difficulty": self.difficulty,
            "question_type": self.question_type,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f"<QAPair(id={self.id}, document_id={self.document_id}, question={self.question[:20]}...)>"