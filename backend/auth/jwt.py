# Last reviewed: 2025-04-30 05:36:04 UTC (User: TeeksssJWT)
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
import os
import secrets
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request, Cookie
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import uuid

from ..db.session import get_db
from ..models.user import User, RefreshToken
from ..core.config import settings
from ..core.exceptions import AuthenticationError, ErrorCode

# Şifre karma için bcrypt kullanımı
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 şema
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/token"
)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Düz metin şifreyi hash'lenmiş şifreyle karşılaştırır
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Şifreyi güvenli bir şekilde hash'ler
    """
    return pwd_context.hash(password)

def create_access_token(
    subject: Union[str, Dict[str, Any]], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    JWT erişim tokenı oluşturur
    
    Args:
        subject: Token konusu (kullanıcı kimliği veya token verileri)
        expires_delta: Token geçerlilik süresi
        
    Returns:
        str: JWT token
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    # Token verisini hazırla
    if isinstance(subject, dict):
        payload = subject.copy()
        if "sub" not in payload:
            raise ValueError("Token subject must include 'sub' key")
        if "exp" not in payload:
            payload["exp"] = expire
    else:
        payload = {"sub": subject, "exp": expire}
        
    # Ek token güvenlik önlemleri
    payload.update({
        "iat": datetime.now(timezone.utc),  # Token oluşturma zamanı
        "jti": str(uuid.uuid4())  # Benzersiz token ID (JWT ID)
    })
    
    # JWT token oluştur
    encoded_jwt = jwt.encode(
        payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt

def create_refresh_token() -> str:
    """
    Güvenli bir refresh token oluşturur
    
    Returns:
        str: Refresh token
    """
    return secrets.token_urlsafe(64)

async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> Optional[User]:
    """
    Kullanıcı kimliğini doğrular
    
    Args:
        db: Veritabanı oturumu
        email: Kullanıcı e-posta adresi
        password: Kullanıcı şifresi
        
    Returns:
        Optional[User]: Doğrulanmış kullanıcı veya None
    """
    # Kullanıcıyı e-posta ile bul
    stmt = select(User).filter(User.email == email)
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    # Kullanıcı yoksa veya şifre hatalıysa
    if not user or not verify_password(password, user.password):
        # Başarısız giriş denemesini kaydet
        if user:
            user.failed_login_attempts += 1
            user.last_failed_login = datetime.now(timezone.utc)
            
            # Hesap kilitleme kontrolü (5 başarısız deneme)
            if user.failed_login_attempts >= 5:
                # 30 dakika kilitle
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
            
            await db.commit()
        
        return None
    
    # Hesap kilitli mi kontrol et
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        return None
    
    # Başarılı giriş ise sayaçları sıfırla
    user.failed_login_attempts = 0
    user.last_failed_login = None
    user.locked_until = None
    user.last_login = datetime.now(timezone.utc)
    user.login_count += 1
    
    await db.commit()
    
    return user

async def save_refresh_token(
    db: AsyncSession, 
    user_id: str, 
    refresh_token: str,
    expires_at: datetime,
    request: Optional[Request] = None
) -> RefreshToken:
    """
    Refresh token'ı veritabanına kaydeder
    
    Args:
        db: Veritabanı oturumu
        user_id: Kullanıcı kimliği
        refresh_token: Refresh token
        expires_at: Sona erme tarihi
        request: İstek nesnesi (isteğe bağlı)
        
    Returns:
        RefreshToken: Kaydedilen refresh token
    """
    # İstek nesnesinden cihaz bilgilerine eriş
    device_info = None
    ip_address = None
    
    if request:
        # IP adresi
        if "x-forwarded-for" in request.headers:
            ip_address = request.headers["x-forwarded-for"].split(",")[0].strip()
        elif request.client:
            ip_address = request.client.host
            
        # Kullanıcı aracısı
        user_agent = request.headers.get("user-agent")
        
        device_info = {
            "user_agent": user_agent
        }
    
    # RefreshToken nesnesini oluştur
    db_refresh_token = RefreshToken(
        token=refresh_token,
        expires_at=expires_at,
        user_id=user_id,
        device_info=device_info,
        ip_address=ip_address
    )
    
    db.add(db_refresh_token)
    await db.commit()
    await db.refresh(db_refresh_token)
    
    return db_refresh_token

async def revoke_refresh_token(
    db: AsyncSession, refresh_token: str
) -> bool:
    """
    Refresh token'ı iptal eder
    
    Args:
        db: Veritabanı oturumu
        refresh_token: İptal edilecek refresh token
        
    Returns:
        bool: İşlem başarılı ise True
    """
    # Token'ı bul
    stmt = select(RefreshToken).filter(RefreshToken.token == refresh_token)
    result = await db.execute(stmt)
    db_token = result.scalars().first()
    
    if not db_token:
        return False
    
    # Token'ı iptal et
    db_token.revoked = True
    await db.commit()
    
    return True

async def revoke_all_user_tokens(
    db: AsyncSession, user_id: str
) -> int:
    """
    Kullanıcının tüm refresh token'larını iptal eder
    
    Args:
        db: Veritabanı oturumu
        user_id: Kullanıcı kimliği
        
    Returns:
        int: İptal edilen token sayısı
    """
    # Kullanıcının tüm token'larını al
    stmt = select(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked == False
    )
    result = await db.execute(stmt)
    tokens = result.scalars().all()
    
    # Tüm token'ları iptal et
    count = 0
    for token in tokens:
        token.revoked = True
        count += 1
    
    await db.commit()
    
    return count

async def use_refresh_token(
    db: AsyncSession, refresh_token: str
) -> Optional[User]:
    """
    Refresh token kullanarak kullanıcıyı döndürür
    
    Args:
        db: Veritabanı oturumu
        refresh_token: Refresh token
        
    Returns:
        Optional[User]: Kullanıcı veya None
    """
    # Token'ı bul
    stmt = select(RefreshToken).filter(
        RefreshToken.token == refresh_token,
        RefreshToken.revoked == False,
        RefreshToken.expires_at > datetime.now(timezone.utc)
    ).join(User)
    result = await db.execute(stmt)
    db_token = result.scalars().first()
    
    if not db_token:
        return None
    
    # Kullanıcıyı al
    user = db_token.user
    
    # Kullanıcı aktif mi kontrol et
    if not user or not user.is_active:
        return None
    
    return user

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> Dict[str, Any]:
    """
    Geçerli JWT token'dan kullanıcı bilgilerini alır
    
    Args:
        db: Veritabanı oturumu
        token: JWT token
        
    Returns:
        Dict[str, Any]: Kullanıcı bilgileri
    
    Raises:
        AuthenticationError: Kimlik doğrulama başarısız olduğunda
    """
    try:
        # Token'ı doğrula
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Token süresi dolmuş mu kontrol et
        if "exp" in payload and datetime.fromtimestamp(payload["exp"], timezone.utc) < datetime.now(timezone.utc):
            raise AuthenticationError(
                message="Token has expired",
                error_code=ErrorCode.EXPIRED_TOKEN
            )
        
        # Kullanıcı kimliğini al
        user_id: str = payload.get("sub")
        if user_id is None:
            raise AuthenticationError(
                message="Invalid authentication credentials",
                error_code=ErrorCode.INVALID_TOKEN
            )
        
        # Rol bilgilerini al
        roles = payload.get("roles", [])
        is_superuser = payload.get("is_superuser", False)
        
        # Kullanıcı aktif mi kontrol et
        stmt = select(User).filter(User.id == user_id, User.is_active == True)
        result = await db.execute(stmt)
        user = result.scalars().first()
        
        if not user:
            raise AuthenticationError(
                message="User not found or inactive",
                error_code=ErrorCode.ACCOUNT_DISABLED
            )
        
        # Kullanıcı bilgilerini döndür
        return {
            "id": user_id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_superuser": is_superuser,
            "roles": roles,
            "organization_id": str(user.organization_id) if user.organization_id else None
        }
        
    except JWTError:
        raise AuthenticationError(
            message="Could not validate credentials",
            error_code=ErrorCode.INVALID_TOKEN
        )

async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Geçerli kullanıcının aktif olduğunu kontrol eder
    
    Args:
        current_user: Geçerli kullanıcı
        
    Returns:
        Dict[str, Any]: Kullanıcı bilgileri
    
    Raises:
        HTTPException: Kullanıcı aktif değilse
    """
    if not current_user.get("is_active"):
        raise AuthenticationError(
            message="Inactive user",
            error_code=ErrorCode.ACCOUNT_DISABLED
        )
    return current_user

def get_token_from_cookie_or_header(
    request: Request,
    refresh_token: Optional[str] = Cookie(None, alias="refresh_token")
) -> Optional[str]:
    """
    İstek cookie veya Authorization header'dan refresh token alır
    
    Args:
        request: İstek nesnesi
        refresh_token: Cookie'den gelen refresh token
        
    Returns:
        Optional[str]: Refresh token
    """
    # Önce cookie'den al
    if refresh_token:
        return refresh_token
    
    # Cookie yoksa Authorization header'dan al
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.replace("Bearer ", "")
    
    return None