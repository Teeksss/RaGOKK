# Last reviewed: 2025-04-29 11:06:31 UTC (User: Teekssseksiklikleri)
from typing import List, Dict, Any
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import numpy as np
import asyncio
import os
from functools import lru_cache

from .logger import get_logger

logger = get_logger(__name__)

class CrossEncoderReranker:
    """
    Cross-Encoder modeli kullanarak belgeleri yeniden sıralayan sınıf.
    MS MARCO veya benzeri modeller kullanır.
    """
    
    def __init__(self, model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.max_length = 512
        
        # Model ve tokenizer'ı yükle
        self._load_model()
    
    @lru_cache(maxsize=1)  # Modeli sadece bir kere yükle
    def _load_model(self):
        """Model ve tokenizer'ı yükler"""
        try:
            logger.info(f"Cross-Encoder reranker modeli yükleniyor: {self.model_name}")
            
            # İlk önce tokenizer'ı yükle
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            
            # Sonra modeli yükle
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            self.model.to(self.device)
            
            logger.info(f"Cross-Encoder reranker model yüklendi. Cihaz: {self.device}")
        except Exception as e:
            logger.error(f"Reranker model yükleme hatası: {e}")
            # Model yüklenemezse fallback
            self.model = None
            self.tokenizer = None
    
    async def rerank(self, query: str, docs: List[Dict[str, Any]], top_k: int = None) -> List[Dict[str, Any]]:
        """
        Belgeleri sorguya göre yeniden sıralar
        
        Args:
            query: Kullanıcı sorgusu
            docs: Sıralanacak belgeler listesi
            top_k: En üstteki kaç sonucu döndürmek istediğimiz (None ise tümü)
            
        Returns:
            List[Dict]: Yeniden sıralanmış belgeler listesi
        """
        if not docs:
            return []
            
        if self.model is None or self.tokenizer is None:
            logger.warning("Reranker model yüklenmemiş, orijinal sıralama kullanılacak")
            return docs[:top_k] if top_k else docs
        
        try:
            # Her belge için sorgu-içerik çiftleri oluştur
            pairs = [(query, doc.get("title", "") + " " + doc.get("content", "")) for doc in docs]
            
            # Model hesaplama işlemi CPU-bound, bu nedenle thread pool'da çalıştır
            scores = await asyncio.to_thread(
                self._compute_scores, pairs
            )
            
            # Yeni skorları ekle ve sırala
            for i, doc in enumerate(docs):
                # Normalize edilmiş skor (0 ile 1 arası)
                norm_score = float(scores[i])
                
                # Orijinal skora yeni skoru entegre et (karşılaştırılabilir olması için)
                if "score" in doc:
                    # Önceki skoru sakla
                    doc["original_score"] = doc["score"]
                    # Yeni skor = normalize edilmiş rerank skoru (daha yüksek öncelikli)
                    doc["score"] = norm_score
                    doc["reranked"] = True
            
            # Skora göre sırala (yüksekten düşüğe)
            reranked_docs = sorted(docs, key=lambda x: x["score"], reverse=True)
            
            # İstenirse top_k kadar sonuç döndür
            return reranked_docs[:top_k] if top_k else reranked_docs
            
        except Exception as e:
            logger.error(f"Reranking işlemi sırasında hata: {e}")
            return docs[:top_k] if top_k else docs
    
    def _compute_scores(self, pairs: List[tuple]) -> List[float]:
        """
        Cross-Encoder modelini kullanarak skorları hesaplar
        Bu işlem senkron olarak çalışır (CPU/GPU işlemi)
        """
        # Tokenize
        features = self.tokenizer.batch_encode_plus(
            pairs,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        # Tensörleri doğru cihaza taşı
        features = {key: val.to(self.device) for key, val in features.items()}
        
        # Model ile tahmin yap
        with torch.no_grad():
            scores = self.model(**features).logits
        
        # Bir sınıflı modeller için normalize et
        if scores.shape[1] == 1:  # [batch_size, 1]
            scores = torch.sigmoid(scores).squeeze(1)
        else:  # Çok sınıflı ise, softmax uygula
            scores = torch.softmax(scores, dim=1)[:, 1]  # İkinci sınıf (alakalı) olasılıklarını al
            
        return scores.cpu().numpy().tolist()

# Singleton
reranker = CrossEncoderReranker()