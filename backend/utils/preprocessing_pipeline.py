# Last reviewed: 2025-04-29 11:33:20 UTC (User: Teekssseksikleri)
from typing import List, Dict, Any, Optional, Tuple, Set, Union, Callable
import re
import string
import unicodedata
import numpy as np
from dataclasses import dataclass
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer, PorterStemmer, SnowballStemmer
from nltk.tokenize import word_tokenize
import langdetect

# NLTK gereksinimleri
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')
    nltk.download('wordnet')

from ..utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class PreprocessingOptions:
    """Ön işleme seçenekleri"""
    remove_punctuation: bool = True
    remove_stopwords: bool = True
    lowercase: bool = True
    lemmatize: bool = True
    stem: bool = False
    remove_numbers: bool = False
    normalize_whitespace: bool = True
    min_word_length: int = 2
    language: str = "auto"  # auto, en, tr, etc.
    custom_stopwords: Optional[Set[str]] = None
    custom_pipeline: Optional[List[Callable]] = None
    normalize_embeddings: bool = True

class TextPreprocessor:
    """
    Vektör veritabanına ekleme öncesi metin ön işleme pipeline'ı.
    Desteklenen işlemler:
    - Stopword çıkarımı
    - Lemmatization
    - Stemming
    - Noktalama temizliği
    - Sayı çıkarma
    - Boşluk düzeltme
    - Özel işleme adımları
    """
    
    def __init__(self, options: Optional[PreprocessingOptions] = None):
        self.options = options or PreprocessingOptions()
        
        self.lemmatizers = {
            'en': WordNetLemmatizer(),
            # Diğer diller için buraya lemmatizer eklenebilir
        }
        
        self.stemmers = {
            'en': PorterStemmer(),
            'tr': SnowballStemmer('turkish')
            # Diğer diller için buraya stemmer eklenebilir
        }
        
        # Durdurucu kelimeler sözlüğü
        self.stopwords = {}
        for lang in ['english', 'turkish', 'german', 'french', 'spanish']:
            try:
                self.stopwords[lang[:2]] = set(stopwords.words(lang))
            except:
                # Dil paketi yüklü değilse atla
                pass
        
        # Özel stopwords ekle
        if self.options.custom_stopwords:
            self.stopwords['custom'] = self.options.custom_stopwords
    
    def preprocess_text(self, text: str) -> str:
        """Ana ön işleme fonksiyonu"""
        if not text:
            return ""
        
        # Dil tespiti
        language = self.options.language
        if language == "auto":
            try:
                language = langdetect.detect(text)
            except:
                language = "en"  # Varsayılan dil
        
        # Özel işleme adımları varsa önce onları çalıştır
        if self.options.custom_pipeline:
            for process_fn in self.options.custom_pipeline:
                text = process_fn(text)
        
        # Küçük harfe çevir
        if self.options.lowercase:
            text = text.lower()
        
        # Unicode normalleştirme
        text = unicodedata.normalize('NFKD', text)
        
        # Noktalama işaretlerini kaldır
        if self.options.remove_punctuation:
            text = self._remove_punctuation(text)
        
        # Sayıları kaldır
        if self.options.remove_numbers:
            text = re.sub(r'\d+', '', text)
        
        # Boşlukları normalleştir
        if self.options.normalize_whitespace:
            text = self._normalize_whitespace(text)
        
        # Tokenize
        tokens = word_tokenize(text)
        
        # Stopword'leri kaldır
        if self.options.remove_stopwords:
            tokens = self._remove_stopwords(tokens, language)
        
        # Minimum uzunluk kontrolü
        if self.options.min_word_length > 0:
            tokens = [t for t in tokens if len(t) >= self.options.min_word_length]
        
        # Lemmatize
        if self.options.lemmatize:
            tokens = self._lemmatize(tokens, language)
        
        # Stemming
        if self.options.stem:
            tokens = self._stem(tokens, language)
        
        # Tokenleri birleştir
        return ' '.join(tokens)
    
    def preprocess_batch(self, texts: List[str]) -> List[str]:
        """Metin listesini toplu olarak ön işler"""
        return [self.preprocess_text(text) for text in texts]
    
    def _remove_punctuation(self, text: str) -> str:
        """Noktalama işaretlerini kaldırır"""
        translator = str.maketrans('', '', string.punctuation)
        return text.translate(translator)
    
    def _normalize_whitespace(self, text: str) -> str:
        """Boşlukları normalleştir"""
        return ' '.join(text.split())
    
    def _remove_stopwords(self, tokens: List[str], language: str) -> List[str]:
        """Durdurucu kelimeleri kaldırır"""
        # Dile özel stopwords
        lang_stopwords = self.stopwords.get(language[:2], set())
        
        # Özel stopwords
        custom_stopwords = self.stopwords.get('custom', set())
        
        # Tüm stopwords
        all_stopwords = lang_stopwords.union(custom_stopwords)
        
        return [t for t in tokens if t.lower() not in all_stopwords]
    
    def _lemmatize(self, tokens: List[str], language: str) -> List[str]:
        """Kelimeleri lemmatize eder"""
        lemmatizer = self.lemmatizers.get(language[:2])
        if not lemmatizer:
            return tokens  # Dil için lemmatizer yoksa tokenleri değiştirmeden döndür
            
        return [lemmatizer.lemmatize(token) for token in tokens]
    
    def _stem(self, tokens: List[str], language: str) -> List[str]:
        """Kelimeleri stem eder"""
        stemmer = self.stemmers.get(language[:2])
        if not stemmer:
            return tokens  # Dil için stemmer yoksa tokenleri değiştirmeden döndür
            
        return [stemmer.stem(token) for token in tokens]


class EmbeddingProcessor:
    """
    Embedding vektörlerini normalize eden ve işleyen sınıf
    """
    
    def normalize_embedding(self, embedding: List[float]) -> List[float]:
        """Vektörü L2 normuna göre normalize eder"""
        arr = np.array(embedding)
        norm = np.linalg.norm(arr)
        if norm == 0:
            return embedding
        return (arr / norm).tolist()
    
    def batch_normalize_embeddings(self, embeddings: List[List[float]]) -> List[List[float]]:
        """Birden çok vektörü normalize eder"""
        return [self.normalize_embedding(emb) for emb in embeddings]
    
    def average_embeddings(self, embeddings: List[List[float]]) -> List[float]:
        """Birden çok vektörün ortalamasını alır"""
        if not embeddings:
            return []
        
        # Vektörleri numpy array'e çevir
        arrays = np.array(embeddings)
        
        # Ortalama al
        avg_embedding = np.mean(arrays, axis=0)
        
        # Normalize et
        return self.normalize_embedding(avg_embedding.tolist())


class DocumentProcessingPipeline:
    """
    Doküman işleme ve vektörleştirme işlemlerini birleştiren pipeline
    """
    
    def __init__(self, 
                preprocessing_options: Optional[PreprocessingOptions] = None,
                chunk_size: int = 512,
                chunk_overlap: int = 50):
        self.text_preprocessor = TextPreprocessor(preprocessing_options)
        self.embedding_processor = EmbeddingProcessor()
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    async def process_document(self, 
                          content: str, 
                          metadata: Optional[Dict[str, Any]] = None,
                          get_embeddings_fn: Optional[Callable] = None
                         ) -> Dict[str, Any]:
        """
        Dokümanı işler ve vektörleştirir
        
        Args:
            content: Doküman içeriği
            metadata: Doküman meta verileri
            get_embeddings_fn: Metin için embedding vektörü üreten fonksiyon
            
        Returns:
            Dict: İşlenmiş doküman ve chunk'ları
        """
        # 1. İçeriği normalize et
        normalized_text = self.text_preprocessor.preprocess_text(content)
        
        # 2. Chunk'lara böl
        chunks = self._chunk_text(normalized_text)
        
        # 3. Her chunk'ı işle
        processed_chunks = []
        
        for i, chunk in enumerate(chunks):
            # Chunk'ı preprocessor ile işle
            processed_text = chunk
            
            # Embedding hesapla (eğer embedding fonksiyonu verilmişse)
            embedding = None
            if get_embeddings_fn:
                try:
                    embedding = await get_embeddings_fn(processed_text)
                    
                    # Embedding'i normalize et
                    if embedding:
                        embedding = self.embedding_processor.normalize_embedding(embedding)
                except Exception as e:
                    logger.error(f"Embedding hesaplama hatası: {e}")
            
            # Chunk'ı kaydet
            processed_chunk = {
                "chunk_id": f"chunk_{i+1}",
                "text": processed_text,
                "embedding": embedding,
                "start_idx": i * (self.chunk_size - self.chunk_overlap) if i > 0 else 0,
            }
            
            processed_chunks.append(processed_chunk)
        
        # 4. Sonuçları hazırla
        result = {
            "content": normalized_text,
            "chunks": processed_chunks,
            "chunk_count": len(processed_chunks),
            "metadata": metadata or {}
        }
        
        return result
    
    def _chunk_text(self, text: str) -> List[str]:
        """Metni belirli boyutta chunk'lara böler"""
        # Kısa metin kontrolü
        if len(text) <= self.chunk_size:
            return [text]
        
        # Paragraf bazlı bölme yapmaya çalış
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            # Paragraf tek başına chunk boyutundan büyükse, kelime bazlı böl
            if len(para) > self.chunk_size:
                # Mevcut chunk'ı ekle (boş değilse)
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                
                # Paragrafı kelime bazlı böl
                words = para.split()
                temp_chunk = ""
                
                for word in words:
                    if len(temp_chunk) + len(word) + 1 > self.chunk_size:
                        chunks.append(temp_chunk)
                        temp_chunk = word
                    else:
                        if temp_chunk:
                            temp_chunk += " "
                        temp_chunk += word
                
                # Kalan kelimeler varsa ekle
                if temp_chunk:
                    current_chunk = temp_chunk
            
            # Paragraf + mevcut chunk chunk boyutunu aşıyorsa, mevcut chunk'ı ekle
            elif len(current_chunk) + len(para) + 2 > self.chunk_size:
                chunks.append(current_chunk)
                current_chunk = para
            
            # Paragrafı mevcut chunk'a ekle
            else:
                if current_chunk:
                    current_chunk += "\n\n"
                current_chunk += para
        
        # Son chunk'ı ekle
        if current_chunk:
            chunks.append(current_chunk)
        
        # Chunk'lar arası belirli bir overlap oluştur
        if self.chunk_overlap > 0 and len(chunks) > 1:
            overlapped_chunks = []
            
            for i, chunk in enumerate(chunks):
                if i == 0:
                    overlapped_chunks.append(chunk)
                else:
                    # Önceki chunk'tan overlap kadar kelime al
                    prev_chunk = chunks[i-1]
                    prev_words = prev_chunk.split()
                    
                    # Önceki chunk'ın son N kelimesi
                    overlap_start = max(0, len(prev_words) - self.chunk_overlap)
                    overlap_words = prev_words[overlap_start:]
                    
                    # Overlap'i mevcut chunk'ın başına ekle
                    overlapped_chunk = " ".join(overlap_words) + " " + chunk
                    overlapped_chunks.append(overlapped_chunk)
                    
            return overlapped_chunks
        
        return chunks