# Last reviewed: 2025-04-30 07:30:01 UTC (User: Teeksss)
from typing import Optional, Dict, Any
import pyotp
import qrcode
import io
import base64
import secrets
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from ..models.user import User
from ..repositories.user_repository import UserRepository

class TwoFactorAuth:
    """İki faktörlü kimlik doğrulama servisi"""
    
    def __init__(self):
        self.user_repository = UserRepository()
    
    async def setup_2fa(self, db: AsyncSession, user_id: str) -> Dict[str, Any]:
        """
        Kullanıcı için 2FA kurulumu
        
        Returns:
            Dict: QR code ve secret key bilgileri
        """
        # Kullanıcıyı getir
        user = await self.user_repository.get_user_by_id(db, user_id)
        if not user:
            return {"success": False, "error": "User not found"}
        
        # Secret key oluştur
        secret = pyotp.random_base32()
        
        # Geçici olarak kullanıcı verisine kaydet (doğrulama sonrası kalıcı hale gelecek)
        metadata = user.metadata or {}
        metadata["temp_2fa_secret"] = secret
        metadata["temp_2fa_created_at"] = datetime.utcnow().isoformat()
        
        await self.user_repository.update_user(db, user_id=user_id, metadata=metadata)
        
        # QR Code URL'i oluştur
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(user.email, issuer_name="RAG Base")
        
        # QR Code görüntüsü oluştur
        qr_img = qrcode.make(uri)
        buffered = io.BytesIO()
        qr_img.save(buffered)
        qr_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        return {
            "success": True,
            "secret": secret,
            "qr_code": f"data:image/png;base64,{qr_base64}",
            "uri": uri
        }
    
    async def verify_and_activate_2fa(self, 
                                  db: AsyncSession, 
                                  user_id: str, 
                                  code: str) -> Dict[str, bool]:
        """
        2FA kodunu doğrula ve aktifleştir
        
        Args:
            db: Veritabanı oturumu
            user_id: Kullanıcı ID
            code: Doğrulama kodu
            
        Returns:
            Dict: İşlem sonucu
        """
        # Kullanıcıyı getir
        user = await self.user_repository.get_user_by_id(db, user_id)
        if not user or not user.metadata or "temp_2fa_secret" not in user.metadata:
            return {"success": False, "error": "No 2FA setup in progress"}
        
        # Geçici 2FA anahtarını kontrol et
        secret = user.metadata["temp_2fa_secret"]
        created_at = datetime.fromisoformat(user.metadata["temp_2fa_created_at"])
        
        # Kurulum 10 dakikadan eski ise iptal et
        if datetime.utcnow() - created_at > timedelta(minutes=10):
            metadata = user.metadata
            del metadata["temp_2fa_secret"]
            del metadata["temp_2fa_created_at"]
            await self.user_repository.update_user(db, user_id=user_id, metadata=metadata)
            return {"success": False, "error": "2FA setup expired"}
        
        # Kodu doğrula
        totp = pyotp.TOTP(secret)
        if totp.verify(code):
            # 2FA'yı aktifleştir
            metadata = user.metadata
            metadata["2fa_enabled"] = True
            metadata["2fa_secret"] = secret
            
            # Geçici verileri temizle
            del metadata["temp_2fa_secret"]
            del metadata["temp_2fa_created_at"]
            
            await self.user_repository.update_user(
                db, 
                user_id=user_id, 
                metadata=metadata,
                has_2fa=True
            )
            return {"success": True}
        else:
            return {"success": False, "error": "Invalid verification code"}
    
    async def verify_2fa_code(self, 
                          db: AsyncSession, 
                          user_id: str, 
                          code: str) -> bool:
        """
        2FA kodunu doğrula (login sırasında)
        """
        # Kullanıcıyı getir
        user = await self.user_repository.get_user_by_id(db, user_id)
        if not user or not user.metadata or not user.metadata.get("2fa_enabled"):
            return False
        
        # 2FA anahtarını al
        secret = user.metadata["2fa_secret"]
        
        # Kodu doğrula
        totp = pyotp.TOTP(secret)
        return totp.verify(code)
    
    async def disable_2fa(self, 
                      db: AsyncSession, 
                      user_id: str, 
                      code: str) -> Dict[str, bool]:
        """
        2FA'yı devre dışı bırak
        """
        if not await self.verify_2fa_code(db, user_id, code):
            return {"success": False, "error": "Invalid verification code"}
        
        user = await self.user_repository.get_user_by_id(db, user_id)
        if not user:
            return {"success": False, "error": "User not found"}
        
        # 2FA'yı kaldır
        metadata = user.metadata or {}
        if "2fa_enabled" in metadata:
            metadata["2fa_enabled"] = False
        if "2fa_secret" in metadata:
            del metadata["2fa_secret"]
        
        await self.user_repository.update_user(
            db,
            user_id=user_id,
            metadata=metadata,
            has_2fa=False
        )
        
        return {"success": True}