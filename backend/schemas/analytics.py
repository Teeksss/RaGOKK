# Last reviewed: 2025-04-30 05:13:15 UTC (User: TeeksssAnalitik)
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class AnalyticsTimeRange(str, Enum):
    """Analitik zaman aralığı seçenekleri"""
    TODAY = "today"
    YESTERDAY = "yesterday"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"
    THIS_QUARTER = "this_quarter"
    LAST_QUARTER = "last_quarter"
    THIS_YEAR = "this_year"

class AnalyticsExportFormat(str, Enum):
    """Analitik dışa aktarım formatları"""
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"

class TimeRangeInfo(BaseModel):
    """Zaman aralığı bilgisi"""
    start_date: str = Field(..., description="Başlangıç tarihi (ISO 8601)")
    end_date: str = Field(..., description="Bitiş tarihi (ISO 8601)")

class UserActivityItem(BaseModel):
    """Kullanıcı etkinlik bilgisi"""
    user_id: str
    email: str
    username: Optional[str] = None
    full_name: Optional[str] = None
    event_count: int

class DailyActivityItem(BaseModel):
    """Günlük etkinlik bilgisi"""
    date: str
    count: int

class EventTypeDistribution(BaseModel):
    """Etkinlik türü dağılımı"""
    type: str
    count: int

class UserActivityReport(BaseModel):
    """Kullanıcı etkinlik raporu"""
    total_logins: int = Field(..., description="Toplam oturum açma sayısı")
    active_users_count: int = Field(..., description="Aktif kullanıcı sayısı")
    total_users_count: int = Field(..., description="Toplam kayıtlı kullanıcı sayısı")
    active_users_percentage: float = Field(..., description="Aktif kullanıcı