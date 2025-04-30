# Last reviewed: 2025-04-30 07:34:44 UTC (User: Teeksss)
import pytest
import os
import sys
import asyncio
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import Dict, Any, Generator, AsyncGenerator

# Proje dizinini Python modül yoluna ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test veritabanı için URL
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:"
)

# SQLite için Foreign Key desteğini aktive et
@pytest.fixture(scope="session")
def event_loop():
    """Tüm testler için tek bir event loop oluştur"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def async_db_engine():
    """Test veritabanı motoru oluştur"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=True
    )
    
    # Test schema oluştur
    from backend.db.base import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Temizleme
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest_asyncio.fixture
async def async_db_session(async_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Test oturumu oluştur"""
    connection = await async_db_engine.connect()
    transaction = await connection.begin()
    
    async_session = sessionmaker(
        connection, expire_on_commit=False, class_=AsyncSession
    )
    
    async with async_session() as session:
        yield session
    
    await transaction.rollback()
    await connection.close()

@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Test konfigürasyon verilerini döndür"""
    return {
        "test_user_email": "test@example.com",
        "test_user_password": "TestPassword123!",
        "test_admin_email": "admin@example.com",
        "test_admin_password": "AdminPassword123!",
    }