# RAG Base API Dokümantasyonu

**Son Güncelleme Tarihi:** 2025-04-29

## Genel Bilgiler

Bu dokümantasyon, RAG Base sisteminin API arayüzlerini ve kullanımlarını açıklamaktadır. Tüm API çağrıları JWT kimlik doğrulama gerektirmektedir.

### Kimlik Doğrulama

API isteklerinde kimlik doğrulama için JWT token gereklidir. Token, `Authorization` başlığında "Bearer" önekiyle birlikte gönderilmelidir:
