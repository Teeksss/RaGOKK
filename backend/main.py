# Last reviewed: 2025-04-29 13:14:42 UTC (User: TeeksssAPI)
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
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
from .api.openapi import custom_openapi

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
app.openapi = lambda: custom_openapi(app)

# Swagger UI
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
        swagger_favicon_url="/static/favicon.png",
    )

# Swagger OAuth redirect
@app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
async def swagger_ui_redirect():
    return get_swagger_ui_oauth2_redirect_html()

# ReDoc
@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="/static/redoc.standalone.js",
        redoc_favicon_url="/static/favicon.png",
    )

# OpenAPI JSON
@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_json():
    return JSONResponse(content=app.openapi())

# API dokümantasyon ana sayfası
@app.get("/api", response_class=HTMLResponse, include_in_schema=False)
async def api_documentation():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>RAG Base API Documentation</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }
            h1 {
                border-bottom: 1px solid #eaecef;
                padding-bottom: 10px;
            }
            .card {
                border: 1px solid #e1e4e8;
                border-radius: 6px;
                padding: 20px;
                margin: 20px 0;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
            }
            .card h2 {
                margin-top: 0;
            }
            a {
                color: #0366d6;
                text-decoration: none;
            }
            a:hover {
                text-decoration: underline;
            }
            .button {
                display: inline-block;
                padding: 8px 16px;
                background-color: #0366d6;
                color: white;
                border-radius: 4px;
                margin-right: 10px;
                margin-bottom: 10px;
            }
            .button:hover {
                background-color: #0255b3;
                text-decoration: none;
            }
            footer {
                border-top: 1px solid #eaecef;
                margin-top: 30px;
                padding-top: 20px;
                color: #6a737d;
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        <h1>RAG Base API Documentation</h1>
        
        <p>Welcome to the API documentation for RAG Base, a document management and search system.</p>
        
        <div class="card">
            <h2>Interactive Documentation</h2>
            <p>Explore the API using our interactive documentation tools:</p>
            <a href="/docs" class="button">Swagger UI</a>
            <a href="/redoc" class="button">ReDoc</a>
        </div>
        
        <div class="card">
            <h2>API Specification</h2>
            <p>Download the OpenAPI specification:</p>
            <a href="/openapi.json" class="button">OpenAPI JSON</a>
        </div>
        
        <div class="card">
            <h2>Getting Started</h2>
            <p>To use the API, you need to authenticate using one of the following methods:</p>
            <ul>
                <li>JWT Bearer Token (for web applications)</li>
                <li>API Key (for server-to-server integration)</li>
            </ul>
            <p>Check the <a href="/docs">API documentation</a> for more details.</p>
        </div>
        
        <footer>
            <p>© 2025 RAG Base. All rights reserved.</p>
            <p>For support, contact <a href="mailto:support@ragbase.example.com">support@ragbase.example.com</a></p>
        </footer>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)