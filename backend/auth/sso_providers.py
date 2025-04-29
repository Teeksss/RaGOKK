# Last reviewed: 2025-04-29 13:23:09 UTC (User: TeeksssSSO)
from enum import Enum
from typing import Dict, Any, Optional, List, Union
import logging
import json
import base64
import httpx
import time
from urllib.parse import urlencode
import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.x509 import load_pem_x509_certificate

from ..config import settings
from ..services.cache_service import CacheService

logger = logging.getLogger(__name__)

class SSOProviderType(str, Enum):
    """SSO sağlayıcı türleri"""
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    GITHUB = "github"
    OKTA = "okta"
    AUTH0 = "auth0"
    CUSTOM = "custom"
    SAML = "saml"

class SSOProvider:
    """
    SSO sağlayıcısı için temel sınıf
    
    OAuth2, OpenID Connect ve SAML protokollerini destekler.
    Tüm SSO sağlayıcıları bu temel sınıfı kullanmalıdır.
    """
    
    def __init__(
        self,
        provider_type: SSOProviderType,
        client_id: str,
        client_secret: str,
        name: str = None,
        icon: str = None,
        enabled: bool = True,
        scopes: List[str] = None,
        config: Dict[str, Any] = None
    ):
        """
        Args:
            provider_type: Sağlayıcı türü
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            name: Sağlayıcı görünen adı
            icon: Sağlayıcı ikon URL'si
            enabled: Sağlayıcının etkin olup olmadığı
            scopes: İstenecek izin kapsamları
            config: Ek yapılandırma seçenekleri
        """
        self.provider_type = provider_type
        self.client_id = client_id
        self.client_secret = client_secret
        self.name = name or provider_type.value.title()
        self.icon = icon
        self.enabled = enabled
        self.scopes = scopes or ["openid", "email", "profile"]
        self.config = config or {}
        self.cache = CacheService()
    
    async def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        """
        Yetkilendirme URL'sini oluşturur
        
        Args:
            redirect_uri: Yönlendirme URI'si
            state: CSRF koruma için durum
            
        Returns:
            str: Yetkilendirme URL'si
        """
        raise NotImplementedError("Subclasses must implement get_authorization_url")
    
    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Yetkilendirme kodunu token'a dönüştürür
        
        Args:
            code: Yetkilendirme kodu
            redirect_uri: Kullanılan yönlendirme URI'si
            
        Returns:
            Dict[str, Any]: Token bilgileri
        """
        raise NotImplementedError("Subclasses must implement exchange_code_for_token")
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Token'ı doğrular ve kullanıcı bilgilerini alır
        
        Args:
            token: Doğrulanacak token
            
        Returns:
            Dict[str, Any]: Doğrulanmış kullanıcı bilgileri
        """
        raise NotImplementedError("Subclasses must implement validate_token")
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Kullanıcı bilgilerini alır
        
        Args:
            access_token: Access token
            
        Returns:
            Dict[str, Any]: Kullanıcı bilgileri
        """
        raise NotImplementedError("Subclasses must implement get_user_info")
    
    def get_icon_html(self) -> str:
        """
        HTML formatında provider ikonunu döndürür
        
        Returns:
            str: Icon HTML
        """
        if not self.icon:
            return f'<i class="fas fa-sign-in-alt"></i>'
        
        if self.icon.startswith('fa-'):
            return f'<i class="fab {self.icon}"></i>'
        
        return f'<img src="{self.icon}" alt="{self.name}" class="sso-icon" />'
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Sağlayıcı bilgilerini sözlük olarak döndürür
        
        Returns:
            Dict[str, Any]: Sağlayıcı bilgileri
        """
        return {
            "provider_type": self.provider_type,
            "name": self.name,
            "icon": self.icon,
            "enabled": self.enabled
        }


class GoogleSSOProvider(SSOProvider):
    """Google OAuth2 / OpenID Connect sağlayıcısı"""
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        name: str = "Google",
        icon: str = "fa-google",
        enabled: bool = True,
        scopes: List[str] = None,
        config: Dict[str, Any] = None
    ):
        super().__init__(
            provider_type=SSOProviderType.GOOGLE,
            client_id=client_id,
            client_secret=client_secret,
            name=name,
            icon=icon,
            enabled=enabled,
            scopes=scopes or ["openid", "email", "profile"],
            config=config
        )
        self.authorization_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_endpoint = "https://oauth2.googleapis.com/token"
        self.jwks_uri = "https://www.googleapis.com/oauth2/v3/certs"
        self.userinfo_endpoint = "https://openidconnect.googleapis.com/v1/userinfo"
    
    async def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        """Google yetkilendirme URL'sini oluştur"""
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "access_type": "offline",
            "prompt": "consent"
        }
        
        if state:
            params["state"] = state
        
        return f"{self.authorization_endpoint}?{urlencode(params)}"
    
    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Google yetkilendirme kodunu token'a dönüştür"""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(self.token_endpoint, data=data)
            response.raise_for_status()
            return response.json()
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """ID token'ı doğrula"""
        try:
            # JWKS anahtarlarını al (önbellekten veya Google'dan)
            jwks = await self._get_jwks()
            
            # JWT header'ını çözümle
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            
            if not kid or not jwks:
                raise ValueError("Invalid token or JWKS data")
            
            # Token için uygun anahtarı bul
            key = None
            for jwk in jwks.get("keys", []):
                if jwk.get("kid") == kid:
                    key = jwk
                    break
            
            if not key:
                raise ValueError(f"Key ID {kid} not found in JWKS")
            
            # Google'ın public key'ini kullanarak token'ı doğrula
            cert = key.get("x5c")[0]
            cert_obj = load_pem_x509_certificate(
                f"-----BEGIN CERTIFICATE-----\n{cert}\n-----END CERTIFICATE-----".encode(),
                default_backend()
            )
            public_key = cert_obj.public_key()
            
            # Token'ı doğrula
            decoded = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=self.client_id,
                options={"verify_exp": True}
            )
            
            return decoded
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise ValueError(f"Invalid token: {str(e)}")
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Access token ile kullanıcı bilgilerini al"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return response.json()
    
    async def _get_jwks(self) -> Dict[str, Any]:
        """JWK anahtarlarını önbellekten veya Google'dan al"""
        cache_key = f"google_jwks"
        jwks = await self.cache.get(cache_key)
        
        if not jwks:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.jwks_uri)
                response.raise_for_status()
                jwks = response.json()
                
                # 12 saat önbellekle (Google anahtarları rotasyona tabi)
                await self.cache.set(cache_key, jwks, ttl=60 * 60 * 12)
        
        return jwks


class MicrosoftSSOProvider(SSOProvider):
    """Microsoft Azure AD sağlayıcısı"""
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        tenant_id: str = "common",
        name: str = "Microsoft",
        icon: str = "fa-microsoft",
        enabled: bool = True,
        scopes: List[str] = None,
        config: Dict[str, Any] = None
    ):
        super().__init__(
            provider_type=SSOProviderType.MICROSOFT,
            client_id=client_id,
            client_secret=client_secret,
            name=name,
            icon=icon,
            enabled=enabled,
            scopes=scopes or ["openid", "email", "profile", "User.Read"],
            config=config
        )
        self.tenant_id = tenant_id
        self.authorization_endpoint = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
        self.token_endpoint = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        self.jwks_uri = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
        self.userinfo_endpoint = "https://graph.microsoft.com/v1.0/me"
    
    async def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        """Microsoft yetkilendirme URL'sini oluştur"""
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "response_mode": "query"
        }
        
        if state:
            params["state"] = state
        
        return f"{self.authorization_endpoint}?{urlencode(params)}"
    
    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Microsoft yetkilendirme kodunu token'a dönüştür"""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(self.token_endpoint, data=data)
            response.raise_for_status()
            return response.json()
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """ID token'ı doğrula"""
        try:
            # JWKS anahtarlarını al (önbellekten veya Microsoft'tan)
            jwks = await self._get_jwks()
            
            # JWT header'ını çözümle
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            
            if not kid or not jwks:
                raise ValueError("Invalid token or JWKS data")
            
            # Token için uygun anahtarı bul
            key = None
            for jwk in jwks.get("keys", []):
                if jwk.get("kid") == kid:
                    key = jwk
                    break
            
            if not key:
                raise ValueError(f"Key ID {kid} not found in JWKS")
            
            # Microsoft'un public key'ini oluştur
            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
            
            # Token'ı doğrula
            decoded = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=self.client_id,
                options={"verify_exp": True}
            )
            
            return decoded
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise ValueError(f"Invalid token: {str(e)}")
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Access token ile kullanıcı bilgilerini al"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return response.json()
    
    async def _get_jwks(self) -> Dict[str, Any]:
        """JWK anahtarlarını önbellekten veya Microsoft'tan al"""
        cache_key = f"microsoft_jwks_{self.tenant_id}"
        jwks = await self.cache.get(cache_key)
        
        if not jwks:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.jwks_uri)
                response.raise_for_status()
                jwks = response.json()
                
                # 24 saat önbellekle
                await self.cache.set(cache_key, jwks, ttl=60 * 60 * 24)
        
        return jwks


class SAMLProvider(SSOProvider):
    """SAML 2.0 sağlayıcısı"""
    
    def __init__(
        self,
        entity_id: str,
        acs_url: str,
        idp_metadata_url: str = None,
        idp_metadata_xml: str = None,
        name: str = "Enterprise SSO",
        icon: str = "fa-building",
        enabled: bool = True,
        config: Dict[str, Any] = None
    ):
        super().__init__(
            provider_type=SSOProviderType.SAML,
            client_id=entity_id,  # entity_id client_id olarak kullanılır
            client_secret="",  # SAML için gerekli değil
            name=name,
            icon=icon,
            enabled=enabled,
            scopes=[],  # SAML için kullanılmaz
            config=config
        )
        self.entity_id = entity_id  # Service Provider Entity ID
        self.acs_url = acs_url  # Assertion Consumer Service URL
        self.idp_metadata_url = idp_metadata_url  # IdP metadata URL
        self.idp_metadata_xml = idp_metadata_xml  # IdP metadata XML
        
        # Python-SAML kütüphanesini kullanıyoruz (OneLogin'in SAML kütüphanesi)
        try:
            from onelogin.saml2.auth import OneLogin_Saml2_Auth
            from onelogin.saml2.settings import OneLogin_Saml2_Settings
            from onelogin.saml2.idp_metadata_parser import OneLogin_Saml2_IdPMetadataParser
            
            self.saml2_auth = OneLogin_Saml2_Auth
            self.saml2_settings = OneLogin_Saml2_Settings
            self.idp_metadata_parser = OneLogin_Saml2_IdPMetadataParser
        except ImportError:
            logger.error("python3-saml package is not installed. SAML functionality will not work.")
    
    async def get_idp_metadata(self) -> Dict[str, Any]:
        """IdP metadata bilgisini al"""
        # Önbellekten kontrol et
        cache_key = f"saml_idp_metadata_{self.entity_id}"
        metadata = await self.cache.get(cache_key)
        
        if metadata:
            return metadata
        
        # Metadata URL'den alınacak
        if self.idp_metadata_url:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(self.idp_metadata_url)
                    response.raise_for_status()
                    metadata_xml = response.text
                    
                    idp_data = self.idp_metadata_parser.parse(metadata_xml)
                    
                    # 24 saat önbellekle
                    await self.cache.set(cache_key, idp_data, ttl=60 * 60 * 24)
                    
                    return idp_data
            except Exception as e:
                logger.error(f"Error fetching IdP metadata from URL: {e}")
                raise ValueError(f"Could not fetch IdP metadata: {str(e)}")
        
        # Metadata XML string olarak verilmiş
        elif self.idp_metadata_xml:
            try:
                idp_data = self.idp_metadata_parser.parse(self.idp_metadata_xml)
                
                # 24 saat önbellekle
                await self.cache.set(cache_key, idp_data, ttl=60 * 60 * 24)
                
                return idp_data
            except Exception as e:
                logger.error(f"Error parsing IdP metadata XML: {e}")
                raise ValueError(f"Could not parse IdP metadata: {str(e)}")
        
        # Metadata yok
        else:
            raise ValueError("No IdP metadata provided")
    
    async def get_saml_settings(self, request_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """SAML ayarlarını oluştur"""
        idp_data = await self.get_idp_metadata()
        
        # SP (Service Provider) ve IdP (Identity Provider) ayarları
        settings = {
            "strict": True,
            "debug": settings.DEBUG,
            "sp": {
                "entityId": self.entity_id,
                "assertionConsumerService": {
                    "url": self.acs_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                },
                "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
            },
            "idp": idp_data["idp"]
        }
        
        # İmzalama ve şifreleme ayarları
        if self.config.get("sign_request", False):
            sp_cert = self.config.get("sp_cert")
            sp_key = self.config.get("sp_key")
            
            if sp_cert and sp_key:
                settings["sp"]["x509cert"] = sp_cert
                settings["sp"]["privateKey"] = sp_key
            else:
                logger.warning("Request signing enabled but no SP certificate/key provided")
        
        # Ek ayarlar
        settings.update(self.config.get("saml_settings", {}))
        
        return settings
    
    async def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        """
        SAML AuthnRequest için yönlendirme URL'si oluştur
        
        Not: SAML için bu fonksiyon doğrudan SSO başlatma URL'sini döndürür
        """
        # SAML için bu sadece bir yer tutucu - gerçek uygulamada Flask/Django gibi
        # bir web framework kullanarak request ve response context'i gerekli
        if not hasattr(self, "saml2_auth"):
            raise NotImplementedError("python3-saml is not available")
        
        # Dummy request data - tam implementasyon için web framework'e özgü request veri yapısı gerekli
        request_data = {
            "https": "on",
            "http_host": redirect_uri.split("//")[1].split("/")[0],
            "script_name": "/",
            "get_data": {},
            "post_data": {}
        }
        
        if state:
            request_data["get_data"]["state"] = state
        
        settings_dict = await self.get_saml_settings(request_data)
        auth = self.saml2_auth(request_data, settings_dict)
        
        return auth.login()
    
    async def process_saml_response(self, saml_response: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        SAML Response işleme
        
        Args:
            saml_response: IdP'den gelen SAML yanıtı
            request_data: HTTP istek verisi
            
        Returns:
            Dict[str, Any]: Kullanıcı bilgileri
        """
        if not hasattr(self, "saml2_auth"):
            raise NotImplementedError("python3-saml is not available")
        
        try:
            settings_dict = await self.get_saml_settings(request_data)
            auth = self.saml2_auth(request_data, settings_dict)
            
            # SAML yanıtını işle
            auth.process_response(saml_response)
            
            # Yanıt geçerli mi kontrol et
            errors = auth.get_errors()
            if errors:
                error_msg = auth.get_last_error_reason()
                logger.error(f"SAML Response error: {error_msg}")
                raise ValueError(f"SAML validation failed: {error_msg}")
            
            if not auth.is_authenticated():
                raise ValueError("SAML authentication failed")
            
            # Kullanıcı bilgilerini al
            attributes = auth.get_attributes()
            name_id = auth.get_nameid()
            session_index = auth.get_session_index()
            
            # Standart kullanıcı bilgileri formatına dönüştür
            user_info = {
                "id": name_id,
                "session_index": session_index,
                "attributes": attributes
            }
            
            # E-posta ve ad gibi yaygın alanları çıkar
            if "urn:oid:0.9.2342.19200300.100.1.3" in attributes:
                user_info["email"] = attributes["urn:oid:0.9.2342.19200300.100.1.3"][0]
            elif "email" in attributes:
                user_info["email"] = attributes["email"][0]
                
            if "urn:oid:2.5.4.42" in attributes and "urn:oid:2.5.4.4" in attributes:
                user_info["name"] = f"{attributes['urn:oid:2.5.4.42'][0]} {attributes['urn:oid:2.5.4.4'][0]}"
            elif "firstName" in attributes and "lastName" in attributes:
                user_info["name"] = f"{attributes['firstName'][0]} {attributes['lastName'][0]}"
            elif "displayName" in attributes:
                user_info["name"] = attributes["displayName"][0]
            
            return user_info
            
        except Exception as e:
            logger.error(f"Error processing SAML response: {e}")
            raise ValueError(f"Error processing SAML response: {str(e)}")
    
    # SSO provider interface için gereken diğer metodlar
    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """SAML için kullanılmaz"""
        raise NotImplementedError("Not applicable for SAML")
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """SAML için kullanılmaz"""
        raise NotImplementedError("Not applicable for SAML")
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """SAML için kullanılmaz"""
        raise NotImplementedError("Not applicable for SAML")


def create_sso_provider(provider_config: Dict[str, Any]) -> SSOProvider:
    """
    Yapılandırmadan SSO sağlayıcısı oluşturur
    
    Args:
        provider_config: Sağlayıcı yapılandırması
        
    Returns:
        SSOProvider: Oluşturulan sağlayıcı
    """
    provider_type = provider_config.get("provider_type")
    
    if not provider_type:
        raise ValueError("Provider type not specified")
    
    if provider_type == SSOProviderType.GOOGLE:
        return GoogleSSOProvider(
            client_id=provider_config.get("client_id", ""),
            client_secret=provider_config.get("client_secret", ""),
            name=provider_config.get("name", "Google"),
            icon=provider_config.get("icon", "fa-google"),
            enabled=provider_config.get("enabled", True),
            scopes=provider_config.get("scopes"),
            config=provider_config.get("config", {})
        )
    
    elif provider_type == SSOProviderType.MICROSOFT:
        return MicrosoftSSOProvider(
            client_id=provider_config.get("client_id", ""),
            client_secret=provider_config.get("client_secret", ""),
            tenant_id=provider_config.get("tenant_id", "common"),
            name=provider_config.get("name", "Microsoft"),
            icon=provider_config.get("icon", "fa-microsoft"),
            enabled=provider_config.get("enabled", True),
            scopes=provider_config.get("scopes"),
            config=provider_config.get("config", {})
        )
    
    elif provider_type == SSOProviderType.SAML:
        return SAMLProvider(
            entity_id=provider_config.get("entity_id", ""),
            acs_url=provider_config.get("acs_url", ""),
            idp_metadata_url=provider_config.get("idp_metadata_url"),
            idp_metadata_xml=provider_config.get("idp_metadata_xml"),
            name=provider_config.get("name", "Enterprise SSO"),
            icon=provider_config.get("icon", "fa-building"),
            enabled=provider_config.get("enabled", True),
            config=provider_config.get("config", {})
        )
    
    else:
        raise ValueError(f"Unsupported provider type: {provider_type}")


def load_sso_providers() -> Dict[str, SSOProvider]:
    """
    Yapılandırmadan tüm SSO sağlayıcılarını yükler
    
    Returns:
        Dict[str, SSOProvider]: Sağlayıcı kodu -> sağlayıcı eşlemesi
    """
    providers = {}
    
    # Yapılandırmadan sağlayıcıları al
    provider_configs = settings.SSO_PROVIDERS
    
    for provider_code, provider_config in provider_configs.items():
        # Devre dışı bırakılmış sağlayıcıları atla
        if not provider_config.get("enabled", True):
            continue
            
        try:
            provider = create_sso_provider(provider_config)
            providers[provider_code] = provider
        except Exception as e:
            logger.error(f"Error creating SSO provider {provider_code}: {e}")
    
    return providers