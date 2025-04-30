# Last reviewed: 2025-04-29 14:31:59 UTC (User: Teeksss)
from sqlalchemy import Column, String, Text, Boolean, ForeignKey, DateTime, Index, func, text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, timezone

from ..db.base_class import Base

class PromptTemplate(Base):
    """
    LLM prompt şablonları tablosu
    
    Bu model, RAG sorguları için kullanılacak prompt şablonlarını saklar.
    Sistemde hazır şablonlar ve kullanıcı tarafından oluşturulan şablonlar bulunabilir.
    """
    __tablename__ = "prompt_templates"
    
    # Birincil anahtar
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Şablon bilgileri
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    template = Column(Text, nullable=False)
    
    # Şablon türü
    is_system = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    
    # İlişkiler
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    organization_id = Column(UUID(as_uuid=False), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    
    # İlişki referansları
    user = relationship("User", back_populates="prompt_templates")
    organization = relationship("Organization", back_populates="prompt_templates")
    
    # Zaman damgaları
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # İndeksler ve kısıtlamalar
    __table_args__ = (
        # Kullanıcı başına şablon adı benzersiz olmalı
        UniqueConstraint("user_id", "name", name="uq_prompt_template_user_name"),
        
        # Organizasyon başına şablon adı benzersiz olmalı
        UniqueConstraint("organization_id", "name", name="uq_prompt_template_org_name"),
        
        # Sistem şablonları için ad benzersiz olmalı
        UniqueConstraint("name", name="uq_system_template_name", postgresql_where=text("is_system = true")),
        
        # İndeksler
        Index("idx_prompt_templates_user_id", "user_id"),
        Index("idx_prompt_templates_organization_id", "organization_id"),
        Index("idx_prompt_templates_is_system", "is_system"),
        Index("idx_prompt_templates_name", "name"),
    )
    
    def __repr__(self):
        return f"<PromptTemplate(id={self.id}, name='{self.name}', is_system={self.is_system})>"
    
    def to_dict(self):
        """Sözlük gösterimi"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "template": self.template,
            "is_system": self.is_system,
            "user_id": str(self.user_id) if self.user_id else None,
            "organization_id": str(self.organization_id) if self.organization_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }