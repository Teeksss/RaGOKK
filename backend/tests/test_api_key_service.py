# Last reviewed: 2025-04-29 10:59:14 UTC (User: Teekssseksiklikleri)
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from ..services.api_key_service import ApiKeyService
from ..models.api_key_models import ApiProvider
from ..repositories.api_key_repository import ApiKeyRepository
from ..repositories.security_log_repository import SecurityLogRepository
from ..utils.api_verification import ApiKeyVerifier
from ..services.notification_service import NotificationService

@pytest.fixture
def api_key_service():
    with patch('backend.services.api_key_service.ApiKeyRepository') as mock_repo:
        with patch('backend.services.api_key_service.SecurityLogRepository') as mock_sec_repo:
            service = ApiKeyService()
            # Repository mock'larını hizmet örneğine ata
            service.repository = mock_repo()
            service.security_log_repo = mock_sec_repo()
            yield service

@pytest.mark.asyncio
async def test_get_api_key_with_cache(api_key_service):
    """Önbellekten API anahtarı alma testi"""
    # Önbelleğe test verisi ekle
    api_key_service._cache["test_provider"] = {
        "key": "test-key-from-cache",
        "expires_at": datetime.datetime.now().timestamp() + 300  # 5 dakika sonra sona erecek
    }
    
    # Mock veritabanı session'ı
    mock_db = AsyncMock(spec=AsyncSession)
    
    # Anahtarı getir (önbellekten gelmeli)
    key = await api_key_service.get_api_key(mock_db, "test_provider")
    
    # Beklenen sonuç
    assert key == "test-key-from-cache"
    # Repository'den getirmedi, önbellekten aldı
    api_key_service.repository.get_key_by_provider.assert_not_called()

@pytest.mark.asyncio
async def test_get_api_key_from_db(api_key_service):
    """Veritabanından API anahtarı alma testi"""
    # Mock veritabanı session'ı
    mock_db = AsyncMock(spec=AsyncSession)
    
    # Mock API anahtarı
    mock_key = MagicMock()
    mock_key.api_key = "encrypted-key"
    mock_key.is_active = True
    
    # get_key_by_provider metodunu mock'la
    api_key_service.repository.get_key_by_provider.return_value = mock_key
    
    # decrypt_value fonksiyonunu mock'la
    with patch('backend.services.api_key_service.decrypt_value', return_value="decrypted-key"):
        # Anahtarı getir (veritabanından gelmeli)
        key = await api_key_service.get_api_key(mock_db, ApiProvider.OPENAI, use_cache=False)
        
        # Beklenen sonuç
        assert key == "decrypted-key"
        api_key_service.repository.get_key_by_provider.assert_called_with(mock_db, ApiProvider.OPENAI)
        api_key_service.repository.update_last_used.assert_called_once()

@pytest.mark.asyncio
async def test_clear_cache(api_key_service):
    """Önbellek temizleme testi"""
    # Önbelleğe test verileri ekle
    api_key_service._cache = {
        "provider1": {"key": "key1", "expires_at": 12345},
        "provider2": {"key": "key2", "expires_at": 12345}
    }
    
    # Belirli bir sağlayıcı için önbelleği temizle
    await api_key_service.clear_cache("provider1")
    
    # provider1 temizlendi, provider2 duruyor mu?
    assert "provider1" not in api_key_service._cache
    assert "provider2" in api_key_service._cache
    
    # Tüm önbelleği temizle
    await api_key_service.clear_cache()
    
    # Tüm önbellek temizlendi mi?
    assert len(api_key_service._cache) == 0

@pytest.mark.asyncio
async def test_is_api_key_valid(api_key_service):
    """API anahtarı geçerlilik kontrolü testi"""
    # Mock veritabanı session'ı
    mock_db = AsyncMock(spec=AsyncSession)
    
    # Test case 1: Geçerli anahtar
    mock_key_valid = MagicMock()
    mock_key_valid.is_active = True
    mock_key_valid.api_key = "encrypted-key"
    
    api_key_service.repository.get_key_by_provider.return_value = mock_key_valid
    
    # Anahtar geçerli
    is_valid = await api_key_service.is_api_key_valid(mock_db, "test_provider")
    assert is_valid == True
    
    # Test case 2: Geçersiz anahtar (devre dışı)
    mock_key_inactive = MagicMock()
    mock_key_inactive.is_active = False
    mock_key_inactive.api_key = "encrypted-key"
    
    api_key_service.repository.get_key_by_provider.return_value = mock_key_inactive
    
    # Anahtar devre dışı
    is_valid = await api_key_service.is_api_key_valid(mock_db, "test_provider")
    assert is_valid == False
    
    # Test case 3: Anahtar yok
    api_key_service.repository.get_key_by_provider.return_value = None
    
    # Anahtar yok
    is_valid = await api_key_service.is_api_key_valid(mock_db, "non_existent_provider")
    assert is_valid == False

@pytest.mark.asyncio
async def test_verify_api_key(api_key_service):
    """API anahtarı doğrulama testi"""
    # Mock veritabanı session'ı
    mock_db = AsyncMock(spec=AsyncSession)
    
    # Mock API anahtarı
    mock_key = MagicMock()
    mock_key.api_key = "encrypted-key"
    mock_key.is_active = True
    
    # get_key_by_provider metodunu mock'la
    api_key_service.repository.get_key_by_provider.return_value = mock_key
    
    # decrypt_value fonksiyonunu mock'la
    with patch('backend.services.api_key_service.decrypt_value', return_value="decrypted-key"):
        # api_key_verifier.verify_key metodunu mock'la
        with patch('backend.utils.api_verification.api_key_verifier.verify_key') as mock_verify:
            # Başarılı doğrulama sonucu
            mock_verify.return_value = {
                "is_valid": True,
                "message": "API anahtarı geçerli",
                "provider": "test_provider",
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
            
            # Anahtarı doğrula
            result = await api_key_service.verify_api_key(mock_db, "test_provider")
            
            # Beklenen sonuç
            assert result["is_valid"] == True
            assert result["message"] == "API anahtarı geçerli"
            mock_verify.assert_called_once()

@pytest.mark.asyncio
async def test_log_api_key_access(api_key_service):
    """API anahtarı erişim loglama testi"""
    # Mock veritabanı session'ı
    mock_db = AsyncMock(spec=AsyncSession)
    
    # _log_api_key_access metodunu çağır
    await api_key_service._log_api_key_access(
        db=mock_db,
        provider="test_provider",
        user_id="test_user",
        action="access",
        success=True,
        details={"source": "cache"}
    )
    
    # SecurityLogRepository'nin create_log metodu doğru parametrelerle çağrıldı mı?
    api_key_service.security_log_repo.create_log.assert_called_with(
        db=mock_db,
        log_type="api_key",
        action="access",
        user_id="test_user",
        resource_type="provider",
        resource_id="test_provider",
        ip_address=None,
        user_agent=None,
        details={"source": "cache"},
        success=True,
        severity="info"
    )

@pytest.mark.asyncio
async def test_create_api_key(api_key_service):
    """API anahtarı oluşturma testi"""
    # Mock veritabanı session'ı
    mock_db = AsyncMock(spec=AsyncSession)
    
    # Notification service mock
    with patch('backend.services.api_key_service.notification_service.notify_api_key_change') as mock_notify:
        mock_notify.return_value = True
        
        # Repository'nin create_key metodunu mock'la
        mock_created_key = MagicMock()
        api_key_service.repository.create_key.return_value = mock_created_key
        
        # API anahtarı oluştur
        result = await api_key_service.create_api_key(
            db=mock_db,
            provider="test_provider",
            api_key="test-key",
            description="Test key",
            user_id="test_user"
        )
        
        # Beklenen sonuç
        assert result == mock_created_key
        api_key_service.repository.create_key.assert_called_once()
        mock_notify.assert_called_once()