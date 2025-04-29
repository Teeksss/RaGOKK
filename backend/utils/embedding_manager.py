# Last reviewed: 2025-04-29 09:08:04 UTC (User: Teekssseskileri)
from typing import List, Dict, Any, Optional, Union
import numpy as np
import os
import json
import time
import asyncio
from enum import Enum

from .config import (
    SEMANTIC_MODEL, VECTOR_DIMENSION, MULTILINGUAL_EMBEDDINGS_MODEL,
    EMBEDDING_PROVIDER, OPENAI_API_KEY, COHERE_API_KEY, JINA_API_KEY,
    EMBEDDING_BATCH_SIZE, EMBEDDING_CACHE_ENABLED, EMBEDDING_CACHE_SIZE
)
from .logger import get_logger

# Lazy imports
sentence_transformers = None
openai = None
cohere = None
httpx = None

logger = get_logger(__name__)

class EmbeddingProvider(str, Enum):
    SENTENCE_TRANSFORMER = "sentence_transformer"
    OPENAI = "openai"
    COHERE = "cohere"
    JINA = "jina"

class EmbeddingManager:
    """Farklı embedding model sağlayıcıları arasında geçiş yapabilen manager"""
    
    def __init__(self):
        self.provider = EmbeddingProvider(EMBEDDING_PROVIDER) if EMBEDDING_PROVIDER else EmbeddingProvider.SENTENCE_TRANSFORMER
        self.sentence_transformers_model = None
        self.openai_client = None
        self.cohere_client = None
        self.jina_client = None
        self.default_model_name = SEMANTIC_MODEL
        self.multilingual_model_name = MULTILINGUAL_EMBEDDINGS_MODEL
        self.vector_dimension = VECTOR_DIMENSION
        self.batch_size = EMBEDDING_BATCH_SIZE
        
        # Embedding cache
        self.cache_enabled = EMBEDDING_CACHE_ENABLED
        self.cache_size = EMBEDDING_CACHE_SIZE
        self._cache = {}
        
        logger.info(f"Embedding Manager başlatıldı: {self.provider} (default model: {self.default_model_name})")
    
    async def get_embedding(
        self, 
        text: str, 
        model_name: Optional[str] = None,
        provider: Optional[EmbeddingProvider] = None
    ) -> List[float]:
        """Metin için embedding vektörü oluşturur"""
        if not text.strip():
            # Boş metin için sıfır vektörü döndür
            return [0.0] * self.vector_dimension
            
        # Cache kontrolü
        if self.cache_enabled:
            cache_key = self._get_cache_key(text, model_name, provider)
            if cache_key in self._cache:
                return self._cache[cache_key]
        
        # Kullanılacak provider ve model belirleme
        use_provider = provider if provider else self.provider
        use_model = model_name if model_name else self.default_model_name
        
        # Multilingual model adı kontrolü
        if not model_name and use_model == "multilingual":
            use_model = self.multilingual_model_name
        
        # Uygun provider ile embedding oluştur
        embedding = None
        start_time = time.time()
        
        try:
            if use_provider == EmbeddingProvider.SENTENCE_TRANSFORMER:
                embedding = await self._get_sentence_transformers_embedding(text, use_model)
            elif use_provider == EmbeddingProvider.OPENAI:
                embedding = await self._get_openai_embedding(text, use_model)
            elif use_provider == EmbeddingProvider.COHERE:
                embedding = await self._get_cohere_embedding(text, use_model)
            elif use_provider == EmbeddingProvider.JINA:
                embedding = await self._get_jina_embedding(text, use_model)
            else:
                logger.error(f"Bilinmeyen embedding provider: {use_provider}")
                # Yedek olarak Sentence Transformers kullan
                embedding = await self._get_sentence_transformers_embedding(text, self.default_model_name)
            
            # Oluşturma süresini logla
            elapsed = time.time() - start_time
            logger.debug(f"Embedding oluşturuldu: {elapsed:.2f}s ({use_provider}, {use_model})")
            
            # Cache'e ekle
            if self.cache_enabled and embedding is not None:
                self._update_cache(text, embedding, model_name, provider)
                
            return embedding
            
        except Exception as e:
            logger.error(f"Embedding oluşturma hatası: {e}")
            # Boş vektör döndür
            return [0.0] * self.vector_dimension
    
    async def get_embeddings_batch(
        self, 
        texts: List[str], 
        model_name: Optional[str] = None,
        provider: Optional[EmbeddingProvider] = None
    ) -> List[List[float]]:
        """Metin listesi için batch embedding vektörleri oluşturur"""
        if not texts:
            return []
            
        # Kullanılacak provider ve model belirleme
        use_provider = provider if provider else self.provider
        use_model = model_name if model_name else self.default_model_name
        
        # Multilingual model adı kontrolü
        if not model_name and use_model == "multilingual":
            use_model = self.multilingual_model_name
        
        # Cache'den kontrol ve eksik olanları belirleme
        uncached_texts = []
        uncached_indices = []
        result_embeddings = [None] * len(texts)
        
        if self.cache_enabled:
            for i, text in enumerate(texts):
                cache_key = self._get_cache_key(text, model_name, provider)
                if cache_key in self._cache:
                    result_embeddings[i] = self._cache[cache_key]
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i)
        else:
            uncached_texts = texts
            uncached_indices = list(range(len(texts)))
        
        # Hiç eksik yoksa direkt döndür
        if not uncached_texts:
            return result_embeddings
            
        # Batch boyutuna göre işle
        batch_size = self.batch_size
        all_embeddings = []
        
        for i in range(0, len(uncached_texts), batch_size):
            batch_texts = uncached_texts[i:i+batch_size]
            
            # Uygun provider ile batch embedding oluştur
            batch_embeddings = None
            start_time = time.time()
            
            try:
                if use_provider == EmbeddingProvider.SENTENCE_TRANSFORMER:
                    batch_embeddings = await self._get_sentence_transformers_batch_embedding(batch_texts, use_model)
                elif use_provider == EmbeddingProvider.OPENAI:
                    batch_embeddings = await self._get_openai_batch_embedding(batch_texts, use_model)
                elif use_provider == EmbeddingProvider.COHERE:
                    batch_embeddings = await self._get_cohere_batch_embedding(batch_texts, use_model)
                elif use_provider == EmbeddingProvider.JINA:
                    batch_embeddings = await self._get_jina_batch_embedding(batch_texts, use_model)
                else:
                    logger.error(f"Bilinmeyen batch embedding provider: {use_provider}")
                    # Yedek olarak Sentence Transformers kullan
                    batch_embeddings = await self._get_sentence_transformers_batch_embedding(batch_texts, self.default_model_name)
                
                # Oluşturma süresini logla
                elapsed = time.time() - start_time
                logger.debug(f"Batch embedding oluşturuldu ({len(batch_texts)} metin): {elapsed:.2f}s ({use_provider}, {use_model})")
                
                # Cache'e ekle
                if self.cache_enabled and batch_embeddings:
                    for j, (text, embedding) in enumerate(zip(batch_texts, batch_embeddings)):
                        self._update_cache(text, embedding, model_name, provider)
                
                all_embeddings.extend(batch_embeddings if batch_embeddings else [[0.0] * self.vector_dimension] * len(batch_texts))
                
            except Exception as e:
                logger.error(f"Batch embedding oluşturma hatası: {e}")
                # Boş vektörler döndür
                batch_zeros = [[0.0] * self.vector_dimension] * len(batch_texts)
                all_embeddings.extend(batch_zeros)
        
        # Sonuçları birleştir
        for i, embedding in zip(uncached_indices, all_embeddings):
            result_embeddings[i] = embedding
            
        return result_embeddings
    
    async def _get_sentence_transformers_embedding(self, text: str, model_name: str) -> List[float]:
        """Sentence Transformers kullanarak embedding oluşturur"""
        # Lazy import
        global sentence_transformers
        if sentence_transformers is None:
            try:
                import sentence_transformers
            except ImportError:
                logger.error("sentence_transformers kütüphanesi bulunamadı.")
                raise ImportError("sentence_transformers kütüphanesi yüklenmiş mi?")
            
        if self.sentence_transformers_model is None or self.sentence_transformers_model.get_name() != model_name:
            # Modeli yükle
            self.sentence_transformers_model = await asyncio.to_thread(
                sentence_transformers.SentenceTransformer, model_name
            )
        
        # CPU-bound işlem olduğu için thread pool'da yürüt
        embedding = await asyncio.to_thread(
            self.sentence_transformers_model.encode, 
            text, 
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        
        # NumPy array'i liste dönüştür
        return embedding.tolist()
    
    async def _get_sentence_transformers_batch_embedding(self, texts: List[str], model_name: str) -> List[List[float]]:
        """Sentence Transformers kullanarak batch embedding oluşturur"""
        # Lazy import
        global sentence_transformers
        if sentence_transformers is None:
            try:
                import sentence_transformers
            except ImportError:
                logger.error("sentence_transformers kütüphanesi bulunamadı.")
                raise ImportError("sentence_transformers kütüphanesi yüklenmiş mi?")
            
        if self.sentence_transformers_model is None or self.sentence_transformers_model.get_name() != model_name:
            # Modeli yükle
            self.sentence_transformers_model = await asyncio.to_thread(
                sentence_transformers.SentenceTransformer, model_name
            )
        
        # CPU-bound işlem olduğu için thread pool'da yürüt
        embeddings = await asyncio.to_thread(
            self.sentence_transformers_model.encode, 
            texts, 
            convert_to_numpy=True,
            normalize_embeddings=True,
            batch_size=self.batch_size
        )
        
        # NumPy array'i liste dönüştür
        return embeddings.tolist()
    
    async def _get_openai_embedding(self, text: str, model_name: str) -> List[float]:
        """OpenAI API kullanarak embedding oluşturur"""
        global openai
        if openai is None:
            try:
                import openai
            except ImportError:
                logger.error("openai kütüphanesi bulunamadı.")
                raise ImportError("openai kütüphanesi yüklenmiş mi?")
        
        if not OPENAI_API_KEY:
            logger.error("OpenAI API Key bulunamadı")
            raise ValueError("OpenAI API Key missing")
        
        if self.openai_client is None:
            self.openai_client = openai.AsyncClient(api_key=OPENAI_API_KEY)
        
        # API'da kullanılacak model adını kontrol et
        api_model_name = model_name
        if model_name in ["default", "multilingual"]:
            api_model_name = "text-embedding-3-large"
        
        try:
            response = await self.openai_client.embeddings.create(
                input=[text],
                model=api_model_name
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"OpenAI embedding hatası: {e}")
            raise
    
    async def _get_openai_batch_embedding(self, texts: List[str], model_name: str) -> List[List[float]]:
        """OpenAI API kullanarak batch embedding oluşturur"""
        global openai
        if openai is None:
            try:
                import openai
            except ImportError:
                logger.error("openai kütüphanesi bulunamadı.")
                raise ImportError("openai kütüphanesi yüklenmiş mi?")
        
        if not OPENAI_API_KEY:
            logger.error("OpenAI API Key bulunamadı")
            raise ValueError("OpenAI API Key missing")
        
        if self.openai_client is None:
            self.openai_client = openai.AsyncClient(api_key=OPENAI_API_KEY)
        
        # API'da kullanılacak model adını kontrol et
        api_model_name = model_name
        if model_name in ["default", "multilingual"]:
            api_model_name = "text-embedding-3-large"
        
        try:
            response = await self.openai_client.embeddings.create(
                input=texts,
                model=api_model_name
            )
            
            # Sırayı korumak için embeddings sözlüğü oluştur
            embeddings_dict = {item.index: item.embedding for item in response.data}
            
            # Sıralı listeyi döndür
            return [embeddings_dict[i] for i in range(len(texts))]
            
        except Exception as e:
            logger.error(f"OpenAI batch embedding hatası: {e}")
            raise
    
    async def _get_cohere_embedding(self, text: str, model_name: str) -> List[float]:
        """Cohere API kullanarak embedding oluşturur"""
        global cohere
        if cohere is None:
            try:
                import cohere
            except ImportError:
                logger.error("cohere kütüphanesi bulunamadı.")
                raise ImportError("cohere kütüphanesi yüklenmiş mi?")
        
        if not COHERE_API_KEY:
            logger.error("Cohere API Key bulunamadı")
            raise ValueError("Cohere API Key missing")
        
        if self.cohere_client is None:
            self.cohere_client = cohere.AsyncClient(COHERE_API_KEY)
        
        # API'da kullanılacak model adını kontrol et
        api_model_name = model_name
        if model_name in ["default"]:
            api_model_name = "embed-english-v3.0"
        elif model_name in ["multilingual"]:
            api_model_name = "embed-multilingual-v3.0"
        
        try:
            response = await self.cohere_client.embed(
                texts=[text],
                model=api_model_name,
                input_type="search_document"
            )
            
            return response.embeddings[0]
            
        except Exception as e:
            logger.error(f"Cohere embedding hatası: {e}")
            raise
    
    async def _get_cohere_batch_embedding(self, texts: List[str], model_name: str) -> List[List[float]]:
        """Cohere API kullanarak batch embedding oluşturur"""
        global cohere
        if cohere is None:
            try:
                import cohere
            except ImportError:
                logger.error("cohere kütüphanesi bulunamadı.")
                raise ImportError("cohere kütüphanesi yüklenmiş mi?")
        
        if not COHERE_API_KEY:
            logger.error("Cohere API Key bulunamadı")
            raise ValueError("Cohere API Key missing")
        
        if self.cohere_client is None:
            self.cohere_client = cohere.AsyncClient(COHERE_API_KEY)
        
        # API'da kullanılacak model adını kontrol et
        api_model_name = model_name
        if model_name in ["default"]:
            api_model_name = "embed-english-v3.0"
        elif model_name in ["multilingual"]:
            api_model_name = "embed-multilingual-v3.0"
        
        try:
            response = await self.cohere_client.embed(
                texts=texts,
                model=api_model_name,
                input_type="search_document"
            )
            
            return response.embeddings
            
        except Exception as e:
            logger.error(f"Cohere batch embedding hatası: {e}")
            raise
    
    async def _get_jina_embedding(self, text: str, model_name: str) -> List[float]:
        """Jina API kullanarak embedding oluşturur"""
        global httpx
        if httpx is None:
            try:
                import httpx
            except ImportError:
                logger.error("httpx kütüphanesi bulunamadı.")
                raise ImportError("httpx kütüphanesi yüklenmiş mi?")
        
        if not JINA_API_KEY:
            logger.error("Jina API Key bulunamadı")
            raise ValueError("Jina API Key missing")
        
        # API'da kullanılacak model adını kontrol et
        api_model_name = model_name
        if model_name in ["default", "multilingual"]:
            api_model_name = "jina-embeddings-v2-base-en"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {JINA_API_KEY}"
        }
        
        data = {
            "texts": [text],
            "model": api_model_name
        }
        
        try:
            # Async HTTP çağrısı yap
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.jina.ai/v1/embeddings",
                    headers=headers,
                    json=data
                )
                response.raise_for_status()
                result = response.json()
                
                return result["embeddings"][0]
            
        except Exception as e:
            logger.error(f"Jina embedding hatası: {e}")
            raise
    
    async def _get_jina_batch_embedding(self, texts: List[str], model_name: str) -> List[List[float]]:
        """Jina API kullanarak batch embedding oluşturur"""
        global httpx
        if httpx is None:
            try:
                import httpx
            except ImportError:
                logger.error("httpx kütüphanesi bulunamadı.")
                raise ImportError("httpx kütüphanesi yüklenmiş mi?")
        
        if not JINA_API_KEY:
            logger.error("Jina API Key bulunamadı")
            raise ValueError("Jina API Key missing")
        
        # API'da kullanılacak model adını kontrol et
        api_model_name = model_name
        if model_name in ["default", "multilingual"]:
            api_model_name = "jina-embeddings-v2-base-en"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {JINA_API_KEY}"
        }
        
        data = {
            "texts": texts,
            "model": api_model_name
        }
        
        try:
            # Async HTTP çağrısı yap
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.jina.ai/v1/embeddings",
                    headers=headers,
                    json=data,
                    timeout=60.0
                )
                response.raise_for_status()
                result = response.json()
                
                return result["embeddings"]
            
        except Exception as e:
            logger.error(f"Jina batch embedding hatası: {e}")
            raise
    
    def _get_cache_key(self, text: str, model_name: Optional[str], provider: Optional[EmbeddingProvider]) -> str:
        """Cache için anahtar oluşturur"""
        use_provider = provider if provider else self.provider
        use_model = model_name if model_name else self.default_model_name
        
        if use_model == "multilingual":
            use_model = self.multilingual_model_name
            
        # Hash oluştur: provider_model_texthash
        import hashlib
        text_hash = hashlib.md5(text.encode()).hexdigest()
        return f"{use_provider}_{use_model}_{text_hash}"
    
    def _update_cache(self, text: str, embedding: List[float], model_name: Optional[str], provider: Optional[EmbeddingProvider]) -> None:
        """Cache'i günceller ve boyut sınırlarını kontrol eder"""
        cache_key = self._get_cache_key(text, model_name, provider)
        self._cache[cache_key] = embedding
        
        # Cache boyutunu kontrol et
        if len(self._cache) > self.cache_size:
            # En eski girişleri kaldır (basit LRU yerine)
            items = list(self._cache.items())
            self._cache = dict(items[-self.cache_size:])

# Embedding manager singleton
embedding_manager = EmbeddingManager()