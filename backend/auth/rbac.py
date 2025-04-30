# Last reviewed: 2025-04-30 07:41:30 UTC (User: Teeksss)
from enum import Enum
from typing import Dict, Any, List, Optional, Callable, Union, Set
from fastapi import Depends, HTTPException, status

from .enhanced_jwt import get_current_user_enhanced

class Permission(str, Enum):
    """Sistem izinleri"""
    # Belge izinleri
    VIEW_DOCUMENTS = "view:documents"
    CREATE_DOCUMENT = "create:document"
    EDIT_DOCUMENT = "edit:document"
    DELETE_DOCUMENT = "delete:document"
    
    # Kullanıcı izinleri
    VIEW_USERS = "view:users"
    CREATE_USER = "create:user"
    EDIT_USER = "edit:user"
    DELETE_USER = "delete:user"
    
    # Organizasyon izinleri
    VIEW_ORGANIZATION = "view:organization"
    MANAGE_ORGANIZATION = "manage:organization"
    
    # Sorgu izinleri
    RUN_QUERIES = "run:queries"
    VIEW_QUERY_HISTORY = "view:query_history"
    
    # Analitik izinleri
    VIEW_ANALYTICS = "view:analytics"
    
    # Admin izinleri
    ADMIN_PANEL = "access:admin"
    SYSTEM_CONFIG = "manage:system"

class Role(str, Enum):
    """Kullanıcı rolleri"""
    ADMIN = "admin"
    USER = "user"
    EDITOR = "editor" 
    VIEWER = "viewer"
    GUEST = "guest"
    ORG_ADMIN = "org_admin"
    ORG_MANAGER = "org_manager"

# Rol-izin matrisi
ROLE_PERMISSIONS: Dict[Role, List[Permission]] = {
    Role.ADMIN: [p for p in Permission],  # Admin tüm izinlere sahip
    
    Role.USER: [
        Permission.VIEW_DOCUMENTS,
        Permission.CREATE_DOCUMENT,
        Permission.EDIT_DOCUMENT,
        Permission.RUN_QUERIES,
        Permission.VIEW_QUERY_HISTORY,
        Permission.VIEW_ANALYTICS
    ],
    
    Role.EDITOR: [
        Permission.VIEW_DOCUMENTS,
        Permission.CREATE_DOCUMENT,
        Permission.EDIT_DOCUMENT,
        Permission.DELETE_DOCUMENT,
        Permission.RUN_QUERIES,
        Permission.VIEW_QUERY_HISTORY
    ],
    
    Role.VIEWER: [
        Permission.VIEW_DOCUMENTS,
        Permission.RUN_QUERIES,
        Permission.VIEW_QUERY_HISTORY
    ],
    
    Role.GUEST: [
        Permission.VIEW_DOCUMENTS,
        Permission.RUN_QUERIES
    ],
    
    Role.ORG_ADMIN: [
        Permission.VIEW_DOCUMENTS,
        Permission.CREATE_DOCUMENT,
        Permission.EDIT_DOCUMENT,
        Permission.DELETE_DOCUMENT,
        Permission.VIEW_USERS,
        Permission.CREATE_USER,
        Permission.EDIT_USER,
        Permission.DELETE_USER,
        Permission.VIEW_ORGANIZATION,
        Permission.MANAGE_ORGANIZATION,
        Permission.RUN_QUERIES,
        Permission.VIEW_QUERY_HISTORY,
        Permission.VIEW_ANALYTICS
    ],
    
    Role.ORG_MANAGER: [
        Permission.VIEW_DOCUMENTS,
        Permission.CREATE_DOCUMENT,
        Permission.EDIT_DOCUMENT,
        Permission.VIEW_USERS,
        Permission.VIEW_ORGANIZATION,
        Permission.RUN_QUERIES,
        Permission.VIEW_QUERY_HISTORY,
        Permission.VIEW_ANALYTICS
    ]
}

class RBACChecker:
    """
    Rol tabanlı erişim kontrolü sınıfı
    """
    
    @staticmethod
    def has_role(user: Dict[str, Any], required_role: Union[Role, str]) -> bool:
        """
        Kullanıcının belirli bir role sahip olup olmadığını kontrol eder
        
        Args:
            user: Kullanıcı bilgileri (token'dan çıkarılan)
            required_role: Gerekli rol
            
        Returns:
            bool: Role sahipse True
        """
        roles = user.get("roles", [])
        
        # Admin her zaman tüm rollere sahiptir
        if Role.ADMIN in roles:
            return True
            
        # Gerekli rolü kontrol et
        if isinstance(required_role, str):
            return required_role in roles
        
        return required_role.value in roles
    
    @staticmethod
    def has_permission(user: Dict[str, Any], required_permission: Union[Permission, str]) -> bool:
        """
        Kullanıcının belirli bir izne sahip olup olmadığını kontrol eder
        
        Args:
            user: Kullanıcı bilgileri (token'dan çıkarılan)
            required_permission: Gerekli izin
            
        Returns:
            bool: İzne sahipse True
        """
        # Özel izinleri kontrol et
        user_permissions = user.get("permissions", [])
        
        # Permission enum veya string olabilir
        perm_value = required_permission
        if isinstance(required_permission, Permission):
            perm_value = required_permission.value
            
        # Doğrudan izni var mı?
        if perm_value in user_permissions:
            return True
        
        # Rollerden gelen izinleri kontrol et
        roles = user.get("roles", [])
        
        for role_name in roles:
            if role_name in [r.value for r in Role]:
                role = Role(role_name)
                if role in ROLE_PERMISSIONS:
                    if isinstance(required_permission, str):
                        if required_permission in [p.value for p in ROLE_PERMISSIONS[role]]:
                            return True
                    else:
                        if required_permission in ROLE_PERMISSIONS[role]:
                            return True
        
        return False
    
    @staticmethod
    def has_any_permission(user: Dict[str, Any], permissions: List[Union[Permission, str]]) -> bool:
        """
        Kullanıcının herhangi bir izne sahip olup olmadığını kontrol eder
        
        Args:
            user: Kullanıcı bilgileri
            permissions: İzin listesi
            
        Returns:
            bool: Herhangi bir izne sahipse True
        """
        return any(RBACChecker.has_permission(user, perm) for perm in permissions)
    
    @staticmethod
    def has_all_permissions(user: Dict[str, Any], permissions: List[Union[Permission, str]]) -> bool:
        """
        Kullanıcının tüm izinlere sahip olup olmadığını kontrol eder
        
        Args:
            user: Kullanıcı bilgileri
            permissions: İzin listesi
            
        Returns:
            bool: Tüm izinlere sahipse True
        """
        return all(RBACChecker.has_permission(user, perm) for perm in permissions)

# Bağımlılık fonksiyonları
def require_permission(
    required_permission: Union[Permission, str],
    error_message: Optional[str] = None
):
    """
    Belirli bir izin gerektirir
    
    Args:
        required_permission: Gerekli izin
        error_message: Özel hata mesajı (opsiyonel)
    """
    async def dependency(current_user: Dict[str, Any] = Depends(get_current_user_enhanced)):
        if not RBACChecker.has_permission(current_user, required_permission):
            permission_name = required_permission
            if isinstance(required_permission, Permission):
                permission_name = required_permission.value
                
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_message or f"Permission denied: {permission_name} is required"
            )
        return current_user
    
    return dependency

def require_role(
    required_role: Union[Role, str], 
    error_message: Optional[str] = None
):
    """
    Belirli bir rol gerektirir
    
    Args:
        required_role: Gerekli rol
        error_message: Özel hata mesajı (opsiyonel)
    """
    async def dependency(current_user: Dict[str, Any] = Depends(get_current_user_enhanced)):
        if not RBACChecker.has_role(current_user, required_role):
            role_name = required_role
            if isinstance(required_role, Role):
                role_name = required_role.value
                
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_message or f"Role denied: {role_name} is required"
            )
        return current_user
    
    return dependency

def require_any_permission(
    permissions: List[Union[Permission, str]],
    error_message: Optional[str] = None
):
    """
    Verilen izinlerden herhangi birine sahip olmayı gerektirir
    """
    async def dependency(current_user: Dict[str, Any] = Depends(get_current_user_enhanced)):
        if not RBACChecker.has_any_permission(current_user, permissions):
            perm_names = [p.value if isinstance(p, Permission) else p for p in permissions]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_message or f"Permission denied: One of these permissions is required: {', '.join(perm_names)}"
            )
        return current_user
    
    return dependency

def require_all_permissions(
    permissions: List[Union[Permission, str]],
    error_message: Optional[str] = None
):
    """
    Verilen izinlerin tümüne sahip olmayı gerektirir
    """
    async def dependency(current_user: Dict[str, Any] = Depends(get_current_user_enhanced)):
        if not RBACChecker.has_all_permissions(current_user, permissions):
            perm_names = [p.value if isinstance(p, Permission) else p for p in permissions]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_message or f"Permission denied: All these permissions are required: {', '.join(perm_names)}"
            )
        return current_user
    
    return dependency

# Örnek kullanım:
"""
@router.get("/admin", dependencies=[Depends(require_role(Role.ADMIN))])
async def admin_endpoint():
    return {"message": "Admin access granted"}

@router.get("/documents", dependencies=[Depends(require_permission(Permission.VIEW_DOCUMENTS))])
async def documents_endpoint():
    return {"message": "Documents access granted"}
"""