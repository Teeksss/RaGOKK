# Last reviewed: 2025-04-29 13:14:42 UTC (User: TeeksssAPI)
import pytest
import asyncio
from typing import Dict, Any, Generator
import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from httpx import AsyncClient

from ..db.base import Base
from ..db.session import get_db
from ..main import app
from ..config import settings
from ..auth import jwt

# Test veritabanı URL'si
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/test_db"
)

# Test JWT secret
TEST_JWT_SECRET = "test_secret_key_for_testing_purposes_only"

# Log seviyesini ayarla
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test veritabanı motoru
engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
)

# JWT ayarlarını test için geçersiz kıl
jwt.SECRET_KEY = TEST_JWT_SECRET
jwt.ALGORITHM = "HS256"
jwt.ACCESS_TOKEN_EXPIRE_MINUTES = 30

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def setup_database():
    """Test veritabanını oluştur ve testlerden sonra temizle."""
    # Tabloları oluştur
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Veritabanını temizle
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session(setup_database) -> AsyncSession:
    """FastAPI test istekleri için veritabanı oturumu."""
    async with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()

@pytest.fixture
async def client(db_session) -> Generator:
    """FastAPI test istekleri için async test client."""
    
    async def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()

@pytest.fixture
async def authenticated_client(client, test_user) -> AsyncClient:
    """Kimlik doğrulaması yapılmış test client."""
    user_dict, token = test_user
    headers = {"Authorization": f"Bearer {token}"}
    client.headers.update(headers)
    return client

@pytest.fixture
async def test_user(db_session) -> tuple[Dict[str, Any], str]:
    """Test kullanıcısı oluştur ve JWT token döndür."""
    # Test kullanıcı bilgileri
    user_dict = {
        "id": "test_user_id",
        "email": "test@example.com",
        "username": "testuser",
        "full_name": "Test User",
        "is_active": True,
        "is_superuser": False
    }
    
    # Kullanıcıyı veritabanına ekle
    from ..repositories.user_repository import UserRepository
    user_repo = UserRepository()
    
    # Şifreli parola
    from ..auth.password import get_password_hash
    hashed_password = get_password_hash("testpassword")
    
    # Kullanıcıyı oluştur
    try:
        await user_repo.create_user(
            db=db_session,
            email=user_dict["email"],
            username=user_dict["username"],
            password=hashed_password,
            full_name=user_dict["full_name"]
        )
        await db_session.commit()
    except Exception as e:
        await db_session.rollback()
        logger.error(f"Test kullanıcısı oluştururken hata: {e}")
        raise
    
    # JWT token oluştur
    from ..auth.jwt import create_access_token
    token = create_access_token(data={"sub": user_dict["email"]})
    
    return user_dict, token