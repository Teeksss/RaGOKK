# Last reviewed: 2025-04-29 07:20:15 UTC (User: Teeksss)
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from ..utils.config import POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
from ..utils.logger import get_logger

logger = get_logger(__name__)

# PostgreSQL bağlantı URL'i
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# SQLAlchemy engine ve session
try:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("Veritabanı bağlantısı başarıyla oluşturuldu")
except Exception as e:
    logger.critical(f"Veritabanı bağlantısı oluşturulamadı: {e}")
    raise

# DB session dependency - FastAPI'nin dependency injection sistemi için
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# SQLAlchemy model inheritance için Base sınıfı
Base = declarative_base()