# Last reviewed: 2025-04-29 12:28:23 UTC (User: TeeksssCSRF)
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time
import secrets
import re
import logging
import base64
import hashlib
import hmac
import urllib.parse
import typing
import json
from enum import Enum
from dataclasses import dataclass
import html

logger = logging.getLogger(__name__)

class SecurityPolicyType(Enum):
    """Güvenlik politika türleri"""
    STRICT = "strict"
    MODERATE = "moderate"
    RELAXED = "relaxed"

@dataclass
class SecurityConfig:
    """Güvenlik yapılandırması"""
    # CSRF
    csrf_enabled: bool = True
    csrf_cookie_name: str = "csrf_token"
    csrf_header_name: str = "X-CSRF-Token"
    csrf_cookie_secure: bool = True
    csrf_cookie_samesite: str = "Lax"
    csrf_cookie_path: str = "/"
    csrf_methods: typing.List[str] = None  # POST, PUT, DELETE, PATCH
    csrf_exempt_paths: typing.List[str] = None
    csrf_secret_key: str = None  # JWT ile imzalama için gizli anahtar
    
    # XSS
    xss_protection: bool = True
    xss_sanitize_inputs: bool = True
    xss_filter_response: bool = True
    xss_filter_exempt_paths: typing.List[str] = None
    
    # Content Security Policy
    csp_enabled: bool = True
    csp_policy: typing.Dict[str, str] = None
    csp_report_only: bool = False
    csp_report_uri: str = None
    
    # Security Headers
    security_headers: bool = True
    hsts_enabled: bool = True
    hsts_max_age: int = 31536000  # 1 yıl
    
    # CORS
    cors_origins: typing.List[str] = None
    cors_allow_credentials: bool = True
    cors_allow_methods: typing.List[str] = None
    cors_allow_headers: typing.List[str] = None
    
    def __post_init__(self):
        """Varsayılan değerleri ayarla"""
        if self.csrf_methods is None:
            self.csrf_methods = ["POST", "PUT", "DELETE", "PATCH"]
        
        if self.csrf_exempt_paths is None:
            self.csrf_exempt_paths = ["/api/auth/login", "/api/auth/register"]
        
        if self.csrf_secret_key is None:
            self.csrf_secret_key = secrets.token_hex(32)
        
        if self.xss_filter_exempt_paths is None:
            self.xss_filter_exempt_paths = ["/api/admin/logs"]
        
        if self.csp_policy is None:
            self.csp_policy = {
                "default-src": "'self'",
                "img-src": "'self' data: https:",
                "script-src": "'self'",
                "style-src": "'self' 'unsafe-inline'",
                "font-src": "'self' https:",
                "object-src": "'none'",
                "connect-src": "'self' https:",
                "frame-src": "'self'",
                "frame-ancestors": "'self'"
            }
            
        if self.cors_origins is None:
            self.cors_origins = ["*"]
            
        if self.cors_allow_methods is None:
            self.cors_allow_methods = ["*"]
            
        if self.cors_allow_headers is None:
            self.cors_allow_headers = ["*"]
    
    @classmethod
    def from_policy(cls, policy_type: SecurityPolicyType) -> "SecurityConfig":
        """
        Belirli bir güvenlik politikasına göre yapılandırma döndürür
        
        Args:
            policy_type: Güvenlik politika türü
            
        Returns:
            SecurityConfig: Güvenlik yapılandırması
        """
        if policy_type == SecurityPolicyType.STRICT:
            return cls(
                csrf_enabled=True,
                csrf_cookie_secure=True,
                csrf_cookie_samesite="Strict",
                xss_protection=True,
                xss_sanitize_inputs=True,
                xss_filter_response=True,
                csp_enabled=True,
                csp_report_only=False,
                security_headers=True,
                hsts_enabled=True,
                cors_origins=["https://example.com"],
                cors_allow_credentials=True
            )
        elif policy_type == SecurityPolicyType.MODERATE:
            return cls(
                csrf_enabled=True,
                csrf_cookie_secure=True,
                csrf_cookie_samesite="Lax",
                xss_protection=True,
                xss_sanitize_inputs=True,
                xss_filter_response=True,
                csp_enabled=True,
                csp_report_only=True,
                security_headers=True,
                cors_origins=["*"],
                cors_allow_credentials=True
            )
        elif policy_type == SecurityPolicyType.RELAXED:
            return cls(
                csrf_enabled=True,
                csrf_cookie_secure=False,
                csrf_cookie_samesite="Lax",
                xss_protection=True,
                xss_sanitize_inputs=False,
                xss_filter_response=False,
                csp_enabled=False,
                security_headers=True,
                cors_origins=["*"],
                cors_allow_credentials=True
            )
        else:
            raise ValueError(f"Unknown policy type: {policy_type}")

class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF koruması için middleware"""
    
    def __init__(self, app, config: SecurityConfig):
        super().__init__(app)
        self.config = config
    
    async def dispatch(self, request: Request, call_next):
        # CSRF koruması devre dışı ise atla
        if not self.config.csrf_enabled:
            return await call_next(request)
        
        # CSRF muaf yolları kontrol et
        if any(request.url.path.startswith(path) for path in self.config.csrf_exempt_paths):
            return await call_next(request)
        
        # CSRF gerektiren HTTP metodlarını kontrol et
        if request.method not in self.config.csrf_methods:
            # CSRF gerektirmeyen metod, token üret ve ayarla
            response = await call_next(request)
            await self._set_csrf_token(request, response)
            return response
        
        # CSRF token kontrolü yap
        csrf_token = self._get_csrf_token(request)
        if not csrf_token:
            # CSRF token bulunamadı
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "CSRF token missing"
                }
            )
        
        # CSRF tokeni doğrula
        if not self._verify_csrf_token(request, csrf_token):
            # CSRF token geçersiz
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "CSRF token invalid"
                }
            )
        
        # CSRF token doğrulandı
        response = await call_next(request)
        
        # Yeni token üret ve ayarla
        await self._set_csrf_token(request, response)
        
        return response
    
    def _get_csrf_token(self, request: Request) -> str:
        """
        İstekten CSRF tokeni alır.
        Önce başlıkta arar, bulamazsa form verilerinde arar.
        
        Args:
            request: HTTP isteği
            
        Returns:
            str: CSRF token veya None
        """
        # Başlıktan token al
        csrf_token = request.headers.get(self.config.csrf_header_name)
        if csrf_token:
            return csrf_token
        
        # Form verilerinden token al
        form_data = None
        try:
            if request.method == "POST":
                form_data = request.form()
                csrf_token = form_data.get("csrf_token")
                if csrf_token:
                    return csrf_token
                    
        except Exception:
            pass
            
        # JSON body'den token al
        json_data = None
        try:
            json_data = request.json()
            csrf_token = json_data.get("csrf_token")
            if csrf_token:
                return csrf_token
                
        except Exception:
            pass
        
        # Son olarak cookie'den token al
        cookies = request.cookies
        csrf_token = cookies.get(self.config.csrf_cookie_name)
        return csrf_token
    
    def _verify_csrf_token(self, request: Request, token: str) -> bool:
        """
        CSRF tokeni doğrular.
        Token, kullanıcı session ID, istemci IP ve zaman damgası ile imzalanır.
        
        Args:
            request: HTTP isteği
            token: Doğrulanacak CSRF token
            
        Returns:
            bool: Geçerli ise True
        """
        try:
            # Base64 decode
            decoded = base64.urlsafe_b64decode(token)
            
            # Token bileşenlerini çıkar
            parts = decoded.split(b":")
            if len(parts) != 3:
                return False
                
            timestamp_bytes, session_ip_hash, signature = parts
            
            # Zaman damgasını kontrol et (24 saatten eski ise reddet)
            timestamp = int(timestamp_bytes.decode("utf-8"))
            now = int(time.time())
            
            if now - timestamp > 86400:  # 24 saat
                return False
            
            # İstemci IP'sini al
            client_ip = request.client.host if request.client else "unknown"
            
            # Session ID'yi al (varsa)
            session_id = ""
            if "session" in request.cookies:
                session_id = request.cookies.get("session", "")
            
            # IP ve session hash'ini hesapla
            expected_ip_hash = self._compute_client_hash(client_ip, session_id)
            
            # IP hash'i kontrol et (IP değişmişse reddet)
            if session_ip_hash != expected_ip_hash:
                return False
            
            # İmzayı doğrula
            data = timestamp_bytes + b":" + session_ip_hash
            expected_signature = self._sign_data(data)
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"CSRF token doğrulama hatası: {e}")
            return False
    
    async def _set_csrf_token(self, request: Request, response: Response) -> None:
        """
        Yanıta yeni CSRF token ekler
        
        Args:
            request: HTTP isteği
            response: HTTP yanıtı
        """
        # Token oluştur
        token = self._generate_csrf_token(request)
        
        # Cookie olarak ayarla
        response.set_cookie(
            key=self.config.csrf_cookie_name,
            value=token,
            httponly=True,
            secure=self.config.csrf_cookie_secure,
            samesite=self.config.csrf_cookie_samesite,
            path=self.config.csrf_cookie_path
        )
        
        # Token'i başlık olarak da ekle (AJAX istekleri için)
        response.headers[self.config.csrf_header_name] = token
    
    def _generate_csrf_token(self, request: Request) -> str:
        """
        Yeni bir CSRF token oluşturur
        
        Args:
            request: HTTP isteği
            
        Returns:
            str: Yeni CSRF token
        """
        # Zaman damgası
        timestamp = str(int(time.time())).encode("utf-8")
        
        # İstemci IP'si ve session ID'si
        client_ip = request.client.host if request.client else "unknown"
        session_id = request.cookies.get("session", "")
        
        # IP ve session hash'i
        ip_hash = self._compute_client_hash(client_ip, session_id)
        
        # İmzalı veri
        data = timestamp + b":" + ip_hash
        signature = self._sign_data(data)
        
        # Token oluştur
        token_bytes = timestamp + b":" + ip_hash + b":" + signature
        token = base64.urlsafe_b64encode(token_bytes).decode("utf-8")
        
        return token
    
    def _compute_client_hash(self, client_ip: str, session_id: str) -> bytes:
        """
        İstemci IP'si ve session ID'sinden hash oluşturur
        
        Args:
            client_ip: İstemci IP adresi
            session_id: Oturum ID'si
            
        Returns:
            bytes: Hash değeri
        """
        data = (client_ip + session_id).encode("utf-8")
        return hashlib.sha256(data).digest()[:16]  # 16 byte hash
    
    def _sign_data(self, data: bytes) -> bytes:
        """
        Veriyi HMAC ile imzalar
        
        Args:
            data: İmzalanacak veri
            
        Returns:
            bytes: İmza
        """
        key = self.config.csrf_secret_key.encode("utf-8")
        return hmac.new(key, data, digestmod=hashlib.sha256).digest()

class XSSProtectionMiddleware(BaseHTTPMiddleware):
    """XSS koruması için middleware"""
    
    def __init__(self, app, config: SecurityConfig):
        super().__init__(app)
        self.config = config
        
        # XSS temizleme için regex kalıpları
        self.xss_patterns = [
            re.compile(r"<script.*?>.*?</script>", re.I | re.S),
            re.compile(r"javascript:", re.I),
            re.compile(r"on\w+\s*=", re.I),
            re.compile(r"<iframe.*?>.*?</iframe>", re.I | re.S),
            re.compile(r"<object.*?>.*?</object>", re.I | re.S),
            re.compile(r"<embed.*?>.*?</embed>", re.I | re.S)
        ]
    
    async def dispatch(self, request: Request, call_next):
        # XSS koruması devre dışı ise atla
        if not self.config.xss_protection:
            return await call_next(request)
        
        # Muaf yolları kontrol et
        if any(request.url.path.startswith(path) for path in self.config.xss_filter_exempt_paths):
            return await call_next(request)
        
        # Girdi temizleme
        if self.config.xss_sanitize_inputs:
            await self._sanitize_request(request)
        
        # İstek işleme
        response = await call_next(request)
        
        # Çıktı filtreleme
        if self.config.xss_filter_response:
            response = self._filter_response(response)
        
        # XSS koruması başlıkları
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        return response
    
    async def _sanitize_request(self, request: Request) -> None:
        """
        İstek verilerini XSS saldırılarına karşı temizler
        
        Args:
            request: HTTP isteği
        """
        # Query parametreleri
        query_params = dict(request.query_params)
        for key, value in query_params.items():
            if isinstance(value, str):
                request.scope["query_string"] = urllib.parse.urlencode(
                    {**query_params, key: self._sanitize_string(value)}
                ).encode()
        
        # Form verileri
        if request.method == "POST" and request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded"):
            try:
                form_data = await request.form()
                sanitized_form = {}
                for key, value in form_data.items():
                    if isinstance(value, str):
                        sanitized_form[key] = self._sanitize_string(value)
                    else:
                        sanitized_form[key] = value
                
                # Sanitized form verilerini enjekte et
                # Not: Bu FastAPI'nin iç implementasyonuna bağlıdır
                setattr(request, "_form", sanitized_form)
            except Exception:
                pass
        
        # JSON body
        if request.headers.get("content-type", "").startswith("application/json"):
            try:
                body = await request.json()
                if isinstance(body, dict):
                    sanitized_body = self._sanitize_data(body)
                    
                    # Sanitized JSON verilerini enjekte et
                    # Not: Bu FastAPI'nin iç implementasyonuna bağlıdır
                    setattr(request, "_json", sanitized_body)
            except Exception:
                pass
    
    def _sanitize_data(self, data: typing.Any) -> typing.Any:
        """
        Veriyi recursive olarak sanitize eder
        
        Args:
            data: Sanitize edilecek veri
            
        Returns:
            Any: Sanitize edilmiş veri
        """
        if isinstance(data, str):
            return self._sanitize_string(data)
        elif isinstance(data, dict):
            return {k: self._sanitize_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        else:
            return data
    
    def _sanitize_string(self, value: str) -> str:
        """
        String'i XSS saldırılarına karşı temizler
        
        Args:
            value: Temizlenecek string
            
        Returns:
            str: Temizlenmiş string
        """
        # Basit HTML escape
        value = html.escape(value)
        
        # Tehlikeli kalıpları temizle
        for pattern in self.xss_patterns:
            value = pattern.sub("", value)
            
        return value
    
    def _filter_response(self, response: Response) -> Response:
        """
        Yanıt içeriğini XSS saldırılarına karşı filtreler
        
        Args:
            response: HTTP yanıtı
            
        Returns:
            Response: Filtrelenmiş yanıt
        """
        # Sadece JSON yanıtlarını filtrele
        if response.headers.get("content-type", "").startswith("application/json"):
            try:
                # Yanıt içeriğini al
                body = response.body
                if not body:
                    return response
                    
                content = json.loads(body)
                
                # İçeriği sanitize et
                sanitized_content = self._sanitize_data(content)
                
                # Yanıtı güncelle
                response.body = json.dumps(sanitized_content).encode()
                response.headers["content-length"] = str(len(response.body))
            except Exception:
                pass
                
        return response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Güvenlik başlıkları için middleware"""
    
    def __init__(self, app, config: SecurityConfig):
        super().__init__(app)
        self.config = config
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        if not self.config.security_headers:
            return response
        
        # Content-Security-Policy
        if self.config.csp_enabled:
            csp_value = self._build_csp_header()
            header_name = "Content-Security-Policy-Report-Only" if self.config.csp_report_only else "Content-Security-Policy"
            response.headers[header_name] = csp_value
        
        # HTTP Strict-Transport-Security
        if self.config.hsts_enabled:
            hsts_value = f"max-age={self.config.hsts_max_age}; includeSubDomains; preload"
            response.headers["Strict-Transport-Security"] = hsts_value
        
        # Referrer-Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions-Policy
        response.headers["Permissions-Policy"] = "geolocation=(self), microphone=(), camera=(), accelerometer=()"
        
        # Frame options
        response.headers["X-Frame-Options"] = "DENY"
        
        return response
    
    def _build_csp_header(self) -> str:
        """
        Content-Security-Policy başlığı oluşturur
        
        Returns:
            str: CSP başlık değeri
        """
        csp_parts = []
        
        for directive, value in self.config.csp_policy.items():
            csp_parts.append(f"{directive} {value}")
        
        if self.config.csp_report_uri:
            csp_parts.append(f"report-uri {self.config.csp_report_uri}")
        
        return "; ".join(csp_parts)

def setup_security_middleware(app: FastAPI, config: SecurityConfig = None) -> FastAPI:
    """
    FastAPI uygulamasına güvenlik middleware'lerini ekler
    
    Args:
        app: FastAPI uygulaması
        config: Güvenlik yapılandırması
        
    Returns:
        FastAPI: Middleware'ler eklenmiş uygulama
    """
    # Varsayılan yapılandırma
    if config is None:
        config = SecurityConfig()
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=config.cors_allow_credentials,
        allow_methods=config.cors_allow_methods,
        allow_headers=config.cors_allow_headers
    )
    
    # Güvenlik başlıkları
    app.add_middleware(SecurityHeadersMiddleware, config=config)
    
    # XSS koruması
    app.add_middleware(XSSProtectionMiddleware, config=config)
    
    # CSRF koruması
    app.add_middleware(CSRFMiddleware, config=config)
    
    return app