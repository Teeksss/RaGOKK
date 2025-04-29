# Last reviewed: 2025-04-29 09:00:20 UTC (User: TeeksssTF-IDF)
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
import time
import asyncio
import json
from sqlalchemy.ext.asyncio import AsyncSession

from ..utils.database import es_client
from ..utils.embedding_manager import embedding_manager, EmbeddingProvider
from ..utils.weaviate_connector import weaviate_connector
from ..utils.logger import get_logger
from ..auth import get_current_active_user, UserInDB as User, require_admin
from ..db.async_database import get_db
from ..websockets.background_tasks import manager as task_manager
from ..repositories.personalization_repository import PersonalizationRepository
from ..utils.config import JINA_API_KEY, JINA_SEARCH_ENDPOINT

router = APIRouter()
logger = get_logger(__name__)

# --- Modeller ---
class JinaSearchRequest(BaseModel):
    query: str = Field(..., description="Kullanıcı sorusu")
    language: Optional[str] = Field("en", description="Dil kodu (örn: en, tr)")
    provider: Optional[str] = Field("jina", description="Embedding sağlayıcı")

class SearchResult(BaseModel):
    id: str
    text: str
    source_info: Optional[Dict[str, Any]] = None
    score: Optional[float] = None
    
class JinaSearchResponse(BaseModel):
    results: List[SearchResult]
    query_time_ms: Optional[float] = None
    
# JinaSearch işlemci sınıfı
class JinaSearch:
    def __init__(self, api_key=JINA_API_KEY, search_endpoint=JINA_SEARCH_ENDPOINT):
        self.api_key = api_key
        self.search_endpoint = search_endpoint
    
    async def search(
        self,
        query: str,
        limit: int = 5,
        language: str = "en",
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Jina AI ile semantik arama yapar"""
        import httpx
        
        if not self.api_key:
            logger.error("Jina API Key bulunamadı")
            raise ValueError("Jina API Key eksik")
            
        try:
            start_time = time.time()
            
            # Sorgu için embedding oluştur
            query_embedding = await embedding_manager.get_embedding(
                query,
                provider=EmbeddingProvider.JINA
            )
            
            # Sorgu parametrelerini hazırla
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "query": query,
                "vector": query_embedding,
                "limit": limit,
                "language": language
            }
            
            # Filtreleri ekle (varsa)
            if filters:
                data["filters"] = filters
            
            # API çağrısını yap
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.search_endpoint,
                    headers=headers,
                    json=data,
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Sonuçları dönüştür
                docs = []
                
                for item in result.get("matches", []):
                    # Metadata ayrıştır
                    metadata = item.get("metadata", {})
                    
                    # Kaynak bilgisi
                    source_info = {
                        "source_type": metadata.get("source_type", "jina"),
                        "url": metadata.get("url", ""),
                        "title": metadata.get("title", "")
                    }
                    
                    # Belgeyi ekle
                    doc = {
                        "id": item.get("id", f"jina_{len(docs)}"),
                        "text": item.get("text", ""),
                        "score": item.get("score", 0.0),
                        "source_info": source_info,
                        "search_type": "jina_semantic"
                    }
                    
                    docs.append(doc)
                
                elapsed_time = time.time() - start_time
                logger.info(f"Jina search completed in {elapsed_time:.2f}s ({len(docs)} results)")
                
                return docs
                
        except Exception as e:
            logger.error(f"Jina search error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Jina search failed: {str(e)}"
            )

# Jina Search singleton
jina_search = JinaSearch()

# --- API Endpointleri ---
@router.post("/search/jina", response_model=JinaSearchResponse)
async def search_with_jina(
    request: JinaSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(5, ge=1, le=20),
    filter_source: Optional[str] = Query(None, description="Filter by source type")
):
    """Jina AI ile çok dilli semantik arama yapar"""
    query = request.query.strip()
    language = request.language
    
    if not query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Empty query is not allowed"
        )
    
    # Filtreleri hazırla
    filters = {}
    
    if filter_source:
        filters["source_type"] = filter_source
    
    try:
        start_time = time.time()
        
        # Jina search ile ara
        results = await jina_search.search(
            query=query,
            limit=limit,
            language=language,
            filters=filters
        )
        
        # Yanıt oluştur
        response_results = [
            SearchResult(
                id=doc["id"],
                text=doc["text"],
                source_info=doc["source_info"],
                score=doc["score"]
            ) for doc in results
        ]
        
        query_time_ms = (time.time() - start_time) * 1000
        
        return JinaSearchResponse(
            results=response_results,
            query_time_ms=query_time_ms
        )
        
    except ValueError as e:
        logger.error(f"Value error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )

@router.post("/weaviate/search", response_model=JinaSearchResponse)
async def search_with_weaviate(
    request: JinaSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    search_type: str = Query("hybrid", enum=["hybrid", "vector"]),
    limit: int = Query(5, ge=1, le=20),
    filter_source: Optional[str] = Query(None, description="Filter by source type")
):
    """Weaviate ile semantik veya hybrid arama yapar"""
    query = request.query.strip()
    provider = request.provider
    
    if not query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Empty query is not allowed"
        )
    
    # Filtreleri hazırla
    filters = {}
    
    if filter_source:
        filters["source"] = filter_source
    
    # Admin olmayan kullanıcılar sadece kendi belgelerini görebilir
    if "admin" not in current_user.roles:
        filters["owner_id"] = current_user.username
    
    try:
        start_time = time.time()
        
        # Embedding oluştur
        provider_enum = None
        if provider:
            try:
                provider_enum = EmbeddingProvider(provider)
            except ValueError:
                provider_enum = None
        
        vector = await embedding_manager.get_embedding(
            query,
            provider=provider_enum
        )
        
        # Weaviate ile ara
        if search_type == "hybrid":
            results = await weaviate_connector.hybrid_search(
                query=query,
                vector=vector,
                limit=limit,
                filters=filters
            )
        else:
            results = await weaviate_connector.search(
                query=query,
                vector=vector,
                limit=limit,
                filters=filters
            )
        
        # Yanıt oluştur
        response_results = [
            SearchResult(
                id=doc["id"],
                text=doc["text"],
                source_info=doc["source_info"],
                score=doc["score"]
            ) for doc in results
        ]
        
        query_time_ms = (time.time() - start_time) * 1000
        
        return JinaSearchResponse(
            results=response_results,
            query_time_ms=query_time_ms
        )
        
    except ValueError as e:
        logger.error(f"Value error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ConnectionError as e:
        logger.error(f"Connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Weaviate connection failed"
        )
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )