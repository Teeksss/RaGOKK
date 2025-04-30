# Last reviewed: 2025-04-30 05:03:25 UTC (User: Teeksss)
import logging
from typing import Dict, Any, List, Optional, Union, Set
import json
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, and_

from ..db.session import get_db
from ..models.user import User
from ..models.role_permission import Role, Permission
from ..auth.jwt import get_current_user, get_current_active_user
from ..core.exceptions import PermissionError, ErrorCode

logger = logging.getLogger(__name__)

class AuthorizationService:
    """
    Rol tabanlı yetkilendirme servisi
    
    Bu servis şunları sağlar:
    - Kullanıcı izinlerini kontrol etme
    - Role ve izne göre erişim kontrolü
    - Kaynak tabanlı yetkilendirme
    """
    
    async def get_user_permissions(
        self, 
        user_id: str,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """
        Kullanıcının tüm izinlerini getir
        
        Args:
            user_id: Kullanıcı ID
            db: Veritabanı bağlantısı
            
        Returns:
            List[Dict[str, Any]]: İzin listesi
        """
        try:
            # Kullanıcıyı ve rollerini getir
            stmt = (
                select(User)
                .filter(User.id == user_id)
                .options(
                    selectinload(User.roles).selectinload(Role.permissions)
                )
            )
            
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                return []
            
            # Süper kullanıcı kontrolü - tüm izinlere sahip
            if user.is_superuser:
                # Tüm izinleri getir
                stmt = select(Permission)
                result = await db.execute(stmt)
                permissions = result.scalars().all()
                
                return [
                    {
                        "id": str(permission.id),
                        "code": permission.code,
                        "name": permission.name,
                        "resource_type": permission.resource_type,
                        "action": permission.action,
                        "category": permission.category,
                        "constraints": permission.constraints
                    }
                    for permission in permissions
                ]
            
            # Normal kullanıcılar için rol tabanlı izinleri getir
            permissions_map = {}  # Yinelenen izinleri önlemek için
            
            for role in user.roles:
                if not role.is_active:
                    continue
                    
                for permission in role.permissions:
                    permission_id = str(permission.id)
                    if permission_id not in permissions_map:
                        permissions_map[permission_id] = {
                            "id": permission_id,
                            "code": permission.code,
                            "name": permission.name,
                            "resource_type": permission.resource_type,
                            "action": permission.action,
                            "category": permission.category,
                            "constraints": permission.constraints
                        }
            
            return list(permissions_map.values())
            
        except Exception as e:
            logger.error(f"Error fetching user permissions: {str(e)}")
            return []
    
    async def has_permission(
        self,
        user_id: str,
        resource_type: str,
        action: str,
        db: AsyncSession,
        resource_id: Optional[str] = None,
        category: Optional[str] = None
    ) -> bool:
        """
        Kullanıcının belirli bir izne sahip olup olmadığını kontrol et
        
        Args:
            user_id: Kullanıcı ID
            resource_type: Kaynak türü (document, collection vb.)
            action: İşlem (create, read, update, delete vb.)
            db: Veritabanı bağlantısı
            resource_id: Kaynak ID (opsiyonel)
            category: İzin kategorisi (opsiyonel)
            
        Returns:
            bool: İzin varsa True
        """
        try:
            # Kullanıcıyı getir
            stmt = select(User).filter(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                return False
            
            # Süper kullanıcı her zaman erişebilir
            if user.is_superuser:
                return True
            
            # İlgili izinleri bul
            conditions = [
                Permission.resource_type == resource_type,
                Permission.action == action
            ]
            
            if category:
                conditions.append(Permission.category == category)
            
            stmt = (
                select(Permission)
                .join(role_permission)
                .join(Role)
                .join(user_role)
                .filter(
                    user_role.c.user_id == user_id,
                    Role.is_active == True,
                    *conditions
                )
            )
            
            result = await db.execute(stmt)
            permissions = result.scalars().all()
            
            # İzin yoksa
            if not permissions:
                return False
            
            # Kaynak ID'si belirtilmişse, kısıtlamaları kontrol et
            if resource_id:
                for permission in permissions:
                    # Kısıtlama yoksa veya boşsa, erişime izin ver
                    if not permission.constraints:
                        return True
                    
                    # Kısıtlamaları kontrol et
                    constraints = permission.constraints
                    
                    # Belirli bir ID kısıtlaması var mı?
                    if "allowed_ids" in constraints:
                        allowed_ids = constraints["allowed_ids"]
                        if resource_id in allowed_ids:
                            return True
                    
                    # Sahiplik kısıtlaması var mı?
                    if "ownership_required" in constraints and constraints["ownership_required"]:
                        # Kullanıcının kendi kaynağına erişimi her zaman var
                        # (Gerçek sahiplik kontrolü kaynak türüne özel servislerde yapılmalı)
                        if resource_id:
                            return True
                    
                    # Organizasyon kısıtlaması var mı?
                    if "same_organization" in constraints and constraints["same_organization"]:
                        # Bu durumda kaynağın organizasyon bilgisi ile kullanıcı organizasyonu karşılaştırılmalı
                        # (Gerçek organizasyon kontrolü kaynak türüne özel servislerde yapılmalı)
                        if user.organization_id:
                            return True
                    
                    # Diğer kısıtlamalar burada uygulanabilir
                
                # Hiçbir kısıtlama izin vermediyse erişim reddedilir
                return False
            
            # Kaynak ID belirtilmemişse, izin varsa erişime izin ver
            return len(permissions) > 0
            
        except Exception as e:
            logger.error(f"Error checking permission: {str(e)}")
            return False
    
    async def get_user_roles(
        self,
        user_id: str,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """
        Kullanıcının rollerini getir
        
        Args:
            user_id: Kullanıcı ID
            db: Veritabanı bağlantısı
            
        Returns:
            List[Dict[str, Any]]: Rol listesi
        """
        try:
            # Kullanıcı rollerini getir
            stmt = (
                select(Role)
                .join(user_role)
                .filter(
                    user_role.c.user_id == user_id,
                    Role.is_active == True
                )
            )
            
            result = await db.execute(stmt)
            roles = result.scalars().all()
            
            return [
                {
                    "id": str(role.id),
                    "name": role.name,
                    "code": role.code,
                    "description": role.description,
                    "is_system": role.is_system,
                    "organization_id": str(role.organization_id) if role.organization_id else None
                }
                for role in roles
            ]
            
        except Exception as e:
            logger.error(f"Error fetching user roles: {str(e)}")
            return []
    
    async def assign_role_to_user(
        self,
        user_id: str,
        role_id: str,
        db: AsyncSession,
        assigned_by: Optional[str] = None
    ) -> bool:
        """
        Kullanıcıya rol ata
        
        Args:
            user_id: Kullanıcı ID
            role_id: Rol ID
            db: Veritabanı bağlantısı
            assigned_by: Atamayı yapan kullanıcı ID (opsiyonel)
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            # Kullanıcı ve rolü kontrol et
            stmt = select(User).filter(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                return False
            
            stmt = select(Role).filter(Role.id == role_id)
            result = await db.execute(stmt)
            role = result.scalar_one_or_none()
            
            if not role:
                return False
            
            # Rol zaten atanmış mı kontrol et
            stmt = (
                select(user_role)
                .filter(
                    user_role.c.user_id == user_id,
                    user_role.c.role_id == role_id
                )
            )
            
            result = await db.execute(stmt)
            existing = result.first()
            
            if existing:
                return True  # Zaten atanmış
            
            # Yeni atamayı ekle
            values = {
                "user_id": user_id,
                "role_id": role_id,
                "created_at": datetime.now(timezone.utc),
                "created_by": assigned_by
            }
            
            stmt = user_role.insert().values(**values)
            await db.execute(stmt)
            await db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error assigning role to user: {str(e)}")
            await db.rollback()
            return False
    
    async def remove_role_from_user(
        self,
        user_id: str,
        role_id: str,
        db: AsyncSession
    ) -> bool:
        """
        Kullanıcıdan rol kaldır
        
        Args:
            user_id: Kullanıcı ID
            role_id: Rol ID
            db: Veritabanı bağlantısı
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            # Rol atamasını sil
            stmt = (
                user_role.delete()
                .filter(
                    user_role.c.user_id == user_id,
                    user_role.c.role_id == role_id
                )
            )
            
            await db.execute(stmt)
            await db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error removing role from user: {str(e)}")
            await db.rollback()
            return False

# Yetkilendirme middleware fonksiyonları
def requires_permission(resource_type: str, action: str, category: Optional[str] = None):
    """
    Belirli bir izin gerektiren endpoint için yetkilendirme kontrolü yapan bir bağımlılık fonksiyonu
    
    Args:
        resource_type: Kaynak türü (document, collection vb.)
        action: İşlem (create, read, update, delete vb.)
        category: İzin kategorisi (opsiyonel)
        
    Returns:
        Callable: FastAPI bağımlılık fonksiyonu
    """
    auth_service = AuthorizationService()
    
    async def check_permission(
        current_user: Dict[str, Any] = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
    ):
        user_id = current_user["id"]
        
        # Süper kullanıcı kontrolü
        if current_user.get("is_superuser", False):
            return current_user
        
        # İzin kontrolü
        has_permission = await auth_service.has_permission(
            user_id=user_id,
            resource_type=resource_type,
            action=action,
            category=category,
            db=db
        )
        
        if not has_permission:
            raise PermissionError(
                message=f"Permission denied. Required: {resource_type}:{action}",
                error_code=ErrorCode.INSUFFICIENT_PRIVILEGES,
                detail=f"User does not have the required permission: {resource_type}:{action}"
            )
        
        return current_user
    
    return check_permission

def requires_resource_permission(
    resource_type: str, 
    action: str, 
    resource_id_name: str = "id", 
    category: Optional[str] = None
):
    """
    Belirli bir kaynak üzerinde izin gerektiren endpoint için yetkilendirme kontrolü
    
    Args:
        resource_type: Kaynak türü (document, collection vb.)
        action: İşlem (create, read, update, delete vb.)
        resource_id_name: URL'deki kaynak ID parametre adı
        category: İzin kategorisi (opsiyonel)
        
    Returns:
        Callable: FastAPI bağımlılık fonksiyonu
    """
    auth_service = AuthorizationService()
    
    async def check_resource_permission(
        current_user: Dict[str, Any] = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
        **path_params
    ):
        user_id = current_user["id"]
        
        # Süper kullanıcı kontrolü
        if current_user.get("is_superuser", False):
            return current_user
        
        # Kaynak ID'sini URL'den al
        resource_id = path_params.get(resource_id_name)
        
        if not resource_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing resource ID parameter: {resource_id_name}"
            )
        
        # İzin kontrolü
        has_permission = await auth_service.has_permission(
            user_id=user_id,
            resource_type=resource_type,
            action=action,
            resource_id=resource_id,
            category=category,
            db=db
        )
        
        if not has_permission:
            raise PermissionError(
                message=f"Permission denied for {resource_type} with ID {resource_id}",
                error_code=ErrorCode.INSUFFICIENT_PRIVILEGES,
                detail=f"User does not have permission to {action} this {resource_type}"
            )
        
        return current_user
    
    return check_resource_permission

def requires_role(role_code: Union[str, List[str]]):
    """
    Belirli bir rol gerektiren endpoint için yetkilendirme kontrolü
    
    Args:
        role_code: Gerekli rol kodu veya kodları listesi
        
    Returns:
        Callable: FastAPI bağımlılık fonksiyonu
    """
    async def check_role(
        current_user: Dict[str, Any] = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
    ):
        user_id = current_user["id"]
        
        # Süper kullanıcı kontrolü
        if current_user.get("is_superuser", False):
            return current_user
        
        # Kullanıcı rollerini al
        auth_service = AuthorizationService()
        user_roles = await auth_service.get_user_roles(user_id, db)
        
        user_role_codes = {role["code"] for role in user_roles}
        
        # Rol kontrolü
        required_roles = [role_code] if isinstance(role_code, str) else role_code
        
        if not any(code in user_role_codes for code in required_roles):
            role_list = ", ".join(required_roles)
            raise PermissionError(
                message=f"Permission denied. Required role(s): {role_list}",
                error_code=ErrorCode.INSUFFICIENT_PRIVILEGES,
                detail=f"User does not have any of the required roles: {role_list}"
            )
        
        return current_user
    
    return check_role