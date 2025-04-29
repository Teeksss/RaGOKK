# Last reviewed: 2025-04-29 11:55:43 UTC (User: TeeksssTespit Edilen Eksiklikleri tamamla)
from typing import Dict, List, Any, Optional, Tuple, Union
import os
import json
import time
import asyncio
import numpy as np
import logging
from abc import ABC, abstractmethod
import requests
from datetime import datetime, timedelta
import hashlib
import base64

# Veritabanı bağlantıları için gerekli importlar
import elasticsearch
try:
    import weaviate
    WEAVIATE_AVAILABLE = True
except ImportError:
    WEAVIATE_AVAILABLE = False
    
try:
    import pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    
try:
    from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
    MILVUS_AVAILABLE = True
except ImportError:
    MILVUS_AVAILABLE = False

from ..utils.logger import get_logger

logger = get_logger(__name__)

# Vektör önbellek sınıfı
class VectorCache:
    """Embedding vektörlerini önbellekte saklayan sınıf"""
    
    def __init__(self, max_size: int = 10000, ttl: int = 86400):
        """
        Args:
            max_size: Önbellekte saklanacak maksimum öğe sayısı
            ttl: Önbellek süresi (saniye)
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache = {}
        self._last_cleanup = time.time()
    
    def get(self, key: str) -> Optional[List[float]]:
        """Önbellekten vektör al"""
        if key in self.cache:
            item = self.cache[key]
            # TTL kontrolü
            if time.time() - item['timestamp'] < self.ttl:
                return item['vector']
            else:
                # Süresi dolmuş, sil
                del self.cache[key]
        return None
    
    def set(self, key: str, vector: List[float]) -> None:
        """Önbelleğe vektör ekle"""
        # Önbellek temizliği (her 1000 ekleme işleminden sonra)
        if len(self.cache) >= self.max_size:
            self._cleanup()
            
        self.cache[key] = {
            'vector': vector,
            'timestamp': time.time()
        }
    
    def _cleanup(self) -> None:
        """Süresi dolmuş öğeleri temizle"""
        # Son temizlikten beri 5 dakikadan az zaman geçtiyse atla
        if time.time() - self._last_cleanup < 300:
            return
            
        now = time.time()
        self._last_cleanup = now
        
        # Süresi dolmuş öğeleri temizle
        expired_keys = [k for k, v in self.cache.items() if now - v['timestamp'] >= self.ttl]
        for key in expired_keys:
            del self.cache[key]
            
        # Hala çok fazla öğe varsa, en eskileri sil
        if len(self.cache) >= self.max_size:
            sorted_items = sorted(self.cache.items(), key=lambda x: x[1]['timestamp'])
            # İlk %20'yi sil
            items_to_remove = int(len(sorted_items) * 0.2)
            for i in range(items_to_remove):
                del self.cache[sorted_items[i][0]]
    
    def clear(self) -> None:
        """Tüm önbelleği temizle"""
        self.cache.clear()
    
    def info(self) -> Dict[str, Any]:
        """Önbellek istatistiklerini döndür"""
        now = time.time()
        active_items = len([k for k, v in self.cache.items() if now - v['timestamp'] < self.ttl])
        
        return {
            'total_items': len(self.cache),
            'active_items': active_items,
            'expired_items': len(self.cache) - active_items,
            'max_size': self.max_size,
            'ttl': self.ttl,
            'last_cleanup': datetime.fromtimestamp(self._last_cleanup).isoformat()
        }


# Rate limiting için simple token bucket
class RateLimiter:
    """API istekleri için hız sınırlama"""
    
    def __init__(self, rate: int, per: int = 60, max_tokens: Optional[int] = None):
        """
        Args:
            rate: Belirtilen sürede izin verilen maksimum istek sayısı
            per: Süre (saniye)
            max_tokens: Maksimum token sayısı (belirtilmezse rate ile aynı olur)
        """
        self.rate = rate
        self.per = per
        self.max_tokens = max_tokens or rate
        self.tokens = self.max_tokens
        self.last_update = time.time()
    
    async def acquire(self, tokens: int = 1) -> bool:
        """Token alır, yeterli token yoksa False döner"""
        self._update_tokens()
        
        if tokens <= self.tokens:
            self.tokens -= tokens
            return True
        
        # Yeterli token yok, bekleme süresi hesapla
        wait_time = (tokens - self.tokens) * self.per / self.rate
        
        # 5 saniyeden fazla beklemeyi önermiyoruz
        if wait_time <= 5:
            await asyncio.sleep(wait_time)
            self._update_tokens()
            if tokens <= self.tokens:
                self.tokens -= tokens
                return True
                
        return False
    
    def _update_tokens(self) -> None:
        """Token sayısını günceller"""
        now = time.time()
        elapsed = now - self.last_update
        
        # Geçen süreye göre token ekle
        new_tokens = elapsed * (self.rate / self.per)
        self.tokens = min(self.max_tokens, self.tokens + new_tokens)
        self.last_update = now


class VectorDBClient(ABC):
    """Vektör veritabanları için soyut temel sınıf"""
    
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self.vector_cache = VectorCache()
    
    @abstractmethod
    async def connect(self) -> bool:
        """Veritabanına bağlanır"""
        pass
    
    @abstractmethod
    async def create_collection(self, dimension: int) -> bool:
        """Koleksiyon oluşturur"""
        pass
    
    @abstractmethod
    async def delete_collection(self) -> bool:
        """Koleksiyonu siler"""
        pass
    
    @abstractmethod
    async def insert(self, id: str, vector: List[float], metadata: Dict[str, Any]) -> bool:
        """Vektör ekler"""
        pass
    
    @abstractmethod
    async def search(self, vector: List[float], top_k: int = 10, filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Vektör arar"""
        pass
    
    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Vektörü siler"""
        pass
    
    @abstractmethod
    async def get(self, id: str) -> Optional[Dict[str, Any]]:
        """ID'ye göre vektör ve metadata getirir"""
        pass
    
    @abstractmethod
    async def count(self) -> int:
        """Vektör sayısını döndürür"""
        pass


class ElasticsearchVectorClient(VectorDBClient):
    """Elasticsearch vektör veritabanı istemcisi"""
    
    def __init__(self, collection_name: str, hosts: List[str], index_name: Optional[str] = None, **kwargs):
        super().__init__(collection_name)
        self.hosts = hosts
        self.index_name = index_name or collection_name.lower()
        self.es_kwargs = kwargs
        self.client = None
        self.is_connected = False
        
        # Rate limiter - varsayılan olarak saniyede 10 istek
        self.rate_limiter = RateLimiter(rate=10, per=1)
    
    async def connect(self) -> bool:
        """Elasticsearch'e bağlanır"""
        try:
            # Elasticsearch client'ı asenkron değil, bu yüzden thread pool'da çalıştır
            self.client = elasticsearch.Elasticsearch(
                hosts=self.hosts,
                **self.es_kwargs
            )
            
            # Bağlantıyı doğrula
            info = await asyncio.to_thread(self.client.info)
            self.is_connected = True
            logger.info(f"Elasticsearch bağlantısı başarılı: {info['version']['number']}")
            return True
            
        except Exception as e:
            logger.error(f"Elasticsearch bağlantı hatası: {e}")
            self.is_connected = False
            return False
    
    async def create_collection(self, dimension: int) -> bool:
        """Elasticsearch indeksi oluşturur"""
        if not self.is_connected:
            await self.connect()
            
        try:
            # İndeks zaten var mı kontrol et
            index_exists = await asyncio.to_thread(self.client.indices.exists, index=self.index_name)
            if index_exists:
                logger.info(f"İndeks zaten mevcut: {self.index_name}")
                return True
                
            # İndeks ayarları ve mapping
            settings = {
                "number_of_shards": 3,
                "number_of_replicas": 1,
                "refresh_interval": "1s",
                "analysis": {
                    "analyzer": {
                        "default": {
                            "type": "standard",
                            "stopwords": "_none_"
                        }
                    }
                }
            }
            
            mappings = {
                "properties": {
                    "id": {"type": "keyword"},
                    "vector": {
                        "type": "dense_vector",
                        "dims": dimension,
                        "index": True,
                        "similarity": "cosine"
                    },
                    "content": {"type": "text"},
                    "metadata": {"type": "object"},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"}
                }
            }
            
            # Rate limiting uygula
            await self.rate_limiter.acquire()
            
            # İndeks oluştur
            await asyncio.to_thread(
                self.client.indices.create,
                index=self.index_name,
                body={"settings": settings, "mappings": mappings}
            )
            
            logger.info(f"Elasticsearch indeksi oluşturuldu: {self.index_name}")
            return True
            
        except Exception as e:
            logger.error(f"Elasticsearch indeksi oluşturma hatası: {e}")
            return False
    
    async def delete_collection(self) -> bool:
        """Elasticsearch indeksini siler"""
        if not self.is_connected:
            await self.connect()
            
        try:
            # Rate limiting uygula
            await self.rate_limiter.acquire()
            
            # İndeks sil
            await asyncio.to_thread(self.client.indices.delete, index=self.index_name)
            logger.info(f"Elasticsearch indeksi silindi: {self.index_name}")
            return True
            
        except Exception as e:
            logger.error(f"Elasticsearch indeksi silme hatası: {e}")
            return False
    
    async def insert(self, id: str, vector: List[float], metadata: Dict[str, Any]) -> bool:
        """Vektör ekler"""
        if not self.is_connected:
            await self.connect()
            
        try:
            # Rate limiting uygula
            await self.rate_limiter.acquire()
            
            # Doküman oluştur
            doc = {
                "id": id,
                "vector": vector,
                "metadata": metadata,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Content alanı varsa ekle
            if "content" in metadata:
                doc["content"] = metadata["content"]
            
            # Dokümanı ekle
            await asyncio.to_thread(
                self.client.index,
                index=self.index_name,
                id=id,
                body=doc,
                refresh=True
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Elasticsearch doküman ekleme hatası: {e}")
            return False
    
    async def search(self, vector: List[float], top_k: int = 10, filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Vektör arar"""
        if not self.is_connected:
            await self.connect()
            
        try:
            # Rate limiting uygula
            await self.rate_limiter.acquire(tokens=2)  # Arama daha maliyetli
            
            # KNN sorgusu
            knn_query = {
                "field": "vector",
                "query_vector": vector,
                "k": top_k,
                "num_candidates": top_k * 5
            }
            
            # Filtre varsa ekle
            if filter:
                # Bool sorgusu oluştur
                bool_query = {"must": []}
                
                for key, value in filter.items():
                    if key == "metadata":
                        for meta_key, meta_value in value.items():
                            path = f"metadata.{meta_key}"
                            bool_query["must"].append({"match": {path: meta_value}})
                    else:
                        bool_query["must"].append({"match": {key: value}})
                
                knn_query["filter"] = {"bool": bool_query}
            
            # Sorgu yap
            response = await asyncio.to_thread(
                self.client.search,
                index=self.index_name,
                body={"knn": knn_query, "_source": True},
                size=top_k
            )
            
            # Sonuçları işle
            hits = response["hits"]["hits"]
            results = []
            
            for hit in hits:
                source = hit["_source"]
                score = hit["_score"]
                
                results.append({
                    "id": source["id"],
                    "score": score,
                    "metadata": source["metadata"],
                    "vector": source.get("vector")
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Elasticsearch arama hatası: {e}")
            return []
    
    async def delete(self, id: str) -> bool:
        """Vektörü siler"""
        if not self.is_connected:
            await self.connect()
            
        try:
            # Rate limiting uygula
            await self.rate_limiter.acquire()
            
            # Dokümanı sil
            await asyncio.to_thread(
                self.client.delete,
                index=self.index_name,
                id=id,
                refresh=True
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Elasticsearch doküman silme hatası: {e}")
            return False
    
    async def get(self, id: str) -> Optional[Dict[str, Any]]:
        """ID'ye göre vektör ve metadata getirir"""
        if not self.is_connected:
            await self.connect()
            
        try:
            # Rate limiting uygula
            await self.rate_limiter.acquire()
            
            # Dokümanı getir
            response = await asyncio.to_thread(
                self.client.get,
                index=self.index_name,
                id=id
            )
            
            if not response["found"]:
                return None
                
            source = response["_source"]
            return {
                "id": source["id"],
                "vector": source["vector"],
                "metadata": source["metadata"],
                "created_at": source.get("created_at"),
                "updated_at": source.get("updated_at")
            }
            
        except elasticsearch.NotFoundError:
            return None
        except Exception as e:
            logger.error(f"Elasticsearch doküman getirme hatası: {e}")
            return None
    
    async def count(self) -> int:
        """Vektör sayısını döndürür"""
        if not self.is_connected:
            await self.connect()
            
        try:
            # Rate limiting uygula
            await self.rate_limiter.acquire()
            
            # Toplam kayıt sayısı
            response = await asyncio.to_thread(
                self.client.count,
                index=self.index_name
            )
            
            return response["count"]
            
        except Exception as e:
            logger.error(f"Elasticsearch sayım hatası: {e}")
            return 0


class WeaviateVectorClient(VectorDBClient):
    """Weaviate vektör veritabanı istemcisi"""
    
    def __init__(self, collection_name: str, url: str, api_key: Optional[str] = None, **kwargs):
        if not WEAVIATE_AVAILABLE:
            raise ImportError("Weaviate kütüphanesi yüklü değil. 'pip install weaviate-client' komutunu çalıştırın.")
            
        super().__init__(collection_name)
        self.url = url
        self.api_key = api_key
        self.client = None
        self.is_connected = False
        self.class_name = self._format_class_name(collection_name)
        self.weaviate_kwargs = kwargs
        
        # Rate limiter - varsayılan olarak saniyede 10 istek
        self.rate_limiter = RateLimiter(rate=10, per=1)
    
    def _format_class_name(self, name: str) -> str:
        """Weaviate sınıf adı formatına dönüştürür (PascalCase)"""
        # Boşlukları ve özel karakterleri kaldır
        name = ''.join(c for c in name if c.isalnum() or c == '_')
        
        # PascalCase formatına dönüştür
        words = name.split('_')
        return ''.join(word.capitalize() for word in words)
    
    async def connect(self) -> bool:
        """Weaviate'e bağlanır"""
        try:
            # Auth konfigürasyonu
            auth_config = None
            if self.api_key:
                auth_config = weaviate.auth.AuthApiKey(api_key=self.api_key)
            
            # Client oluştur
            self.client = weaviate.Client(
                url=self.url,
                auth_client_secret=auth_config,
                **self.weaviate_kwargs
            )
            
            # Bağlantıyı doğrula
            is_ready = await asyncio.to_thread(self.client.is_ready)
            if not is_ready:
                logger.error("Weaviate bağlantısı başarısız: Sunucu hazır değil")
                return False
                
            self.is_connected = True
            logger.info("Weaviate bağlantısı başarılı")
            return True
            
        except Exception as e:
            logger.error(f"Weaviate bağlantı hatası: {e}")
            self.is_connected = False
            return False
    
    async def create_collection(self, dimension: int) -> bool:
        """Weaviate sınıfı oluşturur"""
        if not self.is_connected:
            await self.connect()
            
        try:
            # Sınıf zaten var mı kontrol et
            class_exists = await asyncio.to_thread(self.client.schema.exists, self.class_name)
            if class_exists:
                logger.info(f"Weaviate sınıfı zaten mevcut: {self.class_name}")
                return True
                
            # Sınıf şeması
            class_schema = {
                "class": self.class_name,
                "vectorizer": "none",  # Vektörleri manuel ekleyeceğiz
                "vectorIndexType": "hnsw",
                "vectorIndexConfig": {
                    "distance": "cosine"
                },
                "properties": [
                    {
                        "name": "content",
                        "dataType": ["text"],
                        "description": "Doküman içeriği"
                    },
                    {
                        "name": "metadata",
                        "dataType": ["object"],
                        "description": "Doküman meta verileri"
                    },
                    {
                        "name": "createdAt",
                        "dataType": ["date"],
                        "description": "Oluşturulma tarihi"
                    },
                    {
                        "name": "updatedAt",
                        "dataType": ["date"],
                        "description": "Güncellenme tarihi"
                    }
                ]
            }
            
            # Rate limiting uygula
            await self.rate_limiter.acquire(tokens=3)  # Şema oluşturma daha maliyetli
            
            # Sınıfı oluştur
            await asyncio.to_thread(self.client.schema.create_class, class_schema)
            logger.info(f"Weaviate sınıfı oluşturuldu: {self.class_name}")
            return True
            
        except Exception as e:
            logger.error(f"Weaviate sınıfı oluşturma hatası: {e}")
            return False
    
    async def delete_collection(self) -> bool:
        """Weaviate sınıfını siler"""
        if not self.is_connected:
            await self.connect()
            
        try:
            # Rate limiting uygula
            await self.rate_limiter.acquire(tokens=2)
            
            # Sınıfı sil
            await asyncio.to_thread(self.client.schema.delete_class, self.class_name)
            logger.info(f"Weaviate sınıfı silindi: {self.class_name}")
            return True
            
        except Exception as e:
            logger.error(f"Weaviate sınıfı silme hatası: {e}")
            return False
    
    async def insert(self, id: str, vector: List[float], metadata: Dict[str, Any]) -> bool:
        """Vektör ekler"""
        if not self.is_connected:
            await self.connect()
            
        try:
            # Doküman oluştur
            properties = {
                "metadata": metadata,
                "createdAt": datetime.utcnow().isoformat(),
                "updatedAt": datetime.utcnow().isoformat()
            }
            
            # Content alanı varsa ekle
            if "content" in metadata:
                properties["content"] = metadata["content"]
            
            # Rate limiting uygula
            await self.rate_limiter.acquire()
            
            # Dokümanı ekle
            await asyncio.to_thread(
                self.client.data_object.create,
                properties,
                self.class_name,
                id,
                vector=vector
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Weaviate doküman ekleme hatası: {e}")
            return False
    
    async def search(self, vector: List[float], top_k: int = 10, filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Vektör arar"""
        if not self.is_connected:
            await self.connect()
            
        try:
            # GraphQL sorgusu oluştur
            properties = ["content", "metadata", "createdAt", "updatedAt", "_additional {id certainty}"]
            
            # Rate limiting uygula
            await self.rate_limiter.acquire(tokens=2)
            
            # Filter varsa, where filtresini oluştur
            where_filter = None
            if filter:
                where_clauses = []
                
                if "metadata" in filter and isinstance(filter["metadata"], dict):
                    for key, value in filter["metadata"].items():
                        where_clauses.append({
                            "path": ["metadata", key],
                            "operator": "Equal",
                            "valueString": str(value)
                        })
                
                if where_clauses:
                    where_filter = {"operator": "And", "operands": where_clauses}
            
            # Vektör sorgusu yap
            result = await asyncio.to_thread(
                self.client.query.get,
                self.class_name,
                properties
            ).with_near_vector({
                "vector": vector,
                "certainty": 0.7
            }).with_limit(top_k)
            
            if where_filter:
                result = result.with_where(where_filter)
                
            response = result.do()
            
            # Sonuçları işle
            results = []
            if "data" in response and "Get" in response["data"]:
                items = response["data"]["Get"].get(self.class_name, [])
                
                for item in items:
                    # Certainty skoru al (1 - mesafe)
                    certainty = item["_additional"]["certainty"]
                    item_id = item["_additional"]["id"]
                    
                    results.append({
                        "id": item_id,
                        "score": certainty,
                        "metadata": item["metadata"],
                        "content": item.get("content"),
                        "created_at": item.get("createdAt"),
                        "updated_at": item.get("updatedAt")
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Weaviate arama hatası: {e}")
            return []
    
    async def delete(self, id: str) -> bool:
        """Vektörü siler"""
        if not self.is_connected:
            await self.connect()
            
        try:
            # Rate limiting uygula
            await self.rate_limiter.acquire()
            
            # Dokümanı sil
            await asyncio.to_thread(self.client.data_object.delete, id, self.class_name)
            
            return True
            
        except Exception as e:
            logger.error(f"Weaviate doküman silme hatası: {e}")
            return False
    
    async def get(self, id: str) -> Optional[Dict[str, Any]]:
        """ID'ye göre vektör ve metadata getirir"""
        if not self.is_connected:
            await self.connect()
            
        try:
            # Rate limiting uygula
            await self.rate_limiter.acquire()
            
            # Dokümanı getir
            result = await asyncio.to_thread(
                self.client.data_object.get,
                id,
                self.class_name,
                with_vector=True
            )
            
            if not result:
                return None
                
            return {
                "id": id,
                "vector": result.get("vector"),
                "metadata": result