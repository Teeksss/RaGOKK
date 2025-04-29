# RAG Base Veritabanı Ölçeklendirme Stratejisi

**Tarih:** 2025-04-29  
**Versiyon:** 1.0

## 1. Genel Bakış

Bu belge, RAG Base uygulamasının veritabanı ölçeklendirme stratejisini tanımlar. Sistemin büyümesi ve yük artışı ile beraber veritabanı performansını ve erişilebilirliğini korumak için uygulanan stratejileri içerir.

## 2. Mevcut Durum

- **Veritabanı**: PostgreSQL 14
- **Mevcut Boyut**: ~300GB
- **Mevcut Tablo Sayısı**: 28
- **En Büyük Tablolar**: 
  - `documents` (~150GB)
  - `document_versions` (~70GB)
  - `user_activity` (~50GB)
  - `search_history` (~20GB)
- **Günlük İşlem Hacmi**:
  - ~10,000 yeni belge
  - ~50,000 arama işlemi
  - ~100,000 kullanıcı aktivitesi

## 3. Ölçeklendirme Zorlukları

1. **Veri Boyutu Artışı**: Belge sayısı ve boyutu lineer olmayan şekilde artıyor
2. **Eşzamanlı Kullanıcı Sayısı**: Yüksek eşzamanlı erişim ve sorgulama
3. **Karmaşık Sorgular**: Tam metin aramaları ve çok tablodan birleştirmeler
4. **Yüksek Yazma Yoğunluğu**: Belge yüklemeleri ve kullanıcı aktivite kayıtları
5. **Coğrafi Dağıtım**: Farklı bölgelerdeki kullanıcılara düşük gecikme süresi

## 4. Ölçeklendirme Stratejileri

### 4.1 Dikey Ölçeklendirme (Vertical Scaling)

**Kısa Vadeli Strateji**:
- Mevcut tek PostgreSQL sunucusunu daha güçlü donanımla yükseltmek
- CPU, RAM ve disk I/O performansını artırmak

**Parametreler**:
- `shared_buffers`: RAM'in %25'i (minimum 8GB)
- `work_mem`: Belge aramaları için optimize (128MB)
- `maintenance_work_mem`: Verimli indeks oluşturma için (2GB)
- `effective_cache_size`: RAM'in %75'i
- `random_page_cost`: SSD depolama için 1.1
- `max_parallel_workers_per_gather`: CPU çekirdek sayısına göre (8-16)

**Avantajlar**:
- Uygulama mimarisinde değişiklik gerektirmez
- Dağıtım ve yönetim basitliği

**Dezavantajlar**:
- Belirli bir noktadan sonra ekonomik olmayan maliyet artışı
- Tek hata noktası (SPOF) riski
- Gecikme süresi optimizasyonlarında sınırlı iyileşme

### 4.2 Yatay Ölçeklendirme (Horizontal Scaling)

#### 4.2.1 Read Replicas (Okuma Replikaları)

**Orta Vadeli Strateji**:
- Ana yazma sunucusu + çoklu okuma replikaları
- Akıllı yük dengeleme ile okuma işlemlerinin dağıtılması
- Coğrafi olarak dağıtılmış replikalar

**Yapılandırma**:
- Streaming replication ile senkronizasyon
- `hot_standby = on`
- `hot_standby_feedback = on` 
- `max_standby_streaming_delay = 30s`

**İş Yükü Dağıtımı**:
- Tüm yazma işlemleri master sunucuya
- Rapor sorguları ve arama işlemleri replikalara
- Kullanıcının coğrafi konumuna en yakın replika seçimi

#### 4.2.2 Database Sharding (Veritabanı Parçalama)

**Uzun Vadeli Strateji**:
- Veri kümesini mantıksal olarak parçalara bölmek
- Her bir parça ayrı veritabanı sunucusunda barındırılır

**Sharding Anahtar Stratejileri**:
1. **Kurum/Organizasyon Bazlı**:
   - Her müşteri/organizasyon ayrı veritabanında
   - Multi-tenant mimari için uygun
   - `organization_id` sharding anahtarı olarak kullanılır

2. **Belge Türü Bazlı**:
   - Belge türlerine göre farklı sunuculara dağıtım
   - Belge türleri arasında çapraz sorgular sınırlı
   - `document_type` sharding anahtarı olarak kullanılır

3. **Hash Bazlı**:
   - Document ID üzerinden hash fonksiyonu ile parçalama
   - Dengeli veri dağılımı sağlar
   - ID aralık genişlemesi sorunu yaşanmaz

**Sharding Mimarisi**:
- Citusdb PostgreSQL uzantısı kullanımı
- Merkezi koordinasyon ve sorgu planlama bileşeni
- Dağıtık sorgu yürütme

### 4.3 Partition Tables (Tablo Bölümleme)

**Kısa-Orta Vadeli Strateji**:
- Büyük tablolarda verileri mantıksal parçalara bölme
- Fiziksel olarak farklı tablolarda saklama
- Aynı veritabanı sunucusu içinde gerçekleşir

**Bölümleme Stratejileri**:
1. **Zaman Bazlı Bölümleme**:
   - `user_activity`: Aylık bölümler (`RANGE` tipi)
   - `search_history`: Haftalık bölümler (`RANGE` tipi)
   - `document_versions`: Üç aylık bölümler (`RANGE` tipi)

2. **Hash Bazlı Bölümleme**:
   - `documents`: Document ID hash değerine göre 16 bölüm (`HASH` tipi)

3. **Liste Bazlı Bölümleme**:
   - `documents`: Belge türüne göre bölümler (`LIST` tipi)

**Örnek Uygulama** (Zaman Bazlı Bölümleme):
```sql
-- Ana tablo tanımı
CREATE TABLE user_activity (
    id BIGSERIAL,
    user_id UUID NOT NULL,
    activity_type VARCHAR(50) NOT NULL,
    activity_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY(id, created_at)
) PARTITION BY RANGE (created_at);

-- Aylık bölümler
CREATE TABLE user_activity_y2025m01 
PARTITION OF user_activity
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE user_activity_y2025m02 
PARTITION OF user_activity
FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');