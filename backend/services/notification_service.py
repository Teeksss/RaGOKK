# Last reviewed: 2025-04-29 10:59:14 UTC (User: Teekssseksiklikleri)
from typing import Dict, List, Optional, Any, Union
import asyncio
import httpx
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime

from ..utils.config import (
    EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, EMAIL_SMTP_USER, 
    EMAIL_SMTP_PASSWORD, EMAIL_FROM, WEBHOOK_URLS
)
from ..utils.logger import get_logger
from ..utils.email_templates import EmailTemplates

logger = get_logger(__name__)

class NotificationService:
    """
    Bildirim servisi - webhook ve email bildirimlerini gönderir.
    API anahtarı değişikliklerinde ve güvenlik olaylarında kullanılır.
    """
    
    async def send_webhook(self, 
                         event_type: str, 
                         payload: Dict[str, Any],
                         webhook_url: Optional[str] = None) -> bool:
        """
        Webhook gönderir
        
        Args:
            event_type: Olay türü (api_key_change, security_alert, vs.)
            payload: Gönderilecek veri
            webhook_url: Özel webhook URL (yoksa konfigürasyondaki kullanılır)
        """
        # Webhook URL'leri yoksa hata ver
        webhook_urls = []
        
        # Belirli URL verilmişse onu kullan
        if webhook_url:
            webhook_urls.append(webhook_url)
        # Konfigürasyondaki URL'leri kullan
        elif WEBHOOK_URLS and isinstance(WEBHOOK_URLS, dict) and event_type in WEBHOOK_URLS:
            urls = WEBHOOK_URLS[event_type]
            if isinstance(urls, list):
                webhook_urls.extend(urls)
            elif isinstance(urls, str):
                webhook_urls.append(urls)
        
        if not webhook_urls:
            logger.warning(f"Webhook URL'leri bulunamadı: {event_type}")
            return False
            
        # Webhook verisi oluştur
        webhook_data = {
            "event_type": event_type,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "data": payload
        }
        
        # Webhook'ları asenkron gönder
        success = True
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                for url in webhook_urls:
                    try:
                        response = await client.post(
                            url,
                            json=webhook_data,
                            headers={"Content-Type": "application/json"}
                        )
                        
                        if response.status_code >= 400:
                            logger.warning(f"Webhook gönderimi başarısız ({url}): HTTP {response.status_code}")
                            success = False
                    except Exception as e:
                        logger.error(f"Webhook gönderimi hatası ({url}): {e}")
                        success = False
            
            return success
        except Exception as e:
            logger.error(f"Webhook gönderimi sırasında hata: {e}")
            return False
    
    async def send_email(self, 
                       recipient: str, 
                       subject: str, 
                       body_text: str,
                       body_html: Optional[str] = None) -> bool:
        """Email bildirim gönderme"""
        # Email ayarları yoksa hata ver
        if not EMAIL_SMTP_HOST or not EMAIL_SMTP_USER or not EMAIL_SMTP_PASSWORD:
            logger.warning("Email ayarları eksik")
            return False
        
        # Email gönderimi CPU-bound işlem, bu nedenle thread pool'da çalıştırılır
        try:
            return await asyncio.to_thread(
                self._send_email_sync,
                recipient,
                subject,
                body_text,
                body_html
            )
        except Exception as e:
            logger.error(f"Email gönderimi sırasında hata: {e}")
            return False
    
    def _send_email_sync(self,
                        recipient: str, 
                        subject: str, 
                        body_text: str,
                        body_html: Optional[str] = None) -> bool:
        """Senkron email gönderim implementasyonu"""
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = EMAIL_FROM if EMAIL_FROM else EMAIL_SMTP_USER
            message["To"] = recipient
            
            # Text ve HTML gövde ekle
            part1 = MIMEText(body_text, "plain")
            message.attach(part1)
            
            if body_html:
                part2 = MIMEText(body_html, "html")
                message.attach(part2)
            
            # SMTP bağlantısı kur ve email gönder
            with smtplib.SMTP(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT) as server:
                server.starttls()
                server.login(EMAIL_SMTP_USER, EMAIL_SMTP_PASSWORD)
                server.send_message(message)
                
            return True
        except Exception as e:
            logger.error(f"Email gönderimi hatası: {e}")
            return False
    
    async def send_admin_notification(self, 
                                   subject: str, 
                                   body: str,
                                   body_html: Optional[str] = None,
                                   admin_emails: Optional[List[str]] = None) -> bool:
        """
        Admin kullanıcılarına bildirim gönderme
        
        Args:
            subject: Email konusu
            body: Email metni
            body_html: HTML formatında email (opsiyonel)
            admin_emails: Belirli admin email listesi (yoksa konfigürasyondaki kullanılır)
        """
        # Admin emailleri yoksa konfigürasyondan al
        if not admin_emails:
            # Gerçek uygulamada admin_users tablosundan veya config'den alınmalı
            admin_emails = ["admin@example.com"]
        
        if not admin_emails:
            logger.warning("Admin email listesi bulunamadı")
            return False
        
        # Her admine email gönder
        success = True
        for email in admin_emails:
            email_result = await self.send_email(email, subject, body, body_html)
            if not email_result:
                success = False
        
        return success
    
    async def notify_api_key_change(self,
                                  provider: str,
                                  change_type: str,  # 'create', 'update', 'delete'
                                  changed_by: str,
                                  details: Optional[Dict[str, Any]] = None) -> bool:
        """
        API anahtarı değişikliği bildirimi
        
        Args:
            provider: API sağlayıcısı adı (openai, cohere, vb.)
            change_type: Değişiklik türü (create, update, delete)
            changed_by: Değişikliği yapan kullanıcı ID'si
            details: Ek detaylar
        """
        # Webhook'a gönderilecek veriyi hazırla
        webhook_payload = {
            "provider": provider,
            "change_type": change_type,
            "changed_by": changed_by,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "details": details
        }
        
        # Webhook gönder
        webhook_success = await self.send_webhook("api_key_change", webhook_payload)
        
        # Email template'i kullanarak email içeriği oluştur
        email_content = EmailTemplates.api_key_change_template(change_type, provider, changed_by, details)
        
        # Admin'lere email gönder
        email_success = await self.send_admin_notification(
            email_content["subject"], 
            email_content["text"],
            email_content["html"]
        )
        
        return webhook_success and email_success
    
    async def notify_security_event(self,
                                 event_type: str,  # 'login_failure', 'unauthorized_access', etc.
                                 severity: str,    # 'info', 'warning', 'error', 'critical'
                                 message: str,
                                 details: Optional[Dict[str, Any]] = None) -> bool:
        """
        Güvenlik olayı bildirimi
        
        Args:
            event_type: Olay türü (login_failure, unauthorized_access, vb.)
            severity: Önem derecesi (info, warning, error, critical)
            message: Ana mesaj
            details: Ek detaylar
        """
        # Webhook'a gönderilecek veriyi hazırla
        webhook_payload = {
            "event_type": event_type,
            "severity": severity,
            "message": message,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "details": details
        }
        
        # Webhook gönder
        webhook_success = await self.send_webhook("security_event", webhook_payload)
        
        # Kritik ve hata olayları için email bildirim gönder
        if severity in ["critical", "error"]:
            # Email template'i kullanarak email içeriği oluştur
            email_content = EmailTemplates.security_alert_template(event_type, severity, message, details)
            
            # Admin'lere email gönder
            await self.send_admin_notification(
                email_content["subject"], 
                email_content["text"],
                email_content["html"]
            )
        
        return webhook_success

    async def send_test_notification(self, recipient: str) -> bool:
        """
        Test amaçlı olarak bildirim gönderir
        """
        subject = "Bildirim Sistemi Testi"
        text = "Bu bir test mesajıdır. Bildirim sistemi düzgün çalışıyor."
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Test Bildirimi</title>
        </head>
        <body>
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
                <h2 style="color: #4a90e2;">Bildirim Sistemi Testi</h2>
                <p>Bu bir test mesajıdır. Bildirim sistemi düzgün çalışıyor.</p>
                <p style="color: #4caf50; font-weight: bold;">✓ Sistem aktif ve çalışıyor.</p>
            </div>
        </body>
        </html>
        """
        
        return await self.send_email(recipient, subject, text, html)

# Notification service singleton
notification_service = NotificationService()