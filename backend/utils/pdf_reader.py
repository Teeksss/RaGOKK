# Last reviewed: 2025-04-29 07:03:48 UTC (User: Teeksss)
# Adım 6: Asenkron I/O (asyncio.to_thread kullanılıyor)
from .logger import get_logger
import asyncio
from typing import Optional

# VERİ İŞLEME NOTU: Karmaşık PDF'ler için `pdfplumber` veya `PyMuPDF (fitz)` daha iyi olabilir.

logger = get_logger(__name__)

def read_pdf(pdf_path: str) -> Optional[str]:
    """PDF dosyasından metin içeriğini okur (PyPDF2 kullanarak - Senkron)."""
    # ... (önceki kod - FileNotFoundError/ImportError fırlatıyor) ...

async def read_pdf_async(pdf_path: str) -> Optional[str]:
    """PDF okuma işlemini async olarak çalıştırır."""
    try:
        # Adım 6: Asenkron I/O (to_thread kullanımı)
        return await asyncio.to_thread(read_pdf, pdf_path)
    except (FileNotFoundError, ImportError) as known_err: raise known_err
    except Exception as e: logger.error(f"PDF async thread hatası ({pdf_path}): {e}", exc_info=True); return None