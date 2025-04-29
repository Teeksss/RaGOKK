# Last reviewed: 2025-04-29 10:51:12 UTC (User: TeeksssPrioritizationTest.js)
import os
import jinja2
from typing import Dict, Any, Optional

# Jinja2 template ortamını ayarla
template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
template_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(template_dir),
    autoescape=True
)

class EmailTemplates:
    """
    HTML email template sistemini yöneten sınıf.
    Jinja2 kullanarak template'leri render eder.
    """
    
    @staticmethod
    def render_template(template_name: str, context: Dict[str, Any]) -> str:
        """
        Verilen template'i context ile render eder
        
        Args:
            template_name: Template dosya adı (uzantısız)
            context: Template değişkenleri
            
        Returns:
            str: Render edilmiş HTML içeriği
        """
        try:
            template = template_env.get_template(f"{template_name}.html")
            return template.render(**context)
        except jinja2.exceptions.TemplateNotFound:
            # Template bulunamadığında, basit bir HTML template oluştur
            return EmailTemplates._create_default_template(template_name, context)
    
    @staticmethod
    def _create_default_template(template_name: str, context: Dict[str, Any]) -> str:
        """
        Template bulunamadığında basit bir varsayılan HTML template oluşturur
        """
        title = context.get('title', 'Bildirim')
        content = context.get('content', '')
        
        # Basit bir e-posta şablonu
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333333;
                    margin: 0;
                    padding: 20px;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: #ffffff;
                    padding: 20px;
                    border: 1px solid #dddddd;
                    border-radius: 5px;
                }}
                .header {{
                    text-align: center;
                    padding: 10px;
                    background-color: #f5f5f5;
                    border-radius: 5px;
                    margin-bottom: 20px;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 20px;
                    font-size: 12px;
                    color: #777777;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{title}</h1>
                </div>
                <div class="content">
                    {content}
                </div>
                <div class="footer">
                    <p>Bu e-posta otomatik olarak oluşturulmuştur. Lütfen yanıtlamayınız.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html
    
    @staticmethod
    def api_key_change_template(change_type: str, provider: str, changed_by: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        API anahtarı değişiklik bildirimleri için HTML ve metin içeriği oluşturur
        
        Returns:
            Dict[str, str]: HTML ve metin içeriği
        """
        action_map = {
            "create": "oluşturuldu",
            "update": "güncellendi",
            "delete": "silindi"
        }
        action = action_map.get(change_type, change_type)
        
        title = f"API Anahtarı {action.capitalize()}: {provider}"
        
        # HTML için ek detaylar
        details_html = ""
        if details:
            details_html = "<h3>Detaylar:</h3><ul>"
            for key, value in details.items():
                details_html += f"<li><strong>{key}:</strong> {value}</li>"
            details_html += "</ul>"
        
        # Metin içeriği
        text_content = (f"API anahtarı {provider} için {action} işlemi yapıldı.\n\n"
                      f"Değişiklik yapan: {changed_by}\n")
                      
        if details:
            text_content += "\nDetaylar:\n"
            for key, value in details.items():
                text_content += f"- {key}: {value}\n"
                
        # HTML içeriği için context
        context = {
            "title": title,
            "provider": provider,
            "action": action,
            "changed_by": changed_by,
            "details": details,
            "details_html": details_html,
            "content": f"""
                <p>API anahtarı <strong>{provider}</strong> için <strong>{action}</strong> işlemi yapıldı.</p>
                <p><strong>Değişiklik yapan:</strong> {changed_by}</p>
                {details_html}
            """
        }
        
        # HTML içeriği render et
        html_content = EmailTemplates.render_template("api_key_change", context)
        
        return {
            "subject": title,
            "html": html_content,
            "text": text_content
        }
    
    @staticmethod
    def security_alert_template(event_type: str, severity: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        Güvenlik uyarıları için HTML ve metin içeriği oluşturur
        
        Returns:
            Dict[str, str]: HTML ve metin içeriği
        """
        event_title = event_type.replace("_", " ").title()
        title = f"Güvenlik Uyarısı: {event_title} ({severity.capitalize()})"
        
        # Severity sınıfı
        severity_class = {
            "info": "info",
            "warning": "warning",
            "error": "error", 
            "critical": "critical"
        }.get(severity.lower(), "info")
        
        # HTML için ek detaylar
        details_html = ""
        if details:
            details_html = "<h3>Teknik Detaylar:</h3><ul>"
            for key, value in details.items():
                details_html += f"<li><strong>{key}:</strong> {value}</li>"
            details_html += "</ul>"
        
        # Metin içeriği
        text_content = (f"Güvenlik Uyarısı: {event_title}\n\n"
                      f"Önem: {severity.capitalize()}\n"
                      f"Mesaj: {message}\n")
                      
        if details:
            text_content += "\nTeknik Detaylar:\n"
            for key, value in details.items():
                text_content += f"- {key}: {value}\n"
                
        # HTML içeriği için context
        context = {
            "title": title,
            "event_type": event_title,
            "severity": severity,
            "severity_class": severity_class,
            "message": message,
            "details": details,
            "details_html": details_html,
            "content": f"""
                <div class="alert {severity_class}">
                    <p><strong>Önem Derecesi:</strong> {severity.capitalize()}</p>
                    <p><strong>Mesaj:</strong> {message}</p>
                </div>
                {details_html}
            """
        }
        
        # HTML içeriği render et
        html_content = EmailTemplates.render_template("security_alert", context)
        
        return {
            "subject": title,
            "html": html_content,
            "text": text_content
        }