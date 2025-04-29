# Last reviewed: 2025-04-29 09:15:13 UTC (User: TeeksssAPI)
from typing import Optional
from cryptography.fernet import Fernet
import base64
import os
from .config import SECRET_KEY
from .logger import get_logger

logger = get_logger(__name__)

# Fernet anahtarı için en az 32 byte'lık bir anahtar gerekir
def get_encryption_key() -> bytes:
    """Şifreleme için kullanılacak anahtarı oluşturur"""
    # SECRET_KEY'i kullan ama 32 byte'a genişlet veya kısalt
    if SECRET_KEY:
        # SHA-256 ile 32 byte'lık anahtar oluştur
        import hashlib
        sha256 = hashlib.sha256()
        sha256.update(SECRET_KEY.encode())
        return base64.urlsafe_b64encode(sha256.digest())
    else:
        # Yeni bir anahtar oluştur (sadece geliştirme için)
        logger.warning("SECRET_KEY bulunamadı, geçici şifreleme anahtarı oluşturuluyor")
        return Fernet.generate_key()

# Şifreleme anahtarını önbelleğe al
try:
    encryption_key = get_encryption_key()
    cipher_suite = Fernet(encryption_key)
except Exception as e:
    logger.error(f"Şifreleme anahtarı oluşturma hatası: {e}")
    cipher_suite = None

def encrypt_value(value: str) -> Optional[str]:
    """Bir değeri şifreler"""
    if not value:
        return None
        
    if not cipher_suite:
        logger.error("Şifreleme anahtarı oluşturulamadığı için şifreleme yapılamadı")
        # Acil durum: Üretimde asla kullanma!
        return f"UNENCRYPTED:{value}"
    
    try:
        return cipher_suite.encrypt(value.encode()).decode()
    except Exception as e:
        logger.error(f"Şifreleme hatası: {e}")
        return None

def decrypt_value(encrypted_value: str) -> Optional[str]:
    """Şifrelenmiş bir değeri çözer"""
    if not encrypted_value:
        return None
        
    # Acil durum kodunu kontrol et
    if encrypted_value.startswith("UNENCRYPTED:"):
        logger.warning("Şifrelenmemiş değer tespit edildi!")
        return encrypted_value[12:]
    
    if not cipher_suite:
        logger.error("Şifreleme anahtarı oluşturulamadığı için çözme yapılamadı")
        return None
    
    try:
        return cipher_suite.decrypt(encrypted_value.encode()).decode()
    except Exception as e:
        logger.error(f"Çözme hatası: {e}")
        return None