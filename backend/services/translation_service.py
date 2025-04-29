# Last reviewed: 2025-04-29 12:51:02 UTC (User: TeeksssCI/CD)
import os
import logging
import asyncio
from typing import Dict, Any, List, Optional, Union
import time
from datetime import datetime

# Çeviri kitaplıkları
import httpx
from googletrans import Translator as GoogleTranslator
from deep_translator import GoogleTranslator as DeepGoogleTranslator
from deep_translator import MicrosoftTranslator
from langdetect import detect as detect_language

from .translation_cache_service import TranslationCacheService
from ..config import settings
from ..utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

class TranslationEngine:
    """Çeviri motoru türleri"""
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    GOOGLE_API = "google_api"
    CUSTOM_API = "custom_api"

class TranslationService:
    """
    Çeviri hizmetlerini yöneten servis sınıfı.
    
    Özellikler:
    - Çoklu çeviri motorları desteği
    - Önbellek entegrasyonu
    - Rate limiting
    - Otomatik dil algılama
    - Hata yönetimi ve geri dönüş mekanizmaları
    - Asenkron çalışma
    """
    
    def __init__(self):
        """Çeviri servisini ve bağımlılıklarını başlatır"""
        # Yapılandırma
        self.default_engine = settings.TRANSLATION_ENGINE or TranslationEngine.GOOGLE
        self.google_api_key = settings.GOOGLE_TRANSLATE_API_KEY
        self.ms_api_key = settings.MS_TRANSLATOR_API_KEY
        self.custom_api_url = settings.CUSTOM_TRANSLATE_API_URL
        
        # Motorlar
        self.engines = {}
        self.init_engines()
        
        # Rate limiter
        self.rate_limiters = {
            TranslationEngine.GOOGLE: RateLimiter(5, 1),  # 5 istek/saniye
            TranslationEngine.MICROSOFT: RateLimiter(10, 1),  # 10 istek/saniye
            TranslationEngine.GOOGLE_API: RateLimiter(50, 60),  # 50 istek/dakika
            TranslationEngine.CUSTOM_API: RateLimiter(20, 1)  # 20 istek/saniye
        }
        
        # Önbellek servisi
        self.cache_service = TranslationCacheService()
        
        # Desteklenen diller
        self.supported_languages = self._get_supported_languages()
        
        # Dil algılama hızlandırma
        self.detect_limiter = RateLimiter(10, 1)  # 10 algılama/saniye
    
    def init_engines(self):
        """Çeviri motorlarını başlatır"""
        # Google çevirisi (kitaplık tabanlı, API anahtarı gerektirmez)
        try:
            self.engines[TranslationEngine.GOOGLE] = GoogleTranslator()
        except Exception as e:
            logger.error(f"Google Translator initialization error: {e}")
        
        # Microsoft Çevirisi (API key gereklidir)
        if self.ms_api_key:
            self.engines[TranslationEngine.MICROSOFT] = MicrosoftTranslator(api_key=self.ms_api_key)
        
        # Google API (API key gereklidir)
        if self.google_api_key:
            self.engines[TranslationEngine.GOOGLE_API] = True
    
    def _get_supported_languages(self) -> Dict[str, List[str]]:
        """
        Motorlar için desteklenen dilleri döndürür
        
        Returns:
            Dict[str, List[str]]: Motor türüne göre desteklenen dil kodları
        """
        # Temel desteklenen diller
        supported = {
            TranslationEngine.GOOGLE: ['af', 'sq', 'am', 'ar', 'hy', 'az', 'eu', 'be', 'bn', 'bs', 'bg', 'ca', 'ceb', 
                                      'zh-cn', 'zh-tw', 'co', 'hr', 'cs', 'da', 'nl', 'en', 'eo', 'et', 'fi', 'fr', 
                                      'fy', 'gl', 'ka', 'de', 'el', 'gu', 'ht', 'ha', 'haw', 'he', 'hi', 'hmn', 'hu', 
                                      'is', 'ig', 'id', 'ga', 'it', 'ja', 'jw', 'kn', 'kk', 'km', 'ko', 'ku', 'ky', 
                                      'lo', 'la', 'lv', 'lt', 'lb', 'mk', 'mg', 'ms', 'ml', 'mt', 'mi', 'mr', 'mn', 
                                      'my', 'ne', 'no', 'ny', 'ps', 'fa', 'pl', 'pt', 'pa', 'ro', 'ru', 'sm', 'gd', 
                                      'sr', 'st', 'sn', 'sd', 'si', 'sk', 'sl', 'so', 'es', 'su', 'sw', 'sv', 'tg', 
                                      'ta', 'te', 'th', 'tr', 'uk', 'ur', 'uz', 'vi', 'cy', 'xh', 'yi', 'yo', 'zu'],
            TranslationEngine.MICROSOFT: [],
            TranslationEngine.GOOGLE_API: ['af', 'sq', 'am', 'ar', 'hy', 'az', 'eu', 'be', 'bn', 'bs', 'bg', 'ca', 'ceb', 
                                          'zh-cn', 'zh-tw', 'co', 'hr', 'cs', 'da', 'nl', 'en', 'eo', 'et', 'fi', 'fr', 
                                          'fy', 'gl', 'ka', 'de', 'el', 'gu', 'ht', 'ha', 'haw', 'he', 'hi', 'hmn', 'hu', 
                                          'is', 'ig', 'id', 'ga', 'it', 'ja', 'jw', 'kn', 'kk', 'km', 'ko', 'ku', 'ky', 
                                          'lo', 'la', 'lv', 'lt', 'lb', 'mk', 'mg', 'ms', 'ml', 'mt', 'mi', 'mr', 'mn', 
                                          'my', 'ne', 'no', 'ny', 'ps', 'fa', 'pl', 'pt', 'pa', 'ro', 'ru', 'sm', 'gd', 
                                          'sr', 'st', 'sn', 'sd', 'si', 'sk', 'sl', 'so', 'es', 'su', 'sw', 'sv', 'tg', 
                                          'ta', 'te', 'th', 'tr', 'uk', 'ur', 'uz', 'vi', 'cy', 'xh', 'yi', 'yo', 'zu'],
            TranslationEngine.CUSTOM_API: []
        }
        
        # Microsoft API için desteklenen dilleri al
        if TranslationEngine.MICROSOFT in self.engines:
            try:
                ms_langs = self.engines[TranslationEngine.MICROSOFT].get_supported_languages()
                supported[TranslationEngine.MICROSOFT] = ms_langs
            except Exception as e:
                logger.error(f"Failed to get Microsoft supported languages: {e}")
        
        return supported
    
    async def detect_language(self, text: str) -> Optional[str]:
        """
        Metin dili tespit eder
        
        Args:
            text: Dili tespit edilecek metin
            
        Returns:
            Optional[str]: Tespit edilen dil kodu veya None
        """
        if not text or len(text.strip()) < 3:
            return None
        
        # Rate limiting
        await self.detect_limiter.acquire()
        
        try:
            # İlk 100 karakter ile tespit yap (performans)
            sample_text = text[:100].strip()
            
            # Dili tespit et
            return detect_language(sample_text)
        except Exception as e:
            logger.error(f"Language detection error: {e}")
            return None
    
    async def translate(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None,
        engine: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Metni çevirir
        
        Args:
            text: Çevrilecek metin
            target_language: Hedef dil kodu
            source_language: Kaynak dil kodu (belirlenmemişse otomatik algılanır)
            engine: Kullanılacak çeviri motoru
            use_cache: Önbellek kullanılsın mı?
            
        Returns:
            Dict[str, Any]: Çeviri sonucu
        """
        start_time = time.time()
        
        # Metin kontrolü
        if not text or not text.strip():
            return {
                "translated_text": "",
                "source_language": source_language,
                "target_language": target_language,
                "engine": engine or self.default_engine,
                "processing_time_ms": int((time.time() - start_time) * 1000),
                "from_cache": False
            }
        
        # Çeviri motoru seçimi
        engine = engine or self.default_engine
        if engine not in self.engines and engine != TranslationEngine.CUSTOM_API:
            engine = self.default_engine
        
        # Kaynak dil belirlenmemişse, otomatik algıla
        if not source_language:
            source_language = await self.detect_language(text) or "en"
        
        # Kaynak dil ve hedef dil aynı ise, doğrudan metni döndür
        if source_language == target_language:
            return {
                "translated_text": text,
                "source_language": source_language,
                "target_language": target_language,
                "engine": engine,
                "processing_time_ms": int((time.time() - start_time) * 1000),
                "from_cache": False
            }
        
        # Önbellekten kontrol et
        if use_cache:
            cached_result = await self.cache_service.get_cached_translation(
                text=text,
                source_lang=source_language,
                target_lang=target_language
            )
            
            if cached_result:
                # Önbellekten bulunan sonucu döndür
                cached_result["from_cache"] = True
                cached_result["processing_time_ms"] = int((time.time() - start_time) * 1000)
                return cached_result
        
        # Rate limiter
        if engine in self.rate_limiters:
            await self.rate_limiters[engine].acquire()
        
        # Çeviri yöntemine göre çevirip sonucu döndür
        try:
            if engine == TranslationEngine.GOOGLE:
                result = await self._translate_with_google(text, source_language, target_language)
            elif engine == TranslationEngine.MICROSOFT:
                result = await self._translate_with_microsoft(text, source_language, target_language)
            elif engine == TranslationEngine.GOOGLE_API:
                result = await self._translate_with_google_api(text, source_language, target_language)
            elif engine == TranslationEngine.CUSTOM_API:
                result = await self._translate_with_custom_api(text, source_language, target_language)
            else:
                # Bilinmeyen motor, varsayılan olarak Google kullan
                result = await self._translate_with_google(text, source_language, target_language)
            
            # Sonuç oluştur
            translation_result = {
                "translated_text": result,
                "source_language": source_language,
                "target_language": target_language,
                "engine": engine,
                "processing_time_ms": int((time.time() - start_time) * 1000),
                "from_cache": False,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Sonucu önbelleğe al
            if use_cache and result:
                await self.cache_service.cache_translation(
                    text=text,
                    source_lang=source_language,
                    target_lang=target_language,
                    result=translation_result
                )
            
            return translation_result
            
        except Exception as e:
            logger.error(f"Translation error with engine {engine}: {e}")
            
            # Yedek çeviri motoru ile tekrar dene
            if engine != TranslationEngine.GOOGLE:
                logger.info(f"Fallback to Google translator")
                return await self.translate(
                    text=text,
                    target_language=target_language,
                    source_language=source_language,
                    engine=TranslationEngine.GOOGLE,
                    use_cache=use_cache
                )
            
            # Tüm motorlar başarısız olursa hata bildir
            return {
                "translated_text": text,  # Hata durumunda orijinal metni döndür
                "source_language": source_language,
                "target_language": target_language,
                "engine": engine,
                "processing_time_ms": int((time.time() - start_time) * 1000),
                "from_cache": False,
                "error": str(e)
            }
    
    async def _translate_with_google(self, text: str, source_language: str, target_language: str) -> str:
        """
        Google çeviri kitaplığı ile çeviri yapar
        
        Args:
            text: Çevrilecek metin
            source_language: Kaynak dil kodu
            target_language: Hedef dil kodu
            
        Returns:
            str: Çeviri sonucu
        """
        if len(text) > 5000:
            # Google çeviri limiti aşıldı, metni parçalara böl
            parts = self._split_text(text, 4500)
            results = []
            
            for part in parts:
                # Asenkron çalıştırabilmek için thread pool kullan
                part_result = await asyncio.to_thread(
                    self.engines[TranslationEngine.GOOGLE].translate,
                    part,
                    dest=target_language,
                    src=source_language
                )
                results.append(part_result.text)
            
            return " ".join(results)
        else:
            # Normal çeviri
            result = await asyncio.to_thread(
                self.engines[TranslationEngine.GOOGLE].translate,
                text,
                dest=target_language,
                src=source_language
            )
            return result.text
    
    async def _translate_with_microsoft(self, text: str, source_language: str, target_language: str) -> str:
        """
        Microsoft çeviri API'si ile çeviri yapar
        
        Args:
            text: Çevrilecek metin
            source_language: Kaynak dil kodu
            target_language: Hedef dil kodu
            
        Returns:
            str: Çeviri sonucu
        """
        if TranslationEngine.MICROSOFT not in self.engines:
            raise ValueError("Microsoft Translator engine not initialized")
        
        translator = self.engines[TranslationEngine.MICROSOFT]
        
        if len(text) > 5000:
            # Microsoft çeviri limiti aşıldı, metni parçalara böl
            parts = self._split_text(text, 4500)
            results = []
            
            for part in parts:
                part_result = await asyncio.to_thread(
                    translator.translate,
                    part,
                    target=target_language,
                    source=source_language
                )
                results.append(part_result)
            
            return " ".join(results)
        else:
            # Normal çeviri
            result = await asyncio.to_thread(
                translator.translate,
                text,
                target=target_language,
                source=source_language
            )
            return result
    
    async def _translate_with_google_api(self, text: str, source_language: str, target_language: str) -> str:
        """
        Google çeviri API'si ile çeviri yapar
        
        Args:
            text: Çevrilecek metin
            source_language: Kaynak dil kodu
            target_language: Hedef dil kodu
            
        Returns:
            str: Çeviri sonucu
        """
        if not self.google_api_key:
            raise ValueError("Google Translate API key not set")
        
        # API URL
        api_url = "https://translation.googleapis.com/language/translate/v2"
        
        # İstek parametreleri
        params = {
            "q": text,
            "target": target_language,
            "format": "text",
            "key": self.google_api_key
        }
        
        # Kaynak dil belirlenmişse ekle
        if source_language != "auto":
            params["source"] = source_language
        
        # HTTP isteği gönder
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=params)
            response.raise_for_status()
            
            data = response.json()
            
            if "data" in data and "translations" in data["data"] and data["data"]["translations"]:
                return data["data"]["translations"][0]["translatedText"]
            else:
                raise ValueError(f"Invalid response from Google Translate API: {data}")
    
    async def _translate_with_custom_api(self, text: str, source_language: str, target_language: str) -> str:
        """
        Özel çeviri API'si ile çeviri yapar
        
        Args:
            text: Çevrilecek metin
            source_language: Kaynak dil kodu
            target_language: Hedef dil kodu
            
        Returns:
            str: Çeviri sonucu
        """
        if not self.custom_api_url:
            raise ValueError("Custom translation API URL not set")
        
        # İstek parametreleri
        payload = {
            "text": text,
            "source_language": source_language,
            "target_language": target_language
        }
        
        # HTTP isteği gönder
        async with httpx.AsyncClient() as client:
            response = await client.post(self.custom_api_url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            if "result" in data and "translated_text" in data["result"]:
                return data["result"]["translated_text"]
            elif "translated_text" in data:
                return data["translated_text"]
            else:
                raise ValueError(f"Invalid response from Custom API: {data}")
    
    def _split_text(self, text: str, max_length: int) -> List[str]:
        """
        Metni belirtilen maksimum uzunluğa göre parçalara böler
        
        Args:
            text: Bölünecek metin
            max_length: Maksimum parça uzunluğu
            
        Returns:
            List[str]: Metin parçaları
        """
        # Kısa metin için optimizasyon
        if len(text) <= max_length:
            return [text]
        
        # Metni cümlelere böl
        parts = []
        sentences = text.split(". ")
        current_part = ""
        
        for sentence in sentences:
            # Nokta ekle (split ile kayboldu)
            if sentence:
                sentence = sentence + "."
            
            # Bu cümleyi eklemek maksimum uzunluğu aşar mı?
            if len(current_part) + len(sentence) <= max_length:
                current_part += sentence + " "
            else:
                # Mevcut parçayı ekle ve yeni parça başlat
                if current_part:
                    parts.append(current_part.strip())
                
                # Bu cümle tek başına çok uzunsa, kelimelere böl
                if len(sentence) > max_length:
                    words = sentence.split()
                    current_part = ""
                    
                    for word in words:
                        if len(current_part) + len(word) + 1 <= max_length:
                            current_part += word + " "
                        else:
                            parts.append(current_part.strip())
                            current_part = word + " "
                else:
                    current_part = sentence + " "
        
        # Son parçayı ekle
        if current_part:
            parts.append(current_part.strip())
        
        return parts
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Önbellek istatistiklerini getirir
        
        Returns:
            Dict[str, Any]: İstatistikler
        """
        return await self.cache_service.get_stats()
    
    async def clear_cache(self, source_lang: Optional[str] = None, target_lang: Optional[str] = None) -> int:
        """
        Çeviri önbelleğini temizler
        
        Args:
            source_lang: Filtrelenecek kaynak dil (opsiyonel)
            target_lang: Filtrelenecek hedef dil (opsiyonel)
            
        Returns:
            int: Silinen önbellek sayısı
        """
        return await self.cache_service.clear_cache(source_lang, target_lang)