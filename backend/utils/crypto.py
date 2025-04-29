# Last reviewed: 2025-04-29 07:20:15 UTC (User: Teeksss)
from cryptography.fernet import Fernet
import base64
import json
from typing import Dict, Any, Optional

from .config import SECRET_KEY
from .logger import get_logger

logger = get_logger(__name__)

class TokenEncryptor:
    def __init__(self, secret_key: str = SECRET_KEY):
        if not secret_key or len(secret_key) < 32:
            logger.error("SECRET_KEY çok kısa veya yok!")
            raise ValueError("Token şifreleme için SECRET_KEY gerekli ve en az 32 karakter olmalı")
            
        # SECRET_KEY'den 32 byte'lık bir key üret
        key_bytes = secret_key.encode()[:32].ljust(32, b'\0')
        key = base64.urlsafe_b64encode(key_bytes)
        self.cipher_suite = Fernet(key)
        
    def encrypt(self, data: Dict[str, Any]) -> str:
        """Token verisini şifreler ve base64 string olarak döndürür"""
        json_data = json.dumps(data)
        encrypted_bytes = self.cipher_suite.encrypt(json_data.encode('utf-8'))
        return base64.urlsafe_b64encode(encrypted_bytes).decode('utf-8')
        
    def decrypt(self, encrypted_data: str) -> Optional[Dict[str, Any]]:
        """Şifrelenmiş token verisini çözer ve dict olarak döndürür"""
        try:
            decoded = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            decrypted_bytes = self.cipher_suite.decrypt(decoded)
            return json.loads(decrypted_bytes.decode('utf-8'))
        except Exception as e:
            logger.error(f"Token çözme hatası: {e}")
            return None