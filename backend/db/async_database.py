# Last reviewed: 2025-04-29 08:07:22 UTC (User: TeeksssNative)
import os
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import asyncio
from contextlib import asynccontextmanager

from ..utils.config import (
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD,
    DB_POOL_SIZE, DB_MAX_OVERFLOW, DB_POOL_RECYCLE, DB_ECHO
)
from ..utils.logger import get_logger

logger = get_logger(__name__)

# SQLAlchemy Base sınıfı
Base = declarative_base()

# PostgreSQL bağlantı URL'i (async sürücü)
DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Havuz ayarları
pool_size = DB_POOL_SIZE
max_overflow = DB_MAX_OVERFLOW
pool_recycle = DB_POOL_RECYCLE
echo = DB_ECHO

# Async engine havuz yapılandırması ile
engine = create_async_engine(
    DATABASE_URL,
    pool_size=pool_size, # Havuz boyutu
    max_overflow=max_overflow, # Havuz aşıldığında izin verilen maksimum ekstra bağlantı
    pool_recycle=pool_recycle, # Bağlantılar kaç saniyede bir yenilenecek
    pool_pre_ping=True, # Bağlantı kullanmadan önce ping atarak sağlamlığını kontrol et
    echo=echo # SQL sorgularının loglanması
)

# Async session factory
AsyncSessionFactory = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
    autoflush=False
)

async def init_db():
    """Veritabanı tablolarını oluşturur (Async)"""
    try:
        async with engine.begin() as conn:
            # Tabloları oluştur (eğer yoksa)
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Veritabanı tabloları başarıyla oluşturuldu")
    except Exception as e:
        logger.critical(f"Veritabanı tabloları oluşturulamadı: {e}", exc_info=True)
        raise

async def close_db():
    """Veritabanı bağlantısını kapatır"""
    try:
        await engine.dispose()
        logger.info("Veritabanı bağlantıları kapatıldı")
    except Exception as e:
        logger.error(f"Veritabanı kapatma hatası: {e}", exc_info=True)

@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency için async session context manager"""
    session = AsyncSessionFactory()
    try:
        yield session
    except Exception as e:
        logger.error(f"Session hatası: {e}", exc_info=True)
        await session.rollback()
        raise
    finally:
        await session.close()

# FastAPI dependency için kullanılacak fonksiyon
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency için async db session"""
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"DB session hatası: {e}", exc_info=True)
            await session.rollback()
            raise

# Geriye dönük uyumluluk için helper fonksiyonlar (to_thread yerine native async kullanır)
async def execute_with_session(session: AsyncSession, query_func, *args, **kwargs):
    """Bir session ile bir sorgu fonksiyonunu çalıştırır"""
    try:
        return await query_func(session, *args, **kwargs)
    except Exception as e:
        logger.error(f"Query execution error: {e}", exc_info=True)
        raise

# Singleton session pool (AppState üzerinden de yönetilebilir)
_session_pool = None

async def get_session_pool():
    """Singleton session pool döndürür"""
    global _session_pool
    if _session_pool is None:
        _session_pool = AsyncSessionFactory()
    return _session_pool