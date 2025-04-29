# Last reviewed: 2025-04-29 12:57:38 UTC (User: Teeksssprometheus)
from prometheus_client import Counter, Histogram, Gauge, Info, Summary, REGISTRY
from prometheus_client.exposition import generate_latest
from prometheus_client import multiprocess, CollectorRegistry
import time
import os
import psutil
import logging
from typing import Dict, Any, Optional, List
from fastapi import Request, Response
import socket
import inspect
import functools

logger = logging.getLogger(__name__)

class PrometheusMetrics:
    """
    Prometheus metriklerini yöneten servis sınıfı.
    
    Özellikler:
    - HTTP istek takibi
    - Bellek ve CPU kullanımını izleme
    - Doküman işleme metrikleri
    - Vektör veritabanı performansı 
    - Kullanıcı etkileşimleri
    - Arama ve vektörizasyon metrikleri
    """
    
    def __init__(self, app_name: str = "ragbase", enable_default_metrics: bool = True):
        """
        Args:
            app_name: Uygulama adı (etiketlerde kullanılır)
            enable_default_metrics: Varsayılan metrikleri etkinleştir
        """
        self.app_name = app_name
        
        # Çoklu işlem desteği için registry
        if 'prometheus_multiproc_dir' in os.environ:
            self.registry = CollectorRegistry()
            multiprocess.MultiProcessCollector(self.registry)
        else:
            self.registry = REGISTRY
        
        # Standart metrikler
        self.http_requests_total = Counter(
            'http_requests_total', 
            'Total count of HTTP requests', 
            ['method', 'endpoint', 'status_code', 'app_name']
        )
        
        self.http_request_duration_seconds = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint', 'app_name'],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, 30.0, 60.0, float('inf'))
        )
        
        self.http_requests_in_progress = Gauge(
            'http_requests_in_progress',
            'Number of HTTP requests in progress',
            ['method', 'endpoint', 'app_name']
        )
        
        # Sistem metrikleri
        self.memory_usage_bytes = Gauge(
            'memory_usage_bytes', 
            'Memory usage in bytes', 
            ['type', 'app_name']
        )
        
        self.cpu_usage_percent = Gauge(
            'cpu_usage_percent', 
            'CPU usage in percent', 
            ['app_name']
        )
        
        # Doküman işleme metrikleri
        self.document_process_total = Counter(
            'document_process_total',
            'Total number of documents processed',
            ['status', 'source_type', 'app_name']
        )
        
        self.document_process_duration_seconds = Histogram(
            'document_process_duration_seconds',
            'Document processing duration in seconds',
            ['source_type', 'app_name'],
            buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 7.5, 10.0, 30.0, 60.0, 120.0, 300.0, float('inf'))
        )
        
        # Vektör veritabanı metrikleri
        self.vector_db_operation_total = Counter(
            'vector_db_operation_total',
            'Total number of vector database operations',
            ['operation', 'status', 'db_type', 'app_name']
        )
        
        self.vector_db_operation_duration_seconds = Histogram(
            'vector_db_operation_duration_seconds',
            'Vector database operation duration in seconds',
            ['operation', 'db_type', 'app_name'],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, float('inf'))
        )
        
        # Arama metrikleri
        self.search_total = Counter(
            'search_total',
            'Total number of searches',
            ['search_type', 'status', 'app_name']
        )
        
        self.search_duration_seconds = Histogram(
            'search_duration_seconds',
            'Search duration in seconds',
            ['search_type', 'app_name'],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, float('inf'))
        )
        
        # Embedding metrikleri
        self.embedding_creation_total = Counter(
            'embedding_creation_total',
            'Total number of embeddings created',
            ['model', 'status', 'app_name']
        )
        
        self.embedding_creation_duration_seconds = Histogram(
            'embedding_creation_duration_seconds',
            'Embedding creation duration in seconds',
            ['model', 'app_name'],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, float('inf'))
        )
        
        # Kullanıcı metrikleri
        self.active_users_total = Gauge(
            'active_users_total',
            'Total number of active users',
            ['app_name']
        )
        
        self.user_activity_total = Counter(
            'user_activity_total',
            'Total number of user activities',
            ['activity_type', 'app_name']
        )
        
        # Bellek önbellek metrikleri
        self.cache_hits_total = Counter(
            'cache_hits_total',
            'Total number of cache hits',
            ['cache_type', 'app_name']
        )
        
        self.cache_misses_total = Counter(
            'cache_misses_total',
            'Total number of cache misses',
            ['cache_type', 'app_name']
        )
        
        self.cache_ratio = Gauge(
            'cache_ratio',
            'Cache hit ratio',
            ['cache_type', 'app_name']
        )
        
        # Uygulama bilgileri
        self.app_info = Info('app_info', 'Application information')
        self.app_info.info({
            'app_name': app_name,
            'hostname': socket.gethostname(),
            'pid': str(os.getpid())
        })
        
        # Varsayılan metrikleri etkinleştir
        if enable_default_metrics:
            self.start_collecting_default_metrics()
    
    def instrument(self, app):
        """
        FastAPI uygulamasını metrik toplama için enstrümante eder
        
        Args:
            app: FastAPI uygulaması
            
        Returns:
            app: Enstrümante edilmiş FastAPI uygulaması
        """
        @app.middleware("http")
        async def metrics_middleware(request: Request, call_next):
            # Endpoint ve method
            method = request.method
            endpoint = request.url.path
            
            # İstek başlangıç zamanı
            start_time = time.time()
            
            # İşlemdeki istekleri takip et
            in_progress_labels = {'method': method, 'endpoint': endpoint, 'app_name': self.app_name}
            self.http_requests_in_progress.labels(**in_progress_labels).inc()
            
            try:
                # İsteği işle
                response = await call_next(request)
                
                # İşlem süresi
                duration = time.time() - start_time
                
                # Metrikleri kaydet
                status_code = response.status_code
                request_labels = {'method': method, 'endpoint': endpoint, 'status_code': status_code, 'app_name': self.app_name}
                duration_labels = {'method': method, 'endpoint': endpoint, 'app_name': self.app_name}
                
                self.http_requests_total.labels(**request_labels).inc()
                self.http_request_duration_seconds.labels(**duration_labels).observe(duration)
                
                return response
            except Exception as e:
                # Hata durumunda 500 koduyla işaretle
                status_code = 500
                request_labels = {'method': method, 'endpoint': endpoint, 'status_code': status_code, 'app_name': self.app_name}
                self.http_requests_total.labels(**request_labels).inc()
                raise
            finally:
                # İşlemi tamamla
                self.http_requests_in_progress.labels(**in_progress_labels).dec()
        
        # Metrics endpoint ekle
        @app.get("/metrics", include_in_schema=False)
        async def metrics():
            # Sistem metriklerini güncelle
            self.update_system_metrics()
            
            # Metrikleri oluştur
            registry = self.registry if hasattr(self, 'registry') else REGISTRY
            metrics_data = generate_latest(registry)
            return Response(content=metrics_data, media_type="text/plain")
        
        return app
    
    def update_system_metrics(self):
        """Sistem metriklerini günceller (bellek ve CPU kullanımı)"""
        try:
            # Bellek kullanımı
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            self.memory_usage_bytes.labels(type='rss', app_name=self.app_name).set(memory_info.rss)
            self.memory_usage_bytes.labels(type='vms', app_name=self.app_name).set(memory_info.vms)
            
            # CPU kullanımı
            cpu_percent = process.cpu_percent(interval=None) / psutil.cpu_count()
            self.cpu_usage_percent.labels(app_name=self.app_name).set(cpu_percent)
            
        except Exception as e:
            logger.error(f"Error updating system metrics: {e}")
    
    def start_collecting_default_metrics(self):
        """
        Varsayılan sistem metriklerini toplamaya başlar
        (Ayrı bir thread'de çalışır)
        """
        try:
            from prometheus_client import start_http_server
            import threading
            
            def collect_metrics():
                # Her 15 saniyede bir sistem metriklerini güncelle
                while True:
                    try:
                        self.update_system_metrics()
                    except Exception as e:
                        logger.error(f"Error collecting metrics: {e}")
                    
                    time.sleep(15)
            
            # Arkaplanda metrik toplama thread'i başlat
            metrics_thread = threading.Thread(target=collect_metrics, daemon=True)
            metrics_thread.start()
            logger.info("Started background metrics collection thread")
            
        except Exception as e:
            logger.error(f"Failed to start background metrics collection: {e}")
    
    def track_document_process(self, source_type: str, duration: float, status: str = "success"):
        """
        Doküman işleme metriklerini kaydeder
        
        Args:
            source_type: Doküman türü
            duration: İşlem süresi (saniye)
            status: İşlem durumu
        """
        self.document_process_total.labels(status=status, source_type=source_type, app_name=self.app_name).inc()
        
        if status == "success":
            self.document_process_duration_seconds.labels(source_type=source_type, app_name=self.app_name).observe(duration)
    
    def track_vector_db_operation(self, operation: str, db_type: str, duration: float, status: str = "success"):
        """
        Vektör veritabanı işlemlerini kaydeder
        
        Args:
            operation: İşlem türü (insert, search, delete, vb.)
            db_type: Veritabanı türü
            duration: İşlem süresi (saniye)
            status: İşlem durumu
        """
        self.vector_db_operation_total.labels(operation=operation, status=status, db_type=db_type, app_name=self.app_name).inc()
        
        if status == "success":
            self.vector_db_operation_duration_seconds.labels(operation=operation, db_type=db_type, app_name=self.app_name).observe(duration)
    
    def track_search(self, search_type: str, duration: float, status: str = "success"):
        """
        Arama işlemlerini kaydeder
        
        Args:
            search_type: Arama türü (vector, full_text, hybrid)
            duration: İşlem süresi (saniye)
            status: İşlem durumu
        """
        self.search_total.labels(search_type=search_type, status=status, app_name=self.app_name).inc()
        
        if status == "success":
            self.search_duration_seconds.labels(search_type=search_type, app_name=self.app_name).observe(duration)
    
    def track_embedding_creation(self, model: str, duration: float, status: str = "success"):
        """
        Embedding oluşturma işlemlerini kaydeder
        
        Args:
            model: Embedding modeli
            duration: İşlem süresi (saniye)
            status: İşlem durumu
        """
        self.embedding_creation_total.labels(model=model, status=status, app_name=self.app_name).inc()
        
        if status == "success":
            self.embedding_creation_duration_seconds.labels(model=model, app_name=self.app_name).observe(duration)
    
    def track_user_activity(self, activity_type: str):
        """
        Kullanıcı aktivitelerini kaydeder
        
        Args:
            activity_type: Aktivite türü
        """
        self.user_activity_total.labels(activity_type=activity_type, app_name=self.app_name).inc()
    
    def set_active_users(self, count: int):
        """
        Aktif kullanıcı sayısını ayarlar
        
        Args:
            count: Kullanıcı sayısı
        """
        self.active_users_total.labels(app_name=self.app_name).set(count)
    
    def track_cache(self, cache_type: str, hit: bool):
        """
        Önbellek hit/miss olaylarını kaydeder
        
        Args:
            cache_type: Önbellek türü
            hit: True ise hit, False ise miss
        """
        if hit:
            self.cache_hits_total.labels(cache_type=cache_type, app_name=self.app_name).inc()
        else:
            self.cache_misses_total.labels(cache_type=cache_type, app_name=self.app_name).inc()
        
        # Oranı güncelle
        try:
            hits = self.cache_hits_total.labels(cache_type=cache_type, app_name=self.app_name)._value.get()
            misses = self.cache_misses_total.labels(cache_type=cache_type, app_name=self.app_name)._value.get()
            total = hits + misses
            
            if total > 0:
                self.cache_ratio.labels(cache_type=cache_type, app_name=self.app_name).set(hits / total)
        except:
            pass

# Metrik toplama için dekoratörler
def track_time(metric_func=None, **kwargs):
    """
    Fonksiyon çalışma süresini ölçen ve metrik olarak kaydeden dekoratör
    
    Args:
        metric_func: Metriği kaydeden fonksiyon
        **kwargs: metric_func'a iletilecek parametreler
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **func_kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **func_kwargs)
                duration = time.time() - start_time
                
                # Metriği kaydet
                if metric_func:
                    metric_func(duration=duration, status="success", **kwargs)
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                
                # Metriği kaydet (hata ile)
                if metric_func:
                    metric_func(duration=duration, status="error", **kwargs)
                
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **func_kwargs):
            start_time = time.time()
            try:
                result = func(*args, **func_kwargs)
                duration = time.time() - start_time
                
                # Metriği kaydet
                if metric_func:
                    metric_func(duration=duration, status="success", **kwargs)
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                
                # Metriği kaydet (hata ile)
                if metric_func:
                    metric_func(duration=duration, status="error", **kwargs)
                
                raise
        
        # Asenkron mu senkron mu kontrol et
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator