# Last reviewed: 2025-04-29 07:20:15 UTC (User: Teeksss)
import os
import io
import asyncio
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import dropbox
from dropbox import DropboxOAuth2Flow
from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from .config import (
    GOOGLE_DRIVE_SCOPES, GOOGLE_CREDENTIALS_FILE, GOOGLE_REDIRECT_URI,
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
    DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_REDIRECT_URI
)
from .token_store import (
    save_oauth_state_to_session, validate_oauth_state_from_session,
    save_token_db, load_token_db, save_google_token, load_google_token
)
from .logger import get_logger
from typing import Optional, Dict

logger = get_logger(__name__)

# --- Google Drive Fonksiyonları ---
def _check_google_credentials_file():
    """Credentials dosyasının varlığını ve config'i kontrol eder."""
    if not os.path.exists(GOOGLE_CREDENTIALS_FILE):
        raise ValueError(f"Google Credentials dosyası bulunamadı: {GOOGLE_CREDENTIALS_FILE}.")
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise ValueError("GOOGLE_CLIENT_ID veya GOOGLE_CLIENT_SECRET .env dosyasında ayarlanmamış.")

def get_google_drive_service(user_id: int, db: Session):
    """Google Drive API servisini oluşturur (kullanıcıya özel)."""
    creds = load_google_token(user_id, db)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info(f"GDrive token (User ID: {user_id}) yenileniyor...")
            try:
                # Client ID/Secret eksikse config'den al
                if not creds.client_id:
                    creds._client_id = GOOGLE_CLIENT_ID
                if not creds.client_secret:
                    creds._client_secret = GOOGLE_CLIENT_SECRET
                creds.refresh(Request())
                save_google_token(creds, user_id, db)
                logger.info(f"GDrive token (User ID: {user_id}) yenilendi.")
            except Exception as e:
                logger.error(f"GDrive token (User ID: {user_id}) yenilenemedi: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Google Drive token yenilenemedi."
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google Drive yetkilendirmesi gerekli/geçersiz."
            )
    try:
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        logger.error(f"GDrive servisi oluşturulamadı (User ID: {user_id}): {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Google Drive servisine bağlanılamadı."
        )

def start_google_drive_auth_flow(request: Request, user_id: str) -> str:
    """Yetkilendirme akışını başlatır ve URL'yi döndürür."""
    _check_google_credentials_file()
    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            GOOGLE_CREDENTIALS_FILE,
            GOOGLE_DRIVE_SCOPES,
            redirect_uri=GOOGLE_REDIRECT_URI
        )
        state = save_oauth_state_to_session(request, user_id, 'google')
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            prompt='consent',
            state=state
        )
        logger.info(f"GDrive yetkilendirme URL'si oluşturuldu (User ID: {user_id}).")
        return auth_url
    except Exception as e:
        logger.error(f"GDrive yetkilendirme başlatılamadı (User ID: {user_id}): {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google Drive yetkilendirme başlatılamadı."
        )

async def complete_google_drive_auth_flow(request: Request, state: str, code: str, db: Session):
    """Callback'i işler, state'i doğrular ve token alır/saklar."""
    validated_data = validate_oauth_state_from_session(request, state)
    if not validated_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Geçersiz OAuth state."
        )
    
    user_id = int(validated_data['user_id'])
    
    _check_google_credentials_file()
    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            GOOGLE_CREDENTIALS_FILE,
            GOOGLE_DRIVE_SCOPES,
            redirect_uri=GOOGLE_REDIRECT_URI
        )
        flow.fetch_token(code=code)
        save_google_token(flow.credentials, user_id, db)
        logger.info(f"GDrive yetkilendirmesi tamamlandı (User ID: {user_id}).")
        return flow.credentials
    except Exception as e:
        logger.error(f"Google token alınamadı (User ID: {user_id}): {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google yetkilendirme kodu geçersiz/kullanılamadı."
        )

async def read_google_drive_file(file_id: str, user_id: int, db: Session) -> Optional[str]:
    """Google Drive dosyasının içeriğini okur (async, kullanıcıya özel)."""
    service = get_google_drive_service(user_id, db)
    try:
        logger.info(f"GDrive'dan dosya indiriliyor: {file_id} (User ID: {user_id})")
        
        def download_sync():
            request_media = service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request_media)
            done = False
            while not done:
                status_prog, done = downloader.next_chunk()
            fh.seek(0)
            return fh.read()
        
        file_bytes = await asyncio.to_thread(download_sync)
        
        # TODO: Dosya türüne göre (PDF, image, text) içerik çıkarımı
        try:
            content = file_bytes.decode('utf-8')
            logger.info(f"GDrive dosyası {file_id} okundu.")
            return content
        except UnicodeDecodeError:
            logger.warning(f"Dosya {file_id} UTF-8 değil.")
            return "[Okunamayan İçerik]"
    except HttpError as error:
        logger.error(f"GDrive indirme hatası ({file_id}): {error}", exc_info=True)
        if error.resp.status == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"GDrive dosyası bulunamadı: {file_id}"
            )
        elif error.resp.status in [401, 403]:
            raise HTTPException(
                status_code=error.resp.status,
                detail=f"GDrive dosya erişim hatası ({error.resp.status}): {file_id}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"GDrive dosya indirme hatası ({error.resp.status})"
            )
    except Exception as e:
        logger.error(f"GDrive okuma hatası ({file_id}): {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"GDrive dosyası okunamadı."
        )

# --- Dropbox Fonksiyonları ---
def get_dropbox_client(user_id: int, db: Session):
    """Dropbox istemcisini oluşturur (kullanıcıya özel)."""
    token_data = load_token_db(db, user_id, 'dropbox')
    if not token_data:
        logger.error(f"Dropbox token bulunamadı (User ID: {user_id})")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Dropbox yetkilendirmesi gerekli."
        )
    
    access_token = token_data.get('access_token')
    if not access_token:
        logger.error(f"Dropbox token geçersiz (User ID: {user_id})")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz Dropbox token."
        )
        
    try:
        dbx = dropbox.Dropbox(access_token)
        dbx.users_get_current_account()  # Test token
        return dbx
    except dropbox.exceptions.AuthError as e:
        logger.error(f"Dropbox auth hatası (User ID: {user_id}): {e}", exc_info=True)
        
        # Refresh token varsa yenile
        refresh_token = token_data.get('refresh_token')
        if refresh_token:
            try:
                new_token = dropbox.oauth.DropboxOAuth2RefreshResult(
                    access_token=refresh_token,
                    expires_in=14400  # Default
                )
                # Yeni token'ı kaydet
                token_data['access_token'] = new_token.access_token
                token_data['expires_at'] = new_token.expires_at.isoformat() if hasattr(new_token, 'expires_at') else None
                
                save_token_db(db, user_id, 'dropbox', token_data)
                
                # Yeni token'la istemci oluştur
                dbx = dropbox.Dropbox(new_token.access_token)
                dbx.users_get_current_account()  # Tekrar test
                return dbx
            except Exception as refresh_err:
                logger.error(f"Dropbox token yenilemesi başarısız (User ID: {user_id}): {refresh_err}", exc_info=True)
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Dropbox oturumunuz geçersiz. Lütfen tekrar yetkilendirin."
        )
    except Exception as e:
        logger.error(f"Dropbox istemci hatası: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Dropbox servisine bağlanılamadı."
        )

def start_dropbox_auth_flow(request: Request, user_id: str) -> str:
    """Dropbox OAuth yetkilendirme akışını başlatır"""
    if not all([DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_REDIRECT_URI]):
        logger.error("Dropbox OAuth ayarları eksik.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Dropbox OAuth ayarları eksik."
        )
    
    try:
        # CSRF koruması için OAuth state oluştur
        state = save_oauth_state_to_session(request, user_id, 'dropbox')
        
        # Dropbox auth URL'ini oluştur
        auth_flow = DropboxOAuth2Flow(
            consumer_key=DROPBOX_APP_KEY,
            consumer_secret=DROPBOX_APP_SECRET,
            redirect_uri=DROPBOX_REDIRECT_URI,
            session={},  # Boş session, state zaten FastAPI session'da tutuluyor
            csrf_token_session_key=state,  # State'i anahtar olarak kullan
        )
        
        auth_url = auth_flow.start()
        logger.info(f"Dropbox yetkilendirme URL'si oluşturuldu (User ID: {user_id}).")
        return auth_url
    except Exception as e:
        logger.error(f"Dropbox yetkilendirme başlatılamadı (User ID: {user_id}): {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dropbox yetkilendirme başlatılamadı."
        )

async def complete_dropbox_auth_flow(request: Request, state: str, code: str, db: Session):
    """Dropbox OAuth callback'i işler ve token alır/saklar"""
    validated_data = validate_oauth_state_from_session(request, state)
    if not validated_data:
        logger.warning("Geçersiz Dropbox OAuth state.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Geçersiz OAuth state."
        )
    
    user_id = int(validated_data['user_id'])
    
    if not all([DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_REDIRECT_URI]):
        logger.error("Dropbox OAuth ayarları eksik.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Dropbox OAuth ayarları eksik."
        )
    
    try:
        # Token al
        auth_flow = DropboxOAuth2Flow(
            consumer_key=DROPBOX_APP_KEY,
            consumer_secret=DROPBOX_APP_SECRET,
            redirect_uri=DROPBOX_REDIRECT_URI,
            session={},  # Boş session
            csrf_token_session_key=state,  # State'i anahtar olarak kullan
        )
        
        oauth_result = auth_flow.finish({"state": state, "code": code})
        
        # Token verisini hazırla
        token_data = {
            'access_token': oauth_result.access_token,
            'refresh_token': getattr(oauth_result, 'refresh_token', None),
            'token_type': getattr(oauth_result, 'token_type', 'bearer'),
            'expires_at': oauth_result.expires_at.isoformat() if hasattr(oauth_result, 'expires_at') else None,
            'scope': getattr(oauth_result, 'scope', ['files.content.read'])
        }
        
        # Token verisini kaydet
        success = save_token_db(db, user_id, 'dropbox', token_data)
        if not success:
            raise Exception("Token kaydedilemedi")
        
        logger.info(f"Dropbox yetkilendirmesi tamamlandı (User ID: {user_id}).")
        return token_data
    except Exception as e:
        logger.error(f"Dropbox token alınamadı (User ID: {user_id}): {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dropbox yetkilendirme hatası: {str(e)}"
        )

async def read_dropbox_file(file_path: str, user_id: int, db: Session) -> Optional[str]:
    """Dropbox dosyasının içeriğini okur (async, kullanıcıya özel)."""
    dbx = get_dropbox_client(user_id, db)
    
    try:
        if not file_path.startswith('/'):
            file_path = '/' + file_path
        
        logger.info(f"Dropbox'tan dosya indiriliyor: {file_path} (User ID: {user_id})")
        
        def download_sync_dbx():
            metadata, res = dbx.files_download(path=file_path)
            return res.content
        
        file_bytes = await asyncio.to_thread(download_sync_dbx)
        
        try:
            content = file_bytes.decode('utf-8')
            logger.info(f"Dropbox dosyası {file_path} okundu.")
            return content
        except UnicodeDecodeError:
            logger.warning(f"Dosya {file_path} UTF-8 değil.")
            return "[Okunamayan İçerik]"
    except dropbox.exceptions.ApiError as err:
        logger.error(f"Dropbox API hatası ({file_path}): {err}", exc_info=True)
        if isinstance(err.error, dropbox.files.DownloadError) and err.error.is_path() and err.error.get_path().is_not_found():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dropbox dosyası bulunamadı: {file_path}"
            )
        elif isinstance(err.error, dropbox.files.DownloadError) and err.error.is_path() and err.error.get_path().is_restricted_content():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Dropbox dosya erişimi kısıtlı: {file_path}"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dropbox API hatası."
        )
    except Exception as e:
        logger.error(f"Dropbox okuma hatası ({file_path}): {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dropbox dosyası okunamadı."
        )