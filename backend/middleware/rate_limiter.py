# Last reviewed: 2025-04-30 07:41:30 UTC (User: Teeksss)
from typing import Dict, Any, List, Optional, Tuple, Callable
import time
import json
import logging
from datetime import datetime
import hashlib
import os

# Redis için async client
import redis.asyncio as redis

# FastAPI
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Rate limiter ayarları
DEFAULT_RATE_LIMIT = int(os.getenv("DEFAULT_RATE_LIMIT", "100"))  # dakika başına istek sayısı
LOGIN_RATE_LIMIT = int(os.getenv("LOGIN_RATE_LIMIT", "5"))        # dakika başına login denemesi
LOGIN_BLOCK_DURATION = int(os.getenv("LOGIN_BLOCK_DURATION", "15")) # dakika
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"

class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting ve brute-force koruma için middleware
    """
    def __init__(self, app):
        """
        Args:
            app: FastAPI uygulaması
        """
        super().__init__(app)
        
        # Redis bağlantısını başlat
        try:
            self.redis = redis.from_url(REDIS_URL) if RATE_LIMIT_ENABLED else None
        except Exception as e:
            logger.warning(f"Redis connection failed, rate limiting is disabled: {str(e)}")
            self.redis = None
        
        # Limitleri ayarla
        self.path_limits = {
            "/api/v1/auth/login": LOGIN_RATE_LIMIT,
            "/api/v1/auth/refresh": LOGIN_RATE_LIMIT * 2
        }
        self.default_rate_limit = DEFAULT_RATE_LIMIT
        self.login_block_duration = LOGIN_BLOCK_DURATION
    
    async def rate_limit_key(self, request: Request) -> str:
        """
        İstek için benzersiz anahtar oluşturur
        
        Args:
            request: FastAPI istek nesnesi
            
        Returns:
            str: Redis key
        """
        # Erişim kontrolü için anahtarı belirle
        path = request.url.path
        
        # Auth endpoint'leri için IP bazlı anahtar
        if path.startswith("/api/v1/auth/"):
            # IP adresi al (X-Forwarded-For, X-Real-IP veya client.host)
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                client_ip = forwarded_for.split(",")[0].strip()
            else:
                client_ip = request.headers.get("X-Real-IP", request.client.host)
                
            key_base = f"ip:{client_ip}:{path}"
        else:
            # Kullanıcı kimliği varsa kullan, yoksa IP
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                # Token'dan identifier çıkar (tam token kullanmadan unique değer oluştur)
                token_hash = hashlib.md5(auth_header[7:].encode()).hexdigest()[:8]
                key_base = f"user:{token_hash}:{path}"
            else:
                # IP adresi kullan
                client_ip = request.headers.get("X-Real-IP", request.client.host)
                key_base = f"ip:{client_ip}:{path}"
        
        # Redis key'i döndür
        return f"rate_limit:{hashlib.md5(key_base.encode()).hexdigest()}"
    
    async def is_rate_limited(self, request: Request) -> Tuple[bool, int]:
        """
        İstek rate limited mi kontrolü yapar
        
        Args:
            request: FastAPI istek nesnesi
            
        Returns:
            Tuple[bool, int]: Rate limited mi, kalan limit
        """
        # Redis yok veya rate limiting kapalıysa sınırlama yok
        if not self.redis or not RATE_LIMIT_ENABLED:
            return False, self.default_rate_limit
        
        path = request.url.path
        
        # Login endpoint'i için IP blok kontrolü
        if path == "/api/v1/auth/login":
            # IP adresi
            client_ip = request.headers.get("X-Real-IP", request.client.host)
            
            # Bloklanmış mı kontrol et
            block_key = f"login_block:{hashlib.md5(client_ip.encode()).hexdigest()}"
            is_blocked = await self.redis.exists(block_key)
            
            if is_blocked:
                return True, 0
        
        # Rate limit anahtarını oluştur
        key = await self.rate_limit_key(request)
        current_minute = int(time.time() / 60)
        full_key = f"{key}:{current_minute}"
        
        # Yol için limit belirle
        limit = self.path_limits.get(path, self.default_rate_limit)
        
        # Sayacı artır
        count = await self.redis.incr(full_key)
        
        # İlk istek ise TTL ayarla
        if count == 1:
            await self.redis.expire(full_key, 60)  # 1 dakika
        
        # Limit aşıldı mı?
        if count > limit:
            return True, 0
        
        return False, limit - count
    
    async def record_failed_login(self, request: Request) -> int:
        """
        Başarısız login denemesini kaydeder
        
        Args:
            request: FastAPI istek nesnesi
            
        Returns:
            int: Toplam başarısız deneme sayısı
        """
        # Redis yoksa kayıt yapma
        if not self.redis or not RATE_LIMIT_ENABLED:
            return 0
        
        # IP adresi
        client_ip = request.headers.get("X-Real-IP", request.client.host)
        ip_hash = hashlib.md5(client_ip.encode()).hexdigest()
        
        # Mevcut dakika
        current_minute = int(time.time() / 60)
        key = f"failed_login:{ip_hash}:{current_minute}"
        
        # Sayacı artır
        count = await self.redis.incr(key)
        
        # İlk deneme ise TTL ayarla
        if count == 1:
            await self.redis.expire(key, 60)  # 1 dakika
        
        # Limit aşıldıysa blokla
        if count >= LOGIN_RATE_LIMIT:
            block_key = f"login_block:{ip_hash}"
            await self.redis.set(block_key, 1, ex=self.login_block_duration * 60)
            logger.warning(f"IP blocked for login attempts: {client_ip}")
        
        return count
    
    async def reset_failed_logins(self, request: Request) -> None:
        """
        Başarılı login sonrası failed login sayacını sıfırlar
        
        Args:
            request: FastAPI istek nesnesi
        """
        # Redis yoksa işlem yapma
        if not self.redis or not RATE_LIMIT_ENABLED:
            return
        
        # IP adresi
        client_ip = request.headers.get("X-Real-IP", request.client.host)
        ip_hash = hashlib.md5(client_ip.encode()).hexdigest()
        
        # Mevcut dakika
        current_minute = int(time.time() / 60)
        key = f"failed_login:{ip_hash}:{current_minute}"
        
        # Sayacı sıfırla
        await self.redis.delete(key)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Middleware dispatch metodu
        """
        # Public endpoint'ler ve OPTIONS istekleri için rate limit kontrolü yapma
        if request.method == "OPTIONS" or request.url.path in [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json"
        ] or request.url.path.startswith(("/static/", "/assets/")):
            return await call_next(request)
        
        # Rate limit kontrolü
        is_limited, remaining = await self.is_rate_limited(request)
        
        if is_limited:
            # Rate limit aşıldı
            logger.warning(f"Rate limit exceeded for {request.url.path} from {request.client.host}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Too many requests, please try again later."
                }
            )
        
        # İstek işleme devam et
        response = await call_next(request)
        
        # Rate limit header'larını ekle
        if RATE_LIMIT_ENABLED:
            path = request.url.path
            limit = self.path_limits.get(path, self.default_rate_limit)
            
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(int(time.time() / 60) * 60 + 60)  # Dakika sonunda reset
        
        return response


# Login Handler için başarısız giriş kaydedici
class LoginHandler:
    """
    Login istekleri için özel işleyici.
    Başarısız girişleri kaydeder ve başarılı girişlerde sayacı sıfırlar.
    """
    def __init__(self, rate_limiter: RateLimiterMiddleware):
        self.rate_limiter = rate_limiter
    
    async def record_failed_login(self, request: Request) -> None:
        """
        Başarısız login denemesini kaydeder
        """
        await self.rate_limiter.record_failed_login(request)
    
    async def reset_failed_logins(self, request: Request) -> None:
        """
        Başarılı login sonrası sayacı sıfırlar
        """
        await self.rate_limiter.reset_failed_logins(request)