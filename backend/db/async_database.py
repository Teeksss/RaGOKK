# Last reviewed: 2025-04-29 11:44:12 UTC (User: Teekssseskikleri tamamla)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.pool import QueuePool
import os
from typing import AsyncGenerator

# Veritabanı URL'si
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./app.db")

# Pool ayarları
pool_size = int(os.getenv("DB_POOL_SIZE", "5"))
max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "10"))
pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "1800"))  # 30 dakika

# SQLite için özel ayarlar
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    # SQLite için pooling gereksiz, devre dışı bırakılır
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        connect_args=connect_args,
        future=True
    )
else:
    # PostgreSQL, MySQL vb. için pooling yapılandırması
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
        pool_pre_ping=True  # Bağlantı sağlamlık kontrolü
    )

# Asenkron session factory
async_session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Veritabanı oturumu oluşturan ve yöneten dependency.
    FastAPI'nin Depends() ile kullanılır.
    
    Yields:
        AsyncSession: Asenkron veritabanı oturumu
    """
    session = async_session_factory()
    try:
        yield session
    finally:
        await session.close()