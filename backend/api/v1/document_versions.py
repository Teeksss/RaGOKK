# Last reviewed: 2025-04-30 07:34:44 UTC (User: Teeksss)
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
import logging

from ...db.session import get_db
from ...services.document_versioning import DocumentVersioningService
from ...repositories.document_repository import DocumentRepository
from ...auth.jwt import get_current_active_user
from ...schemas.document_version import VersionResponse, VersionListResponse, VersionDiffResponse
from ...auth.enhanced_jwt import get_current_user_enhanced
from ...auth.permissions import require_permission, Permission

router = APIRouter(prefix="/document-versions", tags=["document-versions"])
logger = logging.getLogger(__name__)

# Servisleri başlat
document_versioning_service = DocumentVersioningService()
document_repository = DocumentRepository()

@router.get("/{document_id}", response_model=VersionListResponse)
async def get_document_versions(
    document_id: str = Path(..., description="Belge ID'si"),
    current_user: Dict[str, Any] = Depends(get_current_user_enhanced),
    db: AsyncSession = Depends(get_db)
):
    """
    Belgeye ait tüm versiyonları getirir
    
    - **document_id**: Belge ID'si
    """
    try:
        # Belge erişim kontrolü
        document = await document_repository.get_document_by_id(db, document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
            
        # Yetki kontrolü
        if document.user_id != current_user.get("id") and document.organization_id != current_user.get("organization_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this document"
            )
        
        # Versiyonları getir
        versions = await document_versioning_service.get_versions(db, document_id)
        
        return {
            "document_id": document_id,
            "versions": versions["versions"],
            "total": versions["total"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document versions: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting document versions: {str(e)}"
        )

@router.get("/{document_id}/{version_number}", response_model=VersionResponse)
async def get_document_version(
    document_id: str = Path(..., description="Belge ID'si"),
    version_number: int = Path(..., description="Versiyon numarası"),
    current_user: Dict[str, Any] = Depends(get_current_user_enhanced),
    db: AsyncSession = Depends(get_db)
):
    """
    Belirli bir belge versiyonunu getirir
    
    - **document_id**: Belge ID'si
    - **version_number**: Versiyon numarası
    """
    try:
        # Belge erişim kontrolü
        document = await document_repository.get_document_by_id(db, document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
            
        # Yetki kontrolü
        if document.user_id != current_user.get("id") and document.organization_id != current_user.get("organization_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this document"
            )
        
        # Versiyonu getir
        version_result = await document_versioning_service.get_version(
            db, document_id, version_number
        )
        
        if not version_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=version_result.get("error", "Version not found")
            )
            
        return version_result["version"]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document version: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting document version: {str(e)}"
        )

@router.post("/{document_id}", response_model=VersionResponse)
async def create_document_version(
    document_id: str = Path(..., description="Belge ID'si"),
    change_description: str = Query(..., description="Değişiklik açıklaması"),
    current_user: Dict[str, Any] = Depends(get_current_user_enhanced),
    db: AsyncSession = Depends(get_db)
):
    """
    Belgenin mevcut halinden yeni bir versiyon oluşturur
    
    - **document_id**: Belge ID'si
    - **change_description**: Değişiklik açıklaması
    """
    try:
        # Belge erişim kontrolü
        document = await document_repository.get_document_by_id(db, document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
            
        # Düzenleme yetkisi kontrolü
        if document.user_id != current_user.get("id") and document.organization_id != current_user.get("organization_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to create versions for this document"
            )
        
        # Versiyon oluştur
        version_result = await document_versioning_service.create_version(
            db=db,
            document_id=document_id,
            user_id=current_user["id"],
            change_description=change_description
        )
        
        if not version_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=version_result.get("error", "Error creating version")
            )
            
        return version_result["version"]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating document version: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating document version: {str(e)}"
        )

@router.get("/{document_id}/diff", response_model=VersionDiffResponse)
async def get_version_diff(
    document_id: str = Path(..., description="Belge ID'si"),
    from_version: int = Query(..., description="Başlangıç versiyon numarası"),
    to_version: Optional[int] = Query(None, description="Bitiş versiyon numarası (None ise mevcut belge)"),
    current_user: Dict[str, Any] = Depends(get_current_user_enhanced),
    db: AsyncSession = Depends(get_db)
):
    """
    İki versiyon arasındaki farkları getirir
    
    - **document_id**: Belge ID'si
    - **from_version**: Başlangıç versiyon numarası
    - **to_version**: Bitiş versiyon numarası (belirtilmezse mevcut belge kullanılır)
    """
    try:
        # Belge erişim kontrolü
        document = await document_repository.get_document_by_id(db, document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
            
        # Yetki kontrolü
        if document.user_id != current_user.get("id") and document.organization_id != current_user.get("organization_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this document"
            )
        
        # Farkları getir
        diff_result = await document_versioning_service.get_diff(
            db=db,
            document_id=document_id,
            from_version=from_version,
            to_version=to_version
        )
        
        if not diff_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=diff_result.get("error", "Error getting diff")
            )
            
        return {
            "document_id": document_id,
            "from_version": diff_result["from_version"],
            "to_version": diff_result["to_version"],
            "diff_text": diff_result["diff_text"],
            "diff_html": diff_result["diff_html"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting version diff: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting version diff: {str(e)}"
        )

@router.post("/{document_id}/restore/{version_number}", response_model=VersionResponse)
async def restore_document_version(
    document_id: str = Path(..., description="Belge ID'si"),
    version_number: int = Path(..., description="Geri dönülecek versiyon numarası"),
    current_user: Dict[str, Any] = Depends(get_current_user_enhanced),
    db: AsyncSession = Depends(get_db)
):
    """
    Belgeyi belirli bir versiyona geri döndürür
    
    - **document_id**: Belge ID'si
    - **version_number**: Geri dönülecek versiyon numarası
    """
    try:
        # Belge erişim kontrolü
        document = await document_repository.get_document_by_id(db, document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
            
        # Düzenleme yetkisi kontrolü
        if document.user_id != current_user.get("id") and document.organization_id != current_user.get("organization_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to restore versions for this document"
            )
        
        # Versiyona geri dön
        restore_result = await document_versioning_service.restore_version(
            db=db,
            document_id=document_id,
            version_number=version_number,
            user_id=current_user["id"]
        )
        
        if not restore_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=restore_result.get("error", "Error restoring version")
            )
            
        return restore_result["version"]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring document version: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error restoring document version: {str(e)}"
        )