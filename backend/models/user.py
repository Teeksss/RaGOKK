# Last reviewed: 2025-04-30 05:03:25 UTC (User: Teeksss)
from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, Table, Index, UniqueConstraint, text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime, timezone

from ..db.base_class import Base
from .role_permission import user_role

class User(Base):
    """Kullanıcı tablosu"""
    __tablename__ = "users"
    
    # Birincil anahtar
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Kimlik bilgileri
    email = Column(String(255), nullable=False, unique=True)
    username = Column(String(50), nullable=True, unique=True)
    password = Column(String(255), nullable=False)
    
    # Kullanıcı bilgileri
    full_name = Column(String(100), nullable=True)
    profile_image = Column(String(255), nullable=True)
    
    # Durum ve güvenlik
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    is_verified = Column(Boolean, nullable=False, default=False, server_default="false")
    is_superuser = Column(Boolean, nullable=False, default=False, server_default="false")
    verification_token = Column(String(255), nullable=True)
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Kullanıcı ayarları ve tercihleri
    preferences = Column(JSONB, nullable=True)
    locale = Column(String(10), nullable=True, default="en")
    timezone = Column(String(50), nullable=True, default="UTC")
    
    # Kullanım durumu
    last_login = Column(DateTime(timezone=True), nullable=True)
    login_count = Column(Integer, nullable=False, default=0)
    
    # İlişkiler
    organization_id = Column(UUID(as_uuid=False), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    
    # İlişki referansları
    organization = relationship("Organization", back_populates="users")
    documents = relationship("Document", back_populates="user")
    prompt_templates = relationship("PromptTemplate", back_populates="user")
    roles = relationship("Role", secondary=user_role, back_populates="users")
    
    # Zaman damgaları
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # İndeksler
    __table_args__ = (
        Index("idx_user_email", email),
        Index("idx_user_username", username),
        Index("idx_user_organization", organization_id),
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', username='{self.username}')>"