# Last reviewed: 2025-04-29 08:07:22 UTC (User: TeeksssNative)
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, OperationFailure
from typing import List, Dict, Optional, Any
import asyncio

from ..utils.config import (
    MONGODB_URI, MONGODB_MAX_POOL_SIZE, MONGODB_MIN_POOL_SIZE, 
    MONGODB_MAX_IDLE_TIME_MS
)
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Motor client singleton
_motor_client = None

async def get_mongodb_client():
    """MongoDB için async client döndürür (Motor kullanarak)"""
    global _motor_client
    
    if _motor_client is None:
        try:
            # Connection pool yapılandırması
            _motor_client = AsyncIOMotorClient(
                MONGODB_URI,
                maxPoolSize=MONGODB_MAX_POOL_SIZE,
                minPoolSize=MONGODB_MIN_POOL_SIZE,
                maxIdleTimeMS=MONGODB_MAX_IDLE_TIME_MS,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000
            )
            # Bağlantıyı test et
            await _motor_client.admin.command('ping')
            logger.info(f"MongoDB bağlantısı başarıyla kuruldu (Pool Size: {MONGODB_MAX_POOL_SIZE})")
        except (ConnectionFailure, OperationFailure) as e:
            logger.error(f"MongoDB bağlantı hatası: {e}", exc_info=True)
            _motor_client = None
            raise
    
    return _motor_client

async def close_mongodb_client():
    """MongoDB bağlantısını kapatır"""
    global _motor_client
    if _motor_client:
        _motor_client.close()
        _motor_client = None
        logger.info("MongoDB bağlantısı kapatıldı")

async def fetch_data_from_mongodb_async(
    db_name: str, 
    collection_name: str, 
    query: Dict = None,
    projection: Optional[Dict] = None, 
    limit: int = 0,
    sort: List[tuple] = None
) -> List[Dict]:
    """MongoDB'den veriyi asenkron olarak çeker"""
    if query is None:
        query = {}
    
    client = await get_mongodb_client()
    if not client:
        raise ConnectionError("MongoDB bağlantısı kurulamadı")
    
    database = client[db_name]
    collection = database[collection_name]
    
    try:
        # Sorguyu yapılandır
        cursor = collection.find(query, projection)
        
        # Sıralama uygula
        if sort:
            cursor = cursor.sort(sort)
        
        # Limit uygula
        if limit > 0:
            cursor = cursor.limit(limit)
        
        # Sonuçları topla (asenkron)
        documents = await cursor.to_list(length=limit if limit > 0 else None)
        logger.info(f"MongoDB'den {len(documents)} döküman çekildi: {db_name}.{collection_name}")
        
        return documents
    
    except Exception as e:
        logger.error(f"MongoDB veri çekme hatası: {e}", exc_info=True)
        raise

async def count_mongodb_documents(db_name: str, collection_name: str, query: Dict = None) -> int:
    """MongoDB koleksiyonundaki belge sayısını sayar"""
    if query is None:
        query = {}
    
    client = await get_mongodb_client()
    if not client:
        raise ConnectionError("MongoDB bağlantısı kurulamadı")
    
    database = client[db_name]
    collection = database[collection_name]
    
    try:
        count = await collection.count_documents(query)
        return count
    except Exception as e:
        logger.error(f"MongoDB sayma hatası: {e}", exc_info=True)
        raise