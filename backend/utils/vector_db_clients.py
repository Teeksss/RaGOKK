# Last reviewed: 2025-04-29 12:28:23 UTC (User: TeeksssCSRF)
from typing import Dict, List, Any, Optional, Tuple, Union
import os
import time
import asyncio
import logging
import json
import numpy as np

# Vektör veritabanı entegrasyonları
from .vector_db_manager import VectorDBClient, RateLimiter, ScanResult

logger = logging.getLogger(__name__)

class PineconeVectorClient(VectorDBClient):
    """Pinecone vektör veritabanı istemcisi"""
    
    def __init__(self, 
                 collection_name: str, 
                 api_key: str, 
                 environment: str, 
                 namespace: Optional[str] = None, 
                 **kwargs):
        """
        Args:
            collection_name: Koleksiyon/index adı
            api_key: Pinecone API anahtarı
            environment: Pinecone ortamı (ör. 'us-west1-gcp')
            namespace: Pinecone namespace (opsiyonel)
        """
        try:
            import pinecone
            self.pinecone_available = True
        except ImportError:
            logger.error("Pinecone kütüphanesi yüklü değil. 'pip install pinecone-client' komutunu çalıştırın.")
            self.pinecone_available = False
            
        super().__init__(collection_name)
        self.api_key = api_key
        self.environment = environment
        self.namespace = namespace
        self.pinecone_kwargs = kwargs
        self.index = None
        self.is_connected = False
        self.dimension = None
        
        # Rate limiter - varsayılan olarak dakikada 100 istek (free tier için güvenli)
        self.rate_limiter = RateLimiter(rate=100, per=60)
    
    async def connect(self) -> bool:
        """Pinecone'a bağlanır"""
        if not self.pinecone_available:
            logger.error("Pinecone kütüphanesi yüklü değil")
            return False
            
        try:
            import pinecone
            
            # Pinecone'u başlat
            pinecone.init(api_key=self.api_key, environment=self.environment)
            
            # İndeksleri listele
            indexes = await asyncio.to_thread(pinecone.list_indexes)
            
            # İndeks varsa bağlan
            if self.collection_name in indexes:
                self.index = pinecone.Index(self.collection_name)
                self.is_connected = True
                
                # İndeks boyutunu al
                index_stats = await asyncio.to_thread(pinecone.describe_index, self.collection_name)
                self.dimension = index_stats.dimension
                
                logger.info(f"Pinecone bağlantısı başarılı: {self.collection_name}, dimension={self.dimension}")
                return True
            else:
                logger.warning(f"Pinecone indeksi bulunamadı: {self.collection_name}")
                return False
                
        except Exception as e:
            logger.error(f"Pinecone bağlantı hatası: {e}")
            self.is_connected = False
            return False
    
    async def create_collection(self, dimension: int) -> bool:
        """Pinecone indeksi oluşturur"""
        if not self.pinecone_available:
            return False
            
        try:
            import pinecone
            
            # Pinecone'u başlat
            pinecone.init(api_key=self.api_key, environment=self.environment)
            
            # İndeks zaten var mı kontrol et
            indexes = await asyncio.to_thread(pinecone.list_indexes)
            if self.collection_name in indexes:
                # İndeks zaten var, bağlan
                self.index = pinecone.Index(self.collection_name)
                self.is_connected = True
                self.dimension = dimension
                logger.info(f"Pinecone indeksi zaten var: {self.collection_name}")
                return True
            
            # İndeks oluştur
            await asyncio.to_thread(
                pinecone.create_index,
                name=self.collection_name,
                dimension=dimension,
                metric="cosine",
                **self.pinecone_kwargs
            )
            
            # İndeksin oluşturulmasını bekle
            max_retries = 10
            for i in range(max_retries):
                try:
                    indexes = await asyncio.to_thread(pinecone.list_indexes)
                    if self.collection_name in indexes:
                        break
                except:
                    pass
                    
                await asyncio.sleep(5)  # 5 saniye bekle
            
            # İndekse bağlan
            self.index = pinecone.Index(self.collection_name)
            self.is_connected = True
            self.dimension = dimension
            
            logger.info(f"Pinecone indeksi oluşturuldu: {self.collection_name}, dimension={dimension}")
            return True
            
        except Exception as e:
            logger.error(f"Pinecone indeksi oluşturma hatası: {e}")
            self.is_connected = False
            return False
    
    async def delete_collection(self) -> bool:
        """Pinecone indeksini siler"""
        if not self.pinecone_available or not self.is_connected:
            return False
            
        try:
            import pinecone
            
            # Pinecone'u başlat
            pinecone.init(api_key=self.api_key, environment=self.environment)
            
            # İndeksi sil
            await asyncio.to_thread(pinecone.delete_index, self.collection_name)
            
            self.index = None
            self.is_connected = False
            
            logger.info(f"Pinecone indeksi silindi: {self.collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Pinecone indeksi silme hatası: {e}")
            return False
    
    async def insert(self, id: str, vector: List[float], metadata: Dict[str, Any]) -> bool:
        """Vektör ekler"""
        if not self.pinecone_available or not self.is_connected:
            return False
            
        try:
            # Rate limiting uygula
            await self.rate_limiter.acquire()
            
            # Vektör ekleme için ID ve vektör hazırla
            vector_data = {
                "id": id,
                "values": vector,
                "metadata": metadata
            }
            
            # Namespace eklenmişse kullan
            namespace_param = {}
            if self.namespace:
                namespace_param["namespace"] = self.namespace
            
            # Vektörü ekle
            await asyncio.to_thread(
                self.index.upsert,
                vectors=[vector_data],
                **namespace_param
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Pinecone vektör ekleme hatası: {e}")
            return False
    
    async def search(self, vector: List[float], top_k: int = 10, filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Vektör arar"""
        if not self.pinecone_available or not self.is_connected:
            return []
            
        try:
            # Rate limiting uygula
            await self.rate_limiter.acquire(tokens=2)  # Arama daha maliyetli
            
            # Pinecone filtresi oluştur
            filter_query = None
            if filter:
                filter_query = {}
                for key, value in filter.items():
                    filter_query[key] = value
            
            # Namespace eklenmişse kullan
            namespace_param = {}
            if self.namespace:
                namespace_param["namespace"] = self.namespace
            
            # Arama yap
            response = await asyncio.to_thread(
                self.index.query,
                vector=vector,
                top_k=top_k,
                include_values=True,
                include_metadata=True,
                filter=filter_query,
                **namespace_param
            )
            
            # Sonuçları işle
            results = []
            for match in response.matches:
                results.append({
                    "id": match.id,
                    "score": match.score,
                    "metadata": match.metadata,
                    "vector": match.values if hasattr(match, 'values') else None
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Pinecone arama hatası: {e}")
            return []
    
    async def delete(self, id: str) -> bool:
        """Vektörü siler"""
        if not self.pinecone_available or not self.is_connected:
            return False
            
        try:
            # Rate limiting uygula
            await self.rate_limiter.acquire()
            
            # Namespace eklenmişse kullan
            namespace_param = {}
            if self.namespace:
                namespace_param["namespace"] = self.namespace
            
            # Vektörü sil
            await asyncio.to_thread(
                self.index.delete,
                ids=[id],
                **namespace_param
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Pinecone vektör silme hatası: {e}")
            return False
    
    async def get(self, id: str) -> Optional[Dict[str, Any]]:
        """ID'ye göre vektör ve metadata getirir"""
        if not self.pinecone_available or not self.is_connected:
            return None
            
        try:
            # Rate limiting uygula
            await self.rate_limiter.acquire()
            
            # Namespace eklenmişse kullan
            namespace_param = {}
            if self.namespace:
                namespace_param["namespace"] = self.namespace
            
            # Vektörü getir
            response = await asyncio.to_thread(
                self.index.fetch,
                ids=[id],
                **namespace_param
            )
            
            # Sonucu işle
            vectors = response.get("vectors", {})
            if id not in vectors:
                return None
                
            vector_data = vectors[id]
            
            return {
                "id": id,
                "vector": vector_data.get("values"),
                "metadata": vector_data.get("metadata", {}),
            }
            
        except Exception as e:
            logger.error(f"Pinecone vektör getirme hatası: {e}")
            return None
    
    async def count(self) -> int:
        """Vektör sayısını döndürür"""
        if not self.pinecone_available or not self.is_connected:
            return 0
            
        try:
            # Rate limiting uygula
            await self.rate_limiter.acquire()
            
            # İndeks istatistiklerini al
            stats = await asyncio.to_thread(self.index.describe_index_stats)
            
            # Namespace'e özel sayı
            if self.namespace and "namespaces" in stats and self.namespace in stats["namespaces"]:
                return stats["namespaces"][self.namespace]["vector_count"]
                
            # Toplam sayı
            return stats["total_vector_count"]
            
        except Exception as e:
            logger.error(f"Pinecone sayım hatası: {e}")
            return 0


class MilvusVectorClient(VectorDBClient):
    """Milvus vektör veritabanı istemcisi"""
    
    def __init__(self, 
                 collection_name: str, 
                 host: str = "localhost", 
                 port: str = "19530", 
                 user: Optional[str] = None, 
                 password: Optional[str] = None,
                 **kwargs):
        """
        Args:
            collection_name: Koleksiyon adı
            host: Milvus sunucu adresi
            port: Milvus sunucu portu
            user: Milvus kullanıcı adı (opsiyonel)
            password: Milvus şifresi (opsiyonel)
        """
        try:
            from pymilvus import connections
            self.milvus_available = True
        except ImportError:
            logger.error("Milvus kütüphanesi yüklü değil. 'pip install pymilvus' komutunu çalıştırın.")
            self.milvus_available = False
            
        super().__init__(collection_name)
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.milvus_kwargs = kwargs
        self.collection = None
        self.is_connected = False
        self.dimension = None
        
        # Rate limiter - varsayılan olarak saniyede 10 istek
        self.rate_limiter = RateLimiter(rate=10, per=1)
        
        # Bağlantı adı
        self.connection_alias = f"default_{int(time.time())}"
    
    async def connect(self) -> bool:
        """Milvus'a bağlanır"""
        if not self.milvus_available:
            logger.error("Milvus kütüphanesi yüklü değil")
            return False
            
        try:
            from pymilvus import connections, Collection, utility
            
            # Milvus'a bağlan
            conn_params = {
                "host": self.host,
                "port": self.port
            }
            
            if self.user and self.password:
                conn_params["user"] = self.user
                conn_params["password"] = self.password
            
            await asyncio.to_thread(
                connections.connect,
                alias=self.connection_alias,
                **conn_params
            )
            
            # Koleksiyon varsa yükle
            has_collection = await asyncio.to_thread(
                utility.has_collection,
                self.collection_name
            )
            
            if has_collection:
                self.collection = await asyncio.to_thread(
                    Collection,
                    self.collection_name
                )
                await asyncio.to_thread(self.collection.load)
                
                # Boyut bilgisini al
                schema = self.collection.schema
                for field in schema.fields:
                    if field.dtype == 100:  # FloatVector
                        self.dimension = field.params.get("dim")
                
                self.is_connected = True
                logger.info(f"Milvus bağlantısı başarılı: {self.collection_name}, dimension={self.dimension}")
                return True
            else:
                logger.warning(f"Milvus koleksiyonu bulunamadı: {self.collection_name}")
                return False
                
        except Exception as e:
            logger.error(f"Milvus bağlantı hatası: {e}")
            self.is_connected = False
            return False
    
    async def create_collection(self, dimension: int) -> bool:
        """Milvus koleksiyonu oluşturur"""
        if not self.milvus_available:
            return False
            
        try:
            from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
            
            # Milvus'a bağlan (bağlantı yoksa)
            if not self.is_connected:
                conn_params = {
                    "host": self.host,
                    "port": self.port
                }
                
                if self.user and self.password:
                    conn_params["user"] = self.user
                    conn_params["password"] = self.password
                
                await asyncio.to_thread(
                    connections.connect,
                    alias=self.connection_alias,
                    **conn_params
                )
            
            # Koleksiyon zaten var mı kontrol et
            has_collection = await asyncio.to_thread(
                utility.has_collection,
                self.collection_name
            )
            
            if has_collection:
                self.collection = await asyncio.to_thread(
                    Collection,
                    self.collection_name
                )
                await asyncio.to_thread(self.collection.load)
                self.is_connected = True
                self.dimension = dimension
                logger.info(f"Milvus koleksiyonu zaten var: {self.collection_name}")
                return True
            
            # Koleksiyon şeması oluştur
            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, auto_id=False, max_length=100),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dimension),
                FieldSchema(name="metadata", dtype=DataType.JSON)
            ]
            
            schema = CollectionSchema(fields=fields)
            
            # Koleksiyonu oluştur
            self.collection = await asyncio.to_thread(
                Collection,
                name=self.collection_name,
                schema=schema,
                **self.milvus_kwargs
            )
            
            # İndeks oluştur
            index_params = {
                "metric_type": "COSINE",
                "index_type": "HNSW",
                "params": {"M": 8, "efConstruction": 64}
            }
            
            await asyncio.to_thread(
                self.collection.create_index,
                field_name="vector",
                index_params=index_params
            )
            
            # Koleksiyonu yükle
            await asyncio.to_thread(self.collection.load)
            
            self.is_connected = True
            self.dimension = dimension
            
            logger.info(f"Milvus koleksiyonu oluşturuldu: {self.collection_name}, dimension={dimension}")
            return True
            
        except Exception as e:
            logger.error(f"Milvus koleksiyonu oluşturma hatası: {e}")
            self.is_connected = False
            return False
    
    async def delete_collection(self) -> bool:
        """Milvus koleksiyonunu siler"""
        if not self.milvus_available or not self.is_connected:
            return False
            
        try:
            from pymilvus import utility
            
            # Koleksiyonu sil
            await asyncio.to_thread(
                utility.drop_collection,
                self.collection_name
            )
            
            self.collection = None
            self.is_connected = False
            
            logger.info(f"Milvus koleksiyonu silindi: {self.collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Milvus koleksiyonu silme hatası: {e}")
            return False
    
    async def insert(self, id: str, vector: List[float], metadata: Dict[str, Any]) -> bool:
        """Vektör ekler"""
        if not self.milvus_available or not self.is_connected:
            return False
            
        try:
            # Rate limiting uygula
            await self.rate_limiter.acquire()
            
            # Veri hazırla
            data = [
                [id],                  # id
                [vector],              # vector
                [json.dumps(metadata)] # metadata (JSON string olarak)
            ]
            
            # Vektör ekle
            await asyncio.to_thread(
                self.collection.insert,
                data=data
            )
            
            # Değişiklikleri flushlama
            await asyncio.to_thread(
                self.collection.flush
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Milvus vektör ekleme hatası: {e}")
            return False
    
    async def search(self, vector: List[float], top_k: int = 10, filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Vektör arar"""
        if not self.milvus_available or not self.is_connected:
            return []
            
        try:
            # Rate limiting uygula
            await self.rate_limiter.acquire(tokens=2)  # Arama daha maliyetli
            
            # Milvus için filtreyi dönüştür
            expr = None
            if filter:
                # JSON metadata filtreleri için özel dönüşüm
                conditions = []
                for key, value in filter.items():
                    if key == "metadata" and isinstance(value, dict):
                        for meta_key, meta_value in value.items():
                            # Metadata JSON field içindeki değerleri filtreleme
                            # JSON_CONTAINS_ANY kullanıyoruz
                            if isinstance(meta_value, str):
                                condition = f'JSON_CONTAINS_ANY(metadata, "{{\"{meta_key}\": \"{meta_value}\"}}")'
                                conditions.append(condition)
                            elif isinstance(meta_value, (int, float, bool)):
                                condition = f'JSON_CONTAINS_ANY(metadata, "{{\"{meta_key}\": {meta_value}}}")'
                                conditions.append(condition)
                    else:
                        # Doğrudan alan filtreleme
                        if isinstance(value, str):
                            condition = f'{key} == "{value}"'
                            conditions.append(condition)
                        elif isinstance(value, (int, float, bool)):
                            condition = f"{key} == {value}"
                            conditions.append(condition)
                
                # Koşulları AND ile birleştir
                if conditions:
                    expr = " and ".join(conditions)
            
            # Arama parametrelerini hazırla
            search_params = {
                "metric_type": "COSINE",
                "params": {"ef": 64}
            }
            
            # Arama yap
            results = await asyncio.to_thread(
                self.collection.search,
                data=[vector],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                expr=expr,
                output_fields=["metadata"]
            )
            
            # Sonuçları işle
            processed_results = []
            
            if results and len(results) > 0:
                hits = results[0]  # İlk sorgu sonuçları
                
                for hit in hits:
                    # Metadata'yı JSON'dan parse et
                    metadata = {}
                    if hasattr(hit, "entity") and "metadata" in hit.entity:
                        try:
                            metadata = json.loads(hit.entity.get("metadata", "{}"))
                        except:
                            pass
                    
                    processed_results.append({
                        "id": hit.id,
                        "score": hit.score,
                        "metadata": metadata
                    })
            
            return processed_results
            
        except Exception as e:
            logger.error(f"Milvus arama hatası: {e}")
            return []
    
    async def delete(self, id: str) -> bool:
        """Vektörü siler"""
        if not self.milvus_available or not self.is_connected:
            return False
            
        try:
            # Rate limiting uygula
            await self.rate_limiter.acquire()
            
            # Silme ifadesi
            expr = f'id == "{id}"'
            
            # Vektörü sil
            await asyncio.to_thread(
                self.collection.delete,
                expr
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Milvus vektör silme hatası: {e}")
            return False
    
    async def get(self, id: str) -> Optional[Dict[str, Any]]:
        """ID'ye göre vektör ve metadata getirir"""
        if not self.milvus_available or not self.is_connected:
            return None
            
        try:
            # Rate limiting uygula
            await self.rate_limiter.acquire()
            
            # ID'ye göre sorgu
            expr = f'id == "{id}"'
            
            # Vektörü getir
            results = await asyncio.to_thread(
                self.collection.query,
                expr=expr,
                output_fields=["vector", "metadata"]
            )
            
            if not results or len(results) == 0:
                return None
                
            # İlk eşleşme
            result = results[0]
            
            # Vektörü al
            vector = result.get("vector")
            
            # Metadata'yı JSON'dan parse et
            metadata = {}
            if "metadata" in result:
                try:
                    metadata = json.loads(result.get("metadata", "{}"))
                except:
                    pass
            
            return {
                "id": id,
                "vector": vector,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Milvus vektör getirme hatası: {e}")
            return None
    
    async def count(self) -> int:
        """Vektör sayısını döndürür"""
        if not self.milvus_available or not self.is_connected:
            return 0
            
        try:
            # Rate limiting uygula
            await self.rate_limiter.acquire()
            
            # Toplam kayıt sayısı
            stats = await asyncio.to_thread(
                self.collection.num_entities
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Milvus sayım hatası: {e}")
            return 0