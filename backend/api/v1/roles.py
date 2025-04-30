# Last reviewed: 2025-04-30 05:03:25 UTC (User: Teeksss)
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List
import logging
import uuid
from datetime import datetime

from ...db.session import get_db
from ...schemas.role import RoleCreate, RoleUpdate, RoleResponse, RoleList
from ...schemas.permission import PermissionResponse, PermissionList
from ...models.role_permission import Role, Permission
from ...auth.jwt import get_current_active_user
from ...auth.authorization import requires_permission, requires_role
from ...repositories.role_repository import RoleRepository
from ...services.audit_service import AuditService, AuditLogType

router = APIRouter(
    prefix="/api/roles",
    tags=["roles"],
    responses={401: {"description": "Unauthorized"}, 403: {"description": "Forbidden"}}
)

logger = logging.getLogger(__name__)
role_repository = RoleRepository()
audit_service = AuditService()

@router.get("/", response_model=RoleList)
async def list_roles(
    search: Optional[str] = Query(None, description="Search roles by name or code"),
    is_system: Optional[bool] = Query(None, description="Filter system roles"),
    organization_id: Optional[str] = Query(None, description="Filter by organization"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    current_user: Dict[str, Any] = Depends(
        requires_permission("role", "list")
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Rolleri listeler
    
    Bu endpoint rolleri listeler. Süper kullanıcılar tüm rolleri görebilir.
    Normal kullanıcılar sadece kendi organizasyonlarına ait rolleri görebilir.
    """
    try:
        # Süper kullanıcı değilse, sadece kendi organizasyonuna ait rolleri gösterebilir
        if not current_user.get("is_superuser"):
            organization_id = current_user.get("organization_id")
        
        roles = await role_repository.list_roles(
            db=db,
            search=search,
            is_system=is_system,
            organization_id=organization_id,
            page=page,
            page_size=page_size
        )
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.ACCESS,
            user_id=current_user["id"],
            action="list",
            resource_type="roles",
            status="success",
            details={"search": search, "is_system": is_system, "organization_id": organization_id},
            db=db
        )
        
        return roles
        
    except Exception as e:
        logger.error(f"Error listing roles: {str(e)}")
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.ACCESS,
            user_id=current_user["id"],
            action="list",
            resource_type="roles",
            status="failure",
            details={"error": str(e)},
            db=db
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while listing roles: {str(e)}"
        )

@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: str = Path(..., description="Role ID"),
    current_user: Dict[str, Any] = Depends(
        requires_permission("role", "read")
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Rol detaylarını getirir
    """
    try:
        # Rolü getir
        role = await role_repository.get_role_by_id(db, role_id)
        
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        # İzin kontrolü - Süper kullanıcı değilse kendi organizasyonuna ait olmayan rolleri göremez
        if not current_user.get("is_superuser") and role.organization_id != current_user.get("organization_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this role"
            )
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.ACCESS,
            user_id=current_user["id"],
            action="read",
            resource_type="role",
            resource_id=role_id,
            status="success",
            db=db
        )
        
        # Rol ve izinlerini döndür
        return {
            "id": str(role.id),
            "name": role.name,
            "code": role.code,
            "description": role.description,
            "is_system": role.is_system,
            "is_active": role.is_active,
            "organization_id": str(role.organization_id) if role.organization_id else None,
            "created_at": role.created_at,
            "updated_at": role.updated_at,
            "permissions": [
                {
                    "id": str(permission.id),
                    "code": permission.code,
                    "name": permission.name,
                    "resource_type": permission.resource_type,
                    "action": permission.action,
                    "category": permission.category
                }
                for permission in role.permissions
            ],
            "user_count": len(role.users)
        }
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(f"Error getting role: {str(e)}")
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.ACCESS,
            user_id=current_user["id"],
            action="read",
            resource_type="role",
            resource_id=role_id,
            status="failure",
            details={"error": str(e)},
            db=db
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while getting role: {str(e)}"
        )

@router.post("/", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: RoleCreate,
    current_user: Dict[str, Any] = Depends(
        requires_permission("role", "create")
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Yeni rol oluşturur
    
    Sadece süper kullanıcılar sistem rolü oluşturabilir. Normal kullanıcılar
    kendi organizasyonlarına ait özel roller oluşturabilir.
    """
    try:
        # Sistem rolü oluşturma kontrolü - sadece süper kullanıcılar
        if role_data.is_system and not current_user.get("is_superuser"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only superusers can create system roles"
            )
        
        # Organizasyon ataması - süper kullanıcı değilse kendi organizasyonunu kullan
        organization_id = role_data.organization_id
        if not current_user.get("is_superuser"):
            organization_id = current_user.get("organization_id")
        
        # Rolü oluştur
        role = await role_repository.create_role(
            db=db,
            name=role_data.name,
            code=role_data.code,
            description=role_data.description,
            is_system=role_data.is_system,
            organization_id=organization_id,
            created_by=current_user["id"]
        )
        
        # İzinleri ekle
        if role_data.permission_ids:
            await role_repository.assign_permissions_to_role(
                db=db,
                role_id=str(role.id),
                permission_ids=role_data.permission_ids,
                assigned_by=current_user["id"]
            )
            
            await db.refresh(role)
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.ADMIN,
            user_id=current_user["id"],
            action="create",
            resource_type="role",
            resource_id=str(role.id),
            status="success",
            details={
                "name": role.name,
                "code": role.code,
                "is_system": role.is_system,
                "permission_count": len(role_data.permission_ids or [])
            },
            db=db
        )
        
        # Rolü döndür
        return {
            "id": str(role.id),
            "name": role.name,
            "code": role.code,
            "description": role.description,
            "is_system": role.is_system,
            "is_active": role.is_active,
            "organization_id": str(role.organization_id) if role.organization_id else None,
            "created_at": role.created_at,
            "updated_at": role.updated_at,
            "permissions": [
                {
                    "id": str(permission.id),
                    "code": permission.code,
                    "name": permission.name,
                    "resource_type": permission.resource_type,
                    "action": permission.action,
                    "category": permission.category
                }
                for permission in role.permissions
            ],
            "user_count": 0
        }
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(f"Error creating role: {str(e)}")
        await db.rollback()
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.ADMIN,
            user_id=current_user["id"],
            action="create",
            resource_type="role",
            status="failure",
            details={"error": str(e), "name": role_data.name, "code": role_data.code},
            db=db
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating role: {str(e)}"
        )

@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: str,
    role_data: RoleUpdate,
    current_user: Dict[str, Any] = Depends(
        requires_permission("role", "update")
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Rol bilgilerini günceller
    
    Sistem rolleri sadece süper kullanıcılar tarafından güncellenebilir.
    Normal kullanıcılar kendi organizasyonlarına ait özel rolleri güncelleyebilir.
    """
    try:
        # Rolü getir
        role = await role_repository.get_role_by_id(db, role_id)
        
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        # İzin kontrolü
        if role.is_system and not current_user.get("is_superuser"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only superusers can update system roles"
            )
        
        # Organizasyon kontrolü - süper kullanıcı değilse kendi organizasyonuna ait rolleri güncelleyebilir
        if not current_user.get("is_superuser") and role.organization_id != current_user.get("organization_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this role"
            )
        
        # Rolü güncelle
        updated_role = await role_repository.update_role(
            db=db,
            role_id=role_id,
            name=role_data.name,
            description=role_data.description,
            is_active=role_data.is_active,
            updated_by=current_user["id"]
        )
        
        # İzinleri güncelle
        if role_data.permission_ids is not None:
            # Önce tüm izinleri kaldır
            await role_repository.remove_all_permissions_from_role(
                db=db,
                role_id=role_id
            )
            
            # Sonra yeni izinleri ekle
            if role_data.permission_ids:
                await role_repository.assign_permissions_to_role(
                    db=db,
                    role_id=role_id,
                    permission_ids=role_data.permission_ids,
                    assigned_by=current_user["id"]
                )
            
            await db.refresh(updated_role)
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.ADMIN,
            user_id=current_user["id"],
            action="update",
            resource_type="role",
            resource_id=role_id,
            status="success",
            details={
                "name": updated_role.name,
                "is_active": updated_role.is_active,
                "permission_count": len(role_data.permission_ids or []) if role_data.permission_ids is not None else None
            },
            db=db
        )
        
        # Güncellenmiş rolü döndür
        return {
            "id": str(updated_role.id),
            "name": updated_role.name,
            "code": updated_role.code,
            "description": updated_role.description,
            "is_system": updated_role.is_system,
            "is_active": updated_role.is_active,
            "organization_id": str(updated_role.organization_id) if updated_role.organization_id else None,
            "created_at": updated_role.created_at,
            "updated_at": updated_role.updated_at,
            "permissions": [
                {
                    "id": str(permission.id),
                    "code": permission.code,
                    "name": permission.name,
                    "resource_type": permission.resource_type,
                    "action": permission.action,
                    "category": permission.category
                }
                for permission in updated_role.permissions
            ],
            "user_count": len(updated_role.users)
        }
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(f"Error updating role: {str(e)}")
        await db.rollback()
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.ADMIN,
            user_id=current_user["id"],
            action="update",
            resource_type="role",
            resource_id=role_id,
            status="failure",
            details={"error": str(e)},
            db=db
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while updating role: {str(e)}"
        )

@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: str,
    current_user: Dict[str, Any] = Depends(
        requires_permission("role", "delete")
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Rolü siler
    
    Sistem rolleri silinemez. Normal kullanıcılar kendi organizasyonlarına ait
    özel rolleri silebilir.
    """
    try:
        # Rolü getir
        role = await role_repository.get_role_by_id(db, role_id)
        
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        # Sistem rolü kontrolü
        if role.is_system:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="System roles cannot be deleted"
            )
        
        # Organizasyon kontrolü - süper kullanıcı değilse kendi organizasyonuna ait rolleri silebilir
        if not current_user.get("is_superuser") and role.organization_id != current_user.get("organization_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this role"
            )
        
        # Rolü sil
        success = await role_repository.delete_role(
            db=db,
            role_id=role_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete role"
            )
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.ADMIN,
            user_id=current_user["id"],
            action="delete",
            resource_type="role",
            resource_id=role_id,
            status="success",
            details={"name": role.name, "code": role.code},
            db=db
        )
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(f"Error deleting role: {str(e)}")
        await db.rollback()
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.ADMIN,
            user_id=current_user["id"],
            action="delete",
            resource_type="role",
            resource_id=role_id,
            status="failure",
            details={"error": str(e)},
            db=db
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while deleting role: {str(e)}"
        )

@router.get("/permissions/all", response_model=PermissionList)
async def list_all_permissions(
    category: Optional[str] = Query(None, description="Filter by category"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    action: Optional[str] = Query(None, description="Filter by action"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=500, description="Results per page"),
    current_user: Dict[str, Any] = Depends(
        requires_permission("permission", "list")
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Tüm izinleri listeler
    
    Bu endpoint sistemdeki tüm izinleri listeler. İzinler yönetici tarafından
    önceden tanımlanmıştır ve kullanıcılar tarafından değiştirilemez.
    """
    try:
        permissions = await role_repository.list_permissions(
            db=db,
            category=category,
            resource_type=resource_type,
            action=action,
            page=page,
            page_size=page_size
        )
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.ACCESS,
            user_id=current_user["id"],
            action="list",
            resource_type="permissions",
            status="success",
            details={"category": category, "resource_type": resource_type, "action": action},
            db=db
        )
        
        return permissions
        
    except Exception as e:
        logger.error(f"Error listing permissions: {str(e)}")
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.ACCESS,
            user_id=current_user["id"],
            action="list",
            resource_type="permissions",
            status="failure",
            details={"error": str(e)},
            db=db
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while listing permissions: {str(e)}"
        )

@router.post("/{role_id}/permissions", status_code=status.HTTP_200_OK)
async def assign_permissions_to_role(
    role_id: str,
    permission_ids: List[str] = Body(..., embed=True),
    current_user: Dict[str, Any] = Depends(
        requires_permission("role", "update")
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Role izin atar
    """
    try:
        # Rolü getir
        role = await role_repository.get_role_by_id(db, role_id)
        
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        # İzin kontrolü
        if role.is_system and not current_user.get("is_superuser"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only superusers can update system roles"
            )
        
        # Organizasyon kontrolü - süper kullanıcı değilse kendi organizasyonuna ait rolleri güncelleyebilir
        if not current_user.get("is_superuser") and role.organization_id != current_user.get("organization_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this role"
            )
        
        # İzinleri ekle
        success = await role_repository.assign_permissions_to_role(
            db=db,
            role_id=role_id,
            permission_ids=permission_ids,
            assigned_by=current_user["id"]
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to assign permissions"
            )
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.ADMIN,
            user_id=current_user["id"],
            action="update",
            resource_type="role_permissions",
            resource_id=role_id,
            status="success",
            details={
                "role_name": role.name,
                "permission_count": len(permission_ids)
            },
            db=db
        )
        
        return {"message": "Permissions assigned successfully"}
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(f"Error assigning permissions: {str(e)}")
        await db.rollback()
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.ADMIN,
            user_id=current_user["id"],
            action="update",
            resource_type="role_permissions",
            resource_id=role_id,
            status="failure",
            details={"error": str(e)},
            db=db
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while assigning permissions: {str(e)}"
        )

@router.delete("/{role_id}/permissions", status_code=status.HTTP_200_OK)
async def remove_permissions_from_role(
    role_id: str,
    permission_ids: List[str] = Body(..., embed=True),
    current_user: Dict[str, Any] = Depends(
        requires_permission("role", "update")
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Rolden izin kaldırır
    """
    try:
        # Rolü getir
        role = await role_repository.get_role_by_id(db, role_id)
        
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        # İzin kontrolü
        if role.is_system and not current_user.get("is_superuser"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only superusers can update system roles"
            )
        
        # Organizasyon kontrolü - süper kullanıcı değilse kendi organizasyonuna ait rolleri güncelleyebilir
        if not current_user.get("is_superuser") and role.organization_id != current_user.get("organization_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this role"
            )
        
        # İzinleri kaldır
        success = await role_repository.remove_permissions_from_role(
            db=db,
            role_id=role_id,
            permission_ids=permission_ids
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to remove permissions"
            )
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.ADMIN,
            user_id=current_user["id"],
            action="update",
            resource_type="role_permissions",
            resource_id=role_id,
            status="success",
            details={
                "role_name": role.name,
                "removed_permission_count": len(permission_ids)
            },
            db=db
        )
        
        return {"message": "Permissions removed successfully"}
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(f"Error removing permissions: {str(e)}")
        await db.rollback()
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.ADMIN,
            user_id=current_user["id"],
            action="update",
            resource_type="role_permissions",
            resource_id=role_id,
            status="failure",
            details={"error": str(e)},
            db=db
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while removing permissions: {str(e)}"
        )