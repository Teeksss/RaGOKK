# Last reviewed: 2025-04-29 12:17:43 UTC (User: TeeksssVektör)
from typing import Dict, List, Any, Optional, Tuple, Union, TypeVar, Generic, Callable
import time
import threading
import numpy as np
import pickle
import os
import hashlib
import json
import logging
import asyncio
from dataclasses import dataclass
from collections import OrderedDict
from functools import lru_cache

T = TypeVar('T')

logger = logging.getLogger(__name__)

@dataclass
class CacheStats:
    """Önbellek istatistikleri"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    lookups: int = 0
    inserts: int = 0
    disk_hits: int = 0
    disk_writes: int = 0
    
    @property
    def hit_ratio(self) -> float:
        """İsabet oranı"""
        total = self.hits + self.misses
        if total == 0:
            return 0
        return self.hits / total

class TwoLayerCache(Generic[T]):
    """
    İki katmanlı (bellek + disk) vektör önbellek sistemi.
    - LRU (Least Recently Used) önbellekleme stratejisi
    - TTL desteği
    - Disk tabanlı ikincil önbellek
    - Async/await desteği
    - Veri sıkıştırma
    - Paralel işleme
    """
    
    def __init__(self, 
                 max_memory_items: int = 10000,
                 max_disk_items: int = 100000,
                 ttl: int = 86400,  # 1 gün
                 disk_cache_dir: Optional[str] = None,
                 compress: bool = True,
                 shards: int = 8,
                 key_function: Optional[Callable[[str], str]] = None):
        """
        Args:
            max_memory_items: Bellek önbelleğinde saklanacak maksimum öğe sayısı
            max_disk_items: Disk önbelleğinde saklanacak maksimum öğe sayısı
            ttl: Önbellek süresi (saniye)
            disk_cache_dir: Disk önbelleği dizini (None ise disk önbelleği devre dışı)
            compress: Disk önbelleğinde sıkıştırma kullanılsın mı?
            shards: Önbellek parça sayısı (parçalama ile daha verimli threading)
            key_function: Anahtar dönüştürme fonksiyonu
        """
        self.max_memory_items = max_memory_items
        self.max_disk_items = max_disk_items
        self.ttl = ttl
        self.disk_cache_dir = disk_cache_dir
        self.compress = compress
        self.key_function = key_function or (lambda x: x)
        
        # Çoklu parçalı önbellek (thread-safe)
        self.shards = shards
        self.memory_caches = []
        self.locks = []
        
        # Her parça için ayrı bir önbellek ve kilit
        for _ in range(shards):
            self.memory_caches.append(OrderedDict())
            self.locks.append(threading.RLock())
        
        # Disk önbelleği
        if disk_cache_dir and not os.path.exists(disk_cache_dir):
            os.makedirs(disk_cache_dir, exist_ok=True)
        
        # İstatistikler
        self.stats = CacheStats()
    
    def _get_shard(self, key: str) -> int:
        """Anahtar için parça indeksini döndürür"""
        hash_value = int(hashlib.md5(key.encode()).hexdigest(), 16)
        return hash_value % self.shards
    
    def _get_disk_path(self, key: str) -> str:
        """Anahtar için disk yolunu döndürür"""
        if not self.disk_cache_dir:
            return None
        
        # Anahtar karması ile alt klasör oluştur (çok sayıda dosya için)
        hash_hex = hashlib.md5(key.encode()).hexdigest()
        subdir = os.path.join(self.disk_cache_dir, hash_hex[:2])
        
        if not os.path.exists(subdir):
            os.makedirs(subdir, exist_ok=True)
            
        return os.path.join(subdir, f"{hash_hex}.cache")
    
    async def get(self, key: str) -> Optional[T]:
        """Önbellekten değer alır"""
        normalized_key = self.key_function(key)
        shard = self._get_shard(normalized_key)
        
        self.stats.lookups += 1
        
        # Bellek önbelleğinde ara
        with self.locks[shard]:
            if normalized_key in self.memory_caches[shard]:
                cache_item = self.memory_caches[shard][normalized_key]
                timestamp, value = cache_item
                
                # TTL kontrolü
                if time.time() - timestamp < self.ttl:
                    # LRU güncellemesi: Öğeyi listenin sonuna taşı
                    self.memory_caches[shard].move_to_end(normalized_key)
                    self.stats.hits += 1
                    return value
                else:
                    # Süresi dolmuş, kaldır
                    del self.memory_caches[shard][normalized_key]
        
        # Disk önbelleğinde ara (eğer etkinse)
        if self.disk_cache_dir:
            disk_path = self._get_disk_path(normalized_key)
            
            if os.path.exists(disk_path):
                try:
                    # Disk önbelleğinden oku (non-blocking I/O)
                    loop = asyncio.get_event_loop()
                    cache_data = await loop.run_in_executor(None, self._read_disk_cache, disk_path)
                    
                    if cache_data and isinstance(cache_data, tuple) and len(cache_data) == 2:
                        timestamp, value = cache_data
                        
                        # TTL kontrolü
                        if time.time() - timestamp < self.ttl:
                            # Önbelleğe alınan değeri bellek önbelleğine taşı
                            await self.set(key, value, from_disk=True)
                            self.stats.disk_hits += 1
                            return value
                        else:
                            # Süresi dolmuş, disk dosyasını sil
                            await loop.run_in_executor(None, lambda: os.remove(disk_path))
                except Exception as e:
                    logger.warning(f"Disk önbelleği okuma hatası: {e}")
        
        # Bulunamadı
        self.stats.misses += 1
        return None
    
    async def set(self, key: str, value: T, from_disk: bool = False) -> bool:
        """Önbelleğe değer ekler"""
        normalized_key = self.key_function(key)
        shard = self._get_shard(normalized_key)
        
        self.stats.inserts += 1
        
        # Bellek önbelleğine ekle
        with self.locks[shard]:
            # Mevcut önbellek boyutu kontrol et
            if len(self.memory_caches[shard]) >= self.max_memory_items // self.shards:
                # En eski öğeyi çıkar
                try:
                    oldest_key, oldest_item = next(iter(self.memory_caches[shard].items()))
                    
                    # Önbellekten çıkarılan öğeyi diske yaz
                    if self.disk_cache_dir and not from_disk:
                        disk_path = self._get_disk_path(oldest_key)
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(
                            None, 
                            self._write_disk_cache,
                            disk_path, 
                            oldest_item
                        )
                        
                    # Önbellekten çıkar
                    del self.memory_caches[shard][oldest_key]
                    self.stats.evictions += 1
                except (StopIteration, RuntimeError):
                    pass
            
            # Yeni değeri ekle
            self.memory_caches[shard][normalized_key] = (time.time(), value)
            self.stats.size = sum(len(cache) for cache in self.memory_caches)
            
            return True
    
    def _read_disk_cache(self, path: str) -> Tuple[float, T]:
        """Disk önbelleğinden okur"""
        try:
            with open(path, 'rb') as f:
                if self.compress:
                    import gzip
                    with gzip.GzipFile(fileobj=f) as gz:
                        return pickle.load(gz)
                else:
                    return pickle.load(f)
        except Exception as e:
            logger.warning(f"Disk önbelleği okuma hatası: {path} - {e}")
            return None
    
    def _write_disk_cache(self, path: str, cache_item: Tuple[float, T]) -> None:
        """Disk önbelleğine yazar"""
        try:
            with open(path, 'wb') as f:
                if self.compress:
                    import gzip
                    with gzip.GzipFile(fileobj=f, mode='wb') as gz:
                        pickle.dump(cache_item, gz)
                else:
                    pickle.dump(cache_item, f)
                    
            self.stats.disk_writes += 1
            
            # Disk önbellek boyutunu kontrol et (ayrı bir thread'de)
            if self.stats.disk_writes % 100 == 0:  # Her 100 yazımda bir
                threading.Thread(target=self._check_disk_cache_size).start()
                
        except Exception as e:
            logger.warning(f"Disk önbelleği yazma hatası: {path} - {e}")
    
    def _check_disk_cache_size(self) -> None:
        """Disk önbellek boyutunu kontrol eder ve gerekirse eski öğeleri temizler"""
        if not self.disk_cache_dir or not os.path.exists(self.disk_cache_dir):
            return
            
        try:
            # Tüm önbellek dosyalarını bul
            cache_files = []
            for root, _, files in os.walk(self.disk_cache_dir):
                for file in files:
                    if file.endswith('.cache'):
                        full_path = os.path.join(root, file)
                        mtime = os.path.getmtime(full_path)
                        cache_files.append((full_path, mtime))
            
            # Dosya sayısı kontrolü
            if len(cache_files) > self.max_disk_items:
                # En eski dosyaları sil
                cache_files.sort(key=lambda x: x[1])  # mtime'a göre sırala
                files_to_delete = cache_files[:len(cache_files) - self.max_disk_items]
                
                for file_path, _ in files_to_delete:
                    try:
                        os.remove(file_path)
                    except:
                        pass
        except Exception as e:
            logger.warning(f"Disk önbellek boyutu kontrolü hatası: {e}")
    
    async def clear(self) -> None:
        """Tüm önbelleği temizler"""
        # Bellek önbelleğini temizle
        for i in range(self.shards):
            with self.locks[i]:
                self.memory_caches[i].clear()
        
        # Disk önbelleğini temizle (eğer etkinse)
        if self.disk_cache_dir and os.path.exists(self.disk_cache_dir):
            loop = asyncio.get_event_loop()
            
            # Asenkron temizlik için executor kullan
            def clear_disk_cache():
                for root, _, files in os.walk(self.disk_cache_dir):
                    for file in files:
                        if file.endswith('.cache'):
                            try:
                                os.remove(os.path.join(root, file))
                            except:
                                pass
            
            await loop.run_in_executor(None, clear_disk_cache)
        
        # İstatistikleri sıfırla
        self.stats = CacheStats()
    
    def get_stats(self) -> Dict[str, Any]:
        """Önbellek istatistiklerini döndürür"""
        return {
            "memory_size": self.stats.size,
            "max_memory_size": self.max_memory_items,
            "hits": self.stats.hits,
            "misses": self.stats.misses,
            "lookups": self.stats.lookups,
            "hit_ratio": self.stats.hit_ratio,
            "inserts": self.stats.inserts,
            "evictions": self.stats.evictions,
            "disk_hits": self.stats.disk_hits,
            "disk_writes": self.stats.disk_writes,
            "disk_cache_enabled": bool(self.disk_cache_dir),
            "ttl": self.ttl,
            "shards": self.shards
        }


class OptimizedVectorCache:
    """
    Optimized vector cache with:
    - Numpy array storage
    - Faster similarity calculations
    - Memory efficient storage
    - Distance-based neighbor caching
    """
    
    def __init__(self, 
                 dimension: int,
                 max_memory_items: int = 10000,
                 max_disk_items: int = 100000,
                 ttl: int = 86400,
                 disk_cache_dir: Optional[str] = None,
                 similarity_threshold: float = 0.85):
        """
        Args:
            dimension: Vector dimension
            max_memory_items: Maximum number of items in memory cache
            max_disk_items: Maximum number of items in disk cache
            ttl: Cache TTL in seconds
            disk_cache_dir: Disk cache directory
            similarity_threshold: Threshold for adding similar vectors to cache
        """
        # Base cache
        self.cache = TwoLayerCache(
            max_memory_items=max_memory_items,
            max_disk_items=max_disk_items,
            ttl=ttl,
            disk_cache_dir=disk_cache_dir,
            # Use hash of the stringified vector as key to avoid floating point issues
            key_function=lambda key: hashlib.md5(str(key).encode()).hexdigest()
        )
        
        self.dimension = dimension
        self.similarity_threshold = similarity_threshold
        
        # For accelerating vector similarity search
        self._vector_matrix = np.zeros((max_memory_items, dimension), dtype=np.float32)
        self._vector_ids = []
        self._current_size = 0
        self._lock = threading.RLock()
    
    async def get(self, query: str, vector: List[float]) -> Optional[List[float]]:
        """Get vector from cache"""
        # Try exact match first
        cached_vector = await self.cache.get(query)
        if cached_vector is not None:
            return cached_vector
        
        # If no exact match, try similarity search
        if len(vector) == self.dimension:
            await self._find_similar(vector, query)
            
        return None
    
    async def _find_similar(self, vector: List[float], query: str) -> Optional[List[float]]:
        """Find similar vectors in memory"""
        if self._current_size == 0:
            return None
            
        with self._lock:
            # Convert input to numpy array for efficient calculation
            query_vec = np.array(vector, dtype=np.float32)
            
            # Calculate dot product with all vectors in memory
            # (assuming vectors are normalized, this is equivalent to cosine similarity)
            if self._current_size > 0:
                similarities = np.dot(self._vector_matrix[:self._current_size], query_vec)
                
                # Find most similar vector above threshold
                max_idx = np.argmax(similarities)
                if similarities[max_idx] >= self.similarity_threshold:
                    # Get the vector ID
                    vector_id = self._vector_ids[max_idx]
                    
                    # Get the actual vector from cache
                    return await self.cache.get(vector_id)
                    
        return None
    
    async def set(self, query: str, vector: List[float]) -> bool:
        """Add vector to cache"""
        # Store normalized vector
        vec_array = np.array(vector, dtype=np.float32)
        norm = np.linalg.norm(vec_array)
        if norm > 0:
            vec_array = vec_array / norm
            
        # Store in base cache
        await self.cache.set(query, vector)
        
        # Update in-memory matrix for similarity search
        with self._lock:
            if self._current_size < len(self._vector_ids):
                # Add to existing array
                self._vector_matrix[self._current_size] = vec_array
                self._vector_ids.append(query)
                self._current_size += 1
            else:
                # Need to evict
                if self._current_size > 0:
                    # Simple FIFO replacement
                    self._vector_matrix = np.roll(self._vector_matrix, -1, axis=0)
                    self._vector_matrix[-1] = vec_array
                    self._vector_ids.pop(0)
                    self._vector_ids.append(query)
                else:
                    # First insertion
                    self._vector_matrix[0] = vec_array
                    self._vector_ids.append(query)
                    self._current_size = 1
                    
        return True
    
    async def clear(self) -> None:
        """Clear cache"""
        await self.cache.clear()
        
        with self._lock:
            self._vector_matrix = np.zeros((len(self._vector_matrix), self.dimension), dtype=np.float32)
            self._vector_ids = []
            self._current_size = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = self.cache.get_stats()
        stats.update({
            "dimension": self.dimension,
            "similarity_threshold": self.similarity_threshold,
            "vector_matrix_size": self._current_size
        })
        return stats