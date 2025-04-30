# Last reviewed: 2025-04-30 07:11:25 UTC (User: Teeksss)
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
import logging

from ...db.session import get_db
from ...services.qa_generator import QAGenerator
from ...repositories.qa_pairs_repository import QAPairsRepository
from ...repositories.document_repository import DocumentRepository
from ...auth.jwt import get_current_active_user
from ...schemas.qa_generation import QAPairResponse, QAPairList

router = APIRouter(prefix="/qa-generation", tags=["qa-generation"])
logger = logging.getLogger(__name__)

qa_generator = QAGenerator()
qa_pairs_repository = QAPairsRepository()
document_repository = DocumentRepository()

@router.post("/{document_id}", response_model=Dict[str, Any])
async def generate_qa_pairs(
    background_tasks: BackgroundTasks,
    document_id: str = Path(..., description="Belge ID'si"),
    force_refresh: bool = Query(False, description="Mevcut QA çiftlerini sil ve yeniden oluştur"),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Belge için soru-cevap çiftleri oluşturur
    
    - **document_id**: QA çiftleri oluşturulacak belge ID'si
    - **force_refresh**: Mevcut QA çiftlerini silip yeniden oluşturmak için True
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
        
        # QA çiftleri kontrolü
        qa_pairs_exist = False
        if document.metadata and document.metadata.get("qa_pairs_generated"):
            qa_pairs_exist = True
            
        # İstek verilerini hazırla
        if qa_pairs_exist and not force_refresh:
            # Mevcut QA çiftleri
            qa_pairs = await qa_pairs_repository.get_qa_pairs_by_document_id(db, document_id)
            
            return {
                "success": True,
                "document_id": document_id,
                "total": len(qa_pairs),
                "status": "existing",
                "message": "QA pairs already exist for this document"
            }
        
        # QA çiftlerini sil (eğer force_refresh ise)
        if force_refresh and qa_pairs_exist:
            deleted_count = await qa_pairs_repository.delete_qa_pairs_by_document_id(db, document_id)
            logger.info(f"Deleted {deleted_count} existing QA pairs for document {document_id}")
        
        # Arka planda QA çiftleri oluştur
        background_tasks.add_task(
            qa_generator.generate_qa_for_document,
            db=db,
            document_id=document_id
        )
        
        return {
            "success": True,
            "document_id": document_id,
            "status": "pending",
            "message": "QA pairs generation started in background"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating QA pairs: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating QA pairs: {str(e)}"
        )

@router.get("/{document_id}", response_model=QAPairList)
async def get_qa_pairs(
    document_id: str = Path(..., description="Belge ID'si"),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Belgeye ait soru-cevap çiftlerini getirir
    
    - **document_id**: QA çiftleri getirilecek belge ID'si
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
        
        # QA çiftlerini getir
        qa_pairs = await qa_pairs_repository.get_qa_pairs_by_document_id(db, document_id)
        
        # Generation durumu kontrol et
        generation_status = "completed" if qa_pairs else "not_started"
        if document.metadata and document.metadata.get("qa_pairs_generated_at"):
            generated_at = document.metadata.get("qa_pairs_generated_at")
        else:
            generated_at = None
            
        return {
            "document_id": document_id,
            "items": qa_pairs,
            "total": len(qa_pairs),
            "generation_status": generation_status,
            "generated_at": generated_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting QA pairs: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting QA pairs: {str(e)}"
        )