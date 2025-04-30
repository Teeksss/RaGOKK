# Last reviewed: 2025-04-30 06:34:07 UTC (User: Teeksss)
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional

from ...db.session import get_db
from ...services.rag_feedback import RAGFeedbackService
from ...schemas.feedback import FeedbackCreate, FeedbackResponse, FeedbackList
from ...auth.jwt import get_current_active_user
from ...core.exceptions import NotFoundError

router = APIRouter(prefix="/feedback", tags=["feedback"])

feedback_service = RAGFeedbackService()

@router.post("/{query_id}", response_model=FeedbackResponse)
async def create_feedback(
    query_id: str = Path(..., description="Sorgu ID'si"),
    feedback: FeedbackCreate = Depends(),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Bir sorgu için kullanıcı geri bildirimi oluşturur
    
    - **query_id**: Geri bildirim verilecek sorgu ID'si (path parametresi)
    - **rating**: Derecelendirme puanı (1-5 arası)
    - **feedback_text**: Geri bildirim açıklaması (opsiyonel)
    - **feedback_type**: Geri bildirim türü (varsayılan: answer_quality)
    """
    try:
        # Geri bildirimi kaydet
        result = await feedback_service.log_feedback(
            db=db,
            query_id=query_id,
            user_id=current_user["id"],
            rating=feedback.rating,
            feedback_text=feedback.feedback_text,
            feedback_type=feedback.feedback_type,
            query_data=feedback.query_data
        )
        
        return result
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating feedback: {str(e)}"
        )

@router.get("/{query_id}", response_model=FeedbackList)
async def get_feedback_for_query(
    query_id: str = Path(..., description="Sorgu ID'si"),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Belirli bir sorgu için tüm geri bildirimleri getirir
    
    - **query_id**: Geri bildirim alınacak sorgu ID'si (path parametresi)
    """
    try:
        # Sorgunun kullanıcıya ait olduğunu kontrol et
        # TODO: Bu kontrol, sorgu sahipliği kontrolü ile değiştirilebilir
        
        # Geri bildirimleri getir
        results = await feedback_service.get_query_feedback(db, query_id)
        
        return {
            "total": len(results),
            "items": results
        }
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting feedback: {str(e)}"
        )

@router.get("/user/{user_id}", response_model=FeedbackList)
async def get_feedback_for_user(
    user_id: str = Path(..., description="Kullanıcı ID'si"),
    limit: int = Query(50, ge=1, le=100, description="Maksimum kayıt sayısı"),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Belirli bir kullanıcının tüm geri bildirimlerini getirir
    
    - **user_id**: Geri bildirimleri alınacak kullanıcı ID'si (path parametresi)
    - **limit**: Maksimum kayıt sayısı (default: 50)
    """
    try:
        # Yetki kontrolü: Sadece kendi geri bildirimlerini veya admin görebilir
        if user_id != current_user["id"] and not current_user.get("is_superuser"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied. You can only view your own feedback."
            )
        
        # Geri bildirimleri getir
        results = await feedback_service.get_user_feedback(db, user_id, limit)
        
        return {
            "total": len(results),
            "items": results
        }
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting user feedback: {str(e)}"
        )