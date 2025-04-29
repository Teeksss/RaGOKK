# Last reviewed: 2025-04-29 13:59:34 UTC (User: TeeksssAPI)
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union, Tuple
import asyncio
import aioredis
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db.session import get_db, engine
from ..models.quota import QuotaType, UsageMetric
from ..repositories.quota_repository import QuotaRepository
from ..repositories.organization_repository import OrganizationRepository

logger = logging.getLogger(__name__)

class QuotaExceededError(Exception):
    """Kota aşıldığında fırlatılır"""
    pass

class QuotaService:
    """
    Kullanım kotaları ve raporlama servisi
    
    Bu servis şunları sağlar:
    - Organizasyon ve kullanıcı bazında kota tanımlama ve yönetme
    - Kullanım takibi ve raporlama
    - Kota limitlerine yaklaşıldığında uyarı bildirimleri
    - Kota aşım durumlarında eylem kontrolü
    """
    
    def __init__(self):
        """Kota servisi başlat"""
        self.quota_repository = QuotaRepository()
        self.organization_repository = OrganizationRepository()
        
        # Önbellek
        self.redis = None
        self.cache_ttl = 300  # 5 dakika
        self.quota_check_cache_ttl = 60  # 1 dakika
        
        # Varsayılan yapılandırma
        self.quota_defaults = {
            QuotaType.STORAGE: 5 * 1024 * 1024 * 1024,  # 5 GB
            QuotaType.DOCUMENTS: 1000,  # 1000 belge
            QuotaType.SEARCH_QUERIES: 10000,  # 10000 arama sorgusu
            QuotaType.API_CALLS: 50000,  # 50000 API çağrısı
            QuotaType.USERS: 10,  # 10 kullanıcı
            QuotaType.INTEGRATIONS: 5,  # 5 entegrasyon
        }
        
        # Rate limiting için anahtar oluşturma
        self.key_patterns = {
            QuotaType.API_CALLS: "quota:api:{org_id}:{timeframe}",
            QuotaType.SEARCH_QUERIES: "quota:search:{org_id}:{timeframe}"
        }
    
    async def connect(self):
        """Redis bağlantısı oluştur"""
        if settings.REDIS_URL:
            try:
                self.redis = aioredis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True
                )
                logger.info("Quota service connected to Redis")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {str(e)}")
    
    async def disconnect(self):
        """Redis bağlantısını kapat"""
        if self.redis:
            await self.redis.close()
            logger.info("Quota service disconnected from Redis")
    
    async def get_quota(
        self,
        organization_id: str,
        quota_type: QuotaType,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Belirtilen organizasyon ve tip için kotayı al
        
        Args:
            organization_id: Organizasyon kimliği
            quota_type: Kota türü
            db: Veritabanı oturumu (opsiyonel)
            
        Returns:
            Dict[str, Any]: Kota bilgileri (limit ve kullanım)
        """
        # Önbellekten kontrol et
        if self.redis:
            cache_key = f"quota:{organization_id}:{quota_type.value}"
            cached = await self.redis.get(cache_key)
            if cached:
                try:
                    return json.loads(cached)
                except json.JSONDecodeError:
                    pass
        
        # Veritabanından al
        own_session = db is None
        try:
            if own_session:
                async with AsyncSession(engine) as db:
                    quota = await self.quota_repository.get_quota(
                        db=db,
                        organization_id=organization_id,
                        quota_type=quota_type
                    )
                    
                    if not quota:
                        # Varsayılan kotayı kullan
                        quota = {
                            "limit": self.quota_defaults.get(quota_type, 0),
                            "current_usage": await self.get_current_usage(
                                db=db,
                                organization_id=organization_id,
                                quota_type=quota_type
                            ),
                            "reset_date": None,
                            "is_default": True
                        }
            else:
                quota = await self.quota_repository.get_quota(
                    db=db,
                    organization_id=organization_id,
                    quota_type=quota_type
                )
                
                if not quota:
                    # Varsayılan kotayı kullan
                    quota = {
                        "limit": self.quota_defaults.get(quota_type, 0),
                        "current_usage": await self.get_current_usage(
                            db=db,
                            organization_id=organization_id,
                            quota_type=quota_type
                        ),
                        "reset_date": None,
                        "is_default": True
                    }
            
            # Önbelleğe al
            if self.redis:
                await self.redis.set(
                    cache_key,
                    json.dumps(quota),
                    ex=self.cache_ttl
                )
            
            return quota
        
        except Exception as e:
            logger.error(f"Error getting quota: {str(e)}")
            
            # Varsayılan kotayı döndür
            return {
                "limit": self.quota_defaults.get(quota_type, 0),