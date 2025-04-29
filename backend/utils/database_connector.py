# Last reviewed: 2025-04-29 07:28:02 UTC (User: TeeksssNative)
import asyncio
import re  # Tablo adı doğrulaması için
from typing import List, Tuple, Dict, Any, Optional, Union

# Senkron sürücüler
import psycopg2
import psycopg2.pool
import mysql.connector
from mysql.connector import pooling
import pymongo
import sqlite3

# Async sürücüler (try/except içinde import et)
try:
    import asyncpg
    HAVE_ASYNCPG = True
except ImportError:
    HAVE_ASYNCPG = False

try:
    import motor.motor_asyncio
    HAVE_MOTOR = True
except ImportError:
    HAVE_MOTOR = False

try:
    import aiomysql
    HAVE_AIOMYSQL = True
except ImportError:
    HAVE_AIOMYSQL = False

from .config import (
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD,
    MYSQL_HOST, MYSQL_PORT, MYSQL_DB, MYSQL_USER, MYSQL_PASSWORD,
    MONGODB_HOST, MONGODB_DB, MONGODB_USER, MONGODB_PASSWORD
)
from .logger import get_logger

logger = get_logger(__name__)

# --------------- PostgreSQL ---------------

# Senkron havuz
pg_pool = None

def init_postgres_pool(min_conn=5, max_conn=20):
    """PostgreSQL bağlantı havuzunu oluşturur"""
    global pg_pool
    if not all([POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD]):
        logger.error("PostgreSQL bilgileri eksik.")
        return False
        
    try:
        pg_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=min_conn,
            maxconn=max_conn,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            connect_timeout=10
        )
        logger.info(f"PostgreSQL bağlantı havuzu oluşturuldu ({min_conn}-{max_conn})")
        return True
    except psycopg2.Error as e:
        logger.error(f"PostgreSQL havuz oluşturma hatası: {e}", exc_info=True)
        return False

def get_postgres_connection():
    """Havuzdan PostgreSQL bağlantısı alır"""
    global pg_pool
    if pg_pool is None:
        logger.warning("PostgreSQL havuzu henüz oluşturulmamış, oluşturuluyor...")
        init_postgres_pool()
        
    if pg_pool is None:
        logger.error("PostgreSQL havuzu oluşturulamadı.")
        return None
        
    try:
        connection = pg_pool.getconn()
        logger.debug("PostgreSQL bağlantısı havuzdan alındı")
        return connection
    except (psycopg2.pool.PoolError, psycopg2.Error) as e:
        logger.error(f"PostgreSQL havuzdan bağlantı alınamadı: {e}")
        return None

def release_postgres_connection(connection):
    """Kullanılan PostgreSQL bağlantısını havuza iade eder"""
    global pg_pool
    if pg_pool and connection:
        try:
            pg_pool.putconn(connection)
            logger.debug("PostgreSQL bağlantısı havuza iade edildi")
        except Exception as e:
            logger.error(f"PostgreSQL bağlantısı iade edilemedi: {e}")

def fetch_data_from_postgresql(conn, table_name: str, columns: List[str] = None, limit: Optional[int] = None) -> Optional[List[Tuple]]:
    """PostgreSQL'den veri çeker."""
    if not conn:
        return None
        
    cursor = None
    try:
        cursor = conn.cursor()
        column_str = "*" if not columns else ", ".join(f'"{col}"' for col in columns)
        
        # Tablo adı güvenliği
        if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
            raise ValueError("Geçersiz tablo adı.")
            
        query = f'SELECT {column_str} FROM "{table_name}"'
        params = []
        
        if limit:
            query += " LIMIT %s"
            params.append(int(limit))
            
        logger.debug(f"PostgreSQL sorgusu: {query} Params: {params}")
        cursor.execute(query, params if params else None)
        results = cursor.fetchall()
        logger.info(f"PostgreSQL '{table_name}' -> {len(results)} satır.")
        return results
    except (psycopg2.Error, ValueError) as e:
        logger.error(f"PostgreSQL fetch hatası ({table_name}): {e}", exc_info=True)
        return None
    finally:
        if cursor:
            cursor.close()
            
# -------- PostgreSQL Async (asyncpg) --------

# AsyncPG bağlantı havuzu
asyncpg_pool = None

async def init_asyncpg_pool(min_conn=5, max_conn=20):
    """AsyncPG bağlantı havuzu oluşturur"""
    global asyncpg_pool
    if not HAVE_ASYNCPG:
        logger.error("AsyncPG kütüphanesi yüklü değil")
        return False
    
    if not all([POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD]):
        logger.error("PostgreSQL bilgileri eksik.")
        return False
        
    try:
        asyncpg_pool = await asyncpg.create_pool(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            min_size=min_conn,
            max_size=max_conn,
            command_timeout=10
        )
        logger.info(f"AsyncPG bağlantı havuzu oluşturuldu ({min_conn}-{max_conn})")
        return True
    except Exception as e:
        logger.error(f"AsyncPG havuz oluşturma hatası: {e}", exc_info=True)
        return False

async def fetch_data_from_postgresql_async(table_name: str, columns: List[str] = None, limit: Optional[int] = None) -> Optional[List[Dict[str, Any]]]:
    """AsyncPG ile PostgreSQL'den veri çeker"""
    global asyncpg_pool
    
    if not HAVE_ASYNCPG:
        logger.error("AsyncPG kütüphanesi yüklü değil, senkron sürücü kullanılıyor")
        # Senkron sürücüye fallback
        conn = get_postgres_connection()
        try:
            result = fetch_data_from_postgresql(conn, table_name, columns, limit)
            if result and columns:
                # Tuple sonuçları dict'e çevir
                return [dict(zip(columns, row)) for row in result]
            return result
        finally:
            if conn:
                release_postgres_connection(conn)
    
    if asyncpg_pool is None:
        logger.warning("AsyncPG havuzu henüz oluşturulmamış, oluşturuluyor...")
        await init_asyncpg_pool()
        
    if asyncpg_pool is None:
        logger.error("AsyncPG havuzu oluşturulamadı.")
        return None
        
    # Tablo adı güvenliği
    if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
        logger.error(f"Geçersiz tablo adı: {table_name}")
        return None
    
    column_str = "*" if not columns else ", ".join(f'"{col}"' for col in columns)
    query = f'SELECT {column_str} FROM "{table_name}"'
    
    if limit:
        query += f" LIMIT {int(limit)}"
        
    try:
        async with asyncpg_pool.acquire() as connection:
            logger.debug(f"AsyncPG sorgusu: {query}")
            rows = await connection.fetch(query)
            logger.info(f"AsyncPG '{table_name}' -> {len(rows)} satır.")
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"AsyncPG fetch hatası ({table_name}): {e}", exc_info=True)
        return None

# --------------- MySQL ---------------

# MySQL bağlantı havuzu
mysql_pool = None

def init_mysql_pool(pool_name="mysql_pool", pool_size=10):
    """MySQL bağlantı havuzu oluşturur"""
    global mysql_pool
    
    if not all([MYSQL_HOST, MYSQL_DB, MYSQL_USER, MYSQL_PASSWORD]):
        logger.error("MySQL bilgileri eksik.")
        return False
        
    try:
        dbconfig = {
            "host": MYSQL_HOST,
            "port": int(MYSQL_PORT),
            "database": MYSQL_DB,
            "user": MYSQL_USER,
            "password": MYSQL_PASSWORD,
            "connect_timeout": 10
        }
        mysql_pool = pooling.MySQLConnectionPool(
            pool_name=pool_name,
            pool_size=pool_size,
            pool_reset_session=True,
            **dbconfig
        )
        logger.info(f"MySQL bağlantı havuzu oluşturuldu (boyut: {pool_size})")
        return True
    except mysql.connector.Error as e:
        logger.error(f"MySQL havuz oluşturma hatası: {e}", exc_info=True)
        return False

def get_mysql_connection():
    """Havuzdan MySQL bağlantısı alır"""
    global mysql_pool
    
    if mysql_pool is None:
        logger.warning("MySQL havuzu henüz oluşturulmamış, oluşturuluyor...")
        init_mysql_pool()
        
    if mysql_pool is None:
        logger.error("MySQL havuzu oluşturulamadı.")
        return None
        
    try:
        connection = mysql_pool.get_connection()
        logger.debug("MySQL bağlantısı havuzdan alındı")
        return connection
    except mysql.connector.Error as e:
        logger.error(f"MySQL havuzdan bağlantı alınamadı: {e}")
        return None

def fetch_data_from_mysql(conn, table_name: str, columns: List[str] = None, limit: Optional[int] = None) -> Optional[List[Tuple]]:
    """MySQL'den veri çeker."""
    # ... (önceki kod) ...

# -------- MySQL Async (aiomysql) --------

# AioMySQL bağlantı havuzu
aiomysql_pool = None

async def init_aiomysql_pool(min_conn=5, max_conn=20):
    """AioMySQL bağlantı havuzu oluşturur"""
    global aiomysql_pool
    
    if not HAVE_AIOMYSQL:
        logger.error("AioMySQL kütüphanesi yüklü değil")
        return False
    
    if not all([MYSQL_HOST, MYSQL_DB, MYSQL_USER, MYSQL_PASSWORD]):
        logger.error("MySQL bilgileri eksik.")
        return False
        
    try:
        aiomysql_pool = await aiomysql.create_pool(
            host=MYSQL_HOST,
            port=int(MYSQL_PORT),
            db=MYSQL_DB,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            minsize=min_conn,
            maxsize=max_conn,
            autocommit=False,
            pool_recycle=3600
        )
        logger.info(f"AioMySQL bağlantı havuzu oluşturuldu ({min_conn}-{max_conn})")
        return True
    except Exception as e:
        logger.error(f"AioMySQL havuz oluşturma hatası: {e}", exc_info=True)
        return False

async def fetch_data_from_mysql_async(table_name: str, columns: List[str] = None, limit: Optional[int] = None) -> Optional[List[Dict[str, Any]]]:
    """AioMySQL ile MySQL'den veri çeker"""
    global aiomysql_pool
    
    if not HAVE_AIOMYSQL:
        logger.error("AioMySQL kütüphanesi yüklü değil, senkron sürücü kullanılıyor")
        # Senkron sürücüye fallback
        conn = get_mysql_connection()
        try:
            result = fetch_data_from_mysql(conn, table_name, columns, limit)
            if result and columns:
                # Tuple sonuçları dict'e çevir
                return [dict(zip(columns, row)) for row in result]
            return result
        finally:
            if conn:
                conn.close()
    
    if aiomysql_pool is None:
        logger.warning("AioMySQL havuzu henüz oluşturulmamış, oluşturuluyor...")
        await init_aiomysql_pool()
        
    if aiomysql_pool is None:
        logger.error("AioMySQL havuzu oluşturulamadı.")
        return None
        
    # Tablo adı güvenliği
    if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
        logger.error(f"Geçersiz tablo adı: {table_name}")
        return None
    
    column_str = "*" if not columns else ", ".join(f'`{col}`' for col in columns)
    query = f"SELECT {column_str} FROM `{table_name}`"
    
    if limit:
        query += f" LIMIT {int(limit)}"
        
    try:
        async with aiomysql_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                logger.debug(f"AioMySQL sorgusu: {query}")
                await cursor.execute(query)
                rows = await cursor.fetchall()
                logger.info(f"AioMySQL '{table_name}' -> {len(rows)} satır.")
                return rows
    except Exception as e:
        logger.error(f"AioMySQL fetch hatası ({table_name}): {e}", exc_info=True)
        return None

# --------------- MongoDB ---------------

# Motor async client
motor_client = None

def get_mongodb_connection():
    """MongoDB bağlantısı oluşturur"""
    if not all([MONGODB_HOST, MONGODB_DB]):
        logger.error("MongoDB bilgileri eksik.")
        return None
        
    try:
        uri = f"mongodb://{MONGODB_USER}:{MONGODB_PASSWORD}@{MONGODB_HOST.replace('mongodb://','')}/?authSource=admin" if MONGODB_USER and MONGODB_PASSWORD else f"mongodb://{MONGODB_HOST.replace('mongodb://','')}/"
        client = pymongo.MongoClient(
            uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            maxPoolSize=50,
            minPoolSize=10,
            maxIdleTimeMS=30000
        )
        client.admin.command('ping')
        db = client[MONGODB_DB]
        logger.info(f"MongoDB bağlantısı oluşturuldu (max_pool: 50)")
        return db
    except pymongo.errors.ConnectionFailure as e:
        logger.error(f"MongoDB bağlantı hatası: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"MongoDB beklenmeyen hata: {e}", exc_info=True)
        return None

def init_motor_client():
    """Motor Async MongoDB bağlantısı oluşturur"""
    global motor_client
    
    if not HAVE_MOTOR:
        logger.error("Motor kütüphanesi yüklü değil")
        return False
    
    if not all([MONGODB_HOST, MONGODB_DB]):
        logger.error("MongoDB bilgileri eksik.")
        return False
        
    try:
        uri = f"mongodb://{MONGODB_USER}:{MONGODB_PASSWORD}@{MONGODB_HOST.replace('mongodb://','')}/?authSource=admin" if MONGODB_USER and MONGODB_PASSWORD else f"mongodb://{MONGODB_HOST.replace('mongodb://','')}/"
        motor_client = motor.motor_asyncio.AsyncIOMotorClient(
            uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            maxPoolSize=50,
            minPoolSize=10
        )
        logger.info("Motor MongoDB bağlantısı oluşturuldu (max_pool: 50)")
        return True
    except Exception as e:
        logger.error(f"Motor MongoDB bağlantı hatası: {e}", exc_info=True)
        motor_client = None
        return False

async def fetch_data_from_mongodb_async(collection_name: str, query: Dict = {}, projection: Optional[Dict] = None, limit: int = 0) -> Optional[List[Dict]]:
    """Motor ile MongoDB'den veri çeker"""
    global motor_client
    
    if not HAVE_MOTOR:
        logger.error("Motor kütüphanesi yüklü değil, senkron sürücü kullanılıyor")
        # Senkron sürücüye fallback
        db = get_mongodb_connection()
        if not db:
            return None
        try:
            return fetch_data_from_mongodb(db, collection_name, query, projection, limit)
        finally:
            pass  # MongoDB bağlantısı kapatılmamalı (pool)
    
    if motor_client is None:
        logger.warning("Motor MongoDB client henüz oluşturulmamış, oluşturuluyor...")
        init_motor_client()
        
    if motor_client is None:
        logger.error("Motor MongoDB client oluşturulamadı.")
        return None
        
    try:
        db = motor_client[MONGODB_DB]
        collection = db[collection_name]
        
        logger.debug(f"Motor MongoDB sorgusu: collection='{collection_name}', query={query}, limit={limit}")
        cursor = collection.find(query, projection).limit(limit)
        
        documents = await cursor.to_list(length=limit if limit else 1000)
        logger.info(f"Motor MongoDB '{collection_name}' -> {len(documents)} belge.")
        return documents
    except Exception as e:
        logger.error(f"Motor MongoDB fetch hatası ({collection_name}): {e}", exc_info=True)
        return None

# --- Uygulama başlangıcında tüm havuzları başlat ---
async def init_all_pools():
    """Tüm veritabanı bağlantı havuzlarını başlat"""
    logger.info("Tüm veritabanı bağlantı havuzları başlatılıyor...")
    
    # Senkron havuzlar
    init_postgres_pool()
    init_mysql_pool()
    
    # Async havuzlar
    tasks = []
    if HAVE_ASYNCPG:
        tasks.append(init_asyncpg_pool())
    if HAVE_AIOMYSQL:
        tasks.append(init_aiomysql_pool())
    if HAVE_MOTOR:
        tasks.append(asyncio.to_thread(init_motor_client))
        
    # Async görevleri bekle
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
        
    logger.info("Tüm veritabanı bağlantı havuzları başlatıldı")