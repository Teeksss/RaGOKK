# Last reviewed: 2025-04-29 13:23:09 UTC (User: TeeksssSSO)
import logging
import os
import io
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, List, BinaryIO, Union, Tuple
from pathlib import Path
import mimetypes
import hashlib
import time
import asyncio
import aiofiles
import aiofiles.os
from datetime import datetime, timedelta
from urllib.parse import urlparse, quote
import httpx

logger = logging.getLogger(__name__)

class StorageProviderType(str, Enum):
    """Depolama sağlayıcı türleri"""
    LOCAL = "local"
    S3 = "s3"
    AZURE_BLOB = "azure_blob"
    GOOGLE_CLOUD = "google_cloud"
    DROPBOX = "dropbox"
    ONEDRIVE = "onedrive"

class StorageProvider(ABC):
    """
    Depolama sağlayıcısı için temel sınıf
    
    Tüm depolama sağlayıcıları bu temel sınıfı kullanmalıdır.
    """
    
    def __init__(self, name: str, provider_type: StorageProviderType, config: Dict[str, Any]):
        """
        Args:
            name: Sağlayıcı görünen adı
            provider_type: Sağlayıcı türü
            config: Sağlayıcı yapılandırması
        """
        self.name = name
        self.provider_type = provider_type
        self.config = config
    
    @abstractmethod
    async def upload_file(self, file_data: Union[BinaryIO, bytes], destination_path: str, content_type: Optional[str] = None) -> str:
        """
        Dosya yükler
        
        Args:
            file_data: Dosya verisi
            destination_path: Hedef yolu
            content_type: Dosya içerik türü
            
        Returns:
            str: Dosya URL'si veya ID'si
        """
        pass
    
    @abstractmethod
    async def download_file(self, file_path: str) -> Tuple[BinaryIO, str]:
        """
        Dosya indirir
        
        Args:
            file_path: Dosya yolu
            
        Returns:
            Tuple[BinaryIO, str]: Dosya verisi ve içerik türü
        """
        pass
    
    @abstractmethod
    async def delete_file(self, file_path: str) -> bool:
        """
        Dosya siler
        
        Args:
            file_path: Dosya yolu
            
        Returns:
            bool: Başarılı ise True
        """
        pass
    
    @abstractmethod
    async def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Dosya meta verilerini alır
        
        Args:
            file_path: Dosya yolu
            
        Returns:
            Dict[str, Any]: Dosya meta verileri
        """
        pass
    
    @abstractmethod
    async def list_files(self, directory_path: str = "", recursive: bool = False) -> List[Dict[str, Any]]:
        """
        Dizindeki dosyaları listeler
        
        Args:
            directory_path: Dizin yolu
            recursive: Alt dizinleri de listele
            
        Returns:
            List[Dict[str, Any]]: Dosya listesi
        """
        pass
    
    @abstractmethod
    async def generate_presigned_url(self, file_path: str, expires_in: int = 3600) -> str:
        """
        Önceden imzalanmış URL oluşturur
        
        Args:
            file_path: Dosya yolu
            expires_in: Geçerlilik süresi (saniye)
            
        Returns:
            str: Önceden imzalanmış URL
        """
        pass
    
    def get_content_type(self, file_path: str, default: str = "application/octet-stream") -> str:
        """
        Dosya içerik türünü tahmin eder
        
        Args:
            file_path: Dosya yolu
            default: Varsayılan içerik türü
            
        Returns:
            str: İçerik türü
        """
        content_type, _ = mimetypes.guess_type(file_path)
        return content_type or default
    
    def get_file_extension(self, content_type: str) -> str:
        """
        İçerik türünden dosya uzantısını tahmin eder
        
        Args:
            content_type: İçerik türü
            
        Returns:
            str: Dosya uzantısı
        """
        ext = mimetypes.guess_extension(content_type)
        return ext or ""


class LocalStorageProvider(StorageProvider):
    """Yerel dosya sistemi depolama sağlayıcısı"""
    
    def __init__(
        self,
        name: str = "Local Storage",
        storage_path: str = "data/storage",
        base_url: str = "/storage",
        **kwargs
    ):
        """
        Args:
            name: Sağlayıcı görünen adı
            storage_path: Depolama dizini
            base_url: Dosya URL'leri için temel URL
        """
        config = {
            "storage_path": storage_path,
            "base_url": base_url
        }
        super().__init__(name=name, provider_type=StorageProviderType.LOCAL, config=config)
        
        # Depolama dizinini oluştur
        os.makedirs(storage_path, exist_ok=True)
    
    async def upload_file(
        self,
        file_data: Union[BinaryIO, bytes],
        destination_path: str,
        content_type: Optional[str] = None
    ) -> str:
        """Dosyayı yerel sisteme yükler"""
        try:
            # Dizin yapısını oluştur
            file_path = os.path.join(self.config["storage_path"], destination_path)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Dosyayı yaz
            if isinstance(file_data, bytes):
                # Bytes verisi
                async with aiofiles.open(file_path, "wb") as f:
                    await f.write(file_data)
            else:
                # Dosya nesnesi
                file_data.seek(0)
                async with aiofiles.open(file_path, "wb") as f:
                    while chunk := file_data.read(16384):
                        await f.write(chunk)
            
            # URL döndür
            return os.path.join(self.config["base_url"], destination_path)
        except Exception as e:
            logger.error(f"Local file upload error: {e}")
            raise IOError(f"File upload failed: {str(e)}")
    
    async def download_file(self, file_path: str) -> Tuple[BinaryIO, str]:
        """Dosyayı yerel sistemden indirir"""
        try:
            # URL'den dosya yoluna çevir
            if file_path.startswith(self.config["base_url"]):
                file_path = file_path[len(self.config["base_url"]):].lstrip("/")
            
            full_path = os.path.join(self.config["storage_path"], file_path)
            
            # Dosyanın var olup olmadığını kontrol et
            if not os.path.exists(full_path) or not os.path.isfile(full_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Dosyayı oku
            content_type = self.get_content_type(full_path)
            
            # BytesIO nesnesine oku
            async with aiofiles.open(full_path, "rb") as f:
                file_data = io.BytesIO(await f.read())
                file_data.seek(0)
            
            return file_data, content_type
        except Exception as e:
            logger.error(f"Local file download error: {e}")
            raise IOError(f"File download failed: {str(e)}")
    
    async def delete_file(self, file_path: str) -> bool:
        """Dosyayı yerel sistemden siler"""
        try:
            # URL'den dosya yoluna çevir
            if file_path.startswith(self.config["base_url"]):
                file_path = file_path[len(self.config["base_url"]):].lstrip("/")
            
            full_path = os.path.join(self.config["storage_path"], file_path)
            
            # Dosyanın var olup olmadığını kontrol et
            if not os.path.exists(full_path) or not os.path.isfile(full_path):
                return False
            
            # Dosyayı sil
            await aiofiles.os.remove(full_path)
            
            # Boş dizinleri temizle
            dir_path = os.path.dirname(full_path)
            while dir_path != self.config["storage_path"]:
                if len(os.listdir(dir_path)) == 0:
                    os.rmdir(dir_path)
                    dir_path = os.path.dirname(dir_path)
                else:
                    break
            
            return True
        except Exception as e:
            logger.error(f"Local file delete error: {e}")
            return False
    
    async def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """Dosya meta verilerini alır"""
        try:
            # URL'den dosya yoluna çevir
            if file_path.startswith(self.config["base_url"]):
                file_path = file_path[len(self.config["base_url"]):].lstrip("/")
            
            full_path = os.path.join(self.config["storage_path"], file_path)
            
            # Dosyanın var olup olmadığını kontrol et
            if not os.path.exists(full_path) or not os.path.isfile(full_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Dosya meta verilerini al
            stats = os.stat(full_path)
            
            return {
                "name": os.path.basename(file_path),
                "path": file_path,
                "url": os.path.join(self.config["base_url"], file_path),
                "size": stats.st_size,
                "created": datetime.fromtimestamp(stats.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stats.st_mtime).isoformat(),
                "content_type": self.get_content_type(full_path)
            }
        except Exception as e:
            logger.error(f"Local file metadata error: {e}")
            raise IOError(f"Failed to get file metadata: {str(e)}")
    
    async def list_files(self, directory_path: str = "", recursive: bool = False) -> List[Dict[str, Any]]:
        """Dizindeki dosyaları listeler"""
        try:
            # Dizin yolu
            dir_path = os.path.join(self.config["storage_path"], directory_path)
            
            # Dizinin var olup olmadığını kontrol et
            if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
                return []
            
            files = []
            
            # Recursive olmayan listeleme
            if not recursive:
                for item in os.listdir(dir_path):
                    item_path = os.path.join(dir_path, item)
                    rel_path = os.path.join(directory_path, item)
                    
                    if os.path.isfile(item_path):
                        stats = os.stat(item_path)
                        files.append({
                            "name