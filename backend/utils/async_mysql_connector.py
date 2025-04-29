# Last reviewed: 2025-04-29 08:07:22 UTC (User: TeeksssNative)
import aiomysql
from typing import List, Tuple, Dict, Any, Optional
import asyncio

from ..utils.config import (
    MYSQL_HOST, MYSQL_PORT, MYSQL_DB, MYSQL_USER, MYSQL_PASSWORD,
    MYSQL_POOL_SIZE, MYSQL_MAX_OVERFLOW
)
from ..utils.logger import get_logger

logger = get_logger(__name__)

# MySQL connection pool singleton
_mysql_pool = None

async def get_mysql_pool():
    """MySQL için async connection pool döndürür"""
    global _mysql_pool
    
    if _mysql_pool is None:
        try:
            _mysql_pool = await aiomysql.create_pool(
                host=MYSQL_HOST,
                port=int(MYSQL_PORT),
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                db=MYSQL_DB,
                maxsize=MYSQL_POOL_SIZE,
                pool_recycle=1800,  # 30 dakika
                echo=False,  # SQL loglarını gösterme
                autocommit=True,
                charset="utf8mb4"
            )
            logger.info(f"MySQL connection pool başarıyla oluşturuldu (Pool Size: {MYSQL_POOL_SIZE})")
        except Exception as e:
            logger.error(f"MySQL connection pool oluşturma hatası: {e}", exc_info=True)
            _mysql_pool = None
            raise
    
    return _mysql_pool

async def close_mysql_pool():
    """MySQL connection pool'u kapatır"""
    global _mysql_pool
    if _mysql_pool:
        _mysql_pool.close()
        await _mysql_pool.wait_closed()
        _mysql_pool = None
        logger.info("MySQL connection pool kapatıldı")

async def validate_table_name(conn, table_name: str) -> bool:
    """Tablo adının güvenli olup olmadığını kontrol eder"""
    # SQL injection engelleme
    if not isinstance(table_name, str) or not table_name.isalnum() or table_name.startswith(('_', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9')):
        return False
    
    # Tablo varlığını kontrol et
    async with conn.cursor() as cursor:
        await cursor.execute("SHOW TABLES LIKE %s", (table_name,))
        result = await cursor.fetchone()
        return result is not None

async def fetch_data_from_mysql_async(
    table_name: str, 
    columns: Optional[List[str]] = None, 
    where: Optional[Dict] = None,
    limit: Optional[int] = None,
    order_by: Optional[str] = None,
    desc: bool = False
) -> Optional[List[Tuple]]:
    """MySQL'den veriyi asenkron olarak çeker"""
    pool = await get_mysql_pool()
    if not pool:
        raise ConnectionError("MySQL bağlantısı kurulamadı")
    
    async with pool.acquire() as conn:
        # Tablo adını doğrula
        if not await validate_table_name(conn, table_name):
            logger.error(f"Geçersiz tablo adı: {table_name}")
            raise ValueError(f"Geçersiz tablo adı: {table_name}")
        
        # Sorgu oluştur
        query_parts = []
        query_params = []
        
        # SELECT kısmı
        cols = "*"
        if columns:
            # Her sütun adını doğrula
            valid_columns = []
            async with conn.cursor() as cursor:
                await cursor.execute(f"SHOW COLUMNS FROM {table_name}")
                table_columns = [row[0] for row in await cursor.fetchall()]
            
            for col in columns:
                if col in table_columns:
                    valid_columns.append(f"`{col}`")
            
            if valid_columns:
                cols = ", ".join(valid_columns)
        
        query_parts.append(f"SELECT {cols} FROM {table_name}")
        
        # WHERE kısmı
        if where and isinstance(where, dict):
            where_clauses = []
            for key, value in where.items():
                where_clauses.append(f"`{key}` = %s")
                query_params.append(value)
            
            if where_clauses:
                query_parts.append("WHERE " + " AND ".join(where_clauses))
        
        # ORDER BY kısmı
        if order_by:
            query_parts.append(f"ORDER BY `{order_by}` {'DESC' if desc else 'ASC'}")
        
        # LIMIT kısmı
        if limit and limit > 0:
            query_parts.append(f"LIMIT {limit}")
        
        # Tam sorgu
        query = " ".join(query_parts)
        
        try:
            # Sorguyu çalıştır ve sonuçları al
            async with conn.cursor() as cursor:
                await cursor.execute(query, tuple(query_params))
                results = await cursor.fetchall()
                
                logger.info(f"MySQL'den {len(results)} satır çekildi: {table_name}")
                return results
        
        except Exception as e:
            logger.error(f"MySQL veri çekme hatası: {e}", exc_info=True)
            raise