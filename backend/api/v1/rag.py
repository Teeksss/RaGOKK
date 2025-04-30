# Last reviewed: 2025-04-29 14:19:03 UTC (User: TeeksssRAG)
from fastapi import APIRouter, Depends, HTTPException, status, Body, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List
import logging

from ...db.session import get_db
from ...schemas.rag import RAGQuery, RAGResponse
from ...services.rag_service import RAGService
from ...services.audit_service import AuditService, AuditLogType
from ...auth.jwt import get_current_active_user

router = APIRouter(
    prefix="/api/rag",
    tags=["rag"],
    responses={401: {"description": "Unauthorized"}}
)

logger = logging.getLogger(__name__)
rag_service = RAGService()
audit_service = AuditService()

@router.post("/query", response_model=RAGResponse)
async def query_rag(
    query: RAGQuery,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    RAG sorgusu yapar ve cevap üretir
    
    Request body:
    - **question**: Kullanıcı sorusu
    - **search_type**: Arama türü (semantic, keyword)
    - **prompt_template_id**: Kullanılacak prompt şablonu ID (opsiyonel)
    - **max_results**: Kullanılacak maksimum belge sayısı (opsiyonel)
    
    Returns:
    - **RAGResponse**: Üretilen cevap ve kaynaklar
    """
    try:
        # Sorguyu işle ve cevap oluştur
        response = await rag_service.answer_query(
            query=query,
            user_id=current_user["id"],
            organization_id=current_user.get("organization_id"),
            db=db
        )
        
        # Arka planda audit log kaydı
        background_tasks.add_task(
            audit_service.log_event,
            event_type=AuditLogType.DATA,
            user_id=current_user["id"],
            action="query",
            resource_type="rag",
            resource_id=response.query_id,
            status="success",
            details={
                "question": query.question,
                "search_type": query.search_type,
                "prompt_template_id": query.prompt_template_id,
                "sources_count": len(response.sources)
            },
            db=db
        )
        
        return response
    except Exception as e:
        logger.error(f"Error processing RAG query: {str(e)}")
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.DATA,
            user_id=current_user["id"],
            action="query",
            resource_type="rag",
            status="failure",
            details={
                "error": str(e),
                "question": query.question,
                "search_type": query.search_type
            },
            db=db
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the query: {str(e)}"
        )