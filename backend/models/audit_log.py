# Last reviewed: 2025-04-29 13:59:34 UTC (User: TeeksssAPI)
from sqlalchemy import Column, String, DateTime, JSON, Enum, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
import enum
import uuid
from datetime import datetime, timezone
import json

from ..db.base_class import Base

class AuditLogType(str, enum.Enum):
    """Denetim kaydı olay türleri"""
    AUTH = "auth"  # Kimlik doğrulama olayları
    DATA = "data"  # Veri değişikliği olayları
    ADMIN = "admin"  # Yönetim olayları
    SYSTEM = "system"  # Sistem olayları
    SECURITY = "security"  # Güvenlik olayları
    API = "api"  # API erişim olayları
    INTEGRATION = "integration"  # Entegrasyon olayları

class AuditLogStatus(str, enum.Enum):
    """Denetim kaydı durum türleri"""
    SUCCESS = "success"  # Başarılı işlem
    FAILURE = "failure"  # Başarısız işlem
    WARNING = "warning"  # Uyarı
    INFO = "info"  # Bilgilendirme

class AuditLog(Base):
    """Denetim kaydı modeli"""
    __tablename__ = "audit_logs"
    
    # Benzersiz kimlik
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Olay bilgileri
    event_type = Column(String(50), nullable=False, index=True)
    user_id = Column(String(100), nullable=True, index=True)
    resource_type = Column(String(50), nullable=True, index=True)
    resource_id = Column(String(100), nullable=True, index=True)
    action = Column(String(50), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="success", index=True)
    
    # Detaylar
    details = Column(JSON, nullable=True)
    
    # Meta bilgiler
    ip_address = Column(String(45), nullable=True)  # IPv6 için 45 karakter
    user_agent = Column(Text, nullable=True)
    organization_id = Column(String(100), nullable=True, index=True)
    
    # Zaman damgası (her zaman UTC olarak saklanır)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    
    # İndeksler
    __table_args__ = (
        # Zaman bazlı sorgular için
        Index('idx_audit_logs_timestamp', timestamp.desc()),
        
        # Kaynak bazlı sorgular için
        Index('idx_audit_logs_resource', resource_type, resource_id),
        
        # Kullanıcı aktiviteleri için
        Index('idx_audit_logs_user_timestamp', user_id, timestamp.desc()),
        
        # Organizasyon olayları için
        Index('idx_audit_logs_org_timestamp', organization_id, timestamp.desc()),
        
        # Güvenlik olayları için
        Index('idx_audit_logs_security', event_type, status, timestamp.desc()),
    )
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, type={self.event_type}, user={self.user_id}, resource={self.resource_type}:{self.resource_id})>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "event_type": self.event_type,
            "user_id": self.user_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action": self.action,
            "status": self.status,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "organization_id": self.organization_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }