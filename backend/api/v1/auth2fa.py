# Last reviewed: 2025-04-30 07:41:30 UTC (User: Teeksss)
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, BackgroundTasks, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
import logging

from ...db.session import get_db
from ...auth.two_factor import TwoFactorAuth
from ...auth.enhanced_jwt import get_current_user_enhanced
from ...schemas.auth import TwoFactorSetupSchema, TwoFactorVerifySchema
from ...repositories.user_repository import UserRepository

router = APIRouter(prefix="/auth/2fa", tags=["auth"])
logger = logging.getLogger(__name__)

# Servisleri başlat
two_factor_auth = TwoFactorAuth()
user_repository = UserRepository()

@router.get("/status", response_model=Dict[str, Any])
async def get_2fa_status(
    current_user: Dict[str, Any] = Depends(get_current_user_enhanced),
    db: AsyncSession = Depends(get_db)
):
    """
    Kullanıcının 2FA durumunu getirir
    """
    try:
        # Kullanıcıyı getir
        user = await user_repository.get_user_by_id(db, current_user["id"])
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # 2FA durumu
        has_2fa = False
        setup_in_progress = False
        
        if user.metadata:
            # 2FA aktif mi?
            has_2fa = user.metadata.get("2fa_enabled", False)
            
            # Kurulum devam ediyor mu?
            setup_in_progress = "temp_2fa_secret" in user.metadata
        
        return {
            "has_2fa": has_2fa,
            "setup_in_progress": setup_in_progress
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting 2FA status: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting 2FA status: {str(e)}"
        )

@router.post("/setup", response_model=TwoFactorSetupSchema)
async def setup_2fa(
    current_user: Dict[str, Any] = Depends(get_current_user_enhanced),
    db: AsyncSession = Depends(get_db)
):
    """
    Kullanıcı için 2FA kurulumu başlatır
    """
    try:
        # 2FA kurulumunu başlat
        result = await two_factor_auth.setup_2fa(db, current_user["id"])
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Error setting up 2FA")
            )
        
        # Kurulum bilgilerini döndür
        return {
            "secret": result["secret"],
            "qr_code": result["qr_code"],
            "setup_uri": result["uri"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting up 2FA: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error setting up 2FA: {str(e)}"
        )

@router.post("/verify", response_model=Dict[str, Any])
async def verify_2fa(
    verify_data: TwoFactorVerifySchema,
    current_user: Dict[str, Any] = Depends(get_current_user_enhanced),
    db: AsyncSession = Depends(get_db)
):
    """
    2FA kodunu doğrular ve aktifleştirir
    """
    try:
        # 2FA kodunu doğrula
        result = await two_factor_auth.verify_and_activate_2fa(
            db=db,
            user_id=current_user["id"],
            code=verify_data.code
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Invalid verification code")
            )
        
        return {
            "success": True,
            "message": "Two-factor authentication enabled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying 2FA: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying 2FA: {str(e)}"
        )

@router.post("/disable", response_model=Dict[str, Any])
async def disable_2fa(
    verify_data: TwoFactorVerifySchema,
    current_user: Dict[str, Any] = Depends(get_current_user_enhanced),
    db: AsyncSession = Depends(get_db)
):
    """
    2FA'yı devre dışı bırakır
    """
    try:
        # 2FA'yı devre dışı bırak
        result = await two_factor_auth.disable_2fa(
            db=db,
            user_id=current_user["id"],
            code=verify_data.code
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Invalid verification code")
            )
        
        return {
            "success": True,
            "message": "Two-factor authentication disabled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disabling 2FA: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error disabling 2FA: {str(e)}"
        )

@router.post("/login-verify", response_model=Dict[str, Any])
async def login_verify_2fa(
    verify_data: TwoFactorVerifySchema,
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Login sırasında 2FA doğrulaması yapar
    """
    try:
        # Session'dan kullanıcı ID'sini al
        user_id = request.session.get("2fa_pending_user_id")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No pending 2FA verification"
            )
        
        # 2FA kodunu doğrula
        valid = await two_factor_auth.verify_2fa_code(
            db=db,
            user_id=user_id,
            code=verify_data.code
        )
        
        if not valid:
            # Başarısız deneme sayacını artır (brute-force önleme)
            background_tasks.add_task(
                increment_failed_2fa_attempts,
                request.client.host
            )
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code"
            )
        
        # Kullanıcıyı getir
        user = await user_repository.get_user_by_id(db, user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Session'dan 2FA durumunu temizle
        if "2fa_pending_user_id" in request.session:
            del request.session["2fa_pending_user_id"]
        
        # Token oluştur
        from ...auth.enhanced_jwt import EnhancedJWTHandler
        
        user_data = {
            "sub": str(user.id),
            "id": str(user.id),
            "email": user.email,
            "roles": user.roles or ["user"],
            "organization_id": str(user.organization_id) if user.organization_id else None,
            "permissions": user.metadata.get("permissions", []) if user.metadata else []
        }
        
        access_token = EnhancedJWTHandler.create_access_token(data=user_data)
        refresh_token = EnhancedJWTHandler.create_refresh_token(data={"sub": str(user.id)})
        
        # Cookie'ye kaydet
        EnhancedJWTHandler.setup_token_cookies(
            response=response,
            access_token=access_token["token"],
            refresh_token=refresh_token["token"]
        )
        
        return {
            "success": True,
            "access_token": access_token["token"],
            "refresh_token": refresh_token["token"],
            "token_type": "bearer",
            "expires_at": access_token["expires_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying 2FA during login: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying 2FA during login: {str(e)}"
        )


# 2FA başarısız deneme sayacı artırma (brute-force önleme)
async def increment_failed_2fa_attempts(ip: str):
    """
    Başarısız 2FA denemelerini artırır
    """
    # Redis bağlantısı yoksa işlem yapma
    from backend.auth.enhanced_jwt import redis_client
    if not redis_client:
        return
    
    import hashlib
    ip_hash = hashlib.md5(ip.encode()).hexdigest()
    key = f"failed_2fa:{ip_hash}"
    
    # Sayacı artır
    count = await redis_client.incr(key)
    
    # İlk deneme ise TTL ayarla
    if count == 1:
        await redis_client.expire(key, 300)  # 5 dakika
    
    # Limit aşıldıysa blokla (5 başarısız deneme)
    if count >= 5:
        block_key = f"2fa_block:{ip_hash}"
        await redis_client.set(block_key, 1, ex=900)  # 15 dakika blok
        logger.warning(f"IP blocked for 2FA attempts: {ip}")