# Last reviewed: 2025-04-29 10:34:18 UTC (User: Teekssseksikleri)
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status, Request
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.async_database import get_db
from ..auth import get_current_active_user, require_admin, UserInDB as User
from ..repositories.security_log_repository import SecurityLogRepository
from ..utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()
security_log_repo = SecurityLogRepository()

class SecurityLogResponse(BaseModel):
    logs: List[Dict[str, Any]]
    total: int
    page: int
    limit: int
    
class SecurityLogDetail(BaseModel):
    log: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@router.get("/security-logs", response_model=SecurityLogResponse)
async def get_security_logs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),  # Sadece admin erişebilir
    log_type: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    resource_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    success: Optional[bool] = Query(None)
):
    """Güvenlik loglarını getirir (sadece admin)"""
    try:
        # Tarih filtreleri varsa datetime'a çevir
        start_date_obj = None
        end_date_obj = None
        
        if start_date:
            try:
                start_date_obj = datetime.datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid start_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
                )
                
        if end_date:
            try:
                end_date_obj = datetime.datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid end_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
                )
        
        # Offset hesapla
        offset = (page - 1) * limit
        
        # Logları getir
        logs = await security_log_repo.get_logs(
            db=db,
            log_type=log_type,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            start_date=start_date_obj,
            end_date=end_date_obj,
            limit=limit,
            offset=offset,
            sort_by="timestamp",
            sort_order="desc"
        )
        
        # Success filtresi (veritabanı katmanında daha verimli olabilirdi, ama örnekte sonuçları filtreleyelim)
        if success is not None:
            logs = [log for log in logs if log["success"] == success]
        
        # Toplam sayıyı getir
        total = await security_log_repo.get_logs_count(
            db=db,
            log_type=log_type,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            start_date=start_date_obj,
            end_date=end_date_obj
        )
        
        return SecurityLogResponse(
            logs=logs,
            total=total,
            page=page,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"Security logs retrieval error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve security logs: {str(e)}"
        )

@router.get("/security-logs/{log_id}", response_model=SecurityLogDetail)
async def get_security_log_by_id(
    log_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)  # Sadece admin erişebilir
):
    """Belirli bir güvenlik log kaydını ID'ye göre getirir"""
    try:
        log = await security_log_repo.get_log_by_id(db, log_id)
        
        if not log:
            return SecurityLogDetail(error=f"Security log with ID {log_id} not found")
            
        return SecurityLogDetail(log=log)
        
    except Exception as e:
        logger.error(f"Security log retrieval error: {e}")
        return SecurityLogDetail(error=f"Failed to retrieve security log: {str(e)}")