# RAG Base Projesi (Lokal Çalışma Odaklı)

Bu proje, çeşitli veri kaynaklarından bilgi alıp bunları lokalde çalışan Elasticsearch'te indeksleyerek ve bir Üretken Dil Modeli (LLM - **lokal veya bulut tabanlı**) kullanarak bu bilgilere dayalı soruları yanıtlayan bir Retrieval-Augmented Generation (RAG) sistemi iskeletidir.

**Not:** Bu proje iskeleti, kullanıcı `Teeksss`'in istekleri doğrultusunda 2025-04-29 07:10:53 UTC itibarıyla güncellenmiştir. Güvenlik, performans, frontend ve eksik özellikler başlıklarındaki **tüm 17 adım** için **placeholder'lar, yorumlar ve yapısal öneriler** eklenmiştir. **Gerçek implementasyon geliştirici tarafından yapılmalıdır.**

## Özellikler
# ... (Önceki özellikler aynı) ...

## Kurulum
1.  **Depoyu Klonla ve Sanal Ortam Oluştur:**
    ```bash
    # ... (önceki) ...
    ```
2.  **Gerekli Kütüphaneleri Kur:**
    ```bash
    # requirements.txt'deki temel kütüphaneleri kur:
    pip install -r requirements.txt
    # İSTEĞE BAĞLI ve SONRAKİ ADIMLAR İÇİN:
    # Yorum satırı kaldırılmış diğer kütüphaneleri (pytest, sqlalchemy, ragas vb.)
    # ihtiyacınız oldukça kurun.
    ```
    *   **(Opsiyonel) `python-magic`:** ...
    *   **Lokal LLM (Transformers) için:** ...
    *   **OCR için:** ...

3.  **Elasticsearch'ü Lokalde Çalıştır (Docker Önerilir):**
    ```bash
    # ... (önceki) ...
    ```
4.  **Veritabanlarını Lokalde Çalıştır (Opsiyonel - Docker Önerilir):**
    *   **PostgreSQL:** (Adım 2 - Güvenli Saklama için önerilir)
        ```bash
        # ... (önceki) ...
        ```
    *   **MySQL:** ...
    *   **MongoDB:** ...

5.  **Lokal LLM Çalıştır (Opsiyonel):** ...

6.  **Yapılandırma Dosyasını (`.env`) Oluştur ve Ayarla:**
    *   `cp .env.example .env`
    *   `.env` dosyasını açın ve **lokal kurulumunuza uygun ayarları** yapın.
    *   **KRİTİK (Adım 1, 3):** Güçlü ve rastgele bir `SECRET_KEY` ayarlayın! (`python -c 'import secrets; print(secrets.token_hex(32))'`)
    *   **KRİTİK (Adım 2):** Kullanıcıları ve token'ları saklamak için bir veritabanı (örn. PostgreSQL) seçtiyseniz, ilgili `POSTGRES_...` veya diğer DB bağlantı bilgilerini doldurun.
    *   **Harici servisler (Adım 5):** Google Drive, Dropbox, Email, Twitter için OAuth veya anahtar bilgilerini ayarlayın.
    *   **Kullanıcılar:** Başlangıçta `backend/auth.py` içindeki sahte kullanıcıları **değiştirin** veya Adım 2'deki veritabanı entegrasyonunu yapın.

## Çalıştırma
# ... (Önceki çalıştırma adımları aynı) ...

## API Endpoints
# ... (Önceki API endpointleri aynı) ...

## Testler

*   **(17) Testler:**
    *   `backend/tests` dizininde temel yapı ve placeholder testler mevcuttur.
    *   **Yapılacak:** `pytest`, `httpx`, `pytest-asyncio`, `unittest.mock` gibi kütüphanelerle kapsamlı testler yazın.
*   Testleri çalıştırmak için (gerekli bağımlılıkları kurduktan sonra):
    ```bash
    pytest backend/tests
    ```

## Proje Yapısı
# ... (Önceki proje yapısı aynı, test dosyaları dahil) ...

## Potansiyel Geliştirmeler ve İyileştirme Alanları (Adımlar 1-17)

**Güvenlik (Kritik Öncelik):**

*   **(1) Frontend Login/JWT:** Frontend'e login formu ve JWT token yönetimi (güvenli saklama, isteklerle gönderme, yenileme) ekleyin. **(Yapılacak - Kritik)**
    *   *Adreslendi (Placeholder):* `frontend/src/contexts/AuthContext.js`, `frontend/src/hooks/useApi.js` placeholder'ları JWT akışını ve saklamayı gösterir. `fetchApi` yerine `useApi` hook'u bileşenlere eklendi.
*   **(2) Veritabanı Entegrasyonu (Kullanıcılar/Tokenlar):** Kullanıcıları ve OAuth token'larını güvenli bir veritabanında (örn. PostgreSQL + SQLAlchemy) saklayın. Token'ları şifreleyin. **(Yapılacak - Kritik)**
    *   *Adreslendi (Placeholder):* `backend/auth.py`, `backend/utils/token_store.py` içine DB kullanımı için placeholder yorumlar ve SQLAlchemy model örnekleri eklendi.
*   **(3) CSRF Koruması:** State değiştiren endpointler için CSRF koruması ekleyin (`fastapi-csrf-protect` vb.). **(Yapılacak)**
    *   *Adreslendi (Placeholder):* `backend/main.py` içine middleware ekleme yeri ve notları eklendi.
*   **(4) Rate Limiting:** API rate limiting uygulayın (`slowapi` vb.). **(Yapılacak)**
    *   *Adreslendi (Placeholder):* `backend/main.py` içine middleware ekleme yeri ve notları eklendi.
*   **(5) Kullanıcı Bazlı OAuth:** Dropbox/Sosyal Medya için kullanıcı bazlı OAuth2 implemente edin. **(Yapılacak)**
    *   *Adreslendi (Placeholder):* `backend/utils/social_media_connector.py` ve `backend/utils/cloud_storage_connector.py` içine OAuth akışı ve token yönetimi için yorumlar eklendi.

**Performans ve Ölçeklenebilirlik:**

*   **(6) Asenkron İşlemler:** Native async kütüphanelere (`asyncpg`, `motor`, `aioimaplib`, `aiohttp` vb.) geçin. **(Yapılacak)**
    *   *Adreslendi (Kısmen):* Senkron I/O işlemleri `asyncio.to_thread` ile sarmalandı. İlgili dosyalara native async kütüphane önerileri eklendi.
*   **(7) Veritabanı Bağlantı Havuzları (Pooling):** SQLAlchemy veya sürücüye özel havuzlama implemente edin. **(Yapılacak)**
    *   *Adreslendi (Notlar):* `backend/utils/database_connector.py` içine notlar eklendi.
*   **(11) Lokal LLM / Elasticsearch Optimizasyonu:** Quantization, `torch.compile`, FlashAttention, ES KNN parametreleri, Profile API gibi teknikleri deneyin. **(Yapılacak)**
    *   *Adreslendi (Notlar):* İlgili kod bölümlerine (`LLMGenerator`, `ElasticsearchRetriever`) notlar eklendi.

**Hata Yönetimi ve Loglama:**

*   **(8) Yapılandırılmış Loglama / Hata İzleme:** JSON loglama (`python-json-logger`) ve hata izleme (Sentry vb.) implemente edin. **(Yapılacak)**
    *   *Adreslendi (Notlar/Temel):* Log formatı iyileştirildi. İlgili dosyalara notlar eklendi.

**Veri İşleme ve Konnektörler:**

*   **(10) Chunking Stratejisi:** Farklı stratejileri (boyut, overlap, splitter türü, metadata) deneyin. **(Yapılacak)**
    *   *Adreslendi (Notlar):* `backend/routers/data_source.py` içine notlar eklendi.
*   **(15) Facebook/LinkedIn Konnektörleri:** OAuth2 akışlarını ve API çağrılarını tamamlayın. **(Yapılacak)**
    *   *Adreslendi (Placeholder):* İlgili backend ve frontend dosyalarına placeholder kodlar ve UI elemanları eklendi.
*   **Diğer:** Daha yetenekli OCR/PDF/Web kütüphanelerini değerlendirin. Veritabanı metin çıkarımını iyileştirin.

**RAG Pipeline İyileştirmeleri:**

*   **Retriever:** Sorgu genişletme, yeniden sıralama (Re-ranking) ekleyin. **(Yapılacak)**
    *   *Adreslendi (Notlar):* `backend/routers/query.py` içine notlar eklendi.
*   **Generator:** Prompt mühendisliği, parametre ayarlama, faithfulness check, uzun context yönetimi implemente edin. **(Yapılacak)**
    *   *Adreslendi (Notlar):* `backend/routers/query.py` (`LLMGenerator`) içine notlar eklendi.

**Frontend:**

*   **(12) State Yönetimi:** Context API, Redux veya Zustand implemente edin. **(Yapılacak)**
    *   *Adreslendi (Placeholder/Yapı):* `frontend/src/contexts/AuthContext.js` placeholder'ı ve `App.js`'de kullanım notları eklendi.
*   **(13) Kullanıcı Deneyimi (UX):** Spinner, Toast/Notification, Arka Plan Görev Takibi UI, Form Validasyonu ekleyin/iyileştirin. **(Yapılacak)**
    *   *Adreslendi (Placeholder/Notlar):* İlgili CSS class'ları, placeholder bileşenler ve yorumlar eklendi.
*   **(14) Kod Kalitesi ve Yapı:** API hook/servisini tamamlayın. Bileşenleri ayırın. TypeScript'e geçişi değerlendirin. **(Yapılacak)**
    *   *Adreslendi (Placeholder/Yapı):* `frontend/src/hooks/useApi.js` placeholder'ı oluşturuldu ve bileşenler bunu kullanacak şekilde güncellendi. İlgili notlar eklendi.

**Diğer:**

*   **(9) Detaylı RBAC:** Veritabanı ile entegre, kapsamlı izin sistemi geliştirin. **(Yapılacak)**
    *   *Adreslendi (Notlar/Temel):* İlgili backend dosyalarına notlar ve temel kontroller eklendi.
*   **(16) Değerlendirme Endpoint'i (`/evaluate`):** RAGAS gibi kütüphanelerle gerçek değerlendirme mantığını implemente edin. **(Yapılacak)**
    *   *Adreslendi (Placeholder/Notlar):* Backend endpoint'ine notlar eklendi.
*   **(17) Testler:** Kapsamlı unit ve integration testleri yazın. **(Yapılacak)**
    *   *Adreslendi (Placeholder/Yapı):* `backend/tests` dizini ve placeholder test dosyaları oluşturuldu.

## Katkıda Bulunma
# ... (Öncekiyle aynı) ...

## Lisans
# ... (Öncekiyle aynı) ...