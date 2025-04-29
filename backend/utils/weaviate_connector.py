# Last reviewed: 2025-04-29 09:00:20 UTC (User: TeeksssTF-IDF)
from typing import List, Dict, Any, Optional, Union
import os
import json
import asyncio
import uuid
from datetime import datetime

from .config import (
    WEAVIATE_URL, WEAVIATE_API_KEY, WEAVIATE_CLASS_NAME,
    WEAVIATE_BATCH_SIZE, VECTOR_DIMENSION
)
from .logger import get_logger
from .embedding_manager import embedding_manager

logger = get_logger(__name__)

class WeaviateConnector:
    """Weaviate Vector Veritabanı Bağlantısı"""
    
    def __init__(self, url=WEAVIATE_URL, api_key=WEAVIATE_API_KEY, class_name=WEAVIATE_CLASS_NAME):
        self.url = url
        self.api_key = api_key
        self.class_name = class_name
        self.client = None
        self.batch_size = WEAVIATE_BATCH_SIZE
        self.vector_dimension = VECTOR_DIMENSION
        
    async def connect(self):
        """Weaviate bağlantısı kurar"""
        if self.client is not None:
            return
            
        try:
            # Lazy import
            import weaviate
            from weaviate.auth import AuthApiKey
            
            # Weaviate client başlatma
            auth_config = AuthApiKey(api_key=self.api_key) if self.api_key else None
            
            # Client oluştur - async olmadığı için thread pool'da çalıştır
            self.client = await asyncio.to_thread(
                weaviate.Client,
                url=self.url,
                auth_client_secret=auth_config,
                additional_headers={
                    "X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY", "")  # OpenAI entegrasyonu için
                }
            )
            
            # Bağlantıyı test et
            is_ready = await asyncio.to_thread(self.client.is_ready)
            if not is_ready:
                logger.error("Weaviate bağlantısı hazır değil")
                self.client = None
                return False
                
            logger.info(f"Weaviate bağlantısı kuruldu: {self.url}")
            
            # Şema kontrolü yap
            await self._ensure_schema()
            return True
            
        except Exception as e:
            logger.error(f"Weaviate bağlantı hatası: {e}")
            self.client = None
            return False
    
    async def _ensure_schema(self):
        """Gereken schema var mı kontrol et, yoksa oluştur"""
        if self.client is None:
            await self.connect()
            
        try:
            # Weaviate schema kontrolü CPU-bound işlem
            schema = await asyncio.to_thread(self.client.schema.get)
            
            # Sınıf var mı kontrol et
            classes = [c["class"] for c in schema["classes"]] if "classes" in schema else []
            
            if self.class_name not in classes:
                # Sınıf yoksa oluştur
                class_obj = {
                    "class": self.class_name,
                    "description": "RAG Belge Veritabanı",
                    "vectorizer": "none",  # Dışarıdan embedding kullanacağız
                    "vectorIndexType": "hnsw",
                    "vectorIndexConfig": {
                        "distance": "cosine"
                    },
                    "properties": [
                        {
                            "name": "text",
                            "dataType": ["text"],
                            "description": "Belge metni"
                        },
                        {
                            "name": "source",
                            "dataType": ["string"],
                            "description": "Kaynak tipi"
                        },
                        {
                            "name": "source_url",
                            "dataType": ["string"],
                            "description": "Kaynak URL"
                        },
                        {
                            "name": "source_id",
                            "dataType": ["string"],
                            "description": "Kaynak ID"
                        },
                        {
                            "name": "owner_id",
                            "dataType": ["string"],
                            "description": "Sahip kullanıcı ID"
                        },
                        {
                            "name": "timestamp",
                            "dataType": ["date"],
                            "description": "Oluşturulma zamanı"
                        },
                        {
                            "name": "category",
                            "dataType": ["string"],
                            "description": "Kategori"
                        },
                        {
                            "name": "metadata",
                            "dataType": ["object"],
                            "description": "Ek metadata"
                        }
                    ]
                }
                
                logger.info(f"Weaviate sınıfı oluşturuluyor: {self.class_name}")
                await asyncio.to_thread(self.client.schema.create_class, class_obj)
                logger.info(f"Weaviate sınıfı oluşturuldu: {self.class_name}")
            else:
                logger.info(f"Weaviate sınıfı zaten mevcut: {self.class_name}")
                
        except Exception as e:
            logger.error(f"Weaviate schema oluşturma hatası: {e}")
            raise
    
    async def add_document(
        self, 
        text: str, 
        metadata: Optional[Dict[str, Any]] = None, 
        vector: Optional[List[float]] = None,
        id: Optional[str] = None
    ) -> str:
        """Tek bir belgeyi veritabanına ekler"""
        if self.client is None:
            success = await self.connect()
            if not success:
                raise ConnectionError("Weaviate bağlantısı kurulamadı")
        
        try:
            # UUID oluştur
            doc_id = id if id else str(uuid.uuid4())
            
            # Belge verilerini hazırla
            document = {
                "text": text,
                "source": metadata.get("source", "unknown") if metadata else "unknown",
                "source_url": metadata.get("source_url", "") if metadata else "",
                "source_id": metadata.get("source_id", "") if metadata else "",
                "owner_id": metadata.get("owner_id", "") if metadata else "",
                "timestamp": metadata.get("timestamp", datetime.utcnow().isoformat()) if metadata else datetime.utcnow().isoformat(),
                "category": metadata.get("category", "") if metadata else "",
                "metadata": metadata if metadata else {}
            }
            
            # Embedding yoksa oluştur
            if vector is None:
                vector = await embedding_manager.get_embedding(text)
            
            # Weaviate'e ekle
            await asyncio.to_thread(
                self.client.data_object.create,
                data_object=document,
                class_name=self.class_name,
                uuid=doc_id,
                vector=vector
            )
            
            return doc_id
            
        except Exception as e:
            logger.error(f"Weaviate belge ekleme hatası: {e}")
            raise
    
    async def add_documents_batch(
        self, 
        documents: List[Dict[str, Any]],
        generate_vectors: bool = True
    ) -> List[str]:
        """Belgeleri batch olarak veritabanına ekler"""
        if self.client is None:
            success = await self.connect()
            if not success:
                raise ConnectionError("Weaviate bağlantısı kurulamadı")
        
        try:
            # Batch işlemi için hazırlık
            doc_ids = []
            import weaviate.util as weaviate_util
            
            # Belgeleri batch_size kadar gruplara ayır
            for i in range(0, len(documents), self.batch_size):
                batch = documents[i:i+self.batch_size]
                
                # Embeddings oluştur (eğer istenirse)
                if generate_vectors:
                    texts = [doc["text"] for doc in batch]
                    vectors = await embedding_manager.get_embeddings_batch(texts)
                else:
                    vectors = [doc.get("vector") for doc in batch]
                
                # Batch işlemi için veri yapısını hazırla
                with self.client.batch as batch_processor:
                    batch_processor.batch_size = self.batch_size
                    
                    for j, doc in enumerate(batch):
                        doc_id = doc.get("id", str(uuid.uuid4()))
                        doc_ids.append(doc_id)
                        
                        # Belge verilerini hazırla
                        metadata = doc.get("metadata", {})
                        
                        data_object = {
                            "text": doc["text"],
                            "source": doc.get("source", metadata.get("source", "unknown")),
                            "source_url": doc.get("source_url", metadata.get("source_url", "")),
                            "source_id": doc.get("source_id", metadata.get("source_id", "")),
                            "owner_id": doc.get("owner_id", metadata.get("owner_id", "")),
                            "timestamp": doc.get("timestamp", metadata.get("timestamp", datetime.utcnow().isoformat())),
                            "category": doc.get("category", metadata.get("category", "")),
                            "metadata": metadata
                        }
                        
                        # Batch'e ekle
                        batch_processor.add_data_object(
                            data_object=data_object,
                            class_name=self.class_name,
                            uuid=doc_id,
                            vector=vectors[j] if vectors and j < len(vectors) else None
                        )
            
            return doc_ids
            
        except Exception as e:
            logger.error(f"Weaviate batch belge ekleme hatası: {e}")
            raise
    
    async def search(
        self,
        query: str,
        vector: Optional[List[float]] = None,
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Vector ve/veya keyword ile belge arar"""
        if self.client is None:
            success = await self.connect()
            if not success:
                raise ConnectionError("Weaviate bağlantısı kurulamadı")
        
        try:
            # Vector yoksa oluştur
            if vector is None and query:
                vector = await embedding_manager.get_embedding(query)
            
            # GraphQL filtreleri oluştur
            filter_string = ""
            if filters:
                where_conditions = []
                
                for key, value in filters.items():
                    if key == "owner_id":
                        where_conditions.append(f'owner_id: "{value}"')
                    elif key == "source":
                        where_conditions.append(f'source: "{value}"')
                    elif key == "category":
                        where_conditions.append(f'category: "{value}"')
                        
                if where_conditions:
                    filter_string = "where: {" + ", ".join(where_conditions) + "}"
            
            # GraphQL sorgusu oluştur
            query_string = f"""
            {{
              Get {{
                {self.class_name}(
                  nearVector: {{
                    vector: {json.dumps(vector)}
                    certainty: 0.6
                  }}
                  {filter_string}
                  limit: {limit}
                ) {{
                  text
                  source
                  source_url
                  source_id
                  owner_id
                  timestamp
                  category
                  metadata
                  _additional {{
                    id
                    certainty
                    distance
                  }}
                }}
              }}
            }}
            """
            
            # Sorguyu çalıştır
            result = await asyncio.to_thread(self.client.query.raw, query_string)
            
            # Sonuçları dönüştür
            weaviate_objects = result["data"]["Get"][self.class_name]
            
            docs = []
            for obj in weaviate_objects:
                # Metadata'yı parse et
                metadata = obj["metadata"]
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except:
                        metadata = {}
                
                # Kaynak bilgilerini hazırla
                source_info = {
                    "source_type": obj["source"],
                    "url": obj["source_url"],
                    "id": obj["source_id"]
                }
                
                # Ek metadata ekle
                source_info.update(metadata)
                
                # Belge nesnesini oluştur
                doc = {
                    "id": obj["_additional"]["id"],
                    "text": obj["text"],
                    "score": obj["_additional"]["certainty"],
                    "source_info": source_info,
                    "timestamp": obj["timestamp"],
                    "category": obj["category"],
                    "search_type": "vector",
                    "owner_id": obj["owner_id"]
                }
                
                docs.append(doc)
            
            return docs
            
        except Exception as e:
            logger.error(f"Weaviate arama hatası: {e}")
            raise
    
    async def hybrid_search(
        self,
        query: str,
        vector: Optional[List[float]] = None,
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        alpha: float = 0.5  # Vector ve keyword ağırlık dengesi
    ) -> List[Dict[str, Any]]:
        """Hybrid arama (hem vector hem de keyword tabanlı)"""
        if self.client is None:
            success = await self.connect()
            if not success:
                raise ConnectionError("Weaviate bağlantısı kurulamadı")
        
        try:
            # Vector yoksa oluştur
            if vector is None and query:
                vector = await embedding_manager.get_embedding(query)
            
            # GraphQL filtreleri oluştur
            filter_string = ""
            if filters:
                where_conditions = []
                
                for key, value in filters.items():
                    if key == "owner_id":
                        where_conditions.append(f'owner_id: "{value}"')
                    elif key == "source":
                        where_conditions.append(f'source: "{value}"')
                    elif key == "category":
                        where_conditions.append(f'category: "{value}"')
                        
                if where_conditions:
                    filter_string = "where: {" + ", ".join(where_conditions) + "}"
            
            # GraphQL sorgusu oluştur - hybrid arama
            query_string = f"""
            {{
              Get {{
                {self.class_name}(
                  hybrid: {{
                    query: "{query}"
                    vector: {json.dumps(vector)}
                    alpha: {alpha}
                  }}
                  {filter_string}
                  limit: {limit}
                ) {{
                  text
                  source
                  source_url
                  source_id
                  owner_id
                  timestamp
                  category
                  metadata
                  _additional {{
                    id
                    score
                  }}
                }}
              }}
            }}
            """
            
            # Sorguyu çalıştır
            result = await asyncio.to_thread(self.client.query.raw, query_string)
            
            # Sonuçları dönüştür
            weaviate_objects = result["data"]["Get"][self.class_name]
            
            docs = []
            for obj in weaviate_objects:
                # Metadata'yı parse et
                metadata = obj["metadata"]
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except:
                        metadata = {}
                
                # Kaynak bilgilerini hazırla
                source_info = {
                    "source_type": obj["source"],
                    "url": obj["source_url"],
                    "id": obj["source_id"]
                }
                
                # Ek metadata ekle
                source_info.update(metadata)
                
                # Belge nesnesini oluştur
                doc = {
                    "id": obj["_additional"]["id"],
                    "text": obj["text"],
                    "score": obj["_additional"]["score"],
                    "source_info": source_info,
                    "timestamp": obj["timestamp"],
                    "category": obj["category"],
                    "search_type": "hybrid",
                    "owner_id": obj["owner_id"]
                }
                
                docs.append(doc)
            
            return docs
            
        except Exception as e:
            logger.error(f"Weaviate hybrid arama hatası: {e}")
            raise
    
    async def delete_document(self, doc_id: str) -> bool:
        """Belgeyi siler"""
        if self.client is None:
            success = await self.connect()
            if not success:
                raise ConnectionError("Weaviate bağlantısı kurulamadı")
        
        try:
            # UUID ile sil
            await asyncio.to_thread(self.client.data_object.delete, doc_id, self.class_name)
            return True
            
        except Exception as e:
            logger.error(f"Weaviate belge silme hatası: {e}")
            return False
    
    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Belgeyi ID ile getirir"""
        if self.client is None:
            success = await self.connect()
            if not success:
                raise ConnectionError("Weaviate bağlantısı kurulamadı")
        
        try:
            # UUID ile getir
            result = await asyncio.to_thread(self.client.data_object.get, doc_id, self.class_name)
            
            if not result:
                return None
                
            # Sonucu dönüştür
            obj = result
            
            # Metadata'yı parse et
            metadata = obj.get("metadata", {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}
            
            # Kaynak bilgilerini hazırla
            source_info = {
                "source_type": obj.get("source", "unknown"),
                "url": obj.get("source_url", ""),
                "id": obj.get("source_id", "")
            }
            
            # Ek metadata ekle
            source_info.update(metadata)
            
            # Belge nesnesini oluştur
            doc = {
                "id": doc_id,
                "text": obj.get("text", ""),
                "source_info": source_info,
                "timestamp": obj.get("timestamp", ""),
                "category": obj.get("category", ""),
                "owner_id": obj.get("owner_id", "")
            }
            
            return doc
            
        except Exception as e:
            logger.error(f"Weaviate belge getirme hatası: {e}")
            return None

# Weaviate connector singleton
weaviate_connector = WeaviateConnector()