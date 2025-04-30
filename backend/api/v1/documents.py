# Last reviewed: 2025-04-30 05:56:23 UTC (User: Teeksss)
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
import os
import uuid
import shutil
from datetime import datetime
import logging

from ...db.session import get_db
from ...repositories.document_repository import DocumentRepository
from ...schemas.document import DocumentCreate, DocumentResponse, DocumentList, DocumentUpdate
from ...services.document_processor import DocumentProcessorService
from ...core.config import settings
from ...auth.jwt import get_current_active_user
from ...services.audit_service import AuditService, AuditLogType
from ...core.exceptions import NotFoundError, PermissionError

router = APIRouter(prefix="/documents", tags=["documents"])
logger = logging.getLogger(__name__)

document_repository = DocumentRepository()
document_processor = DocumentProcessorService()
audit_service = AuditService()

@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    title: str = Form(...),
    file: UploadFile = File(...),
    apply_ocr: bool = Form(False),  # OCR uygulanıp uygulanmayacağı
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Yeni bir belge yükler ve oluşturur
    - **title**: Belge başlığı
    - **file**: Yüklenecek dosya
    - **apply_ocr**: OCR işlemi uygulansın mı? (varsayılan: False)
    """
    try:
        # Yükleme dizinini oluştur (yoksa)
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        # Benzersiz dosya adı oluştur
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
        
        # Dosyayı kaydet
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Dosya hash'ini hesapla (kopya kontrolü için)
        file_hash = await document_repository.calculate_file_hash(file_path)
        
        # Belge işleme
        file_info = await document_processor.get_file_info(file_path)
        file_type = file_info.get("file_type", "")
        file_size = os.path.getsize(file_path)
        
        # OCR işlemi (isteğe bağlı)
        content = ""
        if apply_ocr:
            content = await document_processor.extract_text_from_file(file_path, file_type)
        else:
            # OCR olmadan basit metin çıkarma
            content = await document_processor.extract_basic_text(file_path, file_type)
        
        # Belgeyi veritabanına kaydet
        document = await document_repository.create_document(
            db=db,
            title=title,
            content=content,
            file_path=file_path,
            file_name=file.filename,
            file_type=file_type,
            file_size=file_size,
            file_hash=file_hash,
            metadata={
                "original_filename": file.filename,
                "upload_time": datetime.now().isoformat(),
                "content_type": file.content_type,
                "ocr_applied": apply_ocr
            },
            user_id=current_user["id"],
            organization_id=current_user.get("organization_id")
        )
        
        # Audit log
        await audit_service.log_event(
            event_type=AuditLogType.DATA,
            user_id=current_user["id"],
            action="create",
            resource_type="document",
            resource_id=str(document.id),
            details={
                "title": title, 
                "file_name": file.filename,
                "file_size": file_size,
                "file_type": file_type,
                "ocr_applied": apply_ocr
            },
            db=db
        )
        
        return document
        
    except Exception as e:
        # Hata durumunda dosyayı temizle
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        
        # Aynı belge yüklenmeye çalışılıyorsa özel hata
        if 'duplicate' in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A document with identical content already exists"
            )
        
        logger.error(f"Error creating document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str = Path(...),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Belirli bir belgeyi getirir
    - **document_id**: Belge ID
    """
    try:
        # Kullanıcı süper kullanıcı değilse ve farklı organizasyondan belge istiyorsa
        # belge erişimini kısıtla
        is_superuser = current_user.get("is_superuser", False)
        
        document = await document_repository.get_document_by_id(db, document_id)
        
        # Organizasyon kontrolü
        if not is_superuser and document.organization_id != current_user.get("organization_id"):
            raise PermissionError(
                message="Permission denied",
                error_code="INSUFFICIENT_PRIVILEGES",
                detail="You don't have permission to access this document"
            )
        
        # Audit log
        await audit_service.log_event(
            event_type=AuditLogType.ACCESS,
            user_id=current_user["id"],
            action="read",
            resource_type="document",
            resource_id=document_id,
            db=db
        )
        
        return document
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message
        )
    except Exception as e:
        logger.error(f"Error getting document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str = Path(...),
    force: bool = Query(False, description="Süper kullanıcılar için zorunlu silme"),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Belgeyi siler
    - **document_id**: Belge ID
    - **force**: Süper kullanıcılar için zorunlu silme (sahibi olmasa bile)
    """
    try:
        is_superuser = current_user.get("is_superuser", False)
        
        # Belgeyi getir (önce belgenin var olduğundan emin ol)
        document = await document_repository.get_document_by_id(db, document_id)
        
        # Sadece belge sahibi veya süper kullanıcı silebilir
        if not is_superuser and document.user_id != current_user["id"]:
            raise PermissionError(
                message="Permission denied",
                error_code="INSUFFICIENT_PRIVILEGES",
                detail="You don't have permission to delete this document"
            )
        
        # Süper kullanıcı olmayan ve belgenin sahibi olmayan kullanıcılar silemez
        check_owner = not is_superuser
        
        # Force parametresi sadece süper kullanıcılar için geçerlidir
        if force and not is_superuser:
            force = False
            
        await document_repository.delete_document(
            db=db, 
            document_id=document_id, 
            check_owner=check_owner,
            user_id=current_user["id"],
            force=force
        )
        
        # Audit log
        await audit_service.log_event(
            event_type=AuditLogType.DATA,
            user_id=current_user["id"],
            action="delete",
            resource_type="document",
            resource_id=document_id,
            details={"title": document.title, "forced": force},
            db=db
        )
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message
        )
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/", response_model=DocumentList)
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = Query(None, description="Title or content search"),
    file_type: Optional[str] = Query(None, description="File type filter"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)"),
    user_documents: bool = Query(False, description="Only show current user's documents"),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Belgeleri listeler
    - **skip**: Atlanacak belge sayısı
    - **limit**: Maksimum belge sayısı
    - **search**: Başlık veya içerik araması
    - **file_type**: Dosya türüne göre filtreleme
    - **sort_by**: Sıralama alanı
    - **sort_order**: Sıralama yönü (asc veya desc)
    - **user_documents**: Sadece mevcut kullanıcının belgelerini göster
    """
    try:
        # Kullanıcı yetkilerine göre filtrele
        is_superuser = current_user.get("is_superuser", False)
        
        user_id = None
        organization_id = current_user.get("organization_id")
        
        # Sadece kullanıcı belgeleri isteniyorsa
        if user_documents:
            user_id = current_user["id"]
        
        # Süper kullanıcılar tüm belgeleri görebilir
        if is_superuser:
            organization_id = None
        
        # Belgeleri listele
        result = await document_repository.list_documents(
            db=db,
            skip=skip,
            limit=limit,
            user_id=user_id,
            organization_id=organization_id,
            search_term=search,
            file_type=file_type,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # Audit log
        await audit_service.log_event(
            event_type=AuditLogType.ACCESS,
            user_id=current_user["id"],
            action="list",
            resource_type="documents",
            details={
                "search": search,
                "file_type": file_type,
                "user_documents": user_documents,
                "count": len(result["items"])
            },
            db=db
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )