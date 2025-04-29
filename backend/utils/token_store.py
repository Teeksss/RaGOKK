# Last reviewed: 2025-04-29 07:20:15 UTC (User: Teeksss)
import json
import os
import secrets
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from fastapi import Request, HTTPException, status
from sqlalchemy.orm import Session

from .crypto import TokenEncryptor
from .logger import get_logger
from ..crud.user import get_user_token, save_user_token
from ..models.database import UserToken
from ..crud.user import get_user_by_id

logger = get_logger(__name__)

try:
    encryptor = TokenEncryptor()
    logger.info("Token şifreleme sistemi başlatıldı")
except ValueError as e:
    logger.critical(f"Token şifreleme sistemi başlatılamadı: {e}")
    encryptor = None

def save_token_db(db: Session, user_id: int, service: str, token_data: Dict[str, Any]) -> bool:
    """Token verilerini veritabanına şifreli olarak kaydeder"""
    if encryptor is None:
        logger.error("Token şifreleme sistemi başlatılmadı!")
        raise ValueError("Token şifreleme sistemi başlatılmadı")
        
    user = get_user_by_id(db, user_id)
    if not user:
        logger.error(f"Token kaydedilemedi: Kullanıcı bulunamadı (ID: {user_id})")
        return False
        
    # Token verilerini şifrele
    encrypted_token = encryptor.encrypt(token_data)
    
    # Expire date hesapla (varsa)
    expires_at = None
    if 'expires_in' in token_data:
        expires_at = datetime.utcnow() + timedelta(seconds=token_data['expires_in'])
    elif 'expiry' in token_data and token_data['expiry']:
        # Google OAuth için
        try:
            if isinstance(token_data['expiry'], str):
                expires_at = datetime.fromisoformat(token_data['expiry'])
            else:
                expires_at = token_data['expiry']
        except:
            pass
    
    # Token'ı kaydet
    return save_user_token(db, user_id, service, encrypted_token, expires_at)

def load_token_db(db: Session, user_id: int, service: str) -> Optional[Dict[str, Any]]:
    """Token verilerini veritabanından yükler ve çözer"""
    if encryptor is None:
        logger.error("Token şifreleme sistemi başlatılmadı!")
        raise ValueError("Token şifreleme sistemi başlatılmadı")
        
    token = get_user_token(db, user_id, service)
    if not token:
        logger.debug(f"{service} token bulunamadı (User ID: {user_id})")
        return None
        
    # Token süresi dolmuş mu kontrol et
    if token.expires_at and token.expires_at < datetime.utcnow():
        logger.warning(f"{service} token süresi dolmuş (User ID: {user_id})")
        # Eğer refresh token içeriyorsa, hata döndürmek yerine refresh edilebilir
        
    # Şifreli token'ı çöz
    token_data = encryptor.decrypt(token.encrypted_token)
    if not token_data:
        logger.error(f"{service} token çözülemedi (User ID: {user_id})")
        return None
        
    logger.info(f"{service} token DB'den yüklendi (User ID: {user_id})")
    return token_data

def save_google_token(creds: Credentials, user_id: int, db: Session):
    """Google kimlik bilgilerini güvenli bir şekilde veritabanına saklar"""
    token_data = {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': creds.scopes
    }
    
    # Expire bilgisi varsa ekle
    if hasattr(creds, 'expiry') and creds.expiry:
        token_data['expiry'] = creds.expiry.isoformat() if hasattr(creds.expiry, 'isoformat') else str(creds.expiry)
    
    return save_token_db(db, user_id, 'google', token_data)

def load_google_token(user_id: int, db: Session) -> Optional[Credentials]:
    """Google kimlik bilgilerini veritabanından yükler"""
    token_data = load_token_db(db, user_id, 'google')
    if not token_data:
        return None
        
    try:
        # Credentials oluştur
        return Credentials(
            token=token_data.get('token'),
            refresh_token=token_data.get('refresh_token'),
            token_uri=token_data.get('token_uri'),
            client_id=token_data.get('client_id'),
            client_secret=token_data.get('client_secret'),
            scopes=token_data.get('scopes')
        )
    except Exception as e:
        logger.error(f"Google Credentials oluşturulamadı: {e}", exc_info=True)
        return None

# --- OAuth State Yönetimi (Redis'e veya başka bir session store'a taşınabilir) ---
OAUTH_STATE_KEY = "oauth_state"

def save_oauth_state_to_session(request: Request, user_id: str, service: str = 'google') -> str:
    """CSRF koruması için state oluşturur ve oturuma kaydeder"""
    if "session" not in request.scope:
        logger.error("Oturum yönetimi aktif değil veya SECRET_KEY ayarlanmamış!")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Oturum yönetimi yapılandırılmamış."
        )
    state = secrets.token_urlsafe(16)
    # State ile birlikte kullanıcı ID ve hangi servis için olduğunu sakla
    request.session[OAUTH_STATE_KEY] = {
        "state": state,
        "user_id": user_id,
        "service": service,
        "timestamp": datetime.utcnow().isoformat()  # Ek güvenlik için timestamp ekle
    }
    logger.debug(f"OAuth state oturuma kaydedildi ({service}): {state[:6]}... (Kullanıcı: {user_id})")
    return state

def validate_oauth_state_from_session(request: Request, received_state: str) -> Optional[Dict[str, str]]:
    """Oturumdaki state ile callback'ten gelen state'i karşılaştırır ve kullanıcı/servis bilgisini döndürür"""
    if "session" not in request.scope:
        logger.warning("Oturum yönetimi aktif değil!")
        return None
        
    saved_state_data = request.session.pop(OAUTH_STATE_KEY, None)
    if not saved_state_data or not saved_state_data.get("state"):
        logger.warning("Oturumda kayıtlı OAuth state bulunamadı.")
        return None
        
    saved_state = saved_state_data["state"]
    timestamp = saved_state_data.get("timestamp")
    
    # State'in oluşturulma zamanını kontrol et (max 10 dakika)
    if timestamp:
        try:
            created_at = datetime.fromisoformat(timestamp)
            if (datetime.utcnow() - created_at) > timedelta(minutes=10):
                logger.warning("OAuth state süresi dolmuş.")
                return None
        except:
            pass
    
    # Secret compare ile state'i doğrula
    if secrets.compare_digest(saved_state, received_state):
        logger.debug(f"OAuth state doğrulandı ({saved_state_data.get('service')}).")
        return {
            "user_id": saved_state_data.get("user_id"),
            "service": saved_state_data.get("service")
        }
    else:
        logger.warning(f"Geçersiz OAuth state!")
        return None