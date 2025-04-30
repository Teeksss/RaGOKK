# Last reviewed: 2025-04-30 05:36:04 UTC (User: TeeksssJWT)
from fastapi import APIRouter, Depends, HTTPException, status, Body, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
import logging

from ...db.session import get_db
from ...schemas.user import UserCreate, UserResponse, TokenResponse, RefreshTokenRequest
from ...services.user_service import UserService
from ...auth.jwt import (
    authenticate_user, create_access_token, create_refresh_token,
    save_refresh_token, revoke_refresh_token, get_current_active_user,
    use_refresh_token, get_token_from_cookie_or_header
)
from ...core.config import settings
from ...services.audit_service import AuditService, AuditLogType
from ...core.exceptions import AuthenticationError, ErrorCode

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)
audit_service = AuditService()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Yeni bir kullanıcı kaydı oluşturur
    """
    user_service = UserService(db)
    
    try:
        # Kullanıcı kayıt bilgilerini kontrol et
        await user_service.validate_registration_data(user_in)
        
        # Kullanıcıyı oluştur
        user = await user_service.create_user(user_in)
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.USER,
            user_id=str(user.id),
            action="register",
            resource_type="user",
            resource_id=str(user.id),
            status="success",
            db=db
        )
        
        return user
    except Exception as e:
        # Audit log kaydı - başarısız
        await audit_service.log_event(
            event_type=AuditLogType.USER,
            user_id=None,
            action="register",
            resource_type="user",
            status="failure",
            details={"error": str(e), "email": user_in.email},
            db=db
        )
        raise

@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    response: Response,
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth2 uyumlu JWT token oluşturur
    
    - **username**: Email adresi (form-data)
    - **password**: Şifre (form-data)
    """
    # Kullanıcıyı doğrula
    user = await authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        # Audit log kaydı - başarısız giriş
        await audit_service.log_event(
            event_type=AuditLogType.AUTH,
            user_id=None,
            action="login",
            status="failure",
            details={"email": form_data.username, "reason": "invalid_credentials"},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            db=db
        )
        
        raise AuthenticationError(
            message="Incorrect email or password",
            error_code=ErrorCode.INVALID_CREDENTIALS
        )
    
    # Kullanıcı rollerini al
    user_roles = [role.code for role in user.roles]
    
    # Access token oluştur
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token_data = {
        "sub": str(user.id),
        "roles": user_roles,
        "is_superuser": user.is_superuser
    }
    access_token = create_access_token(
        subject=access_token_data,
        expires_delta=access_token_expires
    )
    
    # Refresh token oluştur
    refresh_token = create_refresh_token()
    refresh_token_expires = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    # Refresh token'ı veritabanına kaydet
    await save_refresh_token(
        db=db,
        user_id=str(user.id),
        refresh_token=refresh_token,
        expires_at=refresh_token_expires,
        request=request
    )
    
    # Refresh token'ı güvenli bir çerez olarak ayarla
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,  # HTTPS üzerinde True olmalı
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/v1/auth/refresh"  # Sadece refresh endpoint için gönder
    )
    
    # Audit log kaydı - başarılı giriş
    await audit_service.log_event(
        event_type=AuditLogType.AUTH,
        user_id=str(user.id),
        action="login",
        status="success",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        db=db
    )
    
    # Token ve kullanıcı bilgilerini döndür
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "is_superuser": user.is_superuser,
            "roles": user_roles,
            "organization_id": str(user.organization_id) if user.organization_id else None
        }
    }

@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token: str = Depends(get_token_from_cookie_or_header)
):
    """
    Refresh token kullanarak yeni bir access token oluşturur
    
    Refresh token header (Bearer) veya cookie olarak gönderilebilir
    """
    if not refresh_token:
        raise AuthenticationError(
            message="Refresh token is missing",
            error_code=ErrorCode.INVALID_TOKEN
        )
    
    # Refresh token ile kullanıcıyı bul
    user = await use_refresh_token(db, refresh_token)
    
    if not user:
        # Audit log kaydı - geçersiz refresh token
        await audit_service.log_event(
            event_type=AuditLogType.AUTH,
            user_id=None,
            action="refresh_token",
            status="failure",
            details={"reason": "invalid_refresh_token"},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            db=db
        )
        
        # Geçersiz token çerezini temizle
        response.delete_cookie(key="refresh_token", path="/api/v1/auth/refresh")
        
        raise AuthenticationError(
            message="Invalid or expired refresh token",
            error_code=ErrorCode.INVALID_TOKEN
        )
    
    # Kullanıcı rollerini al
    user_roles = [role.code for role in user.roles]
    
    # Yeni access token oluştur
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token_data = {
        "sub": str(user.id),
        "roles": user_roles,
        "is_superuser": user.is_superuser
    }
    access_token = create_access_token(
        subject=access_token_data,
        expires_delta=access_token_expires
    )
    
    # Yeni refresh token oluştur (token rotasyonu)
    new_refresh_token = create_refresh_token()
    refresh_token_expires = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    # Eski token'ı iptal et
    await revoke_refresh_token(db, refresh_token)
    
    # Yeni refresh token'ı veritabanına kaydet
    await save_refresh_token(
        db=db,
        user_id=str(user.id),
        refresh_token=new_refresh_token,
        expires_at=refresh_token_expires,
        request=request
    )
    
    # Yeni refresh token'ı çerez olarak ayarla
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/v1/auth/refresh"
    )
    
    # Audit log kaydı - başarılı token yenileme
    await audit_service.log_event(
        event_type=AuditLogType.AUTH,
        user_id=str(user.id),
        action="refresh_token",
        status="success",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        db=db
    )
    
    # Token ve kullanıcı bilgilerini döndür
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "is_superuser": user.is_superuser,
            "roles": user_roles,
            "organization_id": str(user.organization_id) if user.organization_id else None
        }
    }

@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    refresh_token: Optional[str] = Depends(get_token_from_cookie_or_header),
    db: AsyncSession = Depends(get_db),
    revoke_all: bool = Body(False)
):
    """
    Kullanıcı oturumunu sonlandırır
    
    - Mevcut refresh token iptal edilir
    - revoke_all=True ise, kullanıcının tüm cihazlarda/tarayıcılarda oturumu sonlandırılır
    """
    try:
        # Belirli bir refresh token iptal edilecekse
        if refresh_token:
            await revoke_refresh_token(db, refresh_token)
        
        # Tüm token'lar iptal edilecekse
        if revoke_all:
            await revoke_all_user_tokens(db, current_user["id"])
        
        # Refresh token çerezini temizle
        response.delete_cookie(key="refresh_token", path="/api/v1/auth/refresh")
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.AUTH,
            user_id=current_user["id"],
            action="logout",
            status="success",
            details={"revoke_all": revoke_all},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            db=db
        )
        
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        
        # Audit log kaydı - başarısız çıkış
        await audit_service.log_event(
            event_type=AuditLogType.AUTH,
            user_id=current_user["id"],
            action="logout",
            status="failure",
            details={"error": str(e)},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            db=db
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during logout: {str(e)}"
        )

@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mevcut kimliği doğrulanmış kullanıcının bilgilerini döndürür
    """
    user_service = UserService(db)
    user = await user_service.get_user_by_id(current_user["id"])
    
    # Kullanıcı bulunamazsa (nadiren olsa da önlem amaçlı)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Kullanıcı rollerini ekle
    user_data = user.to_dict()
    user_data["roles"] = [role.code for role in user.roles]
    
    return user_data