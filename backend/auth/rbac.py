# Last reviewed: 2025-04-29 12:35:57 UTC (User: TeeksssVisual Diff)
from enum import Enum
from typing import List, Dict, Any, Optional, Set, Union, Callable
import json
import logging
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ..db.session import get_db
from ..db import models
from ..auth.jwt import get_current_active_user

logger = logging.getLogger(__name__)

class Permission(str, Enum):
    """Sistem izinleri"""
    # Doküman izinleri
    READ_DOCUMENT = "document:read"
    WRITE_DOCUMENT = "document:write"
    DELETE_DOCUMENT = "document:delete"
    SHARE_DOCUMENT = "document:share"
    
    # Koleksiyon izinleri
    READ_COLLECTION = "collection:read"
    WRITE_COLLECTION = "collection:write"
    DELETE_COLLECTION = "collection:delete"
    
    # Kullanıcı yönetimi izinleri
    READ_USER = "user:read"
    WRITE_USER = "user:write"
    DELETE_USER = "user:delete"
    
    # Sistem yönetimi izinleri
    READ_SYSTEM = "system:read"
    WRITE_SYSTEM = "system:write"
    
    # API izinleri
    USE_API = "api:use"
    ADMIN_API = "api:admin"
    
    # Özel izinler
    CREATE_PUBLIC_DOCUMENT = "document:create_public"
    VIEW_ANALYTICS = "analytics:view"
    RUN_REPORTS = "reports:run"

class Role(str, Enum):
    """Sistem rolleri"""
    ADMIN = "admin"  # Tam sistem yönetimi
    MANAGER = "manager"  # Belge ve kullanıcı yönetimi
    CONTENT_ADMIN = "content_admin"  # İçerik yönetimi
    USER = "user"  # Normal kullanıcı
    GUEST = "guest"  # Misafir/sınırlı erişim
    API_USER = "api_user"  # API erişimi
    READONLY = "readonly"  # Salt okunur erişim

class PermissionSet(BaseModel):
    """Kullanıcı izin kümesi"""
    user_id: str
    roles: List[str] = []
    permissions: List[str] = []
    resource_permissions: Dict[str, List[str]] = {}
    
    def can(self, permission: Union[str, Permission]) -> bool:
        """
        Kullanıcının belirli bir izne sahip olup olmadığını kontrol eder
        
        Args:
            permission: Kontrol edilecek izin
            
        Returns:
            bool: İzne sahipse True
        """
        perm_str = permission if isinstance(permission, str) else permission.value
        
        # Doğrudan izinleri kontrol et
        if perm_str in self.permissions:
            return True
        
        # Admin rolü her şeyi yapabilir
        if Role.ADMIN in self.roles:
            return True
        
        # Rol bazlı izinleri kontrol et
        if any(perm_str in ROLE_PERMISSIONS.get(role, []) for role in self.roles):
            return True
        
        return False
    
    def can_access_resource(self, resource_type: str, resource_id: str, permission: Union[str, Permission]) -> bool:
        """
        Kullanıcının belirli bir kaynağa erişim izni olup olmadığını kontrol eder
        
        Args:
            resource_type: Kaynak türü (ör. 'document', 'collection')
            resource_id: Kaynak ID'si
            permission: Kontrol edilecek izin
            
        Returns:
            bool: İzne sahipse True
        """
        perm_str = permission if isinstance(permission, str) else permission.value
        
        # Doğrudan kaynağa özel izinleri kontrol et
        resource_key = f"{resource_type}:{resource_id}"
        if resource_key in self.resource_permissions:
            if perm_str in self.resource_permissions[resource_key]:
                return True
        
        # Genel izinleri kontrol et
        return self.can(permission)


# Rol bazlı izinler
ROLE_PERMISSIONS: Dict[str, List[Permission]] = {
    Role.ADMIN: [
        # Adminler tüm izinlere sahiptir
    ],
    Role.MANAGER: [
        Permission.READ_DOCUMENT,
        Permission.WRITE_DOCUMENT,
        Permission.SHARE_DOCUMENT,
        Permission.DELETE_DOCUMENT,
        Permission.READ_COLLECTION,
        Permission.WRITE_COLLECTION,
        Permission.DELETE_COLLECTION,
        Permission.READ_USER,
        Permission.CREATE_PUBLIC_DOCUMENT,
        Permission.VIEW_ANALYTICS,
        Permission.RUN_REPORTS
    ],
    Role.CONTENT_ADMIN: [
        Permission.READ_DOCUMENT,
        Permission.WRITE_DOCUMENT,
        Permission.SHARE_DOCUMENT,
        Permission.DELETE_DOCUMENT,
        Permission.READ_COLLECTION,
        Permission.WRITE_COLLECTION,
        Permission.CREATE_PUBLIC_DOCUMENT
    ],
    Role.USER: [
        Permission.READ_DOCUMENT,
        Permission.WRITE_DOCUMENT,
        Permission.SHARE_DOCUMENT,
        Permission.READ_COLLECTION
    ],
    Role.GUEST: [
        Permission.READ_DOCUMENT
    ],
    Role.API_USER: [
        Permission.USE_API,
        Permission.READ_DOCUMENT,
        Permission.WRITE_DOCUMENT
    ],
    Role.READONLY: [
        Permission.READ_DOCUMENT,
        Permission.READ_COLLECTION,
        Permission.READ_USER
    ]
}


class RBACService:
    """
    Rol bazlı erişim kontrol servisi
    
    Bu servis, kullanıcıların izinlerini ve rollerini yönetir.
    Hem genel izinler hem de kaynak bazlı özel izinleri destekler.
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def get_user_permissions(self, user_id: str) -> PermissionSet:
        """
        Kullanıcı izinlerini getirir
        
        Args:
            user_id: Kullanıcı ID'si
            
        Returns:
            PermissionSet: Kullanıcı izin kümesi
        """
        # Kullanıcı rollerini getir
        user_roles = await self._get_user_roles(user_id)
        
        # Kullanıcının doğrudan izinlerini getir
        direct_permissions = await self._get_direct_permissions(user_id)
        
        # Rol bazlı izinleri getir
        role_permissions = []
        for role in user_roles:
            role_perms = ROLE_PERMISSIONS.get(role, [])
            role_permissions.extend([p.value for p in role_perms])
        
        # Kaynak bazlı izinleri getir
        resource_permissions = await self._get_resource_permissions(user_id)
        
        # İzin kümesini oluştur
        return PermissionSet(
            user_id=user_id,
            roles=user_roles,
            permissions=list(set(direct_permissions + role_permissions)),
            resource_permissions=resource_permissions
        )
    
    async def _get_user_roles(self, user_id: str) -> List[str]:
        """
        Kullanıcı rollerini getirir
        
        Args:
            user_id: Kullanıcı ID'si
            
        Returns:
            List[str]: Rol listesi
        """
        query = """
        SELECT role FROM user_roles WHERE user_id = :user_id
        """
        result = await self.db.execute(query, {"user_id": user_id})
        return [row[0] for row in result]
    
    async def _get_direct_permissions(self, user_id: str) -> List[str]:
        """
        Kullanıcının doğrudan izinlerini getirir
        
        Args:
            user_id: Kullanıcı ID'si
            
        Returns:
            List[str]: İzin listesi
        """
        query = """
        SELECT permission FROM user_permissions WHERE user_id = :user_id
        """
        result = await self.db.execute(query, {"user_id": user_id})
        return [row[0] for row in result]
    
    async def _get_resource_permissions(self, user_id: str) -> Dict[str, List[str]]:
        """
        Kullanıcının kaynak bazlı izinlerini getirir
        
        Args:
            user_id: Kullanıcı ID'si
            
        Returns:
            Dict[str, List[str]]: Kaynak bazlı izinler
        """
        resource_permissions = {}
        
        # Doküman izinleri
        document_query = """
        SELECT document_id, permission_type FROM user_document_permissions
        WHERE user_id = :user_id
        """
        doc_result = await self.db.execute(document_query, {"user_id": user_id})
        
        for doc_id, perm_type in doc_result:
            resource_key = f"document:{doc_id}"
            
            # İzin türünü izin listesine dönüştür
            permissions = []
            if perm_type == "read":
                permissions = ["document:read"]
            elif perm_type == "write":
                permissions = ["document:read", "document:write"]
            elif perm_type == "admin":
                permissions = ["document:read", "document:write", "document:delete", "document:share"]
            
            resource_permissions[resource_key] = permissions
        
        # Koleksiyon izinleri
        collection_query = """
        SELECT collection_id, permission_type FROM user_collection_permissions
        WHERE user_id = :user_id
        """
        coll_result = await self.db.execute(collection_query, {"user_id": user_id})
        
        for coll_id, perm_type in coll_result:
            resource_key = f"collection:{coll_id}"
            
            # İzin türünü izin listesine dönüştür
            permissions = []
            if perm_type == "read":
                permissions = ["collection:read"]
            elif perm_type == "write":
                permissions = ["collection:read", "collection:write"]
            elif perm_type == "admin":
                permissions = ["collection:read", "collection:write", "collection:delete"]
            
            resource_permissions[resource_key] = permissions
        
        return resource_permissions
    
    async def add_role_to_user(self, user_id: str, role: Union[str, Role]) -> bool:
        """
        Kullanıcıya rol ekler
        
        Args:
            user_id: Kullanıcı ID'si
            role: Eklenecek rol
            
        Returns:
            bool: Başarılıysa True
        """
        role_str = role if isinstance(role, str) else role.value
        
        # Rolün geçerli olup olmadığını kontrol et
        if role_str not in [r.value for r in Role]:
            raise ValueError(f"Invalid role: {role_str}")
        
        # Kullanıcının bu role zaten sahip olup olmadığını kontrol et
        check_query = """
        SELECT 1 FROM user_roles WHERE user_id = :user_id AND role = :role
        """
        check_result = await self.db.execute(check_query, {"user_id": user_id, "role": role_str})
        
        if check_result.scalar():
            return True  # Zaten bu role sahip
        
        # Rolü ekle
        insert_query = """
        INSERT INTO user_roles (user_id, role) VALUES (:user_id, :role)
        """
        await self.db.execute(insert_query, {"user_id": user_id, "role": role_str})
        
        return True
    
    async def remove_role_from_user(self, user_id: str, role: Union[str, Role]) -> bool:
        """
        Kullanıcıdan rol kaldırır
        
        Args:
            user_id: Kullanıcı ID'si
            role: Kaldırılacak rol
            
        Returns:
            bool: Başarılıysa True
        """
        role_str = role if isinstance(role, str) else role.value
        
        # Rolü kaldır
        delete_query = """
        DELETE FROM user_roles WHERE user_id = :user_id AND role = :role
        """
        result = await self.db.execute(delete_query, {"user_id": user_id, "role": role_str})
        
        return result.rowcount > 0
    
    async def grant_permission(self, user_id: str, permission: Union[str, Permission]) -> bool:
        """
        Kullanıcıya doğrudan izin verir
        
        Args:
            user_id: Kullanıcı ID'si
            permission: Verilecek izin
            
        Returns:
            bool: Başarılıysa True
        """
        perm_str = permission if isinstance(permission, str) else permission.value
        
        # İznin geçerli olup olmadığını kontrol et
        if not any(perm_str == p.value for p in Permission):
            raise ValueError(f"Invalid permission: {perm_str}")
        
        # Kullanıcının bu izne zaten sahip olup olmadığını kontrol et
        check_query = """
        SELECT 1 FROM user_permissions WHERE user_id = :user_id AND permission = :permission
        """
        check_result = await self.db.execute(check_query, {"user_id": user_id, "permission": perm_str})
        
        if check_result.scalar():
            return True  # Zaten bu izne sahip
        
        # İzni ekle
        insert_query = """
        INSERT INTO user_permissions (user_id, permission) VALUES (:user_id, :permission)
        """
        await self.db.execute(insert_query, {"user_id": user_id, "permission": perm_str})
        
        return True
    
    async def revoke_permission(self, user_id: str, permission: Union[str, Permission]) -> bool:
        """
        Kullanıcıdan doğrudan izin kaldırır
        
        Args:
            user_id: Kullanıcı ID'si
            permission: Kaldırılacak izin
            
        Returns:
            bool: Başarılıysa True
        """
        perm_str = permission if isinstance(permission, str) else permission.value
        
        # İzni kaldır
        delete_query = """
        DELETE FROM user_permissions WHERE user_id = :user_id AND permission = :permission
        """
        result = await self.db.execute(delete_query, {"user_id": user_id, "permission": perm_str})
        
        return result.rowcount > 0
    
    async def grant_resource_permission(
        self, 
        user_id: str, 
        resource_type: str, 
        resource_id: str, 
        permission_type: str
    ) -> bool:
        """
        Kullanıcıya kaynak bazlı izin verir
        
        Args:
            user_id: Kullanıcı ID'si
            resource_type: Kaynak türü ('document', 'collection')
            resource_id: Kaynak ID'si
            permission_type: İzin türü ('read', 'write', 'admin')
            
        Returns:
            bool: Başarılıysa True
        """
        if resource_type == "document":
            # Doküman izni
            return await self._grant_document_permission(user_id, resource_id, permission_type)
        elif resource_type == "collection":
            # Koleksiyon izni
            return await self._grant_collection_permission(user_id, resource_id, permission_type)
        else:
            raise ValueError(f"Unsupported resource type: {resource_type}")
    
    async def _grant_document_permission(self, user_id: str, document_id: str, permission_type: str) -> bool:
        """
        Doküman izni verir
        
        Args:
            user_id: Kullanıcı ID'si
            document_id: Doküman ID'si
            permission_type: İzin türü ('read', 'write', 'admin')
            
        Returns:
            bool: Başarılıysa True
        """
        # İzin türünü kontrol et
        if permission_type not in ["read", "write", "admin"]:
            raise ValueError(f"Invalid permission type: {permission_type}")
        
        # Mevcut izni kontrol et
        check_query = """
        SELECT permission_type FROM user_document_permissions 
        WHERE user_id = :user_id AND document_id = :document_id
        """
        check_result = await self.db.execute(check_query, 
                                             {"user_id": user_id, "document_id": document_id})
        
        existing_perm = check_result.scalar()
        
        if existing_perm:
            # İzni güncelle
            update_query = """
            UPDATE user_document_permissions SET permission_type = :permission_type
            WHERE user_id = :user_id AND document_id = :document_id
            """
            await self.db.execute(update_query, 
                                 {"user_id": user_id, "document_id": document_id, "permission_type": permission_type})
        else:
            # Yeni izin ekle
            insert_query = """
            INSERT INTO user_document_permissions (user_id, document_id, permission_type)
            VALUES (:user_id, :document_id, :permission_type)
            """
            await self.db.execute(insert_query, 
                                 {"user_id": user_id, "document_id": document_id, "permission_type": permission_type})
        
        return True
    
    async def _grant_collection_permission(self, user_id: str, collection_id: str, permission_type: str) -> bool:
        """
        Koleksiyon izni verir
        
        Args:
            user_id: Kullanıcı ID'si
            collection_id: Koleksiyon ID'si
            permission_type: İzin türü ('read', 'write', 'admin')
            
        Returns:
            bool: Başarılıysa True
        """
        # İzin türünü kontrol et
        if permission_type not in ["read", "write", "admin"]:
            raise ValueError(f"Invalid permission type: {permission_type}")
        
        # Mevcut izni kontrol et
        check_query = """
        SELECT permission_type FROM user_collection_permissions 
        WHERE user_id = :user_id AND collection_id = :collection_id
        """
        check_result = await self.db.execute(check_query, 
                                            {"user_id": user_id, "collection_id": collection_id})
        
        existing_perm = check_result.scalar()
        
        if existing_perm:
            # İzni güncelle
            update_query = """
            UPDATE user_collection_permissions SET permission_type = :permission_type
            WHERE user_id = :user_id AND collection_id = :collection_id
            """
            await self.db.execute(update_query, 
                                {"user_id": user_id, "collection_id": collection_id, "permission_type": permission_type})
        else:
            # Yeni izin ekle
            insert_query = """
            INSERT INTO user_collection_permissions (user_id, collection_id, permission_type)
            VALUES (:user_id, :collection_id, :permission_type)
            """
            await self.db.execute(insert_query, 
                                {"user_id": user_id, "collection_id": collection_id, "permission_type": permission_type})
        
        return True


# FastAPI izin kontrolü için dependency'ler
async def get_permission_set(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> PermissionSet:
    """
    Mevcut kullanıcı için izin kümesi alır
    
    Args:
        db: Veritabanı oturumu
        current_user: Mevcut kullanıcı
        
    Returns:
        PermissionSet: Kullanıcı izin kümesi
    """
    user_id = current_user["id"]
    rbac_service = RBACService(db)
    return await rbac_service.get_user_permissions(user_id)

def require_permission(permission: Union[str, Permission]):
    """
    Belirli bir izin gerektiren dependency
    
    Args:
        permission: Gereken izin
    """
    async def permission_dependency(
        permission_set: PermissionSet = Depends(get_permission_set)
    ):
        if not permission_set.can(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
    
    return permission_dependency

def require_resource_permission(
    resource_type: str,
    permission: Union[str, Permission],
    resource_id_param: str = "id"
):
    """
    Belirli bir kaynağa erişim izni gerektiren dependency
    
    Args:
        resource_type: Kaynak türü ('document', 'collection')
        permission: Gereken izin
        resource_id_param: Path parametresi adı
    """
    async def resource_permission_dependency(
        permission_set: PermissionSet = Depends(get_permission_set),
        resource_id: str = Depends(lambda: None)  # Path parametresinden alınacak
    ):
        if not resource_id:
            raise ValueError("Resource ID not provided")
            
        if not permission_set.can_access_resource(resource_type, resource_id, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions to access {resource_type} {resource_id}"
            )
    
    return resource_permission_dependency

# Rol gerektiren dependency
def require_role(role: Union[str, Role]):
    """
    Belirli bir rol gerektiren dependency
    
    Args:
        role: Gereken rol
    """
    role_str = role if isinstance(role, str) else role.value
    
    async def role_dependency(
        permission_set: PermissionSet = Depends(get_permission_set)
    ):
        if role_str not in permission_set.roles and Role.ADMIN.value not in permission_set.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {role_str} required"
            )
    
    return role_dependency