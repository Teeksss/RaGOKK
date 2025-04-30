# Last reviewed: 2025-04-30 05:03:25 UTC (User: Teeksss)
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, timedelta, timezone
import json
import pandas as pd
import numpy as np
from sqlalchemy import text, func, desc, and_, or_, select, join, case
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import User
from ..models.document import Document
from ..models.audit import AuditLog
from ..schemas.analytics import (
    AnalyticsTimeRange, 
    UserActivityReport, 
    DocumentAnalytics,
    QueryAnalytics,
    SystemUsageReport,
    AnalyticsExportFormat
)
from ..services.audit_service import AuditLogType
from ..repositories.user_repository import UserRepository
from ..repositories.document_repository import DocumentRepository
from ..repositories.query_repository import QueryRepository

logger = logging.getLogger(__name__)

class AnalyticsService:
    """
    Raporlama ve analitik servisi
    
    Bu servis şunları sağlar:
    - Kullanıcı etkinlik analizleri
    - Belge kullanım istatistikleri
    - Sistem performans metrikleri
    - Sorgu başarı oranları ve istatistikleri
    - Verilerin CSV/Excel/JSON formatlarında dışa aktarımı
    """
    
    def __init__(self):
        """Analytics servisi başlat"""
        self.user_repository = UserRepository()
        self.document_repository = DocumentRepository()
        self.query_repository = QueryRepository()
        
        # Analiz ayarları
        self.default_limit = 100
        self.default_time_range = AnalyticsTimeRange.LAST_30_DAYS
        
        # Zaman aralığı eşleştirmeleri
        self.time_range_mapping = {
            AnalyticsTimeRange.TODAY: self._get_today_range,
            AnalyticsTimeRange.YESTERDAY: self._get_yesterday_range,
            AnalyticsTimeRange.LAST_7_DAYS: self._get_last_n_days_range(7),
            AnalyticsTimeRange.LAST_30_DAYS: self._get_last_n_days_range(30),
            AnalyticsTimeRange.THIS_MONTH: self._get_this_month_range,
            AnalyticsTimeRange.LAST_MONTH: self._get_last_month_range,
            AnalyticsTimeRange.THIS_QUARTER: self._get_this_quarter_range,
            AnalyticsTimeRange.LAST_QUARTER: self._get_last_quarter_range,
            AnalyticsTimeRange.THIS_YEAR: self._get_this_year_range
        }
    
    def _get_today_range(self) -> Tuple[datetime, datetime]:
        """Bugün için tarih aralığı"""
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        return today, tomorrow
    
    def _get_yesterday_range(self) -> Tuple[datetime, datetime]:
        """Dün için tarih aralığı"""
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        return yesterday, today
    
    def _get_last_n_days_range(self, days: int) -> callable:
        """Son N gün için tarih aralığı fonksiyonu oluşturma"""
        def get_range() -> Tuple[datetime, datetime]:
            end_date = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59, microsecond=999999)
            start_date = (end_date - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
            return start_date, end_date
        return get_range
    
    def _get_this_month_range(self) -> Tuple[datetime, datetime]:
        """Bu ay için tarih aralığı"""
        now = datetime.now(timezone.utc)
        start_date = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        if now.month == 12:
            end_date = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end_date = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
        return start_date, end_date
    
    def _get_last_month_range(self) -> Tuple[datetime, datetime]:
        """Geçen ay için tarih aralığı"""
        now = datetime.now(timezone.utc)
        if now.month == 1:
            start_date = datetime(now.year - 1, 12, 1, tzinfo=timezone.utc)
            end_date = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        else:
            start_date = datetime(now.year, now.month - 1, 1, tzinfo=timezone.utc)
            end_date = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        return start_date, end_date
    
    def _get_this_quarter_range(self) -> Tuple[datetime, datetime]:
        """Bu çeyrek için tarih aralığı"""
        now = datetime.now(timezone.utc)
        current_quarter = (now.month - 1) // 3 + 1
        start_month = 3 * (current_quarter - 1) + 1
        start_date = datetime(now.year, start_month, 1, tzinfo=timezone.utc)
        
        if current_quarter == 4:
            end_date = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end_date = datetime(now.year, start_month + 3, 1, tzinfo=timezone.utc)
        
        return start_date, end_date
    
    def _get_last_quarter_range(self) -> Tuple[datetime, datetime]:
        """Geçen çeyrek için tarih aralığı"""
        now = datetime.now(timezone.utc)
        current_quarter = (now.month - 1) // 3 + 1
        
        if current_quarter == 1:
            last_quarter = 4
            year = now.year - 1
        else:
            last_quarter = current_quarter - 1
            year = now.year
        
        start_month = 3 * (last_quarter - 1) + 1
        start_date = datetime(year, start_month, 1, tzinfo=timezone.utc)
        
        if last_quarter == 4:
            end_date = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end_date = datetime(year, start_month + 3, 1, tzinfo=timezone.utc)
        
        return start_date, end_date
    
    def _get_this_year_range(self) -> Tuple[datetime, datetime]:
        """Bu yıl için tarih aralığı"""
        now = datetime.now(timezone.utc)
        start_date = datetime(now.year, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
        return start_date, end_date
    
    def _get_date_range(self, time_range: Union[AnalyticsTimeRange, Tuple[datetime, datetime]]) -> Tuple[datetime, datetime]:
        """
        Belirtilen zaman aralığı için başlangıç ve bitiş tarihlerini al
        