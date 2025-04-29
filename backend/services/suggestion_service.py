# Last reviewed: 2025-04-29 13:51:41 UTC (User: TeeksssArama)
import logging
import json
import asyncio
import datetime
from typing import List, Dict, Any, Optional, Union, Tuple
import re
import heapq
import collections
import math

from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import NotFoundError, RequestError
import redis.asyncio as redis

from ..config import settings
from ..repositories.search_history_repository import SearchHistoryRepository

logger = logging.getLogger(__name__)

class SuggestionType(str):
    """Öneri türleri"""
    COMPLETION = "completion"  # Kelime tamamlama önerisi
    POPULAR = "popular"  # Popüler aramalar
    RECENT = "recent"  # Yakın zamanda yapılan aramalar
    RELATED = "related"  # İlgili aramalar
    CURATED = "curated"  # Manuel olarak eklenen öneriler

class SuggestionSource(str):
    """Öneri kaynakları"""
    INDEX = "index"  # İndeks verileri
    HISTORY = "history"  # Arama geçmişi
    USER_HISTORY = "user_history"  # Kullanıcı arama geçmişi
    MANUAL = "manual"  # Manuel olarak eklenen öneriler

class SuggestionService:
    """
    Arama önerileri ve otomatik tamamlama servisi
    
    Bu servis şunları sağlar:
    - Elasticsearch üzerinden otomatik tamamlama
    - Popüler ve yakın zamanlı aramalar
    - İlgili arama önerileri
    - Önbellek kullanımı ile hızlı yanıt süresi
    """
    
    def __init__(self):
        """Öneri servisi başlatma"""
        self.es_client = None
        self.redis_client = None
        self.search_history_repository = SearchHistoryRepository()
        
        # Elasticsearch için yapılandırma
        self.suggestions_index = settings.ELASTICSEARCH_SUGGESTIONS_INDEX
        self.documents_index = settings.ELASTICSEARCH_DOCUMENTS_INDEX
        
        # Redis için yapılandırma
        self.suggestions_cache_ttl = 3600  # 1 saat
        self.popular_cache_ttl = 43200  # 12 saat
        self.suggestions_cache_prefix = "suggestion:"
        
        # NGram ve edge ngram ayarları
        self.min_ngram_size = 2
        self.max_ngram_size = 20
        
        # Completion ayarları
        self.max_completions = 10
        self.min_completion_length = 2
        self.fuzzy_completions = True
    
    async def connect(self):
        """ES ve Redis istemcilerini oluştur"""
        # Elasticsearch bağlantısı
        if settings.ELASTICSEARCH_ENABLED:
            self.es_client = AsyncElasticsearch(
                hosts=[settings.ELASTICSEARCH_URL],
                http_auth=(settings.ELASTICSEARCH_USER, settings.ELASTICSEARCH_PASSWORD),
                verify_certs=settings.ELASTICSEARCH_VERIFY_CERTS
            )
            logger.info("Suggestion service connected to Elasticsearch")
            
            # Suggestion indeksini kontrol et/oluştur
            await self._check_suggestion_index()
        
        # Redis bağlantısı
        if settings.REDIS_URL:
            self.redis_client = redis.from_url(settings.REDIS_URL)
            logger.info("Suggestion service connected to Redis")
    
    async def disconnect(self):
        """Bağlantıları kapat"""
        if self.es_client:
            await self.es_client.close()
            logger.info("Suggestion service disconnected from Elasticsearch")
        
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Suggestion service disconnected from Redis")
    
    async def _check_suggestion_index(self):
        """Elasticsearch'te suggestion indeksini kontrol et/oluştur"""
        # İndeks var mı kontrol et
        try:
            index_exists = await self.es_client.indices.exists(index=self.suggestions_index)
            
            if not index_exists:
                # İndeksi oluştur
                await self._create_suggestion_index()
                logger.info(f"Created suggestions index: {self.suggestions_index}")
            else:
                logger.info(f"Suggestions index exists: {self.suggestions_index}")
        
        except Exception as e:
            logger.error(f"Error checking suggestion index: {str(e)}")
    
    async def _create_suggestion_index(self):
        """Öneri indeksi oluştur"""
        index_settings = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 1,
                "analysis": {
                    "analyzer": {
                        "autocomplete": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "autocomplete_filter"]
                        },
                        "autocomplete_search": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase"]
                        }
                    },
                    "filter": {
                        "autocomplete_filter": {
                            "type": "edge_ngram",
                            "min_gram": self.min_ngram_size,
                            "max_gram": self.max_ngram_size
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "suggest": {
                        "type": "completion",
                        "analyzer": "autocomplete",
                        "search_analyzer": "autocomplete_search"
                    },
                    "text": {
                        "type": "text",
                        "analyzer": "autocomplete",
                        "search_analyzer": "autocomplete_search",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256
                            }
                        }
                    },
                    "type": {
                        "type": "keyword"
                    },
                    "source": {
                        "type": "keyword"
                    },
                    "weight": {
                        "type": "integer"
                    },
                    "context": {
                        "type": "keyword"
                    },
                    "metadata": {
                        "type": "object",
                        "enabled": True
                    },
                    "created_at": {
                        "type": "date"
                    },
                    "updated_at": {
                        "type": "date"
                    }
                }
            }
        }
        
        await self.es_client.indices.create(
            index=self.suggestions_index,
            body=index_settings
        )
    
    async def get_completions(
        self,
        prefix: str,
        types: List[str] = None,
        contexts: List[str] = None,
        limit: int = 5,
        user_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        Verilen ön eke göre tamamlama önerileri döndürür
        
        Args:
            prefix: Arama ön eki
            types: Öneri türleri (Ör. ["completion", "popular"])
            contexts: Bağlam filtreleri (Ör. ["documents", "collections"])
            limit: Maksimum öneri sayısı
            user_id: Kullanıcı ID'si (kişiselleştirilmiş öneriler için)
            
        Returns:
            List[Dict[str, Any]]: Önerilerin listesi
        """
        if not prefix or len(prefix) < self.min_completion_length:
            logger.debug(f"Prefix too short: {prefix}")
            return []
        
        # Default değerler
        types = types or [SuggestionType.COMPLETION, SuggestionType.POPULAR, SuggestionType.RECENT]
        contexts = contexts or ["documents"]
        
        # Önbellekten sonuçları kontrol et
        cache_key = f"{self.suggestions_cache_prefix}completion:{prefix}:{'-'.join(types)}:{'-'.join(contexts)}:{limit}"
        if user_id:
            cache_key += f":{user_id}"
        
        if self.redis_client:
            try:
                cached = await self.redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Redis cache error: {str(e)}")
        
        # Elasticsearch'ten öneriler al
        try:
            # Suggestion sorgusu oluştur
            suggestion_query = {
                "suggest": {
                    "text": prefix,
                    "completion": {
                        "field": "suggest",
                        "size": limit,
                        "fuzzy": self.fuzzy_completions,
                        "skip_duplicates": True
                    }
                }
            }
            
            # Context filtreleme
            if contexts:
                suggestion_query["suggest"]["completion"]["contexts"] = {
                    "context": contexts
                }
            
            # Sorguyu çalıştır
            response = await self.es_client.search(
                index=self.suggestions_index,
                body=suggestion_query
            )
            
            # Sonuçları işle
            suggestions = []
            for suggestion in response["suggest"]["completion"][0]["options"]:
                suggestion_data = {
                    "text": suggestion["text"],
                    "score": suggestion["_score"],
                    "type": suggestion["_source"].get("type", SuggestionType.COMPLETION),
                    "source": suggestion["_source"].get("source", SuggestionSource.INDEX)
                }
                
                # Varsa metadatayı ekle
                if "metadata" in suggestion["_source"]:
                    suggestion_data["metadata"] = suggestion["_source"]["metadata"]
                
                suggestions.append(suggestion_data)
            
            # Sonuçları önbellekle
            if self.redis_client:
                try:
                    await self.redis_client.set(
                        cache_key,
                        json.dumps(suggestions),
                        ex=self.suggestions_cache_ttl
                    )
                except Exception as e:
                    logger.warning(f"Redis cache set error: {str(e)}")
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Elasticsearch completion error: {str(e)}")
            return []
    
    async def get_popular_searches(
        self,
        limit: int = 10,
        days: int = 30,
        context: str = None
    ) -> List[Dict[str, Any]]:
        """
        Popüler aramaları döndür
        
        Args:
            limit: Maksimum öneri sayısı
            days: Son kaç günün arama geçmişi alınacak
            context: Bağlam filtresi
            
        Returns:
            List[Dict[str, Any]]: Popüler aramalar listesi
        """
        # Önbellek kontrolü
        cache_key = f"{self.suggestions_cache_prefix}popular:{limit}:{days}:{context or 'all'}"
        
        if self.redis_client:
            try:
                cached = await self.redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Redis cache error: {str(e)}")
        
        # Veritabanından popüler aramaları al
        popular_searches = await self.search_history_repository.get_popular_searches(limit, days, context)
        
        # Sonuçları formatla
        result = []
        for search in popular_searches:
            result.append({
                "text": search["query"],
                "count": search["count"],
                "type": SuggestionType.POPULAR,
                "source": SuggestionSource.HISTORY
            })
        
        # Sonuçları önbellekle
        if self.redis_client and result:
            try:
                await self.redis_client.set(
                    cache_key,
                    json.dumps(result),
                    ex=self.popular_cache_ttl
                )
            except Exception as e:
                logger.warning(f"Redis cache set error: {str(e)}")
        
        return result
    
    async def get_recent_searches(
        self,
        user_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Kullanıcının son aramalarını döndür
        
        Args:
            user_id: Kullanıcı ID'si
            limit: Maksimum öneri sayısı
            
        Returns:
            List[Dict[str, Any]]: Son aramalar listesi
        """
        if not user_id:
            return []
        
        # Veritabanından kullanıcının son aramalarını al
        recent_searches = await self.search_history_repository.get_user_searches(user_id, limit)
        
        # Sonuçları formatla
        result = []
        for search in recent_searches:
            result.append({
                "text": search["query"],
                "timestamp": search["timestamp"].isoformat(),
                "type": SuggestionType.RECENT,
                "source": SuggestionSource.USER_HISTORY,
                "metadata": {
                    "results": search.get("result_count", 0)
                }
            })
        
        return result
    
    async def get_related_searches(
        self,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        İlgili aramaları döndür
        
        Args:
            query: Arama sorgusu
            limit: Maksimum öneri sayısı
            
        Returns:
            List[Dict[str, Any]]: İlgili aramalar listesi
        """
        if not query or len(query) < 3:
            return []
        
        # Önbellek kontrolü
        cache_key = f"{self.suggestions_cache_prefix}related:{query}:{limit}"
        
        if self.redis_client:
            try:
                cached = await self.redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Redis cache error: {str(e)}")
        
        # More Like This sorgusu kullanarak benzer aramaları bul
        try:
            related_query = {
                "query": {
                    "more_like_this": {
                        "fields": ["text"],
                        "like": query,
                        "min_term_freq": 1,
                        "max_query_terms": 12,
                        "min_doc_freq": 1
                    }
                },
                "size": limit
            }
            
            response = await self.es_client.search(
                index=self.suggestions_index,
                body=related_query
            )
            
            # Sonuçları işle
            result = []
            for hit in response["hits"]["hits"]:
                result.append({
                    "text": hit["_source"]["text"],
                    "score": hit["_score"],
                    "type": SuggestionType.RELATED,
                    "source": hit["_source"].get("source", SuggestionSource.INDEX)
                })
            
            # Sonuçları önbellekle
            if self.redis_client and result:
                try:
                    await self.redis_client.set(
                        cache_key,
                        json.dumps(result),
                        ex=self.suggestions_cache_ttl
                    )
                except Exception as e:
                    logger.warning(f"Redis cache set error: {str(e)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Elasticsearch related search error: {str(e)}")
            return []
    
    async def record_search(
        self,
        query: str,
        user_id: str = None,
        result_count: int = 0,
        context: str = None
    ) -> bool:
        """
        Arama sorgusu kaydet
        
        Args:
            query: Arama sorgusu
            user_id: Kullanıcı ID'si
            result_count: Bulunan sonuç sayısı 
            context: Arama bağlamı (örn. "documents", "users")
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            # Veritabanına kaydet
            search_id = await self.search_history_repository.add_search(
                query=query,
                user_id=user_id,
                result_count=result_count,
                context=context
            )
            
            # Öneri olarak ekle
            await self._add_suggestion_from_search(
                query=query,
                user_id=user_id,
                result_count=result_count,
                context=context
            )
            
            return True
        except Exception as e:
            logger.error(f"Error recording search: {str(e)}")
            return False
    
    async def _add_suggestion_from_search(
        self,
        query: str,
        user_id: str = None,
        result_count: int = 0,
        context: str = None
    ):
        """
        Arama sorgusundan öneri oluştur
        
        Args:
            query: Arama sorgusu
            user_id: Kullanıcı ID'si
            result_count: Bulunan sonuç sayısı
            context: Arama bağlamı
        """
        if not query or len(query) < 3:
            return
        
        try:
            # Suggestion belgesi oluştur
            suggestion_doc = {
                "suggest": {
                    "input": query,
                    "weight": 1  # Başlangıç ağırlığı
                },
                "text": query,
                "type": SuggestionType.COMPLETION,
                "source": SuggestionSource.HISTORY,
                "weight": 1,
                "created_at": datetime.datetime.utcnow().isoformat(),
                "updated_at": datetime.datetime.utcnow().isoformat(),
                "metadata": {
                    "result_count": result_count
                }
            }
            
            # Bağlamı ekle
            if context:
                suggestion_doc["context"] = context
                suggestion_doc["suggest"]["contexts"] = {
                    "context": [context]
                }
            
            # Kullanıcı bilgisini ekle
            if user_id:
                suggestion_doc["metadata"]["user_id"] = user_id
            
            # Varolan suggestion güncelle veya yeni oluştur
            query_text = query.lower().strip()
            
            # Önce mevcut öneriyi kontrol et
            try:
                existing_query = {
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"text.keyword": query_text}},
                                {"term": {"type": SuggestionType.COMPLETION}}
                            ]
                        }
                    }
                }
                
                if context:
                    existing_query["query"]["bool"]["must"].append({"term": {"context": context}})
                
                response = await self.es_client.search(
                    index=self.suggestions_index,
                    body=existing_query
                )
                
                # Mevcut öneri güncelle
                if response["hits"]["total"]["value"] > 0:
                    existing_id = response["hits"]["hits"][0]["_id"]
                    existing_source = response["hits"]["hits"][0]["_source"]
                    
                    # Ağırlığı artır
                    weight = existing_source.get("weight", 1) + 1
                    
                    # Güncellenecek alanlar
                    update_doc = {
                        "weight": weight,
                        "suggest": {
                            "input": query,
                            "weight": weight
                        },
                        "updated_at": datetime.datetime.utcnow().isoformat()
                    }
                    
                    # Sonuç sayısını güncelle
                    if result_count > 0:
                        update_doc["metadata"] = {"result_count": result_count}
                        if user_id:
                            update_doc["metadata"]["user_id"] = user_id
                    
                    # Güncelle
                    await self.es_client.update(
                        index=self.suggestions_index,
                        id=existing_id,
                        body={"doc": update_doc}
                    )
                    
                    logger.debug(f"Updated suggestion: {query} (weight: {weight})")
                    return
            
            except Exception as e:
                logger.warning(f"Error checking existing suggestion: {str(e)}")
            
            # Yeni öneri oluştur
            await self.es_client.index(
                index=self.suggestions_index,
                body=suggestion_doc,
                refresh=True
            )
            
            logger.debug(f"Added new suggestion: {query}")
            
        except Exception as e:
            logger.error(f"Error adding suggestion from search: {str(e)}")
    
    async def add_manual_suggestion(
        self,
        text: str,
        weight: int = 10,
        context: str = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Manuel öneri ekle
        
        Args:
            text: Öneri metni
            weight: Ağırlık (önem)
            context: Bağlam (örn. "documents", "collections")
            metadata: Ek meta veriler
            
        Returns:
            Dict[str, Any]: Eklenen öneri bilgileri
        """
        try:
            # Suggestion belgesi oluştur
            suggestion_doc = {
                "suggest": {
                    "input": text,
                    "weight": weight
                },
                "text": text,
                "type": SuggestionType.CURATED,
                "source": SuggestionSource.MANUAL,
                "weight": weight,
                "created_at": datetime.datetime.utcnow().isoformat(),
                "updated_at": datetime.datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }
            
            # Bağlamı ekle
            if context:
                suggestion_doc["context"] = context
                suggestion_doc["suggest"]["contexts"] = {
                    "context": [context]
                }
            
            # Öneriyi ekle
            response = await self.es_client.index(
                index=self.suggestions_index,
                body=suggestion_doc,
                refresh=True
            )
            
            return {
                "id": response["_id"],
                "text": text,
                "weight": weight,
                "context": context,
                "type": SuggestionType.CURATED,
                "source": SuggestionSource.MANUAL
            }
            
        except Exception as e:
            logger.error(f"Error adding manual suggestion: {str(e)}")
            raise
    
    async def delete_suggestion(self, suggestion_id: str) -> bool:
        """
        Öneri sil
        
        Args:
            suggestion_id: Öneri ID'si
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            response = await self.es_client.delete(
                index=self.suggestions_index,
                id=suggestion_id,
                refresh=True
            )
            
            return response["result"] == "deleted"
            
        except Exception as e:
            logger.error(f"Error deleting suggestion: {str(e)}")
            return False
    
    async def rebuild_suggestions_from_history(self, days: int = 90) -> Dict[str, Any]:
        """
        Arama geçmişinden önerileri yeniden oluştur
        
        Args:
            days: Son kaç günün arama geçmişi alınacak
            
        Returns:
            Dict[str, Any]: Yeniden oluşturma sonuçları
        """
        try:
            start_time = datetime.datetime.utcnow()
            
            # Tüm suggestions indeksini temizle
            await self.es_client.delete_by_query(
                index=self.suggestions_index,
                body={
                    "query": {
                        "term": {
                            "source": SuggestionSource.HISTORY
                        }
                    }
                }
            )
            
            # Arama geçmişini al
            searches = await self.search_history_repository.get_all_searches(days=days)
            
            # Önerileri oluştur
            added = 0
            skipped = 0
            
            for search in searches:
                query = search["query"]
                
                if not query or len(query) < 3:
                    skipped += 1
                    continue
                
                await self._add_suggestion_from_search(
                    query=query,
                    user_id=search.get("user_id"),
                    result_count=search.get("result_count", 0),
                    context=search.get("context")
                )
                
                added += 1
            
            end_time = datetime.datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            return {
                "status": "success",
                "added": added,
                "skipped": skipped,
                "total": len(searches),
                "duration": duration
            }
            
        except Exception as e:
            logger.error(f"Error rebuilding suggestions from history: {str(e)}")
            
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def extract_terms_from_documents(self, rebuild: bool = False) -> Dict[str, Any]:
        """
        Dökümanlardan arama terimleri çıkarıp öneri ekle
        
        Args:
            rebuild: Mevcut terimleri sil ve yeniden oluştur
            
        Returns:
            Dict[str, Any]: İşlem sonuçları
        """
        try:
            start_time = datetime.datetime.utcnow()
            
            # Mevcut terimleri temizle
            if rebuild:
                await self.es_client.delete_by_query(
                    index=self.suggestions_index,
                    body={
                        "query": {
                            "term": {
                                "source": SuggestionSource.INDEX
                            }
                        }
                    }
                )
            
            # Önemli terimleri çıkar
            terms_query = {
                "size": 0,
                "aggs": {
                    "significant_terms": {
                        "significant_terms": {
                            "field": "content",
                            "size": 1000
                        }
                    },
                    "title_terms": {
                        "significant_terms": {
                            "field": "title",
                            "size": 100
                        }
                    }
                }
            }
            
            response = await self.es_client.search(
                index=self.documents_index,
                body=terms_query
            )
            
            # Terimleri topla
            terms = {}
            
            # İçerikten önemli terimler
            for bucket in response["aggregations"]["significant_terms"]["buckets"]:
                term = bucket["key"]
                score = int(bucket["score"] * 10)  # Ağırlık olarak kullan
                
                if len(term) >= 3:  # En az 3 karakterli terimler
                    terms[term] = max(terms.get(term, 0), score)
            
            # Başlıklardan önemli terimler
            for bucket in response["aggregations"]["title_terms"]["buckets"]:
                term = bucket["key"]
                score = int(bucket["score"] * 20)  # Başlıklar daha önemli
                
                if len(term) >= 3:
                    terms[term] = max(terms.get(term, 0), score)
            
            # Öneri olarak ekle
            added = 0
            skipped = 0
            
            for term, weight in terms.items():
                # Öneri belgesi oluştur
                suggestion_doc = {
                    "suggest": {
                        "input": term,
                        "weight": weight
                    },
                    "text": term,
                    "type": SuggestionType.COMPLETION,
                    "source": SuggestionSource.INDEX,
                    "weight": weight,
                    "context": "documents",
                    "created_at": datetime.datetime.utcnow().isoformat(),
                    "updated_at": datetime.datetime.utcnow().isoformat()
                }
                
                # Bağlamı ekle
                suggestion_doc["suggest"]["contexts"] = {
                    "context": ["documents"]
                }
                
                try:
                    # Öneriyi ekle
                    await self.es_client.index(
                        index=self.suggestions_index,
                        body=suggestion_doc,
                        refresh=False  # Performans için refresh etme
                    )
                    
                    added += 1
                except Exception as e:
                    logger.warning(f"Error adding term suggestion: {str(e)}")
                    skipped += 1
            
            # İndeksi yenile
            await self.es_client.indices.refresh(index=self.suggestions_index)
            
            end_time = datetime.datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            return {
                "status": "success",
                "added": added,
                "skipped": skipped,
                "total": len(terms),
                "duration": duration
            }
            
        except Exception as e:
            logger.error(f"Error extracting terms from documents: {str(e)}")
            
            return {
                "status": "error",
                "error": str(e)
            }