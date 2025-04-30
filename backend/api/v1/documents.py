# Last reviewed: 2025-04-29 14:12:11 UTC (User: TeeksssKullanıcı)
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Body, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List, Union
import logging
import uuid
from datetime import datetime

from ...db.session import get_db
from ...schemas.document import DocumentCreate, DocumentResponse, DocumentUpdate, DocumentListResponse
from ...repositories.document_repository import DocumentRepository
from ...services.document_service import DocumentService
from ...services.storage_service import StorageService
from ...services.audit_service import AuditService, AuditLogType
from ...auth.jwt import get_current_active_user, get_current_user_optional

router = APIRouter(
    prefix="/api/documents",
    tags=["documents"],
    responses={401: {"description": "Unauthorized"}}
)

logger = logging.getLogger(__name__)
document_service = DocumentService()
storage_service = StorageService()
audit_service = AuditService()

@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    search: Optional[str] = Query(None, description="Search query for documents"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    collection_id: Optional[str] = Query(None, description="Filter by collection"),
    status: Optional[str] = Query(None, description="Filter by status"),
    sort_by: str = Query("updated_at", description="Field to sort by"),
    sort_dir: str = Query("desc", description="Sort direction (asc, desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Belgeleri listeler
    
    Parametreler:
    - **search**: Belge başlığı/içeriğinde arama yapmak için sorgu
    - **tags**: Etiketlere göre filtreleme
    - **collection_id**: Koleksiyona göre filtreleme
    - **status**: Duruma göre filtreleme
    - **sort_by**: Sıralama alanı (title, created_at, updated_at, vb.)
    - **sort_dir**: Sıralama yönü (asc, desc)
    - **page**: Sayfa numarası
    - **page_size**: Sayfa başına sonuç sayısı
    
    Dönüş:
    - DocumentListResponse: Belge listesi ve meta veriler
    """
    try:
        # Belgeleri getir
        documents = await document_service.list_documents(
            db=db,
            user_id=current_user["id"],
            search=search,
            tags=tags,
            collection_id=collection_id,
            status=status,
            sort_by=sort_by,
            sort_dir=sort_dir,
            page=page,
            page_size=page_size
        )
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.DATA,
            user_id=current_user["id"],
            action="list",
            resource_type="documents",
            status="success",
            details={
                "search": search,
                "tags": tags,
                "collection_id": collection_id,
                "status": status,
                "page": page,
                "page_size": page_size
            },
            db=db
        )
        
        return documents
    
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.DATA,
            user_id=current_user["id"],
            action="list",
            resource_type="documents",
            status="failure",
            details={
                "error": str(e),
                "search": search,
                "tags": tags,
                "collection_id": collection_id
            },
            db=db
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while listing documents: {str(e)}"
        )

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    include_content: bool = Query(False, description="Include document content"),
    current_user: Dict[str, Any] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Belge detaylarını getirir
    
    Parametreler:
    - **document_id**: Belge ID
    - **include_content**: Belge içeriği dahil edilsin mi
    
    Dönüş:
    - DocumentResponse: Belge detayları
    """
    try:
        # Belgeyi getir
        document = await document_service.get_document(
            db=db,
            document_id=document_id,
            user_id=current_user["id"] if current_user else None,
            include_content=include_content
        )
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Audit log kaydı
        if current_user:
            await audit_service.log_event(
                event_type=AuditLogType.DATA,
                user_id=current_user["id"],
                action="view",
                resource_type="document",
                resource_id=document_id,
                status="success",
                db=db
            )
        
        return document
    
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(f"Error getting document: {str(e)}")
        
        # Audit log kaydı
        if current_user:
            await audit_service.log_event(
                event_type=AuditLogType.DATA,
                user_id=current_user["id"],
                action="view",
                resource_type="document",
                resource_id=document_id,
                status="failure",
                details={"error": str(e)},
                db=db
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while getting document: {str(e)}"
        )

@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    collection_id: Optional[str] = Form(None),
    is_public: bool = Form(False),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Yeni bir belge oluşturur
    
    Parametreler:
    - **file**: Yüklenecek dosya
    - **title**: Belge başlığı
    - **description**: Belge açıklaması (opsiyonel)
    - **tags**: Virgülle ayrılmış etiketler (opsiyonel)
    - **collection_id**: Koleksiyon ID (opsiyonel)
    - **is_public**: Herkese açık mı
    
    Dönüş:
    - DocumentResponse: Oluşturulan belge
    """
    try:
        # IP adresini al
        client_ip = request.client.host if request.client else None
        
        # Form verilerini hazırla
        document_data = DocumentCreate(
            title=title,
            description=description,
            tags=tags.split(",") if tags else [],
            collection_id=collection_id,
            is_public=is_public
        )
        
        # Dosyayı yükle ve belgeyi oluştur
        document = await document_service.create_document(
            db=db,
            document_data=document_data,
            file=file,
            user_id=current_user["id"],
            organization_id=current_user.get("organization_id")
        )
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.DATA,
            user_id=current_user["id"],
            action="create",
            resource_type="document",
            resource_id=document.id,
            status="success",
            details={
                "title": title,
                "is_public": is_public,
                "file_name": file.filename,
                "content_type": file.content_type
            },
            ip_address=client_ip,
            db=db
        )
        
        return document
    
    except Exception as e:
        logger.error(f"Error creating document: {str(e)}")
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.DATA,
            user_id=current_user["id"],
            action="create",
            resource_type="document",
            status="failure",
            details={
                "error": str(e),
                "title": title,
                "file_name": file.filename
            },
            ip_address=client_ip,
            db=db
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating document: {str(e)}"
        )

@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str,
    document_update: DocumentUpdate,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Belge bilgilerini günceller
    
    Parametreler:
    - **document_id**: Güncellenecek belge ID
    - **document_update**: Güncellenecek alanlar
    
    Dönüş:
    - DocumentResponse: Güncellenen belge
    """
    try:
        # Belgenin mevcut olduğunu ve erişim izni olduğunu kontrol et
        existing_document = await document_service.get_document(
            db=db,
            document_id=document_id,
            user_id=current_user["id"]
        )
        
        if not existing_document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or access denied"
            )
        
        # Belgeyi güncelle
        document = await document_service.update_document(
            db=db,
            document_id=document_id,
            document_update=document_update,
            user_id=current_user["id"]
        )
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.DATA,
            user_id=current_user["id"],
            action="update",
            resource_type="document",
            resource_id=document_id,
            status="success",
            details={
                "updated_fields": document_update.dict(exclude_unset=True)
            },
            db=