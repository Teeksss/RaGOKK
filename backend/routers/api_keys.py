# Last reviewed: 2025-04-29 09:15:13 UTC (User: TeeksssAPI)
from fastapi import APIRouter, Depends, HTTPException, Body, status
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import json
import uuid
import time
from datetime import datetime

from ..db.async_database import get_db
from ..utils.config import (
    OPENAI_API_KEY, COHERE_API_KEY, JINA_API_KEY,
    WEAVIATE_API_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
    TWITTER_CLIENT_ID, TWITTER_CLIENT_SECRET
)
from ..models.api_key_models import ApiKey, ApiKeyCreate, ApiKeyUpdate, ApiProvider
from ..auth import get_current_active_user, require_admin, UserInDB as User
from ..repositories.api_key_repository import ApiKeyRepository
from ..utils.encrypt import encrypt_value, decrypt_value
from ..utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

# Repository instance
api_key_repo = ApiKeyRepository()

@router.get("/api-keys", response_model=List[ApiKey])
async def get_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)  # Sadece admin erişebilir
):
    """Sistemdeki tüm API anahtarlarını listeler (sadece meta bilgileri, anahtarları değil)"""
    try:
        keys = await api_key_repo.get_all_keys(db)
        return keys
    except Exception as e:
        logger.error(f"API key listing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list API keys: {str(e)}"
        )

@router.get("/api-keys/{provider}", response_model=ApiKey)
async def get_provider_key(
    provider: ApiProvider,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)  # Sadece admin erişebilir
):
    """Belirli bir sağlayıcının API anahtarı hakkında bilgi verir"""
    try:
        key = await api_key_repo.get_key_by_provider(db, provider)
        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No API key found for provider: {provider}"
            )
        return key
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API key retrieval error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve API key: {str(e)}"
        )

@router.post("/api-keys", response_model=ApiKey)
async def create_api_key(
    key_data: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)  # Sadece admin erişebilir
):
    """Yeni bir API anahtarı ekler"""
    try:
        # İlk önce bu sağlayıcı için anahtar var mı kontrol et
        existing_key = await api_key_repo.get_key_by_provider(db, key_data.provider)
        if existing_key:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"API key already exists for provider: {key_data.provider}"
            )
        
        # API anahtarını şifrele
        encrypted_key = encrypt_value(key_data.api_key)
        
        # Anahtarı oluştur
        new_key = await api_key_repo.create_key(
            db,
            provider=key_data.provider,
            api_key=encrypted_key,
            description=key_data.description,
            is_active=key_data.is_active,
            metadata=key_data.metadata
        )
        
        # Anahtar değerini maskele
        new_key.api_key = "•••••••••••••••" + new_key.api_key[-4:] if new_key.api_key else None
        
        return new_key
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API key creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create API key: {str(e)}"
        )

@router.put("/api-keys/{provider}", response_model=ApiKey)
async def update_api_key(
    provider: ApiProvider,
    key_data: ApiKeyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)  # Sadece admin erişebilir
):
    """API anahtarını günceller"""
    try:
        # Sağlayıcı için anahtar var mı kontrol et
        existing_key = await api_key_repo.get_key_by_provider(db, provider)
        if not existing_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No API key found for provider: {provider}"
            )
        
        # Güncelleme bilgilerini hazırla
        update_data = {}
        
        if key_data.api_key is not None:
            # API anahtarını şifrele
            update_data["api_key"] = encrypt_value(key_data.api_key)
        
        if key_data.description is not None:
            update_data["description"] = key_data.description
            
        if key_data.is_active is not None:
            update_data["is_active"] = key_data.is_active
            
        if key_data.metadata is not None:
            update_data["metadata"] = key_data.metadata
        
        # Anahtarı güncelle
        updated_key = await api_key_repo.update_key(db, provider, update_data)
        
        # Anahtar değerini maskele
        updated_key.api_key = "•••••••••••••••" + updated_key.api_key[-4:] if updated_key.api_key else None
        
        return updated_key
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API key update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update API key: {str(e)}"
        )

@router.delete("/api-keys/{provider}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    provider: ApiProvider,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)  # Sadece admin erişebilir
):
    """API anahtarını siler"""
    try:
        # Sağlayıcı için anahtar var mı kontrol et
        existing_key = await api_key_repo.get_key_by_provider(db, provider)
        if not existing_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No API key found for provider: {provider}"
            )
        
        # Anahtarı sil
        await api_key_repo.delete_key(db, provider)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API key deletion error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete API key: {str(e)}"
        )

@router.get("/api-keys/verify/{provider}")
async def verify_api_key(
    provider: ApiProvider,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)  # Sadece admin erişebilir
):
    """API anahtarını doğrular (provider API'ına test isteği yapar)"""
    try:
        # Sağlayıcı için anahtar var mı kontrol et
        key_record = await api_key_repo.get_key_by_provider(db, provider)
        if not key_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No API key found for provider: {provider}"
            )
        
        # API anahtarını çöz
        api_key = decrypt_value(key_record.api_key)
        
        # Sağlayıcıya özel doğrulama mantığı
        verification_result = await verify_provider_key(provider, api_key)
        
        return {
            "provider": provider,
            "is_valid": verification_result["is_valid"],
            "message": verification_result["message"],
            "details": verification_result.get("details")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API key verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify API key: {str(e)}"
        )

@router.get("/api-providers", response_model=List[Dict[str, Any]])
async def get_api_providers(
    current_user: User = Depends(get_current_active_user)
):
    """Desteklenen API sağlayıcılarının listesini döndürür"""
    providers = []
    
    for provider in ApiProvider:
        provider_info = {
            "id": provider,
            "name": get_provider_name(provider),
            "description": get_provider_description(provider),
            "icon": get_provider_icon(provider),
            "website": get_provider_website(provider),
            "category": get_provider_category(provider)
        }
        providers.append(provider_info)
    
    return providers

@router.get("/api-keys/status")
async def get_api_key_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """API anahtarlarının genel durumunu döndürür (hangi sağlayıcılar aktif vs.)"""
    try:
        # Normal kullanıcılar ve adminler için farklı bilgiler
        is_admin = "admin" in current_user.roles
        
        keys = await api_key_repo.get_all_keys(db) if is_admin else []
        
        result = {}
        
        # Tüm sağlayıcılar için durum oluştur
        for provider in ApiProvider:
            key_record = next((k for k in keys if k.provider == provider), None)
            
            if is_admin:
                result[provider] = {
                    "is_configured": key_record is not None,
                    "is_active": key_record.is_active if key_record else False,
                    "last_updated": key_record.updated_at if key_record else None
                }
            else:
                # Normal kullanıcılar sadece hangi servisin kullanılabilir olduğunu görebilir
                result[provider] = {
                    "is_available": key_record is not None and key_record.is_active if key_record else False
                }
        
        return result
        
    except Exception as e:
        logger.error(f"API key status error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get API key status: {str(e)}"
        )

# --- Yardımcı fonksiyonlar ---

async def verify_provider_key(provider: str, api_key: str) -> Dict[str, Any]:
    """API anahtarını doğrulamak için ilgili servise basit bir istek yapar"""
    try:
        import httpx
        
        result = {
            "is_valid": False,
            "message": "Doğrulama başarısız",
            "details": None
        }
        
        # OpenAI
        if provider == ApiProvider.OPENAI:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    result["is_valid"] = True
                    result["message"] = "API anahtarı geçerli"
                    result["details"] = {"available_models": len(response.json()["data"])}
                else:
                    result["message"] = f"API anahtarı geçersiz: {response.text}"
        
        # Cohere
        elif provider == ApiProvider.COHERE:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "texts": ["Test message for API key validation"]
                }
                response = await client.post(
                    "https://api.cohere.ai/v1/embed",
                    headers=headers,
                    json=payload,
                    timeout=10
                )
                
                if response.status_code == 200:
                    result["is_valid"] = True
                    result["message"] = "API anahtarı geçerli"
                else:
                    result["message"] = f"API anahtarı geçersiz: {response.text}"
        
        # Jina
        elif provider == ApiProvider.JINA:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "texts": ["Test message for API key validation"],
                    "model": "jina-embeddings-v2-base-en"
                }
                response = await client.post(
                    "https://api.jina.ai/v1/embeddings",
                    headers=headers,
                    json=payload,
                    timeout=10
                )
                
                if response.status_code == 200:
                    result["is_valid"] = True
                    result["message"] = "API anahtarı geçerli"
                else:
                    result["message"] = f"API anahtarı geçersiz: {response.text}"
        
        # Weaviate
        elif provider == ApiProvider.WEAVIATE:
            if not api_key:
                result["message"] = "API anahtarı sağlanmadı"
                return result
                
            # Weaviate için basit bir sağlık kontrolü
            # Normalde weaviate-client kullanılır ama burada basit bir HTTP isteği ile kontrol ediyoruz
            try:
                from ..utils.config import WEAVIATE_URL
                weaviate_url = WEAVIATE_URL if WEAVIATE_URL else "http://localhost:8080"
                
                async with httpx.AsyncClient() as client:
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    }
                    response = await client.get(
                        f"{weaviate_url}/v1/.well-known/ready",
                        headers=headers,
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        result["is_valid"] = True
                        result["message"] = "API anahtarı geçerli"
                    else:
                        result["message"] = f"API anahtarı geçersiz: {response.text}"
            except Exception as e:
                result["message"] = f"Weaviate bağlantı hatası: {str(e)}"
        
        # Google
        elif provider == ApiProvider.GOOGLE:
            # Google API doğrulaması daha karmaşık, sadece basit bir kontrol
            if not api_key:
                result["message"] = "API anahtarı sağlanmadı"
                return result
            
            result["is_valid"] = True
            result["message"] = "API anahtarı formatı geçerli (tam doğrulama yapılamıyor)"
        
        # Twitter
        elif provider == ApiProvider.TWITTER:
            # Twitter API doğrulaması OAuth gerektiriyor, basit bir kontrol
            if not api_key:
                result["message"] = "API anahtarı sağlanmadı"
                return result
            
            result["is_valid"] = True
            result["message"] = "API anahtarı formatı geçerli (tam doğrulama yapılamıyor)"
        
        # Diğer sağlayıcılar
        else:
            result["message"] = f"Desteklenmeyen sağlayıcı: {provider}"
        
        return result
        
    except Exception as e:
        return {
            "is_valid": False,
            "message": f"Doğrulama sırasında hata: {str(e)}",
            "details": None
        }

def get_provider_name(provider: str) -> str:
    """Sağlayıcı adını döndürür"""
    names = {
        ApiProvider.OPENAI: "OpenAI",
        ApiProvider.COHERE: "Cohere",
        ApiProvider.JINA: "Jina AI",
        ApiProvider.WEAVIATE: "Weaviate",
        ApiProvider.GOOGLE: "Google Cloud",
        ApiProvider.TWITTER: "Twitter (X)",
        ApiProvider.FACEBOOK: "Facebook",
        ApiProvider.LINKEDIN: "LinkedIn",
        ApiProvider.AZURE: "Azure OpenAI",
        ApiProvider.AWS: "Amazon Web Services",
        ApiProvider.HUGGINGFACE: "Hugging Face"
    }
    return names.get(provider, provider)

def get_provider_description(provider: str) -> str:
    """Sağlayıcı açıklamasını döndürür"""
    descriptions = {
        ApiProvider.OPENAI: "OpenAI API anahtarı ile GPT ve Embedding modellerine erişim sağlar.",
        ApiProvider.COHERE: "Cohere API anahtarı ile gelişmiş LLM ve Embedding modellerine erişim sağlar.",
        ApiProvider.JINA: "Jina AI API anahtarı ile güçlü embedding modellerine erişim sağlar.",
        ApiProvider.WEAVIATE: "Weaviate vector veritabanı için API anahtarı.",
        ApiProvider.GOOGLE: "Google Cloud API anahtarı ile Google servislerine erişim sağlar.",
        ApiProvider.TWITTER: "Twitter (X) API anahtarı ile sosyal medya içeriğine erişim sağlar.",
        ApiProvider.FACEBOOK: "Facebook API anahtarı ile sosyal medya içeriğine erişim sağlar.",
        ApiProvider.LINKEDIN: "LinkedIn API anahtarı ile profesyonel içerik ve bağlantılara erişim sağlar.",
        ApiProvider.AZURE: "Azure OpenAI servisi için API anahtarı.",
        ApiProvider.AWS: "Amazon Web Services için API anahtarı.",
        ApiProvider.HUGGINGFACE: "Hugging Face API anahtarı ile ML modellerine erişim sağlar."
    }
    return descriptions.get(provider, "API anahtarı")

def get_provider_icon(provider: str) -> str:
    """Sağlayıcı ikonunu döndürür"""
    icons = {
        ApiProvider.OPENAI: "openai.svg",
        ApiProvider.COHERE: "cohere.svg",
        ApiProvider.JINA: "jina.svg",
        ApiProvider.WEAVIATE: "weaviate.svg",
        ApiProvider.GOOGLE: "google.svg",
        ApiProvider.TWITTER: "twitter.svg",
        ApiProvider.FACEBOOK: "facebook.svg",
        ApiProvider.LINKEDIN: "linkedin.svg",
        ApiProvider.AZURE: "azure.svg",
        ApiProvider.AWS: "aws.svg",
        ApiProvider.HUGGINGFACE: "huggingface.svg"
    }
    return icons.get(provider, "generic-api.svg")

def get_provider_website(provider: str) -> str:
    """Sağlayıcı web sitesini döndürür"""
    websites = {
        ApiProvider.OPENAI: "https://platform.openai.com",
        ApiProvider.COHERE: "https://cohere.ai",
        ApiProvider.JINA: "https://jina.ai",
        ApiProvider.WEAVIATE: "https://weaviate.io",
        ApiProvider.GOOGLE: "https://cloud.google.com",
        ApiProvider.TWITTER: "https://developer.twitter.com",
        ApiProvider.FACEBOOK: "https://developers.facebook.com",
        ApiProvider.LINKEDIN: "https://developer.linkedin.com",
        ApiProvider.AZURE: "https://azure.microsoft.com/en-us/services/openai-service/",
        ApiProvider.AWS: "https://aws.amazon.com",
        ApiProvider.HUGGINGFACE: "https://huggingface.co"
    }
    return websites.get(provider, "#")

def get_provider_category(provider: str) -> str:
    """Sağlayıcı kategorisini döndürür"""
    categories = {
        ApiProvider.OPENAI: "LLM & Embeddings",
        ApiProvider.COHERE: "LLM & Embeddings",
        ApiProvider.JINA: "Embeddings",
        ApiProvider.WEAVIATE: "Vector Database",
        ApiProvider.GOOGLE: "Cloud & OAuth",
        ApiProvider.TWITTER: "Social Media",
        ApiProvider.FACEBOOK: "Social Media",
        ApiProvider.LINKEDIN: "Social Media",
        ApiProvider.AZURE: "Cloud LLM",
        ApiProvider.AWS: "Cloud Services",
        ApiProvider.HUGGINGFACE: "ML Models"
    }
    return categories.get(provider, "Other")