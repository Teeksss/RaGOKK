# Last reviewed: 2025-04-30 07:34:44 UTC (User: Teeksss)
import pytest
import uuid
from datetime import datetime, timezone

from backend.models.document import Document
from backend.repositories.document_repository import DocumentRepository

# Test fixture
@pytest.fixture
def test_document_data():
    return {
        "title": "Test Document",
        "file_name": "test.pdf",
        "file_type": "pdf",
        "file_path": "/tmp/test.pdf",
        "content": "This is a test document content.",
        "user_id": str(uuid.uuid4()),
        "organization_id": str(uuid.uuid4()),
        "metadata": {
            "page_count": 1,
            "author": "Test Author",
            "tags": ["test", "document"]
        }
    }

# Document repository testleri
@pytest.mark.asyncio
async def test_create_document(async_db_session, test_document_data):
    # Repository oluştur
    repo = DocumentRepository()
    
    # Test belgesini oluştur
    document = Document(**test_document_data)
    
    # Belgeyi kaydet
    saved_document = await repo.create_document(async_db_session, document)
    
    # ID oluşturulmuş olmalı
    assert saved_document.id is not None
    # Diğer alanlar doğru olmalı
    assert saved_document.title == test_document_data["title"]
    assert saved_document.file_name == test_document_data["file_name"]
    assert saved_document.content == test_document_data["content"]
    assert saved_document.user_id == test_document_data["user_id"]
    assert saved_document.metadata == test_document_data["metadata"]
    # created_at alanı ayarlanmış olmalı
    assert saved_document.created_at is not None

@pytest.mark.asyncio
async def test_get_document_by_id(async_db_session, test_document_data):
    # Repository oluştur
    repo = DocumentRepository()
    
    # Test belgesini oluştur
    document = Document(**test_document_data)
    
    # Belgeyi kaydet
    saved_document = await repo.create_document(async_db_session, document)
    
    # ID ile belgeyi getir
    retrieved_document = await repo.get_document_by_id(async_db_session, saved_document.id)
    
    # Aynı belge gelmeli
    assert retrieved_document is not None
    assert retrieved_document.id == saved_document.id
    assert retrieved_document.title == test_document_data["title"]

@pytest.mark.asyncio
async def test_update_document(async_db_session, test_document_data):
    # Repository oluştur
    repo = DocumentRepository()
    
    # Test belgesini oluştur
    document = Document(**test_document_data)
    
    # Belgeyi kaydet
    saved_document = await repo.create_document(async_db_session, document)
    
    # Belgeyi güncelle
    new_title = "Updated Test Document"
    updated_document = await repo.update_document(
        async_db_session,
        document_id=saved_document.id,
        title=new_title
    )
    
    # Güncellenen belgeyi kontrol et
    assert updated_document is not None
    assert updated_document.id == saved_document.id
    assert updated_document.title == new_title
    # Diğer alanlar değişmemiş olmalı
    assert updated_document.content == test_document_data["content"]
    # updated_at alanı güncellenmiş olmalı
    assert updated_document.updated_at is not None

@pytest.mark.asyncio
async def test_delete_document(async_db_session, test_document_data):
    # Repository oluştur
    repo = DocumentRepository()
    
    # Test belgesini oluştur
    document = Document(**test_document_data)
    
    # Belgeyi kaydet
    saved_document = await repo.create_document(async_db_session, document)
    
    # Belgeyi sil
    delete_result = await repo.delete_document(async_db_session, saved_document.id)
    
    # Silme işlemi başarılı olmalı
    assert delete_result is True
    
    # Belge artık olmamalı
    deleted_document = await repo.get_document_by_id(async_db_session, saved_document.id)
    assert deleted_document is None

@pytest.mark.asyncio
async def test_get_documents_by_user(async_db_session, test_document_data):
    # Repository oluştur
    repo = DocumentRepository()
    
    # Aynı kullanıcıya ait 3 belge oluştur
    user_id = test_document_data["user_id"]
    
    for i in range(3):
        doc_data = test_document_data.copy()
        doc_data["title"] = f"Test Document {i+1}"
        document = Document(**doc_data)
        await repo.create_document(async_db_session, document)
    
    # Kullanıcının belgelerini getir
    documents = await repo.get_documents_by_user_id(async_db_session, user_id)
    
    # 3 belge olmalı
    assert len(documents) == 3
    # Tüm belgeler aynı kullanıcıya ait olmalı
    for doc in documents:
        assert doc.user_id == user_id

@pytest.mark.asyncio
async def test_search_documents(async_db_session, test_document_data):
    # Repository oluştur
    repo = DocumentRepository()
    
    # Farklı başlıklarda 3 belge oluştur
    titles = ["Machine Learning", "Artificial Intelligence", "Data Science"]
    
    for title in titles:
        doc_data = test_document_data.copy()
        doc_data["title"] = title
        document = Document(**doc_data)
        await repo.create_document(async_db_session, document)
    
    # Başlığa göre arama yap
    search_results = await repo.search_documents(
        async_db_session,
        search_term="Machine",
        user_id=test_document_data["user_id"]
    )
    
    # 1 sonuç olmalı
    assert len(search_results) == 1
    assert search_results[0].title == "Machine Learning"
    
    # Daha genel bir arama yap
    search_results = await repo.search_documents(
        async_db_session,
        search_term="Learning|Intelligence|Science",
        user_id=test_document_data["user_id"]
    )
    
    # 3 sonuç olmalı
    assert len(search_results) == 3