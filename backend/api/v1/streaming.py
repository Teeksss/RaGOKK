# Last reviewed: 2025-04-30 07:12:47 UTC (User: Teeksss)
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
import logging
import json

from ...db.session import get_db
from ...services.streaming_llm import StreamingLLM
from ...services.multi_vector_retriever import MultiVectorRetriever
from ...auth.jwt import get_current_active_user_ws
from ...core.exceptions import NotFoundError

router = APIRouter(prefix="/streaming", tags=["streaming"])
logger = logging.getLogger(__name__)

streaming_llm = StreamingLLM()
multi_vector_retriever = MultiVectorRetriever()

@router.websocket("/query")
async def streaming_query(
    websocket: WebSocket,
    query: str = Query(..., description="Kullanıcı sorgusu"),
    filters: Optional[str] = Query(None, description="JSON formatında filtreler"),
    search_type: Optional[str] = Query("hybrid", description="Arama türü (hybrid, dense, sparse)"),
    db: AsyncSession = Depends(get_db)
):
    """
    WebSocket üzerinden akışlı sorgu yanıtları
    
    Bağlantı: ws://sunucu_adresi/api/v1/streaming/query?query=Sorgu%20metni
    
    Parametreler:
    - query: Kullanıcı sorgusu
    - filters: (Opsiyonel) JSON formatında filtreler - {"document_ids": ["id1", "id2"]}
    - search_type: (Opsiyonel) Arama türü (hybrid, dense, sparse)
    
    WebSocket dönen veri formatı:
    {
        "type": "chunk" | "info" | "error",
        "content": "Token içeriği",
        "source_id": "1" | null,
        "current_references": ["1", "2"],
        "done": true | false,
        "metadata": { ... }
    }
    """
    try:
        # WebSocket bağlantısını kabul et
        await websocket.accept()
        
        # Kullanıcı kontrolü
        try:
            current_user = await get_current_active_user_ws(websocket)
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            await websocket.send_json({
                "type": "error",
                "content": "Authentication error",
                "metadata": {
                    "error": str(e)
                }
            })
            await websocket.close(code=4000, reason="Authentication error")
            return
        
        # Filtreleri JSON'dan ayrıştır
        query_filters = {}
        if filters:
            try:
                query_filters = json.loads(filters)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "content": "Invalid filters JSON",
                    "metadata": {
                        "error": "Invalid JSON format in filters"
                    }
                })
                await websocket.close()
                return
        
        # Bilgilendirme mesajı
        await websocket.send_json({
            "type": "info",
            "content": "Arama sonuçları bulunuyor...",
            "metadata": {
                "status": "searching"
            }
        })
                
        # Arama sonuçlarını al
        search_results = await multi_vector_retriever.search(
            query_text=query,
            limit=10,
            organization_id=current_user.get("organization_id"),
            filters=query_filters,
            search_type=search_type
        )
        
        # Eğer sonuç bulunamadıysa bildir
        if not search_results.get("results"):
            await websocket.send_json({
                "type": "error",
                "content": "Bu sorguya uygun bir sonuç bulunamadı.",
                "metadata": {
                    "error": "No results found",
                    "query": query
                }
            })
            await websocket.close()
            return
        
        # Streaming LLM işleyiciyi başlat
        await streaming_llm.handle_websocket(
            websocket=websocket,
            query=query,
            search_results=search_results.get("results", []),
            system_prompt=None  # Varsayılan prompt kullan
        )
        
    except WebSocketDisconnect:
        logger.info("WebSocket connection closed by client")
    except Exception as e:
        logger.error(f"Error in streaming query: {str(e)}")
        # WebSocket halen açıksa hata gönder
        try:
            await websocket.send_json({
                "type": "error",
                "content": str(e),
                "metadata": {
                    "error": str(e)
                }
            })
            await websocket.close()
        except:
            pass