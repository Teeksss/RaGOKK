# Last reviewed: 2025-04-29 12:51:02 UTC (User: TeeksssCI/CD)
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import time
from contextlib import asynccontextmanager
import os
import logging

# OpenAPI ve Swagger için
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from fastapi.openapi.utils import get_openapi

# API routers
from .api.v1 import (
    auth,
    documents,
    users,
    search,
    processing,
    analytics,
    admin
)

# Middleware ve util
from .middleware.security import setup_security_middleware
from .middleware.rate_limiter import AdvancedRateLimiter
from .config import settings

# Services
from .services.user_behavior_analytics import UserBehaviorAnalytics
from .services.vector_service import VectorService

logger = logging.getLogger(__name__)

# Uygulama başlangıç ve bitiş işlemleri için context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Uygulama başlangıcı
    logger.info("Starting up application...")
    
    # Servisler başlat
    user_analytics = UserBehaviorAnalytics()
    await user_analytics.start()
    app.state.user_analytics = user_analytics
    
    # Vector servisini bağla
    vector_service = VectorService()
    await vector_service.connect()
    app.state.vector_service = vector_service
    
    yield  # Uygulama çalışması
    
    # Uygulama kapanışı
    logger.info("Shutting down application...")
    
    # Servisleri kapat
    await user_analytics.stop()
    await vector_service.disconnect()
    
    logger.info("Application shutdown complete")

# FastAPI app
app = FastAPI(
    title="RAG Base API",
    description="API for the RAG Base document management and search system",
    version="1.0.0",
    lifespan=lifespan,
    # Swagger ve ReDoc'u devre dışı bırak (özel yollarla sağlanacak)
    docs_url=None,
    redoc_url=None
)

# CORS ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Güvenlik ayarları
from .middleware.security import SecurityConfig, SecurityPolicyType
security_config = SecurityConfig.from_policy(SecurityPolicyType.MODERATE)
app = setup_security_middleware(app, security_config)

# Rate limiting
app.add_middleware(
    AdvancedRateLimiter,
    rules={
        "/api/documents/upload": AdvancedRateLimiter.create_rule(10, 60),  # dakikada 10 upload
        "/api/auth/*": AdvancedRateLimiter.create_rule(30, 60),  # dakikada 30 auth isteği
        "/api/search/*": AdvancedRateLimiter.create_rule(60, 60),  # dakikada 60 arama
    },
    default_rule=AdvancedRateLimiter.create_rule(100, 60)  # dakikada 100 varsayılan
)

# İstek işleme süresi middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# API router'ları
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(users.router)
app.include_router(search.router)
app.include_router(processing.router)
app.include_router(analytics.router)
app.include_router(admin.router)

# Sağlık kontrolü endpoint
@app.get("/api/health", tags=["health"])
async def health_check():
    return {"status": "ok", "version": app.version}

# Statik dosyalar (Swagger UI JavaScript dosyaları için)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Özelleştirilmiş OpenAPI şeması
def custom_openapi():