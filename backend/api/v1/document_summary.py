# Last reviewed: 2025-04-30 07:11:25 UTC (User: Teeksss)
from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
import logging

from ...db.session import get_db
from ...services.document_summarizer import DocumentSummarizer
from ...repositories.document_repository import DocumentRepository
from ...auth.jwt import get_current_active_user
from ...schemas.document import DocumentSummaryResponse

router = APIRouter(prefix="/document-summary", tags=["document-summary"])
logger = logging.getLogger(__name__)

document_summarizer = DocumentSummarizer()
document_repository = DocumentRepository()

@router.get("/{document_id}", response_model=DocumentSummaryResponse)
async def get_document_summary(
    document_id: str = Path(..., description="Belge ID'si"),
    force_refresh: bool = False,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Belge özetini getirir veya oluşturur
    
    - **document_id**: Özet alınacak belge ID'si
    - **force_refresh**: Mevcut özeti yenilemek için True olarak ayarlayın
    """
    try:
        # Belge erişim kontrolü
        document = await document_repository.get_document_by_id(db, document_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
            
        # Belge sahibi veya organizasyon üyesi kontrolü
        if document.user_id != current_user["id"] and document.organization_id != current_user.get("organization_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this document"
            )
        
        # Özet kontrolü
        metadata = document.metadata or {}
        has_summary = metadata.get("summary") is not None
        
        if has_summary and not force_refresh:
            # Mevcut özet
            return {
                "document_id": document_id,
                "title": document.title,
                "summary": metadata.get("summary", {}),
                "generated_at": metadata.get("summary_generated_at", ""),
                "is_new": False
            }
        
        # Yeni özet oluştur veya yenile
        result = await document_summarizer.process_document(db, document_id)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error") or "Unknown error generating summary"
            )
            
        # Güncellenmiş belgeyi getir
        updated_document = await document_repository.get_document_by_id(db, document_id)
        updated_metadata = updated_document.metadata or {}
        
        return {
            "document_id": document_id,
            "title": updated_document.title,
            "summary": updated_metadata.get("summary", {}),
            "generated_at": updated_metadata.get("summary_generated_at", ""),
            "is_new": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document summary: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting document summary: {str(e)}"
        )