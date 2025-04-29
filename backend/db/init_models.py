# Last reviewed: 2025-04-29 10:07:48 UTC (User: TeeksssJina)
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from .async_database import Base

class User(Base):
    """User database table"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String)
    disabled = Column(Boolean, default=False)
    roles = Column(String, default="user")  # Comma-separated roles: "user", "admin", etc.
    created_at = Column(DateTime(timezone=True), default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

class Document(Base):
    """Document database table"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True)
    external_id = Column(String, index=True)  # ID from the external source
    title = Column(String, nullable=True)
    content = Column(Text)
    content_hash = Column(String, index=True)
    source = Column(String)
    source_url = Column(String, nullable=True)
    metadata = Column(Text)  # JSON-serialized metadata
    owner_user_id = Column(Integer, ForeignKey("users.id"))
    es_index = Column(String)
    es_id = Column(String)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationship
    owner = relationship("User")

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