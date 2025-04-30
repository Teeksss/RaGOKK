# Last reviewed: 2025-04-29 14:31:59 UTC (User: Teeksss)
import logging
import asyncio
from typing import Dict, Any, List, Optional, Union, Tuple
import os
import json
import uuid
import numpy as np
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document

from ..config import settings
from ..repositories.document_repository import DocumentRepository
from ..schemas.document import DocumentEmbedding, DocumentChunk

# Vektör veritabanı istemci yapılandırması
try:
    if settings.VECTOR_DB_TYPE == "qdrant":
        from qdrant_client import QdrantClient
        from qdrant_client.http import models as qdrant_models
    elif settings.VECTOR_DB_TYPE == "weaviate":
        import weaviate
    elif settings.VECTOR_DB_TYPE == "pgvector":
        import asyncpg
        import psycopg2.extras
    else:
        # Varsayılan olarak in-memory faiss kullan
        from langchain.vectorstores import FAISS
except ImportError as e:
    logging.error(f"Vector database imports error: {e}")

logger = logging.getLogger(__name__)

class VectorService:
    """
    Vektör tabanlı belge işleme ve arama servisi
    
    Bu servis şunları sağlar:
    - Belgelerden vektör gösterimleri (embeddings) oluşturma
    - Vektör veritabanına belge ekleme
    - Semantik arama ile ilgili belgeleri bulma
    """
    
    def __init__(self):
        """VectorService başlatma"""
        self.document_repository = DocumentRepository()
        self.vector_db_type = settings.VECTOR_DB_TYPE
        self.vector_db_client = None
        
        # Embedding modeli yapılandırması
        self.embeddings_model = OpenAIEmbeddings(
            openai_api_key=settings.OPENAI_API_KEY,
            model=settings.EMBEDDING_MODEL or "text-embedding-ada-002"
        )
        
        # Text splitter yapılandırması
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Koleksiyon/index isimleri
        self.collection_name = "documents"
        
        # Vektör boyutları
        self.vector_dimensions = 1536  # OpenAI ada-002 için
        
        # Önbellek
        self.embedding_cache = {}
    
    async def connect(self):
        """Vektör veritabanına bağlan"""
        try:
            if self.vector_db_type == "qdrant":
                self.vector_db_client = QdrantClient(
                    url=settings.QDRANT_URL,
                    api_key=settings.QDRANT_API_KEY,
                    timeout=120
                )
                
                # Koleksiyon varsa kontrol et, yoksa oluştur
                collections = self.vector_db_client.get_collections().collections
                collection_names = [c.name for c in collections]
                
                if self.collection_name not in collection_names:
                    self.vector_db_client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=qdrant_models.VectorParams(
                            size=self.vector_dimensions,
                            distance=qdrant_models.Distance.COSINE
                        )
                    )
                
                logger.info(f"Connected to Qdrant vector database: {settings.QDRANT_URL}")
            
            elif self.vector_db_type == "weaviate":
                auth_config = weaviate.auth.AuthApiKey(api_key=settings.WEAVIATE_API_KEY) if settings.WEAVIATE_API_KEY else None
                
                self.vector_db_client = weaviate.Client(
                    url=settings.WEAVIATE_URL,
                    auth_client_secret=auth_config,
                    additional_headers={
                        "X-OpenAI-Api-Key": settings.OPENAI_API_KEY
                    } if settings.OPENAI_API_KEY else {}
                )
                
                # Sınıf şeması kontrol et/oluştur
                if not self.vector_db_client.schema.exists(self.collection_name):
                    class_obj = {
                        "class": self.collection_name,
                        "description": "RAG document embeddings",
                        "vectorizer": "none",  # Kendi embeddings'lerimizi kullanacağız
                        "vectorIndexConfig": {
                            "distance": "cosine"
                        },
                        "properties": [
                            {
                                "name": "document_id",
                                "dataType": ["string"],
                                "description": "Document ID",
                                "indexInverted": True
                            },
                            {
                                "name": "text",
                                "dataType": ["text"],
                                "description": "Document text content",
                                "indexInverted": True
                            },
                            {
                                "name": "user_id",
                                "dataType": ["string"],
                                "description": "Owner user ID",
                                "indexInverted": True
                            },
                            {
                                "name": "organization_id",
                                "dataType": ["string"],
                                "description": "Organization ID",
                                "indexInverted": True
                            },
                            {
                                "name": "chunk_id",
                                "dataType": ["string"],
                                "description": "Chunk identifier",
                                "indexInverted": True
                            },
                            {
                                "name": "metadata",
                                "dataType": ["object"],
                                "description": "Additional metadata",
                            }
                        ]
                    }
                    self.vector_db_client.schema.create_class(class_obj)
                
                logger.info(f"Connected to Weaviate vector database: {settings.WEAVIATE_URL}")
            
            elif self.vector_db_type == "pgvector":
                # pgvector bağlantısı kullanılacak
                # Bu örnekte zaten PostgreSQL kullanıyoruz ve pgvector eklentisi ekleneceğini varsayıyoruz
                logger.info("Using PostgreSQL with pgvector extension")
                # Burada pgvector eklentisi ve tablo kontrolleri yapılabilir
                
            elif self.vector_db_type == "faiss":
                # FAISS in-memory kullanım için özel bir bağlantı gerekmez
                logger.info("Using in-memory FAISS vector store")
                
                # FAISS dizinini yükle veya oluştur
                if os.path.exists(f"{settings.FAISS_INDEX_PATH}/{self.collection_name}.index"):
                    # Mevcut indeksi yükle (async olmadığı için dikkatli olmalıyız)
                    loop = asyncio.get_event_loop()
                    self.vector_db_client = await loop.run_in_executor(
                        None,
                        lambda: FAISS.load_local(
                            folder_path=settings.FAISS_INDEX_PATH,
                            embeddings=self.embeddings_model,
                            index_name=self.collection_name
                        )
                    )
                else:
                    # Yeni bir indeks başlat
                    os.makedirs(settings.FAISS_INDEX_PATH, exist_ok=True)
                    
                    # Boş doküman listesi ile başla
                    empty_docs = []
                    if not empty_docs:  # Hiç belge yoksa geçici bir belge ekle
                        empty_docs = [Document(page_content="Temporary document", metadata={"temp": True})]
                    
                    # Embedding'ler ile indeks oluştur
                    loop = asyncio.get_event_loop()
                    empty_embeddings = await loop.run_in_executor(
                        None, 
                        lambda: self.embeddings_model.embed_documents([doc.page_content for doc in empty_docs])
                    )
                    
                    # FAISS indeksi oluştur
                    self.vector_db_client = FAISS.from_embeddings(
                        text_embeddings=list(zip([doc.page_content for doc in empty_docs], empty_embeddings)),
                        embedding=self.embeddings_model,
                        metadatas=[doc.metadata for doc in empty_docs]
                    )
                    
                    # İndeksi kaydet
                    await loop.run_in_executor(
                        None,
                        lambda: self.vector_db_client.save_local(settings.FAISS_INDEX_PATH, self.collection_name)
                    )
            
            else:
                raise ValueError(f"Unsupported vector database type: {self.vector_db_type}")
        
        except Exception as e:
            logger.error(f"Error connecting to vector database: {str(e)}")
            raise
    
    async def disconnect(self):
        """Vektör veritabanı bağlantısını kapat"""
        try:
            if self.vector_db_type == "qdrant" and self.vector_db_client:
                self.vector_db_client.close()
            elif self.vector_db_type == "weaviate" and self.vector_db_client:
                # Weaviate client için özel bir kapatma metodu yok
                pass
            elif self.vector_db_type == "pgvector" and self.vector_db_client:
                # Pool zaten kapatılacak
                pass
            elif self.vector_db_type == "faiss" and self.vector_db_client:
                # In-memory kullanım için özel bir kapatma gerekmez
                pass
            
            logger.info("Disconnected from vector database")
        except Exception as e:
            logger.error(f"Error disconnecting from vector database: {str(e)}")
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Metinler için embedding vektörleri oluştur
        
        Args:
            texts: Embedding oluşturulacak metinler listesi
            
        Returns:
            List[List[float]]: Embedding vektörleri listesi
        """
        try:
            if not texts:
                return []
            
            # Önbellekte varsa kullan
            cached_vectors = []
            texts_to_embed = []
            indices = []
            
            for i, text in enumerate(texts):
                text_hash = hash(text)
                if text_hash in self.embedding_cache:
                    cached_vectors.append((i, self.embedding_cache[text_hash]))
                else:
                    texts_to_embed.append(text)
                    indices.append(i)
            
            # Yeni embedding'leri hesapla
            if texts_to_embed:
                loop = asyncio.get_event_loop()
                new_embeddings = await loop.run_in_executor(
                    None, 
                    lambda: self.embeddings_model.embed_documents(texts_to_embed)
                )
                
                # Önbelleğe ekle
                for text, vector in zip(texts_to_embed, new_embeddings):
                    self.embedding_cache[hash(text)] = vector
            else:
                new_embeddings = []
            
            # Sonuçları birleştir
            result = [None] * len(texts)
            
            # Önbellekten gelen vektörler
            for idx, vector in cached_vectors:
                result[idx] = vector
            
            # Yeni hesaplanan vektörler
            for embed_idx, result_idx in enumerate(indices):
                result[result_idx] = new_embeddings[embed_idx]
            
            return result
        
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            return []
    
    async def add_document(
        self,
        document_id: str,
        content: str,
        metadata: Dict[str, Any],
        user_id: str,
        organization_id: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Belgeyi vektör veritabanına ekle
        
        Args:
            document_id: Belge ID
            content: Belge içeriği
            metadata: Meta veriler (başlık, dosya adı vb.)
            user_id: Kullanıcı ID
            organization_id: Organizasyon ID (opsiyonel)
            db: Veritabanı oturumu (opsiyonel)
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            # İçeriği parçalara ayır
            chunks = self.text_splitter.split_text(content)
            
            if not chunks:
                logger.warning(f"No text chunks extracted from document: {document_id}")
                return False
            
            # Belge parçalarını ve meta verileri hazırla
            chunk_data = []
            for i, chunk in enumerate(chunks):
                chunk_id = f"{document_id}_{i}"
                chunk_metadata = {
                    "document_id": document_id,
                    "chunk_id": chunk_id,
                    "chunk_index": i,
                    "user_id": user_id,
                    "organization_id": organization_id,
                    **metadata  # Diğer meta verileri ekle
                }
                chunk_data.append((chunk_id, chunk, chunk_metadata))
            
            # Embedding'leri oluştur
            chunk_texts = [chunk for _, chunk, _ in chunk_data]
            embeddings = await self.generate_embeddings(chunk_texts)
            
            if len(embeddings) != len(chunks):
                logger.error(f"Embedding count mismatch: {len(embeddings)} embeddings for {len(chunks)} chunks")
                return False
            
            # Veritabanına ekle
            if self.vector_db_type == "qdrant":
                points = []
                for i, ((chunk_id, chunk, metadata), embedding) in enumerate(zip(chunk_data, embeddings)):
                    points.append(
                        qdrant_models.PointStruct(
                            id=chunk_id,
                            vector=embedding,
                            payload={
                                "text": chunk,
                                "document_id": metadata["document_id"],
                                "user_id": metadata["user_id"],
                                "organization_id": metadata.get("organization_id"),
                                "metadata": json.dumps(metadata)
                            }
                        )
                    )
                
                # Batch olarak ekle
                self.vector_db_client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
            
            elif self.vector_db_type == "weaviate":
                with self.vector_db_client.batch as batch:
                    for i, ((chunk_id, chunk, metadata), embedding) in enumerate(zip(chunk_data, embeddings)):
                        batch.add_data_object(
                            data_object={
                                "text": chunk,
                                "document_id": metadata["document_id"],
                                "user_id": metadata["user_id"],
                                "organization_id": metadata.get("organization_id"),
                                "chunk_id": metadata["chunk_id"],
                                "metadata": metadata
                            },
                            class_name=self.collection_name,
                            uuid=chunk_id,
                            vector=embedding
                        )
            
            elif self.vector_db_type == "pgvector":
                # pgvector için SQL sorguları
                # Bu kısım veritabanı şemasına göre uyarlanmalı
                pass
            
            elif self.vector_db_type == "faiss":
                # FAISS için belge ekle
                loop = asyncio.get_event_loop()
                metadatas = [metadata for _, _, metadata in chunk_data]
                
                await loop.run_in_executor(
                    None,
                    lambda: self.vector_db_client.add_embeddings(
                        text_embeddings=list(zip(chunk_texts, embeddings)),
                        metadatas=metadatas
                    )
                )
                
                # İndeksi kaydet
                await loop.run_in_executor(
                    None,
                    lambda: self.vector_db_client.save_local(settings.FAISS_INDEX_PATH, self.collection_name)
                )
            
            # Belge verilerini veritabanına kaydet
            document_chunks = []
            for i, ((chunk_id, chunk, metadata), embedding) in enumerate(zip(chunk_data, embeddings)):
                document_chunks.append(
                    DocumentChunk(
                        id=chunk_id,
                        document_id=document_id,
                        chunk_index=i,
                        content=chunk,
                        embedding=None,  # Embedding vektörünü saklamıyoruz
                        metadata=metadata
                    )
                )
            
            # PostgreSQL veritabanına chunks kaydet
            if db:
                await self.document_repository.save_document_chunks(db, document_chunks)
            
            return True
        
        except Exception as e:
            logger.error(f"Error adding document to vector database: {str(e)}")
            return False
    
    async def delete_document(
        self,
        document_id: str,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Belgeyi vektör veritabanından sil
        
        Args:
            document_id: Belge ID
            db: Veritabanı oturumu (opsiyonel)
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            if self.vector_db_type == "qdrant":
                # Belgeye ait tüm chunk'ları sil
                self.vector_db_client.delete(
                    collection_name=self.collection_name,
                    points_selector=qdrant_models.FilterSelector(
                        filter=qdrant_models.Filter(
                            must=[
                                qdrant_models.FieldCondition(
                                    key="document_id",
                                    match=qdrant_models.MatchValue(value=document_id)
                                )
                            ]
                        )
                    )
                )
            
            elif self.vector_db_type == "weaviate":
                # Belgeye ait tüm chunk'ları sil
                self.vector_db_client.batch.delete_objects(
                    class_name=self.collection_name,
                    where={
                        "path": ["document_id"],
                        "operator": "Equal",
                        "valueString": document_id
                    }
                )
            
            elif self.vector_db_type == "pgvector":
                # pgvector için SQL sorguları
                pass
            
            elif self.vector_db_type == "faiss":
                # FAISS doğrudan bir delete operasyonu sunmaz
                # Tüm belgeyi yeniden oluşturmamız gerekebilir
                
                # Tüm verileri al
                loop = asyncio.get_event_loop()
                all_docs = await loop.run_in_executor(
                    None,
                    lambda: self.vector_db_client.similarity_search_with_score("", k=10000)
                )
                
                # Silinen belge dışındaki belgeleri filtrele
                filtered_docs = [(doc, score) for doc, score in all_docs 
                                if doc.metadata.get("document_id") != document_id]
                
                if not filtered_docs:
                    # Hiç belge kalmadı, geçici bir belge oluştur
                    empty_docs = [Document(page_content="Temporary document", metadata={"temp": True})]
                    empty_embeddings = await loop.run_in_executor(
                        None, 
                        lambda: self.embeddings_model.embed_documents([doc.page_content for doc in empty_docs])
                    )
                    
                    # Yeni indeks oluştur
                    self.vector_db_client = FAISS.from_embeddings(
                        text_embeddings=list(zip([doc.page_content for doc in empty_docs], empty_embeddings)),
                        embedding=self.embeddings_model,
                        metadatas=[doc.metadata for doc in empty_docs]
                    )
                else:
                    # Filtrelenmiş belgelerden yeni indeks oluştur
                    docs = [doc for doc, _ in filtered_docs]
                    metadatas = [doc.metadata for doc in docs]
                    texts = [doc.page_content for doc in docs]
                    embeddings = await self.generate_embeddings(texts)
                    
                    # Yeni indeks oluştur
                    self.vector_db_client = FAISS.from_embeddings(
                        text_embeddings=list(zip(texts, embeddings)),
                        embedding=self.embeddings_model,
                        metadatas=metadatas
                    )
                
                # İndeksi kaydet
                await loop.run_in_executor(
                    None,
                    lambda: self.vector_db_client.save_local(settings.FAISS_INDEX_PATH, self.collection_name)
                )
            
            # PostgreSQL'de chunk kayıtlarını sil
            if db:
                await self.document_repository.delete_document_chunks(db, document_id)
            
            return True
        
        except Exception as e:
            logger.error(f"Error deleting document from vector database: {str(e)}")
            return False
    
    async def search_documents(
        self,
        query: str,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        limit: int = 5,
        db: Optional[AsyncSession] = None
    ) -> List[Dict[str, Any]]:
        """
        Sorgu ile ilgili belgeleri bul
        
        Args:
            query: Arama sorgusu
            user_id: Kullanıcı ID (filtreleme için)
            organization_id: Organizasyon ID (filtreleme için)
            limit: Maksimum sonuç sayısı
            db: Veritabanı oturumu (opsiyonel)
            
        Returns:
            List[Dict[str, Any]]: İlgili belgeler listesi
        """
        try:
            # Sorgu embedding'i oluştur
            query_embeddings = await self.generate_embeddings([query])
            
            if not query_embeddings or len(query_embeddings) == 0:
                logger.error("Failed to generate query embedding")
                return []
            
            query_embedding = query_embeddings[0]
            
            # Arama için filtreleri hazırla
            filters = {}
            if user_id:
                filters["user_id"] = user_id
            if organization_id:
                filters["organization_id"] = organization_id
            
            results = []
            
            if self.vector_db_type == "qdrant":
                # Filtre koşullarını oluştur
                filter_conditions = []
                
                if user_id:
                    filter_conditions.append(
                        qdrant_models.FieldCondition(
                            key="user_id",
                            match=qdrant_models.MatchValue(value=user_id)
                        )
                    )
                
                if organization_id:
                    filter_conditions.append(
                        qdrant_models.FieldCondition(
                            key="organization_id",
                            match=qdrant_models.MatchValue(value=organization_id)
                        )
                    )
                
                query_filter = None
                if filter_conditions:
                    query_filter = qdrant_models.Filter(
                        must=filter_conditions
                    )
                
                # Vektör araması yap
                search_result = self.vector_db_client.search(
                    collection_name=self.collection_name,
                    query_vector=query_embedding,
                    query_filter=query_filter,
                    limit=limit
                )
                
                # Sonuçları işle
                seen_doc_ids = set()
                for hit in search_result:
                    doc_id = hit.payload.get("document_id")
                    if doc_id and doc_id not in seen_doc_ids:
                        seen_doc_ids.add(doc_id)
                        
                        # Meta verileri parse et
                        metadata = json.loads(hit.payload.get("metadata", "{}"))
                        
                        results.append({
                            "id": doc_id,
                            "chunk_id": hit.id,
                            "chunk_content": hit.payload.get("text"),
                            "score": hit.score,
                            "metadata": metadata,
                            "title": metadata.get("title", "Untitled")
                        })
            
            elif self.vector_db_type == "weaviate":
                # Sorgu oluştur
                query_builder = self.vector_db_client.query.get(
                    self.collection_name, 
                    ["document_id", "chunk_id", "text", "user_id", "organization_id", "metadata"]
                )
                
                # Filtre ekle
                if user_id or organization_id:
                    where_filter = {"operator": "And", "operands": []}
                    
                    if user_id:
                        where_filter["operands"].append({
                            "path": ["user_id"],
                            "operator": "Equal",
                            "valueString": user_id
                        })
                    
                    if organization_id:
                        where_filter["operands"].append({
                            "path": ["organization_id"],
                            "operator": "Equal",
                            "valueString": organization_id
                        })
                    
                    query_builder = query_builder.with_where(where_filter)
                
                # Vektör araması yap
                search_result = query_builder.with_near_vector({
                    "vector": query_embedding,
                    "certainty": 0.7
                }).with_limit(limit).do()
                
                # Sonuçları işle
                if search_result and "data" in search_result:
                    objects = search_result["data"]["Get"][self.collection_name]
                    
                    seen_doc_ids = set()
                    for obj in objects:
                        doc_id = obj.get("document_id")
                        if doc_id and doc_id not in seen_doc_ids:
                            seen_doc_ids.add(doc_id)
                            
                            # Weaviate'in certainty değerini skora çevir
                            certainty = obj.get("_additional", {}).get("certainty", 0)
                            score = certainty if certainty is not None else 0
                            
                            results.append({
                                "id": doc_id,
                                "chunk_id": obj.get("chunk_id"),
                                "chunk_content": obj.get("text"),
                                "score": score,
                                "metadata": obj.get("metadata", {}),
                                "title": obj.get("metadata", {}).get("title", "Untitled")
                            })
            
            elif self.vector_db_type == "pgvector":
                # pgvector için SQL sorguları
                pass
            
            elif self.vector_db_type == "faiss":
                # FAISS ile benzerlik araması
                filter_dict = {}
                if user_id:
                    filter_dict["user_id"] = user_id
                if organization_id:
                    filter_dict["organization_id"] = organization_id
                
                loop = asyncio.get_event_loop()
                
                # Metadatas filtreleme fonksiyonu
                def filter_func(metadata):
                    if not filter_dict:
                        return True
                    
                    for key, value in filter_dict.items():
                        if metadata.get(key) != value:
                            return False
                    return True
                
                # Arama yap
                docs_with_scores = await loop.run_in_executor(
                    None,
                    lambda: self.vector_db_client.similarity_search_with_score_by_vector(
                        query_embedding, 
                        k=limit*2,  # Daha fazla sonuç alıp filtreleyeceğiz
                        filter=filter_func if filter_dict else None
                    )
                )
                
                # Sonuçları işle
                seen_doc_ids = set()
                for doc, score in docs_with_scores:
                    doc_id = doc.metadata.get("document_id")
                    if doc_id and doc_id not in seen_doc_ids and len(seen_doc_ids) < limit:
                        seen_doc_ids.add(doc_id)
                        
                        # Skoru normalize et (FAISS'de uzaklık olarak gelir, benzerliğe çevir)
                        similarity = 1.0 / (1.0 + score)
                        
                        results.append({
                            "id": doc_id,
                            "chunk_id": doc.metadata.get("chunk_id"),
                            "chunk_content": doc.page_content,
                            "score": similarity,
                            "metadata": doc.metadata,
                            "title": doc.metadata.get("title", "Untitled")
                        })
            
            # Tam belge bilgilerini veritabanından al
            if db and results:
                doc_ids = [result["id"] for result in results]
                documents = await self.document_repository.get_documents_by_ids(db, doc_ids, user_id)
                
                # Belge bilgilerini eşleştir
                doc_map = {str(doc.id): doc for doc in documents}
                
                for result in results:
                    doc_id = result["id"]
                    if doc_id in doc_map:
                        doc = doc_map[doc_id]
                        result["title"] = doc.title
                        result["description"] = doc.description
                        result["created_at"] = doc.created_at.isoformat() if doc.created_at else None
                        result["updated_at"] = doc.updated_at.isoformat() if doc.updated_at else None
            
            # Sonuçları skora göre sırala
            results.sort(key=lambda x: x.get("score", 0), reverse=True)
            
            return results[:limit]
        
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            return []