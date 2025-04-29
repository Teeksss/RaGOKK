# Last reviewed: 2025-04-29 12:09:11 UTC (User: TeeksssVirüs)
import aiohttp
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import Dict, List, Any, Optional, Tuple, Union
import os
import json
import time
from datetime import datetime
import jinja2
import re
from dataclasses import dataclass
from enum import Enum

from ..utils.logger import get_logger

logger = get_logger(__name__)


class NotificationType(Enum):
    """Bildirim türleri"""
    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_PROCESSED = "document_processed"
    DOCUMENT_UPDATED = "document_updated"
    DOCUMENT_DELETED = "document_deleted"
    DOCUMENT_SHARED = "document_shared"
    DOCUMENT_ACCESS_GRANTED = "document_access_granted"
    DOCUMENT_ACCESS_REVOKED = "document_access_revoked"
    SECURITY_WARNING = "security_warning"
    SECURITY_THREAT = "security_threat"
    SYSTEM_ALERT = "system_alert"
    USER_REGISTERED = "user_registered"
    USER_LOGGED_IN = "user_logged_in"


@dataclass
class NotificationEvent:
    """Bildirim olayı"""
    event_type: NotificationType
    subject: str
    recipient: Optional[str]  # E-posta alıcısı veya webhook alıcısı
    data: Dict[str, Any]
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class NotificationService:
    """
    E-posta bildirimleri ve webhook entegrasyonları için servis.
    - E-posta gönderimi
    - Webhook çağrıları
    - Bildirim şablonları
    - Hız sınırlaması
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Args:
            config: Konfigürasyon parametreleri
        """
        self.config = config or {}
        
        # E-posta ayarları
        self.email_enabled = self.config.get('email_enabled', False)
        self.email_server = self.config.get('email_server', 'localhost')
        self.email_port = self.config.get('email_port', 25)
        self.email_use_tls = self.config.get('email_use_tls', False)
        self.email_username = self.config.get('email_username')
        self.email_password = self.config.get('email_password')
        self.email_from = self.config.get('email_from', 'noreply@example.com')
        self.email_reply_to = self.config.get('email_reply_to')
        
        # Webhook ayarları
        self.webhook_enabled = self.config.get('webhook_enabled', False)
        self.webhook_urls = self.config.get('webhook_urls', {})
        self.webhook_timeout = self.config.get('webhook_timeout', 10)
        self.webhook_retry = self.config.get('webhook_retry', 3)
        
        # Şablon ayarları
        self.templates_dir = self.config.get('templates_dir', 'templates/notifications')
        self.template_env = None
        if os.path.exists(self.templates_dir):
            self.template_env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(self.templates_dir),
                autoescape=True
            )
        
        # Hız sınırlama ayarları
        self.rate_limit_enabled = self.config.get('rate_limit_enabled', True)
        self.rate_limit_per_recipient = self.config.get('rate_limit_per_recipient', 5)  # dakika başına
        self.rate_limit_window = self.config.get('rate_limit_window', 60 * 60)  # 1 saat
        
        # Son bildirimler (hız sınırlaması için)
        self.last_notifications = {}
        
        # Kuyruk
        self.notification_queue = asyncio.Queue()
        self.worker_task = None
        
        # İstatistikler
        self.stats = {
            "emails_sent": 0,
            "emails_failed": 0,
            "webhooks_sent": 0,
            "webhooks_failed": 0,
            "rate_limited": 0
        }
    
    async def start(self):
        """Bildirim işçisini başlat"""
        if self.worker_task is None:
            self.worker_task = asyncio.create_task(self._notification_worker())
            logger.info("Bildirim servisi başlatıldı")
    
    async def stop(self):
        """Bildirim işçisini durdur"""
        if self.worker_task is not None:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
            self.worker_task = None
            logger.info("Bildirim servisi durduruldu")
    
    async def send_notification(self, event: NotificationEvent) -> bool:
        """
        Bildirim gönder (kuyruğa ekle)
        
        Args:
            event: Bildirim olayı
            
        Returns:
            bool: Kuyruğa eklendiyse True
        """
        try:
            # Hız sınırlaması kontrolü
            if self.rate_limit_enabled and event.recipient:
                key = f"{event.event_type.value}:{event.recipient}"
                current_time = time.time()
                
                if key in self.last_notifications:
                    notifications = self.last_notifications[key]
                    
                    # Eski bildirimleri temizle
                    notifications = [n for n in notifications if current_time - n < self.rate_limit_window]
                    
                    # Dakikadaki bildirim sayısını kontrol et
                    recent_count = sum(1 for n in notifications if current_time - n < 60)
                    if recent_count >= self.rate_limit_per_recipient:
                        logger.warning(f"Hız sınırı aşıldı: {event.event_type.value} için {event.recipient}")
                        self.stats["rate_limited"] += 1
                        return False
                    
                    # Listeyi güncelle
                    notifications.append(current_time)
                    self.last_notifications[key] = notifications
                else:
                    self.last_notifications[key] = [current_time]
            
            # Kuyruğa ekle
            await self.notification_queue.put(event)
            return True
            
        except Exception as e:
            logger.error(f"Bildirim kuyruklama hatası: {e}")
            return False
    
    async def _notification_worker(self):
        """Bildirim kuyruğunu işleyen işçi"""
        try:
            logger.info("Bildirim işçisi başlatıldı")
            
            while True:
                # Kuyruktan bildirim al
                event = await self.notification_queue.get()
                
                try:
                    # E-posta bildirimi
                    if self.email_enabled and event.recipient and '@' in event.recipient:
                        await self._send_email_notification(event)
                    
                    # Webhook bildirimi
                    if self.webhook_enabled:
                        await self._send_webhook_notification(event)
                        
                except Exception as e:
                    logger.error(f"Bildirim işleme hatası: {e}, Olay: {event.event_type.value}")
                
                # İşlemi tamamla
                self.notification_queue.task_done()
                
        except asyncio.CancelledError:
            logger.info("Bildirim işçisi durduruldu")
        except Exception as e:
            logger.error(f"Bildirim işçisi hatası: {e}")
    
    async def _send_email_notification(self, event: NotificationEvent):
        """E-posta bildirimi gönder"""
        try:
            if not self.email_enabled:
                return
                
            # Alıcı kontrolü
            if not event.recipient or '@' not in event.recipient:
                logger.warning(f"Geçersiz e-posta adresi: {event.recipient}")
                return
            
            # Şablon hazırla
            html_content = await self._render_template(f"{event.event_type.value}.html", event.data)
            text_content = await self._render_template(f"{event.event_type.value}.txt", event.data)
            
            if not html_content and not text_content:
                # Varsayılan şablon
                html_content = await self._render_default_template(event, is_html=True)
                text_content = await self._render_default_template(event, is_html=False)
            
            # E-posta mesajı oluştur
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email_from
            msg['To'] = event.recipient
            msg['Subject'] = event.subject
            
            if self.email_reply_to:
                msg['Reply-To'] = self.email_reply_to
            
            # Düz metin versiyonu
            if text_content:
                msg.attach(MIMEText(text_content, 'plain'))
            
            # HTML versiyonu
            if html_content:
                msg.attach(MIMEText(html_content, 'html'))
            
            # Dosya ekleri
            attachments = event.data.get('attachments', [])
            for attachment in attachments:
                if isinstance(attachment, dict) and 'content' in attachment and 'filename' in attachment:
                    part = MIMEApplication(attachment['content'])
                    part.add_header('Content-Disposition', 'attachment', filename=attachment['filename'])
                    msg.attach(part)
            
            # Bağlantı kur ve gönder
            server = None
            try:
                if self.email_use_tls:
                    server = smtplib.SMTP(self.email_server, self.email_port)
                    server.starttls()
                else:
                    server = smtplib.SMTP(self.email_server, self.email_port)
                
                if self.email_username and self.email_password:
                    server.login(self.email_username, self.email_password)
                
                server.send_message(msg)
                logger.info(f"E-posta gönderildi: {event.event_type.value} - {event.recipient}")
                self.stats["emails_sent"] += 1
                
            finally:
                if server:
                    server.quit()
                    
        except Exception as e:
            logger.error(f"E-posta gönderim hatası: {e}")
            self.stats["emails_failed"] += 1
    
    async def _send_webhook_notification(self, event: NotificationEvent):
        """Webhook bildirimi gönder"""
        if not self.webhook_enabled:
            return
            
        # Etkinlik türüne uygun webhook URL'si bul
        webhook_url = self.webhook_urls.get(event.event_type.value) or self.webhook_urls.get('default')
        
        if not webhook_url:
            return
            
        # Webhook verisi hazırla
        webhook_data = {
            "event_type": event.event_type.value,
            "timestamp": datetime.fromtimestamp(event.timestamp).isoformat(),
            "data": event.data
        }
        
        # İsteği gönder
        retry_count = 0
        max_retries = self.webhook_retry
        
        while retry_count <= max_retries:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        webhook_url,
                        json=webhook_data,
                        timeout=self.webhook_timeout
                    ) as response:
                        if response.status < 400:  # Başarılı yanıt
                            logger.info(f"Webhook gönderildi: {event.event_type.value} - {webhook_url}")
                            self.stats["webhooks_sent"] += 1
                            return
                        else:
                            error_text = await response.text()
                            logger.warning(f"Webhook hatası: {response.status} - {error_text}")
                            
                            # Yeniden deneme sadece geçici hatalar için
                            if response.status < 500:
                                # 4xx client hatası, yeniden deneme
                                break
            
            except asyncio.TimeoutError:
                logger.warning(f"Webhook zaman aşımı: {webhook_url}")
            except Exception as e:
                logger.error(f"Webhook gönderim hatası: {e}")
            
            # Yeniden deneme
            retry_count += 1
            if retry_count <= max_retries:
                await asyncio.sleep(2 ** retry_count)  # Üstel geri çekilme
        
        # Tüm denemeler başarısız
        self.stats["webhooks_failed"] += 1
    
    async def _render_template(self, template_name: str, data: Dict[str, Any]) -> Optional[str]:
        """Şablon oluştur"""
        if not self.template_env:
            return None
            
        try:
            template = self.template_env.get_template(template_name)
            return template.render(**data)
        except jinja2.exceptions.TemplateNotFound:
            return None
        except Exception as e:
            logger.error(f"Şablon oluşturma hatası: {e}")
            return None
    
    async def _render_default_template(self, event: NotificationEvent, is_html: bool = False) -> str:
        """Varsayılan şablon oluştur"""
        if is_html:
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>{event.subject}</title>
            </head>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #4a90e2;">{event.subject}</h1>
                <p>Yeni bir bildiriminiz var.</p>
                <h2 style="color: #555;">Olay Bilgileri</h2>
                <ul>
                    <li><strong>Olay Tipi:</strong> {event.event_type.value}</li>
                    <li><strong>Tarih:</strong> {datetime.fromtimestamp(event.timestamp).strftime('%d.%m.%Y %H:%M:%S')}</li>
                </ul>
                <div style="background-color: #f5f5f5; border-left: 4px solid #4a90e2; padding: 15px; margin: 20px 0;">
                    <pre style="white-space: pre-wrap;">{json.dumps(event.data, indent=2, ensure_ascii=False)}</pre>
                </div>
                <p style="color: #777; font-size: 12px; margin-top: 30px; border-top: 1px solid #eee; padding-top: 10px;">
                    Bu otomatik bir bildirimdir. Lütfen bu e-postaya yanıt vermeyiniz.
                </p>
            </body>
            </html>
            """
        else:
            return f"""
            {event.subject}
            ==========================================================
            
            Yeni bir bildiriminiz var.
            
            OLAY BİLGİLERİ:
            - Olay Tipi: {event.event_type.value}
            - Tarih: {datetime.fromtimestamp(event.timestamp).strftime('%d.%m.%Y %H:%M:%S')}
            
            İÇERİK:
            {json.dumps(event.data, indent=2, ensure_ascii=False)}
            
            ----------------------------------------------------------
            Bu otomatik bir bildirimdir. Lütfen bu e-postaya yanıt vermeyiniz.
            """