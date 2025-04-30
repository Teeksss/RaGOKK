# Last reviewed: 2025-04-30 05:03:25 UTC (User: Teeksss)
from sqlalchemy import Column, String, Boolean, ForeignKey, Table, DateTime, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime, timezone

from ..db.base_class import Base

# Kullanıcı - Rol ilişki tablosu
user_role = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", UUID(as_uuid=False), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)),
    Column("created_by", UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
)

# Rol - İzin ilişki tablosu
role_permission = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", UUID(as_uuid=False), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", UUID(as_uuid=False), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)),
    Column("created_by", UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
)

class Role(Base):
    """Kullanıcı rolleri tablosu"""
    __tablename__ = "roles"
    
    # Birincil anahtar
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Rol bilgileri
    name = Column(String(100), nullable=False)
    code = Column(String(50), nullable=False, unique=True)
    description = Column(String(255), nullable=True)
    is_system = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    
    # İlişkiler
    organization_id = Column(UUID(as_uuid=False), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    
    # İlişki referansları
    organization = relationship("Organization", back_populates="roles")
    users = relationship("User", secondary=user_role, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permission, back_populates="roles")
    
    # Zaman damgaları
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Oluşturan/güncelleyen
    created_by = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # İndeksler
    __table_args__ = (
        Index("idx_role_code", code),
        Index("idx_role_org", organization_id),
    )
    
    def __repr__(self):
        return f"<Role(id={self.id}, name='{self.name}', code='{self.code}')>"

class Permission(Base):
    """İzinler tablosu"""
    __tablename__ = "permissions"
    
    # Birincil anahtar
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # İzin bilgileri
    name = Column(String(100), nullable=False)
    code = Column(String(100), nullable=False, unique=True)
    description = Column(String(255), nullable=True)
    category = Column(String(50), nullable=False)  # Gruplama için (documents, users, settings vb.)
    resource_type = Column(String(50), nullable=False)  # İzin hangi kaynak türü ile ilgili (document, collection, user vb.)
    action = Column(String(50), nullable=False)  # İzin eylemi (create, read, update, delete, list vb.)
    constraints = Column(JSONB, nullable=True)  # İzin kısıtlamaları (JSON formatında)
    
    # İlişkiler
    roles = relationship("Role", secondary=role_permission, back_populates="permissions")
    
    # Zaman damgaları
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # İndeksler
    __table_args__ = (
        UniqueConstraint("resource_type", "action", "category", name="uq_permission_resource_action"),
        Index("idx_permission_code", code),
        Index("idx_permission_category", category),
        Index("idx_permission_resource_type", resource_type),
    )
    
    def __repr__(self):
        return f"<Permission(id={self.id}, code='{self.code}', resource_type='{self.resource_type}', action='{self.action}')>"