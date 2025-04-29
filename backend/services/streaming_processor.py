# Last reviewed: 2025-04-29 12:17:43 UTC (User: TeeksssVektör)
import os
import tempfile
import asyncio
import aiofiles
import aiohttp
import io
import logging
import time
from typing import Dict, List, Any, Optional, Union, AsyncGenerator, Callable, BinaryIO
from enum import Enum
import hashlib
from dataclasses import dataclass

from ..utils.logger import get_logger

logger = get_logger(__name__)

class StreamingStatus(Enum):
    """Streaming işleme durumları"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class StreamingProgress:
    """Streaming işleme ilerleme durumu"""
    job_id: str
    status: StreamingStatus
    total_size: int
    processed_size: int
    chunks_processed: int
    start_time: float
    last_update: float
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @property
    def progress_percentage(self) -> float:
        """İlerleme yüzdesi"""
        if self.total_size == 0:
            return 0
        return (self.processed_size / self.total_size) * 100
    
    @property
    def elapsed_seconds(self) -> float:
        """Geçen süre (saniye)"""
        return time.time() - self.start_time
    
    @property
    def processing_speed(self) -> float:
        """İşleme hızı (bytes/second)"""
        elapsed = self.elapsed_seconds
        if elapsed == 0:
            return 0
        return self.processed_size / elapsed

class StreamingDocumentProcessor:
    """
    Büyük dokümanlar için streaming işleme sınıfı.
    Özellikler:
    - Disk üzerinde geçici dosyalar kullanarak bellek kullanımını sınırlar
    - Dokümanları parçalar halinde işler
    - İlerleme takibi ve durum bildirimleri yapar
    - Hata yönetimi ve devam mekanizması sağlar
    - Asenkron işleme ve callback desteği sunar
    """
    
    def __init__(
        self, 
        temp_dir: Optional[str] = None,
        chunk_size: int = 1024 * 1024,  # 1 MB
        max_concurrent_chunks: int = 4,
        cleanup_temp: bool = True
    ):
        """
        Args:
            temp_dir: Geçici dosyalar için dizin
            chunk_size: İşleme parça boyutu
            max_concurrent_chunks: Maksimum eşzamanlı işlenecek parça sayısı
            cleanup_temp: İşlem sonrası geçici dosyaları temizle
        """
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.chunk_size = chunk_size
        self.max_concurrent_chunks = max_concurrent_chunks
        self.cleanup_temp = cleanup_temp
        
        # İşleme kuyrukları
        self.active_jobs = {}  # job_id -> StreamingProgress
        self.job_semaphore = asyncio.Semaphore(10)  # Maksimum eşzamanlı iş
    
    async def process_large_file(
        self,
        file_source: Union[str, bytes, BinaryIO],
        processor_func: Callable[[bytes, Dict[str, Any]], Any],
        metadata: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[StreamingProgress], None]] = None
    ) -> Dict[str, Any]:
        """
        Büyük bir dosyayı stream ederek işler
        
        Args:
            file_source: Dosya kaynağı (filepath, URL, bytes veya file-like nesne)
            processor_func: Her parça için işleme fonksiyonu
            metadata: Dosya meta verileri
            progress_callback: İlerleme için çağrılacak callback fonksiyonu
            
        Returns:
            Dict[str, Any]: İşleme sonucu
        """
        async with self.job_semaphore:
            # İş ID'si oluştur
            job_id = f"job_{int(time.time())}_{hashlib.md5(str(file_source).encode()[:100]).hexdigest()[:8]}"
            
            # Geçici dosya dizini oluştur
            job_temp_dir = os.path.join(self.temp_dir, job_id)
            os.makedirs(job_temp_dir, exist_ok=True)
            
            try:
                # Dosyayı geçici bir dosyaya stream et ve toplam boyutu hesapla
                temp_path, total_size = await self._stream_to_temp_file(file_source, job_temp_dir)
                
                # İlerleme nesnesini başlat
                progress = StreamingProgress(
                    job_id=job_id,
                    status=StreamingStatus.PROCESSING,
                    total_size=total_size,
                    processed_size=0,
                    chunks_processed=0,
                    start_time=time.time(),
                    last_update=time.time(),
                    metadata=metadata or {}
                )
                
                # Aktif işlere ekle
                self.active_jobs[job_id] = progress
                
                # İşleme sonucu parçalarını toplama
                processed_chunks = []
                
                try:
                    # Dosyayı parçalar halinde oku ve işle
                    async for chunk, chunk_metadata in self._read_chunks(temp_path, job_id):
                        # Parçanın meta verilerini dosya meta verileriyle birleştir
                        chunk_context = metadata.copy() if metadata else {}
                        chunk_context.update(chunk_metadata)
                        
                        # Parçayı işle
                        result = await processor_func(chunk, chunk_context)
                        processed_chunks.append(result)
                        
                        # İlerlemeyi güncelle
                        progress.processed_size += len(chunk)
                        progress.chunks_processed += 1
                        progress.last_update = time.time()
                        
                        # Callback'i çağır
                        if progress_callback:
                            try:
                                progress_callback(progress)
                            except Exception as e:
                                logger.warning(f"Progress callback hatası: {e}")
                    
                    # İşleme tamamlandı
                    progress.status = StreamingStatus.COMPLETED
                    
                    # Toplam sonucu birleştir ve döndür
                    combined_result = self._combine_results(processed_chunks)
                    return {
                        "job_id": job_id,
                        "status": "completed",
                        "total_size": total_size,
                        "processing_time": progress.elapsed_seconds,
                        "chunks_processed": progress.chunks_processed,
                        "result": combined_result
                    }
                    
                except Exception as e:
                    logger.error(f"Streaming işleme hatası: {e}")
                    progress.status = StreamingStatus.FAILED
                    progress.error = str(e)
                    
                    # Callback ile hatayı bildir
                    if progress_callback:
                        try:
                            progress_callback(progress)
                        except:
                            pass
                    
                    raise
            
            finally:
                # Aktif işlerden kaldır
                if job_id in self.active_jobs:
                    del self.active_jobs[job_id]
                
                # Geçici dosyaları temizle
                if self.cleanup_temp:
                    try:
                        if os.path.exists(job_temp_dir):
                            for file in os.listdir(job_temp_dir):
                                try:
                                    os.unlink(os.path.join(job_temp_dir, file))
                                except:
                                    pass
                            os.rmdir(job_temp_dir)
                    except Exception as e:
                        logger.warning(f"Geçici dosya temizleme hatası: {e}")
    
    async def _stream_to_temp_file(
        self, 
        source: Union[str, bytes, BinaryIO],
        temp_dir: str
    ) -> Tuple[str, int]:
        """
        Kaynaktan gelen veriyi geçici dosyaya yazar
        
        Args:
            source: Veri kaynağı (dosya yolu, URL, bytes veya file-like nesne)
            temp_dir: Geçici dosyaların oluşturulacağı dizin
            
        Returns:
            Tuple[str, int]: Geçici dosya yolu ve toplam boyut
        """
        temp_path = os.path.join(temp_dir, "input_data")
        total_size = 0
        
        try:
            if isinstance(source, str):
                if source.startswith(('http://', 'https://')):
                    # URL'den stream et
                    async with aiohttp.ClientSession() as session:
                        async with session.get(source) as response:
                            if response.status != 200:
                                raise ValueError(f"HTTP hatası: {response.status}")
                            
                            # Toplam boyutu al
                            content_length = response.headers.get('Content-Length')
                            if content_length:
                                total_size = int(content_length)
                            
                            # Chunk'lar halinde oku ve yaz
                            async with aiofiles.open(temp_path, 'wb') as f:
                                async for data in response.content.iter_chunked(self.chunk_size):
                                    await f.write(data)
                                    if not total_size:
                                        total_size += len(data)
                else:
                    # Yerel dosya
                    file_stat = os.stat(source)
                    total_size = file_stat.st_size
                    
                    # Hızlı bir şekilde kopyala
                    await asyncio.to_thread(
                        lambda: os.system(f'cp "{source}" "{temp_path}"')
                    )
            
            elif isinstance(source, bytes):
                # Bytes nesnesini doğrudan yaz
                async with aiofiles.open(temp_path, 'wb') as f:
                    await f.write(source)
                total_size = len(source)
            
            else:
                # File-like nesne
                source.seek(0, os.SEEK_END)
                total_size = source.tell()
                source.seek(0)
                
                async with aiofiles.open(temp_path, 'wb') as f:
                    while chunk := source.read(self.chunk_size):
                        await f.write(chunk)
            
            return temp_path, total_size
            
        except Exception as e:
            logger.error(f"Stream to temp file hatası: {e}")
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    
    async def _read_chunks(self, file_path: str, job_id: str) -> AsyncGenerator[Tuple[bytes, Dict[str, Any]], None]:
        """
        Dosyayı parçalar halinde okur
        
        Args:
            file_path: Dosya yolu
            job_id: İş ID'si
            
        Yields:
            Tuple[bytes, Dict[str, Any]]: Parça ve meta veriler
        """
        # Parçalar için senkronizasyon semaforları
        semaphore = asyncio.Semaphore(self.max_concurrent_chunks)
        
        # Parça sayıcı
        chunk_num = 0
        
        async with aiofiles.open(file_path, 'rb') as f:
            while True:
                async with semaphore:
                    chunk_data = await f.read(self.chunk_size)
                    if not chunk_data:
                        break
                    
                    # Parça meta verisi
                    chunk_metadata = {
                        "chunk_number": chunk_num,
                        "chunk_size": len(chunk_data),
                        "job_id": job_id
                    }
                    
                    # Sonraki parça için sayaç artır
                    chunk_num += 1
                    
                    yield chunk_data, chunk_metadata
    
    def _combine_results(self, chunks: List[Any]) -> Any:
        """
        İşlenmiş parçaları birleştirir
        
        Args:
            chunks: İşlenmiş parçalar
            
        Returns:
            Any: Birleştirilmiş sonuç
        """
        # Sonuçların türüne göre birleştirme stratejileri
        if not chunks:
            return None
            
        # Stringler için basit birleştirme
        if all(isinstance(chunk, str) for chunk in chunks):
            return ''.join(chunks)
            
        # Listeler için birleştirme
        if all(isinstance(chunk, list) for chunk in chunks):
            combined = []
            for chunk in chunks:
                combined.extend(chunk)
            return combined
            
        # Sözlükler için birleştirme
        if all(isinstance(chunk, dict) for chunk in chunks):
            combined = {}
            for chunk in chunks:
                combined.update(chunk)
            return combined
            
        # Diğer durumlarda liste olarak döndür
        return chunks
    
    def get_job_status(self, job_id: str) -> Optional[StreamingProgress]:
        """
        Bir işin durumunu döndürür
        
        Args:
            job_id: İş ID'si
            
        Returns:
            Optional[StreamingProgress]: İş ilerleme durumu
        """
        return self.active_jobs.get(job_id)
    
    def list_active_jobs(self) -> List[StreamingProgress]:
        """
        Aktif işleri listeler
        
        Returns:
            List[StreamingProgress]: Aktif işler
        """
        return list(self.active_jobs.values())