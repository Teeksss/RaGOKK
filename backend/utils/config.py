# Last reviewed: 2025-04-29 10:51:12 UTC (User: TeeksssPrioritizationTest.js)
import os
from typing import Dict, List, Union, Optional, Any

# API anahtarları
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
COHERE_API_KEY = os.getenv("COHERE_API_KEY", "")
JINA_API_KEY = os.getenv("JINA_API_KEY", "")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY", "")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
TWITTER_CLIENT_ID = os.getenv("TWITTER_CLIENT_ID", "")
TWITTER_CLIENT_SECRET = os.getenv("TWITTER_CLIENT_SECRET", "")

# Elasticsearch bağlantı ayarları
ES_HOST = os.getenv("ES_HOST", "localhost")
ES_PORT = int(os.getenv("ES_PORT", "9200"))
ES_USER = os.getenv("ES_USER", "")
ES_PASSWORD = os.getenv("ES_PASSWORD", "")
ES_USE_SSL = os.getenv("ES_USE_SSL", "false").lower() == "true"
ES_VERIFY_CERTS = os.getenv("ES_VERIFY_CERTS", "true").lower() == "true"
ES_TIMEOUT = int(os.getenv("ES_TIMEOUT", "30"))

# Index ayarları
INDEX_NAME = os.getenv("INDEX_NAME", "documents")
VECTOR_DIMENSION = int(os.getenv("VECTOR_DIMENSION", "384"))

# KNN ayarları
ES_KNN_K = int(os.getenv("ES_KNN_K", "10"))
ES_KNN_K_MULTIPLIER = int(os.getenv("ES_KNN_K_MULTIPLIER", "5"))
ES_KNN_NUM_CANDIDATES = int(os.getenv("ES_KNN_NUM_CANDIDATES", "100"))
ES_SEARCH_TIMEOUT = os.getenv("ES_SEARCH_TIMEOUT", "30s")

# Hybrid search ayarları
BM25_BOOST = float(os.getenv("BM25_BOOST", "0.5"))
SEMANTIC_BOOST = float(os.getenv("SEMANTIC_BOOST", "0.5"))
HYBRID_METHOD = os.getenv("HYBRID_METHOD", "rank_fusion")  # rank_fusion, rrf, linear_combination
TIMEFILTER_ENABLED = os.getenv("TIMEFILTER_ENABLED", "true").lower() == "true"

# Top-K Expansion ayarları
MAX_DOCUMENT_SIZE = int(os.getenv("MAX_DOCUMENT_SIZE", "10000"))
TOP_K_EXPANSION_DEPTH = int(os.getenv("TOP_K_EXPANSION_DEPTH", "1"))
PERSONALIZATION_WEIGHT = float(os.getenv("PERSONALIZATION_WEIGHT", "1.2"))

# Query expansion ve dil ayarları
QUERY_EXPANSION_ENABLED = os.getenv("QUERY_EXPANSION_ENABLED", "true").lower() == "true"
QUERY_EXPANSION_LANGUAGES = os.getenv("QUERY_EXPANSION_LANGUAGES", "en,tr").split(",")
QUERY_EXPANSION_EXTERNAL_API = os.getenv("QUERY_EXPANSION_EXTERNAL_API", "none")  # none, wordnet, nlp_api
MULTILINGUAL_EMBEDDINGS_MODEL = os.getenv("MULTILINGUAL_EMBEDDINGS_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# TF-IDF ve BM25 ayarları
TFIDF_NORM = os.getenv("TFIDF_NORM", "l2")
TFIDF_USE_IDF = os.getenv("TFIDF_USE_IDF", "true").lower() == "true"
BM25_K1 = float(os.getenv("BM25_K1", "1.2"))
BM25_B = float(os.getenv("BM25_B", "0.75"))
BM25_DELTA = float(os.getenv("BM25_DELTA", "0.0"))

# Önceliklendirme algoritması ayarları
PRIORITY_CORPORATE_DOCS = float(os.getenv("PRIORITY_CORPORATE_DOCS", "1.5"))
PRIORITY_RECENT_DOCS = float(os.getenv("PRIORITY_RECENT_DOCS", "1.3"))
PRIORITY_REVIEWED_DOCS = float(os.getenv("PRIORITY_REVIEWED_DOCS", "1.2"))
PRIORITY_DOMAINS = os.getenv("PRIORITY_DOMAINS", "company.com,internal.company.com,docs.company.com").split(",")

# Email konfigürasyonu
EMAIL_SMTP_HOST = os.getenv("EMAIL_SMTP_HOST", "")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))
EMAIL_SMTP_USER = os.getenv("EMAIL_SMTP_USER", "")
EMAIL_SMTP_PASSWORD = os.getenv("EMAIL_SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "")

# Secret key ve JWT ayarları
SECRET_KEY = os.getenv("SECRET_KEY", "")
JWT_SECRET = os.getenv("JWT_SECRET", SECRET_KEY)
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# Webhook ayarları
def parse_webhook_urls() -> Dict[str, List[str]]:
    """
    WEBHOOK_URLS çevre değişkenini ayrıştırır.
    
    Format:
    event_type1:url1,url2;event_type2:url3,url4
    
    Örnek:
    api_key_change:https://hooks.example.com/api-keys,https://slack.example.com/api-keys;security_event:https://hooks.example.com/security
    
    Returns:
        Dict[str, List[str]]: {event_type: [url1, url2, ...], ...}
    """
    webhook_urls = {}
    webhook_config = os.getenv("WEBHOOK_URLS", "")
    
    if not webhook_config:
        return {}
    
    try:
        # Event tiplerini noktalı virgül ile ayır
        event_configs = webhook_config.split(";")
        
        for event_config in event_configs:
            if ":" not in event_config:
                continue
                
            event_type, urls_str = event_config.split(":", 1)
            event_type = event_type.strip()
            
            # URL'leri virgülle ayır
            urls = [url.strip() for url in urls_str.split(",") if url.strip()]
            
            if event_type and urls:
                webhook_urls[event_type] = urls
                
        return webhook_urls
    except Exception:
        return {}

WEBHOOK_URLS = parse_webhook_urls()

# Weaviate konfigürasyonu
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "")