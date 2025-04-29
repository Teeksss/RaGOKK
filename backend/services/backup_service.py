# Last reviewed: 2025-04-29 13:44:37 UTC (User: TeeksssVeritabanı)
import os
import logging
import asyncio
import aioboto3
import aiofiles
import json
import tempfile
import tarfile
import shutil
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
import subprocess
from pathlib import Path
import croniter
import signal
from contextlib import asynccontextmanager

from ..config import settings
from ..db.session import engine

logger = logging.getLogger(__name__)

class BackupService:
    """
    Veritabanı ve dosya yedekleme servisi
    
    Özellikleri:
    - PostgreSQL veritabanı yedeği (pg_dump kullanarak)
    - Dosya depolama yedeği (S3, Azure Blob, yerel dosya sistemi)
    - Otomatik yedekleme zamanlaması (cron expression ile)
    - Yedekleme rotasyonu (eski yedeklemeler otomatik silinir)
    - Zamanlama ve durum bilgisi
    """
    
    def __init__(self):
        """Yedekleme servisi başlatılır"""
        self.backup_path = settings.BACKUP_PATH
        self.s3_bucket = settings.BACKUP_S3_BUCKET
        self.s3_prefix = settings.BACKUP_S3_PREFIX
        self.pg_host = settings.DATABASE_HOST
        self.pg_port = settings.DATABASE_PORT
        self.pg_user = settings.DATABASE_USER
        self.pg_password = settings.DATABASE_PASSWORD
        self.pg_db = settings.DATABASE_NAME
        
        # Yedekleme periyodu ayarları
        self.daily_retention = settings.BACKUP_DAILY_RETENTION  # 7 gün
        self.weekly_retention = settings.BACKUP_WEEKLY_RETENTION  # 4 hafta
        self.monthly_retention = settings.BACKUP_MONTHLY_RETENTION  # 12 ay
        
        # Yedekleme zamanlaması (cron expression)
        self.backup_schedule = settings.BACKUP_SCHEDULE
        
        # İşlem durumu
        self.is_running = False
        self.last_backup_time = None
        self.last_backup_status = None
        self.last_backup_error = None
        self.next_backup_time = None
        
        # Yedekleme dizinini oluştur
        os.makedirs(self.backup_path, exist_ok=True)
        
        # S3 session
        self.s3_session = None
        
        # Zamanlamayı başlat
        if self.backup_schedule:
            self._update_next_backup_time()
    
    @asynccontextmanager
    async def _get_s3_client(self):
        """S3 istemcisi oluştur"""
        if not self.s3_session:
            self.s3_session = aioboto3.Session(
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION_NAME
            )
        
        async with self.s3_session.client('s3') as s3_client:
            yield s3_client
    
    async def start(self):
        """Yedekleme servisini başlat"""
        if settings.BACKUP_ENABLED:
            logger.info("Backup service starting...")
            
            # Zamanlayıcı başlatma
            asyncio.create_task(self._backup_scheduler())
    
    async def stop(self):
        """Yedekleme servisini durdur"""
        self.is_running = False
        logger.info("Backup service stopped.")
    
    async def _backup_scheduler(self):
        """Zamanlanmış yedekleme görevini çalıştır"""
        self.is_running = True
        
        while self.is_running:
            now = datetime.now()
            
            if self.next_backup_time and now >= self.next_backup_time:
                # Yedekleme zamanı geldi
                logger.info(f"Scheduled backup starting at {now}")
                try:
                    await self.perform_backup()
                except Exception as e:
                    logger.error(f"Scheduled backup failed: {str(e)}")
                
                # Sonraki yedekleme zamanını güncelle
                self._update_next_backup_time()
            
            # 1 dakika bekleyelim ve tekrar kontrol edelim
            await asyncio.sleep(60)
    
    def _update_next_backup_time(self):
        """Sonraki yedekleme zamanını hesapla"""
        if not self.backup_schedule:
            logger.warning("No backup schedule configured, automatic backups disabled.")
            return
        
        cron = croniter.croniter(self.backup_schedule, datetime.now())
        self.next_backup_time = cron.get_next(datetime)
        logger.info(f"Next scheduled backup: {self.next_backup_time}")
    
    async def perform_backup(self) -> Dict[str, Any]:
        """
        Tam sistem yedeğini gerçekleştir
        
        Returns:
            Dict[str, Any]: Yedekleme sonuçları
        """
        try:
            start_time = datetime.now()
            logger.info(f"Starting full backup at {start_time}")
            
            self.is_running = True
            self.last_backup_status = "running"
            
            # Yedek klasörünü oluştur
            timestamp = start_time.strftime("%Y%m%d_%H%M%S")
            backup_dir = os.path.join(self.backup_path, f"backup_{timestamp}")
            os.makedirs(backup_dir, exist_ok=True)
            
            # Yedekle
            db_backup_file = await self._backup_database(backup_dir, timestamp)
            storage_backup_manifest = await self._backup_storage(backup_dir, timestamp)
            
            # Metadata oluştur
            metadata = {
                "timestamp": timestamp,
                "start_time": start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "database": {
                    "file": os.path.basename(db_backup_file),
                    "size": os.path.getsize(db_backup_file) if os.path.exists(db_backup_file) else 0
                },
                "storage": {
                    "manifest": os.path.basename(storage_backup_manifest),
                    "count": 0,
                    "size": 0
                }
            }
            
            # Storage metadata güncellemesi
            if os.path.exists(storage_backup_manifest):
                async with aiofiles.open(storage_backup_manifest, 'r') as f:
                    storage_data = json.loads(await f.read())
                    metadata["storage"]["count"] = len(storage_data.get("files", []))
                    metadata["storage"]["size"] = storage_data.get("total_size", 0)
            
            # Metadata kaydet
            metadata_file = os.path.join(backup_dir, "metadata.json")
            async with aiofiles.open(metadata_file, 'w') as f:
                await f.write(json.dumps(metadata, indent=2))
            
            # Yedekleri arşivle
            archive_file = await self._create_archive(backup_dir, timestamp)
            
            # S3'e yükle (yapılandırılmışsa)
            if self.s3_bucket:
                await self._upload_to_s3(archive_file, timestamp)
            
            # Geçici klasörü temizle
            shutil.rmtree(backup_dir)
            
            # Yedek rotasyonu
            await self._rotate_backups()
            
            # Durum güncelle
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            self.last_backup_time = end_time
            self.last_backup_status = "success"
            self.last_backup_error = None
            
            logger.info(f"Backup completed successfully in {duration:.2f} seconds")
            
            return {
                "status": "success",
                "timestamp": timestamp,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration": duration,
                "database": metadata["database"],
                "storage": metadata["storage"],
                "archive": os.path.basename(archive_file),
                "archive_size": os.path.getsize(archive_file) if os.path.exists(archive_file) else 0
            }
            
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            self.last_backup_status = "error"
            self.last_backup_error = str(e)
            
            return {
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
        finally:
            self.is_running = False
    
    async def _backup_database(self, backup_dir: str, timestamp: str) -> str:
        """
        Veritabanı yedeği oluştur
        
        Args:
            backup_dir: Yedek dizini
            timestamp: Zaman damgası
            
        Returns:
            str: Yedek dosyasının yolu
        """
        logger.info("Starting database backup...")
        db_backup_file = os.path.join(backup_dir, f"database_{timestamp}.sql.gz")
        
        # pg_dump komutunu oluştur
        cmd = [
            "pg_dump",
            f"--host={self.pg_host}",
            f"--port={self.pg_port}",
            f"--username={self.pg_user}",
            "--format=c",  # Custom format (compressed)
            "--verbose",
            "--file", db_backup_file,
            self.pg_db
        ]
        
        # Ortam değişkenlerini ayarla (şifre)
        env = os.environ.copy()
        env["PGPASSWORD"] = self.pg_password
        
        # pg_dump çalıştır
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error = stderr.decode()
            logger.error(f"Database backup failed: {error}")
            raise Exception(f"Database backup failed: {error}")
        
        logger.info(f"Database backup completed: {db_backup_file}")
        return db_backup_file
    
    async def _backup_storage(self, backup_dir: str, timestamp: str) -> str:
        """
        Dosya depolama yedeği oluştur
        
        Args:
            backup_dir: Yedek dizini
            timestamp: Zaman damgası
            
        Returns:
            str: Manifest dosyasının yolu
        """
        logger.info("Starting storage backup...")
        
        # Yapılandırma okuma
        storage_path = settings.STORAGE_PATH
        if not os.path.exists(storage_path):
            logger.warning(f"Storage path does not exist: {storage_path}")
            return ""
        
        # Manifest oluştur
        storage_dir = os.path.join(backup_dir, "storage")
        os.makedirs(storage_dir, exist_ok=True)
        
        manifest = {
            "timestamp": timestamp,
            "files": [],
            "total_size": 0
        }
        
        # Dosyaları kopyala
        total_size = 0
        file_count = 0
        
        for root, _, files in os.walk(storage_path):
            for file in files:
                src_path = os.path.join(root, file)
                rel_path = os.path.relpath(src_path, storage_path)
                dst_path = os.path.join(storage_dir, rel_path)
                
                # Hedef dizini oluştur
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                
                # Dosyayı kopyala
                try:
                    file_size = os.path.getsize(src_path)
                    shutil.copy2(src_path, dst_path)
                    
                    manifest["files"].append({
                        "path": rel_path,
                        "size": file_size,
                        "mtime": datetime.fromtimestamp(os.path.getmtime(src_path)).isoformat()
                    })
                    
                    total_size += file_size
                    file_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to backup file {src_path}: {str(e)}")
        
        manifest["total_size"] = total_size
        manifest["file_count"] = file_count
        
        # Manifest'i kaydet
        manifest_file = os.path.join(backup_dir, f"storage_manifest_{timestamp}.json")
        async with aiofiles.open(manifest_file, 'w') as f:
            await f.write(json.dumps(manifest, indent=2))
        
        logger.info(f"Storage backup completed: {file_count} files, {total_size} bytes")
        return manifest_file
    
    async def _create_archive(self, backup_dir: str, timestamp: str) -> str:
        """
        Yedekleri tek bir arşiv dosyasına sıkıştır
        
        Args:
            backup_dir: Yedek dizini
            timestamp: Zaman damgası
            
        Returns:
            str: Arşiv dosyasının yolu
        """
        logger.info("Creating backup archive...")
        
        archive_file = os.path.join(self.backup_path, f"ragbase_backup_{timestamp}.tar.gz")
        
        # tar.gz oluştur
        with tarfile.open(archive_file, "w:gz") as tar:
            tar.add(backup_dir, arcname=os.path.basename(backup_dir))
        
        logger.info(f"Backup archive created: {archive_file}")
        return archive_file
    
    async def _upload_to_s3(self, file_path: str, timestamp: str) -> str:
        """
        Yedekleri S3'e yükle
        
        Args:
            file_path: Yüklenecek dosya yolu
            timestamp: Zaman damgası
            
        Returns:
            str: S3 URL'si
        """
        if not self.s3_bucket:
            logger.warning("S3 backup disabled (no bucket configured)")
            return ""
        
        logger.info(f"Uploading backup to S3: {self.s3_bucket}")
        
        try:
            file_name = os.path.basename(file_path)
            s3_key = f"{self.s3_prefix}/{timestamp}/{file_name}" if self.s3_prefix else f"{timestamp}/{file_name}"
            
            async with self._get_s3_client() as s3:
                # S3'e yükle
                with open(file_path, 'rb') as f:
                    await s3.upload_fileobj(
                        f,
                        self.s3_bucket,
                        s3_key,
                        ExtraArgs={
                            'ServerSideEncryption': 'AES256',
                            'ContentType': 'application/gzip'
                        }
                    )
            
            s3_url = f"s3://{self.s3_bucket}/{s3_key}"
            logger.info(f"Backup uploaded to S3: {s3_url}")
            
            return s3_url
            
        except Exception as e:
            logger.error(f"Failed to upload backup to S3: {str(e)}")
            raise
    
    async def _rotate_backups(self) -> Dict[str, int]:
        """
        Eski yedekleri sil (yedek rotasyonu)
        
        Returns:
            Dict[str, int]: Silinen yedek sayısı
        """
        logger.info("Starting backup rotation...")
        
        now = datetime.now()
        deleted = {"daily": 0, "weekly": 0, "monthly": 0}
        
        # Yerel yedekleri listele
        backup_files = []
        for f in os.listdir(self.backup_path):
            if f.startswith("ragbase_backup_") and f.endswith(".tar.gz"):
                file_path = os.path.join(self.backup_path, f)
                try:
                    timestamp_str = f.replace("ragbase_backup_", "").replace(".tar.gz", "")
                    timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    backup_files.append({
                        "path": file_path,
                        "timestamp": timestamp,
                        "age_days": (now - timestamp).days
                    })
                except ValueError:
                    logger.warning(f"Could not parse timestamp from backup file: {f}")
        
        # Eski günlük yedekler
        if self.daily_retention > 0:
            daily_cutoff = now - timedelta(days=self.daily_retention)
            for backup in backup_files:
                # Haftalık veya aylık yedek ise atla
                if backup["timestamp"].weekday() == 6 or backup["timestamp"].day == 1:
                    continue
                
                if backup["timestamp"] < daily_cutoff:
                    await self._delete_backup(backup["path"])
                    deleted["daily"] += 1
        
        # Eski haftalık yedekler
        if self.weekly_retention > 0:
            weekly_cutoff = now - timedelta(weeks=self.weekly_retention)
            for backup in backup_files:
                # Sadece haftalık yedekler (Pazar günleri)
                if backup["timestamp"].weekday() != 6:
                    continue
                
                # Aylık yedek ise atla
                if backup["timestamp"].day <= 7:
                    continue
                
                if backup["timestamp"] < weekly_cutoff:
                    await self._delete_backup(backup["path"])
                    deleted["weekly"] += 1
        
        # Eski aylık yedekler
        if self.monthly_retention > 0:
            monthly_cutoff = now - timedelta(days=30 * self.monthly_retention)
            for backup in backup_files:
                # Sadece aylık yedekler (ayın ilk günü)
                if backup["timestamp"].day != 1:
                    continue
                
                if backup["timestamp"] < monthly_cutoff:
                    await self._delete_backup(backup["path"])
                    deleted["monthly"] += 1
        
        # S3'teki yedekleri döndür
        if self.s3_bucket:
            await self._rotate_s3_backups()
        
        logger.info(f"Backup rotation completed: deleted {sum(deleted.values())} old backups")
        return deleted
    
    async def _delete_backup(self, file_path: str) -> bool:
        """
        Yerel yedek dosyasını sil
        
        Args:
            file_path: Silinecek dosya yolu
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            os.remove(file_path)
            logger.info(f"Deleted old backup: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete backup {file_path}: {str(e)}")
            return False
    
    async def _rotate_s3_backups(self) -> Dict[str, int]:
        """
        S3'teki eski yedekleri sil
        
        Returns:
            Dict[str, int]: Silinen yedek sayısı
        """
        if not self.s3_bucket:
            return {"daily": 0, "weekly": 0, "monthly": 0}
        
        logger.info(f"Starting S3 backup rotation in {self.s3_bucket}...")
        
        now = datetime.now()
        deleted = {"daily": 0, "weekly": 0, "monthly": 0}
        
        try:
            # S3 yedeklerini listele
            async with self._get_s3_client() as s3:
                prefix = f"{self.s3_prefix}/" if self.s3_prefix else ""
                response = await s3.list_objects_v2(Bucket=self.s3_bucket, Prefix=prefix)
                
                if "Contents" not in response:
                    logger.warning(f"No backups found in S3: {self.s3_bucket}/{prefix}")
                    return deleted
                
                backups = []
                for obj in response["Contents"]:
                    key = obj["Key"]
                    if "ragbase_backup_" in key and key.endswith(".tar.gz"):
                        try:
                            # Timestamp'i çıkar
                            parts = key.split("/")
                            timestamp_str = parts[-2] if len(parts) > 1 else parts[0]
                            timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                            
                            backups.append({
                                "key": key,
                                "timestamp": timestamp,
                                "age_days": (now - timestamp).days
                            })
                        except (IndexError, ValueError):
                            logger.warning(f"Could not parse timestamp from S3 key: {key}")
                
                # Aynı silme mantığı uygulanır
                # Günlük, haftalık ve aylık yedekler için rotasyon kuralları
                
                # Silme işlemi
                for backup in backups:
                    if await self._should_delete_backup(backup["timestamp"]):
                        # Dosyayı sil
                        await s3.delete_object(Bucket=self.s3_bucket, Key=backup["key"])
                        
                        # Kategoriye göre sayaç artır
                        if backup["timestamp"].day == 1:
                            deleted["monthly"] += 1
                        elif backup["timestamp"].weekday() == 6:
                            deleted["weekly"] += 1
                        else:
                            deleted["daily"] += 1
                            
                        logger.info(f"Deleted old S3 backup: {backup['key']}")
            
            logger.info(f"S3 backup rotation completed: deleted {sum(deleted.values())} old backups")
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to rotate S3 backups: {str(e)}")
            return deleted
    
    async def _should_delete_backup(self, timestamp: datetime) -> bool:
        """
        Yedek silme kurallarına göre silinip silinmemesi gerektiğini belirler
        
        Args:
            timestamp: Yedek zaman damgası
            
        Returns:
            bool: Silinmeli ise True
        """
        now = datetime.now()
        
        # Aylık yedek mi?
        if timestamp.day == 1:
            # Aylık retention süresi geçmiş mi?
            monthly_cutoff = now - timedelta(days=30 * self.monthly_retention)
            return timestamp < monthly_cutoff
        
        # Haftalık yedek mi? (Pazar günü)
        if timestamp.weekday() == 6:
            # Haftalık retention süresi geçmiş mi?
            weekly_cutoff = now - timedelta(weeks=self.weekly_retention)
            return timestamp < weekly_cutoff
        
        # Günlük yedek
        daily_cutoff = now - timedelta(days=self.daily_retention)
        return timestamp < daily_cutoff
    
    async def get_backup_list(self) -> List[Dict[str, Any]]:
        """
        Mevcut yedeklerin listesini döndür
        
        Returns:
            List[Dict[str, Any]]: Yedek listesi
        """
        backups = []
        
        # Yerel yedekleri listele
        for f in os.listdir(self.backup_path):
            if f.startswith("ragbase_backup_") and f.endswith(".tar.gz"):
                file_path = os.path.join(self.backup_path, f)
                try:
                    timestamp_str = f.replace("ragbase_backup_", "").replace(".tar.gz", "")
                    timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    
                    backup_info = {
                        "id": timestamp_str,
                        "timestamp": timestamp.isoformat(),
                        "size": os.path.getsize(file_path),
                        "type": "local",
                        "file": f
                    }
                    
                    # Metadata dosyasını kontrol et
                    metadata_path = os.path.join(self.backup_path, f"backup_{timestamp_str}", "metadata.json")
                    if os.path.exists(metadata_path):
                        with open(metadata_path, 'r') as mf:
                            metadata = json.load(mf)
                            backup_info["metadata"] = metadata
                    
                    backups.append(backup_info)
                    
                except (ValueError, FileNotFoundError) as e:
                    logger.warning(f"Error processing backup file {f}: {str(e)}")
        
        # S3 yedekleri de listelenebilir
        
        # Timestamp'e göre sırala (yeniden eskiye)
        backups.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return backups
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Yedekleme servisinin durumunu al
        
        Returns:
            Dict[str, Any]: Durum bilgisi
        """
        return {
            "enabled": settings.BACKUP_ENABLED,
            "is_running": self.is_running,
            "last_backup_time": self.last_backup_time.isoformat() if self.last_backup_time else None,
            "last_backup_status": self.last_backup_status,
            "last_backup_error": self.last_backup_error,
            "next_backup_time": self.next_backup_time.isoformat() if self.next_backup_time else None,
            "schedule": self.backup_schedule,
            "s3_enabled": bool(self.s3_bucket),
            "retention": {
                "daily": self.daily_retention,
                "weekly": self.weekly_retention,
                "monthly": self.monthly_retention
            }
        }
    
    async def restore_backup(self, backup_id: str, restore_db: bool = True, restore_storage: bool = True) -> Dict[str, Any]:
        """
        Yedeği geri yükle
        
        Args:
            backup_id: Yedek ID'si (timestamp)
            restore_db: Veritabanını geri yükle
            restore_storage: Dosya depolamayı geri yükle
            
        Returns:
            Dict[str, Any]: Geri yükleme sonuçları
        """
        logger.info(f"Starting restore from backup: {backup_id}")
        
        try:
            # Yedek dosyasını bul
            backup_file = os.path.join(self.backup_path, f"ragbase_backup_{backup_id}.tar.gz")
            
            if not os.path.exists(backup_file):
                raise FileNotFoundError(f"Backup file not found: {backup_file}")
            
            # Geçici dizin oluştur
            with tempfile.TemporaryDirectory() as temp_dir:
                # Arşivi aç
                with tarfile.open(backup_file, "r:gz") as tar:
                    tar.extractall(temp_dir)
                
                # Backup dizinini bul
                backup_dir = os.path.join(temp_dir, f"backup_{backup_id}")
                
                # Metadata yükleme
                metadata_file = os.path.join(backup_dir, "metadata.json")
                if not os.path.exists(metadata_file):
                    raise FileNotFoundError(f"Backup metadata not found: {metadata_file}")
                
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                # Veritabanı geri yükleme
                db_results = None
                if restore_db:
                    db_file = os.path.join(backup_dir, metadata["database"]["file"])
                    db_results = await self._restore_database(db_file)
                
                # Dosya depolama geri yükleme
                storage_results = None
                if restore_storage and "storage" in metadata:
                    storage_dir = os.path.join(backup_dir, "storage")
                    storage_results = await self._restore_storage(storage_dir)
                
                logger.info(f"Restore completed from backup: {backup_id}")
                
                return {
                    "status": "success",
                    "backup_id": backup_id,
                    "timestamp": datetime.now().isoformat(),
                    "database": db_results,
                    "storage": storage_results
                }
                
        except Exception as e:
            logger.error(f"Restore failed: {str(e)}")
            
            return {
                "status": "error",
                "backup_id": backup_id,
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    async def _restore_database(self, db_file: str) -> Dict[str, Any]:
        """
        Veritabanını geri yükle
        
        Args:
            db_file: Veritabanı yedek dosyası
            
        Returns:
            Dict[str, Any]: Geri yükleme sonuçları
        """
        logger.info(f"Restoring database from: {db_file}")
        
        start_time = datetime.now()
        
        try:
            # pg_restore komutunu oluştur
            cmd = [
                "pg_restore",
                "--host", self.pg_host,
                "--port", str(self.pg_port),
                "--username", self.pg_user,
                "--dbname", self.pg_db,
                "--clean",  # Önceki tabloları temizler
                "--if-exists",  # Varsa siler
                "--no-owner",  # Yeni DB'de owner bilgisini değiştirmez
                "--verbose",
                db_file
            ]
            
            # Ortam değişkenlerini ayarla (şifre)
            env = os.environ.copy()
            env["PGPASSWORD"] = self.pg_password
            
            # pg_restore çalıştır
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            stdout, stderr = await process.communicate()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Çıktıları döndür
            return {
                "success": process.returncode == 0,
                "file": os.path.basename(db_file),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration": duration,
                "error": stderr.decode() if process.returncode != 0 else None
            }
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.error(f"Database restore failed: {str(e)}")
            
            return {
                "success": False,
                "file": os.path.basename(db_file),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration": duration,
                "error": str(e)
            }
    
    async def _restore_storage(self, storage_dir: str) -> Dict[str, Any]:
        """
        Dosya depolamayı geri yükle
        
        Args:
            storage_dir: Depolama yedek dizini
            
        Returns:
            Dict[str, Any]: Geri yükleme sonuçları
        """
        logger.info(f"Restoring storage files from: {storage_dir}")
        
        start_time = datetime.now()
        
        try:
            # Hedef dizin
            destination_dir = settings.STORAGE_PATH
            
            # İstatistikler
            stats = {
                "files_total": 0,
                "files_copied": 0,
                "bytes_copied": 0,
                "errors": []
            }
            
            # Dosyaları kopyala
            for root, dirs, files in os.walk(storage_dir):
                for d in dirs:
                    src_dir = os.path.join(root, d)
                    rel_dir = os.path.relpath(src_dir, storage_dir)
                    dest_dir = os.path.join(destination_dir, rel_dir)
                    os.makedirs(dest_dir, exist_ok=True)
                
                for file in files:
                    stats["files_total"] += 1
                    
                    src_file = os.path.join(root, file)
                    rel_file = os.path.relpath(src_file, storage_dir)
                    dest_file = os.path.join(destination_dir, rel_file)
                    
                    try:
                        # Hedef dizini oluştur
                        os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                        
                        # Dosyayı kopyala
                        shutil.copy2(src_file, dest_file)
                        
                        # İstatistikleri güncelle
                        stats["files_copied"] += 1
                        stats["bytes_copied"] += os.path.getsize(src_file)
                        
                    except Exception as e:
                        error_msg = f"Failed to restore file {rel_file}: {str(e)}"
                        logger.warning(error_msg)
                        stats["errors"].append({
                            "file": rel_file,
                            "error": str(e)
                        })
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"Storage restore completed: {stats['files_copied']} of {stats['files_total']} files")
            
            return {
                "success": len(stats["errors"]) == 0,
                "directory": storage_dir,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration": duration,
                "files_total": stats["files_total"],
                "files_copied": stats["files_copied"],
                "bytes_copied": stats["bytes_copied"],
                "errors": stats["errors"]
            }
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.error(f"Storage restore failed: {str(e)}")
            
            return {
                "success": False,
                "directory": storage_dir,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration": duration,
                "error": str(e)
            }