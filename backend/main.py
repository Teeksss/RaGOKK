# Last reviewed: 2025-04-29 11:06:31 UTC (User: Teekssseksiklikleri)
# main.py'nin middleware bölümüne ekleyeceğimiz kod:

from .middlewares.auth_middleware import AuthMiddleware
from .middlewares.rate_limiting import RateLimiter

# ... diğer middleware'ler ...

# Auth Middleware (önce çalışmalı)
app.add_middleware(AuthMiddleware)

# Rate Limiting Middleware (Auth sonra çalışmalı)
app.add_middleware(RateLimiter, max_requests=100, window_seconds=60)