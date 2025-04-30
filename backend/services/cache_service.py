# Last reviewed: 2025-04-29 14:43:27 UTC (User: Teeksss)
import logging
import json
import pickle
import hashlib
from typing import Dict, Any, List, Optional, Union, TypeVar, Generic, Callable
import asyncio
from datetime import datetime, timedelta

from redis.asyncio import Redis
from redis.exceptions import RedisError

from ..config import settings

logger = logging.getLogger(__name__)

# Generic tip tanımı
T = TypeVar('T')

class CacheService(Generic[T]):
    """
    Generic önbellek servisi
    
    Bu servis şunları sağlar:
    - Redis önbelleği ile hızlı veri erişimi
    - Çeşitli veri tipleri desteği (JSON serileştirilebilir, pickle nesneleri)
    - Anahtar bazlı ve sorgu bazlı önbellek
    - TTL (time-to-live) desteği
    - Grup bazlı önbellek silme
    """
    
    def __init__(
        self,
        prefix: str,
        default_ttl: int = 3600,
        serialize_fn: Optional[Callable[[T], bytes]] = None,
        deserialize_fn: Optional[Callable[[bytes], T]] = None,
        max_pool_size: int = 10
    ):
        """Cache servisi başlatma"""
        self.redis_client: Optional[Redis] = None
        self.prefix = prefix
        self.default_ttl = default_ttl
        self.serialize_fn = serialize_fn or self._default_serialize
        self.deserialize_fn = deserialize_fn or self._default_deserialize
        self.max_pool_size = max_pool_size
        
        # Otomatik bağlantı 
        asyncio.create_task(self.connect())
    
    async def connect(self) -> bool:
        """Redis bağlantısını oluştur"""
        if not settings.REDIS_URL:
            logger.warning(f"Redis URL not configured, cache service {self.prefix} will not be available")
            return False
            
        try:
            self.redis_client = Redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=False,  # Raw bytes döndür, deserialize_fn kullanacağız
                max_connections=self.max_pool_size
            )
            
            # Bağlantıyı test et
            await self.redis_client.ping()
            logger.info(f"Cache service {self.prefix} connected to Redis")
            return True
            
        except RedisError as e:
            logger.error(f"Failed to connect to Redis for cache service {self.prefix}: {str(e)}")
            self.redis_client = None
            return False
    
    async def disconnect(self) -> None:
        """Redis bağlantısını kapat"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info(f"Cache service {self.prefix} disconnected from Redis")
            self.redis_client = None
    
    def _default_serialize(self, data: T) -> bytes:
        """
        Varsayılan veri serileştirme (JSON veya pickle)
        
        Args:
            data: Serileştirilecek veri
            
        Returns:
            bytes: Serileştirilmiş veri
        """
        try:
            # Önce JSON kullanmayı dene (daha hızlı)
            serialized = json.dumps(data).encode('utf-8')
            return b'json:' + serialized
        except (TypeError, ValueError, OverflowError):
            # JSON başarısız olursa pickle kullan
            try:
                serialized = pickle.dumps(data)
                return b'pickle:' + serialized
            except Exception as e:
                logger.error(f"Serialization error: {str(e)}")
                raise
    
    def _default_deserialize(self, data: bytes) -> T:
        """
        Varsayılan veri deserileştirme
        
        Args:
            data: Deserileştirilecek veri
            
        Returns:
            T: Deserileştirilmiş veri
        """
        if not data:
            return None
            
        try:
            # Serialization tipini belirle
            if data.startswith(b'json:'):
                return json.loads(data[5:].decode('utf-8'))
            elif data.startswith(b'pickle:'):
                return pickle.loads(data[7:])
            else:
                # Eski tip veri, direkt pickle dene
                return pickle.loads(data)
        except Exception as e:
            logger.error(f"Deserialization error: {str(e)}")
            return None
    
    def _build_key(self, key: str) -> str:
        """
        Önbellek anahtarı oluştur
        
        Args:
            key: Ana anahtar
            
        Returns:
            str: Önekli anahtar
        """
        return f"{self.prefix}:{key}"
    
    def _build_query_key(self, params: Dict[str, Any]) -> str:
        """
        Sorgu parametrelerinden anahtar oluştur
        
        Args:
            params: Sorgu parametreleri
            
        Returns:
            str: Hash anahtarı
        """
        # Parametreleri sırala ve serialize et
        param_str = json.dumps(params, sort_keys=True)
        
        # MD5 hash oluştur
        hash_key = hashlib.md5(param_str.encode('utf-8')).hexdigest()
        
        return f"query:{hash_key}"
    
    async def get(self, key: str) -> Optional[T]:
        """
        Önbellekten veri al
        
        Args:
            key: Veri anahtarı
            
        Returns:
            Optional[T]: Önbellek verisi veya None
        """
        if not self.redis_client:
            return None
            
        try:
            cache_key = self._build_key(key)
            data = await self.redis_client.get(cache_key)
            
            if data:
                return self.deserialize_fn(data)
            return None
            
        except RedisError as e:
            logger.warning(f"Redis get error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Cache get error: {str(e)}")
            return None
    
    async def set(
        self,
        key: str,
        value: T,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Önbelleğe veri ekle
        
        Args:
            key: Veri anahtarı
            value: Veri
            ttl: Süre (saniye)
            
        Returns:
            bool: Başarılı ise True
        """
        if not self.redis_client:
            return False
            
        try:
            cache_key = self._build_key(key)
            data = self.serialize_fn(value)
            
            ttl = ttl if ttl is not None else self.default_ttl
            
            if ttl > 0:
                await self.redis_client.setex(cache_key, ttl, data)
            else:
                await self.redis_client.set(cache_key, data)
                
            return True
            
        except RedisError as e:
            logger.warning(f"Redis set error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Cache set error: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Önbellekten veri sil
        
        Args:
            key: Veri anahtarı
            
        Returns:
            bool: Başarılı ise True
        """
        if not self.redis_client:
            return False
            
        try:
            cache_key = self._build_key(key)
            return await self.redis_client.delete(cache_key) > 0
            
        except RedisError as e:
            logger.warning(f"Redis delete error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Cache delete error: {str(e)}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Anahtar varlığını kontrol et
        
        Args:
            key: Veri anahtarı
            
        Returns:
            bool: Anahar varsa True
        """
        if not self.redis_client:
            return False
            
        try:
            cache_key = self._build_key(key)
            return await self.redis_client.exists(cache_key) > 0
            
        except RedisError as e:
            logger.warning(f"Redis exists error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Cache exists error: {str(e)}")
            return False
    
    async def get_or_set(
        self,
        key: str,
        callable_fn: Callable[[], Union[T, asyncio.coroutine]],
        ttl: Optional[int] = None
    ) -> T:
        """
        Önbellekten veri al, yoksa oluştur ve kaydet
        
        Args:
            key: Veri anahtarı
            callable_fn: Veri oluşturma fonksiyonu
            ttl: Süre (saniye)
            
        Returns:
            T: Veri
        """
        # Önbellekten veriyi al
        cached_data = await self.get(key)
        if cached_data is not None:
            return cached_data
            
        # Veriyi oluştur
        if asyncio.iscoroutinefunction(callable_fn):
            data = await callable_fn()
        else:
            data = callable_fn()
            
        # Önbelleğe kaydet
        await self.set(key, data, ttl)
        
        return data
    
    async def get_by_query(
        self,
        params: Dict[str, Any]
    ) -> Optional[T]:
        """
        Sorgu parametrelerine göre önbellekten veri al
        
        Args:
            params: Sorgu parametreleri
            
        Returns:
            Optional[T]: Önbellek verisi veya None
        """
        query_key = self._build_query_key(params)
        return await self.get(query_key)
    
    async def set_by_query(
        self,
        params: Dict[str, Any],
        value: T,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Sorgu parametrelerine göre önbelleğe veri ekle
        
        Args:
            params: Sorgu parametreleri
            value: Veri
            ttl: Süre (saniye)
            
        Returns:
            bool: Başarılı ise True
        """
        query_key = self._build_query_key(params)
        return await self.set(query_key, value, ttl)
    
    async def get_or_set_by_query(
        self,
        params: Dict[str, Any],
        callable_fn: Callable[[], Union[T, asyncio.coroutine]],
        ttl: Optional[int] = None
    ) -> T:
        """
        Sorgu parametrelerine göre önbellekten veri al, yoksa oluştur ve kaydet
        
        Args:
            params: Sorgu parametreleri
            callable_fn: Veri oluşturma fonksiyonu
            ttl: Süre (saniye)
            
        Returns:
            T: Veri
        """
        query_key = self._build_query_key(params)
        return await self.get_or_set(query_key, callable_fn, ttl)
    
    async def flush_group(self, group_prefix: str) -> int:
        """
        Grup anahtarlarını sil
        
        Args:
            group_prefix: Grup öneki
            
        Returns:
            int: Silinen anahtar sayısı
        """
        if not self.redis_client:
            return 0
            
        try:
            full_prefix = self._build_key(group_prefix)
            
            # Anahtarları bul
            cursor = 0
            count = 0
            
            while True:
                cursor, keys = await self.redis_client.scan(cursor, f"{full_prefix}*", 100)
                
                if keys:
                    count += await self.redis_client.delete(*keys)
                
                if cursor == 0:
                    break
            
            return count
            
        except RedisError as e:
            logger.warning(f"Redis flush group error: {str(e)}")
            return 0
        except Exception as e:
            logger.error(f"Cache flush group error: {str(e)}")
            return 0
    
    async def set_many(self, items: Dict[str, T], ttl: Optional[int] = None) -> int:
        """
        Çoklu veri ekle
        
        Args:
            items: Anahtar-değer çiftleri
            ttl: Süre (saniye)
            
        Returns:
            int: Eklenen anahtar sayısı
        """
        if not self.redis_client or not items:
            return 0
            
        try:
            pipeline = self.redis_client.pipeline()
            ttl = ttl if ttl is not None else self.default_ttl
            
            for key, value in items.items():
                cache_key = self._build_key(key)
                data = self.serialize_fn(value)
                
                if ttl > 0:
                    pipeline.setex(cache_key, ttl, data)
                else:
                    pipeline.set(cache_key, data)
            
            results = await pipeline.execute()
            return sum(1 for r in results if r)
            
        except RedisError as e:
            logger.warning(f"Redis set_many error: {str(e)}")
            return 0
        except Exception as e:
            logger.error(f"Cache set_many error: {str(e)}")
            return 0
    
    async def get_many(self, keys: List[str]) -> Dict[str, T]:
        """
        Çoklu veri al
        
        Args:
            keys: Anahtar listesi
            
        Returns:
            Dict[str, T]: Anahtar-değer çiftleri
        """
        if not self.redis_client or not keys:
            return {}
            
        try:
            cache_keys = [self._build_key(key) for key in keys]
            values = await self.redis_client.mget(cache_keys)
            
            result = {}
            for key, value in zip(keys, values):
                if value:
                    result[key] = self.deserialize_fn(value)
            
            return result
            
        except RedisError as e:
            logger.warning(f"Redis get_many error: {str(e)}")
            return {}
        except Exception as e:
            logger.error(f"Cache get_many error: {str(e)}")
            return {}
    
    async def delete_many(self, keys: List[str]) -> int:
        """
        Çoklu veri sil
        
        Args:
            keys: Anahtar listesi
            
        Returns:
            int: Silinen anahtar sayısı
        """
        if not self.redis_client or not keys:
            return 0
            
        try:
            cache_keys = [self._build_key(key) for key in keys]
            return await self.redis_client.delete(*cache_keys)
            
        except RedisError as e:
            logger.warning(f"Redis delete_many error: {str(e)}")
            return 0
        except Exception as e:
            logger.error(f"Cache delete_many error: {str(e)}")
            return 0
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Sayısal değeri artır
        
        Args:
            key: Anahtar
            amount: Artış miktarı
            
        Returns:
            Optional[int]: Yeni değer veya None
        """
        if not self.redis_client:
            return None
            
        try:
            cache_key = self._build_key(key)
            return await self.redis_client.incrby(cache_key, amount)
            
        except RedisError as e:
            logger.warning(f"Redis increment error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Cache increment error: {str(e)}")
            return None
    
    async def clear_all(self) -> bool:
        """
        Tüm önbellek anahtarlarını sil
        
        Returns:
            bool: Başarılı ise True
        """
        return await self.flush_group("") > 0