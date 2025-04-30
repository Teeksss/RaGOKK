# document_processor.py dosyasına eklenecek kod

# document_processor.py import kısmına eklenecek
from .document_summarizer import DocumentSummarizer

class DocumentProcessorService:
    """
    Belge işleme ve metin çıkarma servisi
    """
    
    def __init__(self):
        """Servis başlangıç ayarları"""
        # ... [mevcut init kodu] ...
        
        # Belge özetleyici
        self.document_summarizer = DocumentSummarizer()
    
    # ... [mevcut metodlar] ...
    
    async def process_document(self, 
                             file_path: str, 
                             title: str,
                             user_id: str,
                             document_id: str,
                             tags: List[str] = None,
                             apply_ocr: bool = False,
                             segmentation_strategy: str = 'paragraph',
                             auto_summarize: bool = True) -> Dict[str, Any]:  # auto_summarize parametresi eklendi
        """
        Belgeyi işler, metin çıkarır ve segmentlere ayırır
        
        Args:
            file_path: Dosya yolu
            title: Belge başlığı
            user_id: Yükleyen kullanıcı ID'si
            document_id: Belge ID'si
            tags: Belge etiketleri
            apply_ocr: OCR uygulansın mı?
            segmentation_strategy: Segmentasyon stratejisi ('paragraph', 'sentence', 'heading', 'chunk')
            auto_summarize: Otomatik özet oluşturulsun mu?
            
        Returns:
            Dict[str, Any]: İşlenmiş belge bilgisi ve segmentleri
        """
        # ... [mevcut kod] ...
        
        # İşlem sonucunu döndür
        result = {
            "title": title,
            "content": content,
            "file_type": file_type,
            "file_name": file_name,
            "page_count": page_count,
            "segment_count": len(all_segments),
            "segments": all_segments,
            "segmentation_strategy": segmentation_strategy,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "auto_summarize": auto_summarize
        }
        
        # Otomatik özetleme isteniyorsa arka planda başlat (işlemi yavaşlatmaması için)
        if auto_summarize:
            # Burada asyncio.create_task kullanmak yerine veritabanı bağlantısı sonrası yap
            # çünkü veritabanı bağlantısı farklı iş parçacıklarında kullanılamayabilir
            result["summary_scheduled"] = True
        
        return result