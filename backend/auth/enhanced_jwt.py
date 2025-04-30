# Last reviewed: 2025-04-30 07:34:44 UTC (User: Teeksss)
import os
from datetime import datetime, timedelta
import jwt
from typing import Dict, Any, Optional, List, Union
import uuid
import logging
from fastapi import Depends, HTTPException, status, Request, Response, Cookie
from fastapi.security import OAuth2PasswordBearer

# Redis depoya kayıt için
import redis
import json

logger = logging.getLogger(__name__)

# JWT Ayarları
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "supersecret_change_in_production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
TOKEN_BLACKLIST_ENABLED = os.getenv("TOKEN_BLACKLIST_ENABLED", "true").lower() == "true"

# Redis ayarları
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
try:
    redis_client = redis.Redis.from_url(REDIS_URL) if TOKEN_BLACKLIST_ENABLED else None
except:
    logger.warning("Redis connection failed, token blacklisting is disabled")
    redis_client = None

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

class EnhancedJWTHandler:
    """
    Gelişmiş JWT işleme ve güvenlik önlemleri sağlayan sınıf
    """

    @staticmethod
    def create_token(data: Dict[str, Any], expires_delta: timedelta, token_type: str = "access") -> Dict[str, str]:
        """
        JWT token oluşturur
        
        Args:
            data: Token payload verileri
            expires_delta: Geçerlilik süresi
            token_type: Token tipi (access/refresh)
            
        Returns:
            Dict[str, str]: Token bilgileri
        """
        # Kopya oluştur ve kimlik doğrulama verilerini koru
        payload = data.copy()
        
        # Token zamanlaması
        now = datetime.utcnow()
        expire = now + expires_delta
        
        # Standart JWT payload claims ekle
        payload.update({
            "exp": expire,
            "iat": now,
            "nbf": now,
            "jti": str(uuid.uuid4()),  # Benzersiz token ID (blacklist için)
            "type": token_type
        })
        
        # Token'ı daha güvenli şekilde kısıtla
        allowed_claims = [
            "sub", "id", "email", "roles", "permissions", 
            "organization_id", "exp", "iat", "nbf", "jti", "type"
        ]
        
        # Sadece izin verilen alanları tut
        filtered_payload = {k: v for k, v in payload.items() if k in allowed_claims}
        
        # Token oluştur
        token = jwt.encode(filtered_payload, SECRET_KEY, algorithm=ALGORITHM)
        
        return {
            "token": token,
            "token_type": token_type,
            "expires_at": expire.isoformat()
        }

    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> Dict[str, str]:
        """
        Access token oluşturur
        """
        if expires_delta is None:
            expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        return EnhancedJWTHandler.create_token(data, expires_delta, "access")

    @staticmethod
    def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> Dict[str, str]:
        """
        Refresh token oluşturur
        """
        if expires_delta is None:
            expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        return EnhancedJWTHandler.create_token(data, expires_delta, "refresh")

    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """
        Token çözümleme
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Blacklist kontrolü
            if TOKEN_BLACKLIST_ENABLED and redis_client and EnhancedJWTHandler.is_token_blacklisted(payload):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been invalidated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @staticmethod
    def is_token_blacklisted(payload: Dict[str, Any]) -> bool:
        """
        Token'ın blacklist'te olup olmadığını kontrol eder
        """
        if not redis_client:
            return False
            
        jti = payload.get("jti")
        if not jti:
            return False
            
        key = f"blacklist:token:{jti}"
        return redis_client.exists(key) == 1

    @staticmethod
    def blacklist_token(token: str) -> bool:
        """
        Token'ı geçersiz kılmak için blacklist'e ekler
        """
        if not redis_client:
            logger.warning("Redis not available, token could not be blacklisted")
            return False
            
        try:
            # Token'ı decode et
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # JTI'yı al
            jti = payload.get("jti")
            if not jti:
                return False
                
            # Blacklist'e ekle
            exp = payload.get("exp")
            if exp:
                # Token'ın orijinal sona erme tarihine kadar tut
                exp_delta = datetime.fromtimestamp(exp) - datetime.utcnow()
                ttl = max(1, int(exp_delta.total_seconds()))
            else:
                # Varsayılan olarak 24 saat tut
                ttl = 86400
                
            key = f"blacklist:token:{jti}"
            redis_client.setex(key, ttl, "1")
            return True
        except:
            logger.exception("Error blacklisting token")
            return False
            
    @staticmethod
    def revoke_all_user_tokens(user_id: str) -> bool:
        """
        Kullanıcının tüm tokenlarını geçersiz kılar
        (şifre değişikliği gibi durumlarda kullanışlı)
        """
        if not redis_client:
            return False
            
        try:
            # Kullanıcı token revoke zaman damgasını güncelle
            key = f"user:tokens:revoked:{user_id}"
            timestamp = datetime.utcnow().timestamp()
            
            # 30 gün boyunca geçerli
            redis_client.setex(key, 2592000, str(timestamp))
            return True
        except:
            logger.exception("Error revoking user tokens")
            return False
            
    @staticmethod
    def setup_token_cookies(response: Response, access_token: str, refresh_token: str) -> None:
        """
        Token cookie'lerini ayarlar
        """
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=REFRESH_TOKEN_EXPIRE_DAYS * 86400
        )
        
    @staticmethod
    def clear_token_cookies(response: Response) -> None:
        """
        Token cookie'lerini temizler
        """
        response.delete_cookie(key="access_token")
        response.delete_cookie(key="refresh_token")


# FastAPI bağımlılık fonksiyonu
async def get_current_user_enhanced(
    token: str = Depends(oauth2_scheme),
    request: Request = None,
    access_token: str = Cookie(None)
) -> Dict[str, Any]:
    """
    Gelişmiş token doğrulama. Hem header hem cookie token kontrolü yapar.
    """
    # Önceliği Authorization header'a ver, yoksa cookie'den dene
    if not token and access_token:
        token = access_token
    
    # Token yoksa hata fırlat
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Token'ı çözümle
    user_data = EnhancedJWTHandler.decode_token(token)
    
    # Token tipini kontrol et
    if user_data.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Token revoke tarihini kontrol et
    if redis_client and "sub" in user_data:
        user_id = user_data["sub"]
        key = f"user:tokens:revoked:{user_id}"
        revoked_at = redis_client.get(key)
        
        if revoked_at:
            token_iat = user_data.get("iat")
            revoked_timestamp = float(revoked_at.decode('utf-8'))
            
            # Token revoke tarihinden sonra oluşturulduysa geçerli
            if token_iat and token_iat < revoked_timestamp:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                    headers={"WWW-Authenticate": "Bearer"},
                )
    
    return user_data