# Last reviewed: 2025-04-30 07:59:11 UTC (User: Teeksss)
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, Path, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
import logging
import os
import shutil
import uuid
import time
from datetime import datetime, timezone

from ...db.session import get_db
from ...services.multimodal_rag import MultimodalRAG
from ...auth.rbac import require_permission, Permission
from ...auth.enhanced_jwt import get_current_user_enhanced

router = APIRouter(prefix="/multimodal", tags=["multimodal"])
logger = logging.getLogger(__name__)

# Servis başlat
multimodal_rag = MultimodalRAG()

# Geçici dosya dizini
TEMP_DIR = os.getenv("TEMP_UPLOAD_DIR", "temp/uploads/images")

# Dizin kontrolü
os.makedirs(TEMP_DIR, exist_ok=True)

@router.post("/query", dependencies=[Depends(require_permission(Permission.RUN_QUERIES))])
async def multimodal_query(
    query: str = Form(..., description="Sorgu metni"),
    images: List[UploadFile] = File(..., description="Analiz edilecek görseller"),
    document_ids: Optional[str] = Form(None, description="JSON formatında belge ID listesi"),
    current_user: Dict[str, Any] = Depends(get_current_user_enhanced),
    db: AsyncSession = Depends(get_db)
):
    """
    Görsel ve metin sorgusu ile multimodal RAG işlemi yapar
    
    - **query**: Sorgu metni
    - **images**: En az 1 en fazla 5 görsel dosya
    - **document_ids**: (Opsiyonel) JSON formatında belge ID listesi "[\"id1\", \"id2\"]"
    """
    try:
        # Görsel dosya sayısı kontrolü
        if not images:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one image must be provided"
            )
            
        if len(images) > 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 5 images allowed"
            )
        
        # Document IDs parse
        doc_ids = None
        if document_ids:
            import json
            try:
                doc_ids = json.loads(document_ids)
                if not isinstance(doc_ids, list):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="document_ids must be a JSON array of strings"
                    )
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid JSON format for document_ids"
                )
        
        # Görsel dosyaları kaydet
        session_id = str(uuid.uuid4())
        session_dir = os.path.join(TEMP_DIR, session_id)
        os.makedirs(session_dir, exist_ok=True)
        
        image_paths = []
        for img in images:
            # Dosya adını güvenli hale getir
            file_extension = os.path.splitext(img.filename)[1].lower()
            safe_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = os.path.join(session_dir, safe_filename)
            
            # Dosyayı kaydet
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(img.file, buffer)
                
            image_paths.append(file_path)
        
        # Multimodal sorguyu işle
        result = await multimodal_rag.process_query_with_images(
            query_text=query,
            image_paths=image_paths,
            document_ids=doc_ids
        )
        
        # İşlem tamamlandıktan sonra geçici dosyaları temizle
        def cleanup_temp_files():
            try:
                shutil.rmtree(session_dir)
            except Exception as e:
                logger.warning(f"Error cleaning up temporary files: {str(e)}")
        
        # 10 dakika sonra geçici dosyaları temizle (çok hızlı silme, istemci görsellere ihtiyaç duyabilir)
        # Gerçek implementasyonda BackgroundTasks ile defer edilmeli
        # Şimdilik yoruma aldık
        # background_tasks.add_task(cleanup_temp_files)
        
        # Session bilgisi ekle
        result["session_id"] = session_id
        result["timestamp"] = datetime.now(timezone.utc).isoformat()
        result["user_id"] = current_user.get("id")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing multimodal query: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing multimodal query: {str(e)}"
        )

@router.get("/document/{document_id}", dependencies=[Depends(require_permission(Permission.VIEW_DOCUMENTS))])
async def multimodal_document_query(
    document_id: str = Path(..., description="Belge ID'si"),
    query: str = Query(..., description="Sorgu metni"),
    current_user: Dict[str, Any] = Depends(get_current_user_enhanced),
    db: AsyncSession = Depends(get_db)
):
    """
    Belirli bir belge için multimodal sorgu işlemi yapar
    
    - **document_id**: Belge ID'si
    - **query**: Sorgu metni
    """
    try:
        # Belge üzerinde multimodal sorgu işle
        result = await multimodal_rag.process_document_with_images(
            document_id=document_id,
            query_text=query,
            db=db
        )
        
        # Zaman damgası ve kullanıcı bilgisi ekle
        result["timestamp"] = datetime.now(timezone.utc).isoformat()
        result["user_id"] = current_user.get("id")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing document multimodal query: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing document multimodal query: {str(e)}"
        )

@router.post("/extract-image-content", dependencies=[Depends(require_permission(Permission.RUN_QUERIES))])
async def extract_image_content(
    image: UploadFile = File(..., description="İçeriği çıkarılacak görsel"),
    extraction_type: str = Form("text_and_content", description="Çıkarım tipi (text_only, content_only, text_and_content)"),
    current_user: Dict[str, Any] = Depends(get_current_user_enhanced)
):
    """
    Görsel içeriğini çıkarır (metin ve/veya içerik açıklaması)
    
    - **image**: Görsel dosya
    - **extraction_type**: Çıkarım tipi (text_only, content_only, text_and_content)
    """
    try:
        # Çıkarım tipi doğrulama
        if extraction_type not in ["text_only", "content_only", "text_and_content"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid extraction_type. Must be one of: text_only, content_only, text_and_content"
            )
        
        # Görsel dosyayı kaydet
        session_id = str(uuid.uuid4())
        session_dir = os.path.join(TEMP_DIR, session_id)
        os.makedirs(session_dir, exist_ok=True)
        
        # Dosya adını güvenli hale getir
        file_extension = os.path.splitext(image.filename)[1].lower()
        safe_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(session_dir, safe_filename)
        
        # Dosyayı kaydet
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        
        # Görsel içeriğini işle
        result = await multimodal_rag.process_image_content(
            image_path=file_path,
            extraction_type=extraction_type
        )
        
        # Session bilgisi ekle
        result["session_id"] = session_id
        result["timestamp"] = datetime.now(timezone.utc).isoformat()
        result["user_id"] = current_user.get("id")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting image content: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting image content: {str(e)}"
        )