# Last reviewed: 2025-04-29 10:27:19 UTC (User: TeeksssAPI)
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .async_database import Base

# Mevcut modeller...

class ApiKeyDB(Base):
    """API anahtarları veritabanı tablosu"""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, unique=True, index=True)  # openai, cohere, jina, vs.
    api_key = Column(String, nullable=True)  # Şifrelenmiş API anahtarı
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    metadata = Column(Text, nullable=True)  # JSON olarak serileştirilmiş ek veriler
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True)
    last_used = Column(DateTime(timezone=True), nullable=True)

class SecurityLogDB(Base):
    """Güvenlik loglama tablosu"""
    __tablename__ = "security_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), default=func.now(), index=True)
    log_type = Column(String, index=True)  # api_key, auth, admin_action, etc.
    user_id = Column(String, nullable=True, index=True)
    action = Column(String, nullable=False)  # create, update, delete, access
    resource_type = Column(String, nullable=True)  # provider type for API keys
    resource_id = Column(String, nullable=True)  # specific resource identifier
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    details = Column(Text, nullable=True)  # JSON formatted details
    success = Column(Boolean, default=True)
    severity = Column(String, default="info")  # info, warning, error, critical