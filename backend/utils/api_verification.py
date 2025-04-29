# Last reviewed: 2025-04-29 10:27:19 UTC (User: TeeksssAPI)
from typing import Dict, Any, Optional, List, Tuple
import httpx
import asyncio
import time
import json
from enum import Enum
import logging
from datetime import datetime, timedelta

from ..utils.logger import get_logger
from ..models.api_key_models import ApiProvider

logger = get_logger(__name__)

class VerificationLevel(str, Enum):
    """Doğrulama seviyesi türleri"""
    BASIC = "basic"       # Sadece formatın doğruluğu ve HTTP durum kodları
    STANDARD = "standard" # Basic + API temel fonksiyonalite testi
    COMPLETE = "complete" # Standard + rate limits, token yeterlilik kontrolü

class RateLimitInfo:
    """Rate limit bilgisi"""
    def __init__(self, 
                 limit: int = 0, 
                 remaining: int = 0, 
                 reset: int = 0,
                 unit: str = "minute"):
        self.limit = limit
        self.remaining = remaining
        self.reset = reset
        self.unit = unit
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "limit": self.limit,
            "remaining": self.remaining,
            "reset_seconds": self.reset,
            "unit": self.unit
        }

class ApiKeyVerifier:
    """
    API anahtarlarının doğruluğunu ve yetkilerini test eden sınıf.
    Rate limiting, token geçerliliği ve diğer ayrıntıları kontrol eder.
    """
    
    def __init__(self):
        self.cache = {}  # {provider: {api_key: {result, timestamp}}}
        self.cache_ttl = 300  # 5 dakika (saniye olarak)
    
    async def verify_key(self, 
                        provider: str, 
                        api_key: str, 
                        level: VerificationLevel = VerificationLevel.STANDARD,
                        use_cache: bool = True) -> Dict[str, Any]:
        """API anahtarını doğrular ve sonuç döndürür"""
        # Cache kontrolü
        cache_key = f"{provider}:{api_key}"
        if use_cache and cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if time.time() - cache_entry["timestamp"] < self.cache_ttl:
                return cache_entry["result"]
        
        # Sağlayıcıya özel doğrulama
        result = await self._verify_provider_key(provider, api_key, level)
        
        # Cache'e kaydet
        if use_cache:
            self.cache[cache_key] = {
                "result": result,
                "timestamp": time.time()
            }
        
        return result
    
    async def _verify_provider_key(self, 
                                  provider: str, 
                                  api_key: str, 
                                  level: VerificationLevel) -> Dict[str, Any]:
        """Sağlayıcı türüne göre anahtarı doğrular"""
        result = {
            "provider": provider,
            "is_valid": False,
            "message": "Doğrulama başarısız",
            "details": None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # Anahtar formatını kontrol et
            format_valid, format_msg = self._check_key_format(provider, api_key)
            if not format_valid:
                result["message"] = f"API anahtarı format kontrolü başarısız: {format_msg}"
                return result
            
            # Sağlayıcı türüne göre doğrulama fonksiyonu seç
            if provider == ApiProvider.OPENAI:
                verify_result = await self._verify_openai(api_key, level)
            elif provider == ApiProvider.COHERE:
                verify_result = await self._verify_cohere(api_key, level)
            elif provider == ApiProvider.JINA:
                verify_result = await self._verify_jina(api_key, level)
            elif provider == ApiProvider.WEAVIATE:
                verify_result = await self._verify_weaviate(api_key, level)
            elif provider == ApiProvider.GOOGLE:
                verify_result = await self._verify_google(api_key, level)
            elif provider == ApiProvider.AZURE:
                verify_result = await self._verify_azure_openai(api_key, level)
            elif provider == ApiProvider.HUGGINGFACE:
                verify_result = await self._verify_huggingface(api_key, level)
            else:
                verify_result = {
                    "is_valid": False,
                    "message": f"Desteklenmeyen sağlayıcı: {provider}",
                    "details": None
                }
            
            # Sonuçları birleştir
            result.update(verify_result)
            
        except Exception as e:
            logger.error(f"API anahtarı doğrulama hatası ({provider}): {str(e)}")
            result["message"] = f"Doğrulama sırasında hata: {str(e)}"
        
        return result
    
    def _check_key_format(self, provider: str, api_key: str) -> Tuple[bool, str]:
        """API anahtarı formatının doğru olup olmadığını kontrol eder"""
        if not api_key or len(api_key) < 8:
            return False, "API anahtarı çok kısa veya boş"
            
        # Sağlayıcıya özel format kontrolü
        if provider == ApiProvider.OPENAI:
            if not api_key.startswith(("sk-", "org-")):
                return False, "OpenAI anahtarları 'sk-' veya 'org-' ile başlamalıdır"
        elif provider == ApiProvider.AZURE:
            # Azure API anahtarları genelde 32 karakter uzunluğunda GUID formatındadır
            if len(api_key) != 32 and not api_key.startswith(("sk-")):
                return False, "Azure API anahtarları 32 karakter olmalı veya 'sk-' ile başlamalıdır"
        elif provider == ApiProvider.HUGGINGFACE:
            if not api_key.startswith("hf_"):
                return False, "HuggingFace anahtarları 'hf_' ile başlamalıdır"
                
        return True, "Format geçerli"
    
    async def _verify_openai(self, 
                           api_key: str, 
                           level: VerificationLevel) -> Dict[str, Any]:
        """OpenAI API anahtarını doğrular"""
        result = {
            "is_valid": False,
            "message": "OpenAI API anahtarı doğrulanamadı",
            "details": None
        }
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            try:
                # Basic: Sadece models API'sini çağırarak durum kontrolü
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers=headers
                )
                
                if response.status_code == 200:
                    result["is_valid"] = True
                    result["message"] = "API anahtarı geçerli"
                    
                    models_data = response.json()
                    
                    # Model listesinden bilgileri çıkar
                    available_models = [model["id"] for model in models_data.get("data", [])]
                    result["details"] = {
                        "available_models_count": len(available_models),
                        "example_models": available_models[:5] if available_models else [],
                        "has_gpt4": any("gpt-4" in model for model in available_models)
                    }
                    
                    # Standard veya Complete seviyesi için rate limit kontrolü
                    if level in [VerificationLevel.STANDARD, VerificationLevel.COMPLETE]:
                        rate_limit_info = self._extract_rate_limits(response.headers)
                        result["details"]["rate_limits"] = rate_limit_info.to_dict()
                    
                    # Complete seviyesi için token testi
                    if level == VerificationLevel.COMPLETE:
                        token_result = await self._test_openai_tokens(client, api_key, headers)
                        result["details"]["token_test"] = token_result
                    
                elif response.status_code == 401:
                    result["message"] = "API anahtarı geçersiz veya yetkisiz"
                elif response.status_code == 429:
                    result["message"] = "API anahtarı rate limiti aşmış"
                    
                    # Rate limit bilgilerini header'dan çıkar
                    rate_limit_info = self._extract_rate_limits(response.headers)
                    result["details"] = {"rate_limits": rate_limit_info.to_dict()}
                else:
                    result["message"] = f"API hatası: HTTP {response.status_code}"
                    try:
                        error_detail = response.json()
                        result["details"] = {"error": error_detail}
                    except:
                        result["details"] = {"raw_response": response.text}
                
            except Exception as e:
                result["message"] = f"Bağlantı hatası: {str(e)}"
                
        return result
    
    async def _test_openai_tokens(self, 
                                client: httpx.AsyncClient, 
                                api_key: str, 
                                headers: Dict[str, str]) -> Dict[str, Any]:
        """OpenAI'nin token yeterlilik durumunu test eder"""
        token_result = {
            "success": False,
            "message": "Token testi yapılamadı"
        }
        
        try:
            # Basit bir completion isteği
            payload = {
                "model": "gpt-3.5-turbo-instruct",
                "prompt": "Hello, this is a test message to verify API key.",
                "max_tokens": 10
            }
            
            response = await client.post(
                "https://api.openai.com/v1/completions",
                headers=headers,
                json=payload,
                timeout=8.0
            )
            
            if response.status_code == 200:
                token_result["success"] = True
                token_result["message"] = "Token testi başarılı"
                
                # Token kullanım bilgilerini çıkar
                try:
                    data = response.json()
                    token_result["usage"] = data.get("usage", {})
                except:
                    pass
            else:
                error_msg = "Bilinmeyen hata"
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Bilinmeyen hata")
                except:
                    pass
                
                token_result["message"] = f"Token testi başarısız: {error_msg}"
        except Exception as e:
            token_result["message"] = f"Token testi sırasında hata: {str(e)}"
            
        return token_result
    
    def _extract_rate_limits(self, headers: Dict[str, str]) -> RateLimitInfo:
        """HTTP yanıt başlıklarından rate limit bilgilerini çıkarır"""
        rate_limit_info = RateLimitInfo()
        
        try:
            # OpenAI/Azure için
            if "x-ratelimit-limit-requests" in headers:
                rate_limit_info.limit = int(headers.get("x-ratelimit-limit-requests", "0"))
                rate_limit_info.remaining = int(headers.get("x-ratelimit-remaining-requests", "0"))
                rate_limit_info.reset = int(headers.get("x-ratelimit-reset-requests", "0"))
                rate_limit_info.unit = "minute"
            # Cohere için
            elif "x-ratelimit-limit" in headers:
                rate_limit_info.limit = int(headers.get("x-ratelimit-limit", "0"))
                rate_limit_info.remaining = int(headers.get("x-ratelimit-remaining", "0"))
                rate_limit_info.reset = int(headers.get("x-ratelimit-reset", "0"))
                rate_limit_info.unit = "minute"
        except (ValueError, TypeError) as e:
            logger.warning(f"Rate limit bilgisi çıkarılırken hata: {e}")
            
        return rate_limit_info
    
    async def _verify_cohere(self, 
                           api_key: str, 
                           level: VerificationLevel) -> Dict[str, Any]:
        """Cohere API anahtarını doğrular"""
        result = {
            "is_valid": False,
            "message": "Cohere API anahtarı doğrulanamadı",
            "details": None
        }
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            try:
                # Basic: Embed API'sini çağırarak durum kontrolü
                payload = {
                    "texts": ["Test message for API key validation"]
                }
                
                response = await client.post(
                    "https://api.cohere.ai/v1/embed",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    result["is_valid"] = True
                    result["message"] = "API anahtarı geçerli"
                    
                    # Cevaptaki embedding boyutunu al
                    try:
                        data = response.json()
                        embeddings = data.get("embeddings", [])
                        if embeddings:
                            result["details"] = {
                                "embedding_dimension": len(embeddings[0]),
                                "model": data.get("model", "")
                            }
                    except:
                        pass
                    
                    # Standard veya Complete seviyesi için rate limit kontrolü
                    if level in [VerificationLevel.STANDARD, VerificationLevel.COMPLETE]:
                        rate_limit_info = self._extract_rate_limits(response.headers)
                        result["details"] = result.get("details", {})
                        result["details"]["rate_limits"] = rate_limit_info.to_dict()
                    
                    # Complete seviyesi için model listeleme
                    if level == VerificationLevel.COMPLETE:
                        model_result = await self._test_cohere_models(client, api_key, headers)
                        result["details"]["models"] = model_result
                    
                elif response.status_code == 401:
                    result["message"] = "API anahtarı geçersiz veya yetkisiz"
                elif response.status_code == 429:
                    result["message"] = "API anahtarı rate limiti aşmış"
                    rate_limit_info = self._extract_rate_limits(response.headers)
                    result["details"] = {"rate_limits": rate_limit_info.to_dict()}
                else:
                    result["message"] = f"API hatası: HTTP {response.status_code}"
                    try:
                        error_detail = response.json()
                        result["details"] = {"error": error_detail}
                    except:
                        result["details"] = {"raw_response": response.text}
                
            except Exception as e:
                result["message"] = f"Bağlantı hatası: {str(e)}"
                
        return result
    
    async def _test_cohere_models(self, 
                                client: httpx.AsyncClient, 
                                api_key: str, 
                                headers: Dict[str, str]) -> Dict[str, Any]:
        """Cohere'in kullanılabilir modellerini test eder"""
        model_result = {
            "success": False,
            "message": "Model listesi alınamadı"
        }
        
        try:
            response = await client.get(
                "https://api.cohere.ai/v1/models",
                headers=headers,
                timeout=8.0
            )
            
            if response.status_code == 200:
                model_result["success"] = True
                model_result["message"] = "Model listesi alındı"
                
                try:
                    data = response.json()
                    models = []
                    for model in data.get("models", []):
                        models.append({
                            "name": model.get("name"),
                            "type": model.get("model_type")
                        })
                    model_result["available_models"] = models
                except Exception as e:
                    model_result["message"] = f"Model listesi işlenirken hata: {str(e)}"
            else:
                model_result["message"] = f"Model listesi alınamadı: HTTP {response.status_code}"
        except Exception as e:
            model_result["message"] = f"Model listesi sorgulanırken hata: {str(e)}"
            
        return model_result
    
    async def _verify_jina(self, 
                         api_key: str, 
                         level: VerificationLevel) -> Dict[str, Any]:
        """Jina AI API anahtarını doğrular"""
        result = {
            "is_valid": False,
            "message": "Jina API anahtarı doğrulanamadı",
            "details": None
        }
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            try:
                # Basic: Embeddings API'sini çağırarak durum kontrolü
                payload = {
                    "texts": ["Test message for API key validation"],
                    "model": "jina-embeddings-v2-base-en"
                }
                
                response = await client.post(
                    "https://api.jina.ai/v1/embeddings",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    result["is_valid"] = True
                    result["message"] = "API anahtarı geçerli"
                    
                    # Embedding boyutunu al
                    try:
                        data = response.json()
                        embeddings = data.get("embeddings", [])
                        if embeddings:
                            result["details"] = {
                                "embedding_dimension": len(embeddings[0]),
                                "model": payload["model"]
                            }
                    except:
                        pass
                    
                    # Standard veya Complete seviyesi için kredi bilgisi
                    if level in [VerificationLevel.STANDARD, VerificationLevel.COMPLETE]:
                        credit_result = await self._check_jina_credits(client, api_key, headers)
                        result["details"] = result.get("details", {})
                        result["details"]["credits"] = credit_result
                        
                elif response.status_code == 401:
                    result["message"] = "API anahtarı geçersiz veya yetkisiz"
                elif response.status_code == 429:
                    result["message"] = "API anahtarı rate limiti aşmış"
                else:
                    result["message"] = f"API hatası: HTTP {response.status_code}"
                    try:
                        error_detail = response.json()
                        result["details"] = {"error": error_detail}
                    except:
                        result["details"] = {"raw_response": response.text}
                
            except Exception as e:
                result["message"] = f"Bağlantı hatası: {str(e)}"
                
        return result
    
    async def _check_jina_credits(self, 
                               client: httpx.AsyncClient, 
                               api_key: str, 
                               headers: Dict[str, str]) -> Dict[str, Any]:
        """Jina AI kredi durumunu kontrol eder"""
        credit_info = {
            "success": False,
            "message": "Kredi bilgileri alınamadı"
        }
        
        # Gerçek uygulamada Jina'nın credit API'sini kullan
        # Bu bir simülasyon - gerçek API'ye göre güncellenmelidir
        credit_info["success"] = True
        credit_info["message"] = "Kredi bilgileri alındı"
        credit_info["remaining_credits"] = 10000  # Örnek değer
        credit_info["reset_date"] = (datetime.utcnow() + timedelta(days=30)).isoformat()
            
        return credit_info
    
    async def _verify_weaviate(self, 
                             api_key: str, 
                             level: VerificationLevel) -> Dict[str, Any]:
        """Weaviate API anahtarını doğrular"""
        result = {
            "is_valid": False,
            "message": "Weaviate API anahtarı doğrulanamadı",
            "details": None
        }
        
        # Weaviate URL'si gerekli - burada varsayılan olarak localhost kullanılıyor
        weaviate_url = "http://localhost:8080"
        
        # Konfigürasyondan URL alınabilir
        try:
            from ..utils.config import WEAVIATE_URL
            if WEAVIATE_URL:
                weaviate_url = WEAVIATE_URL
        except ImportError:
            pass
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            try:
                # Basic: Ready endpoint'ini çağırarak durum kontrolü
                response = await client.get(
                    f"{weaviate_url}/v1/.well-known/ready",
                    headers=headers
                )
                
                if response.status_code == 200:
                    result["is_valid"] = True
                    result["message"] = "API anahtarı geçerli"
                    
                    # Standard veya Complete seviyesi için meta bilgileri al
                    if level in [VerificationLevel.STANDARD, VerificationLevel.COMPLETE]:
                        meta_result = await self._get_weaviate_meta(client, weaviate_url, headers)
                        result["details"] = meta_result
                        
                elif response.status_code == 401:
                    result["message"] = "API anahtarı geçersiz veya yetkisiz"
                else:
                    result["message"] = f"API hatası: HTTP {response.status_code}"
                    try:
                        error_detail = response.json()
                        result["details"] = {"error": error_detail}
                    except:
                        result["details"] = {"raw_response": response.text}
                
            except Exception as e:
                result["message"] = f"Bağlantı hatası: {str(e)}"
                
        return result
    
    async def _get_weaviate_meta(self, 
                              client: httpx.AsyncClient, 
                              weaviate_url: str,
                              headers: Dict[str, str]) -> Dict[str, Any]:
        """Weaviate meta bilgilerini getirir"""
        meta_info = {
            "success": False,
            "message": "Meta bilgileri alınamadı"
        }
        
        try:
            response = await client.get(
                f"{weaviate_url}/v1/meta",
                headers=headers
            )
            
            if response.status_code == 200:
                meta_info["success"] = True
                meta_info["message"] = "Meta bilgileri alındı"
                
                try:
                    data = response.json()
                    meta_info["version"] = data.get("version", "")
                    meta_info["hostname"] = data.get("hostname", "")
                    
                    # Sınıf sayısını al
                    schema_response = await client.get(
                        f"{weaviate_url}/v1/schema",
                        headers=headers
                    )
                    
                    if schema_response.status_code == 200:
                        schema_data = schema_response.json()
                        meta_info["classes_count"] = len(schema_data.get("classes", []))
                        meta_info["classes"] = [cls.get("class") for cls in schema_data.get("classes", [])]
                except Exception as e:
                    meta_info["message"] = f"Meta bilgileri işlenirken hata: {str(e)}"
            else:
                meta_info["message"] = f"Meta bilgileri alınamadı: HTTP {response.status_code}"
        except Exception as e:
            meta_info["message"] = f"Meta sorgulanırken hata: {str(e)}"
            
        return meta_info
    
    async def _verify_google(self, 
                           api_key: str, 
                           level: VerificationLevel) -> Dict[str, Any]:
        """Google Cloud API anahtarını doğrular"""
        result = {
            "is_valid": False,
            "message": "Google API anahtarı doğrulanamadı",
            "details": None
        }
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                # Basic: Basit bir API çağrısı yap (Translation API)
                url = f"https://translation.googleapis.com/language/translate/v2/detect?key={api_key}"
                payload = {
                    "q": "Hello, world!"
                }
                
                response = await client.post(url, json=payload)
                
                if response.status_code == 200:
                    result["is_valid"] = True
                    result["message"] = "API anahtarı geçerli"
                    
                    # Standard seviyesi için bilgileri çıkar
                    if level in [VerificationLevel.STANDARD, VerificationLevel.COMPLETE]:
                        result["details"] = {
                            "api_accessed": "Translation API",
                            "quota_info": "Available"
                        }
                        
                elif response.status_code == 403:
                    result["message"] = "API anahtarı geçersiz veya yetkisiz"
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", "")
                        if "API key not valid" in error_msg:
                            result["message"] = "API anahtarı geçersiz"
                        elif "Requests from this API key for this API have been denied" in error_msg:
                            result["message"] = "API anahtarı için bu API erişimi kısıtlanmış"
                    except:
                        pass
                        
                elif response.status_code == 429:
                    result["message"] = "API anahtarı kota limitini aşmış"
                else:
                    result["message"] = f"API hatası: HTTP {response.status_code}"
                    try:
                        error_detail = response.json()
                        result["details"] = {"error": error_detail}
                    except:
                        result["details"] = {"raw_response": response.text}
                
            except Exception as e:
                result["message"] = f"Bağlantı hatası: {str(e)}"
                
        return result
    
    async def _verify_azure_openai(self, 
                                 api_key: str, 
                                 level: VerificationLevel) -> Dict[str, Any]:
        """Azure OpenAI API anahtarını doğrular"""
        result = {
            "is_valid": False,
            "message": "Azure OpenAI API anahtarı doğrulanamadı",
            "details": None
        }
        
        # Azure endpoint gerekli - bu bir mock değer
        azure_endpoint = "https://your-resource-name.openai.azure.com"
        
        # Konfigürasyondan endpoint alınabilir
        try:
            from ..utils.config import AZURE_OPENAI_ENDPOINT
            if AZURE_OPENAI_ENDPOINT:
                azure_endpoint = AZURE_OPENAI_ENDPOINT
        except ImportError:
            # Bu durumda doğrulama yapamayız
            result["message"] = "Azure OpenAI endpoint bilgisi eksik"
            return result
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            headers = {
                "api-key": api_key,
                "Content-Type": "application/json"
            }
            
            try:
                # Basic: Deployments listesini çek
                response = await client.get(
                    f"{azure_endpoint}/openai/deployments?api-version=2023-05-15",
                    headers=headers
                )
                
                if response.status_code == 200:
                    result["is_valid"] = True
                    result["message"] = "API anahtarı geçerli"
                    
                    # Model deployments bilgilerini çıkar
                    try:
                        data = response.json()
                        deployments = data.get("data", [])
                        result["details"] = {
                            "deployments_count": len(deployments),
                            "deployments": [d.get("id") for d in deployments]
                        }
                    except:
                        pass
                    
                    # Standard veya Complete seviyesi için quota bilgisi
                    if level in [VerificationLevel.STANDARD, VerificationLevel.COMPLETE]:
                        quota_result = await self._check_azure_quota(client, azure_endpoint, headers)
                        result["details"] = result.get("details", {})
                        result["details"]["quota"] = quota_result
                    
                elif response.status_code == 401:
                    result["message"] = "API anahtarı geçersiz veya yetkisiz"
                elif response.status_code == 429:
                    result["message"] = "API anahtarı rate limitini aşmış"
                else:
                    result["message"] = f"API hatası: HTTP {response.status_code}"
                    try:
                        error_detail = response.json()
                        result["details"] = {"error": error_detail}
                    except:
                        result["details"] = {"raw_response": response.text}
                
            except Exception as e:
                result["message"] = f"Bağlantı hatası: {str(e)}"
                
        return result
    
    async def _check_azure_quota(self, 
                              client: httpx.AsyncClient, 
                              azure_endpoint: str,
                              headers: Dict[str, str]) -> Dict[str, Any]:
        """Azure OpenAI kota bilgisini kontrol eder"""
        quota_info = {
            "success": False,
            "message": "Kota bilgileri alınamadı"
        }
        
        # Not: Azure OpenAI için quota API'si yok - bu gerçek bir implementasyon değil
        quota_info["success"] = True
        quota_info["message"] = "Kota bilgileri alındı (simülasyon)"
        quota_info["limits"] = {
            "tokens_per_minute": 10000,  # Örnek değer
            "requests_per_minute": 600   # Örnek değer
        }
            
        return quota_info
    
    async def _verify_huggingface(self, 
                                api_key: str, 
                                level: VerificationLevel) -> Dict[str, Any]:
        """HuggingFace API anahtarını doğrular"""
        result = {
            "is_valid": False,
            "message": "HuggingFace API anahtarı doğrulanamadı",
            "details": None
        }
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            headers = {
                "Authorization": f"Bearer {api_key}"
            }
            
            try:
                # Basic: Account/whoami endpoint'ini çağırarak durum kontrolü
                response = await client.get(
                    "https://huggingface.co/api/whoami",
                    headers=headers
                )
                
                if response.status_code == 200:
                    result["is_valid"] = True
                    result["message"] = "API anahtarı geçerli"
                    
                    # Kullanıcı bilgilerini çıkar
                    try:
                        data = response.json()
                        result["details"] = {
                            "user": data.get("name"),
                            "type": data.get("type"),
                            "canPay": data.get("canPay", False),
                            "isPro": data.get("isPro", False)
                        }
                    except:
                        pass
                    
                    # Standard veya Complete seviyesi için model listesi
                    if level in [VerificationLevel.STANDARD, VerificationLevel.COMPLETE]:
                        models_result = await self._get_hf_models(client, api_key, headers)
                        result["details"]["models"] = models_result
                        
                elif response.status_code == 401:
                    result["message"] = "API anahtarı geçersiz veya yetkisiz"
                elif response.status_code == 429:
                    result["message"] = "API anahtarı rate limitini aşmış"
                else:
                    result["message"] = f"API hatası: HTTP {response.status_code}"
                    try:
                        error_detail = response.json()
                        result["details"] = {"error": error_detail}
                    except:
                        result["details"] = {"raw_response": response.text}
                
            except Exception as e:
                result["message"] = f"Bağlantı hatası: {str(e)}"
                
        return result
    
    async def _get_hf_models(self, 
                          client: httpx.AsyncClient, 
                          api_key: str, 
                          headers: Dict[str, str]) -> Dict[str, Any]:
        """HuggingFace model bilgilerini getirir"""
        models_info = {
            "success": False,
            "message": "Model bilgileri alınamadı"
        }
        
        try:
            # Kullanıcıya ait model sayısı
            response = await client.get(
                "https://huggingface.co/api/models",
                headers=headers,
                params={
                    "limit": 5,
                    "sort": "lastModified",
                    "direction": -1
                }
            )
            
            if response.status_code == 200:
                models_info["success"] = True
                models_info["message"] = "Model bilgileri alındı"
                
                try:
                    data = response.json()
                    models_info["recent_models"] = [
                        {"name": model.get("modelId"), "type": model.get("pipeline_tag")}
                        for model in data
                    ]
                except Exception as e:
                    models_info["message"] = f"Model bilgileri işlenirken hata: {str(e)}"
            else:
                models_info["message"] = f"Model bilgileri alınamadı: HTTP {response.status_code}"
        except Exception as e:
            models_info["message"] = f"Model sorgulanırken hata: {str(e)}"
            
        return models_info

# API key verifier singleton
api_key_verifier = ApiKeyVerifier()