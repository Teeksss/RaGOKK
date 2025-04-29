# Last reviewed: 2025-04-29 13:44:37 UTC (User: TeeksssVeritabanı)
import logging
import json
from enum import Enum
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime, date
import asyncio
import time

from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk
import weaviate
from weaviate.util import generate_uuid5

from ..config import settings
from ..repositories.document_repository import DocumentRepository
from ..repositories.collection_repository import CollectionRepository

logger = logging.getLogger(__name__)

class SearchType(str, Enum):
    """Arama türü"""
    VECTOR = "vector"  # Vektör tabanlı semantik arama
    FULLTEXT = "fulltext"  # Tam metin araması
    HYBRID = "hybrid"  # Vektör ve tam metin birleşimi

class FilterOperator(str, Enum):
    """Filtre operatörleri"""
    EQ = "eq"  # Eşit
    NEQ = "neq"  # Eşit değil
    GT = "gt"  # Büyük
    GTE = "gte"  # Büyük veya eşit
    LT = "lt"  # Küçük
    LTE = "lte"  # Küçük veya eşit
    IN = "in"  # Liste içinde
    NIN = "nin"  # Liste içinde değil
    CONTAINS = "contains"  # İçerir
    NOT_CONTAINS = "not_contains"  # İçermez
    STARTS_WITH = "starts_with"  # İle başlar
    ENDS_WITH = "ends_with"  # İle biter
    EXISTS = "exists"  # Alan var
    NOT_EXISTS = "not_exists"  # Alan yok
    RANGE = "range"  # Aralık içinde

class SortOrder(str, Enum):
    """Sıralama yönü"""
    ASC = "asc"  # Artan
    DESC = "desc"  # Azalan

class SearchFilter:
    """Arama filtresi"""
    
    def __init__(
        self,
        field: str,
        operator: FilterOperator,
        value: Any = None,
        nested_path: Optional[str] = None
    ):
        """
        Args:
            field: Filtre alanı
            operator: Filtre operatörü
            value: Filtre değeri
            nested_path: İç içe alan yolu
        """
        self.field = field
        self.operator = operator
        self.value = value
        self.nested_path = nested_path
    
    def to_dict(self) -> Dict[str, Any]:
        """Filtreyi sözlük olarak döndür"""
        result = {
            "field": self.field,
            "operator": self.operator,
            "value": self.value
        }
        
        if self.nested_path:
            result["nested_path"] = self.nested_path
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchFilter":
        """Sözlükten filtre oluştur"""
        return cls(
            field=data["field"],
            operator=data["operator"],
            value=data.get("value"),
            nested_path=data.get("nested_path")
        )
    
    def to_elasticsearch(self) -> Dict[str, Any]:
        """Elasticsearch sorgusu olarak döndür"""
        if self.operator == FilterOperator.EQ:
            return {"term": {self.field: self.value}}
        
        elif self.operator == FilterOperator.NEQ:
            return {"bool": {"must_not": {"term": {self.field: self.value}}}}
        
        elif self.operator == FilterOperator.GT:
            return {"range": {self.field: {"gt": self.value}}}
        
        elif self.operator == FilterOperator.GTE:
            return {"range": {self.field: {"gte": self.value}}}
        
        elif self.operator == FilterOperator.LT:
            return {"range": {self.field: {"lt": self.value}}}
        
        elif self.operator == FilterOperator.LTE:
            return {"range": {self.field: {"lte": self.value}}}
        
        elif self.operator == FilterOperator.IN:
            return {"terms": {self.field: self.value}}
        
        elif self.operator == FilterOperator.NIN:
            return {"bool": {"must_not": {"terms": {self.field: self.value}}}}
        
        elif self.operator == FilterOperator.CONTAINS:
            return {"wildcard": {self.field: f"*{self.value}*"}}
        
        elif self.operator == FilterOperator.NOT_CONTAINS:
            return {"bool": {"must_not": {"wildcard": {self.field: f"*{self.value}*"}}}}
        
        elif self.operator == FilterOperator.STARTS_WITH:
            return {"prefix": {self.field: self.value}}
        
        elif self.operator == FilterOperator.ENDS_WITH:
            return {"wildcard": {self.field: f"*{self.value}"}}
        
        elif self.operator == FilterOperator.EXISTS:
            return {"exists": {"field": self.field}}
        
        elif self.operator == FilterOperator.NOT_EXISTS:
            return {"bool": {"must_not": {"exists": {"field": self.field}}}}
        
        elif self.operator == FilterOperator.RANGE:
            if not isinstance(self.value, dict) or "from" not in self.value or "to" not in self.value:
                raise ValueError("Range operator requires 'from' and 'to' values")
            
            return {"range": {self.field: {"gte": self.value["from"], "lte": self.value["to"]}}}
        
        else:
            raise ValueError(f"Unsupported operator: {self.operator}")
    
    def to_weaviate(self) -> Dict[str, Any]:
        """Weaviate sorgusu olarak döndür"""
        # Weaviate sorgu dönüşümleri
        # Elasticsearch'ten farklı olabilir
        pass

class SearchFacet:
    """Arama faset/agregasyon"""
    
    def __init__(
        self,
        field: str,
        type: str = "terms",
        name: Optional[str] = None,
        size: int = 10,
        order: SortOrder = SortOrder.DESC,
        min_doc_count: int = 1,
        nested_path: Optional[str] = None,
        ranges: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Args:
            field: Faset alanı
            type: Faset türü (terms, range, date_histogram, histogram)
            name: Faset adı (belirtilmezse alan adı kullanılır)
            size: Döndürülecek değer sayısı (terms için)
            order: Sıralama yönü
            min_doc_count: Minimum döküman sayısı
            nested_path: İç içe alan yolu
            ranges: Aralık tanımları (range için)
        """
        self.field = field
        self.type = type
        self.name = name or field
        self.size = size
        self.order = order
        self.min_doc_count = min_doc_count
        self.nested_path = nested_path
        self.ranges = ranges or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Faseti sözlük olarak döndür"""
        result = {
            "field": self.field,
            "type": self.type,
            "name": self.name,
            "size": self.size,
            "order": self.order,
            "min_doc_count": self.min_doc_count
        }
        
        if self.nested_path:
            result["nested_path"] = self.nested_path
        
        if self.ranges:
            result["ranges"] = self.ranges
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchFacet":
        """Sözlükten faset oluştur"""
        return cls(
            field=data["field"],
            type=data.get("type", "terms"),
            name=data.get("name"),
            size=data.get("size", 10),
            order=data.get("order", SortOrder.DESC),
            min_doc_count=data.get("min_doc_count", 1),
            nested_path=data.get("nested_path"),
            ranges=data.get("ranges")
        )
    
    def to_elasticsearch(self) -> Tuple[str, Dict[str, Any]]:
        """Elasticsearch agregasyon olarak döndür"""
        if self.type == "terms":
            agg = {
                "terms": {
                    "field": self.field,
                    "size": self.size,
                    "min_doc_count": self.min_doc_count,
                    "order": {"_count": self.order}
                }
            }
        
        elif self.type == "range":
            agg = {
                "range": {
                    "field": self.field,
                    "ranges": self.ranges
                }
            }
        
        elif self.type == "date_histogram":
            agg = {
                "date_histogram": {
                    "field": self.field,
                    "calendar_interval": self.ranges[0].get("interval", "month") if self.ranges else "month",
                    "min_doc_count": self.min_doc_count,
                    "order": {"_count": self.order}
                }
            }
        
        elif self.type == "histogram":
            agg = {
                "histogram": {
                    "field": self.field,
                    "interval": self.ranges[0].get("interval", 5) if self.ranges else 5,
                    "min_doc_count": self.min_doc_count,
                    "order": {"_count": self.order}
                }
            }
        
        else:
            raise ValueError(f"Unsupported facet type: {self.type}")
        
        # Nested aggregation kontrolü
        if self.nested_path:
            return self.name, {
                "nested": {
                    "path": self.nested_path
                },
                "aggs": {
                    f"{self.name}_agg": agg
                }
            }
        
        return self.name, agg

class SearchService:
    """Arama servisi"""
    
    def __init__(self):
        """Arama servisi başlatma"""
        self.es_client = None
        self.wv_client = None
    
    async def connect(self):
        """Arama istemcilerini oluştur"""
        # Elasticsearch bağlantısı
        if settings.ELASTICSEARCH_ENABLED:
            self.es_client = AsyncElasticsearch(
                hosts=[settings.ELASTICSEARCH_URL],
                http_auth=(settings.ELASTICSEARCH_USER, settings.ELASTICSEARCH_PASSWORD),
                verify_certs=settings.ELASTICSEARCH_VERIFY_CERTS
            )
            logger.info("Connected to Elasticsearch")
        
        # Weaviate bağlantısı
        if settings.WEAVIATE_ENABLED:
            auth_config = weaviate.auth.AuthApiKey(api_key=settings.WEAVIATE_API_KEY) if settings.WEAVIATE_API_KEY else None
            
            self.wv_client = weaviate.Client(
                url=settings.WEAVIATE_URL,
                auth_client_secret=auth_config,
                additional_headers={"X-OpenAI-Api-Key": settings.OPENAI_API_KEY} if settings.OPENAI_API_KEY else None
            )
            logger.info("Connected to Weaviate")
    
    async def disconnect(self):
        """Arama istemcilerini kapat"""
        if self.es_client:
            await self.es_client.close()
            logger.info("Disconnected from Elasticsearch")
        
        if self.wv_client:
            # Weaviate Python istemcisi asenkron değil
            logger.info("Disconnected from Weaviate")
    
    async def search(
        self,
        query: str,
        search_type: SearchType = SearchType.HYBRID,
        filters: List[SearchFilter] = None,
        facets: List[SearchFacet] = None,
        sort_by: str = None,
        sort_order: SortOrder = SortOrder.DESC,
        page: int = 1,
        page_size: int = 20,
        highlight: bool = True,
        user_id: str = None,
        include_fields: List[str] = None,
        exclude_fields: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Belgelerde arama yapar
        
        Args:
            query: Arama sorgusu
            search_type: Arama türü
            filters: Filtreler
            facets: Fasetler
            sort_by: Sıralama alanı
            sort_order: Sıralama yönü
            page: Sayfa numarası
            page_size: Sayfa boyutu
            highlight: Vurgu yapılsın mı
            user_id: Kullanıcı ID
            include_fields: Dahil edilecek alanlar
            exclude_fields: Hariç tutulacak alanlar
            
        Returns:
            Dict[str, Any]: Arama sonuçları
        """
        filters = filters or []
        facets = facets or []
        
        # Erişim kontrolü filtresi ekle
        if user_id:
            # Kullanıcının erişebileceği dokümanlar
            user_filter = SearchFilter(
                field="access",
                operator=FilterOperator.IN,
                value=["public", f"user_{user_id}"]
            )
            filters.append(user_filter)
        
        # Search engine seçimi
        if settings.WEAVIATE_ENABLED and (search_type == SearchType.VECTOR or search_type == SearchType.HYBRID):
            # Weaviate ile vektör araması
            if search_type == SearchType.HYBRID and settings.ELASTICSEARCH_ENABLED:
                # Hybrid search için hem Elasticsearch hem Weaviate kullan
                es_results = await self._search_elasticsearch(
                    query, filters, facets, sort_by, sort_order, page, page_size, highlight, include_fields, exclude_fields
                )
                
                wv_results = await self._search_weaviate(
                    query, filters, None, sort_by, sort_order, page, page_size, include_fields, exclude_fields
                )
                
                # Sonuçları birleştir
                return self._merge_search_results(es_results, wv_results)
            else:
                # Sadece Weaviate
                return await self._search_weaviate(
                    query, filters, facets, sort_by, sort_order, page, page_size, include_fields, exclude_fields
                )
        else:
            # Elasticsearch ile metin araması
            return await self._search_elasticsearch(
                query, filters, facets, sort_by, sort_order, page, page_size, highlight, include_fields, exclude_fields
            )
    
    async def _search_elasticsearch(
        self,
        query: str,
        filters: List[SearchFilter] = None,
        facets: List[SearchFacet] = None,
        sort_by: str = None,
        sort_order: SortOrder = SortOrder.DESC,
        page: int = 1,
        page_size: int = 20,
        highlight: bool = True,
        include_fields: List[str] = None,
        exclude_fields: List[str] = None
    ) -> Dict[str, Any]:
        """
        Elasticsearch ile arama yapar
        
        Args:
            query: Arama sorgusu
            filters: Filtreler
            facets: Fasetler
            sort_by: Sıralama alanı
            sort_order: Sıralama yönü
            page: Sayfa numarası
            page_size: Sayfa boyutu
            highlight: Vurgu yapılsın mı
            include_fields: Dahil edilecek alanlar
            exclude_fields: Hariç tutulacak alanlar