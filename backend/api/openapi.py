# Last reviewed: 2025-04-29 13:14:42 UTC (User: TeeksssAPI)
from fastapi.openapi.utils import get_openapi
from fastapi import FastAPI
import json
from pathlib import Path

def custom_openapi(app: FastAPI, title: str = "RAG Base API", version: str = "1.0.0"):
    """
    Özelleştirilmiş OpenAPI şeması oluşturur.

    Args:
        app: FastAPI uygulaması
        title: API başlığı
        version: API sürümü

    Returns:
        dict: OpenAPI şeması
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=title,
        version=version,
        description="RAG Base Dokümantasyon Yönetim ve Arama Sistemi API'si",
        routes=app.routes,
    )

    # API bilgilerini ekle
    openapi_schema["info"]["contact"] = {
        "name": "RAG Base Support",
        "url": "https://ragbase.example.com/support",
        "email": "support@ragbase.example.com",
    }
    
    openapi_schema["info"]["license"] = {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    }

    # Server bilgilerini ekle
    openapi_schema["servers"] = [
        {
            "url": "/api",
            "description": "Geliştirme API"
        },
        {
            "url": "https://api.ragbase.example.com",
            "description": "Production API"
        }
    ]

    # Güvenlik şemalarını ekle
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        },
        "apiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
        }
    }

    # Global güvenlik gereksinimleri
    openapi_schema["security"] = [
        {"bearerAuth": []}
    ]

    # Dokümantasyonu JSON dosyasına kaydet
    if app.debug:
        Path("static/openapi").mkdir(parents=True, exist_ok=True)
        with open("static/openapi/openapi.json", "w") as f:
            json.dump(openapi_schema, f, indent=2)

    app.openapi_schema = openapi_schema
    return app.openapi_schema