# RAG Base Webhook Entegrasyon Kılavuzu

Bu belge, RAG Base platformunda gerçekleşen olaylar hakkında bilgi almak için webhook entegrasyonu kurma sürecini açıklar.

## Genel Bakış

Webhooklar, platformunuzdaki belirli olaylar gerçekleştiğinde harici sistemlere otomatik bildirimler göndermenizi sağlar. Bu, üçüncü taraf sistemlerle entegrasyon kurmanıza ve gerçek zamanlı veri akışını yönetmenize yardımcı olur.

## Webhook Yapılandırması

### 1. Webhook Uç Noktası Ekleme

RAG Base'de yeni bir webhook yapılandırmak için:

1. Yönetici paneline gidin: `https://your-domain.com/admin/settings/webhooks`
2. "Yeni Webhook Ekle" düğmesine tıklayın
3. Aşağıdaki alanları doldurun:
   - **Webhook URL'si**: Bildirimler gönderilecek HTTP uç noktası
   - **Etkin Olaylar**: Bildirim almak istediğiniz olaylar
   - **Açıklama**: İç kullanım için tanımlayıcı bir ad
   - **Gizli Anahtar**: İmzalama için kullanılacak gizli anahtar (isteğe bağlı)
   - **Aktif**: Webhook'u etkinleştirmek için bu seçeneği işaretleyin

### 2. Olay Türleri

Aşağıdaki olay türleri için bildirim alabilirsiniz:

| Olay Türü | Açıklama |
|-----------|----------|
| `document_uploaded` | Yeni bir doküman yüklendiğinde |
| `document_processed` | Doküman işleme tamamlandığında |
| `document_updated` | Bir doküman güncellendiğinde |
| `document_shared` | Bir doküman paylaşıldığında |
| `document_deleted` | Bir doküman silindiğinde |
| `security_alert` | Güvenlik uyarısı tespit edildiğinde |
| `user_registered` | Yeni bir kullanıcı kaydolduğunda |

## Webhook İstekleri

### İstek Formatı

RAG Base, olaylar gerçekleştiğinde aşağıdaki formatta POST istekleri gönderir:

```json
{
  "event_type": "document_uploaded",
  "timestamp": "2025-04-29T13:04:50.123Z",
  "webhook_id": "whk_abcdef123456",
  "delivery_attempt": 1,
  "data": {
    // Olay türüne özgü veriler
  }
}