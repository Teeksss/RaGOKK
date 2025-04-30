# Last reviewed: 2025-04-30 05:13:15 UTC (User: TeeksssAnalitik)
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from ...db.session import get_db
from ...schemas.analytics import (
    AnalyticsTimeRange,
    UserActivityReport,
    DocumentAnalytics,
    QueryAnalytics,
    SystemUsageReport,
    AnalyticsExportFormat
)
from ...services.analytics_service import AnalyticsService
from ...services.audit_service import AuditService, AuditLogType
from ...auth.jwt import get_current_active_user
from ...auth.authorization import requires_permission

router = APIRouter(
    prefix="/api/analytics",
    tags=["analytics"],
    responses={401: {"description": "Unauthorized"}, 403: {"description": "Forbidden"}}
)

logger = logging.getLogger(__name__)
analytics_service = AnalyticsService()
audit_service = AuditService()

@router.get("/user-activity", response_model=UserActivityReport)
async def get_user_activity(
    time_range: Optional[AnalyticsTimeRange] = Query(AnalyticsTimeRange.LAST_30_DAYS, description="Time range for analytics"),
    organization_id: Optional[str] = Query(None, description="Filter by organization ID"),
    top_users_limit: int = Query(10, ge=1, le=100, description="Limit for top users"),
    current_user: Dict[str, Any] = Depends(
        requires_permission("analytics", "read", "user")
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Kullanıcı etkinlik raporu alır
    """
    try:
        # Organizasyon kontrolü - süper kullanıcı değilse kendi organizasyonuyla sınırla
        if not current_user.get("is_superuser") and organization_id != current_user.get("organization_id"):
            organization_id = current_user.get("organization_id")
        
        # Raporu oluştur
        report = await analytics_service.get_user_activity_report(
            db=db,
            organization_id=organization_id,
            time_range=time_range,
            top_users_limit=top_users_limit
        )
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.ACCESS,
            user_id=current_user["id"],
            action="read",
            resource_type="analytics",
            status="success",
            details={"report_type": "user_activity", "time_range": str(time_range), "organization_id": organization_id},
            db=db
        )
        
        return report
        
    except Exception as e:
        logger.error(f"Error generating user activity report: {str(e)}")
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.ACCESS,
            user_id=current_user["id"],
            action="read",
            resource_type="analytics",
            status="failure",
            details={"error": str(e), "report_type": "user_activity"},
            db=db
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while generating user activity report: {str(e)}"
        )

@router.get("/document-analytics", response_model=DocumentAnalytics)
async def get_document_analytics(
    time_range: Optional[AnalyticsTimeRange] = Query(AnalyticsTimeRange.LAST_30_DAYS, description="Time range for analytics"),
    organization_id: Optional[str] = Query(None, description="Filter by organization ID"),
    top_documents_limit: int = Query(10, ge=1, le=100, description="Limit for top documents"),
    current_user: Dict[str, Any] = Depends(
        requires_permission("analytics", "read", "document")
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Belge analitikleri raporu alır
    """
    try:
        # Organizasyon kontrolü - süper kullanıcı değilse kendi organizasyonuyla sınırla
        if not current_user.get("is_superuser") and organization_id != current_user.get("organization_id"):
            organization_id = current_user.get("organization_id")
        
        # Raporu oluştur
        report = await analytics_service.get_document_analytics(
            db=db,
            organization_id=organization_id,
            time_range=time_range,
            top_documents_limit=top_documents_limit
        )
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.ACCESS,
            user_id=current_user["id"],
            action="read",
            resource_type="analytics",
            status="success",
            details={"report_type": "document_analytics", "time_range": str(time_range), "organization_id": organization_id},
            db=db
        )
        
        return report
        
    except Exception as e:
        logger.error(f"Error generating document analytics report: {str(e)}")
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.ACCESS,
            user_id=current_user["id"],
            action="read",
            resource_type="analytics",
            status="failure",
            details={"error": str(e), "report_type": "document_analytics"},
            db=db
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while generating document analytics report: {str(e)}"
        )

@router.get("/query-analytics", response_model=QueryAnalytics)
async def get_query_analytics(
    time_range: Optional[AnalyticsTimeRange] = Query(AnalyticsTimeRange.LAST_30_DAYS, description="Time range for analytics"),
    organization_id: Optional[str] = Query(None, description="Filter by organization ID"),
    current_user: Dict[str, Any] = Depends(
        requires_permission("analytics", "read", "query")
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Sorgu analitikleri raporu alır
    """
    try:
        # Organizasyon kontrolü - süper kullanıcı değilse kendi organizasyonuyla sınırla
        if not current_user.get("is_superuser") and organization_id != current_user.get("organization_id"):
            organization_id = current_user.get("organization_id")
        
        # Raporu oluştur
        report = await analytics_service.get_query_analytics(
            db=db,
            organization_id=organization_id,
            time_range=time_range
        )
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.ACCESS,
            user_id=current_user["id"],
            action="read",
            resource_type="analytics",
            status="success",
            details={"report_type": "query_analytics", "time_range": str(time_range), "organization_id": organization_id},
            db=db
        )
        
        return report
        
    except Exception as e:
        logger.error(f"Error generating query analytics report: {str(e)}")
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.ACCESS,
            user_id=current_user["id"],
            action="read",
            resource_type="analytics",
            status="failure",
            details={"error": str(e), "report_type": "query_analytics"},
            db=db
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while generating query analytics report: {str(e)}"
        )

@router.get("/system-usage", response_model=SystemUsageReport)
async def get_system_usage(
    time_range: Optional[AnalyticsTimeRange] = Query(AnalyticsTimeRange.LAST_30_DAYS, description="Time range for analytics"),
    organization_id: Optional[str] = Query(None, description="Filter by organization ID"),
    current_user: Dict[str, Any] = Depends(
        requires_permission("analytics", "read", "system")
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Sistem kullanım raporu alır
    """
    try:
        # Organizasyon kontrolü - süper kullanıcı değilse kendi organizasyonuyla sınırla
        if not current_user.get("is_superuser") and organization_id != current_user.get("organization_id"):
            organization_id = current_user.get("organization_id")
        
        # Raporu oluştur
        report = await analytics_service.get_system_usage_report(
            db=db,
            organization_id=organization_id,
            time_range=time_range
        )
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.ACCESS,
            user_id=current_user["id"],
            action="read",
            resource_type="analytics",
            status="success",
            details={"report_type": "system_usage", "time_range": str(time_range), "organization_id": organization_id},
            db=db
        )
        
        return report
        
    except Exception as e:
        logger.error(f"Error generating system usage report: {str(e)}")
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.ACCESS,
            user_id=current_user["id"],
            action="read",
            resource_type="analytics",
            status="failure",
            details={"error": str(e), "report_type": "system_usage"},
            db=db
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while generating system usage report: {str(e)}"
        )

@router.get("/export/{report_type}")
async def export_analytics(
    report_type: str = Path(..., description="Report type: user_activity, document_analytics, query_analytics, system_usage"),
    format: AnalyticsExportFormat = Query(AnalyticsExportFormat.CSV, description="Export format"),
    time_range: Optional[AnalyticsTimeRange] = Query(AnalyticsTimeRange.LAST_30_DAYS, description="Time range for analytics"),
    organization_id: Optional[str] = Query(None, description="Filter by organization ID"),
    current_user: Dict[str, Any] = Depends(
        requires_permission("analytics", "export")
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Analitik verilerini dışa aktarır
    """
    try:
        # Rapor tipini doğrula
        valid_report_types = ["user_activity", "document_analytics", "query_analytics", "system_usage"]
        if report_type not in valid_report_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid report type. Must be one of: {', '.join(valid_report_types)}"
            )
        
        # Organizasyon kontrolü - süper kullanıcı değilse kendi organizasyonuyla sınırla
        if not current_user.get("is_superuser") and organization_id != current_user.get("organization_id"):
            organization_id = current_user.get("organization_id")
        
        # Dışa aktarım verilerini oluştur
        file_content, filename = await analytics_service.export_analytics_data(
            db=db,
            report_type=report_type,
            format=format,
            organization_id=organization_id,
            time_range=time_range
        )
        
        # Content-Type belirleme
        content_type = {
            AnalyticsExportFormat.CSV: "text/csv",
            AnalyticsExportFormat.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            AnalyticsExportFormat.JSON: "application/json"
        }[format]
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.DATA,
            user_id=current_user["id"],
            action="export",
            resource_type="analytics",
            status="success",
            details={
                "report_type": report_type,
                "format": format.value,
                "time_range": str(time_range),
                "organization_id": organization_id
            },
            db=db
        )
        
        # Dosyayı döndür
        return StreamingResponse(
            iter([file_content]),
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(f"Error exporting analytics data: {str(e)}")
        
        # Audit log kaydı
        await audit_service.log_event(
            event_type=AuditLogType.DATA,
            user_id=current_user["id"],
            action="export",
            resource_type="analytics",
            status="failure",
            details={
                "error": str(e),
                "report_type": report_type,
                "format": format.value
            },
            db=db
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while exporting analytics data: {str(e)}"
        )