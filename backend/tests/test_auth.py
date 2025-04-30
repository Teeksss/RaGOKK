# Last reviewed: 2025-04-30 07:34:44 UTC (User: Teeksss)
import pytest
import os
import sys
from datetime import datetime, timedelta
from fastapi import HTTPException
import jwt
from unittest.mock import patch, MagicMock, AsyncMock

# Proje dizinini Python modül yoluna ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.auth.enhanced_jwt import EnhancedJWTHandler
from backend.models.user import User


# Test için mock kullanıcı nesnesi
@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = "test-user-id"
    user.email = "test@example.com"
    user.roles = ["user"]
    user.organization_id = "test-org-id"
    user.metadata = {"permissions": ["test:permission"]}
    user.is_active = True
    user.password = "$2b$12$TestHashedPassword"  # bcrypt hash
    return user


# Test fixture
@pytest.fixture
def user_data():
    return {
        "sub": "test-user-id",
        "email": "test@example.com",
        "roles": ["user"],
        "organization_id": "test-org-id",
        "permissions": ["test:permission"]
    }


# JWT token oluşturma testi
def test_create_access_token(user_data):
    # Access token oluştur
    token_data = EnhancedJWTHandler.create_access_token(user_data)

    # Sonuçları kontrol et
    assert "token" in token_data
    assert token_data["token_type"] == "access"
    assert "expires_at" in token_data

    # Token çözümleme
    payload = jwt.decode(
        token_data["token"], 
        EnhancedJWTHandler.SECRET_KEY, 
        algorithms=[EnhancedJWTHandler.ALGORITHM]
    )
    
    # Payload kontrolü
    assert payload["sub"] == user_data["sub"]
    assert payload["email"] == user_data["email"]
    assert payload["type"] == "access"
    assert "exp" in payload
    assert "iat" in payload
    assert "jti" in payload


# Refresh token oluşturma testi
def test_create_refresh_token(user_data):
    # Sadece sub bilgisiyle token
    sub_only = {"sub": user_data["sub"]}
    token_data = EnhancedJWTHandler.create_refresh_token(sub_only)
    
    assert "token" in token_data
    assert token_data["token_type"] == "refresh"
    
    # Token çözümleme
    payload = jwt.decode(
        token_data["token"], 
        EnhancedJWTHandler.SECRET_KEY, 
        algorithms=[EnhancedJWTHandler.ALGORITHM]
    )
    
    # Payload kontrolü
    assert payload["sub"] == user_data["sub"]
    assert payload["type"] == "refresh"
    assert "email" not in payload


# Token süresi testi
def test_token_expiration(user_data):
    # Kısa süreli token
    expires = timedelta(seconds=1)
    token_data = EnhancedJWTHandler.create_access_token(user_data, expires)
    
    # Token çözümleyebilmeli
    payload = jwt.decode(
        token_data["token"], 
        EnhancedJWTHandler.SECRET_KEY, 
        algorithms=[EnhancedJWTHandler.ALGORITHM]
    )
    assert payload["sub"] == user_data["sub"]
    
    # 2 saniye bekle
    import time
    time.sleep(2)
    
    # Artık süresi dolmuş olmalı
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(
            token_data["token"], 
            EnhancedJWTHandler.SECRET_KEY, 
            algorithms=[EnhancedJWTHandler.ALGORITHM]
        )


# Token doğrulama testi
def test_decode_token(user_data):
    # Token oluştur
    token_data = EnhancedJWTHandler.create_access_token(user_data)
    
    # Redis bağlantısını mock'la
    with patch('backend.auth.enhanced_jwt.redis_client', None):
        # Token çözümleme
        payload = EnhancedJWTHandler.decode_token(token_data["token"])
        
        # Payload kontrolü
        assert payload["sub"] == user_data["sub"]
        assert payload["email"] == user_data["email"]
        assert payload["type"] == "access"


# Geçersiz token testi
def test_invalid_token():
    # Geçersiz token
    invalid_token = "invalid.token.string"
    
    # Redis bağlantısını mock'la
    with patch('backend.auth.enhanced_jwt.redis_client', None):
        # Exception bekliyoruz
        with pytest.raises(HTTPException) as excinfo:
            EnhancedJWTHandler.decode_token(invalid_token)
        
        # Hata detaylarını kontrol et
        assert excinfo.value.status_code == 401
        assert "Could not validate credentials" in excinfo.value.detail


# Token blacklist testi
def test_blacklist_token(user_data):
    # Token oluştur
    token_data = EnhancedJWTHandler.create_access_token(user_data)
    token = token_data["token"]
    
    # Redis mock
    redis_mock = MagicMock()
    redis_mock.exists.return_value = 1  # Token blacklist'te
    
    # Redis ve is_token_blacklisted fonksiyonunu mock'la
    with patch('backend.auth.enhanced_jwt.redis_client', redis_mock):
        # Token'ı blacklist'e ekle
        EnhancedJWTHandler.blacklist_token(token)
        
        # Token çözümlemeyi dene
        with pytest.raises(HTTPException) as excinfo:
            payload = jwt.decode(token, EnhancedJWTHandler.SECRET_KEY, algorithms=[EnhancedJWTHandler.ALGORITHM])
            EnhancedJWTHandler.is_token_blacklisted(payload)
            
        # Hata detaylarını kontrol et
        assert excinfo.value.status_code == 401
        assert "Token has been invalidated" in excinfo.value.detail


# Login endpoint testi
@pytest.mark.asyncio
async def test_login_endpoint(mock_user):
    from backend.api.v1.auth import login
    
    # Repository mock
    user_repo_mock = AsyncMock()
    user_repo_mock.get_user_by_email.return_value = mock_user
    
    # Password verify mock
    with patch('backend.api.v1.auth.user_repository', user_repo_mock), \
         patch('backend.api.v1.auth.verify_password', return_value=True), \
         patch('backend.api.v1.auth.EnhancedJWTHandler.setup_token_cookies'):
        
        # Form data mock
        form_data = MagicMock()
        form_data.username = mock_user.email
        form_data.password = "test_password"
        
        # Response mock
        response_mock = MagicMock()
        
        # DB mock
        db_mock = AsyncMock()
        
        # Login fonksiyonunu çağır
        result = await login(form_data, db_mock, response_mock)
        
        # Sonuçları kontrol et
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["token_type"] == "bearer"
        assert "expires_at" in result


# Test fixtures ve gerekli sınıfların yüklenmesi
if __name__ == "__main__":
    print("Running auth tests...")
    pytest.main(["-xvs", __file__])