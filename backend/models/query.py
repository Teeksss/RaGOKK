# Last reviewed: 2025-04-30 06:02:16 UTC (User: Teeksss)
from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, Integer, Float, Text, Table, Index, JSON, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime, timezone

from ..db.base_class import Base

class QuerySource(Base):
    """Sorgu kaynağı modeli"""
    __tablename__ = "query_sources"
    
    # Birincil anahtar
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Kaynak belirteci
    query_id = Column(UUID(as_uuid=False), ForeignKey("queries.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(UUID(as_uuid=False), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    
    # Kaynak içeriği
    content = Column(Text, nullable=True)
    content_snippet = Column(String(1000), nullable=True)  # Belge parçasının bir kısmı
    
    # Metadata
    similarity_score = Column(Float, nullable=True)  # Benzerlik puanı
    chunk_index = Column(Integer, nullable=True)  # Belge parçası indeksi
    page_number = Column(Integer, nullable=True)  # PDF sayfası (varsa)
    
    # Yol bilgisi (belge silinirse)
    document_path = Column(String(500), nullable=True)
    document_title = Column(String(255), nullable=True)
    
    # İlişkiler
    query = relationship("Query", back_populates="sources")
    document = relationship("Document", back_populates="query_sources")
    
    # Zaman damgaları
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # İndeksler
    __table_args__ = (
        Index("idx_query_source_query", query_id),
        Index("idx_query_source_document", document_id),
    )
    
    def __repr__(self):
        return f"<QuerySource(id={self.id}, query_id={self.query_id}, document_id={self.document_id})>"

class Query(Base):
    """Sorgu modeli"""
    __tablename__ = "queries"
    
    # Birincil anahtar
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Sorgu bilgileri
    question = Column(String(2000), nullable=False)
    answer = Column(Text, nullable=True)
    
    # Yanıt formatı
    answer_format = Column(String(50), nullable=True)  # markdown, text, html, vb.
    
    # İşlem bilgileri
    processing_time_ms = Column(Integer, nullable=True)
    has_error = Column(Boolean, nullable=False, default=False)
    error_message = Column(String(1000), nullable=True)
    
    # Metadata
    search_type = Column(String(50), nullable=True)  # semantic, hybrid, keyword, vb.
    metadata = Column(JSONB, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    
    # İlişkiler
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    organization_id = Column(UUID(as_uuid=False), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    prompt_template_id = Column(UUID(as_uuid=False), ForeignKey("prompt_templates.id", ondelete="SET NULL"), nullable=True)
    
    # İlişki referansları
    user = relationship("User", back_populates="queries")
    organization = relationship("Organization", back_populates="queries")
    prompt_template = relationship("PromptTemplate", back_populates="queries")
    sources = relationship("QuerySource", back_populates="query", cascade="all, delete-orphan")
    
    # Zaman damgaları
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # İndeksler
    __table_args__ = (
        Index("idx_query_user", user_id),
        Index("idx_query_org", organization_id),
        Index("idx_query_created", created_at),
    )
    
    def __repr__(self):
        return f"<Query(id={self.id}, question={self.question})>"