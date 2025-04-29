# Last reviewed: 2025-04-29 11:33:20 UTC (User: Teekssseksikleri)
import os
import hashlib
from typing import Dict, List, Optional, Any, Tuple, Set
import datetime
import asyncio
import time
import logging
import glob
import json
import watchdog.observers
import watchdog.events
import aiofiles
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..repositories.document_repository import DocumentRepository
from .document_processor import DocumentProcessor
from ..utils.logger import get_logger

logger = get_logger(__name__)

class DocumentSyncService:
    """
    Dosya sisteminden dokümanları senkronize eden servis.
    - Belirli klasörleri izler ve değişiklikleri yakalar
    - Yeni veya değişen dokümanları işler
    - Versiyonlama yapar ve doküman geçmişini korur
    """
    
    def __init__(self, sync_dirs: List[str], polling_interval: int = 60):
        self.sync_dirs = sync_dirs
        self.polling_interval = polling_interval  # saniye
        self.processor = DocumentProcessor()
        self.repository = DocumentRepository()
        self.observers = []
        self.syncing = False
        self.sync_task = None
        self._stop_event = asyncio.Event()
    
    async def start(self):
        """Senkronizasyon servisini başlatır"""
        logger.info(f"Doküman senkronizasyonu başlatılıyor: {self.sync_dirs}")
        
        # İlk senkronizasyon
        await self.sync_all()
        
        # Periyodik senkronizasyon görevi
        self.sync_task = asyncio.create_task(self._periodic_sync())
        
        # Watchdog gözlemcilerini başlat
        await self._setup_observers()
    
    async def stop(self):
        """Senkronizasyon servisini durdurur"""
        logger.info("Doküman senkronizasyonu durduruluyor")
        
        # Durdurma sinyali gönder
        self._stop_event.set()
        
        # Sync task'i bekle
        if self.sync_task:
            try:
                await asyncio.wait_for(self.sync_task, timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("Senkronizasyon görevi zamanında durdurulamadı")
        
        # Watchdog gözlemcilerini durdur
        for observer in self.observers:
            observer.stop()
        
        for observer in self.observers:
            observer.join(timeout=5.0)
        
        self.observers = []
    
    async def _setup_observers(self):
        """Watchdog gözlemcilerini ayarlar"""
        for sync_dir in self.sync_dirs:
            if not os.path.isdir(sync_dir):
                logger.warning(f"Senkronizasyon dizini mevcut değil, oluşturuluyor: {sync_dir}")
                try:
                    os.makedirs(sync_dir, exist_ok=True)
                except Exception as e:
                    logger.error(f"Senkronizasyon dizini oluşturulamadı: {sync_dir}, hata: {e}")
                    continue
            
            event_handler = DocumentEventHandler(self)
            observer = watchdog.observers.Observer()
            observer.schedule(event_handler, sync_dir, recursive=True)
            observer.start()
            self.observers.append(observer)
            logger.info(f"Watchdog gözlemcisi başlatıldı: {sync_dir}")
    
    async def _periodic_sync(self):
        """Periyodik olarak tüm dosyaları senkronize eder"""
        try:
            while not self._stop_event.is_set():
                # Polling interval kadar bekle
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=self.polling_interval)
                except asyncio.TimeoutError:
                    pass
                
                # Durdurma sinyali gelmişse çık
                if self._stop_event.is_set():
                    break
                
                # Tüm dosyaları senkronize et
                await self.sync_all()
                
        except asyncio.CancelledError:
            logger.info("Periyodik senkronizasyon görevi iptal edildi")
        except Exception as e:
            logger.error(f"Periyodik senkronizasyon hatası: {e}")
    
    async def sync_all(self):
        """Tüm dizinlerdeki dosyaları senkronize eder"""
        if self.syncing:
            logger.warning("Senkronizasyon zaten devam ediyor, atlıyorum")
            return
        
        try:
            self.syncing = True
            logger.info("Tam senkronizasyon başlatılıyor")
            
            # Tüm dizinlerdeki dosyaları tara
            file_paths = []
            for sync_dir in self.sync_dirs:
                if not os.path.isdir(sync_dir):
                    logger.warning(f"Senkronizasyon dizini bulunamadı, atlıyorum: {sync_dir}")
                    continue
                
                # Desteklenen tüm dosya türleri için glob desenleri
                patterns = [
                    "**/*.pdf", "**/*.docx", "**/*.txt", "**/*.html",
                    "**/*.xml", "**/*.json", "**/*.csv"
                ]
                
                for pattern in patterns:
                    glob_pattern = os.path.join(sync_dir, pattern)
                    # Recursive glob ile dosyaları listele
                    matched_files = glob.glob(glob_pattern, recursive=True)
                    file_paths.extend(matched_files)
            
            # Veritabanı izlerini getir
            db = await get_db().asend(None)
            try:
                # Document sync tablosundan tüm kayıtları getir
                from ..db.models import DocumentSync
                from sqlalchemy import select
                result = await db.execute(select(DocumentSync))
                syncs = {sync.source_path: sync for sync in result.scalars().all()}
                
                # Senkronize edilmiş dosya yolları
                synced_paths = set(syncs.keys())
                
                # Mevcut dosya yolları
                current_paths = set(file_paths)
                
                # Yeni veya değiştirilmiş dosyaları senkronize et
                for file_path in current_paths:
                    await self.sync_file(db, file_path, syncs.get(file_path))
                
                # Silinmiş dosyaları işaretle
                for deleted_path in synced_paths - current_paths:
                    sync_record = syncs.get(deleted_path)
                    if sync_record and sync_record.document_id:
                        logger.info(f"Silinen dosya tespit edildi: {deleted_path}")
                        # Opsiyonel: Doküman meta verilerine silme işareti ekle veya arşivle
                        document = await self.repository.get_document_by_id(db, sync_record.document_id)
                        if document:
                            metadata = json.loads(document.metadata) if document.metadata else {}
                            metadata["deleted"] = True
                            metadata["deletion_date"] = datetime.datetime.utcnow().isoformat()
                            
                            await self.repository.update_document(
                                db=db,
                                document_id=document.id,
                                update_data={
                                    "metadata": metadata,
                                    "is_public": False  # Silinen dokümanları gizle
                                },
                                user_id="system",
                                create_version=True,
                                version_label=f"deleted_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                            )
                            
                        # Sync kaydını sil
                        from sqlalchemy import delete
                        await db.execute(
                            delete(DocumentSync).where(DocumentSync.source_path == deleted_path)
                        )
                
                await db.commit()
                logger.info(f"Tam senkronizasyon tamamlandı, {len(current_paths)} dosya işlendi")
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Senkronizasyon sırasında hata: {e}")
                raise
            finally:
                await db.close()
                
        except Exception as e:
            logger.error(f"Senkronizasyon hatası: {e}")
        finally:
            self.syncing = False
    
    async def sync_file(self, db: AsyncSession, file_path: str, sync_record: Optional[Any] = None) -> bool:
        """
        Belirli bir dosyayı senkronize eder
        
        Args:
            db: Veritabanı oturumu
            file_path: Dosya yolu
            sync_record: Mevcut senkronizasyon kaydı (varsa)
            
        Returns:
            bool: Başarılı ise True, değilse False
        """
        try:
            # Dosya bilgilerini al
            stats = os.stat(file_path)
            modified_time = datetime.datetime.fromtimestamp(stats.st_mtime)
            
            # Dosya türünü belirle
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext.startswith('.'):
                file_ext = file_ext[1:]  # Noktayı kaldır
                
            # Desteklenen format mı?
            supported_formats = {
                'pdf': 'pdf', 
                'docx': 'docx', 
                'txt': 'txt', 
                'html': 'html',
                'htm': 'html', 
                'xml': 'xml', 
                'json': 'json',
                'csv': 'csv'
            }
            
            if file_ext not in supported_formats:
                logger.debug(f"Desteklenmeyen dosya türü: {file_ext}, atlanıyor: {file_path}")
                return False
                
            file_format = supported_formats[file_ext]
            
            # Hash oluştur
            file_hash = await self._calc_file_hash(file_path)
            
            # Değişiklik kontrolü yap
            if sync_record and sync_record.hash_value == file_hash:
                # Dosya değişmemiş, atla
                logger.debug(f"Dosya değişmemiş, atlanıyor: {file_path}")
                return True
            
            # Dosya içeriğini oku
            async with aiofiles.open(file_path, 'rb') as f:
                file_content = await f.read()
            
            # Dosya adını al
            file_name = os.path.basename(file_path)
            
            # Temel meta verileri hazırla
            metadata = {
                "file_path": file_path,
                "file_name": file_name,
                "file_size": stats.st_size,
                "file_format": file_format,
                "modified_time": modified_time.isoformat(),
                "sync_time": datetime.datetime.utcnow().isoformat(),
                "hash_value": file_hash
            }
            
            # Dokümanı işle
            processed_doc = await self.processor.process_document(
                file_content=file_content,
                file_format=file_format,
                file_name=file_name,
                metadata=metadata
            )
            
            # Dokümanı veritabanında oluştur veya güncelle
            if sync_record and sync_record.document_id:
                # Mevcut dokümanı güncelle
                document = await self.repository.get_document_by_id(db, sync_record.document_id)
                if document:
                    await self.repository.update_document(
                        db=db,
                        document_id=document.id,
                        update_data={
                            "content": processed_doc["content"],
                            "metadata": processed_doc["metadata"],
                            "updated_at": datetime.datetime.utcnow()
                        },
                        user_id="system",
                        create_version=True
                    )
                    
                    # Senkronizasyon kaydını güncelle
                    from ..db.models import DocumentSync
                    from sqlalchemy import update
                    await db.execute(
                        update(DocumentSync).where(DocumentSync.id == sync_record.id).values(
                            last_sync_time=datetime.datetime.utcnow(),
                            last_modified_time=modified_time,
                            hash_value=file_hash,
                            sync_status="success",
                            error_message=None,
                            updated_at=datetime.datetime.utcnow()
                        )
                    )
                    
                    logger.info(f"Doküman güncellendi: {file_path}")
                else:
                    # Doküman kaydı silinmiş, yeniden oluştur
                    await self._create_new_document(db, file_path, processed_doc, file_hash, modified_time)
            else:
                # Yeni doküman oluştur
                await self._create_new_document(db, file_path, processed_doc, file_hash, modified_time)
            
            return True
            
        except Exception as e:
            logger.error(f"Dosya senkronizasyon hatası ({file_path}): {e}")
            
            # Hata kaydı oluştur
            try:
                from ..db.models import DocumentSync
                
                # Mevcut senkronizasyon kaydı varsa güncelle
                if sync_record:
                    from sqlalchemy import update
                    await db.execute(
                        update(DocumentSync).where(DocumentSync.id == sync_record.id).values(
                            last_sync_time=datetime.datetime.utcnow(),
                            sync_status="failed",
                            error_message=str(e),
                            updated_at=datetime.datetime.utcnow()
                        )
                    )
                # Yoksa yeni kayıt oluştur
                else:
                    from sqlalchemy import insert
                    await db.execute(
                        insert(DocumentSync).values(
                            source_path=file_path,
                            last_sync_time=datetime.datetime.utcnow(),
                            sync_status="failed",
                            error_message=str(e),
                            created_at=datetime.datetime.utcnow(),
                            updated_at=datetime.datetime.utcnow()
                        )
                    )
                
                await db.commit()
            except Exception as db_error:
                await db.rollback()
                logger.error(f"Hata kaydı oluşturma hatası: {db_error}")
            
            return False
    
    async def _create_new_document(
        self, 
        db: AsyncSession, 
        file_path: str, 
        processed_doc: Dict[str, Any], 
        file_hash: str, 
        modified_time: datetime.datetime
    ):
        """Yeni doküman ve senkronizasyon kaydı oluşturur"""
        # Yeni doküman oluştur
        document = await self.repository.create_document(
            db=db,
            title=processed_doc["metadata"].get("file_name", Path(file_path).stem),
            content=processed_doc["content"],
            metadata=processed_doc["metadata"],
            owner_id="system",
            source_url=f"file://{file_path}",
            source_type=processed_doc["metadata"].get("file_format", "unknown"),
            is_processed=False
        )
        
        # Senkronizasyon kaydı oluştur
        from ..db.models import DocumentSync
        from sqlalchemy import insert
        await db.execute(
            insert(DocumentSync).values(
                source_path=file_path,
                document_id=document.id,
                last_sync_time=datetime.datetime.utcnow(),
                last_modified_time=modified_time,
                hash_value=file_hash,
                sync_status="success",
                created_at=datetime.datetime.utcnow(),
                updated_at=datetime.datetime.utcnow()
            )
        )
        
        logger.info(f"Yeni doküman oluşturuldu: {file_path}")
    
    async def _calc_file_hash(self, file_path: str) -> str:
        """Dosya içeriğinin hash değerini hesaplar"""
        hash_md5 = hashlib.md5()
        async with aiofiles.open(file_path, "rb") as f:
            # İçeriği bloklar halinde oku
            chunk = await f.read(65536)
            while chunk:
                hash_md5.update(chunk)
                chunk = await f.read(65536)
        return hash_md5.hexdigest()


class DocumentEventHandler(watchdog.events.FileSystemEventHandler):
    """Watchdog olay işleyici"""
    
    def __init__(self, sync_service: DocumentSyncService):
        self.sync_service = sync_service
        self.processing_files = set()
    
    def on_created(self, event):
        if event.is_directory:
            return
        
        # Dosya oluşturma olayını işle
        file_path = event.src_path
        logger.debug(f"Yeni dosya oluşturuldu: {file_path}")
        asyncio.create_task(self._process_file_change(file_path))
    
    def on_modified(self, event):
        if event.is_directory:
            return
        
        # Dosya değişiklik olayını işle
        file_path = event.src_path
        logger.debug(f"Dosya değiştirildi: {file_path}")
        asyncio.create_task(self._process_file_change(file_path))
    
    def on_moved(self, event):
        if event.is_directory:
            return
        
        # Dosya taşıma olayını işle
        dest_path = event.dest_path
        logger.debug(f"Dosya taşındı: {event.src_path} -> {dest_path}")
        asyncio.create_task(self._process_file_change(dest_path))
    
    async def _process_file_change(self, file_path: str):
        """Dosya değişikliğini işler"""
        # Dosya zaten işleniyorsa atla
        if file_path in self.processing_files:
            return
        
        try:
            self.processing_files.add(file_path)
            
            # Biraz bekle (dosya yazma işlemi tamamlanana kadar)
            await asyncio.sleep(2)
            
            # Dosya hala mevcut mu?
            if not os.path.exists(file_path):
                logger.debug(f"Dosya artık mevcut değil, işlem atlanıyor: {file_path}")
                return
            
            # DB bağlantısı al
            db = await get_db().asend(None)
            try:
                # Dosyayı senkronize et
                from ..db.models import DocumentSync
                from sqlalchemy import select
                
                # Mevcut sync kaydını kontrol et
                result = await db.execute(
                    select(DocumentSync).where(DocumentSync.source_path == file_path)
                )
                sync_record = result.scalar_one_or_none()
                
                # Dosyayı senkronize et
                await self.sync_service.sync_file(db, file_path, sync_record)
                await db.commit()
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Dosya işleme hatası: {e}")
            finally:
                await db.close()
                
        except Exception as e:
            logger.error(f"Dosya değişikliği işleme hatası: {e}")
        finally:
            self.processing_files.remove(file_path)