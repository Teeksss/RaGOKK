# Last reviewed: 2025-04-29 06:43:57 UTC (User: Teeksss)
from pydantic import BaseModel, Field, HttpUrl, validator, EmailStr, constr
from typing import List, Optional, Dict, Union
from datetime import datetime
import re

# --- Base Models ---
class BaseDataSourceRequest(BaseModel):
    """Veri kaynağı ekleme istekleri için temel model."""
    pass

# --- Request Modelleri ---
class AddManualDocRequest(BaseDataSourceRequest):
    id: constr(strip_whitespace=True, min_length=1, max_length=100, pattern=r'^[a-zA-Z0-9_-]+$') = Field(
        ...,
        description="Belge için benzersiz, boşluksuz ID (harf, rakam, _, -).",
        examples=["my-document_123"]
    )
    text: str = Field(..., min_length=1, description="Belgenin metin içeriği.")
    source: Optional[str] = Field("manual", max_length=50, description="Veri kaynağı türü.")
    date: Optional[datetime] = None
    popularity: Optional[int] = Field(None, ge=0, description="Popülerlik skoru (varsa).")

class AddWebsiteRequest(BaseDataSourceRequest):
    url: HttpUrl = Field(..., description="İçeriği çekilecek web sitesinin tam URL'si.")

class BaseDbCreds(BaseDataSourceRequest):
    """SQL veritabanı bağlantı bilgileri için temel model."""
    table_name: constr(strip_whitespace=True, min_length=1, max_length=100) = Field(..., description="Veri çekilecek tablo adı.")
    columns: Optional[List[constr(strip_whitespace=True, min_length=1)]] = Field(None, min_length=1, description="Çekilecek sütun adları (boşsa tümü).")
    limit: Optional[int] = Field(None, ge=1, description="Çekilecek maksimum satır sayısı.")

class DbCreds(BaseDbCreds):
    """PostgreSQL ve MySQL için bağlantı bilgileri."""
    host: str = Field(..., min_length=1, description="Veritabanı sunucu adresi.")
    port: int = Field(..., ge=1, le=65535, description="Veritabanı port numarası.")
    database: str = Field(..., min_length=1, description="Veritabanı adı.")
    user: str = Field(..., min_length=1, description="Veritabanı kullanıcı adı.")
    password: str = Field(..., description="Veritabanı şifresi.")

class MongoCreds(BaseDataSourceRequest):
    """MongoDB bağlantı bilgileri."""
    host: str = Field(..., description="MongoDB bağlantı adresi (örn: localhost:27017 veya mongodb://...).")
    database: str = Field(..., min_length=1, description="Veritabanı adı.")
    collection_name: constr(strip_whitespace=True, min_length=1) = Field(..., description="Veri çekilecek koleksiyon adı.")
    user: Optional[str] = Field(None, min_length=1, description="MongoDB kullanıcı adı (gerekirse).")
    password: Optional[str] = Field(None, description="MongoDB şifresi (gerekirse).")
    query: Optional[Dict] = Field({}, description="Veri filtrelemek için MongoDB sorgu objesi.")
    projection: Optional[Dict] = Field(None, description="Döndürülecek alanları belirten projeksiyon objesi.")
    limit: int = Field(0, ge=0, description="Çekilecek maksimum belge sayısı (0=limitsiz).")

class SqliteCreds(BaseDataSourceRequest):
    """SQLite bağlantı bilgileri."""
    # GÜVENLİK NOTU: db_path'in sunucu tarafında güvenli bir şekilde ele alındığından emin olun.
    db_path: str = Field(..., min_length=1, description="SQLite veritabanı dosyasının sunucudaki tam yolu.")
    table_name: constr(strip_whitespace=True, min_length=1, max_length=100) = Field(..., description="Veri çekilecek tablo adı.")
    columns: Optional[List[constr(strip_whitespace=True, min_length=1)]] = Field(None, min_length=1, description="Çekilecek sütun adları (boşsa tümü).")
    limit: Optional[int] = Field(None, ge=1, description="Çekilecek maksimum satır sayısı.")

class CloudStorageRequest(BaseDataSourceRequest):
    """Bulut depolama (Google Drive, Dropbox) için istek modeli."""
    identifier: str = Field(..., min_length=1, description="Dosya ID (Google Drive) veya dosya yolu (Dropbox).")

class EmailRequest(BaseDataSourceRequest):
    """E-posta çekme isteği modeli."""
    mailbox: str = Field("inbox", min_length=1, description="E-postaların çekileceği posta kutusu.")
    criteria: str = Field("ALL", description="E-posta arama kriteri (IMAP formatı).")
    num_latest: int = Field(10, ge=1, le=1000, description="Çekilecek en son e-posta sayısı.")

class TwitterRequest(BaseDataSourceRequest):
    """Twitter arama isteği modeli."""
    query: str = Field(..., min_length=1, max_length=512, description="Twitter arama sorgusu (v2 API formatı).")
    max_results: int = Field(10, ge=10, le=100, description="Çekilecek maksimum tweet sayısı (10-100).")

# --- Response Modelleri ---
class DataSourceListResponseItem(BaseModel):
    """Veri kaynağı listeleme yanıtındaki her bir öğe."""
    id: str
    source: Optional[str] = None
    owner_user_id: Optional[str] = None
    created_timestamp: Optional[datetime] = None
    filename: Optional[str] = None
    url: Optional[HttpUrl] = None
    path: Optional[str] = None
    email_subject: Optional[str] = None
    tweet_id: Optional[str] = None
    original_doc_id: Optional[str] = None
    chunk_index: Optional[int] = None

    class Config:
        from_attributes = True

class RetrievedDocSourceInfo(BaseModel):
    """Retrieved document için kaynak bilgileri (detaylı)."""
    source: Optional[str] = None
    owner_user_id: Optional[str] = None
    created_timestamp: Optional[datetime] = None
    filename: Optional[str] = None
    url: Optional[HttpUrl] = None
    path: Optional[str] = None
    email_subject: Optional[str] = None
    tweet_id: Optional[str] = None
    original_doc_id: Optional[str] = None
    chunk_index: Optional[int] = None
    # Diğer meta alanları eklenebilir
    class Config:
        from_attributes = True

class RetrievedDoc(BaseModel):
    """Retriever tarafından döndürülen her bir belge/chunk."""
    id: str
    score: Optional[float] = None
    text: Optional[str] = None
    source_info: Optional[RetrievedDocSourceInfo] = None

class QueryResponse(BaseModel):
    """RAG pipeline yanıt modeli."""
    answer: str
    retrieved_documents: List[RetrievedDoc]

class QueryRequest(BaseModel):
    """RAG pipeline sorgu isteği modeli."""
    query: str = Field(..., min_length=1, description="Kullanıcının RAG sorgusu.")