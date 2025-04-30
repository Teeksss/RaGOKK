# Last reviewed: 2025-04-30 08:31:26 UTC (User: Teeksss)
import os
from fastapi import FastAPI, Request, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from fastapi_sessions.session_middleware import SessionMiddleware
import uvicorn
import logging
import time
from typing import Dict, Any

# Middleware
from backend.middleware.rate_limiter import RateLimiterMiddleware

# API Routes
from backend.api.v1 import (
    auth, 
    auth2fa,
    documents, 
    queries, 
    document_versions, 
    document_summary, 
    qa_generation, 
    users, 
    admin,
    streaming,
    multimodal,
    monitoring
)

# Dependency
from backend.db.session import get_db
from backend.auth.enhanced_jwt import get_current_user_enhanced
from backend.models import Base
from backend.core.config import settings
from backend.core.monitoring import MonitoringService

# Logger configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Monitoring service
monitoring_service = MonitoringService()

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="RAG Base API",
    version="1.0.0",
    docs_url=None,  # Custom docs URL
    redoc_url=None   # Custom redoc URL
)

# CORS settings
origins = [
    "http://localhost",
    "http://localhost:3000",  # React frontend
    "http://localhost:8000",
    "https://app.ragbase.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware for 2FA flow
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="session",
    max_age=3600,  # 1 hour
)

# Rate limiter middleware
app.add_middleware(RateLimiterMiddleware)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Request duration tracking middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    
    try:
        response = await call_next(request)
        
        # Request süresi (ms)
        process_time = (time.time() - start_time) * 1000
        response.headers["X-Process-Time"] = str(process_time)
        
        # Monitoring için metrik kaydet
        if monitoring_service:
            is_error = 400 <= response.status_code < 600
            monitoring_service.track_api_request(
                path=request.url.path, 
                duration_ms=process_time,
                is_error=is_error
            )
            
        return response
    except Exception as e:
        # Hata durumunda monitoring için kaydet
        if monitoring_service:
            process_time = (time.time() - start_time) * 1000
            monitoring_service.track_api_request(
                path=request.url.path, 
                duration_ms=process_time,
                is_error=True
            )
        raise e

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if monitoring_service:
        health = await monitoring_service.get_health_status()
        return {
            "status": "ok",
            "health": health,
            "version": settings.VERSION
        }
    return {"status": "ok", "version": settings.VERSION}

# Custom docs endpoints with authentication
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user_enhanced)
):
    """Custom Swagger UI with authentication"""
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
    )

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    # Monitoring için API hata metrikleri kaydet
    if monitoring_service:
        monitoring_service.track_api_request(
            path=request.url.path, 
            duration_ms=0,  # Süreyi bilmiyoruz
            is_error=True
        )
    
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."}
    )

# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(auth2fa.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(document_versions.router, prefix="/api/v1")
app.include_router(document_summary.router, prefix="/api/v1")
app.include_router(qa_generation.router, prefix="/api/v1")
app.include_router(queries.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(streaming.router, prefix="/api/v1")
app.include_router(multimodal.router, prefix="/api/v1")
app.include_router(monitoring.router, prefix="/api/v1")

# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup: connect to DB, initialize components"""
    logger.info("Starting RAG Base API")
    
    # Monitoring servisini başlat
    logger.info("Starting monitoring service")
    await monitoring_service.start_monitoring()
    monitoring_service.register_custom_metric("system.startup_time", time.time())

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown: close resources"""
    logger.info("Shutting down RAG Base API")
    
    # Monitoring servisini durdur
    logger.info("Stopping monitoring service")
    await monitoring_service.stop_monitoring()

if __name__ == "__main__":
    """Run the API server"""
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=settings.DEBUG
    )