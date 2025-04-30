# Last reviewed: 2025-04-29 14:19:03 UTC (User: TeeksssRAG)
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List
import logging

from ...db.session import get_db
from ...schemas.rag import PromptTemplate, PromptTemplateCreate, PromptTemplateUpdate, PromptTemplateList
from ...repositories.prompt_repository import PromptRepository
from ...services.audit_service import AuditService, AuditLogType
from ...auth.jwt import get_current_active_user

router = APIRouter(
    prefix="/api/prompts",
    tags=["prompts"],
    responses={401: {"description": "Unauthorized"}}
)

logger = logging.getLogger(__name__)
prompt_repository = PromptRepository()
audit_service = AuditService()

@router.get("/", response_model=PromptTemplateList)
async def list_prompt_templates(
    search: Optional[str] = Query(None, description="Search templates by name"),
    is_system: bool = Query(False, description="Include only system templates"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Prompt şablonlarını listeler
    
    Kullanıcıya ait ve sistem şablonlarını döndürür.
    """
    try:
        templates = await prompt_repository.list_prompt_templates(
            db=db,
            user_id=current_user["id"],
            search=search,
            is_system=is_system,
            page=page,
            page_size=page_size
        )
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.DATA,
            user_id=current_user["id"],
            action="list",
            resource_type="prompt_templates",
            status="success",
            db=db
        )
        
        return templates
    except Exception as e:
        logger.error(f"Error listing prompt templates: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while listing prompt templates: {str(e)}"
        )

@router.get("/{template_id}", response_model=PromptTemplate)
async def get_prompt_template(
    template_id: str,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Bir prompt şablonu getirir
    """
    try:
        template = await prompt_repository.get_prompt_template(
            db=db,
            template_id=template_id,
            user_id=current_user["id"]
        )
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt template not found"
            )
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.DATA,
            user_id=current_user["id"],
            action="view",
            resource_type="prompt_template",
            resource_id=template_id,
            status="success",
            db=db
        )
        
        return template
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prompt template: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while getting prompt template: {str(e)}"
        )

@router.post("/", response_model=PromptTemplate, status_code=status.HTTP_201_CREATED)
async def create_prompt_template(
    template_data: PromptTemplateCreate,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Yeni bir prompt şablonu oluşturur
    """
    try:
        template = await prompt_repository.create_prompt_template(
            db=db,
            name=template_data.name,
            description=template_data.description,
            template=template_data.template,
            is_system=False,  # Kullanıcı sistem şablonu oluşturamaz
            user_id=current_user["id"],
            organization_id=current_user.get("organization_id")
        )
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.DATA,
            user_id=current_user["id"],
            action="create",
            resource_type="prompt_template",
            resource_id=template.id,
            status="success",
            details={"name": template_data.name},
            db=db
        )
        
        return template
    except Exception as e:
        logger.error(f"Error creating prompt template: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating prompt template: {str(e)}"
        )

@router.put("/{template_id}", response_model=PromptTemplate)
async def update_prompt_template(
    template_id: str,
    template_data: PromptTemplateUpdate,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Bir prompt şablonunu günceller
    
    Kullanıcı sadece kendi şablonlarını güncelleyebilir, sistem şablonları güncellenemez.
    """
    try:
        # Mevcut şablonu kontrol et
        existing_template = await prompt_repository.get_prompt_template(
            db=db,
            template_id=template_id,
            user_id=current_user["id"]
        )
        
        if not existing_template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt template not found"
            )
        
        # Sistem şablonlarını güncellemeye izin verme
        if existing_template.is_system:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="System templates cannot be updated"
            )
        
        # Şablonu güncelle
        template = await prompt_repository.update_prompt_template(
            db=db,
            template_id=template_id,
            name=template_data.name,
            description=template_data.description,
            template=template_data.template,
            user_id=current_user["id"]
        )
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.DATA,
            user_id=current_user["id"],
            action="update",
            resource_type="prompt_template",
            resource_id=template_id,
            status="success",
            details={"name": template_data.name},
            db=db
        )
        
        return template
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating prompt template: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while updating prompt template: {str(e)}"
        )

@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt_template(
    template_id: str,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Bir prompt şablonunu siler
    
    Kullanıcı sadece kendi şablonlarını silebilir, sistem şablonları silinemez.
    """
    try:
        # Mevcut şablonu kontrol et
        existing_template = await prompt_repository.get_prompt_template(
            db=db,
            template_id=template_id,
            user_id=current_user["id"]
        )
        
        if not existing_template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt template not found"
            )
        
        # Sistem şablonlarını silmeye izin verme
        if existing_template.is_system:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="System templates cannot be deleted"
            )
        
        # Şablonu sil
        await prompt_repository.delete_prompt_template(
            db=db,
            template_id=template_id,
            user_id=current_user["id"]
        )
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.DATA,
            user_id=current_user["id"],
            action="delete",
            resource_type="prompt_template",
            resource_id=template_id,
            status="success",
            details={"name": existing_template.name},
            db=db
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting prompt template: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while deleting prompt template: {str(e)}"
        )