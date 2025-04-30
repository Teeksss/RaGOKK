# Last reviewed: 2025-04-30 07:30:01 UTC (User: Teeksss)
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timezone
import json
import difflib

from sqlalchemy.ext.asyncio import AsyncSession
from ..models.document_version import DocumentVersion
from ..repositories.document_repository import DocumentRepository
from ..repositories.document_version_repository import DocumentVersionRepository

logger = logging.getLogger(__name__)

class DocumentVersioningService:
    """
    Belge versiyonlama servisi.
    
    Belgelerin değişiklik tarihçesini tutar ve yönetir.
    """
    
    def __init__(self):
        """Servis başlangıç ayarları"""
        self.document_repository = DocumentRepository()
        self.version_repository = DocumentVersionRepository()
    
    async def create_version(self,
                         db: AsyncSession,
                         document_id: str,
                         user_id: str,
                         change_description: str = "Document updated") -> Dict[str, Any]:
        """
        Belgenin mevcut halinden yeni bir versiyon oluşturur
        
        Args:
            db: Veritabanı oturumu
            document_id: Belge ID'si
            user_id: Değişikliği yapan kullanıcının ID'si
            change_description: Değişiklik açıklaması
            
        Returns:
            Dict[str, Any]: Oluşturulan versiyon bilgisi
        """
        try:
            # Belgeyi getir
            document = await self.document_repository.get_document_by_id(db, document_id)
            if not document:
                return {"success": False, "error": "Document not found"}
            
            # Son versiyonu getir
            versions = await self.version_repository.get_document_versions(db, document_id)
            last_version_number = 0
            if versions:
                last_version_number = max(v.version_number for v in versions)
            
            # Yeni versiyon oluştur
            version = DocumentVersion(
                document_id=document_id,
                version_number=last_version_number + 1,
                content=document.content,
                metadata=document.metadata,
                created_by=user_id,
                created_at=datetime.now(timezone.utc),
                change_description=change_description
            )
            
            # Veritabanına kaydet
            new_version = await self.version_repository.create_document_version(db, version)
            
            return {
                "success": True,
                "version": {
                    "id": new_version.id,
                    "document_id": new_version.document_id,
                    "version_number": new_version.version_number,
                    "created_by": new_version.created_by,
                    "created_at": new_version.created_at.isoformat(),
                    "change_description": new_version.change_description
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating document version: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_version(self, 
                      db: AsyncSession, 
                      document_id: str, 
                      version_number: Optional[int] = None) -> Dict[str, Any]:
        """
        Belirli bir belge versiyonunu getirir
        
        Args:
            db: Veritabanı oturumu
            document_id: Belge ID'si
            version_number: Versiyon numarası (None ise son versiyon)
            
        Returns:
            Dict[str, Any]: Versiyon bilgisi
        """
        try:
            if version_number is None:
                # Son versiyonu getir
                versions = await self.version_repository.get_document_versions(db, document_id)
                if not versions:
                    return {"success": False, "error": "No versions found for document"}
                
                version = max(versions, key=lambda v: v.version_number)
            else:
                # Belirli versiyonu getir
                version = await self.version_repository.get_document_version(
                    db, document_id, version_number
                )
                
                if not version:
                    return {"success": False, "error": f"Version {version_number} not found"}
            
            return {
                "success": True,
                "version": {
                    "id": version.id,
                    "document_id": version.document_id,
                    "version_number": version.version_number,
                    "content": version.content,
                    "metadata": version.metadata,
                    "created_by": version.created_by,
                    "created_at": version.created_at.isoformat(),
                    "change_description": version.change_description
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting document version: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_diff(self, 
                  db: AsyncSession, 
                  document_id: str, 
                  from_version: int, 
                  to_version: Optional[int] = None) -> Dict[str, Any]:
        """
        İki versiyon arasındaki farkları getirir
        
        Args:
            db: Veritabanı oturumu
            document_id: Belge ID'si
            from_version: Başlangıç versiyonu
            to_version: Bitiş versiyonu (None ise mevcut belge)
            
        Returns:
            Dict[str, Any]: Fark bilgisi
        """
        try:
            # Başlangıç versiyonunu getir
            from_version_obj = await self.version_repository.get_document_version(
                db, document_id, from_version
            )
            
            if not from_version_obj:
                return {"success": False, "error": f"Version {from_version} not found"}
            
            # Bitiş versiyonu belirtilmediyse mevcut belgeyi kullan
            if to_version is None:
                # Mevcut belgeyi getir
                document = await self.document_repository.get_document_by_id(db, document_id)
                if not document:
                    return {"success": False, "error": "Document not found"}
                
                to_content = document.content
                to_version_info = "current"
            else:
                # Belirtilen versiyonu getir
                to_version_obj = await self.version_repository.get_document_version(
                    db, document_id, to_version
                )
                
                if not to_version_obj:
                    return {"success": False, "error": f"Version {to_version} not found"}
                
                to_content = to_version_obj.content
                to_version_info = to_version
            
            # İçerik farkı hesapla
            from_lines = from_version_obj.content.splitlines()
            to_lines = to_content.splitlines()
            
            differ = difflib.Differ()
            diff = list(differ.compare(from_lines, to_lines))
            
            # HTML formatında farkı oluştur
            html_diff = []
            for line in diff:
                if line.startswith('+ '):
                    html_diff.append(f'<div class="diff-added">{line[2:]}</div>')
                elif line.startswith('- '):
                    html_diff.append(f'<div class="diff-removed">{line[2:]}</div>')
                elif line.startswith('? '):
                    continue
                else:
                    html_diff.append(f'<div class="diff-unchanged">{line[2:]}</div>')
            
            return {
                "success": True,
                "from_version": from_version,
                "to_version": to_version_info,
                "diff_text": '\n'.join(diff),
                "diff_html": '\n'.join(html_diff)
            }
            
        except Exception as e:
            logger.error(f"Error getting document diff: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def restore_version(self, 
                         db: AsyncSession, 
                         document_id: str, 
                         version_number: int,
                         user_id: str) -> Dict[str, Any]:
        """
        Belgeyi belirli bir versiyona geri döndürür
        
        Args:
            db: Veritabanı oturumu
            document_id: Belge ID'si
            version_number: Geri dönülecek versiyon numarası
            user_id: İşlemi yapan kullanıcı ID'si
            
        Returns:
            Dict[str, Any]: İşlem sonucu
        """
        try:
            # Belgeyi getir
            document = await self.document_repository.get_document_by_id(db, document_id)
            if not document:
                return {"success": False, "error": "Document not found"}
            
            # Versiyonu getir
            version = await self.version_repository.get_document_version(
                db, document_id, version_number
            )
            
            if not version:
                return {"success": False, "error": f"Version {version_number} not found"}
            
            # Önce mevcut durumun yeni versiyonunu oluştur
            await self.create_version(
                db=db,
                document_id=document_id,
                user_id=user_id,
                change_description=f"State before restoring to version {version_number}"
            )
            
            # Belgeyi güncelle
            await self.document_repository.update_document(
                db=db,
                document_id=document_id,
                content=version.content,
                metadata=version.metadata
            )
            
            # Restore işleminin versiyonunu oluştur
            restore_version = await self.create_version(
                db=db,
                document_id=document_id,
                user_id=user_id,
                change_description=f"Restored to version {version_number}"
            )
            
            return {
                "success": True,
                "message": f"Document restored to version {version_number}",
                "version": restore_version
            }
            
        except Exception as e:
            logger.error(f"Error restoring document version: {str(e)}")
            return {"success": False, "error": str(e)}