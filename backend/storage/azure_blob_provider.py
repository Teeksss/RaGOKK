# Last reviewed: 2025-04-29 13:36:58 UTC (User: TeeksssMobil)
import io
import logging
import os
from typing import Dict, Any, Optional, List, BinaryIO, Union, Tuple
from datetime import datetime, timedelta
import mimetypes
import hashlib
import asyncio

from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.storage.blob.aio import BlobServiceClient as AsyncBlobServiceClient
from azure.core.exceptions import ResourceNotFoundError

from .storage_providers import StorageProvider, StorageProviderType

logger = logging.getLogger(__name__)

class AzureBlobStorageProvider(StorageProvider):
    """Azure Blob Storage depolama sağlayıcısı"""
    
    def __init__(
        self,
        name: str = "Azure Blob Storage",
        connection_string: str = None,
        account_name: str = None,
        account_key: str = None,
        container_name: str = None,
        base_url: str = None,
        **kwargs
    ):
        """
        Args:
            name: Sağlayıcı görünen adı
            connection_string: Azure Storage bağlantı dizesi
            account_name: Azure Storage hesap adı (connection_string olmadığında)
            account_key: Azure Storage hesap anahtarı (connection_string olmadığında)
            container_name: Blob container adı
            base_url: Dosya URL'leri için temel URL (opsiyonel)
        """
        config = {
            "connection_string": connection_string,
            "account_name": account_name,
            "account_key": account_key,
            "container_name": container_name,
            "base_url": base_url
        }
        super().__init__(name=name, provider_type=StorageProviderType.AZURE_BLOB, config=config)
        
        # Senkron ve asenkron istemciler
        self._service_client = self._create_service_client()
        self._container_client = self._service_client.get_container_client(container_name)
        
        # Asenkron istemcileri başlatma için _init_async metodu kullanılacak
        self._async_service_client = None
        self._async_container_client = None
    
    def _create_service_client(self):
        """Senkron Azure Blob Service istemcisi oluşturur"""
        if self.config["connection_string"]:
            return BlobServiceClient.from_connection_string(self.config["connection_string"])
        else:
            return BlobServiceClient(
                account_url=f"https://{self.config['account_name']}.blob.core.windows.net",
                credential=self.config["account_key"]
            )
    
    async def _init_async(self):
        """Asenkron Azure Blob istemcilerini başlatır"""
        if self._async_service_client is None:
            if self.config["connection_string"]:
                self._async_service_client = AsyncBlobServiceClient.from_connection_string(
                    self.config["connection_string"]
                )
            else:
                self._async_service_client = AsyncBlobServiceClient(
                    account_url=f"https://{self.config['account_name']}.blob.core.windows.net",
                    credential=self.config["account_key"]
                )
            
            self._async_container_client = self._async_service_client.get_container_client(
                self.config["container_name"]
            )
    
    async def upload_file(
        self,
        file_data: Union[BinaryIO, bytes],
        destination_path: str,
        content_type: Optional[str] = None
    ) -> str:
        """Dosyayı Azure Blob'a yükler"""
        try:
            await self._init_async()
            
            # İçerik türünü belirle
            if not content_type:
                content_type = self.get_content_type(destination_path)
            
            # Blob istemcisi al
            blob_client = self._async_container_client.get_blob_client(destination_path)
            
            # Dosyayı yükle
            if isinstance(file_data, bytes):
                # Bytes verisi
                await blob_client.upload_blob(
                    file_data,
                    overwrite=True,
                    content_settings=ContentSettings(content_type=content_type)
                )
            else:
                # Dosya nesnesi
                file_data.seek(0)
                await blob_client.upload_blob(
                    file_data,
                    overwrite=True,
                    content_settings=ContentSettings(content_type=content_type)
                )
            
            # URL döndür
            if self.config["base_url"]:
                return f"{self.config['base_url'].rstrip('/')}/{destination_path}"
            
            return blob_client.url
        
        except Exception as e:
            logger.error(f"Azure Blob upload error: {e}")
            raise IOError(f"Azure Blob upload failed: {str(e)}")
    
    async def download_file(self, file_path: str) -> Tuple[BinaryIO, str]:
        """Dosyayı Azure Blob'dan indirir"""
        try:
            await self._init_async()
            
            # Blob adını al
            blob_name = self._get_blob_name_from_path(file_path)
            
            # Blob istemcisi al
            blob_client = self._async_container_client.get_blob_client(blob_name)
            
            # Download
            download = await blob_client.download_blob()
            data = await download.readall()
            
            # İçerik türünü al
            content_type = download.properties.content_settings.content_type
            if not content_type:
                content_type = self.get_content_type(blob_name)
            
            # BytesIO nesnesine çevir
            file_obj = io.BytesIO(data)
            file_obj.seek(0)
            
            return file_obj, content_type
        
        except ResourceNotFoundError:
            logger.error(f"Azure Blob not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
            
        except Exception as e:
            logger.error(f"Azure Blob download error: {e}")
            raise IOError(f"Azure Blob download failed: {str(e)}")
    
    async def delete_file(self, file_path: str) -> bool:
        """Dosyayı Azure Blob'dan siler"""
        try:
            await self._init_async()
            
            # Blob adını al
            blob_name = self._get_blob_name_from_path(file_path)
            
            # Blob istemcisi al
            blob_client = self._async_container_client.get_blob_client(blob_name)
            
            # Sil
            await blob_client.delete_blob()
            
            return True
        
        except ResourceNotFoundError:
            logger.warning(f"Azure Blob not found for deletion: {file_path}")
            return False
            
        except Exception as e:
            logger.error(f"Azure Blob delete error: {e}")
            return False
    
    async def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """Dosya meta verilerini alır"""
        try:
            await self._init_async()
            
            # Blob adını al
            blob_name = self._get_blob_name_from_path(file_path)
            
            # Blob istemcisi al
            blob_client = self._async_container_client.get_blob_client(blob_name)
            
            # Özelliklerini al
            properties = await blob_client.get_blob_properties()
            
            # URL oluştur
            url = blob_client.url
            if self.config["base_url"]:
                url = f"{self.config['base_url'].rstrip('/')}/{blob_name}"
            
            return {
                "name": blob_name.split("/")[-1],
                "path": blob_name,
                "url": url,
                "size": properties.size,
                "created": properties.creation_time.isoformat() if properties.creation_time else None,
                "modified": properties.last_modified.isoformat() if properties.last_modified else None,
                "content_type": properties.content_settings.content_type,
                "etag": properties.etag,
                "metadata": properties.metadata
            }
        
        except ResourceNotFoundError:
            logger.error(f"Azure Blob not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
            
        except Exception as e:
            logger.error(f"Azure Blob metadata error: {e}")
            raise IOError(f"Failed to get Azure Blob metadata: {str(e)}")
    
    async def list_files(self, directory_path: str = "", recursive: bool = False) -> List[Dict[str, Any]]:
        """Dizindeki dosyaları listeler"""
        try:
            await self._init_async()
            
            # Prefix oluştur
            prefix = directory_path
            if prefix and not prefix.endswith("/"):
                prefix += "/"
            
            # Blob'ları listele
            files = []
            
            # Recursive listesini al
            if recursive:
                blobs = self._async_container_client.list_blobs(name_starts_with=prefix)
            else:
                # İlk seviyeyi al (delimitera göre gruplama)
                blobs = []
                
                # Klasörleri bulmak için
                async for item in self._async_container_client.walk_blobs(
                    name_starts_with=prefix,
                    delimiter="/"
                ):
                    if hasattr(item, "name"):  # Blob
                        blobs.append(item)
                    elif hasattr(item, "prefix"):  # BlobPrefix
                        files.append({
                            "name": item.prefix.rstrip("/").split("/")[-1],
                            "path": item.prefix,
                            "size": 0,
                            "is_dir": True,
                            "created": None,
                            "modified": None
                        })
            
            # Blob'ları işle
            async for blob in blobs:
                # Klasörleri atlayalım (blob.name dizin ise)
                if blob.name.endswith("/"):
                    continue
                
                # URL oluştur
                url = f"https://{self.config['account_name']}.blob.core.windows.net/{self.config['container_name']}/{blob.name}"
                if self.config["base_url"]:
                    url = f"{self.config['base_url'].rstrip('/')}/{blob.name}"
                
                files.append({
                    "name": blob.name.split("/")[-1],
                    "path": blob.name,
                    "url": url,
                    "size": blob.size,
                    "is_dir": False,
                    "created": blob.creation_time.isoformat() if hasattr(blob, "creation_time") and blob.creation_time else None,
                    "modified": blob.last_modified.isoformat() if blob.last_modified else None,
                    "etag": blob.etag,
                    "content_type": getattr(blob.properties.content_settings, "content_type", self.get_content_type(blob.name))
                })
            
            return files
        
        except Exception as e:
            logger.error(f"Azure Blob list files error: {e}")
            raise IOError(f"Failed to list Azure Blob files: {str(e)}")
    
    async def generate_presigned_url(self, file_path: str, expires_in: int = 3600) -> str:
        """Önceden imzalanmış URL (SAS) oluşturur"""
        try:
            await self._init_async()
            
            # Blob adını al
            blob_name = self._get_blob_name_from_path(file_path)
            
            # Blob istemcisi al
            blob_client = self._async_container_client.get_blob_client(blob_name)
            
            # SAS token oluştur (senkron API kullan)
            from azure.storage.blob import generate_blob_sas, BlobSasPermissions
            from datetime import datetime, timedelta
            
            # User delegation key alma
            start_time = datetime.utcnow() - timedelta(minutes=5)
            expiry_time = datetime.utcnow() + timedelta(seconds=expires_in)
            
            # Senkron istemci kullanarak SAS token oluştur
            sync_blob_client = self._container_client.get_blob_client(blob_name)
            
            sas_token = generate_blob_sas(
                account_name=self.config["account_name"],
                container_name=self.config["container_name"],
                blob_name=blob_name,
                account_key=self.config["account_key"],
                permission=BlobSasPermissions(read=True),
                expiry=expiry_time
            )
            
            # SAS URL oluştur
            sas_url = f"{sync_blob_client.url}?{sas_token}"
            
            return sas_url
        
        except Exception as e:
            logger.error(f"Azure Blob presigned URL error: {e}")
            raise IOError(f"Failed to generate Azure Blob presigned URL: {str(e)}")
    
    def _get_blob_name_from_path(self, file_path: str) -> str:
        """URL veya yoldan Azure Blob adını çıkarır"""
        # URL kontrolü
        if file_path.startswith("http"):
            from urllib.parse import urlparse
            
            # Base URL ile başlıyorsa
            if self.config["base_url"] and file_path.startswith(self.config["base_url"]):
                base = self.config["base_url"].rstrip("/")
                return file_path[len(base) + 1:] if file_path.startswith(f"{base}/") else file_path[len(base):]
            
            # Azure URL analizi
            parsed = urlparse(file_path)
            path = parsed.path
            
            # Container adıyla path'i analiz et
            container_name = self.config["container_name"]
            if path.startswith(f"/{container_name}/"):
                return path[len(container_name) + 2:]
            
            # Path başındaki / karakterini temizle
            if path.startswith("/"):
                return path[1:]
            
            return path
        
        # Sadece key verilmişse
        return file_path