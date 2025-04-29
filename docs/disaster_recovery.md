# RAG Base Disaster Recovery Planı

## 1. Genel Bakış

Bu belge, RAG Base sisteminin olası bir kesinti veya veri kaybı durumunda hızlı ve etkili bir şekilde kurtarılmasını sağlayacak prosedürleri tanımlar. Amaç, minimum veri kaybı (RPO - Recovery Point Objective) ve minimum kesinti süresi (RTO - Recovery Time Objective) ile sistemin normal işleyişine dönmesini sağlamaktır.

## 2. Kapsam

Bu plan aşağıdaki bileşenleri kapsar:

- Veritabanı (PostgreSQL)
- Dosya depolama (S3, Azure Blob, yerel depolama)
- Uygulama sunucuları
- Önbellek ve mesaj kuyruk sistemleri
- Arama indeksleri (Elasticsearch, Weaviate)
- Konfigürasyon yönetimi

## 3. Recovery Point Objective (RPO) ve Recovery Time Objective (RTO)

| Ortam     | RPO         | RTO         |
|-----------|-------------|-------------|
| Üretim    | ≤ 1 saat    | ≤ 4 saat    |
| Test      | ≤ 24 saat   | ≤ 8 saat    |
| Geliştirme| ≤ 24 saat   | ≤ 24 saat   |

## 4. Felaket Senaryoları

### 4.1. Veritabanı Arızası

**Senaryo**: Veritabanı sunucusunun donanım arızası, veri bozulması veya silinmesi.

**Etki Derecesi**: Kritik (Tüm sistem etkilenir)

**Kurtarma Adımları**:

1. Yedek veritabanı sunucusunu devreye al (failover mekanizması)
2. Otomatik başarısız olursa manuel failover başlat: `scripts/db_failover.sh`
3. Eğer yedek sunucu da kullanılamıyorsa:
   - En son veritabanı yedeğini belirle: `backup_service.get_backup_list()`
   - Yeni bir PostgreSQL örneği başlat
   - Yedekten geri yükleme gerçekleştir: `backup_service.restore_backup(backup_id, restore_db=True)`
4. Veritabanı bağlantı bilgilerini güncelle
5. Uygulama sunucularını yeniden başlat
6. Veritabanının düzgün çalıştığını doğrula: `scripts/health_check.py --component=database`

### 4.2. Uygulama Sunucusu Arızası

**Senaryo**: Bir veya daha fazla uygulama sunucusunun çökmesi.

**Etki Derecesi**: Orta (Kısmi hizmet kesintisi)

**Kurtarma Adımları**:

1. Load balancer'dan arızalı sunucuları çıkar
2. Yeni uygulama sunucuları başlat
3. Konfigürasyon yönetim sisteminden en son ayarları uygula
4. Uygulama sunucularının düzgün çalıştığını doğrula
5. Yeni sunucuları load balancer'a ekle

### 4.3. Veri Depolama Arızası

**Senaryo**: Dosya depolama sisteminin erişilemez olması veya veri kaybı.

**Etki Derecesi**: Yüksek (Belgelere erişilemez)

**Kurtarma Adımları**:

1. Yedek depolama sistemini devreye al
2. En son depolama yedeğini belirle
3. Yedekten dosyaları geri yükle: `backup_service.restore_backup(backup_id, restore_storage=True)`
4. Depolama bağlantı bilgilerini güncelle
5. Depolama sisteminin düzgün çalıştığını doğrula
6. Eksik dosyaları tedarik etmek için müşterilerle iletişime geç (gerekirse)

### 4.4. Arama İndeksi Arızası

**Senaryo**: Elasticsearch veya Weaviate indekslerinin bozulması veya kaybı.

**Etki Derecesi**: Orta (Arama fonksiyonu çalışmaz)

**Kurtarma Adımları**:

1. Yedek arama sunucusunu devreye al (varsa)
2. Veya yeni bir arama sunucusu başlat
3. Veritabanından indeksi yeniden oluştur: `scripts/rebuild_index.py`
4. İndeksleme işleminin tamamlanmasını bekle
5. Arama hizmetinin düzgün çalıştığını doğrula

### 4.5. Tüm Ortamın Kaybı

**Senaryo**: Doğal afet veya büyük altyapı arızası sonucu tüm ortamın kaybı.

**Etki Derecesi**: Kritik (Tam sistem kaybı)

**Kurtarma Adımları**:

1. Alternatif bölgede yeni bir altyapı hazırla
2. Tüm sunucuları (veritabanı, uygulama, depolama, arama) başlat
3. En son yedekleri tespit et
4. Tüm bileşenleri yedeklerden geri yükle
5. DNS ve load balancer yapılandırmalarını güncelle
6. Sistemi adım adım devreye al ve her bileşenin düzgün çalıştığını doğrula

## 5. Otomatik Kurtarma Mekanizmaları

RAG Base, çeşitli otomatik kurtarma mekanizmaları kullanır:

- **Veritabanı Replikasyonu**: Streaming replikasyon ile sıcak yedekler
- **Kubernetes Self-Healing**: Pod Health Checks ve otomatik yeniden başlatma
- **Circuit Breaker Pattern**: Cascade arızaları önlemek için
- **Düzenli Sağlık Kontrolleri**: Tüm bileşenler için `/health` endpoint'leri

## 6. Felaket Kurtarma Testi

Felaket kurtarma planı düzenli olarak test edilmeli ve belgelenmelidir:

| Test Türü              | Sıklık  | Son Test Tarihi | Sonuç  |
|------------------------|---------|-----------------|--------|
| Veritabanı Geri Yükleme| 3 ayda bir | 2025-03-15    | Başarılı |
| Failover Testi         | Ayda bir  | 2025-04-02    | Başarılı |
| Tam DR Testi           | 6 ayda bir | 2025-01-20    | Başarılı |

## 7. İletişim Planı

Bir felaket durumunda aşağıdaki kişiler bilgilendirilmelidir:

| Rol                    | Kişi         | İletişim Bilgileri     | Yedek Kişi    |
|------------------------|--------------|------------------------|---------------|
| Sistem Yöneticisi      | Ahmet Yılmaz | ahmet@example.com      | Ayşe Demir    |
| Veritabanı Yöneticisi  | Mehmet Kaya  | mehmet@example.com     | Ali Öztürk    |
| Geliştirme Ekibi Lead  | Zeynep Arslan| zeynep@example.com     | Can Güneş     |
| İş Sürekliliği Müdürü  | Deniz Yıldız | deniz@example.com      | Selin Şahin   |

## 8. Dokümantasyon ve Günlük Tutma

Tüm kurtarma işlemleri detaylı olarak belgelenmelidir. Her kurtarma olayı için şunlar kaydedilmelidir:

- Olayın tarihi ve saati
- Olayın türü ve etkilenen sistemler
- Uygulanan kurtarma adımları
- Kurtarma süresi
- Başarı/başarısızlık durumu ve tespit edilen sorunlar
- İyileştirme önerileri

## 9. Sürekli İyileştirme

Felaket kurtarma planı, sistem mimarisi değiştikçe veya yeni bileşenler eklendikçe güncellenmelidir. Planın etkinliğini artırmak için:

- Her kurtarma işlemi sonrasında sonuçları analiz edin
- Düzenli olarak DR alıştırmaları yapın
- Teknoloji ve araç güncellemelerini takip edin
- RTO ve RPO hedeflerinizi periyodik olarak gözden geçirin

## 10. Referanslar ve Kaynaklar

- RAG Base Yedekleme Servisi Dokümantasyonu
- Kubernetes Deployment Yapılandırmaları
- Veritabanı Yönetim Prosedürleri
- Cloud Provider DR Kaynakları

---

**Son Güncelleme**: 2025-04-29  
**Onaylayan**: Zeynep Arslan, Geliştirme Ekibi Lead