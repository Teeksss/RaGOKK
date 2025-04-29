# Last reviewed: 2025-04-29 07:03:48 UTC (User: Teeksss)
# Adım 6: Asenkron I/O (asyncio.to_thread kullanılıyor)
from .logger import get_logger
import asyncio
from typing import Optional
# from .config import OCR_LANGUAGES # Config'den dil alınabilir

logger = get_logger(__name__)

def extract_text_from_image(image_path: str) -> Optional[str]:
    """Görüntü dosyasından metin çıkarır (Tesseract OCR kullanarak - Senkron)."""
    # ... (önceki kod - FileNotFoundError/ImportError fırlatıyor) ...
    # langs = OCR_LANGUAGES # Config'den al
    langs = 'tur+eng' # Şimdilik sabit
    text = pytesseract.image_to_string(Image.open(image_path), lang=langs, timeout=60)
    # ... (önceki kod) ...

async def extract_text_from_image_async(image_path: str) -> Optional[str]:
     """OCR işlemini async olarak çalıştırır."""
     try:
         # Adım 6: Asenkron I/O (to_thread kullanımı)
         return await asyncio.to_thread(extract_text_from_image, image_path)
     except (FileNotFoundError, ImportError) as known_err: raise known_err
     except Exception as e: logger.error(f"OCR async thread hatası ({image_path}): {e}", exc_info=True); return None