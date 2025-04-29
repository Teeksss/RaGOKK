# Last reviewed: 2025-04-29 10:51:12 UTC (User: TeeksssPrioritizationTest.js)
from fastapi import Request, HTTPException, status
import time
import asyncio
from typing import Dict, List, Tuple, Optional, Any
from fastapi.responses import JSONResponse

class RateLimiter:
    """
    Basit bir rate limiting middleware.
    İstemci IP'si, endpoint ve kullanıcıya göre istekleri sınırlar.
    """
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests  # Varsayılan pencere başına maksimum istek sayısı
        self.window_seconds = window_seconds  # Varsayılan pencere süresi (saniye)
        
        # Endpoint bazlı limitler (öncelik sırası: endpoint > global)
        self.endpoint_limits = {
            "/api/api-keys/verify": (5, 60),  # 1 dakikada en fazla 5 doğrulama
            "/api/security-logs": (20, 60),   # 1 dakikada en fazla 20 log sorgusu
            "/api/query/prioritization-test": (10, 60)  # 1 dakikada en fazla 10 test
        }
        
        # İstek kayıtları: {key: [(timestamp1, count1), (timestamp2, count2), ...]}
        # key formatı: "ip:endpoint" veya "user_id:endpoint"
        self.request_records: Dict[str, List[Tuple[float, int]]] = {}
        
        # Temizlik işlemi için task (eski kayıtları temizler)
        asyncio.create_task(self._cleanup_records())
    
    async def _cleanup_records(self):
        """
        Belirli aralıklarla eski kayıtları temizleyen asenkron task
        """
        while True:
            await asyncio.sleep(60)  # Her dakika çalıştır
            
            now = time.time()
            keys_to_remove = []
            
            # Tüm kayıtları kontrol et
            for key, timestamps in self.request_records.items():
                # Şu anki pencereden eski timestamp'ları filtrele
                self.request_records[key] = [
                    (ts, count) for ts, count in timestamps 
                    if now - ts < self.window_seconds
                ]
                
                # Kayıt boşsa, silmek için işaretle
                if not self.request_records[key]:
                    keys_to_remove.append(key)
            
            # Boş kayıtları sil
            for key in keys_to_remove:
                del self.request_records[key]
    
    async def __call__(self, request: Request, call_next):
        """
        Middleware fonksiyonu - istek sayısını kontrol eder ve sınırlar
        """
        # İstek yolunu al
        path = request.url.path
        
        # Admin statik dosyaları ve sağlık kontrolleri için atla
        if path.startswith(("/static/", "/favicon.ico", "/_next/")) or path == "/":
            return await call_next(request)
        
        # IP ve kullanıcı bilgilerini al
        client_ip = request.client.host if request.client else "unknown"
        
        # Endpoint'e özel limitleri al veya varsayılanları kullan
        max_requests, window_seconds = self.endpoint_limits.get(
            path, (self.max_requests, self.window_seconds)
        )
        
        # Kullanıcı ID'si (kimlik doğrulama işlenmişse)
        user_id = None
        if hasattr(request.state, "user") and request.state.user:
            user_id = str(request.state.user.id)
        
        # Rate limit anahtarını oluştur
        # Kullanıcı oturum açmışsa user_id, değilse IP kullan
        limit_key = f"{user_id if user_id else client_ip}:{path}"
        
        # Şimdiki zaman
        now = time.time()
        
        # İstek kaydını al veya yeni oluştur
        records = self.request_records.get(limit_key, [])
        
        # Mevcut penceredeki kayıtları filtrele
        current_window_records = [
            (ts, count) for ts, count in records 
            if now - ts < window_seconds
        ]
        
        # Toplam istek sayısını hesapla
        total_requests = sum(count for _, count in current_window_records)
        
        # İstek limitini aştıysa
        if total_requests >= max_requests:
            # Kalan süreyi hesapla
            if current_window_records:
                oldest_timestamp = min(ts for ts, _ in current_window_records)
                reset_time = oldest_timestamp + window_seconds
                retry_after = int(reset_time - now) + 1
            else:
                retry_after = window_seconds
                
            # Rate limit yanıtı döndür
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Too many requests",
                    "limit": max_requests,
                    "window_seconds": window_seconds,
                    "retry_after": retry_after
                },
                headers={"Retry-After": str(retry_after)}
            )
        
        # İstek sayısını güncelle (son kaydı arttır veya yeni oluştur)
        if current_window_records and current_window_records[-1][0] > now - 1:
            # Son saniye içinde istek varsa, sayıyı artır
            current_window_records[-1] = (current_window_records[-1][0], current_window_records[-1][1] + 1)
        else:
            # Yeni kayıt ekle
            current_window_records.append((now, 1))
        
        # Güncellenen kayıtları kaydet
        self.request_records[limit_key] = current_window_records
        
        # İsteği işle
        response = await call_next(request)
        
        # X-RateLimit başlıklarını ekle
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(max_requests - total_requests - 1)
        response.headers["X-RateLimit-Reset"] = str(int(now + window_seconds))
        
        return response