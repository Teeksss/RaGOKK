# Last reviewed: 2025-04-29 12:51:02 UTC (User: TeeksssCI/CD)
import asyncio
import hashlib
import json
import logging
import time
from typing import Dict, Optional, List, Any, Tuple
from redis.asyncio import Redis

from ..config import settings

logger = logging.getLogger(__name__)

class TranslationCacheService:
    """
    Çeviri sonuçları için önbellekleme servisi.
    
    Özellikler:
    - Redis tabanlı önbellekleme
    - Çoklu dil çiftleri için destek
    - Farklı TTL değerleri (popüler dil çiftleri için daha uzun)
    - Anahtar normalizasyonu
    - Çoklu istek engelleme (aynı çeviri için paralel istekleri engeller)
    - Önbellek istatistikleri
    """
    
    def __init__(self):
        """Redis bağlantısı ve yapılandırma ile servisi başlatır"""
        self._redis_url = settings.REDIS_URL
        self._redis: Optional[Redis] = None
        self._connected = False
        
        # Önbellek ayarları
        self._cache_prefix = "translation:"
        self._in_progress_prefix = "translation_in_progress:"
        self._stats_key = "translation_stats"
        
        # TTL ayarları (saniye)
        self._default_ttl = 60 * 60 * 24 * 7  # 7 gün
        self._popular_ttl = 60 * 60 * 24 * 30  # 30 gün
        
        # Popüler dil çiftleri (daha uzun TTL)
        self._popular_language_pairs = [
            ("en", "tr"), ("tr", "en"),
            ("en", "es"), ("es", "en"),
            ("en", "fr"), ("fr", "en"),
            ("en", "de"), ("de", "en"),
            ("en", "zh"), ("zh", "en"),
            ("en", "ru"), ("ru", "en"),
            ("en", "ar"), ("ar", "en"),
        ]
        
        # Çoklu istek engelleme için kilit
        self._locks = {}
    
    async def connect(self) -> bool:
        """
        Redis bağlantısı kurar
        
        Returns:
            bool: Bağlantı başarılı ise True
        """
        if self._connected and self._redis:
            return True
            
        try:
            self._redis = Redis.from_url(self._redis_url, decode_responses=True)
            # Bağlantıyı test et
            await self._redis.ping()
            self._connected = True
            return True
        except Exception as e:
            logger.error(f"Redis bağlantısı kurulamadı: {e}")
            self._connected = False
            return False
    
    def _get_cache_key(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Çeviri için önbellek anahtarı oluşturur
        
        Args:
            text: Çevrilecek metin
            source_lang: Kaynak dil kodu
            target_lang: Hedef dil kodu
            
        Returns:
            str: Önbellek anahtarı
        """
        # Metni standartlaştır (boşlukları temizle, küçük harfe çevir)
        normalized_text = " ".join(text.strip().lower().split())
        
        # Benzersiz anahtar için hash oluştur
        text_hash = hashlib.md5(normalized_text.encode()).hexdigest()
        
        # Anahtar formatı: "prefix:source_lang:target_lang:hash"
        return f"{self._cache_prefix}{source_lang}:{target_lang}:{text_hash}"
    
    def _get_in_progress_key(self, cache_key: str) -> str:
        """
        Çeviri işlemi devam ederken kullanılacak kilit anahtarı
        
        Args:
            cache_key: Önbellek anahtarı
            
        Returns:
            str: İşlem devam anahtarı
        """
        return f"{self._in_progress_prefix}{cache_key[len(self._cache_prefix):]}"
    
    def _get_ttl(self, source_lang: str, target_lang: str) -> int:
        """
        Dil çiftine göre TTL değeri belirler
        
        Args:
            source_lang: Kaynak dil kodu
            target_lang: Hedef dil kodu
            
        Returns:
            int: TTL değeri (saniye)
        """
        if (source_lang, target_lang) in self._popular_language_pairs:
            return self._popular_ttl
        return self._default_ttl
    
    async def get_cached_translation(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str
    ) -> Optional[Dict[str, Any]]:
        """
        Önbellekten çeviri sonucunu getirir
        
        Args:
            text: Çevrilecek metin
            source_lang: Kaynak dil kodu
            target_lang: Hedef dil kodu
            
        Returns:
            Optional[Dict[str, Any]]: Çeviri sonucu veya None
        """
        if not text or not source_lang or not target_lang:
            return None
            
        # Redis bağlantısı kontrolü
        if not self._connected:
            if not await self.connect():
                return None
        
        # Önbellek anahtarı
        cache_key = self._get_cache_key(text, source_lang, target_lang)
        
        try:
            # Önbellekten getir
            cached_data = await self._redis.get(cache_key)
            
            if cached_data:
                # İstatistikleri güncelle
                await self._increment_stat("hits")
                
                # JSON'dan çevir
                return json.loads(cached_data)
                
            # Devam eden çeviri kontrolü
            in_progress_key = self._get_in_progress_key(cache_key)
            in_progress = await self._redis.exists(in_progress_key)
            
            if in_progress:
                # Bu çeviri için işlem devam ediyor, kısa bir süre bekleyip tekrar dene
                await asyncio.sleep(0.2)
                return await self.get_cached_translation(text, source_lang, target_lang)
            
            # Önbellekte yok
            await self._increment_stat("misses")
            return None
            
        except Exception as e:
            logger.error(f"Çeviri önbelleği okuma hatası: {e}")
            return None
    
    async def cache_translation(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str, 
        result: Dict[str, Any]
    ) -> bool:
        """
        Çeviri sonucunu önbelleğe alır
        
        Args:
            text: Çevrilecek metin
            source_lang: Kaynak dil kodu
            target_lang: Hedef dil kodu
            result: Çeviri sonucu
            
        Returns:
            bool: Başarılı ise True
        """
        if not text or not source_lang or not target_lang or not result:
            return False
            
        # Redis bağlantısı kontrolü
        if not self._connected:
            if not await self.connect():
                return False
        
        # Önbellek anahtarı
        cache_key = self._get_cache_key(text, source_lang, target_lang)
        in_progress_key = self._get_in_progress_key(cache_key)
        
        try:
            # Devam eden işlem olarak işaretle
            await self._redis.set(in_progress_key, "1", ex=30)  # 30 saniye geçerli
            
            # Sonucu JSON'a çevir
            cached_data = json.dumps(result)
            
            # TTL hesapla
            ttl = self._get_ttl(source_lang, target_lang)
            
            # Önbelleğe kaydet
            await self._redis.set(cache_key, cached_data, ex=ttl)
            
            # Devam eden işlem işaretini kaldır
            await self._redis.delete(in_progress_key)
            
            # İstatistikleri güncelle
            await self._increment_stat("stores")
            
            return True
            
        except Exception as e:
            logger.error(f"Çeviri önbelleğe kaydetme hatası: {e}")
            
            # Hata durumunda devam eden işaret temizlenir
            try:
                await self._redis.delete(in_progress_key)
            except:
                pass
                
            return False
    
    async def clear_cache(
        self,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None
    ) -> int:
        """
        Çeviri önbelleğini temizler
        
        Args:
            source_lang: Filtrelenecek kaynak dil (opsiyonel)
            target_lang: Filtrelenecek hedef dil (opsiyonel)
            
        Returns:
            int: Silinen önbellek sayısı
        """
        if not self._connected:
            if not await self.connect():
                return 0
        
        try:
            # Anahtar desenini oluştur
            if source_lang and target_lang:
                pattern = f"{self._cache_prefix}{source_lang}:{target_lang}:*"
            elif source_lang:
                pattern = f"{self._cache_prefix}{source_lang}:*"
            elif target_lang:
                pattern = f"{self._cache_prefix}*:{target_lang}:*"
            else:
                pattern = f"{self._cache_prefix}*"
            
            # Anahtarları bul
            cursor = 0
            deleted_count = 0
            
            while True:
                cursor, keys = await self._redis.scan(cursor, pattern, 100)
                if keys:
                    deleted_count += await self._redis.delete(*keys)
                
                if cursor == 0:
                    break
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Çeviri önbelleği temizleme hatası: {e}")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Önbellek istatistiklerini getirir
        
        Returns:
            Dict[str, Any]: İstatistikler
        """
        if not self._connected:
            if not await self.connect():
                return {}
        
        try:
            # İstatistikleri getir
            stats = await self._redis.hgetall(self._stats_key)
            
            # Değerleri int'e çevir
            stats = {k: int(v) for k, v in stats.items()}
            
            # Tüm istatistikler
            result = {
                "hits": stats.get("hits", 0),
                "misses": stats.get("misses", 0),
                "stores": stats.get("stores", 0),
                "total_requests": stats.get("hits", 0) + stats.get("misses", 0)
            }
            
            # Hit rate hesapla
            total_requests = result["hits"] + result["misses"]
            if total_requests > 0:
                result["hit_rate"] = result["hits"] / total_requests
            else:
                result["hit_rate"] = 0.0
            
            return result
            
        except Exception as e:
            logger.error(f"Çeviri önbelleği istatistikleri okuma hatası: {e}")
            return {}
    
    async def _increment_stat(self, key: str, increment: int = 1) -> bool:
        """
        Belirli bir istatistik değerini artırır
        
        Args:
            key: İstatistik anahtarı
            increment: Artış miktarı
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            await self._redis.hincrby(self._stats_key, key, increment)
            return True
        except Exception:
            return False