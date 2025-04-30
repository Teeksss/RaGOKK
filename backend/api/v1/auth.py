# Last reviewed: 2025-04-29 14:12:11 UTC (User: TeeksssKullanıcı)
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime, timedelta

from ...db.session import get_db
from ...schemas.user import UserCreate, User, TokenResponse, UserUpdate, UserPasswordUpdate
from ...repositories.user_repository import UserRepository
from ...auth.jwt import create_access_token, create_refresh_token, decode_token, get_current_active_user
from ...auth.password import verify_password, get_password_hash
from ...services.audit_service import AuditService, AuditLogType

router = APIRouter(
    prefix="/api/auth",
    tags=["authentication"],
    responses={401: {"description": "Unauthorized"}}
)

logger = logging.getLogger(__name__)
audit_service = AuditService()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

@router.post("/register", response_model=User)
async def register(
    user: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Yeni bir kullanıcı kaydeder
    
    - **email**: E-posta adresi
    - **password**: Şifre
    - **username**: Kullanıcı adı
    - **full_name**: Tam ad
    """
    user_repo = UserRepository()
    
    # E-posta veya kullanıcı adı mevcut mu kontrol et
    db_user = await user_repo.get_user_by_email(db, user.email)
    if db_user:
        await audit_service.log_event(
            event_type=AuditLogType.AUTH,
            action="register",
            status="failure",
            details={"reason": "Email already registered", "email": user.email},
            db=db
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    if user.username:
        db_user = await user_repo.get_user_by_username(db, user.username)
        if db_user:
            await audit_service.log_event(
                event_type=AuditLogType.AUTH,
                action="register",
                status="failure",
                details={"reason": "Username already exists", "username": user.username},
                db=db
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
    
    # Şifreyi hashle
    hashed_password = get_password_hash(user.password)
    
    # Kullanıcıyı oluştur
    db_user = await user_repo.create_user(
        db=db,
        email=user.email,
        password=hashed_password,
        username=user.username,
        full_name=user.full_name
    )
    
    await db.commit()
    await db.refresh(db_user)
    
    # Audit log kaydı
    await audit_service.log_event(
        event_type=AuditLogType.AUTH,
        user_id=str(db_user.id),
        action="register",
        resource_type="user",
        resource_id=str(db_user.id),
        status="success",
        db=db
    )
    
    return db_user

@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Kullanıcı adı ve şifre ile giriş yapar ve JWT token döndürür
    
    - **username**: E-posta adresi veya kullanıcı adı
    - **password**: Şifre
    
    Returns: JWT token ve kullanıcı bilgileri
    """
    user_repo = UserRepository()
    
    # E-posta veya kullanıcı adı ile kullanıcı bul
    user = await user_repo.get_user_by_email(db, form_data.username)
    if not user:
        user = await user_repo.get_user_by_username(db, form_data.username)
    
    # Hatalı kullanıcı adı/şifre kontrolü
    if not user or not verify_password(form_data.password, user.password):
        await audit_service.log_event(
            event_type=AuditLogType.AUTH,
            action="login",
            status="failure",
            details={"reason": "Invalid username or password", "username": form_data.username},
            db=db
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Kullanıcı aktif mi?
    if not user.is_active:
        await audit_service.log_event(
            event_type=AuditLogType.AUTH,
            user_id=str(user.id),
            action="login",
            resource_type="user",
            resource_id=str(user.id),
            status="failure",
            details={"reason": "User is inactive"},
            db=db
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Son giriş bilgisini güncelle
    user.last_login = datetime.now()
    await db.commit()
    
    # Token oluştur
    access_token = create_access_token(
        data={"sub": user.email, "user_id": str(user.id)}
    )
    
    refresh_token = create_refresh_token(
        data={"sub": user.email, "user_id": str(user.id)}
    )
    
    # Audit log kaydı
    await audit_service.log_event(
        event_type=AuditLogType.AUTH,
        user_id=str(user.id),
        action="login",
        resource_type="user",
        resource_id=str(user.id),
        status="success",
        db=db
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 3600,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "created_at": user.created_at,
            "organization_id": str(user.organization_id) if user.organization_id else None
        }
    }

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh token ile yeni bir access token oluşturur
    
    - **refresh_token**: Geçerli bir refresh token
    
    Returns: Yeni JWT token ve kullanıcı bilgileri
    """
    user_repo = UserRepository()
    
    try:
        # Token'ı doğrula
        payload = decode_token(refresh_token)
        email: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        
        if not email or not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token format",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Kullanıcıyı bul
        user = await user_repo.get_user_by_email(db, email)
        
        if not user or str(user.id) != user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User is inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Yeni tokenları oluştur
        access_token = create_access_token(
            data={"sub": user.email, "user_id": str(user.id)}
        )
        new_refresh_token = create_refresh_token(
            data={"sub": user.email, "user_id": str(user.id)}
        )
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.AUTH,
            user_id=str(user.id),
            action="refresh_token",
            resource_type="user",
            resource_id=str(user.id),
            status="success",
            db=db
        )
        
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": 3600,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
                "created_at": user.created_at,
                "organization_id": str(user.organization_id) if user.organization_id else None
            }
        }
    
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.AUTH,
            action="refresh_token",
            status="failure",
            details={"error": str(e)},
            db=db
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.post("/logout")
async def logout(
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Kullanıcı oturumunu sonlandırır
    
    Not: JWT token bazlı sistemlerde, token sunucuda iptal edilemez
    Bu endpoint yalnızca istemci tarafında token'ın silinmesi için kullanılır
    Ayrıca audit log kaydı oluşturur
    """
    # Audit log kaydı
    await audit_service.log_event(
        event_type=AuditLogType.AUTH,
        user_id=current_user["id"],
        action="logout",
        resource_type="user",
        resource_id=current_user["id"],
        status="success",
        db=db
    )
    
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mevcut oturum açmış kullanıcının bilgilerini döndürür
    """
    user_repo = UserRepository()
    user = await user_repo.get_user_by_id(db, current_user["id"])
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user

@router.put("/me", response_model=User)
async def update_user_info(
    user_update: UserUpdate,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mevcut kullanıcının bilgilerini günceller
    
    - **full_name**: Yeni tam ad
    - **username**: Yeni kullanıcı adı (opsiyonel)
    - **email**: Yeni e-posta (opsiyonel)
    """
    user_repo = UserRepository()
    
    # Kullanıcıyı bul
    user = await user_repo.get_user_by_id(db, current_user["id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # E-posta güncellenecekse, mevcut mu kontrol et
    if user_update.email and user_update.email != user.email:
        db_user = await user_repo.get_user_by_email(db, user_update.email)
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Kullanıcı adı güncellenecekse, mevcut mu kontrol et
    if user_update.username and user_update.username != user.username:
        db_user = await user_repo.get_user_by_username(db, user_update.username)
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
    
    # Kullanıcıyı güncelle
    updated_user = await user_repo.update_user(
        db=db,
        user_id=user.id,
        email=user_update.email,
        username=user_update.username,
        full_name=user_update.full_name
    )
    
    await db.commit()
    await db.refresh(updated_user)
    
    # Audit log kaydı
    await audit_service.log_event(
        event_type=AuditLogType.DATA,
        user_id=str(user.id),
        action="update",
        resource_type="user",
        resource_id=str(user.id),
        status="success",
        db=db
    )
    
    return updated_user

@router.put("/me/password")
async def change_password(
    password_update: UserPasswordUpdate,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mevcut kullanıcının şifresini günceller
    
    - **current_password**: Mevcut şifre
    - **new_password**: Yeni şifre
    """
    user_repo = UserRepository()
    
    # Kullanıcıyı bul
    user = await user_repo.get_user_by_id(db, current_user["id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Mevcut şifre doğru mu?
    if not verify_password(password_update.current_password, user.password):
        # Audit log kaydı - başarısız
        await audit_service.log_event(
            event_type=AuditLogType.AUTH,
            user_id=str(user.id),
            action="change_password",
            resource_type="user",
            resource_id=str(user.id),
            status="failure",
            details={"reason": "Incorrect current password"},
            db=db
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    # Şifreyi güncelle
    hashed_password = get_password_hash(password_update.new_password)
    user.password = hashed_password
    await db.commit()
    
    # Audit log kaydı - başarılı
    await audit_service.log_event(
        event_type=AuditLogType.AUTH,
        user_id=str(user.id),
        action="change_password",
        resource_type="user",
        resource_id=str(user.id),
        status="success",
        db=db
    )
    
    return {"message": "Password updated successfully"}