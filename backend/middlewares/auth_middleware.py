# Last reviewed: 2025-04-29 11:06:31 UTC (User: Teekssseksiklikleri)
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.authentication import AuthCredentials, UnauthenticatedUser
import jwt
from typing import Optional, Dict, Any

from ..auth import get_user_by_username
from ..db.async_database import get_db
from ..utils.config import JWT_SECRET
from ..utils.logger import get_logger

logger = get_logger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    """
    JWT token doğrulama ve kullanıcı yükleme middleware'i.
    Rate limiting gibi diğer middleware'ler için request.state'e kullanıcı bilgisi ekler.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Statik dosya isteklerini atla
        if request.url.path.startswith(("/static/", "/favicon.ico")):
            return await call_next(request)
        
        # Auth başlığından JWT token'ı al
        authorization = request.headers.get("Authorization")
        token = None
        user = None
        
        if authorization and authorization.startswith("Bearer "):
            token = authorization.replace("Bearer ", "")
            
            # Token'ı doğrula
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
                username = payload.get("sub")
                
                if username:
                    # DB bağlantısı al (FastAPI'nin depends sistemini kullanamadığımız için manuel)
                    try:
                        db = await get_db().asend(None)
                        user = await get_user_by_username(db, username)
                    except Exception as e:
                        logger.error(f"Kullanıcı bilgisi alınırken hata: {e}")
                    finally:
                        try:
                            await db.close()
                        except:
                            pass
            except jwt.PyJWTError:
                # Token geçersiz, kullanıcıyı None olarak bırak
                pass
        
        # Kullanıcı bilgisini request.state'e ekle
        request.state.user = user
        request.state.token = token
        
        # İsteği işle
        response = await call_next(request)
        
        return response