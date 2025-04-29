# Last reviewed: 2025-04-29 13:59:34 UTC (User: TeeksssAPI)
import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Union
import asyncio
import ipaddress
import hashlib
import uuid
import os
import aiofiles
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db.session import get_db, engine
from ..models.audit_log import AuditLog, AuditLogType, AuditLogStatus
from ..repositories.audit_log_repository import AuditLogRepository

logger = logging.getLogger(__name__)

class AuditService:
    """
    Denetim kaydı hizmeti
    
    Sistem içindeki kritik olayları kaydetmek ve analiz etmek için kullanılır.
    GDPR, SOC2, ISO27001 gibi uyumluluk standartlarını destekler.
    """
    
    def __init__(self):
        """Audit service başlat"""
        self.audit_log_repository = AuditLogRepository()
        self.retention_period = settings.AUDIT_LOG_RETENTION_DAYS  # Gün cinsinden tutma süresi
        self.enabled = settings.AUDIT_LOGGING_ENABLED
        self.sensitive_fields = [
            "password", "token", "secret", "credit_card", "ssn", "social_security",
            "key", "auth", "auth_token", "jwt", "session", "cookie"
        ]
        
        # Dosya kayıt ayarları
        self.file_logging_enabled = settings.AUDIT_FILE_LOGGING_ENABLED
        self.log_directory = settings.AUDIT_LOG_DIRECTORY
        
        # Dış sistemlere gönderim
        self.siem_enabled = settings.AUDIT_SIEM_ENABLED
        self.siem_endpoint = settings.AUDIT_SIEM_ENDPOINT
        self.siem_api_key = settings.AUDIT_SIEM_API_KEY
        
        if self.file_logging_enabled:
            os.makedirs(self.log_directory, exist_ok=True)
    
    async def log_event(
        self, 
        event_type: AuditLogType,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: Optional[str] = None,
        status: AuditLogStatus = AuditLogStatus.SUCCESS,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        organization_id: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> str:
        """
        Denetim olayı kaydet
        
        Args:
            event_type: Olay türü
            user_id: Kullanıcı kimliği
            resource_type: Kaynak türü (ör. "document", "user")
            resource_id: Kaynak kimliği
            action: Gerçekleştirilen eylem (ör. "create", "update", "delete")
            status: İşlem durumu
            details: Olay detayları
            ip_address: İstemci IP adresi
            user_agent: İstemci User-Agent başlığı
            organization_id: Organizasyon kimliği
            db: Veritabanı oturumu (varsa)
            
        Returns:
            str: Oluşturulan denetim kaydı kimliği
        """
        if not self.enabled:
            return None
            
        try:
            # Gizli alanları maskeleme
            if details:
                details = self._sanitize_sensitive_data(details)
            
            # İşlemi kaydedecek olayı oluştur
            audit_log_id = str(uuid.uuid4())
            
            # ISO 8601 UTC zaman damgası
            timestamp = datetime.now(timezone.utc)
            
            # Denetim kaydını oluştur
            audit_log = AuditLog(
                id=audit_log_id,
                event_type=event_type,
                user_id=user_id,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id else None,
                action=action,
                status=status,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent,
                organization_id=organization_id,
                timestamp=timestamp
            )
            
            # Veritabanına kaydet
            own_session = db is None
            if own_session:
                async with AsyncSession(engine) as db:
                    await self.audit_log_repository.create_audit_log(db=db, audit_log=audit_log)
                    await db.commit()
            else:
                await self.audit_log_repository.create_audit_log(db=db, audit_log=audit_log)
            
            # Dosyaya kaydet (opsiyonel)
            if self.file_logging_enabled:
                asyncio.create_task(self._write_to_log_file(audit_log))
            
            # SIEM sistemine gönder (opsiyonel)
            if self.siem_enabled:
                asyncio.create_task(self._send_to_siem(audit_log))
            
            return audit_log_id
            
        except Exception as e:
            logger.error(f"Audit logging error: {str(e)}")
            return None
    
    def _sanitize_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gizli verileri maskele
        
        Args:
            data: İşlenecek veri
            
        Returns:
            Dict[str, Any]: Hassas alanları maskelenmiş veri
        """
        if not data:
            return data
            
        result = {}
        
        for key, value in data.items():
            # Hassas alan kontrolü
            is_sensitive = any(sensitive in key.lower() for sensitive in self.sensitive_fields)
            
            if is_sensitive and isinstance(value, str):
                # Hassas alanları maskele
                if len(value) <= 4:
                    result[key] = "****"
                else:
                    visible_chars = min(4, len(value) // 4)
                    result[key] = value[:visible_chars] + "*" * (len(value) - visible_chars)
            elif isinstance(value, dict):
                # İç içe nesneleri özyinelemeli işle
                result[key] = self._sanitize_sensitive_data(value)
            elif isinstance(value, list):
                # Liste öğelerini işle
                result[key] = [
                    self._sanitize_sensitive_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                # Hassas olmayan alanları olduğu gibi geçir
                result[key] = value
        
        return result
    
    async def _write_to_log_file(self, audit_log: AuditLog):
        """
        Denetim kaydını dosyaya yaz
        
        Args:
            audit_log: Denetim kaydı nesnesi
        """
        try:
            # Günlük tarihine göre dosya adı oluştur
            log_date = audit_log.timestamp.strftime("%Y-%m-%d")
            log_file = os.path.join(self.log_directory, f"audit_{log_date}.jsonl")
            
            # Kaydı JSON satırı olarak formatlayın
            log_entry = {
                "id": audit_log.id,
                "timestamp": audit_log.timestamp.isoformat(),
                "event_type": audit_log.event_type,
                "user_id": audit_log.user_id,
                "resource_type": audit_log.resource_type,
                "resource_id": audit_log.resource_id,
                "action": audit_log.action,
                "status": audit_log.status,
                "details": audit_log.details,
                "ip_address": audit_log.ip_address,
                "organization_id": audit_log.organization_id
            }
            
            # Dosyaya ekle
            async with aiofiles.open(log_file, "a") as f:
                await f.write(json.dumps(log_entry) + "\n")
        
        except Exception as e:
            logger.error(f"Error writing audit log to file: {str(e)}")
    
    async def _send_to_siem(self, audit_log: AuditLog):
        """
        Denetim kaydını SIEM sistemine gönder
        
        Args:
            audit_log: Denetim kaydı nesnesi
        """
        if not self.siem_endpoint or not self.siem_api_key:
            return
            
        try:
            import aiohttp
            
            # SIEM formatı için kaydı hazırla
            siem_entry = {
                "id": audit_log.id,
                "timestamp": audit_log.timestamp.isoformat(),
                "event_type": audit_log.event_type,
                "user_id": audit_log.user_id,
                "resource_type": audit_log.resource_type,
                "resource_id": audit_log.resource_id,
                "action": audit_log.action,
                "status": audit_log.status,
                "details": audit_log.details,
                "ip_address": audit_log.ip_address,
                "user_agent": audit_log.user_agent,
                "organization_id": audit_log.organization_id,
                "source": "ragbase",
                "environment": settings.ENVIRONMENT
            }
            
            # SIEM sistemine gönder
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.siem_endpoint,
                    json=siem_entry,
                    headers={
                        "Authorization": f"Bearer {self.siem_api_key}",
                        "Content-Type": "application/json"
                    }
                ) as response:
                    if response.status >= 400:
                        response_body = await response.text()
                        logger.warning(f"SIEM API error: {response.status} - {response_body}")
        
        except Exception as e:
            logger.error(f"Error sending audit log to SIEM: {str(e)}")
    
    async def get_audit_logs(
        self,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: Optional[str] = None,
        event_type: Optional[AuditLogType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        ip_address: Optional[str] = None,
        organization_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Denetim kayıtlarını sorgula
        
        Args:
            user_id: Kullanıcı kimliği filtresi
            resource_type: Kaynak türü filtresi
            resource_id: Kaynak kimliği filtresi
            action: Eylem filtresi
            event_type: Olay türü filtresi
            start_date: Başlangıç tarihi filtresi
            end_date: Bitiş tarihi filtresi
            ip_address: IP adresi filtresi
            organization_id: Organizasyon kimliği filtresi
            page: Sayfa numarası
            page_size: Sayfa başına kayıt sayısı
            db: Veritabanı oturumu
            
        Returns:
            Dict[str, Any]: Sorgulanan denetim kayıtları ve metadata
        """
        own_session = db is None
        try:
            if own_session:
                async with AsyncSession(engine) as db:
                    return await self.audit_log_repository.get_audit_logs(
                        db=db,
                        user_id=user_id,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        action=action,
                        event_type=event_type,
                        start_date=start_date,
                        end_date=end_date,
                        ip_address=ip_address,
                        organization_id=organization_id,
                        page=page,
                        page_size=page_size
                    )
            else:
                return await self.audit_log_repository.get_audit_logs(
                    db=db,
                    user_id=user_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    action=action,
                    event_type=event_type,
                    start_date=start_date,
                    end_date=end_date,
                    ip_address=ip_address,
                    organization_id=organization_id,
                    page=page,
                    page_size=page_size
                )
        except Exception as e:
            logger.error(f"Error retrieving audit logs: {str(e)}")
            return {"items": [], "total": 0, "page": page, "page_size": page_size}
    
    async def cleanup_old_logs(self) -> int:
        """
        Eski denetim kayıtlarını temizle
        
        Returns:
            int: Silinen kayıt sayısı
        """
        if not self.retention_period or self.retention_period <= 0:
            return 0
            
        try:
            # Tutma süresi dışındaki kayıtları sil
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.retention_period)
            
            async with AsyncSession(engine) as db:
                deleted_count = await self.audit_log_repository.delete_old_audit_logs(
                    db=db,
                    cutoff_date=cutoff_date
                )
                await db.commit()
                
                return deleted_count
                
        except Exception as e:
            logger.error(f"Error cleaning up old audit logs: {str(e)}")
            return 0
    
    async def get_audit_log_stats(
        self,
        resource_type: Optional[str] = None,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Denetim kaydı istatistikleri al
        
        Args:
            resource_type: Kaynak türü filtresi
            user_id: Kullanıcı kimliği filtresi
            organization_id: Organizasyon kimliği filtresi
            start_date: Başlangıç tarihi filtresi
            end_date: Bitiş tarihi filtresi
            db: Veritabanı oturumu
            
        Returns:
            Dict[str, Any]: Denetim kaydı istatistikleri
        """
        own_session = db is None
        try:
            if own_session:
                async with AsyncSession(engine) as db:
                    return await self.audit_log_repository.get_audit_log_stats(
                        db=db,
                        resource_type=resource_type,
                        user_id=user_id,
                        organization_id=organization_id,
                        start_date=start_date,
                        end_date=end_date
                    )
            else:
                return await self.audit_log_repository.get_audit_log_stats(
                    db=db,
                    resource_type=resource_type,
                    user_id=user_id,
                    organization_id=organization_id,
                    start_date=start_date,
                    end_date=end_date
                )
        except Exception as e:
            logger.error(f"Error retrieving audit log stats: {str(e)}")
            return {}