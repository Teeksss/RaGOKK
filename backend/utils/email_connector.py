# Last reviewed: 2025-04-29 07:03:48 UTC (User: Teeksss)
# Adım 6: Asenkron I/O Notu: Bu dosya tamamen senkron. `aioimaplib` kullanılmalı veya `asyncio.to_thread` ile sarmalanmalı.
import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
import asyncio
from .config import EMAIL_ADDRESS, EMAIL_PASSWORD, IMAP_SERVER
from .logger import get_logger
from typing import List, Dict, Optional
from datetime import datetime

logger = get_logger(__name__)

def _decode_header(header):
    # ... (önceki kod) ...

def connect_to_email():
    """IMAP sunucusuna bağlanır ve giriş yapar (SENKRON)."""
    logger.warning("E-posta bağlantısı senkron oluşturuluyor ('aioimaplib' veya to_thread önerilir).")
    # ... (önceki kod) ...

def fetch_emails(mail, mailbox="inbox", criteria="ALL", num_latest=10) -> List[Dict]:
    """Belirtilen posta kutusundan e-postaları çeker (SENKRON)."""
    # ... (önceki kod - tarih parse etme dahil) ...
    return emails