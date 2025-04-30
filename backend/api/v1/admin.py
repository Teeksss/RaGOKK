# Last reviewed: 2025-04-30 07:41:30 UTC (User: Teeksss)
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
import logging

from ...db.session import get_db
from ...auth.rbac import require_role, require_permission, Role, Permission
from ...repositories.user_repository import UserRepository
from ...schemas.user import UserResponse, UserCreate, UserUpdate
from ...models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)

user_repository = UserRepository()

@router.get("/users", response_model=List[UserResponse], dependencies=[Depends(require_permission(Permission.VIEW_USERS))])
async def get_all_users(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    organization_id: Optional[str] = None
):
    """
    Tüm kullanıcıları getirir (Admin yetkilendirilmesi gerektirir)
    """
    try:
        users = await user_repository.get_users(
            db=db, 
            skip=skip, 
            limit=limit,
            organization_id=organization_id
        )
        
        return users
        
    except Exception as e:
        logger.error(f"Error getting all users: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting users: {str(e)}"
        )

@router.post("/users", response_model=UserResponse, dependencies=[Depends(require_permission(Permission.CREATE_USER))])
async def create_user(
    user_create: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Yeni bir kullanıcı oluşturur (Admin yetkilendirilmesi gerektirir)
    """
    try:
        # Email kontrolü
        existing_user = await user_repository.get_user_by_email(db, user_create.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Kullanıcı oluştur
        user = User(
            email=user_create.email,
            hashed_password=user_create.password,  # Repository hash'leyecek
            full_name=user_create.full_name,
            is_active=user_create.is_active,
            roles=user_create.roles,
            organization_id=user_create.organization_id
        )
        
        # Metadata
        if user_create.permissions:
            user.metadata = {"permissions": user_create.permissions}
        
        # Kullanıcıyı kaydet
        user = await user_repository.create_user(db, user)
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}"
        )

@router.put("/users/{user_id}", response_model=UserResponse, dependencies=[Depends(require_permission(Permission.EDIT_USER))])
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Kullanıcı bilgilerini günceller (Admin yetkilendirilmesi gerektirir)
    """
    try:
        # Kullanıcıyı güncelle
        updated_user = await user_repository.update_user(
            db=db,
            user_id=user_id,
            **user_update.dict(exclude_unset=True)  # Sadece ayarlanmış alanları kullan
        )
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return updated_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user: {str(e)}"
        )

@router.delete("/users/{user_id}", dependencies=[Depends(require_permission(Permission.DELETE_USER))])
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Kullanıcıyı siler (Admin yetkilendirilmesi gerektirir)
    """
    try:
        # Kullanıcıyı sil
        result = await user_repository.delete_user(db, user_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {"message": "User deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting user: {str(e)}"
        )

@router.get("/system-info", dependencies=[Depends(require_permission(Permission.SYSTEM_CONFIG))])
async def get_system_info():
    """
    Sistem bilgilerini getirir (Admin yetkilendirilmesi gerektirir)
    """
    try:
        import platform
        import psutil
        import os
        
        # Sistem bilgilerini topla
        system_info = {
            "os": platform.system(),
            "os_version": platform.version(),
            "python_version": platform.python_version(),
            "cpu_count": os.cpu_count(),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2),
            "memory_available_gb": round(psutil.virtual_memory().available / (1024 ** 3), 2),
            "disk_usage_percent": psutil.disk_usage('/').percent
        }
        
        return system_info
        
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting system info: {str(e)}"
        )