# Last reviewed: 2025-04-29 10:59:14 UTC (User: Teekssseksiklikleri)
import pytest
import asyncio
import datetime
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.security_log_repository import SecurityLogRepository
from ..db.models import SecurityLogDB

@pytest.fixture
def security_log_repo():
    return SecurityLogRepository()

@pytest.mark.asyncio
async def test_create_log():
    """Güvenlik log kaydı oluşturma testi"""
    repo = SecurityLogRepository()
    
    # Mock veritabanı session'ı
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    
    # Insert sonucu
    mock_result = MagicMock()
    mock_result.inserted_primary_key = [1]  # ID = 1 dönecek
    mock_db.execute.return_value = mock_result
    
    # Log oluştur
    log_id = await repo.create_log(
        db=mock_db,
        log_type="test",
        action="create",
        user_id="test_user",
        resource_type="api_key",
        resource_id="openai",
        ip_address="127.0.0.1",
        details={"test": "value"}
    )
    
    # Beklenen sonuçlar
    assert log_id == 1
    assert mock_db.execute.called
    assert mock_db.commit.called

@pytest.mark.asyncio
async def test_get_logs():
    """Log kayıtlarını getirme testi"""
    repo = SecurityLogRepository()
    
    # Mock veritabanı session'ı
    mock_db = AsyncMock(spec=AsyncSession)
    
    # Mock veritabanı sonucu
    mock_result = MagicMock()
    
    # İki log kaydı dönecek
    mock_log1 = MagicMock(spec=SecurityLogDB)
    mock_log1.id = 1
    mock_log1.timestamp = datetime.datetime.now()
    mock_log1.log_type = "api_key"
    mock_log1.action = "create"
    mock_log1.user_id = "test_user"
    mock_log1.resource_type = "provider"
    mock_log1.resource_id = "openai"
    mock_log1.ip_address = "127.0.0.1"
    mock_log1.details = '{"test": "value"}'
    mock_log1.success = True
    mock_log1.severity = "info"
    
    mock_log2 = MagicMock(spec=SecurityLogDB)
    mock_log2.id = 2
    mock_log2.timestamp = datetime.datetime.now()
    mock_log2.log_type = "api_key"
    mock_log2.action = "access"
    mock_log2.user_id = "test_user"
    mock_log2.resource_type = "provider"
    mock_log2.resource_id = "cohere"
    mock_log2.ip_address = "127.0.0.1"
    mock_log2.details = None
    mock_log2.success = True
    mock_log2.severity = "info"
    
    # all() metodunu mock'la
    mock_all = MagicMock()
    mock_all.all.return_value = [mock_log1, mock_log2]
    
    # scalars() metodunu mock'la
    mock_scalars = MagicMock()
    mock_scalars.scalars.return_value = mock_all
    
    mock_db.execute.return_value = mock_scalars
    
    # Log'ları getir
    logs = await repo.get_logs(
        db=mock_db,
        log_type="api_key",
        limit=10,
        offset=0
    )
    
    # Beklenen sonuçlar
    assert len(logs) == 2
    assert logs[0]["id"] == 1
    assert logs[1]["id"] == 2
    assert logs[0]["log_type"] == "api_key"
    assert logs[0]["action"] == "create"
    assert logs[1]["action"] == "access"

@pytest.mark.asyncio
async def test_get_logs_count():
    """Log sayısını getirme testi"""
    repo = SecurityLogRepository()
    
    # Mock veritabanı session'ı
    mock_db = AsyncMock(spec=AsyncSession)
    
    # scalar_one() metodu mock'la 
    mock_scalar_one = MagicMock(return_value=5)  # 5 kayıt var
    
    # execute() metodunu mock'la
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 5
    mock_db.execute.return_value = mock_result
    
    # Log sayısını getir
    count = await repo.get_logs_count(
        db=mock_db,
        log_type="api_key"
    )
    
    # Beklenen sonuç
    assert count == 5
    assert mock_db.execute.called

@pytest.mark.asyncio
async def test_get_log_by_id():
    """ID'ye göre log getirme testi"""
    repo = SecurityLogRepository()
    
    # Mock veritabanı session'ı
    mock_db = AsyncMock(spec=AsyncSession)
    
    # Mock veritabanı sonucu
    mock_log = MagicMock(spec=SecurityLogDB)
    mock_log.id = 1
    mock_log.timestamp = datetime.datetime.now()
    mock_log.log_type = "api_key"
    mock_log.action = "create"
    mock_log.user_id = "test_user"
    mock_log.resource_type = "provider"
    mock_log.resource_id = "openai"
    mock_log.ip_address = "127.0.0.1"
    mock_log.details = '{"test": "value"}'
    mock_log.success = True
    mock_log.severity = "info"
    
    # first() metodunu mock'la
    mock_first = MagicMock()
    mock_first.first.return_value = mock_log
    
    # scalars() metodunu mock'la
    mock_scalars = MagicMock()
    mock_scalars.scalars.return_value = mock_first
    
    mock_db.execute.return_value = mock_scalars
    
    # Log'u ID ile getir
    log = await repo.get_log_by_id(mock_db, 1)
    
    # Beklenen sonuçlar
    assert log is not None
    assert log["id"] == 1
    assert log["log_type"] == "api_key"
    assert log["action"] == "create"
    assert log["user_id"] == "test_user"
    
    # Details JSON olarak parse edilmiş olmalı
    assert isinstance(log["details"], dict)
    assert log["details"]["test"] == "value"