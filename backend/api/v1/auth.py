# Last reviewed: 2025-04-29 13:23:09 UTC (User: TeeksssSSO)
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Form, Body
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List
import logging
import secrets
import base64
import time
from urllib.parse import urlparse, urlencode

from ...db.session import get_db
from ...schemas.user import User, UserCreate, TokenResponse
from ...repositories.user_repository import UserRepository
from ...auth.jwt import create_access_token, create_refresh_token, get_current_active_user
from ...auth.password import verify_password, get_password_hash
from ...auth.sso_providers import load_sso_providers, SSOProvider, SSOProviderType

router = APIRouter(
    prefix="/api/auth",
    tags=["authentication"],
    responses={
        401: {"description": "Unauthorized"},
        400: {"description": "Bad Request"}
    }
)

logger = logging.getLogger(__name__)

# SSO sağlayıcılarını yükle
sso_providers = load_sso_providers()

@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Kullanıcı adı ve şifre ile oturum açar
    
    - **username**: Kullanıcı adı veya e-posta
    - **password**: Şifre
    
    Returns a JWT token for authentication.
    """
    user_repo = UserRepository()
    user = await user_repo.get_user_by_email(db, form_data.username)
    
    if not user:
        user = await user_repo.get_user_by_username(db, form_data.username)
        
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # JWT token oluştur
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "created_at": user.created_at
        }
    }

@router.post("/register", response_model=User)
async def register(
    user: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Yeni kullanıcı kaydı yapar
    
    - **email**: E-posta adresi
    - **username**: Kullanıcı adı
    - **password**: Şifre
    - **full_name**: Ad ve soyad
    """
    user_repo = UserRepository()
    
    # E-posta veya kullanıcı adı zaten kullanılıyor mu kontrol et
    existing_user = await user_repo.get_user_by_email(db, user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    existing_user = await user_repo.get_user_by_username(db, user.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Şifreyi hashle
    hashed_password = get_password_hash(user.password)
    
    # Kullanıcıyı oluştur
    new_user = await user_repo.create_user(
        db=db,
        email=user.email,
        username=user.username,
        password=hashed_password,
        full_name=user.full_name
    )
    
    await db.commit()
    
    return new_user

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh token kullanarak yeni access token oluşturur
    
    - **refresh_token**: Geçerli bir refresh token
    """
    from ...auth.jwt import decode_token
    
    try:
        # Refresh token'ı doğrula
        payload = decode_token(refresh_token)
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Kullanıcıyı kontrol et
        user_repo = UserRepository()
        user = await user_repo.get_user_by_email(db, username)
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Yeni token oluştur
        access_token = create_access_token(data={"sub": user.email})
        new_refresh_token = create_refresh_token(data={"sub": user.email})
        
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
                "created_at": user.created_at
            }
        }
    except Exception as e:
        logger.error(f"Refresh token error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Mevcut kullanıcı bilgilerini döndürür"""
    user_repo = UserRepository()
    user = await user_repo.get_user_by_id(db, current_user["id"])
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user

@router.get("/sso/providers")
async def list_sso_providers():
    """Kullanılabilir SSO sağlayıcılarını listeler"""
    providers_info = {}
    
    for code, provider in sso_providers.items():
        if provider.enabled:
            providers_info[code] = provider.to_dict()
    
    return {"providers": providers_info}

@router.get("/sso/{provider}")
async def initiate_sso_login(
    provider: str,
    request: Request,
    redirect_uri: Optional[str] = None
):
    """SSO oturum açma işlemini başlatır"""
    # Sağlayıcıyı bul
    if provider not in sso_providers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SSO provider '{provider}' not found"
        )
    
    sso_provider = sso_providers[provider]
    
    # Yönlendirme URI'si belirleme
    if not redirect_uri:
        redirect_uri = str(request.url_for('complete_sso_login', provider=provider))
    
    # CSRF koruma için state oluştur
    state = secrets.token_urlsafe(32)
    state_data = {
        "provider": provider,
        "redirect_uri": redirect_uri,
        "timestamp": int(time.time())
    }
    
    # State'i session'a kaydet (gerçek uygulamada session veya Redis kullanılmalı)
    # Burada örnek olarak cookie kullanıyoruz
    encoded_state = base64.b64encode(json.dumps(state_data).encode()).decode()
    response = RedirectResponse(url=await sso_provider.get_authorization_url(redirect_uri, state))
    response.set_cookie(key="sso_state", value=encoded_state, httponly=True, secure=True, max_age=3600)
    
    return response

@router.get("/sso/{provider}/callback")
async def complete_sso_login(
    provider: str,
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    SAMLResponse: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """SSO sağlayıcısından gelen callback'i işler"""
    # Sağlayıcıyı bul
    if provider not in sso_providers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SSO provider '{provider}' not found"
        )
    
    sso_provider = sso_providers[provider]
    
    try:
        # SAML için özel işleme
        if sso_provider.provider_type == SSOProviderType.SAML:
            if not SAMLResponse:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing SAML response"
                )
            
            # SAML yanıtını işle
            request_data = {
                "https": "on" if request.url.scheme == "https" else "off",
                "http_host": request.headers.get("host"),
                "script_name": request.url.path,
                "get_data": dict(request.query_params),
                "post_data": {"SAMLResponse": SAMLResponse}
            }
            
            user_info = await sso_provider.process_saml_response(SAMLResponse, request_data)
        else:
            # OAuth/OIDC için standart işleme
            if not code or not state:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing authorization code or state"
                )
            
            # State'i doğrula (gerçek uygulamada session veya Redis kullanılmalı)
            stored_state = request.cookies.get("sso_state")
            if not stored_state:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid state (no stored state found)"
                )
            
            try:
                state_data = json.loads(base64.b64decode(stored_state))
                if state_data.get("provider") != provider or int(time.time()) - state_data.get("timestamp", 0) > 3600:
                    raise ValueError("State mismatch or expired")
            except Exception as e:
                logger.error(f"State validation error: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid state data"
                )
            
            # Callback URI
            redirect_uri = state_data.get("redirect_uri")
            if not redirect_uri:
                redirect_uri = str(request.url_for('complete_sso_login', provider=provider))
            
            # Kodu token'a dönüştür
            token_data = await sso_provider.exchange_code_for_token(code, redirect_uri)
            
            access_token = token_data.get("access_token")
            id_token = token_data.get("id_token")
            
            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to obtain access token"
                )
            
            # ID token varsa doğrula
            if id_token:
                try:
                    user_info = await sso_provider.validate_token(id_token)
                except Exception as e:
                    logger.error(f"ID token validation error: {e}")
                    user_info = None
            else:
                user_info = None
            
            # Kullanıcı bilgilerini al (ID token yoksa veya doğrulanamadıysa)
            if not user_info:
                user_info = await sso_provider.get_user_info(access_token)
        
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to obtain user information"
            )
        
        # Kullanıcı e-postası kontrolü
        email = user_info.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User email not provided by identity provider"
            )
        
        # Kullanıcı var mı kontrol et, yoksa oluştur
        user_repo = UserRepository()
        user = await user_repo.get_user_by_email(db, email)
        
        if not user:
            # Kullanıcı adı oluştur
            name = user_info.get("name", "").split()
            username = email.split("@")[0]
            
            # Kullanıcı adının benzersiz olduğundan emin ol
            base_username = username
            i = 1
            while await user_repo.get_user_by_username(db, username):
                username = f"{base_username}{i}"
                i += 1
            
            # Yeni kullanıcı oluştur
            full_name = user_info.get("name") or f"{username}"
            password = secrets.token_urlsafe(32)  # Rastgele şifre (SSO kullanıcıları için gerekli değil)
            
            user = await user_repo.create_user(
                db=db,
                email=email,
                username=username,
                password=get_password_hash(password),
                full_name=full_name,
                sso_provider=provider,
                sso_id=user_info.get("id", "")
            )
            await db.commit()
        
        # JWT token oluştur
        access_token = create_access_token(data={"sub": user.email})
        refresh_token = create_refresh_token(data={"sub": user.email})
        
        # Kullanıcıyı frontend'e yönlendir (token ile)
        frontend_url = settings.FRONTEND_URL
        
        if not frontend_url:
            # Token bilgilerini JSON yanıt olarak döndür
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "full_name": user.full_name
                }
            }
        
        # Frontend URL'sine token bilgileriyle yönlendir
        query_params = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "provider": provider
        }
        redirect_url = f"{frontend_url}/auth/callback?{urlencode(query_params)}"
        
        # State cookie'sini temizle
        response = RedirectResponse(url=redirect_url)
        response.delete_cookie(key="sso_state")
        
        return response
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(f"SSO login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SSO login failed: {str(e)}"
        )