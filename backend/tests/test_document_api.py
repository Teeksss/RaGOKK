# Last reviewed: 2025-04-29 13:14:42 UTC (User: TeeksssAPI)
import pytest
import json
from pathlib import Path
from typing import Dict, Any
import io

pytestmark = pytest.mark.asyncio

class TestDocumentAPI:
    """Doküman API'si için test sınıfı."""
    
    async def test_upload_document(self, authenticated_client, tmp_path):
        """Doküman yükleme testi."""
        # Test dosyası oluştur
        test_content = "This is a test document content."
        test_file = tmp_path / "test_doc.txt"
        test_file.write_text(test_content)
        
        # Form verileri hazırla
        form_data = {
            "title": "Test Document",
            "description": "This is a test document",
            "is_public": "false",
            "tags": "test,document,api",
            "auto_process": "true"
        }
        
        # Dosyayı aç
        with open(test_file, "rb") as f:
            files = {"file": ("test_doc.txt", f, "text/plain")}
            
            # İsteği gönder
            response = await authenticated_client.post(
                "/api/documents/upload",
                data=form_data,
                files=files
            )
        
        # Sonucu kontrol et
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["title"] == "Test Document"
        assert data["status"] in ["uploaded", "processing"]
    
    async def test_list_documents(self, authenticated_client):
        """Doküman listeleme testi."""
        # İsteği gönder
        response = await authenticated_client.get("/api/documents/")
        
        # Sonucu kontrol et
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    async def test_get_document(self, authenticated_client):
        """Belirli bir dokümanı getirme testi."""
        # Önce doküman oluştur
        test_content = "This is another test document content."
        files = {"file": ("another_doc.txt", io.BytesIO(test_content.encode()), "text/plain")}
        form_data = {"title": "Another Test Document"}
        
        upload_response = await authenticated_client.post(
            "/api/documents/upload",
            data=form_data,
            files=files
        )
        
        upload_data = upload_response.json()
        document_id = upload_data["id"]
        
        # Dokümanı getir
        response = await authenticated_client.get(f"/api/documents/{document_id}")
        
        # Sonucu kontrol et
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == document_id
        assert data["title"] == "Another Test Document"
    
    async def test_update_document(self, authenticated_client):
        """Doküman güncelleme testi."""
        # Önce doküman oluştur
        test_content = "Document to be updated."
        files = {"file": ("update_doc.txt", io.BytesIO(test_content.encode()), "text/plain")}
        form_data = {"title": "Document Before Update"}
        
        upload_response = await authenticated_client.post(
            "/api/documents/upload",
            data=form_data,
            files=files
        )
        
        upload_data = upload_response.json()
        document_id = upload_data["id"]
        
        # Dokümanı güncelle
        update_data = {
            "title": "Updated Document Title",
            "description": "Updated description",
            "tags": ["updated", "document"]
        }
        
        response = await authenticated_client.put(
            f"/api/documents/{document_id}",
            json=update_data
        )
        
        # Sonucu kontrol et
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == document_id
        assert data["title"] == "Updated Document Title"
        assert data["description"] == "Updated description"
    
    async def test_delete_document(self, authenticated_client):
        """Doküman silme testi."""
        # Önce doküman oluştur
        test_content = "Document to be deleted."
        files = {"file": ("delete_doc.txt", io.BytesIO(test_content.encode()), "text/plain")}
        form_data = {"title": "Document To Delete"}
        
        upload_response = await authenticated_client.post(
            "/api/documents/upload",
            data=form_data,
            files=files
        )
        
        upload_data = upload_response.json()
        document_id = upload_data["id"]
        
        # Dokümanı sil
        response = await authenticated_client.delete(f"/api/documents/{document_id}")
        
        # Sonucu kontrol et
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        
        # Dokümanın gerçekten silindiğini kontrol et
        get_response = await authenticated_client.get(f"/api/documents/{document_id}")
        assert get_response.status_code == 404