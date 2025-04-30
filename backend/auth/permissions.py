# Last reviewed: 2025-04-30 07:30:01 UTC (User: Teeksss)
from enum import Enum, auto
from typing import Dict, List, Set, Optional, Union
from fastapi import Depends, HTTPException, status

class Permission(str, Enum):
    """İzin tipleri"""
    VIEW_DOCUMENTS = "view:documents"
    CREATE_DOCUMENT = "create:document"
    EDIT_DOCUMENT = "edit:document"
    DELETE_DOCUMENT = "delete:document"
    MANAGE_USERS = "manage:users"
    MANAGE_ORGANIZATION = "manage:organization"
    RUN_QUERIES = "run:queries"
    VIEW_ANALYTICS = "view:analytics"
    ADMIN_PANEL = "access:admin"

class Role(str, Enum):
    """Kullanıcı rolleri"""
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"
    GUEST = "guest"
    ORGANIZATION_ADMIN = "org_admin"

# Rol-İzin matrisi
ROLE_PERMISSIONS: Dict[Role, List[Permission]] = {
    Role.ADMIN: [p for p in Permission],  # Admin tüm izinlere sahip
    Role.EDITOR: [
        Permission.VIEW_DOCUMENTS,
        Permission.CREATE_DOCUMENT,
        Permission.EDIT_DOCUMENT,
        Permission.RUN_QUERIES,
        Permission.VIEW_ANALYTICS
    ],
    Role.VIEWER: [
        Permission.VIEW_DOCUMENTS,
        Permission.RUN_QUERIES,
        Permission.VIEW_ANALYTICS
    ],
    Role.GUEST: [
        Permission.VIEW_DOCUMENTS,
        Permission.RUN_QUERIES
    ],
    Role.ORGANIZATION_ADMIN: [
        Permission.VIEW_DOCUMENTS,
        Permission.CREATE_DOCUMENT,
        Permission.EDIT_DOCUMENT,
        Permission.DELETE_DOCUMENT,
        Permission.MANAGE_USERS,
        Permission.RUN_QUERIES,
        Permission.VIEW_ANALYTICS,
    ]
}

class PermissionChecker:
    """İzin kontrolü yapan sınıf"""
    
    @staticmethod
    def has_permission(user_data: Dict, required_permission: Permission) -> bool:
        """
        Kullanıcının belirli bir izne sahip olup olmadığını kontrol eder
        
        Args:
            user_data: Kullanıcı verisi (JWT token'dan çıkarılan)
            required_permission: Gerekli izin
            
        Returns:
            bool: İzne sahipse True
        """
        # Kullanıcı rollerini al
        roles = user_data.get("roles", [])
        
        # Kullanıcı özel izinlerini al
        custom_permissions = user_data.get("permissions", [])
        
        # Özel izinlerde doğrudan varsa kabul et
        if required_permission in custom_permissions:
            return True
        
        # Her rol için izinleri kontrol et
        for role in roles:
            if role in ROLE_PERMISSIONS and required_permission in ROLE_PERMISSIONS[role]:
                return True
                
        return False

    @staticmethod
    def has_any_permission(user_data: Dict, permissions: List[Permission]) -> bool:
        """
        Kullanıcının izin listesinden herhangi birine sahip olup olmadığını kontrol eder
        """
        return any(PermissionChecker.has_permission(user_data, permission) for permission in permissions)
    
    @staticmethod
    def has_all_permissions(user_data: Dict, permissions: List[Permission]) -> bool:
        """
        Kullanıcının tüm izin listesine sahip olup olmadığını kontrol eder
        """
        return all(PermissionChecker.has_permission(user_data, permission) for permission in permissions)

# FastAPI için bağımlılık fonksiyonu
def require_permission(required_permission: Permission):
    """
    Belirli bir izin gerektiren endpoint'ler için bağımlılık
    
    Kullanım:
    @app.get("/admin", dependencies=[Depends(require_permission(Permission.ADMIN_PANEL))])
    """
    def dependency(current_user: Dict = Depends(get_current_active_user)):
        if not PermissionChecker.has_permission(current_user, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {required_permission} is required"
            )
        return current_user
    
    return dependency