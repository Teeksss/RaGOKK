# Last reviewed: 2025-04-29 07:03:48 UTC (User: Teeksss)
# Adım 6: Asenkron I/O (get_text_embedding içinde to_thread kullanılacak)
from sentence_transformers import SentenceTransformer
from .config import SEMANTIC_MODEL, LOCAL_LLM_DEVICE
from .logger import get_logger
import numpy as np
from typing import List, Union, Optional
import time
import torch
import asyncio # asyncio eklendi

# CACHING NOTU: Embedding sonuçlarını cache'lemek performansı artırır.

logger = get_logger(__name__)
model: Optional[SentenceTransformer] = None
model_device: Optional[str] = None
vector_dimension: Optional[int] = None

def load_semantic_model():
    """Sentence Transformer modelini yükler (veya yüklüyse döndürür)."""
    # ... (önceki kod) ...

async def get_text_embedding_async(text: Union[str, List[str]]) -> Optional[Union[List[float], List[List[float]]]]:
    """Verilen metnin/metinlerin vektör temsilini (embedding) oluşturur (Async)."""
    current_model = load_semantic_model()
    if current_model is None:
        logger.error("Embedding oluşturulamadı: Semantic model yüklenemedi.")
        return None
    if not text: return [] if isinstance(text, list) else None

    # CACHING NOTU: Cache kontrolü burada yapılabilir.
    def encode_sync(): # Senkron encode işlemi
        try:
            # show_progress_bar=False önemli, thread içinde sorun çıkarabilir
            embeddings = current_model.encode(text, convert_to_numpy=True, show_progress_bar=False, device=model_device)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Embedding oluşturulurken hata: {e}", exc_info=True)
            return None # Hata durumunda None döndür

    try:
        # Adım 6: Asenkron I/O (to_thread kullanımı)
        result = await asyncio.to_thread(encode_sync)
        # CACHING NOTU: Sonucu cache'e yaz.
        return result
    except Exception as thread_err: # to_thread hatası
        logger.error(f"Embedding thread hatası: {thread_err}", exc_info=True)
        return None

def get_vector_dimension() -> Optional[int]:
    """Modelin vektör boyutunu döndürür (model yüklenmişse)."""
    # ... (önceki kod) ...