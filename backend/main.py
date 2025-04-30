# Last reviewed: 2025-04-30 05:22:47 UTC (User: Teeksss)
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import logging

from .db.init_db import init_db
from .api.v1 import api_router
from .api.docs import docs_router
from .core.config import settings
from .core.error_handler import register_exception_handlers

# Temel uygulama örneği oluştur
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=None,
    redoc_url=None
)

# CORS middleware'ini ekle
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# İstisna işleyicileri kaydedilir
register_exception_handlers(app)

# API ve dokümantasyon yönlendiricilerini dahil et
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(docs_router)

# Başlangıç işlemi
@app.on_event("startup")
async def startup_event():
    # Veritabanını başlat
    await init_db()
    
    # Gerekli başlangıç ayarları
    logging.info("Application starting up")

# Kapatma işlemi
@app.on_event("shutdown")
async def shutdown_event():
    # Kaynakları serbest bırak
    logging.info("Application shutting down")

# Ana yol
@app.get("/")
def read_root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "description": settings.PROJECT_DESCRIPTION,
        "documentation": "/docs"
    }

# Sağlık kontrolü
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "version": settings.PROJECT_VERSION
    }