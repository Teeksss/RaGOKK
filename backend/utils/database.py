# Last reviewed: 2025-04-29 08:07:22 UTC (User: TeeksssNative)
from elasticsearch import AsyncElasticsearch, ConnectionError as ESConnectionError
from typing import Dict, List, Optional, Any
import json
import time
from contextlib import asynccontextmanager

from .config import (
    ELASTICSEARCH_HOSTS, ELASTICSEARCH_USER, ELASTICSEARCH_PASSWORD,
    ES_CLIENT_MAX_SIZE, ES_CLIENT_TIMEOUT, ES_INDEX_SHARDS, 
    ES_INDEX_REPLICAS, ES_SEARCH_TIMEOUT, ES_KNN_K,
    ES_KNN_NUM_CANDIDATES, ES_BULK_SIZE
)
from .logger import get_logger

logger = get_logger(__name__)

es_client: Optional[AsyncElasticsearch] = None

def connect_elasticsearch():
    """Elasticsearch bağlantısını kurar."""
    global es_client
    if es_client:
        return
        
    logger.info(f"Elasticsearch'e bağlanılıyor: {', '.join(ELASTICSEARCH_HOSTS)}")
    
    http_auth = (ELASTICSEARCH_USER, ELASTICSEARCH_PASSWORD) if ELASTICSEARCH_USER and ELASTICSEARCH_PASSWORD else None
    
    try:
        # Havuz optimizasyonu ile ES istemcisi oluştur
        es_client = AsyncElasticsearch(
            hosts=ELASTICSEARCH_HOSTS,
            http_auth=http_auth,
            request_timeout=ES_CLIENT_TIMEOUT,
            max_retries=3,
            retry_on_timeout=True,
            connections_per_node=ES_CLIENT_MAX_SIZE,  # Bağlantı havuzu boyutu
            maxsize=ES_CLIENT_MAX_SIZE * len(ELASTICSEARCH_HOSTS),  # Toplam bağlantı sayısı
            sniff_on_start=True,  # Küme düğümlerini otomatik keşfet
            sniff_on_connection_fail=True,  # Bağlantı hatalarında keşfet
            sniff_timeout=1  # Keşif zaman aşımı
        )
        logger.info(f"AsyncElasticsearch istemcisi oluşturuldu (max_size: {ES_CLIENT_MAX_SIZE})")
    except Exception as e:
        logger.error(f"ES istemcisi oluşturulamadı: {e}", exc_info=True)
        es_client = None
        raise

async def close_elasticsearch():
    """Elasticsearch bağlantısını kapatır."""
    global es_client
    if es_client:
        logger.info("Elasticsearch bağlantısı kapatılıyor...")
        try:
            await es_client.close()
            logger.info("Elasticsearch bağlantısı kapatıldı")
        except Exception as e:
            logger.error(f"ES kapatma hatası: {e}", exc_info=True)
        finally:
            es_client = None

async def optimize_elasticsearch_index(index_name: str):
    """Elasticsearch indeksinin performansını optimize eder"""
    if not es_client:
        logger.error("Elasticsearch bağlantısı yok")
        return False
    
    try:
        # Force merge - segment consolidation
        logger.info(f"Force merge başlatılıyor: {index_name}")
        await es_client.indices.forcemerge(
            index=index_name,
            max_num_segments=1,  # Segment sayısını azalt
        )
        
        # Cache temizleme
        logger.info(f"Cache temizleniyor: {index_name}")
        await es_client.indices.clear_cache(
            index=index_name
        )
        
        # Refresh
        logger.info(f"Index refresh: {index_name}")
        await es_client.indices.refresh(
            index=index_name
        )
        
        # İstatistikleri logla
        stats = await es_client.indices.stats(index=index_name)
        logger.info(f"Index stats: {json.dumps(stats['_all']['primaries']['search'], indent=2)}")
        
        return True
    except Exception as e:
        logger.error(f"Index optimize etme hatası: {e}", exc_info=True)
        return False

@asynccontextmanager
async def bulk_helper(index_name: str, refresh: str = "wait_for"):
    """Elasticsearch bulk operasyonları için yardımcı context manager"""
    if not es_client:
        logger.error("Elasticsearch bağlantısı yok")
        raise ConnectionError("Elasticsearch bağlantısı yok")
    
    operations = []
    start_time = time.time()
    
    try:
        # Context içinde kullanılması için operations listesini yield et
        yield operations
        
        if operations:
            # Bulk indexleme yap
            success_count, errors = 0, []
            
            # ES_BULK_SIZE büyüklüğünde batch'ler halinde gönder
            for i in range(0, len(operations), ES_BULK_SIZE):
                batch = operations[i:i + ES_BULK_SIZE]
                response = await es_client.bulk(operations=batch, refresh=refresh)
                
                # Hataları işle
                if response.get("errors", False):
                    for item in response["items"]:
                        if "error" in item.get("index", {}):
                            errors.append(item["index"]["error"])
                        else:
                            success_count += 1
                else:
                    success_count += len(batch)
            
            elapsed = time.time() - start_time
            logger.info(f"Bulk indexleme tamamlandı - {success_count} başarılı, {len(errors)} hata, {elapsed:.2f} saniyede")
            
            if errors:
                first_errors = errors[:3]  # İlk birkaç hatayı logla
                logger.error(f"İlk indexleme hataları: {first_errors}")
    except Exception as e:
        logger.error(f"Bulk işlemi hatası: {e}", exc_info=True)
        raise

async def get_index_mapping(index_name: str) -> Dict:
    """Elasticsearch indeks mapping'ini döndürür"""
    if not es_client:
        logger.error("Elasticsearch bağlantısı yok")
        raise ConnectionError("Elasticsearch bağlantısı yok")
    
    try:
        mapping = await es_client.indices.get_mapping(index=index_name)
        return mapping
    except Exception as e:
        logger.error(f"Mapping alma hatası: {e}", exc_info=True)
        raise

async def get_index_settings(index_name: str) -> Dict:
    """Elasticsearch indeks ayarlarını döndürür"""
    if not es_client:
        logger.error("Elasticsearch bağlantısı yok")
        raise ConnectionError("Elasticsearch bağlantısı yok")
    
    try:
        settings = await es_client.indices.get_settings(index=index_name)
        return settings
    except Exception as e:
        logger.error(f"Settings alma hatası: {e}", exc_info=True)
        raise

async def create_optimized_index(index_name: str, mapping: Dict, settings: Optional[Dict] = None):
    """Optimize edilmiş ayarlarla Elasticsearch indeksi oluşturur"""
    if not es_client:
        logger.error("Elasticsearch bağlantısı yok")
        raise ConnectionError("Elasticsearch bağlantısı yok")
    
    try:
        # Index mevcut mu kontrol et
        exists = await es_client.indices.exists(index=index_name)
        if exists:
            logger.info(f"Index zaten mevcut: {index_name}")
            return True
        
        # Default settings
        default_settings = {
            "number_of_shards": ES_INDEX_SHARDS,
            "number_of_replicas": ES_INDEX_REPLICAS,
            "refresh_interval": "30s",  # Daha az refresh, daha iyi indexleme performansı
            "index.knn": True,  # KNN özelliğini aktifleştir
            "index.knn.space_type": "cosinesimil",  # Veya "l2" Euclidean distance için
            "analysis": {  # Text analizini özelleştir
                "analyzer": {
                    "default": {
                        "type": "standard",
                        "stopwords": "_english_"
                    }
                }
            }
        }
        
        # Özel ayarlar varsa birleştir
        if settings:
            # Nested dictionaries için recursive merge uygulamak daha iyi olur
            default_settings.update(settings)
        
        logger.info(f"'{index_name}' indeksi oluşturuluyor, settings: {json.dumps(default_settings)}")
        await es_client.indices.create(
            index=index_name,
            mappings=mapping,
            settings=default_settings
        )
        
        logger.info(f"Index oluşturuldu: {index_name}")
        return True
    except Exception as e:
        logger.error(f"Index oluşturma hatası: {e}", exc_info=True)
        raise