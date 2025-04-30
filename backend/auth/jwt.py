# Last reviewed: 2025-04-29 14:12:11 UTC (User: TeeksssKullanıcı)
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import uuid

from ..config import settings
from ..repositories.user_repository import UserRepository
from ..db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

# JWT ayarları
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

# OAuth2 şeması
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def create_access_token(data: Dict[str, Any]) -> str:
    """
    Access token oluşturur
    
    Args:
        data: Token içinde saklanacak veriler
        
    Returns:
        str: JWT token
    """
    to_encode = data.copy()
    
    # Token geçerlilik süresi
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "jti": str(uuid.uuid4()), "token_type": "access"})
    
    # JWT oluştur
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Refresh token oluşturur
    
    Args:
        data: Token içinde saklanacak veriler
        
    Returns:
        str: JWT token
    """
    to_encode = data.copy()
    
    # Token geçerlilik süresi
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "jti": str(uuid.uuid4()), "token_type": "refresh"})
    
    # JWT oluştur
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Dict[str, Any]:
    """
    JWT token'ı çözer
    
    Args:
        token: JWT token
        
    Returns:
        Dict[str, Any]: Token payload
    """
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Geçerli token'dan mevcut kullanıcıyı alır
    
    Args:
        token: JWT token
        db: Veritabanı oturumu
        
    Returns:
        Dict[str, Any]: Kullanıcı bilgileri
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Token'ı çöz
        payload = decode_token(token)
        
        # Token tipini kontrol et
        token_type = payload.get("token_type")
        if token_type != "access":
            raise credentials_exception
        
        # Kullanıcı bilgilerini al
        email: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        
        if not email or not user_id:
            raise credentials_exception
        
    except JWTError:
        raise credentials_exception
    
    # Kullanıcıyı veritabanından doğrula
    user_repo = UserRepository()
    user = await user_repo.get_user_by_email(db, email)
    
    if not user or str(user.id) != user_id:
        raise credentials_exception
    
    return {
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "organization_id": str(user.organization_id) if user.organization_id else None
    }

async def get_current_active_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Kullanıcının aktif olduğunu doğrular
    
    Args:
        current_user: Mevcut kullanıcı bilgileri
        
    Returns:
        Dict[str, Any]: Aktif kullanıcı bilgileri
    """
    if not current_user["is_active"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user

async def get_current_superuser(current_user: Dict[str, Any] = Depends(get_current_active_user)) -> Dict[str, Any]:
    """
    Kullanıcının admin olduğunu doğrular
    
    Args:
        current_user: Mevcut kullanıcı bilgileri
        
    Returns:
        Dict[str, Any]: Admin kullanıcı bilgileri
    """
    if not current_user["is_superuser"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not enough permissions"
        )
    return current_user

async def get_current_user_optional(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> Optional[Dict[str, Any]]:
    """
    Geçerli token'dan mevcut kullanıcıyı alır (opsiyonel)
    
    Args:
        token: JWT token
        db: Veritabanı oturumu
        
    Returns:
        Optional[Dict[str, Any]]: Kullanıcı bilgileri veya None
    """
    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None