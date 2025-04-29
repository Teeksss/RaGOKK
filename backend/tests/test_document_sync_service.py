# Last reviewed: 2025-04-29 11:44:12 UTC (User: Teekssseskikleri tamamla)
import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
import datetime

from ..services.document_sync_service import DocumentSyncService, DocumentEventHandler

@pytest.fixture
def temp_dir():
    # Geçici dizin oluştur
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def document_sync_service(temp_dir):
    # Test için senkronizasyon servisi
    service = DocumentSyncService([temp_dir], polling_interval=1)
    # Repository'yi mock'la
    service.repository = MagicMock()
    # Processor'ü mock'la
    service.processor = MagicMock()
    return service

@pytest.mark.asyncio
async def test_sync_file_new_document(document_sync_service, temp_dir):
    # Test dosyası oluştur
    test_file_path = os.path.join(temp_dir, "test.txt")
    with open(test_file_path, 'w') as f:
        f.write("Test file content")
    
    # Mock DB session
    mock_db = AsyncMock()
    
    # Processor mock'unu yapılandır
    document_sync_service.processor.process_document.return_value = {
        "content": "Test file content",
        "metadata": {
            "file_name": "test.txt",
            "language": "en"
        }
    }
    
    # Repository mock'unu yapılandır - yeni döküman yaratılması
    mock_document = MagicMock()
    mock_document.id = 123
    document_sync_service.repository.create_document.return_value = mock_document
    
    # sync_file metodunu çağır
    result = await document_sync_service.sync_file(mock_db, test_file_path)
    
    # Sonucu kontrol et
    assert result == True
    
    # Processor çağrıldı mı?
    document_sync_service.processor.process_document.assert_called_once()
    
    # Döküman oluşturuldu mu?
    document_sync_service.repository.create_document.assert_called_once()
    
    # DB commit çağrıldı mı?
    mock_db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_sync_file_existing_document(document_sync_service, temp_dir):
    # Test dosyası oluştur
    test_file_path = os.path.join(temp_dir, "existing.txt")
    with open(test_file_path, 'w') as f:
        f.write("Updated content")
    
    # Mock DB session
    mock_db = AsyncMock()
    
    # Processor mock'unu yapılandır
    document_sync_service.processor.process_document.return_value = {
        "content": "Updated content",
        "metadata": {
            "file_name": "existing.txt",
            "language": "en"
        }
    }
    
    # Mevcut senkronizasyon kaydı
    mock_sync_record = MagicMock()
    mock_sync_record.id = 456
    mock_sync_record.document_id = 789
    
    # Mevcut dökümanı yapılandır
    mock_document = MagicMock()
    mock_document.id = 789
    mock_document.content = "Old content"
    mock_document.metadata = '{}'
    
    # Repository mock'unu yapılandır - mevcut döküman güncelleme
    document_sync_service.repository.get_document_by_id.return_value = mock_document
    
    # sync_file metodunu çağır
    result = await document_sync_service.sync_file(mock_db, test_file_path, mock_sync_record)
    
    # Sonucu kontrol et
    assert result == True
    
    # Processor çağrıldı mı?
    document_sync_service.processor.process_document.assert_called_once()
    
    # Döküman güncellendi mi?
    document_sync_service.repository.update_document.assert_called_once()
    
    # DB commit çağrıldı mı?
    mock_db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_calc_file_hash(document_sync_service, temp_dir):
    # Test dosyası oluştur
    test_file_path = os.path.join(temp_dir, "hash_test.txt")
    test_content = "Test content for hashing"
    
    with open(test_file_path, 'w') as f:
        f.write(test_content)
    
    # Hash hesapla
    file_hash = await document_sync_service._calc_file_hash(test_file_path)
    
    # Hash doğru bir değer mi?
    assert isinstance(file_hash, str)
    assert len(file_hash) == 32  # MD5 hash 32 karakter
    
    # Aynı içerik için her zaman aynı hash değeri olmalı
    another_file_path = os.path.join(temp_dir, "hash_test2.txt")
    with open(another_file_path, 'w') as f:
        f.write(test_content)
        
    another_hash = await document_sync_service._calc_file_hash(another_file_path)
    assert file_hash == another_hash
    
    # Farklı içerik için farklı hash değeri olmalı
    different_file_path = os.path.join(temp_dir, "different.txt")
    with open(different_file_path, 'w') as f:
        f.write("Different content")
        
    different_hash = await document_sync_service._calc_file_hash(different_file_path)
    assert file_hash != different_hash

@pytest.mark.asyncio
async def test_event_handler(document_sync_service, temp_dir):
    # Event handler oluştur
    event_handler = DocumentEventHandler(document_sync_service)
    
    # get_db mock'u oluştur
    mock_db = AsyncMock()
    mock_get_db = AsyncMock()
    mock_get_db.asend.return_value = mock_db
    
    # Watchdog event mock'ları
    mock_created_event = MagicMock()
    mock_created_event.is_directory = False
    mock_created_event.src_path = os.path.join(temp_dir, "new_file.txt")
    
    mock_modified_event = MagicMock()
    mock_modified_event.is_directory = False
    mock_modified_event.src_path = os.path.join(temp_dir, "modified_file.txt")
    
    # Test için dosyalar oluştur
    with open(mock_created_event.src_path, 'w') as f:
        f.write("New file")
        
    with open(mock_modified_event.src_path, 'w') as f:
        f.write("Modified file")
    
    # Event handler metodları için patch'ler
    with patch('backend.services.document_sync_service.get_db', return_value=mock_get_db):
        # sync_file çağrısını mock'la
        document_sync_service.sync_file = AsyncMock(return_value=True)
        
        # Event handler metodlarını çağır
        event_handler.on_created(mock_created_event)
        event_handler.on_modified(mock_modified_event)
        
        # Asenkron işlemlerin tamamlanmasını bekle
        await asyncio.sleep(0.1)
        
        # Event handler işlemi doğru çalıştı mı?
        assert mock_created_event.src_path in event_handler.processing_files
        assert mock_modified_event.src_path in event_handler.processing_files
        
        # Asenkron işlemlerin tamamlanmasını bekle
        await asyncio.sleep(3)  # _process_file_change içinde 2 saniye bekleme var
        
        # İşleme tamamlandı mı?
        assert mock_created_event.src_path not in event_handler.processing_files
        assert mock_modified_event.src_path not in event_handler.processing_files
        
        # Document sync servisi çağrıldı mı?
        assert document_sync_service.sync_file.call_count >= 2