# Last reviewed: 2025-04-30 05:49:14 UTC (User: Teeksss)
from sqlalchemy import Column, String, Integer, Float, Boolean, ForeignKey, DateTime, Table, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
import uuid
from datetime import datetime, timezone

from ..db.base_class import Base

class Document(Base):
    """Belge tablosu"""
    __tablename__ = "documents"
    
    # Birincil anahtar
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Belge bilgileri
    title = Column(String(255), nullable=False, index=True)
    description = Column(String(1000), nullable=True)
    source_type = Column(String(50), nullable=False)  # web, pdf, docx, txt, vb.
    file_type = Column(String(50), nullable=True)  # mime type veya uzantı
    file_path = Column(String(500), nullable=True)  # depolama yolu
    file_size = Column(Integer, nullable=True)  # bayt cinsinden boyut
    file_hash = Column(String(128), nullable=True, index=True)  # Dosya içerik hash'i (SHA-256)
    url = Column(String(1000), nullable=True)  # URL kaynak için
    
    # İndeksleme bilgileri
    indexed = Column(Boolean, nullable=False, default=False)
    indexed_at = Column(DateTime(timezone=True), nullable=True)
    error = Column(String(1000), nullable=True)
    chunks_count = Column(Integer, nullable=False, default=0)  # Toplam parça sayısı
    total_tokens = Column(Integer, nullable=True)  # Toplam token sayısı
    
    # OCR bilgileri
    ocr_applied = Column(Boolean, nullable=False, default=False)
    ocr_language = Column(String(10), nullable=True)  # OCR dili
    ocr_quality = Column(Float, nullable=True)  # OCR kalitesi (0-1)
    
    # Metadata
    metadata = Column(JSONB, nullable=True)  # Ek metadata
    tags = Column(ARRAY(String), nullable=True)  # Etiketler
    
    # İlişkiler
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    organization_id = Column(UUID(as_uuid=False), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    
    # İlişki referansları
    user = relationship("User", back_populates="documents")
    organization = relationship("Organization", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    
    # Paylaşım ayarları
    is_public = Column(Boolean, nullable=False, default=False)  # Herkese açık mı
    shared_with_organization = Column(Boolean, nullable=False, default=True)  # Organizasyon içinde paylaşımlı mı
    
    # Zaman damgaları
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # İndeksler
    __table_args__ = (
        Index("idx_document_user", user_id),
        Index("idx_document_organization", organization_id),
        Index("idx_document_created", created_at),
        Index("idx_document_file_hash_org", file_hash, organization_id),
        UniqueConstraint("file_hash", "organization_id", name="uq_document_file_hash_org")
    )
    
    def __repr__(self):
        return f"<Document(id={self.id}, title='{self.title}', indexed={self.indexed})>"

class DocumentChunk(Base):
    """Belge parçası tablosu"""
    __tablename__ = "document_chunks"
    
    # Birincil anahtar
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Parça bilgileri
    chunk_index = Column(Integer, nullable=False)
    content = Column(String, nullable=False)
    metadata = Column(JSONB, nullable=True)  # Parça özel metadata
    tokens_count = Column(Integer, nullable=True)  # Parçadaki token sayısı
    embedding_model = Column(String(100), nullable=True)  # Embedding modeli
    
    # Vektör DB entegrasyonu için dışsal kimlik
    external_id = Column(String(100), nullable=True)  # Vektör DB'deki kimlik
    
    # İlişkiler
    document_id = Column(UUID(as_uuid=False), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # İlişki referansları
    document = relationship("Document", back_populates="chunks")
    
    # Zaman damgaları
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # İndeksler
    __table_args__ = (
        Index("idx_chunk_document", document_id),
        Index("idx_chunk_index", document_id, chunk_index)
    )
    
    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, document_id={self.document_id}, chunk_index={self.chunk_index})>"