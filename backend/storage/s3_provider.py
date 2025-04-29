# Last reviewed: 2025-04-29 13:36:58 UTC (User: TeeksssMobil)
import io
import logging
import boto3
import botocore
from typing import Dict, Any, Optional, List, BinaryIO, Union, Tuple
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
import mimetypes
import hashlib

from .storage_providers import StorageProvider, StorageProviderType

logger = logging.getLogger(__name__)

class S3StorageProvider(StorageProvider):
    """Amazon S3 depolama sağlayıcısı"""
    
    def __init__(
        self,
        name: str = "Amazon S3",
        bucket_name: str = None,
        region_name: str = None,
        aws_access_key_id: str = None,
        aws_secret_access_key: str = None,
        endpoint_url: str = None,
        base_url: str = None,
        use_path_style: bool = False,
        **kwargs
    ):
        """
        Args:
            name: Sağlayıcı görünen adı
            bucket_name: S3 bucket adı
            region_name: AWS bölgesi
            aws_access_key_id: AWS erişim anahtarı
            aws_secret_access_key: AWS gizli anahtarı
            endpoint_url: Özel S3 endpoint URL'si (MinIO, DigitalOcean Spaces, vb. için)
            base_url: Dosya URL'leri için temel URL
            use_path_style: Path-style URL'leri kullan (MinIO için True olmalı)
        """
        config = {
            "bucket_name": bucket_name,
            "region_name": region_name,
            "aws_access_key_id": aws_access_key_id,
            "aws_secret_access_key": aws_secret_access_key,
            "endpoint_url": endpoint_url,
            "base_url": base_url,
            "use_path_style": use_path_style
        }
        super().__init__(name=name, provider_type=StorageProviderType.S3, config=config)
        
        # S3 istemcisi oluştur
        self._s3 = self._create_s3_client()
    
    def _create_s3_client(self):
        """S3 istemcisi oluşturur"""
        config = boto3.session.Config(
            signature_version='s3v4',
            s3={'addressing_style': 'path' if self.config["use_path_style"] else 'virtual'}
        )
        
        return boto3.client(
            's3',
            region_name=self.config["region_name"],
            aws_access_key_id=self.config["aws_access_key_id"],
            aws_secret_access_key=self.config["aws_secret_access_key"],
            endpoint_url=self.config["endpoint_url"],
            config=config
        )
    
    async def upload_file(
        self,
        file_data: Union[BinaryIO, bytes],
        destination_path: str,
        content_type: Optional[str] = None
    ) -> str:
        """Dosyayı S3'e yükler"""
        try:
            # İçerik türünü belirle
            if not content_type:
                content_type = self.get_content_type(destination_path)
            
            # ExtraArgs hazırla
            extra_args = {
                "ContentType": content_type
            }
            
            # Dosyayı yükle
            import asyncio
            
            if isinstance(file_data, bytes):
                # Bytes verisi
                file_obj = io.BytesIO(file_data)
                
                await asyncio.to_thread(
                    self._s3.upload_fileobj,
                    file_obj,
                    self.config["bucket_name"],
                    destination_path,
                    ExtraArgs=extra_args
                )
            else:
                # Dosya nesnesi
                file_data.seek(0)
                
                await asyncio.to_thread(
                    self._s3.upload_fileobj,
                    file_data,
                    self.config["bucket_name"],
                    destination_path,
                    ExtraArgs=extra_args
                )
            
            # URL döndür
            if self.config["base_url"]:
                return f"{self.config['base_url'].rstrip('/')}/{destination_path}"
            
            # URL'yi oluştur (endpoint belirtilmişse özelleştirilmiş URL)
            if self.config["endpoint_url"]:
                host = self.config["endpoint_url"].rstrip("/")
                return f"{host}/{self.config['bucket_name']}/{destination_path}"
            
            # AWS S3 için varsayılan URL
            region = self.config["region_name"]
            bucket = self.config["bucket_name"]
            return f"https://{bucket}.s3.{region}.amazonaws.com/{destination_path}"
        
        except Exception as e:
            logger.error(f"S3 file upload error: {e}")
            raise IOError(f"S3 upload failed: {str(e)}")
    
    async def download_file(self, file_path: str) -> Tuple[BinaryIO, str]:
        """Dosyayı S3'ten indirir"""
        try:
            # URL'den dosya yolunu ayıkla
            key = self._get_key_from_path(file_path)
            
            # BytesIO nesnesi oluştur
            file_obj = io.BytesIO()
            
            # Dosyayı indir
            import asyncio
            await asyncio.to_thread(
                self._s3.download_fileobj,
                self.config["bucket_name"],
                key,
                file_obj
            )
            
            # İçerik türünü al
            response = await asyncio.to_thread(
                self._s3.head_object,
                Bucket=self.config["bucket_name"],
                Key=key
            )
            
            content_type = response.get("ContentType", self.get_content_type(key))
            
            file_obj.seek(0)
            return file_obj, content_type
        
        except Exception as e:
            logger.error(f"S3 file download error: {e}")
            raise IOError(f"S3 download failed: {str(e)}")
    
    async def delete_file(self, file_path: str) -> bool:
        """Dosyayı S3'ten siler"""
        try:
            # URL'den dosya yolunu ayıkla
            key = self._get_key_from_path(file_path)
            
            # Dosyayı sil
            import asyncio
            await asyncio.to_thread(
                self._s3.delete_object,
                Bucket=self.config["bucket_name"],
                Key=key
            )
            
            return True
        
        except Exception as e:
            logger.error(f"S3 file delete error: {e}")
            return False
    
    async def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """Dosya meta verilerini alır"""
        try:
            # URL'den dosya yolunu ayıkla
            key = self._get_key_from_path(file_path)
            
            # Meta verileri al
            import asyncio
            response = await asyncio.to_thread(
                self._s3.head_object,
                Bucket=self.config["bucket_name"],
                Key=key
            )
            
            # URL oluştur
            url = file_path
            if not url.startswith("http"):
                if self.config["base_url"]:
                    url = f"{self.config['base_url'].rstrip('/')}/{key}"
                else:
                    region = self.config["region_name"]
                    bucket = self.config["bucket_name"]
                    url = f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
            
            return {
                "name": key.split("/")[-1],
                "path": key,
                "url": url,
                "size": response.get("ContentLength", 0),
                "created": response.get("LastModified").isoformat(),
                "modified": response.get("LastModified").isoformat(),
                "content_type": response.get("ContentType", self.get_content_type(key)),
                "etag": response.get("ETag", "").strip('"'),
                "metadata": response.get("Metadata", {})
            }
        
        except Exception as e:
            logger.error(f"S3 file metadata error: {e}")
            raise IOError(f"Failed to get S3 file metadata: {str(e)}")
    
    async def list_files(self, directory_path: str = "", recursive: bool = False) -> List[Dict[str, Any]]:
        """Dizindeki dosyaları listeler"""
        try:
            # Prefix ve delimiter ayarla
            prefix = directory_path
            if prefix and not prefix.endswith("/"):
                prefix += "/"
            
            delimiter = "/" if not recursive else None
            
            # Dosyaları listele
            import asyncio
            paginator = self._s3.get_paginator("list_objects_v2")
            
            page_iterator = paginator.paginate(
                Bucket=self.config["bucket_name"],
                Prefix=prefix,
                Delimiter=delimiter
            )
            
            files = []
            
            async for page in page_iterator:
                # Klasörleri işle
                common_prefixes = page.get("CommonPrefixes", [])
                for cp in common_prefixes:
                    prefix_path = cp.get("Prefix", "")
                    name = prefix_path.rstrip("/").split("/")[-1]
                    
                    files.append({
                        "name": name,
                        "path": prefix_path,
                        "size": 0,
                        "is_dir": True,
                        "created": None,
                        "modified": None
                    })
                
                # Dosyaları işle
                for obj in page.get("Contents", []):
                    key = obj.get("Key")
                    
                    # Dizin ise atla (boş dizinleri temsil eden nesneler)
                    if key.endswith("/"):
                        continue
                    
                    name = key.split("/")[-1]
                    
                    # URL oluştur
                    url = key
                    if self.config["base_url"]:
                        url = f"{self.config['base_url'].rstrip('/')}/{key}"
                    else:
                        region = self.config["region_name"]
                        bucket = self.config["bucket_name"]
                        url = f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
                    
                    files.append({
                        "name": name,
                        "path": key,
                        "url": url,
                        "size": obj.get("Size", 0),
                        "is_dir": False,
                        "created": None,
                        "modified": obj.get("LastModified").isoformat() if obj.get("LastModified") else None,
                        "etag": obj.get("ETag", "").strip('"'),
                        "content_type": self.get_content_type(key)
                    })
            
            return files
        
        except Exception as e:
            logger.error(f"S3 list files error: {e}")
            raise IOError(f"Failed to list S3 files: {str(e)}")
    
    async def generate_presigned_url(self, file_path: str, expires_in: int = 3600) -> str:
        """Önceden imzalanmış URL oluşturur"""
        try:
            # URL'den dosya yolunu ayıkla
            key = self._get_key_from_path(file_path)
            
            # Presigned URL oluştur
            import asyncio
            url = await asyncio.to_thread(
                self._s3.generate_presigned_url,
                'get_object',
                Params={
                    'Bucket': self.config["bucket_name"],
                    'Key': key
                },
                ExpiresIn=expires_in
            )
            
            return url
        
        except Exception as e:
            logger.error(f"S3 presigned URL error: {e}")
            raise IOError(f"Failed to generate presigned URL: {str(e)}")
    
    def _get_key_from_path(self, file_path: str) -> str:
        """URL veya yoldan S3 nesne anahtarını çıkarır"""
        # URL kontrolü
        if file_path.startswith("http"):
            from urllib.parse import urlparse
            
            # Base URL ile başlıyorsa
            if self.config["base_url"] and file_path.startswith(self.config["base_url"]):
                base = self.config["base_url"].rstrip("/")
                return file_path[len(base) + 1:] if file_path.startswith(f"{base}/") else file_path[len(base):]
            
            # Endpoint kontrolü
            parsed = urlparse(file_path)
            path = parsed.path
            
            # Bucket adı path'de varsa çıkar
            bucket_name = self.config["bucket_name"]
            if path.startswith(f"/{bucket_name}/"):
                return path[len(bucket_name) + 2:]
            
            if path.startswith("/"):
                return path[1:]
            
            return path
        
        # Sadece key verilmişse
        return file_path