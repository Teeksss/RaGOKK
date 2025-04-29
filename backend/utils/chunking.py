# Last reviewed: 2025-04-29 08:46:01 UTC (User: Teeksssgelişmiş)
from typing import List, Dict, Any, Optional, Callable
import re
from enum import Enum
import hashlib
import asyncio
from transformers import AutoTokenizer
import numpy as np

from .config import (
    CHUNK_STRATEGY, CHUNK_SIZE, CHUNK_OVERLAP,
    SEMANTIC_MODEL, LLM_MAX_TOKENS
)
from .logger import get_logger
from .llm_manager import llm_manager

logger = get_logger(__name__)

class ChunkStrategy(str, Enum):
    RECURSIVE = "recursive"
    TOKEN = "token"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    HYBRID = "hybrid"

class ChunkingProcessor:
    """Belgeleri yüksek kaliteli parçalara ayırma işlemcisi"""
    
    def __init__(
        self,
        strategy: ChunkStrategy = CHUNK_STRATEGY,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP
    ):
        self.strategy = ChunkStrategy(strategy)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.tokenizer = None
        logger.info(f"Chunking Processor başlatıldı: {self.strategy} (boyut: {self.chunk_size}, örtüşme: {self.chunk_overlap})")
    
    def _load_tokenizer(self):
        """Tokenizer yükler (lazy)"""
        if self.tokenizer is None:
            try:
                self.tokenizer = AutoTokenizer.from_pretrained("gpt2")
                logger.info(f"Chunking tokenizer başarıyla yüklendi")
            except Exception as e:
                logger.error(f"Tokenizer yükleme hatası: {e}")
                # Fallback olarak basit boşluk tokenizer
                self.tokenizer = lambda x: x.split()
    
    def _generate_chunk_id(self, text: str, index: int) -> str:
        """Chunk için benzersiz ID oluşturur"""
        chunk_hash = hashlib.md5(text.encode()).hexdigest()
        return f"chunk_{index}_{chunk_hash[:8]}"
    
    async def process(self, text: str, metadata: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Metni seçilen stratejiye göre parçalara ayırır"""
        if not text:
            return []
            
        if self.strategy == ChunkStrategy.RECURSIVE:
            chunks = await self._chunk_recursive(text)
        elif self.strategy == ChunkStrategy.TOKEN:
            chunks = await self._chunk_by_tokens(text)
        elif self.strategy == ChunkStrategy.SENTENCE:
            chunks = await self._chunk_by_sentence(text)
        elif self.strategy == ChunkStrategy.PARAGRAPH:
            chunks = await self._chunk_by_paragraph(text)
        elif self.strategy == ChunkStrategy.HYBRID:
            chunks = await self._chunk_hybrid(text)
        else:
            # Varsayılan olarak recursive chunking kullan
            chunks = await self._chunk_recursive(text)
        
        # Parçaları hazırla
        result_chunks = []
        for i, chunk_text in enumerate(chunks):
            # Chunk ID oluştur
            chunk_id = self._generate_chunk_id(chunk_text, i)
            
            # Chunk nesnesini hazırla
            chunk_obj = {
                "id": chunk_id,
                "text": chunk_text,
                "index": i,
                "content_length": len(chunk_text)
            }
            
            # Metadata ekle (varsa)
            if metadata:
                chunk_obj["metadata"] = metadata.copy()
                chunk_obj["metadata"]["chunk_index"] = i
                chunk_obj["metadata"]["chunk_total"] = len(chunks)
            
            result_chunks.append(chunk_obj)
        
        return result_chunks
    
    async def _chunk_recursive(self, text: str) -> List[str]:
        """Metni özyinelemeli olarak parçalara ayırır"""
        # Parse metni paragraf -> cümle -> kelime seviyesinde
        chunks = []
        
        # Önce paragrafları ayır
        paragraphs = re.split(r'\n\s*\n', text)
        
        current_chunk = []
        current_size = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            paragraph_size = len(paragraph)
            
            # Paragraf tek başına chunk_size'dan büyükse, cümlelere böl
            if paragraph_size > self.chunk_size:
                # Cümlelere böl
                sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                        
                    sentence_size = len(sentence)
                    
                    # Cümle tek başına chunk_size'dan büyükse, kelime kelime ekle
                    if sentence_size > self.chunk_size:
                        words = sentence.split()
                        current_sentence = []
                        current_sentence_size = 0
                        
                        for word in words:
                            word_size = len(word) + 1  # +1 for space
                            if current_sentence_size + word_size <= self.chunk_size:
                                current_sentence.append(word)
                                current_sentence_size += word_size
                            else:
                                # Mevcut cümleyi mevcut parçaya ekle
                                if current_sentence:
                                    sentence_text = " ".join(current_sentence)
                                    if current_size + len(sentence_text) <= self.chunk_size:
                                        current_chunk.append(sentence_text)
                                        current_size += len(sentence_text) + 1  # +1 for space
                                    else:
                                        # Mevcut parçayı tamamla
                                        if current_chunk:
                                            chunks.append(" ".join(current_chunk))
                                        # Yeni parça başlat
                                        current_chunk = [sentence_text]
                                        current_size = len(sentence_text)
                                
                                # Yeni cümle başlat
                                current_sentence = [word]
                                current_sentence_size = word_size
                        
                        # Kalan kelimeleri işle
                        if current_sentence:
                            sentence_text = " ".join(current_sentence)
                            if current_size + len(sentence_text) <= self.chunk_size:
                                current_chunk.append(sentence_text)
                                current_size += len(sentence_text) + 1
                            else:
                                # Mevcut parçayı tamamla
                                if current_chunk:
                                    chunks.append(" ".join(current_chunk))
                                # Yeni parça başlat
                                current_chunk = [sentence_text]
                                current_size = len(sentence_text)
                    else:
                        # Cümle chunk_size'dan küçükse
                        if current_size + sentence_size <= self.chunk_size:
                            current_chunk.append(sentence)
                            current_size += sentence_size + 1
                        else:
                            # Mevcut parçayı tamamla
                            if current_chunk:
                                chunks.append(" ".join(current_chunk))
                            # Yeni parça başlat
                            current_chunk = [sentence]
                            current_size = sentence_size
            else:
                # Paragraf chunk_size'dan küçükse
                if current_size + paragraph_size <= self.chunk_size:
                    current_chunk.append(paragraph)
                    current_size += paragraph_size + 1
                else:
                    # Mevcut parçayı tamamla
                    if current_chunk:
                        chunks.append(" ".join(current_chunk))
                    # Yeni parça başlat
                    current_chunk = [paragraph]
                    current_size = paragraph_size
        
        # Son parçayı ekle
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        # Parçalar arası örtüşmeyi sağla
        result_chunks = []
        prev_chunk_content = ""
        
        for i, chunk in enumerate(chunks):
            if i > 0 and self.chunk_overlap > 0:
                # Önceki chunk'ın son kısmını al
                overlap_content = prev_chunk_content[-self.chunk_overlap:]
                # Mevcut chunk'ın başına ekle
                chunk = overlap_content + " " + chunk
            
            result_chunks.append(chunk)
            prev_chunk_content = chunk
        
        return result_chunks
    
    async def _chunk_by_tokens(self, text: str) -> List[str]:
        """Metni token sayısına göre parçalara ayırır"""
        self._load_tokenizer()
        
        tokens = self.tokenizer.encode(text)
        chunks = []
        
        start_idx = 0
        while start_idx < len(tokens):
            end_idx = min(start_idx + self.chunk_size, len(tokens))
            chunk_tokens = tokens[start_idx:end_idx]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            chunks.append(chunk_text)
            
            # Sonraki parçanın başlangıcı (örtüşmeyi hesapla)
            start_idx = end_idx - self.chunk_overlap
        
        return chunks
    
    async def _chunk_by_sentence(self, text: str) -> List[str]:
        """Metni cümlelere göre parçalara ayırır"""
        # Cümlelere böl
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            sentence_size = len(sentence)
            
            # Cümle çok uzunsa, kelime kelime ekle
            if sentence_size > self.chunk_size:
                words = sentence.split()
                current_sentence = []
                current_sentence_size = 0
                
                for word in words:
                    word_size = len(word) + 1  # +1 for space
                    if current_sentence_size + word_size <= self.chunk_size:
                        current_sentence.append(word)
                        current_sentence_size += word_size
                    else:
                        # Mevcut cümleyi mevcut parçaya ekle
                        if current_sentence:
                            sentence_text = " ".join(current_sentence)
                            if current_size + len(sentence_text) <= self.chunk_size:
                                current_chunk.append(sentence_text)
                                current_size += len(sentence_text) + 1
                            else:
                                # Mevcut parçayı tamamla
                                if current_chunk:
                                    chunks.append(" ".join(current_chunk))
                                # Yeni parça başlat
                                current_chunk = [sentence_text]
                                current_size = len(sentence_text)
                        
                        # Yeni cümle başlat
                        current_sentence = [word]
                        current_sentence_size = word_size
                
                # Kalan kelimeleri işle
                if current_sentence:
                    sentence_text = " ".join(current_sentence)
                    if current_size + len(sentence_text) <= self.chunk_size:
                        current_chunk.append(sentence_text)
                        current_size += len(sentence_text) + 1
                    else:
                        # Mevcut parçayı tamamla
                        if current_chunk:
                            chunks.append(" ".join(current_chunk))
                        # Yeni parça başlat
                        current_chunk = [sentence_text]
                        current_size = len(sentence_text)
            else:
                # Cümle chunk_size'dan küçükse
                if current_size + sentence_size <= self.chunk_size:
                    current_chunk.append(sentence)
                    current_size += sentence_size + 1
                else:
                    # Mevcut parçayı tamamla
                    if current_chunk:
                        chunks.append(" ".join(current_chunk))
                    # Yeni parça başlat
                    current_chunk = [sentence]
                    current_size = sentence_size
        
        # Son parçayı ekle
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    async def _chunk_by_paragraph(self, text: str) -> List[str]:
        """Metni paragraflara göre parçalara ayırır"""
        # Paragrafları böl (boş satırlar)
        paragraphs = re.split(r'\n\s*\n', text)
        chunks = []
        
        current_chunk = []
        current_size = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            paragraph_size = len(paragraph)
            
            # Paragraf çok uzunsa alt paragraflara böl (cümle grupları)
            if paragraph_size > self.chunk_size:
                # Paragrafı cümlelere ayırarak işle
                sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                current_sub_paragraph = []
                current_sub_size = 0
                
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                        
                    sentence_size = len(sentence)
                    
                    # Alt paragraf büyüklüğünü kontrol et
                    if current_sub_size + sentence_size <= self.chunk_size:
                        current_sub_paragraph.append(sentence)
                        current_sub_size += sentence_size + 1  # +1 for space
                    else:
                        # Alt paragrafı ekle
                        if current_sub_paragraph:
                            sub_para_text = " ".join(current_sub_paragraph)
                            
                            # Ana chunk'a eklenebilir mi?
                            if current_size + len(sub_para_text) <= self.chunk_size:
                                current_chunk.append(sub_para_text)
                                current_size += len(sub_para_text) + 2  # +2 for paragraph break
                            else:
                                # Mevcut chunk'ı tamamla
                                if current_chunk:
                                    chunks.append("\n\n".join(current_chunk))
                                # Yeni chunk başlat
                                current_chunk = [sub_para_text]
                                current_size = len(sub_para_text)
                        
                        # Yeni alt paragraf başlat
                        current_sub_paragraph = [sentence]
                        current_sub_size = sentence_size
                
                # Kalan alt paragrafı işle
                if current_sub_paragraph:
                    sub_para_text = " ".join(current_sub_paragraph)
                    
                    # Ana chunk'a eklenebilir mi?
                    if current_size + len(sub_para_text) <= self.chunk_size:
                        current_chunk.append(sub_para_text)
                        current_size += len(sub_para_text) + 2
                    else:
                        # Mevcut chunk'ı tamamla
                        if current_chunk:
                            chunks.append("\n\n".join(current_chunk))
                        # Yeni chunk başlat
                        current_chunk = [sub_para_text]
                        current_size = len(sub_para_text)
            else:
                # Paragraf chunk_size'dan küçükse
                if current_size + paragraph_size <= self.chunk_size:
                    current_chunk.append(paragraph)
                    current_size += paragraph_size + 2  # +2 for paragraph break
                else:
                    # Mevcut chunk'ı tamamla
                    if current_chunk:
                        chunks.append("\n\n".join(current_chunk))
                    # Yeni chunk başlat
                    current_chunk = [paragraph]
                    current_size = paragraph_size
        
        # Son chunk'ı ekle
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
        
        # Örtüşmeyi sağla (paragraf sınırlarını korur)
        if self.chunk_overlap > 0 and len(chunks) > 1:
            result_chunks = [chunks[0]]
            
            for i in range(1, len(chunks)):
                # Son parçanın son birkaç paragrafı
                prev_paragraphs = result_chunks[-1].split("\n\n")
                overlap_paragraphs = prev_paragraphs[-min(2, len(prev_paragraphs)):]  # En fazla son 2 paragraf
                
                # Mevcut parçanın başına ekle
                current_with_overlap = "\n\n".join(overlap_paragraphs) + "\n\n" + chunks[i]
                result_chunks.append(current_with_overlap)
                
            return result_chunks
            
        return chunks
    
    async def _chunk_hybrid(self, text: str) -> List[str]:
        """Önce yapısal olarak böler, sonra içerik temelli ince ayar yapar"""
        # 1. Metni öncelikle yapısal olarak parçalara ayır (başlık/bölüm sınırları)
        structural_chunks = []
        
        # Başlıkları bul (Markdown ve benzeri)
        heading_pattern = r'(^|\n)(#{1,5}\s+.+?|[^\n]+\n[=-]{2,})'
        headings = list(re.finditer(heading_pattern, text, re.MULTILINE))
        
        if not headings:
            # Başlık bulunamazsa normal paragraf bölme işlemini uygula
            return await self._chunk_by_paragraph(text)
        
        # Başlıklar arasını bölümler olarak ayır
        for i in range(len(headings)):
            start = headings[i].start()
            end = headings[i+1].start() if i < len(headings) - 1 else len(text)
            
            section = text[start:end].strip()
            if section:
                structural_chunks.append(section)
        
        # 2. Her yapısal parçayı içerik temelli olarak daha küçük parçalara ayır
        detailed_chunks = []
        
        for section in structural_chunks:
            # Bölüm doğrudan kullanılabilir boyutta mı?
            if len(section) <= self.chunk_size:
                detailed_chunks.append(section)
                continue
                
            # Bölümü semantik anlam koruyan alt parçalara ayır
            # Öncelikle paragraflarla bölmeyi dene
            paragraphs = re.split(r'\n\s*\n', section)
            
            current_chunk = []
            current_size = 0
            section_heading = ""
            
            # Bölüm başlığını koru
            heading_match = re.match(heading_pattern, section)
            if heading_match:
                section_heading = heading_match.group(0).strip()
                
            for p_idx, paragraph in enumerate(paragraphs):
                paragraph = paragraph.strip()
                if not paragraph:
                    continue
                    
                # İlk paragraf başlık olabilir
                if p_idx == 0 and heading_match and paragraph.startswith(section_heading):
                    is_heading = True
                else:
                    is_heading = False
                
                paragraph_size = len(paragraph)
                
                # Paragrafı doğrudan ekleyebilir miyiz?
                if current_size + paragraph_size <= self.chunk_size:
                    current_chunk.append(paragraph)
                    current_size += paragraph_size + 2
                else:
                    # Mevcut chunk'ı tamamla
                    if current_chunk:
                        chunk_text = "\n\n".join(current_chunk)
                        detailed_chunks.append(chunk_text)
                    
                    # Yeni chunk başlat
                    if is_heading:
                        # Başlık her zaman korunmalı
                        current_chunk = [paragraph]
                    else:
                        # Eğer önceki chunk'ta başlık varsa, onu tekrarla
                        if section_heading and len(detailed_chunks) > 0:
                            current_chunk = [section_heading, paragraph]
                        else:
                            current_chunk = [paragraph]
                            
                    current_size = len("\n\n".join(current_chunk))
            
            # Son chunk'ı ekle
            if current_chunk:
                chunk_text = "\n\n".join(current_chunk)
                detailed_chunks.append(chunk_text)
        
        # 3. Örtüşme ve semantik bağlamı sağlama
        if len(detailed_chunks) <= 1:
            return detailed_chunks
        
        # Parçalar arasında örtüşmeli geçiş için düzenleme
        result_chunks = [detailed_chunks[0]]
        
        for i in range(1, len(detailed_chunks)):
            # Bir önceki parçadan ilgili bilgileri al
            prev_chunks = result_chunks[-1].split("\n\n")
            
            # Başlık varsa koru
            heading = None
            for p in prev_chunks:
                if re.match(heading_pattern, p):
                    heading = p
                    break
            
            # Örtüşmeli geçiş için önceki chunk'tan metin al
            # Başlık + son paragraf veya sadece son paragraf
            overlap_text = ""
            if heading:
                overlap_text = heading + "\n\n"
            
            # Son paragrafı al (semantik bağlam oluşturmak için)
            if len(prev_chunks) > 0:
                last_para = prev_chunks[-1]
                if last_para != heading:  # Başlık değilse ekle
                    overlap_text += last_para + "\n\n"
            
            # Yeni chunk'ı örtüşme ile oluştur
            current_chunk = overlap_text + detailed_chunks[i]
            
            # Uzunluk kontrolü
            if len(current_chunk) > self.chunk_size * 1.5:  # Biraz esneklik ver
                # Çok uzunsa kırp
                current_chunk = current_chunk[:self.chunk_size * 1.5]
            
            result_chunks.append(current_chunk)
        
        return result_chunks

    async def context_stitching(self, chunks: List[str], query: str = None) -> str:
        """Bağlam parçalarını akıcı ve anlamlı bir metne dönüştürür"""
        if not chunks:
            return ""
            
        if len(chunks) == 1:
            return chunks[0]
        
        # 1. LLM kullanarak parçaları birleştir
        try:
            # Parça sayısına göre strateji belirle
            if len(chunks) <= 3:
                # Az sayıda parça için direkt birleştirme
                stitched_text = await llm_manager.chunk_and_stitch("\n\n".join(chunks))
                return stitched_text
            else:
                # Çok sayıda parça için hiyerarşik birleştirme
                # Önce parçaları gruplara ayır
                groups = []
                for i in range(0, len(chunks), 3):
                    group = chunks[i:i+3]
                    groups.append("\n\n".join(group))
                
                # Her grubu birleştir
                intermediates = []
                for group in groups:
                    stitched_group = await llm_manager.chunk_and_stitch(group)
                    intermediates.append(stitched_group)
                
                # Birleştirilmiş grupları tekrar birleştir
                final_text = await llm_manager.chunk_and_stitch("\n\n".join(intermediates))
                
                return final_text
        
        except Exception as e:
            # LLM ile birleştirme başarısız olursa yedek strateji kullan
            logger.error(f"LLM stitching hatası, yedek strateji kullanılıyor: {e}")
            return self._backup_stitching(chunks)
    
    def _backup_stitching(self, chunks: List[str]) -> str:
        """LLM olmadan basit birleştirme"""
        # Tekrar eden kısımları temizle
        unique_parts = []
        seen_text = set()
        
        for chunk in chunks:
            # Her parçayı cümlelere ayır
            sentences = re.split(r'(?<=[.!?])\s+', chunk)
            
            # Yeni cümleleri ekle
            new_sentences = []
            for sentence in sentences:
                normalized = sentence.strip().lower()
                if normalized not in seen_text and len(normalized) > 5:
                    new_sentences.append(sentence.strip())
                    seen_text.add(normalized)
            
            if new_sentences:
                unique_parts.append(" ".join(new_sentences))
        
        # Parçaları birleştir
        return "\n\n".join(unique_parts)