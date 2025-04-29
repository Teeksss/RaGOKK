# RAG Base API Referansı

## Genel Bilgiler

RAG Base API'si, doküman yönetimi, dil işleme ve vektör arama özellikleri için RESTful bir arayüz sağlar. Tüm endpoint'ler JSON formatını destekler ve kimlik doğrulama gerektirir.

### Kimlik Doğrulama

API isteklerinde kimlik doğrulama için JWT token kullanılır. Token, isteklerin `Authorization` başlığında "Bearer" önekiyle birlikte gönderilmelidir:
