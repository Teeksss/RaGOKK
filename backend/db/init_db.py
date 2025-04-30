# Last reviewed: 2025-04-30 05:43:44 UTC (User: Teeksss)
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .session import engine, Base, get_db
from ..models.user import User
from ..models.role_permission import Role, Permission
from ..core.config import settings
from ..auth.jwt import get_password_hash

logger = logging.getLogger(__name__)

async def init_db() -> None:
    """
    Veritabanı şemasını ve başlangıç verilerini oluşturur
    """
    async with engine.begin() as conn:
        # Tabloları oluştur (eğer yoksa)
        # await conn.run_sync(Base.metadata.drop_all)  # Geliştirme aşamasında tabloları silmek için
        await conn.run_sync(Base.metadata.create_all)
    
    # Seed verileri ekle
    async for db in get_db():
        await create_initial_data(db)

async def create_initial_data(db: AsyncSession) -> None:
    """
    Başlangıç verilerini oluşturur (roller, izinler, süper kullanıcı)
    """
    # Temel izinleri oluştur
    await create_permissions(db)
    
    # Temel rolleri oluştur
    await create_roles(db)
    
    # Süper kullanıcı oluştur
    await create_superuser(db)

async def create_permissions(db: AsyncSession) -> None:
    """
    Temel izinleri oluşturur
    """
    # İzinleri tanımla
    permissions_data = [
        # Belge izinleri
        {
            "name": "Create Document",
            "code": "document:create",
            "description": "Create new documents",
            "category": "document",
            "resource_type": "document",
            "action": "create"
        },
        {
            "name": "Read Document",
            "code": "document:read",
            "description": "Read documents",
            "category": "document",
            "resource_type": "document",
            "action": "read"
        },
        {
            "name": "Update Document",
            "code": "document:update",
            "description": "Update documents",
            "category": "document",
            "resource_type": "document",
            "action": "update"
        },
        {
            "name": "Delete Document",
            "code": "document:delete",
            "description": "Delete documents",
            "category": "document",
            "resource_type": "document",
            "action": "delete"
        },
        {
            "name": "List Documents",
            "code": "document:list",
            "description": "List documents",
            "category": "document",
            "resource_type": "document",
            "action": "list"
        },
        
        # Prompt izinleri
        {
            "name": "Create Prompt Template",
            "code": "prompt:create",
            "description": "Create prompt templates",
            "category": "prompt",
            "resource_type": "prompt_template",
            "action": "create"
        },
        {
            "name": "Read Prompt Template",
            "code": "prompt:read",
            "description": "Read prompt templates",
            "category": "prompt",
            "resource_type": "prompt_template",
            "action": "read"
        },
        {
            "name": "Update Prompt Template",
            "code": "prompt:update",
            "description": "Update prompt templates",
            "category": "prompt",
            "resource_type": "prompt_template",
            "action": "update"
        },
        {
            "name": "Delete Prompt Template",
            "code": "prompt:delete",
            "description": "Delete prompt templates",
            "category": "prompt",
            "resource_type": "prompt_template",
            "action": "delete"
        },
        {
            "name": "List Prompt Templates",
            "code": "prompt:list",
            "description": "List prompt templates",
            "category": "prompt",
            "resource_type": "prompt_template",
            "action": "list"
        },
        
        # Sorgu izinleri
        {
            "name": "Create Query",
            "code": "query:create",
            "description": "Create queries",
            "category": "query",
            "resource_type": "query",
            "action": "create"
        },
        {
            "name": "Read Query",
            "code": "query:read",
            "description": "Read queries",
            "category": "query",
            "resource_type": "query",
            "action": "read"
        },
        {
            "name": "Delete Query",
            "code": "query:delete",
            "description": "Delete queries",
            "category": "query",
            "resource_type": "query",
            "action": "delete"
        },
        {
            "name": "List Queries",
            "code": "query:list",
            "description": "List queries",
            "category": "query",
            "resource_type": "query",
            "action": "list"
        },
        
        # Analitik izinleri
        {
            "name": "Read User Analytics",
            "code": "analytics:read:user",
            "description": "View user analytics",
            "category": "analytics",
            "resource_type": "analytics",
            "action": "read"
        },
        {
            "name": "Read Document Analytics",
            "code": "analytics:read:document",
            "description": "View document analytics",
            "category": "analytics",
            "resource_type": "analytics",
            "action": "read"
        },
        {
            "name": "Read Query Analytics",
            "code": "analytics:read:query",
            "description": "View query analytics",
            "category": "analytics",
            "resource_type": "analytics",
            "action": "read"
        },
        {
            "name": "Read System Analytics",
            "code": "analytics:read:system",
            "description": "View system analytics",
            "category": "analytics",
            "resource_type": "analytics",
            "action": "read"
        },
        {
            "name": "Export Analytics",
            "code": "analytics:export",
            "description": "Export analytics data",
            "category": "analytics",
            "resource_type": "analytics",
            "action": "export"
        },
        
        # Kullanıcı yönetimi izinleri
        {
            "name": "Create User",
            "code": "user:create",
            "description": "Create users",
            "category": "user",
            "resource_type": "user",
            "action": "create"
        },
        {
            "name": "Read User",
            "code": "user:read",
            "description": "Read user details",
            "category": "user",
            "resource_type": "user",
            "action": "read"
        },
        {
            "name": "Update User",
            "code": "user:update",
            "description": "Update users",
            "category": "user",
            "resource_type": "user",
            "action": "update"
        },
        {
            "name": "Delete User",
            "code": "user:delete",
            "description": "Delete users",
            "category": "user",
            "resource_type": "user",
            "action": "delete"
        },
        {
            "name": "List Users",
            "code": "user:list",
            "description": "List users",
            "category": "user",
            "resource_type": "user",
            "action": "list"
        },
        
        # Rol yönetimi izinleri
        {
            "name": "Create Role",
            "code": "role:create",
            "description": "Create roles",
            "category": "role",
            "resource_type": "role",
            "action": "create"
        },
        {
            "name": "Read Role",
            "code": "role:read",
            "description": "Read role details",
            "category": "role",
            "resource_type": "role",
            "action": "read"
        },
        {
            "name": "Update Role",
            "code": "role:update",
            "description": "Update roles",
            "category": "role",
            "resource_type": "role",
            "action": "update"
        },
        {
            "name": "Delete Role",
            "code": "role:delete",
            "description": "Delete roles",
            "category": "role",
            "resource_type": "role",
            "action": "delete"
        },
        {
            "name": "List Roles",
            "code": "role:list",
            "description": "List roles",
            "category": "role",
            "resource_type": "role",
            "action": "list"
        },
        {
            "name": "List Permissions",
            "code": "permission:list",
            "description": "List permissions",
            "category": "role",
            "resource_type": "permission",
            "action": "list"
        }
    ]

    # İzinler mevcut mu kontrol et
    for permission_data in permissions_data:
        stmt = select(Permission).filter(Permission.code == permission_data["code"])
        result = await db.execute(stmt)
        permission = result.scalars().first()
        
        # İzin yoksa oluştur
        if not permission:
            permission = Permission(**permission_data)
            db.add(permission)
    
    await db.commit()
    logger.info("Base permissions created")

async def create_roles(db: AsyncSession) -> None:
    """
    Temel rolleri oluşturur
    """
    # Rolleri tanımla
    roles_data = [
        {
            "name": "Admin",
            "code": "admin",
            "description": "Administrator with full access",
            "is_system": True
        },
        {
            "name": "User",
            "code": "user",
            "description": "Standard user",
            "is_system": True
        },
        {
            "name": "Analyst",
            "code": "analyst",
            "description": "Analytics and reporting user",
            "is_system": True
        },
        {
            "name": "Read-only",
            "code": "readonly",
            "description": "Read-only access",
            "is_system": True
        }
    ]
    
    # İzinleri al
    stmt = select(Permission)
    result = await db.execute(stmt)
    all_permissions = result.scalars().all()
    
    # İzin kodlarına göre gruplama
    permissions_by_code = {p.code: p for p in all_permissions}
    
    # Rol-izin eşleştirmeleri
    role_permissions = {
        "admin": [p.code for p in all_permissions],  # Tüm izinler
        "user": [
            # Temel kullanıcı izinleri
            "document:create", "document:read", "document:update", "document:delete", "document:list",
            "prompt:read", "prompt:list",
            "query:create", "query:read", "query:list", "query:delete"
        ],
        "analyst": [
            # Analitik ve raporlama izinleri
            "document:read", "document:list",
            "query:read", "query:list",
            "analytics:read:user", "analytics:read:document", "analytics:read:query", 
            "analytics:read:system", "analytics:export"
        ],
        "readonly": [
            # Salt okunur izinler
            "document:read", "document:list",
            "prompt:read", "prompt:list",
            "query:read", "query:list"
        ]
    }
    
    # Rolleri oluştur ve izinleri ata
    for role_data in roles_data:
        role_code = role_data["code"]
        
        # Rol mevcut mu kontrol et
        stmt = select(Role).filter(Role.code == role_code)
        result = await db.execute(stmt)
        role = result.scalars().first()
        
        # Rol yoksa oluştur
        if not role:
            role = Role(**role_data)
            db.add(role)
            await db.flush()  # Role ID almak için flush
        
        # Roleün izinlerini ata
        if role_code in role_permissions:
            # Önce mevcut izinleri temizle
            role.permissions = []
            
            # Yeni izinleri ekle
            for permission_code in role_permissions[role_code]:
                if permission_code in permissions_by_code:
                    role.permissions.append(permissions_by_code[permission_code])
    
    await db.commit()
    logger.info("Base roles and permissions created")

async def create_superuser(db: AsyncSession) -> None:
    """
    Süper kullanıcı oluşturur (eğer yoksa)
    """
    # Süper kullanıcı mevcut mu kontrol et
    stmt = select(User).filter(User.email == settings.FIRST_SUPERUSER_EMAIL)
    result = await db.execute(stmt)
    superuser = result.scalars().first()
    
    if not superuser:
        # Admin rolünü al
        stmt = select(Role).filter(Role.code == "admin")
        result = await db.execute(stmt)
        admin_role = result.scalars().first()
        
        if not admin_role:
            logger.warning("Admin role not found, superuser creation skipped")
            return
        
        # Süper kullanıcı oluştur
        hashed_password = get_password_hash(settings.FIRST_SUPERUSER_PASSWORD)
        superuser = User(
            email=settings.FIRST_SUPERUSER_EMAIL,
            username="admin",
            password=hashed_password,
            full_name="System Administrator",
            is_active=True,
            is_verified=True,
            is_superuser=True
        )
        
        # Admin rolünü ata
        superuser.roles.append(admin_role)
        
        db.add(superuser)
        await db.commit()
        
        logger.info(f"Superuser created: {settings.FIRST_SUPERUSER_EMAIL}")
    else:
        logger.info(f"Superuser already exists: {settings.FIRST_SUPERUSER_EMAIL}")