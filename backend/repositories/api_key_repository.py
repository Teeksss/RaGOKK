# Last reviewed: 2025-04-29 09:15:13 UTC (User: TeeksssAPI)
from typing import Dict, List, Optional, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete, func
import datetime
import json

from ..db.async_database import Base
from ..db.models import ApiKeyDB
from ..models.api_key_models import ApiKey, ApiProvider
from ..utils.logger import get_logger

logger = get_logger(__name__)

class ApiKeyRepository:
    """API anahtarlarını yönetmek için repository"""
    
    async def get_all_keys(self, db: AsyncSession) -> List[ApiKey]:
        """Tüm API anahtarlarını getirir"""
        try:
            result = await db.execute(select(ApiKeyDB))
            keys_db = result.scalars().all()
            
            keys = []
            for key_db in keys_db:
                # API anahtarını maskele (sadece son 4 karakter görünsün)
                masked_key = None
                if key_db.api_key:
                    masked_key = "•••••••••••••••" + key_db.api_key[-4:] if len(key_db.api_key) >= 4 else "••••••••"
                
                # Metadata'yı parse et
                metadata = {}
                if key_db.metadata:
                    try:
                        metadata = json.loads(key_db.metadata)
                    except:
                        metadata = {}
                
                # Pydantic modeli oluştur
                key = ApiKey(
                    id=key_db.id,
                    provider=key_db.provider,
                    api_key=masked_key,
                    description=key_db.description,
                    is_active=key_db.is_active,
                    metadata=metadata,
                    created_at=key_db.created_at,
                    updated_at=key_db.updated_at,
                    last_used=key_db.last_used
                )
                keys.append(key)
            
            return keys
            
        except Exception as e:
            logger.error(f"Error getting all API keys: {e}")
            raise
    
    async def get_key_by_provider(self, db: AsyncSession, provider: Union[ApiProvider, str]) -> Optional[ApiKey]:
        """Belirli bir sağlayıcı için API anahtarını getirir"""
        try:
            result = await db.execute(select(ApiKeyDB).where(ApiKeyDB.provider == provider))
            key_db = result.scalars().first()
            
            if not key_db:
                return None
            
            # Metadata'yı parse et
            metadata = {}
            if key_db.metadata:
                try:
                    metadata = json.loads(key_db.metadata)
                except:
                    metadata = {}
            
            # Pydantic modeli oluştur
            key = ApiKey(
                id=key_db.id,
                provider=key_db.provider,
                api_key=key_db.api_key,  # Şifrelenmiş anahtarı döndür
                description=key_db.description,
                is_active=key_db.is_active,
                metadata=metadata,
                created_at=key_db.created_at,
                updated_at=key_db.updated_at,
                last_used=key_db.last_used
            )
            
            return key
            
        except Exception as e:
            logger.error(f"Error getting API key by provider {provider}: {e}")
            raise
    
    async def create_key(
        self, 
        db: AsyncSession, 
        provider: Union[ApiProvider, str], 
        api_key: str,
        description: Optional[str] = None,
        is_active: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ApiKey:
        """Yeni bir API anahtarı oluşturur"""
        try:
            # Metadata'yı JSON'a çevir
            metadata_json = json.dumps(metadata) if metadata else None
            
            # Insert
            stmt = insert(ApiKeyDB).values(
                provider=provider,
                api_key=api_key,
                description=description,
                is_active=is_active,
                metadata=metadata_json,
                created_at=datetime.datetime.utcnow()
            ).returning(ApiKeyDB)
            
            result = await db.execute(stmt)
            key_db = result.scalars().first()
            
            # DB işlemini kaydet
            await db.commit()
            
            # Pydantic modeli oluştur
            key = ApiKey(
                id=key_db.id,
                provider=key_db.provider,
                api_key=key_db.api_key,
                description=key_db.description,
                is_active=key_db.is_active,
                metadata=metadata,
                created_at=key_db.created_at,
                updated_at=key_db.updated_at,
                last_used=key_db.last_used
            )
            
            return key
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating API key for provider {provider}: {e}")
            raise
    
    async def update_key(
        self, 
        db: AsyncSession, 
        provider: Union[ApiProvider, str], 
        update_data: Dict[str, Any]
    ) -> ApiKey:
        """API anahtarını günceller"""
        try:
            # Güncel zamanı ekle
            update_values = {
                "updated_at": datetime.datetime.utcnow(),
                **update_data
            }
            
            # Metadata'yı JSON'a çevir (eğer varsa)
            if "metadata" in update_values:
                update_values["metadata"] = json.dumps(update_values["metadata"]) if update_values["metadata"] else None
            
            # Update
            stmt = update(ApiKeyDB).where(ApiKeyDB.provider == provider).values(**update_values).returning(ApiKeyDB)
            
            result = await db.execute(stmt)
            key_db = result.scalars().first()
            
            if not key_db:
                raise ValueError(f"No API key found for provider: {provider}")
            
            # DB işlemini kaydet
            await db.commit()
            
            # Metadata'yı parse et
            metadata = {}
            if key_db.metadata:
                try:
                    metadata = json.loads(key_db.metadata)
                except:
                    metadata = {}
            
            # Pydantic modeli oluştur
            key = ApiKey(
                id=key_db.id,
                provider=key_db.provider,
                api_key=key_db.api_key,
                description=key_db.description,
                is_active=key_db.is_active,
                metadata=metadata,
                created_at=key_db.created_at,
                updated_at=key_db.updated_at,
                last_used=key_db.last_used
            )
            
            return key
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating API key for provider {provider}: {e}")
            raise
    
    async def delete_key(self, db: AsyncSession, provider: Union[ApiProvider, str]) -> bool:
        """API anahtarını siler"""
        try:
            # Delete
            stmt = delete(ApiKeyDB).where(ApiKeyDB.provider == provider)
            
            result = await db.execute(stmt)
            
            # DB işlemini kaydet
            await db.commit()
            
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting API key for provider {provider}: {e}")
            raise
    
    async def update_last_used(self, db: AsyncSession, provider: Union[ApiProvider, str]) -> bool:
        """API anahtarının son kullanım zamanını günceller"""
        try:
            # Update
            stmt = update(ApiKeyDB).where(ApiKeyDB.provider == provider).values(
                last_used=datetime.datetime.utcnow()
            )
            
            await db.execute(stmt)
            
            # DB işlemini kaydet
            await db.commit()
            
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating last used time for provider {provider}: {e}")
            return False