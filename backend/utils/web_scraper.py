# Last reviewed: 2025-04-29 06:53:09 UTC (User: Teeksss)
from .logger import get_logger
import asyncio
import httpx
from typing import Optional

# VERİ İŞLEME NOTU: Dinamik siteler için `Playwright` veya `Selenium` gerekebilir.
# Boilerplate temizliği için `boilerpy3` veya `readability-lxml` kullanılabilir.

logger = get_logger(__name__)

async def scrape_website(url: str) -> Optional[str]:
    """Web sitesinden metin içeriğini çeker (httpx ve BeautifulSoup - async)."""
    try: from bs4 import BeautifulSoup
    except ImportError: logger.error("Web scraping için 'beautifulsoup4' gerekli."); raise ImportError("Web scraping için 'beautifulsoup4' gerekli.")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,tr;q=0.8',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=20.0, http2=True, verify=False) as client: # SSL doğrulaması atlandı (dikkat!)
            logger.info(f"Web sitesi çekiliyor: {url}")
            response = await client.get(url, headers=headers)
            response.raise_for_status() # 4xx, 5xx hatalarını fırlat
            content_type = response.headers.get('content-type', '').lower()
            if 'html' not in content_type: logger.warning(f"URL HTML değil ({content_type}): {url}"); return None

            # VERİ İŞLEME NOTU: HTML temizliği için daha iyi kütüphaneler kullanılabilir.
            soup = BeautifulSoup(response.text, 'html.parser')
            # Kaldırılacak etiketler
            tags_to_remove = ["script", "style", "nav", "footer", "aside", "header", "form", "noscript", "iframe", "button", "input", "select", "textarea"]
            for element in soup(tags_to_remove): element.decompose()

            # Ana içerik alanı bulunmaya çalışılabilir (heuristic)
            main_content = soup.find('main') or soup.find('article') or soup.find('div', role='main') or soup.body
            if not main_content: main_content = soup # Body bulunamazsa tüm soup

            text = main_content.get_text(separator='\n', strip=True)
            # Çoklu boş satırları tek satıra indir
            text = '\n'.join(line for line in text.splitlines() if line.strip())

            if not text: logger.warning(f"Web sitesinden metin çıkarılamadı: {url}"); return None
            logger.info(f"Web sitesi çekildi: {url} ({len(text)} karakter)")
            return text
    except ImportError as imp_err: raise imp_err
    except httpx.HTTPStatusError as e: logger.error(f"Web HTTP hatası ({url}, {e.response.status_code}): {e.response.text[:200]}"); return None
    except httpx.RequestError as e: logger.error(f"Web bağlantı hatası ({url}): {e}", exc_info=True); return None
    except Exception as e: logger.error(f"Web scraping hatası ({url}): {e}", exc_info=True); return None