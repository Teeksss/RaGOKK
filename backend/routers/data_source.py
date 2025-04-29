# Last reviewed: 2025-04-29 07:07:30 UTC (User: Teeksss)
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Body, BackgroundTasks, Request, status
from typing import List, Optional, Dict, Any, Union
import os
import base64
import time
import asyncio
import traceback
from datetime import datetime
import magic
from werkzeug.utils import secure_filename
from elasticsearch import AsyncElasticsearch, NotFoundError, RequestError
from elasticsearch.helpers import async_scan, async_bulk
import re # Tablo adı doğrulaması için

# VERİ İŞLEME NOTU (Chunking)
# Adım 10: Chunking Stratejisi Notları
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter, TokenTextSplitter, SentenceTransformersTokenTextSplitter
    # Farklı splitter'lar denenebilir:
    # text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    # text_splitter = TokenTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    # text_splitter = SentenceTransformersTokenTextSplitter(chunk_overlap=CHUNK_OVERLAP, model_name=SEMANTIC_MODEL)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    logger.info(f"Langchain Text Splitter kullanılıyor: {type(text_splitter).__name__}")
except ImportError:
    logger.warning("Langchain kurulu değil, basit chunking kullanılacak (önerilmez).")
    text_splitter = None # Basit chunking fonksiyonu yazılabilir

# Utils
from ..utils.database import es_client
# Adım 6: Async embedding fonksiyonu import edildi
from ..utils.semantic_search import get_text_embedding_async, get_vector_dimension
from ..utils.logger import get_logger
# Adım 9 (RBAC): require_admin import edildi
from ..auth import UserInDB as User, get_current_active_user, require_admin
from ..utils.config import MAX_UPLOAD_FILE_SIZE_MB, ALLOWED_MIME_TYPES, CHUNK_SIZE, CHUNK_OVERLAP

# Konnektörler (async versiyonları import edildi)
# Adım 6: Async I/O
from ..utils.ocr import extract_text_from_image_async
from ..utils.pdf_reader import read_pdf_async
from ..utils.web_scraper import scrape_website # Zaten async
from ..utils.database_connector import (
    connect_to_postgresql, fetch_data_from_postgresql,
    connect_to_mysql, fetch_data_from_mysql,
    connect_to_mongodb, fetch_data_from_mongodb,
    connect_to_sqlite, fetch_data_from_sqlite
) # Bunlar hala senkron, to_thread ile kullanılacak
from ..utils.cloud_storage_connector import read_google_drive_file, read_dropbox_file # Zaten async
from ..utils.email_connector import connect_to_email, fetch_emails # Senkron, to_thread ile kullanılacak
# Adım 15: Facebook/LinkedIn import edildi
from ..utils.social_media_connector import search_recent_tweets, get_facebook_page_posts, get_linkedin_company_updates # search_recent_tweets zaten async

# Modeller
from ..models.data_models import (
    AddManualDocRequest, AddWebsiteRequest, DbCreds, MongoCreds, SqliteCreds,
    CloudStorageRequest, EmailRequest, TwitterRequest, DataSourceListResponseItem
)

logger = get_logger(__name__)
router = APIRouter()

# --- Elasticsearch Index Ayarları ---
# ... (önceki INDEX_NAME, VECTOR_DIMENSION, INDEX_SETTINGS, INDEX_MAPPINGS) ...

async def ensure_index_exists(index_name: str):
    # ... (önceki kod) ...

# --- Dosya Yükleme Yardımcı Fonksiyonu ---
async def _validate_uploaded_file(file: UploadFile) -> str:
    # ... (önceki kod) ...

# --- Yardımcı İndeksleme Fonksiyonları ---
async def run_bulk_index(actions: List[Dict], operation_desc: str):
    # ... (önceki kod) ...

async def index_document_with_chunking(doc_id: str, document_data: dict, index_name: str = INDEX_NAME):
    """Belgeyi (gerekirse chunk'lara ayırarak) Elasticsearch'e indeksler (Async Embedding ile)."""
    # ... (önceki kod - VECTOR_DIMENSION kontrolü) ...
    text_content = document_data.get("text", "")
    actions = []
    created_time = datetime.utcnow()
    # Adım 10: Chunking Stratejisi Notu: Chunking koşulu ve metodu iyileştirilebilir.
    should_chunk = text_splitter and text_content and len(text_content) > (CHUNK_SIZE + CHUNK_OVERLAP)

    if should_chunk:
        # ... (önceki chunking kodu) ...
        try:
            # Adım 6: Async embedding
            embedding = await get_text_embedding_async(chunk_text)
            if embedding and len(embedding) == VECTOR_DIMENSION: chunk_data["text_vector"] = embedding
            # ... (önceki chunking kodu) ...
        except Exception as emb_err: logger.error(f"Embedding hatası (chunk {chunk_id}): {emb_err}", exc_info=True)
        # ... (önceki chunking kodu) ...
    else:
         # ... (önceki kod) ...
         if text_content:
             try:
                 # Adım 6: Async embedding
                 embedding = await get_text_embedding_async(text_content)
                 if embedding and len(embedding) == VECTOR_DIMENSION: document_data["text_vector"] = embedding
                 # ... (önceki kod) ...
             except Exception as emb_err: logger.error(f"Embedding hatası (belge {doc_id}): {emb_err}", exc_info=True)
         # ... (önceki kod) ...

    if actions: await run_bulk_index(actions, f"Indexing for {doc_id}")
    else: logger.warning(f"İndekslenecek eylem bulunamadı: {doc_id}")

# --- Veri Kaynağı Ekleme Endpointleri ---
@router.on_event("startup")
async def startup_event(): await ensure_index_exists(INDEX_NAME)

@router.post("/data_source/add_manual", status_code=status.HTTP_202_ACCEPTED)
async def add_manual_data_source( # ... (önceki parametreler) ... ):
    # ... (önceki kod - index_document_with_chunking kullanılıyor) ...
    doc_data = { "text": doc_request.text, "source": doc_request.source or "manual", "owner_user_id": current_user.username, "date": doc_request.date, "popularity": doc_request.popularity }
    background_tasks.add_task(index_document_with_chunking, doc_request.id, doc_data)
    # ... (önceki kod) ...

@router.post("/data_source/add_file", status_code=status.HTTP_202_ACCEPTED)
async def add_file_data_source( # ... (önceki parametreler) ... ):
    # ... (önceki kod - _validate_uploaded_file) ...
    async def process_file_in_background(temp_file_path: str, original_filename: str, mime_type: str, user_id: str):
        # ... (önceki kod - dosya kaydetme) ...
        text_content = None
        doc_id = f"file_{user_id}_{secure_filename(original_filename)}_{int(time.time())}"
        try:
            if mime_type.startswith("image/"):
                # Adım 6: Async OCR
                text_content = await extract_text_from_image_async(temp_file_path)
            elif mime_type == "application/pdf":
                # Adım 6: Async PDF
                text_content = await read_pdf_async(temp_file_path)
            elif mime_type.startswith("text/"):
                # ... (önceki text okuma) ...
            # ... (önceki kod - indexleme) ...
        except (FileNotFoundError, ImportError) as proc_err: logger.error(f"Dosya işleme hatası (background: {original_filename}): {proc_err}"); return # Arka planda hata
        # ... (önceki kod - finally bloğu) ...
    # ... (önceki kod - arka plan görevi başlatma) ...

@router.post("/data_source/add_website", status_code=status.HTTP_202_ACCEPTED)
async def add_website_data_source( # ... (önceki parametreler) ... ):
    # ... (önceki kod) ...
    async def process_website_in_background(url: str, user_id: str):
        doc_id = f"web_{user_id}_{base64.urlsafe_b64encode(url.encode()).decode()[:50]}"
        try:
            # scrape_website zaten async
            text_content = await scrape_website(url)
            # ... (önceki kod - indexleme) ...
        # ... (önceki kod - hata yönetimi) ...
    # ... (önceki kod - arka plan görevi başlatma) ...

# --- Veritabanı Endpointleri ---
async def process_db_data(conn_func, fetch_func, creds: Union[DbCreds, MongoCreds, SqliteCreds], source_type: str, background_tasks: BackgroundTasks, current_user: User):
    # ... (önceki kod - to_thread ile senkron DB fonksiyonları çağrılıyor) ...
    # Adım 6: Async I/O (to_thread kullanımı)
    # Adım 7: Pooling Notu: conn_func havuzdan bağlantı almalı.
    conn = await asyncio.to_thread(conn_func, **conn_args)
    # ... (önceki kod) ...
    data = await asyncio.to_thread(fetch_func, conn, **fetch_args)
    # ... (önceki kod) ...

async def bulk_index_db_data(items_to_index: List[Dict], index_name: str):
    # ... (önceki kod - async embedding kullanıyor) ...
    try:
        # Adım 6: Async embedding
        embedding = await get_text_embedding_async(chunk_text)
        # ... (önceki kod) ...
    except Exception as emb_err: logger.error(f"Embedding hatası (db chunk {chunk_id}): {emb_err}")
    # ... (önceki kod) ...
    if not should_chunk:
        # ... (önceki kod) ...
        if text_content:
            try:
                # Adım 6: Async embedding
                embedding = await get_text_embedding_async(text_content)
                # ... (önceki kod) ...
            except Exception as emb_err: logger.error(f"Embedding hatası (db doc {doc_id}): {emb_err}")
        # ... (önceki kod) ...

# DB Endpointleri
# ... (önceki DB endpointleri process_db_data kullanıyor) ...
# Adım 9 (RBAC): SQLite endpoint'i admin gerektiriyor.
@router.post("/data_source/add_sqlite", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(require_admin)])
async def add_sqlite_data_source(creds: SqliteCreds, background_tasks: BackgroundTasks, current_user: User = Depends(get_current_active_user)):
    # ... (önceki kod) ...

# --- Bulut Depolama Endpointleri ---
@router.post("/data_source/add_google_drive", status_code=status.HTTP_202_ACCEPTED)
async def add_google_drive_data_source( # ... (önceki parametreler) ... ):
    # ... (önceki kod) ...
    async def process_gdrive_in_background(file_id: str, user_id: str):
        doc_id = f"gdrive_{user_id}_{file_id}"
        try:
            # read_google_drive_file zaten async
            text_content = await read_google_drive_file(file_id, user_id)
            # ... (önceki kod - indexleme) ...
        # ... (önceki kod - hata yönetimi) ...
    # ... (önceki kod - arka plan görevi başlatma) ...

@router.post("/data_source/add_dropbox", status_code=status.HTTP_202_ACCEPTED)
async def add_dropbox_data_source( # ... (önceki parametreler) ... ):
    # ... (önceki kod) ...
    async def process_dropbox_in_background(file_path: str, user_id: str):
        doc_id = f"dropbox_{user_id}_{base64.urlsafe_b64encode(file_path.encode()).decode()[:50]}"
        try:
            # read_dropbox_file zaten async
            text_content = await read_dropbox_file(file_path) # TODO: User ID iletilmeli (OAuth sonrası)
            # ... (önceki kod - indexleme) ...
        # ... (önceki kod - hata yönetimi) ...
    # ... (önceki kod - arka plan görevi başlatma) ...

# --- E-posta Endpointi ---
@router.post("/data_source/add_email", status_code=status.HTTP_202_ACCEPTED)
async def add_email_data_source( # ... (önceki parametreler) ... ):
    # ... (önceki kod) ...
    async def process_email_in_background(mailbox: str, criteria: str, num_latest: int, user_id: str):
        conn = None
        actions_to_index = []
        try:
            # Adım 6: Async I/O (to_thread kullanımı)
            conn = await asyncio.to_thread(connect_to_email)
            if not conn: raise ConnectionError("E-posta sunucusuna bağlanılamadı.")
            # Adım 6: Async I/O (to_thread kullanımı)
            emails_data = await asyncio.to_thread(fetch_emails, conn, mailbox, criteria, num_latest)
            # ... (önceki kod - email verilerini işleme ve actions_to_index'e ekleme) ...
        # ... (önceki kod - hata yönetimi ve finally bloğu) ...
        # Adım 6: bulk_index_db_data async embedding kullanıyor
        if actions_to_index: await bulk_index_db_data(actions_to_index, INDEX_NAME)
    # ... (önceki kod - arka plan görevi başlatma) ...

# --- Sosyal Medya Endpointleri ---
@router.post("/data_source/add_twitter", status_code=status.HTTP_202_ACCEPTED)
async def add_twitter_data_source( # ... (önceki parametreler) ... ):
    # ... (önceki kod) ...
    async def process_twitter_in_background(query: str, max_results: int, user_id: str):
        actions_to_index = []
        try:
            # search_recent_tweets zaten async
            tweets_data = await search_recent_tweets(query, max_results)
            # ... (önceki kod - tweet verilerini işleme ve actions_to_index'e ekleme) ...
        # ... (önceki kod - hata yönetimi) ...
        # Adım 6: bulk_index_db_data async embedding kullanıyor
        if actions_to_index: await bulk_index_db_data(actions_to_index, INDEX_NAME)
    # ... (önceki kod - arka plan görevi başlatma) ...

# Adım 15: Facebook/LinkedIn Endpointleri (Placeholder)
@router.post("/data_source/add_facebook", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def add_facebook_data_source(background_tasks: BackgroundTasks, current_user: User = Depends(get_current_active_user), page_id: str = Body(...), max_results: int = Body(10)):
    logger.warning("Facebook veri kaynağı ekleme henüz implemente edilmedi.")
    # TODO: OAuth token'ını kullanıcıya özel olarak al/sakla (DB).
    # page_access_token = get_facebook_token_for_user(current_user.username)
    # background_tasks.add_task(process_facebook_in_background, page_id, page_access_token, max_results, current_user.username)
    raise HTTPException(status_code=501, detail="Facebook entegrasyonu henüz mevcut değil.")

@router.post("/data_source/add_linkedin", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def add_linkedin_data_source(background_tasks: BackgroundTasks, current_user: User = Depends(get_current_active_user), company_urn_or_id: str = Body(...), max_results: int = Body(10)):
    logger.warning("LinkedIn veri kaynağı ekleme henüz implemente edilmedi.")
    # TODO: OAuth token'ını kullanıcıya özel olarak al/sakla (DB).
    # access_token = get_linkedin_token_for_user(current_user.username)
    # background_tasks.add_task(process_linkedin_in_background, company_urn_or_id, access_token, max_results, current_user.username)
    raise HTTPException(status_code=501, detail="LinkedIn entegrasyonu henüz mevcut değil.")


# --- Veri Yönetimi Endpointleri ---
@router.delete("/data_source/{document_id}", status_code=status.HTTP_200_OK)
async def delete_data_source( # ... (önceki parametreler) ... ):
    # ... (önceki kod - kullanıcı sahipliği kontrolü dahil) ...
    # Adım 9 (RBAC): Admin kontrolü veya sahiplik kontrolü yapılıyor.
    # ... (önceki kod) ...

@router.get("/data_source/list", response_model=List[DataSourceListResponseItem])
async def list_data_sources( # ... (önceki parametreler) ... ):
    # ... (önceki kod - kullanıcı izolasyonu filtresi dahil) ...
    # Adım 9 (RBAC): Admin olmayanlar için filtre uygulanıyor.
    # ... (önceki kod) ...

# Adım 9 (RBAC): Yeniden indeksleme admin gerektiriyor.
@router.post("/data_source/reindex", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(require_admin)])
async def reindex_data_sources( # ... (önceki parametreler) ... ):
    # ... (önceki kod - arka plan görevi mantığı) ...
    # Arka plan görevi (bulk_index_db_data gibi) async embedding kullanmalı.
    # ... (önceki kod) ...

# --- Değerlendirme Endpointi (Placeholder) ---
# Adım 16: Değerlendirme Endpoint'i Notları
# Adım 9 (RBAC): Değerlendirme admin gerektiriyor.
@router.post("/evaluate", summary="RAG Pipeline Değerlendirme (Placeholder)", status_code=status.HTTP_501_NOT_IMPLEMENTED, dependencies=[Depends(require_admin)])
async def evaluate_pipeline(current_user: User = Depends(get_current_active_user)):
    """
    RAG pipeline'ının performansını değerlendirir (Henüz implemente edilmedi).
    TODO:
    1. Bir değerlendirme veri seti tanımla (soru, beklenen cevap, bağlam ID'leri).
    2. Veri setindeki her soru için RAG pipeline'ını çalıştır (/api/query gibi).
    3. Elde edilen yanıtı ve bulunan belgeleri RAGAS gibi bir kütüphane kullanarak değerlendir.
       - Faithfulness: Yanıtın sağlanan bağlama ne kadar dayandığı.
       - Answer Relevancy: Yanıtın sorulan soruyla ne kadar ilgili olduğu.
       - Context Precision/Recall: Bulunan belgelerin ne kadar ilgili olduğu.
    4. Metrik sonuçlarını hesapla ve döndür.
    """
    logger.warning("RAG pipeline değerlendirme endpoint'i henüz implemente edilmedi.")
    # Placeholder sonuçlar
    results = {
        "faithfulness_score": 0.0, "answer_relevancy_score": 0.0,
        "context_precision": 0.0, "context_recall": 0.0,
        "answer_similarity": 0.0, # Gerekirse
    }
    # raise HTTPException(status_code=501, detail="Değerlendirme endpoint'i henüz mevcut değil.")
    return {"message": "Değerlendirme placeholder", "results": results}