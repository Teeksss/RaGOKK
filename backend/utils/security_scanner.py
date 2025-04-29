# Last reviewed: 2025-04-29 12:09:11 UTC (User: TeeksssVirüs)
import os
import tempfile
import hashlib
import aiohttp
import asyncio
import re
from typing import Dict, List, Any, Optional, Tuple, Union, Set
import magic
import subprocess
from pathlib import Path
import json
import logging

# Regex için zararlı içerik kalıpları
from dataclasses import dataclass
from enum import Enum

from ..utils.logger import get_logger

logger = get_logger(__name__)


class ScanResult(Enum):
    """Tarama sonucu enum'u"""
    CLEAN = "clean"
    SUSPICIOUS = "suspicious"
    MALICIOUS = "malicious"
    ERROR = "error"


@dataclass
class SecurityScanResult:
    """Güvenlik tarama sonucu"""
    status: ScanResult
    details: Dict[str, Any]
    file_type: str
    mime_type: str
    file_size: int
    sha256: str
    scan_time_ms: int


class SecurityScanner:
    """
    Dosya güvenlik taraması ve zararlı içerik tespiti için sınıf.
    - Virüs/malware taraması
    - Dosya türü doğrulama
    - Zararlı içerik kontrolü
    - Hash tabanlı kontrol
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Args:
            config: Konfigürasyon parametreleri
        """
        self.config = config or {}
        
        # Varsayılan yapılandırma
        self.max_file_size = self.config.get('max_file_size', 100 * 1024 * 1024)  # 100 MB
        self.allowed_mime_types = self.config.get('allowed_mime_types', [
            'application/pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/msword',
            'text/plain',
            'text/html',
            'text/xml',
            'application/json',
            'text/csv',
            'application/xml',
            'image/jpeg',
            'image/png',
            'image/tiff'
        ])
        
        # Virüs tarama motoru ayarları
        self.use_clamav = self.config.get('use_clamav', False)
        self.clamav_socket = self.config.get('clamav_socket', '/var/run/clamav/clamd.ctl')
        
        # VirusTotal API ayarları
        self.use_virustotal = self.config.get('use_virustotal', False)
        self.virustotal_api_key = self.config.get('virustotal_api_key')
        self.virustotal_min_detection = self.config.get('virustotal_min_detection', 3)
        
        # Zararlı içerik ayarları
        self.content_scan_enabled = self.config.get('content_scan_enabled', True)
        self.content_max_scan_size = self.config.get('content_max_scan_size', 5 * 1024 * 1024)  # 5 MB
        
        # Zararlı içerik kalıpları
        self.malicious_patterns = [
            # JavaScript zararlı kod kalıpları
            re.compile(r'<\s*script.*?>(.*?eval\(.*?|.*?document\.write\(.*?|.*?fromCharCode\(.*?|.*?unescape\(.*?)</script>', re.IGNORECASE | re.DOTALL),
            # İçe gömülü iframe'ler
            re.compile(r'<\s*iframe.*?src\s*=\s*["\']?https?:\/\/(?!trusted-domain\.com).*?["\']?.*?>', re.IGNORECASE | re.DOTALL),
            # Şüpheli JavaScript URL'leri
            re.compile(r'javascript:.*?(eval\(|document\.cookie|window\.location|unescape\()', re.IGNORECASE),
            # SQL injection kalıpları
            re.compile(r'(\'|")\s*(\|\||;|--|#|/\*)\s*(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER)', re.IGNORECASE),
            # XSS kalıpları
            re.compile(r'<\s*img.*?onerror\s*=.*?>', re.IGNORECASE | re.DOTALL),
            # PowerShell şifreleme komutları
            re.compile(r'powershell.*?\-enc(?:odedCommand)?\s+[A-Za-z0-9+/=]{20,}', re.IGNORECASE),
            # Base64 şifrelenmiş PE dosyaları
            re.compile(r'TVqQAAMAAAAEAAAA', re.IGNORECASE),
        ]
        
        # Şüpheli içerik kalıpları
        self.suspicious_patterns = [
            # Büyük base64 blokları
            re.compile(r'[A-Za-z0-9+/=]{100,}'),
            # Shell komutları
            re.compile(r'system\s*\(.*?\)|exec\s*\(.*?\)|shell_exec\s*\(.*?\)', re.IGNORECASE),
            # Şüpheli URL uzantıları
            re.compile(r'https?:\/\/.*?\.(tk|ml|ga|cf|gq|top|xyz)\/[^\s]*', re.IGNORECASE),
        ]
        
        # Bilinen zararlı dosya hash'leri
        self.malicious_hashes = set()
        malicious_hashes_file = self.config.get('malicious_hashes_file')
        if malicious_hashes_file and os.path.exists(malicious_hashes_file):
            with open(malicious_hashes_file, 'r') as f:
                for line in f:
                    hash_value = line.strip()
                    if len(hash_value) == 64:  # SHA-256
                        self.malicious_hashes.add(hash_value)
    
    async def scan_file(self, file_content: bytes, file_name: str) -> SecurityScanResult:
        """
        Dosya güvenliği için tarama yapar
        
        Args:
            file_content: Dosya içeriği
            file_name: Dosya adı
            
        Returns:
            SecurityScanResult: Tarama sonucu
        """
        import time
        start_time = time.time()
        
        try:
            # Dosya boyutu kontrolü
            file_size = len(file_content)
            if file_size > self.max_file_size:
                return SecurityScanResult(
                    status=ScanResult.SUSPICIOUS,
                    details={
                        "reason": "file_too_large",
                        "max_size": self.max_file_size,
                        "actual_size": file_size
                    },
                    file_type=Path(file_name).suffix.lower()[1:] if '.' in file_name else 'unknown',
                    mime_type="application/octet-stream",
                    file_size=file_size,
                    sha256=self._calculate_sha256(file_content),
                    scan_time_ms=int((time.time() - start_time) * 1000)
                )
            
            # MIME tipi kontrolü
            mime_type = self._detect_mime_type(file_content)
            if mime_type not in self.allowed_mime_types:
                return SecurityScanResult(
                    status=ScanResult.SUSPICIOUS,
                    details={
                        "reason": "invalid_mime_type",
                        "detected_mime": mime_type,
                        "allowed_mimes": self.allowed_mime_types
                    },
                    file_type=Path(file_name).suffix.lower()[1:] if '.' in file_name else 'unknown',
                    mime_type=mime_type,
                    file_size=file_size,
                    sha256=self._calculate_sha256(file_content),
                    scan_time_ms=int((time.time() - start_time) * 1000)
                )
            
            # SHA-256 hash hesapla
            file_hash = self._calculate_sha256(file_content)
            
            # Bilinen zararlı hash kontrolü
            if file_hash in self.malicious_hashes:
                return SecurityScanResult(
                    status=ScanResult.MALICIOUS,
                    details={
                        "reason": "known_malicious_hash",
                        "hash": file_hash
                    },
                    file_type=Path(file_name).suffix.lower()[1:] if '.' in file_name else 'unknown',
                    mime_type=mime_type,
                    file_size=file_size,
                    sha256=file_hash,
                    scan_time_ms=int((time.time() - start_time) * 1000)
                )
            
            # Virüs tarama
            if self.use_clamav:
                virus_result = await self._scan_with_clamav(file_content)
                if virus_result["status"] != ScanResult.CLEAN:
                    return SecurityScanResult(
                        status=virus_result["status"],
                        details=virus_result,
                        file_type=Path(file_name).suffix.lower()[1:] if '.' in file_name else 'unknown',
                        mime_type=mime_type,
                        file_size=file_size,
                        sha256=file_hash,
                        scan_time_ms=int((time.time() - start_time) * 1000)
                    )
            
            # VirusTotal API ile tarama
            if self.use_virustotal and self.virustotal_api_key:
                vt_result = await self._scan_with_virustotal(file_content, file_hash)
                if vt_result["status"] != ScanResult.CLEAN:
                    return SecurityScanResult(
                        status=vt_result["status"],
                        details=vt_result,
                        file_type=Path(file_name).suffix.lower()[1:] if '.' in file_name else 'unknown',
                        mime_type=mime_type,
                        file_size=file_size,
                        sha256=file_hash,
                        scan_time_ms=int((time.time() - start_time) * 1000)
                    )
            
            # İçerik tarama (metin formatları için)
            if self.content_scan_enabled and file_size <= self.content_max_scan_size:
                if mime_type.startswith(('text/', 'application/json', 'application/xml')) or 'document' in mime_type:
                    try:
                        text_content = file_content.decode('utf-8', errors='ignore')
                        content_result = self._scan_text_content(text_content)
                        if content_result["status"] != ScanResult.CLEAN:
                            return SecurityScanResult(
                                status=content_result["status"],
                                details=content_result,
                                file_type=Path(file_name).suffix.lower()[1:] if '.' in file_name else 'unknown',
                                mime_type=mime_type,
                                file_size=file_size,
                                sha256=file_hash,
                                scan_time_ms=int((time.time() - start_time) * 1000)
                            )
                    except Exception as e:
                        logger.warning(f"İçerik taraması sırasında hata: {e}")
            
            # Tüm kontrollerden geçti, temiz dosya
            return SecurityScanResult(
                status=ScanResult.CLEAN,
                details={"message": "File passed all security checks"},
                file_type=Path(file_name).suffix.lower()[1:] if '.' in file_name else 'unknown',
                mime_type=mime_type,
                file_size=file_size,
                sha256=file_hash,
                scan_time_ms=int((time.time() - start_time) * 1000)
            )
            
        except Exception as e:
            logger.error(f"Dosya tarama hatası: {e}")
            return SecurityScanResult(
                status=ScanResult.ERROR,
                details={"error": str(e)},
                file_type=Path(file_name).suffix.lower()[1:] if '.' in file_name else 'unknown',
                mime_type="unknown",
                file_size=len(file_content),
                sha256=self._calculate_sha256(file_content),
                scan_time_ms=int((time.time() - start_time) * 1000)
            )
    
    def _detect_mime_type(self, file_content: bytes) -> str:
        """Dosya içeriğinden MIME türü tespit eder"""
        try:
            # python-magic kullanarak MIME türü tespiti
            mime = magic.Magic(mime=True)
            return mime.from_buffer(file_content)
        except:
            # Fallback: Basit dosya başlığı kontrolü
            if file_content.startswith(b'%PDF'):
                return 'application/pdf'
            elif file_content.startswith(b'PK\x03\x04'):
                return 'application/zip'  # DOCX ve diğer Office dosyaları ZIP temelli
            else:
                # Varsayılan olarak binary kabul et
                return 'application/octet-stream'
    
    def _calculate_sha256(self, data: bytes) -> str:
        """SHA-256 hash değeri hesaplar"""
        return hashlib.sha256(data).hexdigest()
    
    async def _scan_with_clamav(self, file_content: bytes) -> Dict[str, Any]:
        """ClamAV ile virüs taraması yapar"""
        try:
            # Geçici dosya oluştur
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file_path = temp_file.name
                temp_file.write(file_content)
            
            try:
                # ClamAV socket veya executable ile tarama
                if os.path.exists(self.clamav_socket):
                    # Unix socket bağlantısı
                    command = f"clamdscan --stdout --no-summary {temp_file_path}"
                else:
                    # Komut satırı executable
                    command = f"clamscan --stdout --no-summary {temp_file_path}"
                
                # Asenkron olarak komutu çalıştır
                proc = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await proc.communicate()
                output = stdout.decode().strip()
                
                # Sonucu işle
                if "OK" in output:
                    return {"status": ScanResult.CLEAN, "message": "No threats detected"}
                else:
                    # Virüs adını çıkar
                    threat_match = re.search(r': ([^:]+) FOUND', output)
                    threat_name = threat_match.group(1) if threat_match else "Unknown threat"
                    
                    return {
                        "status": ScanResult.MALICIOUS,
                        "reason": "virus_detected",
                        "threat": threat_name,
                        "scanner": "clamav"
                    }
            finally:
                # Geçici dosyayı temizle
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                
        except Exception as e:
            logger.error(f"ClamAV tarama hatası: {e}")
            return {"status": ScanResult.ERROR, "error": str(e), "scanner": "clamav"}
    
    async def _scan_with_virustotal(self, file_content: bytes, file_hash: str) -> Dict[str, Any]:
        """VirusTotal API ile virüs taraması yapar"""
        try:
            if not self.virustotal_api_key:
                return {"status": ScanResult.ERROR, "error": "VirusTotal API key not configured", "scanner": "virustotal"}
            
            # Önce hash ile sorgu yap (API limitini korumak için)
            hash_url = f"https://www.virustotal.com/api/v3/files/{file_hash}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(hash_url, headers={"x-apikey": self.virustotal_api_key}) as response:
                    if response.status == 200:
                        # Hash bulundu, sonuçları analiz et
                        result = await response.json()
                        return self._parse_virustotal_result(result)
                    elif response.status == 404:
                        # Hash bulunamadı, dosyayı yükle
                        return await self._upload_to_virustotal(file_content, session)
                    else:
                        # API hatası
                        error_detail = await response.text()
                        return {
                            "status": ScanResult.ERROR, 
                            "error": f"VirusTotal API error: {response.status}", 
                            "detail": error_detail,
                            "scanner": "virustotal"
                        }
                        
        except Exception as e:
            logger.error(f"VirusTotal tarama hatası: {e}")
            return {"status": ScanResult.ERROR, "error": str(e), "scanner": "virustotal"}
    
    async def _upload_to_virustotal(self, file_content: bytes, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Dosyayı VirusTotal'a yükler"""
        try:
            # Upload URL al
            upload_url_endpoint = "https://www.virustotal.com/api/v3/files/upload_url"
            
            async with session.get(upload_url_endpoint, headers={"x-apikey": self.virustotal_api_key}) as response:
                if response.status != 200:
                    return {"status": ScanResult.ERROR, "error": "Failed to get upload URL", "scanner": "virustotal"}
                
                upload_url_data = await response.json()
                upload_url = upload_url_data.get("data")
                
                if not upload_url:
                    return {"status": ScanResult.ERROR, "error": "Invalid upload URL response", "scanner": "virustotal"}
                
                # Dosyayı yükle
                form_data = aiohttp.FormData()
                form_data.add_field('file', file_content, filename='scan_file')
                
                async with session.post(upload_url, data=form_data, headers={"x-apikey": self.virustotal_api_key}) as upload_response:
                    if upload_response.status != 200:
                        return {"status": ScanResult.ERROR, "error": "File upload failed", "scanner": "virustotal"}
                    
                    upload_result = await upload_response.json()
                    analysis_id = upload_result.get("data", {}).get("id")
                    
                    if not analysis_id:
                        return {"status": ScanResult.ERROR, "error": "Invalid upload response", "scanner": "virustotal"}
                    
                    # Analiz sonucunu bekleme (maksimum 3 deneme)
                    analysis_url = f"https://www.virustotal.com/api/v3/analyses/{analysis_id}"
                    
                    for attempt in range(3):
                        # Her deneme arasında bekleme süresi
                        await asyncio.sleep(5 * (attempt + 1))
                        
                        async with session.get(analysis_url, headers={"x-apikey": self.virustotal_api_key}) as analysis_response:
                            if analysis_response.status != 200:
                                continue
                                
                            analysis_data = await analysis_response.json()
                            status = analysis_data.get("data", {}).get("attributes", {}).get("status")
                            
                            if status == "completed":
                                return self._parse_virustotal_result(analysis_data)
                    
                    # Zaman aşımı, tamamlanamadı
                    return {
                        "status": ScanResult.SUSPICIOUS,
                        "reason": "scan_timeout",
                        "message": "VirusTotal analysis timeout",
                        "scanner": "virustotal"
                    }
                    
        except Exception as e:
            logger.error(f"VirusTotal yükleme hatası: {e}")
            return {"status": ScanResult.ERROR, "error": str(e), "scanner": "virustotal"}
    
    def _parse_virustotal_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """VirusTotal API sonuçlarını işler"""
        try:
            attributes = result.get("data", {}).get("attributes", {})
            
            # Tarama sonuçları
            stats = attributes.get("stats", {})
            malicious = stats.get("malicious", 0)
            suspicious = stats.get("suspicious", 0)
            undetected = stats.get("undetected", 0)
            
            total_scanners = malicious + suspicious + undetected
            
            if malicious > 0:
                # Malicious tespit edildi
                if malicious >= self.virustotal_min_detection:
                    return {
                        "status": ScanResult.MALICIOUS,
                        "reason": "viruses_detected",
                        "malicious_count": malicious,
                        "suspicious_count": suspicious,
                        "total_scanners": total_scanners,
                        "scanner": "virustotal"
                    }
                else:
                    # Eşiğin altında malicious tespit
                    return {
                        "status": ScanResult.SUSPICIOUS,
                        "reason": "low_virus_detection",
                        "malicious_count": malicious,
                        "suspicious_count": suspicious,
                        "total_scanners": total_scanners,
                        "scanner": "virustotal"
                    }
            elif suspicious > 0:
                # Sadece suspicious tespitler
                return {
                    "status": ScanResult.SUSPICIOUS,
                    "reason": "suspicious_detections",
                    "suspicious_count": suspicious,
                    "total_scanners": total_scanners,
                    "scanner": "virustotal"
                }
            else:
                # Temiz
                return {
                    "status": ScanResult.CLEAN,
                    "total_scanners": total_scanners,
                    "scanner": "virustotal"
                }
                
        except Exception as e:
            logger.error(f"VirusTotal sonuç işleme hatası: {e}")
            return {"status": ScanResult.ERROR, "error": str(e), "scanner": "virustotal"}
    
    def _scan_text_content(self, content: str) -> Dict[str, Any]:
        """Metin içeriğinde zararlı kod kalıpları arar"""
        try:
            # Zararlı kalıpları kontrol et
            for pattern in self.malicious_patterns:
                match = pattern.search(content)
                if match:
                    return {
                        "status": ScanResult.MALICIOUS,
                        "reason": "malicious_content",
                        "pattern": pattern.pattern,
                        "match": match.group(0)[:100] + "..." if len(match.group(0)) > 100 else match.group(0),
                        "scanner": "content_scan"
                    }
            
            # Şüpheli kalıpları kontrol et
            for pattern in self.suspicious_patterns:
                match = pattern.search(content)
                if match:
                    return {
                        "status": ScanResult.SUSPICIOUS,
                        "reason": "suspicious_content",
                        "pattern": pattern.pattern,
                        "match": match.group(0)[:100] + "..." if len(match.group(0)) > 100 else match.group(0),
                        "scanner": "content_scan"
                    }
            
            # Temiz
            return {"status": ScanResult.CLEAN, "scanner": "content_scan"}
            
        except Exception as e:
            logger.error(f"İçerik tarama hatası: {e}")
            return {"status": ScanResult.ERROR, "error": str(e), "scanner": "content_scan"}