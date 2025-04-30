# Last reviewed: 2025-04-30 06:25:07 UTC (User: Teeksss)
from typing import List, Dict, Any, Optional
import logging
import os
from elasticsearch import AsyncElasticsearch, NotFoundError as ESNotFoundError
from elasticsearch.exceptions import ConnectionError, RequestError
import json
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class SparseRetriever:
    """
    Sparse Retrieval (BM25, ElasticSearch) servisi.
    Metin tabanlı arama yapar.
    """
    
    def __init__(self):
        """Elasticsearch bağlantısı ve indexleri başlatır"""
        self.es_url = os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200")
        self.index_name = os.environ.get("ELASTICSEARCH_INDEX", "rag_segments")
        self.es_client = self._initialize_client()
        
    def _initialize_client(self) -> Optional[AsyncElasticsearch]:
        """ElasticSearch istemcisini başlatır"""
        try:
            client = AsyncElasticsearch([self.es_url])
            return client
        except ConnectionError as e:
            logger.error(f"Failed to connect to ElasticSearch: {str(e)}")
            return None
    
    async def index_segment(self, segment: Dict[str, Any]) -> Dict[str, Any]:
        """
        Belge segmentini indeksler
        
        Args:
            segment: İndekslenecek segment
        
        Returns:
            Dict[str, Any]: İndeksleme sonucu
        """
        if not self.es_client:
            logger.error("ElasticSearch client not available")
            return {"success": False, "error": "ElasticSearch client not available"}
        
        try:
            # İndeks yoksa oluştur
            await self._ensure_index_exists()
            
            # İndeksleme dokümanını oluştur
            es_doc = {
                "document_id": segment.get("document_id", ""),
                "segment_id": segment["metadata"]["segment_id"],
                "content": segment["content"],
                "metadata": segment["metadata"],
                "indexed_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Elasticsearch'e ekle
            response = await self.es_client.index(
                index=self.index_name,
                id=segment["metadata"]["segment_id"],
                body=es_doc,
                refresh=True  # Hemen aranabilir olması için
            )
            
            return {
                "success": True,
                "segment_id": segment["metadata"]["segment_id"],
                "index": self.index_name,
                "result": response
            }
            
        except Exception as e:
            logger.error(f"Error indexing segment: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "segment_id": segment["metadata"]["segment_id"]
            }
    
    async def search(self, 
                   query_text: str,
                   limit: int = 10,
                   organization_id: Optional[str] = None,
                   filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        BM25 temelli arama yapar
        
        Args:
            query_text: Arama sorgusu
            limit: Maksimum sonuç sayısı
            organization_id: Organizasyon ID (filtreleme için)
            filters: Ek metadata filtreleri
            
        Returns:
            List[Dict[str, Any]]: Arama sonuçları
        """
        if not self.es_client:
            logger.warning("ElasticSearch client not available")
            return []
            
        if not query_text:
            return []
            
        try:
            # ElasticSearch sorgusu oluştur
            search_query = {
                "size": limit,
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": query_text,
                                    "fields": ["content^3", "metadata.section_title^2", "metadata.source_filename"],
                                    "type": "best_fields"
                                }
                            }
                        ],
                        "filter": []
                    }
                },
                "_source": {
                    "includes": ["document_id", "segment_id", "content", "metadata"]
                },
                "highlight": {
                    "fields": {
                        "content": {
                            "pre_tags": ["<mark>"],
                            "post_tags": ["</mark>"],
                            "fragment_size": 200,
                            "number_of_fragments": 1
                        }
                    }
                }
            }
            
            # Organizasyon filtresi ekle
            if organization_id:
                org_filter = {
                    "term": {
                        "metadata.organization_id": organization_id
                    }
                }
                search_query["query"]["bool"]["filter"].append(org_filter)
                
            # Ek filtreler ekle
            if filters:
                for key, value in filters.items():
                    if key.startswith("metadata."):
                        filter_key = key
                    else:
                        filter_key = f"metadata.{key}"
                        
                    term_filter = {
                        "term": {
                            filter_key: value
                        }
                    }
                    search_query["query"]["bool"]["filter"].append(term_filter)
            
            # Aramayı gerçekleştir
            search_results = await self.es_client.search(
                index=self.index_name,
                body=search_query
            )
            
            # Sonuçları dönüştür
            results = []
            
            for hit in search_results["hits"]["hits"]:
                # Skor normalizasyonu: ES score'u 0-1 aralığına dönüştür
                raw_score = hit["_score"]
                max_score = search_results["hits"]["max_score"] or 1
                normalized_score = raw_score / max_score  # 0-1 arası değer
                
                source = hit["_source"]
                metadata = source.get("metadata", {})
                
                # Vurgulanmış içerik (highlight)
                if "highlight" in hit and "content" in hit["highlight"]:
                    content_snippet = hit["highlight"]["content"][0]
                else:
                    content = source.get("content", "")
                    content_snippet = content[:200] + "..." if len(content) > 200 else content
                
                # Sonuç objesini oluştur
                result = {
                    "document_id": source.get("document_id", ""),
                    "content": source.get("content", ""),
                    "content_snippet": content_snippet,
                    "score": normalized_score,
                    "metadata": metadata,
                    "similarity_percentage": round(normalized_score * 100, 1)
                }
                
                # Dense retriever'da olduğu gibi sonuçları zenginleştir
                if "document_title" not in result and metadata.get("document_title"):
                    result["document_title"] = metadata.get("document_title")
                    
                if "page_number" not in result and metadata.get("page_number"):
                    result["page_number"] = metadata.get("page_number")
                    
                results.append(result)
                
            return results
            
        except Exception as e:
            logger.error(f"Error searching with ElasticSearch: {str(e)}")
            return []
    
    async def delete_segment(self, segment_id: str) -> Dict[str, Any]:
        """
        Belge segmentini silme
        
        Args:
            segment_id: Segment ID
            
        Returns:
            Dict[str, Any]: Silme sonucu
        """
        if not self.es_client:
            return {"success": False, "error": "ElasticSearch client not available"}
            
        try:
            response = await self.es_client.delete(
                index=self.index_name,
                id=segment_id,
                refresh=True
            )
            
            return {
                "success": True,
                "segment_id": segment_id,
                "result": response
            }
            
        except ESNotFoundError:
            # Segment bulunamadı, başarılı olarak döndür
            return {
                "success": True,
                "segment_id": segment_id,
                "result": "not_found"
            }
            
        except Exception as e:
            logger.error(f"Error deleting segment from ElasticSearch: {str(e)}")
            
            return {
                "success": False,
                "error": str(e),
                "segment_id": segment_id
            }
    
    async def delete_document_segments(self, document_id: str) -> Dict[str, Any]:
        """
        Belgenin tüm segmentlerini silme
        
        Args:
            document_id: Belge ID
            
        Returns:
            Dict[str, Any]: Silme sonucu
        """
        if not self.es_client:
            return {"success": False, "error": "ElasticSearch client not available"}
            
        try:
            # Belgeye ait segmentleri bul ve sil
            delete_query = {
                "query": {
                    "term": {
                        "document_id": document_id
                    }
                }
            }
            
            response = await self.es_client.delete_by_query(
                index=self.index_name,
                body=delete_query,
                refresh=True
            )
            
            return {
                "success": True,
                "document_id": document_id,
                "deleted_count": response.get("deleted", 0)
            }
            
        except Exception as e:
            logger.error(f"Error deleting document segments from ElasticSearch: {str(e)}")
            
            return {
                "success": False,
                "error": str(e),
                "document_id": document_id
            }
    
    async def _ensure_index_exists(self) -> bool:
        """Index'in varlığını kontrol et ve gerekirse oluştur"""
        if not self.es_client:
            return False
            
        try:
            # Index var mı kontrol et
            exists = await self.es_client.indices.exists(index=self.index_name)
            
            if not exists:
                # Index yoksa yeni oluştur
                index_config = {
                    "settings": {
                        "number_of_shards": 1,
                        "number_of_replicas": 1,
                        "analysis": {
                            "analyzer": {
                                "custom_analyzer": {
                                    "type": "custom",
                                    "tokenizer": "standard",
                                    "filter": [
                                        "lowercase", 
                                        "stop",
                                        "snowball"
                                    ]
                                }
                            }
                        }
                    },
                    "mappings": {
                        "properties": {
                            "document_id": { "type": "keyword" },
                            "segment_id": { "type": "keyword" },
                            "content": {
                                "type": "text",
                                "analyzer": "custom_analyzer"
                            },
                            "metadata": {
                                "properties": {
                                    "segment_id": { "type": "keyword" },
                                    "segment_index": { "type": "integer" },
                                    "segment_type": { "type": "keyword" },
                                    "source_filename": { "type": "text" },
                                    "page_number": { "type": "integer" },
                                    "section_title": { "type": "text" },
                                    "upload_user_id": { "type": "keyword" },
                                    "document_tags": { "type": "keyword" },
                                    "document_id": { "type": "keyword" },
                                    "document_title": { "type": "text" },
                                    "organization_id": { "type": "keyword" }
                                }
                            },
                            "indexed_at": { "type": "date" }
                        }
                    }
                }
                
                await self.es_client.indices.create(
                    index=self.index_name,
                    body=index_config
                )
                
                logger.info(f"Created ElasticSearch index: {self.index_name}")
                
            return True
            
        except Exception as e:
            logger.error(f"Error ensuring ElasticSearch index exists: {str(e)}")
            return False