# Last reviewed: 2025-04-29 10:59:14 UTC (User: Teekssseksiklikleri)
import pytest
import httpx
import asyncio
from unittest.mock import patch, MagicMock
from ..utils.api_verification import ApiKeyVerifier, VerificationLevel, RateLimitInfo

# Sahte API yanıtları için Mock sınıfı
class MockResponse:
    def __init__(self, status_code, json_data=None, headers=None, text=None):
        self.status_code = status_code
        self._json_data = json_data
        self.headers = headers or {}
        self.text = text or ""
    
    def json(self):
        return self._json_data

@pytest.fixture
def api_key_verifier():
    return ApiKeyVerifier()

@pytest.mark.asyncio
async def test_check_key_format():
    """API anahtarı format kontrolü testleri"""
    verifier = ApiKeyVerifier()
    
    # OpenAI - geçerli
    valid, msg = verifier._check_key_format("openai", "sk-1234567890abcdef")
    assert valid == True
    
    # OpenAI - geçersiz
    valid, msg = verifier._check_key_format("openai", "invalid-key")
    assert valid == False
    assert "OpenAI anahtarları" in msg
    
    # HuggingFace - geçerli
    valid, msg = verifier._check_key_format("huggingface", "hf_1234567890abcdef")
    assert valid == True
    
    # HuggingFace - geçersiz
    valid, msg = verifier._check_key_format("huggingface", "invalid-key")
    assert valid == False
    assert "HuggingFace anahtarları" in msg
    
    # Çok kısa anahtar
    valid, msg = verifier._check_key_format("openai", "sk-123")
    assert valid == False
    assert "çok kısa" in msg

@pytest.mark.asyncio
async def test_verify_key_with_cache():
    """Cache mekanizması testi"""
    verifier = ApiKeyVerifier()
    
    # Cache'e test verisi ekle
    test_result = {
        "is_valid": True,
        "message": "API anahtarı geçerli",
        "provider": "test_provider",
        "timestamp": "2023-01-01T00:00:00"
    }
    
    verifier.cache["test_provider:test_key"] = {
        "result": test_result,
        "timestamp": asyncio.get_running_loop().time()
    }
    
    # Cache'den oku
    result = await verifier.verify_key("test_provider", "test_key")
    assert result == test_result
    assert result["is_valid"] == True
    
    # Cache kullanmadan doğrula
    with patch.object(verifier, '_verify_provider_key') as mock_verify:
        mock_verify.return_value = {"is_valid": False, "message": "Test"}
        result = await verifier.verify_key("test_provider", "test_key", use_cache=False)
        assert result["is_valid"] == False
        assert mock_verify.called

@pytest.mark.asyncio
async def test_extract_rate_limits():
    """HTTP rate limit header extraction testi"""
    verifier = ApiKeyVerifier()
    
    # OpenAI rate limit headers
    headers = {
        "x-ratelimit-limit-requests": "100",
        "x-ratelimit-remaining-requests": "90",
        "x-ratelimit-reset-requests": "60"
    }
    
    rate_info = verifier._extract_rate_limits(headers)
    assert rate_info.limit == 100
    assert rate_info.remaining == 90
    assert rate_info.reset == 60
    
    # Cohere rate limit headers
    headers = {
        "x-ratelimit-limit": "50",
        "x-ratelimit-remaining": "45",
        "x-ratelimit-reset": "120"
    }
    
    rate_info = verifier._extract_rate_limits(headers)
    assert rate_info.limit == 50
    assert rate_info.remaining == 45
    assert rate_info.reset == 120
    
    # Geçersiz headers
    headers = {"unrelated": "value"}
    rate_info = verifier._extract_rate_limits(headers)
    assert rate_info.limit == 0
    assert rate_info.remaining == 0

@pytest.mark.asyncio
async def test_verify_openai():
    """OpenAI API doğrulama testi"""
    verifier = ApiKeyVerifier()
    
    # Başarılı durum
    with patch('httpx.AsyncClient.get') as mock_get:
        # Mock response oluştur
        mock_response = MockResponse(
            200, 
            {
                "data": [
                    {"id": "gpt-3.5-turbo"},
                    {"id": "gpt-4"},
                ]
            },
            {"x-ratelimit-limit-requests": "100"}
        )
        mock_get.return_value = mock_response
        
        result = await verifier._verify_openai("test-key", VerificationLevel.BASIC)
        assert result["is_valid"] == True
        assert "API anahtarı geçerli" in result["message"]
        assert "available_models_count" in result["details"]
    
    # Geçersiz anahtar
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.return_value = MockResponse(401, {"error": {"message": "Invalid API key"}})
        
        result = await verifier._verify_openai("invalid-key", VerificationLevel.BASIC)
        assert result["is_valid"] == False
        assert "geçersiz" in result["message"].lower()
    
    # Rate limit aşıldı
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.return_value = MockResponse(
            429, 
            {"error": {"message": "Rate limit exceeded"}},
            {"x-ratelimit-limit-requests": "100", "x-ratelimit-remaining-requests": "0"}
        )
        
        result = await verifier._verify_openai("rate-limited-key", VerificationLevel.BASIC)
        assert result["is_valid"] == False
        assert "rate limit" in result["message"].lower()
        assert "rate_limits" in result["details"]

@pytest.mark.asyncio
async def test_verify_key_complete():
    """Tam API anahtar doğrulama testi - provider'a göre doğru fonksiyon çağrılıyor mu?"""
    verifier = ApiKeyVerifier()
    
    # OpenAI için doğru metod çağrılıyor mu?
    with patch.object(verifier, '_verify_openai') as mock_openai:
        mock_openai.return_value = {"is_valid": True, "message": "Test"}
        await verifier._verify_provider_key("openai", "test-key", VerificationLevel.STANDARD)
        assert mock_openai.called
        mock_openai.assert_called_with("test-key", VerificationLevel.STANDARD)
    
    # Cohere için doğru metod çağrılıyor mu?
    with patch.object(verifier, '_verify_cohere') as mock_cohere:
        mock_cohere.return_value = {"is_valid": True, "message": "Test"}
        await verifier._verify_provider_key("cohere", "test-key", VerificationLevel.STANDARD)
        assert mock_cohere.called
    
    # Bilinmeyen provider için
    result = await verifier._verify_provider_key("unknown", "test-key", VerificationLevel.STANDARD)
    assert result["is_valid"] == False
    assert "Desteklenmeyen sağlayıcı" in result["message"]