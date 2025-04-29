# Last reviewed: 2025-04-29 12:35:57 UTC (User: TeeksssVisual Diff)
from celery import Celery
import os
import logging
from kombu import Exchange, Queue

# Ortam değişkenlerinden yapılandırma
broker_url = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
result_backend = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
task_serializer = os.environ.get('CELERY_TASK_SERIALIZER', 'json')
result_serializer = os.environ.get('CELERY_RESULT_SERIALIZER', 'json')
accept_content = os.environ.get('CELERY_ACCEPT_CONTENT', 'json').split(',')
timezone = os.environ.get('CELERY_TIMEZONE', 'Europe/Istanbul')
task_time_limit = int(os.environ.get('CELERY_TASK_TIME_LIMIT', 3600))  # 1 saat
task_soft_time_limit = int(os.environ.get('CELERY_TASK_SOFT_TIME_LIMIT', 3300))  # 55 dakika

# Öncelik kuyrukları
task_queues = (
    Queue('high', Exchange('high'), routing_key='high'),
    Queue('default', Exchange('default'), routing_key='default'),
    Queue('low', Exchange('low'), routing_key='low'),
)

task_default_queue = 'default'
task_default_exchange = 'default'
task_default_routing_key = 'default'

task_routes = {
    # Yüksek öncelikli
    'backend.tasks.document_tasks.process_uploaded_document': {'queue': 'high'},
    'backend.tasks.notification_tasks.send_urgent_notification': {'queue': 'high'},
    
    # Orta öncelikli (varsayılan)
    'backend.tasks.document_tasks.generate_document_embeddings': {'queue': 'default'},
    'backend.tasks.indexing_tasks.index_document': {'queue': 'default'},
    
    # Düşük öncelikli
    'backend.tasks.maintenance_tasks.cleanup_old_files': {'queue': 'low'},
    'backend.tasks.analytics_tasks.generate_usage_report': {'queue': 'low'},
}

# Logger yapılandırması
logger = logging.getLogger('celery')

# Celery instance oluştur
app = Celery('rag_base')

# Yapılandırma
app.conf.update(
    broker_url=broker_url,
    result_backend=result_backend,
    task_serializer=task_serializer,
    result_serializer=result_serializer,
    accept_content=accept_content,
    timezone=timezone,
    task_time_limit=task_time_limit,
    task_soft_time_limit=task_soft_time_limit,
    task_queues=task_queues,
    task_default_queue=task_default_queue,
    task_default_exchange=task_default_exchange,
    task_default_routing_key=task_default_routing_key,
    task_routes=task_routes,
    
    # Görev yürütme seçenekleri
    task_acks_late=True,  # Görev tamamlandığında onaylanır (retry güvenliği için)
    task_reject_on_worker_lost=True,  # Worker kaybedilirse görevi reddet
    task_track_started=True,  # Görev durumunu izle
    
    # Performans ayarları
    worker_prefetch_multiplier=4,  # Worker başına önceden alınan görev sayısı
    worker_concurrency=os.cpu_count(),  # CPU sayısı kadar eşzamanlı worker
    
    # Loglama
    worker_hijack_root_logger=False,  # Root logger'ı değiştirme
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    
    # Hata işleme
    task_annotations={
        '*': {
            'rate_limit': '100/m',  # Varsayılan görev hız sınırı
            'max_retries': 3,  # Maksimum yeniden deneme sayısı
            'retry_backoff': True,  # Üstel geri çekilme
            'retry_backoff_max': 600,  # Maksimum geri çekilme süresi (saniye)
            'retry_jitter': True,  # Geri çekilme süresinde rastgelelik
        }
    },
)

# Modülleri otomatik keşfet
app.autodiscover_tasks(['backend.tasks'])

if __name__ == '__main__':
    app.start()