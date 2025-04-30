# Last reviewed: 2025-04-30 06:23:58 UTC (User: Teeksss)
from typing import List, Dict, Any, Optional, Tuple
import re
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
import logging
from datetime import datetime, timezone

# NLTK kaynakları indir
try:
    nltk.download('punkt', quiet=True)
except Exception as e:
    logging.warning(f"NLTK resource download error: {str(e)}")

logger = logging.getLogger(__name__)

class DocumentSegmenter:
    """
    Belge segmentasyonu için gelişmiş hizmet sınıfı.
    Belgeleri cümle, paragraf veya başlık bazında segmentlere ayırır
    ve her segment için metadata oluşturur.
    """
    
    def __init__(self, 
                min_segment_size: int = 50,  # Minimum karakter
                max_segment_size: int = 1000,  # Maksimum karakter
                overlap: int = 20,  # % cinsinden örtüşme
                separator_patterns: Optional[List[str]] = None):
        """
        Args:
            min_segment_size: Minimum segment boyutu (karakter)
            max_segment_size: Maksimum segment boyutu (karakter)
            overlap: Segmentler arası örtüşme yüzdesi
            separator_patterns: Özel ayırıcı regex desenleri
        """
        self.min_segment_size = min_segment_size
        self.max_segment_size = max_segment_size
        self.overlap = overlap / 100.0  # Yüzdeyi ondalık değere dönüştür
        
        # Varsayılan ayırıcı desenler
        self.separator_patterns = separator_patterns or [
            r'\n\s*\n+',  # Boş satırlar (paragraf)
            r'(?<=\.)\s+(?=[A-Z])',  # Nokta ve büyük harf (cümle)
            r'(?<=\n)#{1,6}\s+.+\n',  # Markdown başlıkları
            r'<h[1-6]>.*?</h[1-6]>',  # HTML başlıkları
        ]
        
    def segment_text(self, 
                    text: str, 
                    metadata: Dict[str, Any],
                    strategy: str = 'paragraph') -> List[Dict[str, Any]]:
        """
        Metni belirtilen stratejiye göre segmentlere ayırır
        
        Args:
            text: Segmentlere ayrılacak metin
            metadata: Segment metadata'larına eklenecek bilgiler
            strategy: Segmentasyon stratejisi ('paragraph', 'sentence', 'heading', 'chunk')
            
        Returns:
            List[Dict[str, Any]]: Segment ve metadata'ları içeren liste
        """
        if not text:
            return []
        
        segments = []
        
        try:
            # Strateji seçimi
            if strategy == 'paragraph':
                raw_segments = self._split_by_paragraphs(text)
            elif strategy == 'sentence':
                raw_segments = self._split_by_sentences(text)
            elif strategy == 'heading':
                raw_segments = self._split_by_headings(text)
            elif strategy == 'chunk':
                raw_segments = self._split_by_chunk_size(text)
            else:
                logger.warning(f"Unknown segmentation strategy: {strategy}, falling back to paragraph")
                raw_segments = self._split_by_paragraphs(text)
                
            # Her segment için metadata oluştur
            for i, segment_text in enumerate(raw_segments):
                if not segment_text.strip():
                    continue
                    
                segment = {
                    "content": segment_text.strip(),
                    "metadata": {
                        # Genel metadata
                        "segment_id": f"{metadata.get('document_id', 'unknown')}_{i}",
                        "segment_index": i,
                        "segment_type": strategy,
                        "char_count": len(segment_text),
                        "word_count": len(word_tokenize(segment_text.strip())),
                        "segment_timestamp": datetime.now(timezone.utc).isoformat(),
                        
                        # Belge metadata'sını ekle
                        "source_filename": metadata.get("source_filename", ""),
                        "page_number": metadata.get("page_number"),
                        "section_title": self._extract_section_title(segment_text, raw_segments, i),
                        "upload_user_id": metadata.get("upload_user_id", ""),
                        "document_tags": metadata.get("document_tags", []),
                        "document_id": metadata.get("document_id", ""),
                        "document_title": metadata.get("document_title", ""),
                    }
                }
                segments.append(segment)
                
            return segments
            
        except Exception as e:
            logger.error(f"Error segmenting text: {str(e)}")
            # Hata durumunda tek bir segment olarak döndür
            return [{
                "content": text,
                "metadata": {
                    **metadata,
                    "segment_id": f"{metadata.get('document_id', 'unknown')}_0",
                    "segment_index": 0,
                    "segment_type": "full_document",
                    "segmentation_error": str(e)
                }
            }]
    
    def _split_by_paragraphs(self, text: str) -> List[str]:
        """Metni paragraf bazında böler"""
        # Paragraf ayırıcı regex
        paragraph_separator = re.compile(r'\n\s*\n+')
        paragraphs = paragraph_separator.split(text)
        
        # Boş satırları kaldır ve trim
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _split_by_sentences(self, text: str) -> List[str]:
        """Metni cümle bazında böler"""
        # NLTK sentenece tokenizer kullan
        sentences = sent_tokenize(text)
        
        # Büyük segmentler için cümleleri birleştir
        result = []
        current_segment = ""
        
        for sentence in sentences:
            if len(current_segment) + len(sentence) < self.max_segment_size:
                current_segment += " " + sentence if current_segment else sentence
            else:
                if current_segment:
                    result.append(current_segment)
                current_segment = sentence
                
        # Son segmenti ekle
        if current_segment:
            result.append(current_segment)
            
        return result
    
    def _split_by_headings(self, text: str) -> List[str]:
        """Metni başlıklara göre böler (Markdown veya HTML)"""
        # Markdown başlıkları için regex
        md_heading_pattern = re.compile(r'(?<=\n)#{1,6}\s+.+\n')
        # HTML başlıkları için regex
        html_heading_pattern = re.compile(r'<h[1-6]>.*?</h[1-6]>')
        
        # Tüm başlık eşleşmelerini bul
        md_matches = list(md_heading_pattern.finditer(text))
        html_matches = list(html_heading_pattern.finditer(text))
        
        # Tüm eşleşmeleri başlangıç konumuna göre sırala
        all_matches = sorted(md_matches + html_matches, key=lambda m: m.start())
        
        if not all_matches:
            # Başlık bulunamazsa paragraf olarak böl
            return self._split_by_paragraphs(text)
        
        segments = []
        last_end = 0
        
        # Her başlığı ve sonraki içeriği segment olarak al
        for i, match in enumerate(all_matches):
            if i > 0:
                # Önceki başlıktan bu başlığa kadar olan içerik
                segment = text[last_end:match.start()]
                if segment.strip():
                    segments.append(segment)
            
            # Başlığın kendisini ekle
            heading = match.group(0)
            if heading.strip():
                segments.append(heading)
                
            last_end = match.end()
        
        # Son segment
        if last_end < len(text):
            segment = text[last_end:]
            if segment.strip():
                segments.append(segment)
                
        return segments
    
    def _split_by_chunk_size(self, text: str) -> List[str]:
        """Metni sabit boyutlu parçalara böler, örtüşmeye izin verir"""
        # Boş metnin kontrolü
        if not text.strip():
            return []
        
        chunks = []
        overlap_size = int(self.max_segment_size * self.overlap)
        
        # Metni maksimum boyuta göre parçala
        for i in range(0, len(text), self.max_segment_size - overlap_size):
            # Segment başlangıç ve bitiş
            chunk_start = i
            chunk_end = min(i + self.max_segment_size, len(text))
            
            # Segment metnini al
            chunk = text[chunk_start:chunk_end]
            
            # Minimum boyut kontrolü
            if len(chunk) >= self.min_segment_size:
                chunks.append(chunk)
                
        return chunks
    
    def _extract_section_title(self, segment_text: str, all_segments: List[str], index: int) -> Optional[str]:
        """Segment için bölüm başlığını çıkarır"""
        # Segment başlık içeriyor mu kontrol et
        heading_patterns = [
            r'^#{1,6}\s+(.+)$',  # Markdown başlık
            r'^<h[1-6]>(.*?)</h[1-6]>$',  # HTML başlık
        ]
        
        # Segmentin kendisi başlık mı?
        for pattern in heading_patterns:
            match = re.search(pattern, segment_text.strip(), re.MULTILINE)
            if match:
                return match.group(1).strip()
        
        # Önceki segmentlerde başlık ara
        if index > 0:
            for i in range(index-1, -1, -1):
                prev_segment = all_segments[i].strip()
                for pattern in heading_patterns:
                    match = re.search(pattern, prev_segment, re.MULTILINE)
                    if match:
                        return match.group(1).strip()
        
        return None