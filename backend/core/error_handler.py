# Last reviewed: 2025-04-30 05:22:47 UTC (User: Teeksss)
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
import logging
import traceback
import json
import sys
from datetime import datetime, timezone
import uuid

from .exceptions import (
    BaseAppException, ErrorCode, ErrorType, ValidationError, 
    DatabaseError, NotFoundError, ConflictError
)

logger = logging.getLogger(__name__)

async def app_exception_handler(request: Request, exc: BaseAppException):
    """
    Özel uygulama istisnalarını işler
    """
    # Detaylı hata günlüğü
    logger.error(
        f"Application Error [{exc.error_code}]: {exc.message}\n"
        f"Request path: {request.url.path}\n"
        f"Trace ID: {exc.trace_id}\n"
        f"Details: {exc.detail}"
    )
    
    # JSON yanıt hazırla
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status_code": exc.status_code,
            "message": exc.message,
            "error_code": exc.error_code,
            "error_type": exc.error_type,
            "detail": exc.detail,
            "timestamp": exc.timestamp,
            "path": request.url.path,
            "trace_id": exc.trace_id
        },
        headers=exc.headers or {}
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Pydantic doğrulama hatalarını işler
    """
    trace_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Hata detaylarını hazırla
    error_details = []
    for error in exc.errors():
        error_details.append({
            "loc": error.get("loc", []),
            "msg": error.get("msg", ""),
            "type": error.get("type", ""),
            "ctx": error.get("ctx")
        })
    
    # Detaylı hata günlüğü
    logger.error(
        f"Validation Error: {str(exc)}\n"
        f"Request path: {request.url.path}\n"
        f"Trace ID: {trace_id}\n"
        f"Details: {error_details}"
    )
    
    # JSON yanıt hazırla
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "message": "Validation error",
            "error_code": ErrorCode.INVALID_INPUT,
            "error_type": ErrorType.VALIDATION_ERROR,
            "detail": error_details,
            "timestamp": timestamp,
            "path": request.url.path,
            "trace_id": trace_id
        }
    )

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    HTTP istisnalarını işler
    """
    trace_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Hata detayı
    detail = exc.detail
    error_code = ErrorCode.INTERNAL_SERVER_ERROR
    error_type = ErrorType.INTERNAL_ERROR
    
    # Hata kodunu ve tipini belirle
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        error_code = ErrorCode.RESOURCE_NOT_FOUND
        error_type = ErrorType.NOT_FOUND_ERROR
    elif exc.status_code == status.HTTP_401_UNAUTHORIZED:
        error_code = ErrorCode.INVALID_CREDENTIALS
        error_type = ErrorType.AUTHENTICATION_ERROR
    elif exc.status_code == status.HTTP_403_FORBIDDEN:
        error_code = ErrorCode.INSUFFICIENT_PRIVILEGES
        error_type = ErrorType.PERMISSION_ERROR
    elif exc.status_code == status.HTTP_409_CONFLICT:
        error_code = ErrorCode.RESOURCE_ALREADY_EXISTS
        error_type = ErrorType.CONFLICT_ERROR
    elif exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        error_code = ErrorCode.RATE_LIMIT_EXCEEDED
        error_type = ErrorType.RATE_LIMIT_ERROR
    
    # Detaylı hata günlüğü
    logger.error(
        f"HTTP Error {exc.status_code}: {str(exc.detail)}\n"
        f"Request path: {request.url.path}\n"
        f"Trace ID: {trace_id}"
    )
    
    # Eğer detail bir sözlük ise ve ek bilgiler içeriyorsa
    if isinstance(detail, dict) and "error_code" in detail:
        error_code = detail.get("error_code", error_code)
        error_type = detail.get("error_type", error_type)
        message = detail.get("message", str(detail))
        detail = detail.get("detail", None)
    else:
        message = str(detail)
    
    # JSON yanıt hazırla
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status_code": exc.status_code,
            "message": message,
            "error_code": error_code,
            "error_type": error_type,
            "detail": detail,
            "timestamp": timestamp,
            "path": request.url.path,
            "trace_id": trace_id
        },
        headers=exc.headers or {}
    )

async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """
    SQLAlchemy veritabanı hatalarını işler
    """
    trace_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Hata tipine göre mesaj ve kod belirle
    if isinstance(exc, IntegrityError):
        error_code = ErrorCode.INTEGRITY_ERROR
        status_code = status.HTTP_409_CONFLICT
        if "unique constraint" in str(exc).lower():
            message = "A resource with the same unique identifier already exists"
        else:
            message = "Database integrity constraint violation"
    elif isinstance(exc, OperationalError):
        error_code = ErrorCode.DATABASE_CONNECTION_ERROR
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        message = "Database connection error"
    else:
        error_code = ErrorCode.QUERY_ERROR
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        message = "Database error occurred"
    
    # Detaylı hata günlüğü
    logger.error(
        f"Database Error: {message}\n"
        f"Exception: {str(exc)}\n"
        f"Request path: {request.url.path}\n"
        f"Trace ID: {trace_id}\n"
        f"Traceback: {traceback.format_exc()}"
    )
    
    # JSON yanıt hazırla
    return JSONResponse(
        status_code=status_code,
        content={
            "status_code": status_code,
            "message": message,
            "error_code": error_code,
            "error_type": ErrorType.DATABASE_ERROR,
            "timestamp": timestamp,
            "path": request.url.path,
            "trace_id": trace_id
        }
    )

async def general_exception_handler(request: Request, exc: Exception):
    """
    Genel istisnaları işler
    """
    trace_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Detaylı hata günlüğü
    logger.error(
        f"Unhandled Exception: {str(exc)}\n"
        f"Request path: {request.url.path}\n"
        f"Trace ID: {trace_id}\n"
        f"Traceback: {traceback.format_exc()}"
    )
    
    # JSON yanıt hazırla
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "message": "Internal server error",
            "error_code": ErrorCode.INTERNAL_SERVER_ERROR,
            "error_type": ErrorType.INTERNAL_ERROR,
            "timestamp": timestamp,
            "path": request.url.path,
            "trace_id": trace_id
        }
    )

def register_exception_handlers(app):
    """
    Tüm istisna işleyicilerini kaydeder
    """
    app.add_exception_handler(BaseAppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("Exception handlers registered")