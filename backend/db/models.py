# Last reviewed: 2025-04-29 11:15:42 UTC (User: TeeksssPDF)
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum, Float
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()

# User modeli
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True))

# Doküman modeli
class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(Text)
    metadata = Column(Text)  # JSON olarak saklanan metadata
    owner_id = Column(String, index=True)
    source_url = Column(String)
    source_type = Column(String, index=True)  # pdf, docx, html, etc.
    is_processed = Column(Boolean, default=False)  # Embedding yapıldı mı?
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), index=True)
    last_viewed = Column(DateTime(timezone=True))
    view_count = Column(Integer, default=0)

# Doküman versiyonları
class DocumentVersion(Base):
    __tablename__ = "document_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), index=True)
    content = Column(Text)
    metadata = Column(Text)  # JSON olarak saklanan metadata
    version_label = Column(String, index=True)  # v1.0, v2.0, etc.
    created_by = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    change_description = Column(Text)

# Doküman etiketleri
class DocumentTag(Base):
    __tablename__ = "document_tags"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), index=True)
    tag_name = Column(String, index=True)
    created_by = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Doküman izinleri
class UserDocumentPermission(Base):
    __tablename__ = "user_document_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), index=True)
    user_id = Column(String, index=True)
    permission_type = Column(String)  # read, write, admin
    granted_by = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True))

# Doküman embeddings
class DocumentEmbedding(Base):
    __tablename__ = "document_embeddings"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), index=True)
    chunk_id = Column(String, index=True)
    chunk_text = Column(Text)
    embedding = Column(Text)  # Base64 kodlanmış vektör
    embedding_model = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True))

# Doküman senkronizasyon durumu
class DocumentSync(Base):
    __tablename__ = "document_syncs"
    
    id = Column(Integer, primary_key=True, index=True)
    source_path = Column(String, unique=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), index=True)
    last_sync_time = Column(DateTime(timezone=True))
    last_modified_time = Column(DateTime(timezone=True))
    hash_value = Column(String)  # Dosya hash değeri
    sync_status = Column(String)  # success, failed
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True))