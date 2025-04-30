# Last reviewed: 2025-04-30 05:22:47 UTC (User: Teeksss)
from typing import Any, Dict, Optional, List, Union
from fastapi import HTTPException, status
from pydantic import BaseModel, Field, validator
import logging
import traceback
import sys
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class ErrorDetail(BaseModel):
    """Hata detayları modeli"""
    loc: Optional[List[str]] = Field(None, description="Hatanın konumu")
    msg: str = Field(..., description="Hata mesajı")
    type: str = Field(..., description="Hata türü")
    code: Optional[str] = Field(None, description="Hata kodu")
    ctx: Optional[Dict[str, Any]] = Field(None, description="Ek hata bağlamı")

class ErrorResponse(BaseModel):
    """Standart hata yanıtı"""
    status_code: int = Field(..., description="HTTP durum kodu")
    message: str = Field(..., description="Ana hata mesajı")
    detail: Optional[Union[str, List[ErrorDetail]]] = Field(None, description="Hata detayları")
    error_code: Optional[str] = Field(None, description="Uygulama hata kodu")
    error_type: Optional[str] = Field(None, description="Hata türü")
    timestamp: str = Field(..., description="Hata zamanı (ISO 8601)")
    path: Optional[str] = Field(None, description="Hata oluşan yol")
    trace_id: Optional[str] = Field(None, description="Benzersiz izleme kimliği")

# Uygulama hata türleri
class ErrorType:
    """Uygulama hata türleri"""
    VALIDATION_ERROR = "validation_error"
    DATABASE_ERROR = "database_error"  
    AUTHENTICATION_ERROR = "authentication_error"
    PERMISSION_ERROR = "permission_error"
    NOT_FOUND_ERROR = "not_found_error"
    CONFLICT_ERROR = "conflict_error"
    EXTERNAL_SERVICE_ERROR = "external_service_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    INTERNAL_ERROR = "internal_error"
    BUSINESS_LOGIC_ERROR = "business_logic_error"
    INPUT_ERROR = "input_error"
    FILE_ERROR = "file_error"

# Uygulama hata kodları
class ErrorCode:
    """Uygulama hata kodları"""
    # Doğrulama hataları (1000-1999)
    INVALID_INPUT = "ERR_1000"
    MISSING_REQUIRED_FIELD = "ERR_1001"
    INVALID_FORMAT = "ERR_1002"
    VALUE_OUT_OF_RANGE = "ERR_1003"
    INVALID_RELATION = "ERR_1004"
    
    # Kimlik doğrulama hataları (2000-2999)
    INVALID_CREDENTIALS = "ERR_2000"
    EXPIRED_TOKEN = "ERR_2001"
    INVALID_TOKEN = "ERR_2002"
    ACCOUNT_DISABLED = "ERR_2003"
    ACCOUNT_LOCKED = "ERR_2004"
    INSUFFICIENT_PRIVILEGES = "ERR_2005"
    
    # Veritabanı hataları (3000-3999)
    DATABASE_CONNECTION_ERROR = "ERR_3000"
    QUERY_ERROR = "ERR_3001"
    INTEGRITY_ERROR = "ERR_3002"
    TRANSACTION_ERROR = "ERR_3003"
    
    # Kaynak hataları (4000-4999)
    RESOURCE_NOT_FOUND = "ERR_4000"
    RESOURCE_ALREADY_EXISTS = "ERR_4001"
    RESOURCE_LOCKED = "ERR_4002"
    
    # Dış servis hataları (5000-5999)
    EXTERNAL_SERVICE_UNAVAILABLE = "ERR_5000"
    EXTERNAL_SERVICE_TIMEOUT = "ERR_5001"
    EXTERNAL_SERVICE_ERROR = "ERR_5002"
    
    # Dosya işleme hataları (6000-6999)
    FILE_TOO_LARGE = "ERR_6000"
    INVALID_FILE_TYPE = "ERR_6001"
    FILE_UPLOAD_ERROR = "ERR_6002"
    FILE_DOWNLOAD_ERROR = "ERR_6003"
    
    # İş mantığı hataları (7000-7999)
    BUSINESS_RULE_VIOLATION = "ERR_7000"
    QUOTA_EXCEEDED = "ERR_7001"
    RATE_LIMIT_EXCEEDED = "ERR_7002"
    OPERATION_NOT_ALLOWED = "ERR_7003"
    
    # Sistem hataları (9000-9999)
    INTERNAL_SERVER_ERROR = "ERR_9000"
    SERVICE_UNAVAILABLE = "ERR_9001"
    NOT_IMPLEMENTED = "ERR_9002"
    CONFIGURATION_ERROR = "ERR_9003"

class BaseAppException(Exception):
    """
    Uygulama için temel özel istisna
    
    Bu sınıf, projedeki tüm özel istisnaların temelini oluşturur.
    Uygulama genelinde tutarlı hata işleme sağlar.
    """
    def __init__(
        self, 
        message: str, 
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None,
        error_type: Optional[str] = None,
        detail: Optional[Union[str, List[Dict[str, Any]]]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or ErrorCode.INTERNAL_SERVER_ERROR
        self.error_type = error_type or ErrorType.INTERNAL_ERROR
        self.detail = detail
        self.headers = headers
        self.trace_id = str(uuid.uuid4())
        self.timestamp = datetime.now(timezone.utc).isoformat()
        super().__init__(self.message)
    
    def to_http_exception(self) -> HTTPException:
        """
        FastAPI HTTP istisna nesnesine dönüştür
        """
        return HTTPException(
            status_code=self.status_code,
            detail={
                "message": self.message,
                "error_code": self.error_code,
                "error_type": self.error_type,
                "detail": self.detail,
                "trace_id": self.trace_id,
                "timestamp": self.timestamp
            },
            headers=self.headers
        )

class ValidationError(BaseAppException):
    """Doğrulama hatası"""
    def __init__(
        self, 
        message: str = "Validation error occurred", 
        detail: Optional[Union[str, List[Dict[str, Any]]]] = None,
        error_code: str = ErrorCode.INVALID_INPUT
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code=error_code,
            error_type=ErrorType.VALIDATION_ERROR,
            detail=detail
        )

class DatabaseError(BaseAppException):
    """Veritabanı hatası"""
    def __init__(
        self, 
        message: str = "Database error occurred", 
        detail: Optional[Union[str, List[Dict[str, Any]]]] = None,
        error_code: str = ErrorCode.DATABASE_CONNECTION_ERROR
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=error_code,
            error_type=ErrorType.DATABASE_ERROR,
            detail=detail
        )

class AuthenticationError(BaseAppException):
    """Kimlik doğrulama hatası"""
    def __init__(
        self, 
        message: str = "Authentication error occurred", 
        detail: Optional[Union[str, List[Dict[str, Any]]]] = None,
        error_code: str = ErrorCode.INVALID_CREDENTIALS,
        headers: Dict[str, str] = {"WWW-Authenticate": "Bearer"}
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=error_code,
            error_type=ErrorType.AUTHENTICATION_ERROR,
            detail=detail,
            headers=headers
        )

class PermissionError(BaseAppException):
    """İzin hatası"""
    def __init__(
        self, 
        message: str = "Permission denied", 
        detail: Optional[Union[str, List[Dict[str, Any]]]] = None,
        error_code: str = ErrorCode.INSUFFICIENT_PRIVILEGES
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code=error_code,
            error_type=ErrorType.PERMISSION_ERROR,
            detail=detail
        )

class NotFoundError(BaseAppException):
    """Kaynak bulunamadı hatası"""
    def __init__(
        self, 
        message: str = "Resource not found", 
        detail: Optional[Union[str, List[Dict[str, Any]]]] = None,
        error_code: str = ErrorCode.RESOURCE_NOT_FOUND
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=error_code,
            error_type=ErrorType.NOT_FOUND_ERROR,
            detail=detail
        )

class ConflictError(BaseAppException):
    """Çakışma hatası"""
    def __init__(
        self, 
        message: str = "Resource conflict", 
        detail: Optional[Union[str, List[Dict[str, Any]]]] = None,
        error_code: str = ErrorCode.RESOURCE_ALREADY_EXISTS
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code=error_code,
            error_type=ErrorType.CONFLICT_ERROR,
            detail=detail
        )

class ExternalServiceError(BaseAppException):
    """Dış servis hatası"""
    def __init__(
        self, 
        message: str = "External service error", 
        detail: Optional[Union[str, List[Dict[str, Any]]]] = None,
        error_code: str = ErrorCode.EXTERNAL_SERVICE_ERROR
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code=error_code,
            error_type=ErrorType.EXTERNAL_SERVICE_ERROR,
            detail=detail
        )

class RateLimitError(BaseAppException):
    """Hız sınırlama hatası"""
    def __init__(
        self, 
        message: str = "Rate limit exceeded", 
        detail: Optional[Union[str, List[Dict[str, Any]]]] = None,
        error_code: str = ErrorCode.RATE_LIMIT_EXCEEDED
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code=error_code,
            error_type=ErrorType.RATE_LIMIT_ERROR,
            detail=detail
        )

class BusinessLogicError(BaseAppException):
    """İş mantığı hatası"""
    def __init__(
        self, 
        message: str = "Business rule violation", 
        detail: Optional[Union[str, List[Dict[str, Any]]]] = None,
        error_code: str = ErrorCode.BUSINESS_RULE_VIOLATION
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=error_code,
            error_type=ErrorType.BUSINESS_LOGIC_ERROR,
            detail=detail
        )

class FileError(BaseAppException):
    """Dosya işleme hatası"""
    def __init__(
        self, 
        message: str = "File processing error", 
        detail: Optional[Union[str, List[Dict[str, Any]]]] = None,
        error_code: str = ErrorCode.FILE_UPLOAD_ERROR
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=error_code,
            error_type=ErrorType.FILE_ERROR,
            detail=detail
        )