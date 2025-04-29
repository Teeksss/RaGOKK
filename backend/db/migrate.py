# Last reviewed: 2025-04-29 10:51:12 UTC (User: TeeksssPrioritizationTest.js)
import asyncio
import argparse
import importlib
import sys
import os
from sqlalchemy import inspect, MetaData, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from async_database import Base
from models import ApiKeyDB, SecurityLogDB, User, Document

# Desteklenen veritabanı türleri
SUPPORTED_DIALECTS = ['sqlite', 'postgresql', 'mysql']

async def check_table_exists(engine, table_name):
    """Veritabanında belirli bir tablonun var olup olmadığını kontrol eder"""
    async with engine.connect() as conn:
        insp = inspect(conn)
        tables = await insp.get_table_names()
        return table_name in tables

async def create_tables(engine):
    """Tüm tabloları oluşturur"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("Tüm tablolar oluşturuldu.")

async def migrate_specific_table(engine, table_class):
    """Belirli bir tabloyu oluşturur"""
    metadata = MetaData()
    table_name = table_class.__tablename__
    
    # Tablo zaten var mı kontrol et
    exists = await check_table_exists(engine, table_name)
    if exists:
        print(f"'{table_name}' tablosu zaten mevcut.")
        return
    
    # Sadece bu tabloyu oluştur
    async with engine.begin() as conn:
        # metadata'ya sadece bu tabloyu ekle
        table = table_class.__table__
        table.metadata = metadata
        metadata.tables[table.name] = table
        
        # Tabloyu oluştur
        await conn.run_sync(metadata.create_all)
    
    print(f"'{table_name}' tablosu başarıyla oluşturuldu.")

async def run_migration(db_url, target_table=None):
    """Migration işlemini başlatır"""
    print(f"Veritabanı URL: {db_url}")
    
    # Engine oluştur
    if db_url.startswith('sqlite'):
        # SQLite için özel ayarlar
        engine = create_async_engine(db_url, echo=True, future=True)
    else:
        # Diğer veritabanları için
        engine = create_async_engine(db_url, echo=True, future=True)
    
    # Tablolar listesi
    table_classes = {
        'users': User,
        'documents': Document,
        'api_keys': ApiKeyDB,
        'security_logs': SecurityLogDB
    }
    
    if target_table:
        if target_table in table_classes:
            print(f"'{target_table}' tablosu için migration başlıyor...")
            await migrate_specific_table(engine, table_classes[target_table])
        else:
            print(f"Hata: '{target_table}' geçerli bir tablo adı değil.")
            print(f"Geçerli tablolar: {', '.join(table_classes.keys())}")
    else:
        print("Tüm tablolar için migration başlıyor...")
        await create_tables(engine)
    
    await engine.dispose()

def main():
    parser = argparse.ArgumentParser(description='Veritabanı Migration Aracı')
    parser.add_argument('--db-url', required=True, help='Veritabanı URL (örn: sqlite+aiosqlite:///app.db)')
    parser.add_argument('--table', help='Sadece belirli bir tabloyu oluştur (boş bırakılırsa tüm tablolar)')
    args = parser.parse_args()
    
    # Desteklenen veritabanı türünü kontrol et
    db_dialect = args.db_url.split(':')[0].split('+')[0]
    if db_dialect not in SUPPORTED_DIALECTS:
        print(f"Hata: '{db_dialect}' desteklenmeyen bir veritabanı türü.")
        print(f"Desteklenen türler: {', '.join(SUPPORTED_DIALECTS)}")
        return
    
    # Migration başlat
    asyncio.run(run_migration(args.db_url, args.table))

if __name__ == "__main__":
    main()