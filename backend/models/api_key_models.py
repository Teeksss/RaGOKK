# Last reviewed: 2025-04-29 09:15:13 UTC (User: TeeksssAPI)
from pydantic import BaseModel, Field, validator
from typing import Dict, Optional, Any, List
from enum import Enum
import datetime

class ApiProvider(str, Enum):
    """Desteklenen API sağlayıcı türleri"""
    OPENAI = "openai"
    COHERE = "cohere"
    JINA = "jina"
    WEAVIATE = "weaviate"
    GOOGLE = "google"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"
    AZURE = "azure"
    AWS = "aws"
    HUGGINGFACE = "huggingface"

class ApiKeyCreate(BaseModel):
    """Yeni bir API anahtarı oluşturmak için model"""
    provider: ApiProvider
    api_key: str
    description: Optional[str] = None
    is_active: bool = True
    metadata: Optional[Dict[str, Any]] = None

class ApiKeyUpdate(BaseModel):
    """Mevcut bir API anahtarını güncellemek için model"""
    api_key: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None

class ApiKey(BaseModel):
    """API anahtarı modeli - veritabanından döndürülen"""
    id: int
    provider: ApiProvider
    api_key: Optional[str] = None  # Maskelenmiş olarak döndürülür
    description: Optional[str] = None
    is_active: bool
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None
    last_used: Optional[datetime.datetime] = None
    
    class Config:
        orm_mode = True