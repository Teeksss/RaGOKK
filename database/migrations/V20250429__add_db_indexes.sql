-- Last reviewed: 2025-04-29 13:51:41 UTC (User: TeeksssVeritabanı)
--------------------------------------------------------------------------------
-- RAG Base Veritabanı İndeksleme ve Optimizasyon Migrasyonu
-- 
-- Belge ve arama performansını iyileştirmek için gerekli indeksler ve
-- veritabanı optimizasyonları bu dosyada bulunmaktadır.
--------------------------------------------------------------------------------

-- Documents tablosu için indeksler
--------------------------------------------------------------------------------

-- Belge adına göre LIKE aramaları için partial index
CREATE INDEX IF NOT EXISTS idx_documents_title_trigram 
ON documents USING gin (title gin_trgm_ops);

-- Full-text arama için indeks
CREATE INDEX IF NOT EXISTS idx_documents_fulltext 
ON documents USING gin (to_tsvector('turkish', title || ' ' || COALESCE(content, '')));

-- Kullanıcı erişim hızı için indeks
CREATE INDEX IF NOT EXISTS idx_documents_user_id 
ON documents(user_id);

-- Belge durumu için indeks
CREATE INDEX IF NOT EXISTS idx_documents_status 
ON documents(status);

-- Şirket/organizasyon filtresi için indeks
CREATE INDEX IF NOT EXISTS idx_documents_organization_id 
ON documents(organization_id);

-- Etiket aramaları için JSONB indeksi
CREATE INDEX IF NOT EXISTS idx_documents_tags 
ON documents USING gin (tags jsonb_path_ops);

-- Belge meta verisi kısmi indeksi (etiketler için)
CREATE INDEX IF NOT EXISTS idx_documents_metadata_tags 
ON documents USING gin ((metadata -> 'tags') jsonb_path_ops);

-- Tarih aramaları için indeks
CREATE INDEX IF NOT EXISTS idx_documents_created_at 
ON documents(created_at);

CREATE INDEX IF NOT EXISTS idx_documents_updated_at 
ON documents(updated_at);

-- Sadece silinen belgeleri sorgularken kullanılır - partial index
CREATE INDEX IF NOT EXISTS idx_documents_deleted 
ON documents(deleted_at) 
WHERE deleted_at IS NOT NULL;

-- Sadece herkese açık belgeler için partial index
CREATE INDEX IF NOT EXISTS idx_documents_public 
ON documents(id) 
WHERE is_public = TRUE;

--------------------------------------------------------------------------------

-- Collections (Koleksiyonlar) tablosu için indeksler
--------------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_collections_name_trigram 
ON collections USING gin (name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_collections_user_id 
ON collections(user_id);

CREATE INDEX IF NOT EXISTS idx_collections_organization_id 
ON collections(organization_id);

-- İç içe ebeveyn-çocuk ilişkileri için indeks
CREATE INDEX IF NOT EXISTS idx_collections_parent_id 
ON collections(parent_id);

--------------------------------------------------------------------------------

-- document_collection (Belge-Koleksiyon ilişkisi) tablosu için indeksler
--------------------------------------------------------------------------------

-- Koleksiyona göre belgelerin hızlı sorgulanması için
CREATE INDEX IF NOT EXISTS idx_document_collection_collection_id 
ON document_collection(collection_id);

-- Belgeye göre koleksiyonların hızlı sorgulanması için
CREATE INDEX IF NOT EXISTS idx_document_collection_document_id 
ON document_collection(document_id);

-- Birleşik benzersiz indeks
CREATE UNIQUE INDEX IF NOT EXISTS idx_document_collection_unique 
ON document_collection(document_id, collection_id);

--------------------------------------------------------------------------------

-- Comments (Yorumlar) tablosu için indeksler
--------------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_comments_document_id 
ON comments(document_id);

CREATE INDEX IF NOT EXISTS idx_comments_user_id 
ON comments(user_id);

CREATE INDEX IF NOT EXISTS idx_comments_created_at 
ON comments(created_at);

--------------------------------------------------------------------------------

-- Search History (Arama Geçmişi) tablosu için indeksler
--------------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_search_history_user_id 
ON search_history(user_id);

CREATE INDEX IF NOT EXISTS idx_search_history_created_at 
ON search_history(created_at);

CREATE INDEX IF NOT EXISTS idx_search_history_query_trigram 
ON search_history USING gin (query gin_trgm_ops);

--------------------------------------------------------------------------------

-- User Activity (Kullanıcı Aktiviteleri) tablosu için indeksler
--------------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_user_activity_user_id 
ON user_activity(user_id);

CREATE INDEX IF NOT EXISTS idx_user_activity_document_id 
ON user_activity(document_id);

CREATE INDEX IF NOT EXISTS idx_user_activity_activity_type 
ON user_activity(activity_type);

CREATE INDEX IF NOT EXISTS idx_user_activity_created_at 
ON user_activity(created_at);

--------------------------------------------------------------------------------

-- Partitioning için gereken hazırlıklar
--------------------------------------------------------------------------------

-- Büyük tablolar için partitioning hazırlığı
-- user_activity tablosu için zaman bazlı partitioning

-- Ana tablo oluştur (eğer yoksa)
CREATE TABLE IF NOT EXISTS user_activity_partitioned (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    document_id UUID,
    activity_type VARCHAR(50) NOT NULL,
    activity_data JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    organization_id UUID
) PARTITION BY RANGE (created_at);

-- Partitionlar
CREATE TABLE IF NOT EXISTS user_activity_y2025m01 PARTITION OF user_activity_partitioned
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE IF NOT EXISTS user_activity_y2025m02 PARTITION OF user_activity_partitioned
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

CREATE TABLE IF NOT EXISTS user_activity_y2025m03 PARTITION OF user_activity_partitioned
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');

CREATE TABLE IF NOT EXISTS user_activity_y2025m04 PARTITION OF user_activity_partitioned
    FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');

CREATE TABLE IF NOT EXISTS user_activity_y2025m05 PARTITION OF user_activity_partitioned
    FOR VALUES FROM ('2025-05-01') TO ('2025-06-01');

CREATE TABLE IF NOT EXISTS user_activity_y2025m06 PARTITION OF user_activity_partitioned
    FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');

-- İndeksler partitionlar için
CREATE INDEX IF NOT EXISTS idx_user_activity_y2025m01_user_id ON user_activity_y2025m01(user_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_y2025m01_created_at ON user_activity_y2025m01(created_at);

CREATE INDEX IF NOT EXISTS idx_user_activity_y2025m02_user_id ON user_activity_y2025m02(user_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_y2025m02_created_at ON user_activity_y2025m02(created_at);

CREATE INDEX IF NOT EXISTS idx_user_activity_y2025m03_user_id ON user_activity_y2025m03(user_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_y2025m03_created_at ON user_activity_y2025m03(created_at);

CREATE INDEX IF NOT EXISTS idx_user_activity_y2025m04_user_id ON user_activity_y2025m04(user_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_y2025m04_created_at ON user_activity_y2025m04(created_at);

CREATE INDEX IF NOT EXISTS idx_user_activity_y2025m05_user_id ON user_activity_y2025m05(user_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_y2025m05_created_at ON user_activity_y2025m05(created_at);

CREATE INDEX IF NOT EXISTS idx_user_activity_y2025m06_user_id ON user_activity_y2025m06(user_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_y2025m06_created_at ON user_activity_y2025m06(created_at);

--------------------------------------------------------------------------------

-- PostgreSQL Tuning parametreleri için önerilen ayarlar (DBA'larla yapılandıralacak)
--------------------------------------------------------------------------------

-- Bu ayarlar postgresql.conf dosyasına eklenmeli:
/*
# Memory Settings
shared_buffers = '4GB'               # %25 of RAM
effective_cache_size = '12GB'        # %75 of RAM
work_mem = '64MB'                    # For complex sorting
maintenance_work_mem = '1GB'         # For vacuum, index creation

# Query Planning
random_page_cost = 1.1               # For SSD storage
effective_io_concurrency = 200       # For SSD storage
default_statistics_target = 100      # Default

# Write-Ahead Log
wal_buffers = '16MB'                  # WAL segment size
synchronous_commit = 'on'             # Protection against power loss

# Checkpointing
checkpoint_timeout = '15min'         # Time between WAL checkpoints
checkpoint_completion_target = 0.9   # Target duration of checkpoint
max_wal_size = '2GB'                 # Maximum size of WAL segments
min_wal_size = '1GB'                 # Minimum size of WAL segments

# Query Execution
max_parallel_workers_per_gather = 4  # Max parallel workers per query
max_parallel_workers = 8             # Max parallel workers for system
*/

--------------------------------------------------------------------------------

-- Veritabanı istatistiklerini güncelleme
--------------------------------------------------------------------------------

-- Bu komutlar DBA tarafından düzenli olarak çalıştırılmalı:
ANALYZE VERBOSE;