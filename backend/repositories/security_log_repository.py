# Last reviewed: 2025-04-29 10:27:19 UTC (User: TeeksssAPI)
from typing import Dict, List, Optional, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, text, desc, func
import datetime
import json

from ..db.models import SecurityLogDB
from ..utils.logger import get_logger

logger = get_logger(__name__)

class SecurityLogRepository:
    """Güvenlik loglarını yönetmek için repository"""
    
    async def create_log(
        self,
        db: AsyncSession,
        log_type: str,
        action: str,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        severity: str = "info"
    ) -> int:
        """Yeni bir güvenlik log kaydı oluşturur"""
        try:
            details_json = json.dumps(details) if details else None
            
            stmt = insert(SecurityLogDB).values(
                timestamp=datetime.datetime.utcnow(),
                log_type=log_type,
                action=action,
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details_json,
                success=success,
                severity=severity
            )
            
            result = await db.execute(stmt)
            await db.commit()
            
            # Son eklenen kaydın ID'sini döndür
            return result.inserted_primary_key[0]
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Security log creation error: {e}")
            raise
    
    async def get_logs(
        self, 
        db: AsyncSession, 
        log_type: Optional[str] = None,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_date: Optional[datetime.datetime] = None,
        end_date: Optional[datetime.datetime] = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "timestamp",
        sort_order: str = "desc"
    ) -> List[Dict[str, Any]]:
        """Güvenlik loglarını filtreli şekilde getirir"""
        try:
            query = select(SecurityLogDB)
            
            # Filtreleri ekle
            if log_type:
                query = query.where(SecurityLogDB.log_type == log_type)
            if user_id:
                query = query.where(SecurityLogDB.user_id == user_id)
            if action:
                query = query.where(SecurityLogDB.action == action)
            if resource_type:
                query = query.where(SecurityLogDB.resource_type == resource_type)
            if resource_id:
                query = query.where(SecurityLogDB.resource_id == resource_id)
            if start_date:
                query = query.where(SecurityLogDB.timestamp >= start_date)
            if end_date:
                query = query.where(SecurityLogDB.timestamp <= end_date)
            
            # Sıralama
            if sort_order.lower() == "asc":
                query = query.order_by(getattr(SecurityLogDB, sort_by))
            else:
                query = query.order_by(desc(getattr(SecurityLogDB, sort_by)))
            
            # Sayfalama
            query = query.limit(limit).offset(offset)
            
            # Sorguyu çalıştır
            result = await db.execute(query)
            logs_db = result.scalars().all()
            
            # DB nesnelerini dict'e çevir
            logs = []
            for log in logs_db:
                log_dict = {
                    "id": log.id,
                    "timestamp": log.timestamp,
                    "log_type": log.log_type,
                    "user_id": log.user_id,
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                    "success": log.success,
                    "severity": log.severity
                }
                
                # JSON details'i parse et
                if log.details:
                    try:
                        log_dict["details"] = json.loads(log.details)
                    except:
                        log_dict["details"] = log.details
                
                logs.append(log_dict)
            
            return logs
                
        except Exception as e:
            logger.error(f"Security log retrieval error: {e}")
            raise
    
    async def get_logs_count(
        self,
        db: AsyncSession,
        log_type: Optional[str] = None,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_date: Optional[datetime.datetime] = None,
        end_date: Optional[datetime.datetime] = None
    ) -> int:
        """Filtrelere göre log sayısını döndürür"""
        try:
            query = select(func.count(SecurityLogDB.id))
            
            # Filtreleri ekle
            if log_type:
                query = query.where(SecurityLogDB.log_type == log_type)
            if user_id:
                query = query.where(SecurityLogDB.user_id == user_id)
            if action:
                query = query.where(SecurityLogDB.action == action)
            if resource_type:
                query = query.where(SecurityLogDB.resource_type == resource_type)
            if resource_id:
                query = query.where(SecurityLogDB.resource_id == resource_id)
            if start_date:
                query = query.where(SecurityLogDB.timestamp >= start_date)
            if end_date:
                query = query.where(SecurityLogDB.timestamp <= end_date)
            
            # Sorguyu çalıştır
            result = await db.execute(query)
            count = result.scalar_one()
            
            return count
            
        except Exception as e:
            logger.error(f"Security log count error: {e}")
            raise
    
    async def get_log_by_id(self, db: AsyncSession, log_id: int) -> Optional[Dict[str, Any]]:
        """ID'ye göre güvenlik logu getirir"""
        try:
            query = select(SecurityLogDB).where(SecurityLogDB.id == log_id)
            result = await db.execute(query)
            log_db = result.scalars().first()
            
            if not log_db:
                return None
                
            log_dict = {
                "id": log_db.id,
                "timestamp": log_db.timestamp,
                "log_type": log_db.log_type,
                "user_id": log_db.user_id,
                "action": log_db.action,
                "resource_type": log_db.resource_type,
                "resource_id": log_db.resource_id,
                "ip_address": log_db.ip_address,
                "user_agent": log_db.user_agent,
                "success": log_db.success,
                "severity": log_db.severity
            }
            
            # JSON details'i parse et
            if log_db.details:
                try:
                    log_dict["details"] = json.loads(log_db.details)
                except:
                    log_dict["details"] = log_db.details
            
            return log_dict
            
        except Exception as e:
            logger.error(f"Security log retrieval by ID error: {e}")
            raise