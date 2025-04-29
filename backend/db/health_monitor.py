# Last reviewed: 2025-04-29 12:28:23 UTC (User: TeeksssCSRF)
import asyncio
import time
import logging
import traceback
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime, timedelta
from enum import Enum
import json

# SQLAlchemy için
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

# PostgreSQL için
import asyncpg

# SQLite için
import aiosqlite

# Redis için
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)

class DatabaseType(Enum):
    """Desteklenen veritabanı türleri"""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    REDIS = "redis"
    UNKNOWN = "unknown"

class DBStatus(Enum):
    """Veritabanı durumları"""
    HEALTHY = "healthy"  # Sağlıklı
    DEGRADED = "degraded"  # Performans sorunu
    UNHEALTHY = "unhealthy"  # Bağlantı sorunu
    RECOVERING = "recovering"  # İyileşme sürecinde
    UNKNOWN = "unknown"  # Durum bilinmiyor

class DBHealthEvent(Enum):
    """Veritabanı sağlık olayları"""
    CONNECTED = "connected"  # Bağlantı başarılı
    DISCONNECTED = "disconnected"  # Bağlantı koptu
    SLOW_QUERY = "slow_query"  # Yavaş sorgu
    ERROR = "error"  # Hata
    RECOVERED = "recovered"  # İyileşme
    FAILOVER = "failover"  # Fail-over gerçekleşti
    POOL_EXHAUSTED = "pool_exhausted"  # Bağlantı havuzu tükendi

class DBConnection:
    """Veritabanı bağlantı bilgileri ve durumu"""
    
    def __init__(
        self,
        name: str,
        url: str,
        db_type: DatabaseType,
        options: Dict[str, Any] = None
    ):
        self.name = name
        self.url = url
        self.type = db_type
        self.options = options or {}
        
        # SQLAlchemy engine
        self.engine = None
        
        # PostgreSQL/MySQL bağlantı havuzu
        self.pool = None
        
        # Redis bağlantısı
        self.redis = None
        
        # Sağlık durumu
        self.status = DBStatus.UNKNOWN
        self.last_checked = None
        self.last_successful_connection = None
        self.last_error = None
        self.consecutive_failures = 0
        self.recovery_attempts = 0
        
        # İstatistikler
        self.stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "total_connections": 0,
            "total_disconnects": 0,
            "slow_queries": 0,
            "avg_query_time": 0.0,
            "last_10_query_times": []
        }
    
    def update_status(self, new_status: DBStatus, error: Optional[Exception] = None) -> None:
        """
        Bağlantı durumunu günceller
        
        Args:
            new_status: Yeni durum
            error: Hata varsa
        """
        old_status = self.status
        self.status = new_status
        self.last_checked = datetime.now()
        
        if new_status == DBStatus.HEALTHY:
            self.last_successful_connection = datetime.now()
            self.consecutive_failures = 0
            if old_status in [DBStatus.UNHEALTHY, DBStatus.RECOVERING]:
                self.recovery_attempts = 0
                logger.info(f"Database '{self.name}' recovered")
        
        elif new_status == DBStatus.UNHEALTHY:
            self.consecutive_failures += 1
            self.last_error = str(error) if error else "Unknown error"
            logger.error(f"Database '{self.name}' is unhealthy: {self.last_error}")
    
    def track_query_time(self, query_time: float, success: bool) -> None:
        """
        Sorgu süresini takip eder
        
        Args:
            query_time: Sorgu süresi (saniye)
            success: Başarılı mı
        """
        self.stats["total_queries"] += 1
        
        if success:
            self.stats["successful_queries"] += 1
        else:
            self.stats["failed_queries"] += 1
        
        # Son 10 sorgu süresini takip et
        times = self.stats["last_10_query_times"]
        times.append(query_time)
        if len(times) > 10:
            times.pop(0)
        
        # Ortalama sorgu süresini güncelle
        if times:
            self.stats["avg_query_time"] = sum(times) / len(times)
        
        # Yavaş sorgu kontrolü (250ms üzeri)
        if query_time > 0.25:
            self.stats["slow_queries"] += 1

class DatabaseHealthMonitor:
    """
    Veritabanı sağlık izleme ve otomatik geri yükleme servisi.
    
    Özellikler:
    - Birden fazla veritabanı bağlantısını izler
    - Düzenli aralıklarla sağlık kontrolü yapar
    - Bağlantı sorunlarında otomatik geri yükleme dener
    - Sağlık olaylarını izler ve raporlar
    - İstatistikler ve metrikler toplar
    """
    
    def __init__(
        self,
        check_interval: int = 30,  # saniye
        recovery_threshold: int = 3,  # peş peşe hata sayısı
        recovery_max_attempts: int = 5,
        recovery_backoff_factor: float = 1.5
    ):
        """
        Args:
            check_interval: Sağlık kontrolü aralığı (saniye)
            recovery_threshold: Geri yükleme için peş peşe hata eşiği
            recovery_max_attempts: Maksimum geri yükleme deneme sayısı
            recovery_backoff_factor: Geri yükleme denemelerinin aralık çarpanı
        """
        self.check_interval = check_interval
        self.recovery_threshold = recovery_threshold
        self.recovery_max_attempts = recovery_max_attempts
        self.recovery_backoff_factor = recovery_backoff_factor
        
        # Bağlantı takibi
        self.connections: Dict[str, DBConnection] = {}
        
        # Çalışma durumu
        self.running = False
        self.monitor_task = None
        
        # Olay izleyicileri
        self.event_listeners: List[Callable[[str, DBHealthEvent, Dict[str, Any]], None]] = []
    
    async def start(self) -> None:
        """Sağlık izleme servisini başlatır"""
        if self.running:
            return
            
        self.running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Database health monitor started")
    
    async def stop(self) -> None:
        """Sağlık izleme servisini durdurur"""
        if not self.running:
            return
            
        self.running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Database health monitor stopped")
    
    async def _monitor_loop(self) -> None:
        """Ana izleme döngüsü"""
        try:
            while self.running:
                try:
                    # Tüm bağlantıları kontrol et
                    for name, connection in self.connections.items():
                        await self._check_health(connection)
                        
                        # Geri yükleme gerekiyorsa dene
                        if (
                            connection.status == DBStatus.UNHEALTHY and
                            connection.consecutive_failures >= self.recovery_threshold and
                            connection.recovery_attempts < self.recovery_max_attempts
                        ):
                            await self._attempt_recovery(connection)
                        
                except Exception as e:
                    logger.error(f"Error in monitor loop: {e}")
                
                # Sonraki kontrole kadar bekle
                await asyncio.sleep(self.check_interval)
                
        except asyncio.CancelledError:
            logger.info("Monitor loop cancelled")
    
    async def _check_health(self, connection: DBConnection) -> None:
        """
        Veritabanı sağlık kontrolü yapar
        
        Args:
            connection: Kontrol edilecek bağlantı
        """
        try:
            start_time = time.time()
            
            if connection.type == DatabaseType.POSTGRESQL or connection.type == DatabaseType.MYSQL:
                if connection.pool:
                    # PostgreSQL/MySQL pool kullanarak kontrol
                    async with connection.pool.acquire() as conn:
                        await conn.execute("SELECT 1")
                elif connection.engine:
                    # SQLAlchemy kullanarak kontrol
                    async with connection.engine.connect() as conn:
                        await conn.execute(text("SELECT 1"))
                else:
                    # Doğrudan PostgreSQL bağlantısı oluştur ve kontrol et
                    if connection.type == DatabaseType.POSTGRESQL:
                        async with asyncpg.connect(connection.url) as conn:
                            await conn.execute("SELECT 1")
            
            elif connection.type == DatabaseType.SQLITE:
                # SQLite kontrol
                if connection.engine:
                    async with connection.engine.connect() as conn:
                        await conn.execute(text("SELECT 1"))
                else:
                    # Doğrudan SQLite bağlantısı oluştur ve kontrol et
                    db_path = connection.url.replace("sqlite://", "")
                    if db_path.startswith("/"):
                        db_path = db_path[1:]
                    async with aiosqlite.connect(db_path) as conn:
                        await conn.execute("SELECT 1")
            
            elif connection.type == DatabaseType.REDIS:
                # Redis kontrol
                if connection.redis:
                    await connection.redis.ping()
                elif REDIS_AVAILABLE:
                    r = redis.from_url(connection.url)
                    await r.ping()
                    await r.close()
                else:
                    raise RuntimeError("Redis client not available")
            
            # Sorgu süresini hesapla
            query_time = time.time() - start_time
            connection.track_query_time(query_time, True)
            
            # Durum güncelle
            old_status = connection.status
            connection.update_status(
                DBStatus.DEGRADED if query_time > 0.5 else DBStatus.HEALTHY
            )
            
            # İyileşme olayı tetikle
            if old_status in [DBStatus.UNHEALTHY, DBStatus.RECOVERING] and connection.status == DBStatus.HEALTHY:
                await self._trigger_event(
                    connection.name, 
                    DBHealthEvent.RECOVERED, 
                    {"previous_status": old_status.value}
                )
            
        except Exception as e:
            # Sorgu başarısız
            query_time = time.time() - start_time
            connection.track_query_time(query_time, False)
            
            # Durum güncelle
            old_status = connection.status
            connection.update_status(DBStatus.UNHEALTHY, e)
            
            # Bağlantı kopma olayı tetikle
            if old_status in [DBStatus.HEALTHY, DBStatus.DEGRADED]:
                await self._trigger_event(
                    connection.name, 
                    DBHealthEvent.DISCONNECTED, 
                    {
                        "error": str(e),
                        "traceback": traceback.format_exc()
                    }
                )
    
    async def _attempt_recovery(self, connection: DBConnection) -> None:
        """
        Bağlantıyı geri yüklemeye çalışır
        
        Args:
            connection: Geri yüklenecek bağlantı
        """
        connection.recovery_attempts += 1
        
        # Geri yükleme durumuna geç
        connection.status = DBStatus.RECOVERING
        
        # Olay tetikle
        await self._trigger_event(
            connection.name, 
            DBHealthEvent.FAILOVER, 
            {
                "attempt": connection.recovery_attempts,
                "max_attempts": self.recovery_max_attempts
            }