# Last reviewed: 2025-04-29 07:03:48 UTC (User: Teeksss)
import logging
import sys
from .config import LOG_LEVEL, LOG_FORMAT

# Adım 8: Loglama Notu: Yapılandırılmış Loglama (JSON) için `python-json-logger` kullanılabilir.
# Adım 8: Hata İzleme Notu: Hata İzleme (Error Tracking) için Sentry vb. entegrasyonu eklenebilir.
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT, stream=sys.stdout)

# Gürültülü kütüphanelerin log seviyesini ayarla
# ... (önceki ayarlar) ...

def get_logger(name):
    """İsimlendirilmiş bir logger instance'ı döndürür."""
    logger = logging.getLogger(name)
    return logger