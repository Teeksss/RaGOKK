# Last reviewed: 2025-04-29 12:17:43 UTC (User: TeeksssVektör)
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import asyncio
import hashlib
from typing import Dict, List, Any, Optional, Callable, Union, Tuple
import redis.asyncio as redis
import json
from dataclasses import dataclass
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class LimitStrategy(Enum):
    """Rate limiting stratejileri"""
    TOKEN_BUCKET = "token_bucket"  # Jeton kovası algoritması
    FIXED_WINDOW = "fixed_window"  # Sabit pencere algoritması
    SLIDING_WINDOW = "sliding_window"  # Kayan pencere algoritması
    LEAKY_BUCKET = "leaky_bucket"  # Sızdıran kova algoritması

@dataclass
class RateLimitRule:
    """Rate limiting kuralı"""
    requests: int  # Belirli sürede izin verilen maksimum istek sayısı
    period: int  # Süre (saniye)
    strategy: LimitStrategy = LimitStrategy.TOKEN_BUCKET  # Strateji
    cost_function: Optional[Callable[[Request], float]] = None  # İstek başına maliyet hesaplama


class AdvancedRateLimiter(BaseHTTPMiddleware):
    """
    Gelişmiş rate limiting middleware.
    Özellikler:
    - Çoklu strateji desteği (token bucket, fixed window, sliding window, leaky bucket)
    - Redis tabanlı distributed rate limiting
    - IP, kullanıcı ID veya özel anahtar bazlı limitleme
    - Belirli endpoint'ler için özel kurallar
    - İstek ağırlık faktörleri
    """
    
    def __init__(
        self, 
        app,
        rules: Dict[str, RateLimitRule] = None,
        default_rule: Optional[RateLimitRule] = None,
        key_function: Optional[Callable[[Request], str]] = None,
        redis_url: Optional[str] = None,
        exempt_patterns: List[str] = None,
        response_headers: bool = True
    ):
        """
        Args:
            app: FastAPI app
            rules: Path bazında kurallar
            default_rule: Varsayılan kural
            key_function: Rate limit anahtarı üretme fonksiyonu
            redis_url: Redis URL'si (distributed rate limiting için)
            exempt_patterns: Rate limiting'den muaf tutulacak path desenleri
            response_headers: Yanıt başlıklarına limit bilgisi ekle
        """
        super().__init__(app)
        self.rules = rules or {}
        self.default_rule = default_rule or RateLimitRule(
            requests=100,  # Varsayılan olarak dakikada 100 istek
            period=60,
            strategy=LimitStrategy.TOKEN_BUCKET
        )
        self.key_function = key_function or self._default_key_function
        self.exempt_patterns = exempt_patterns or []
        self.response_headers = response_headers
        
        # Redis bağlantısı
        self.redis = None
        if redis_url:
            self.redis = redis.from_url(redis_url, decode_responses=True)
        
        # Local state storage (if Redis not available)
        self.local_state = {}
    
    def _default_key_function(self, request: Request) -> str:
        """
        Rate limit anahtarını üretir (varsayılan: IP adresi)
        """
        # Get client IP from X-Forwarded-For or client host
        client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if not client_ip:
            client_ip = request.client.host if request.client else "unknown"
            
        # API anahtarı varsa kullan
        api_key = request.headers.get("X-Api-Key", "")
        if api_key:
            return f"api:{api_key}"
            
        # Kullanıcı kimlik doğrulama varsa kullan
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token_hash = hashlib.sha256(auth_header[7:].encode()).hexdigest()
            return f"user:{token_hash}"
            
        # Varsayılan olarak IP adresi
        return f"ip:{client_ip}"
    
    def _get_rule_for_path(self, path: str) -> RateLimitRule:
        """
        Path için uygun kuralı döndürür
        """
        # Tam eşleşme
        if path in self.rules:
            return self.rules[path]
            
        # Wildcard eşleşme
        for pattern, rule in self.rules.items():
            if pattern.endswith("*") and path.startswith(pattern[:-1]):
                return rule
        
        # Varsayılan
        return self.default_rule
    
    def _is_exempt(self, path: str) -> bool:
        """
        Path'in muaf olup olmadığını kontrol eder
        """
        # Tam eşleşme
        if path in self.exempt_patterns:
            return True
            
        # Wildcard eşleşme
        for pattern in self.exempt_patterns:
            if pattern.endswith("*") and path.startswith(pattern[:-1]):
                return True
                
        return False
    
    async def _check_token_bucket(
        self, 
        key: str, 
        rule: RateLimitRule,
        cost: float = 1.0
    ) -> Tuple[bool, int, int]:
        """
        Token bucket algoritması ile limit kontrolü
        
        Returns:
            Tuple[bool, int, int]: (allowed, remaining, retry_after)
        """
        tokens_key = f"{key}:tokens"
        last_update_key = f"{key}:last_update"
        
        now = time.time()
        
        if self.redis:
            # Redis'te dağıtık işleme
            lua_script = """
            local tokens_key = KEYS[1]
            local last_update_key = KEYS[2]
            local capacity = tonumber(ARGV[1])
            local rate = tonumber(ARGV[2])
            local now = tonumber(ARGV[3])
            local cost = tonumber(ARGV[4])
            
            local last_update = tonumber(redis.call('get', last_update_key) or 0)
            local tokens = tonumber(redis.call('get', tokens_key) or capacity)
            
            -- Geçen zamana göre token ekle
            local elapsed = now - last_update
            local new_tokens = math.min(capacity, tokens + elapsed * rate)
            
            -- Yeterli token varsa işlemi tamamla
            local allowed = 0
            local remaining = 0
            local retry_after = 0
            
            if new_tokens >= cost then
                -- İşlemi onayla
                new_tokens = new_tokens - cost
                allowed = 1
                remaining = math.floor(new_tokens)
            else
                -- Yeterli token yok, gereken süreyi hesapla
                retry_after = math.ceil((cost - new_tokens) / rate)
                remaining = 0
            end
            
            -- Değerleri güncelle
            redis.call('setex', tokens_key, 2 * capacity / rate, new_tokens)
            redis.call('setex', last_update_key, 2 * capacity / rate, now)
            
            return {allowed, remaining, retry_after}
            """
            
            # Rate hesapla (tokens per second)
            capacity = rule.requests
            rate = capacity / rule.period
            
            # Lua script çalıştır
            result = await self.redis.eval(
                lua_script,
                2,  # key sayısı
                tokens_key,
                last_update_key,
                capacity,
                rate,
                now,
                cost
            )
            
            allowed, remaining, retry_after = result
            return bool(allowed), remaining, retry_after
        else:
            # Yerel işleme
            if key not in self.local_state:
                self.local_state[key] = {
                    "tokens": rule.requests,
                    "last_update": now
                }
            
            # Geçen zamana göre token ekle
            state = self.local_state[key]
            elapsed = now - state["last_update"]
            state["tokens"] = min(rule.requests, state["tokens"] + elapsed * (rule.requests / rule.period))
            state["last_update"] = now
            
            # Yeterli token varsa işlemi tamamla
            if state["tokens"] >= cost:
                state["tokens"] -= cost
                return True, int(state["tokens"]), 0
            else:
                retry_after = (cost - state["tokens"]) / (rule.requests / rule.period)
                return False, 0, int(retry_after) + 1
    
    async def _check_fixed_window(
        self, 
        key: str, 
        rule: RateLimitRule,
        cost: float = 1.0
    ) -> Tuple[bool, int, int]:
        """
        Fixed window algoritması ile limit kontrolü
        
        Returns:
            Tuple[bool, int, int]: (allowed, remaining, retry_after)
        """
        counter_key = f"{key}:counter"
        window_key = f"{key}:window"
        
        now = int(time.time())
        window_start = now - (now % rule.period)
        
        if self.redis:
            # Redis'te dağıtık işleme
            lua_script = """
            local counter_key = KEYS[1]
            local window_key = KEYS[2]
            local capacity = tonumber(ARGV[1])
            local window_start = tonumber(ARGV[2])
            local period = tonumber(ARGV[3])
            local cost = tonumber(ARGV[4])
            
            -- Mevcut pencereyi kontrol et
            local current_window = tonumber(redis.call('get', window_key) or -1)
            
            -- Pencere değişti mi?
            if current_window ~= window_start then
                -- Yeni pencere, sayacı sıfırla
                redis.call('setex', counter_key, period, 0)
                redis.call('setex', window_key, period, window_start)
                current_window = window_start
            end
            
            -- Sayaç değerini al
            local counter = tonumber(redis.call('get', counter_key) or 0)
            
            -- Limit kontrolü
            local allowed = 0
            local remaining = 0
            local retry_after = 0
            
            if counter + cost <= capacity then
                -- İşlemi onayla
                redis.call('incrby', counter_key, cost)
                allowed = 1
                remaining = capacity - (counter + cost)
            else
                -- Limit aşıldı, kalan süreyi hesapla
                retry_after = period - (tonumber(redis.call('ttl', counter_key)))
                remaining = 0
            end
            
            return {allowed, remaining, retry_after}
            """
            
            # Lua script çalıştır
            result = await self.redis.eval(
                lua_script,
                2,  # key sayısı
                counter_key,
                window_key,
                rule.requests,
                window_start,
                rule.period,
                cost
            )
            
            allowed, remaining, retry_after = result
            return bool(allowed), remaining, retry_after
        else:
            # Yerel işleme
            if key not in self.local_state or self.local_state[key].get("window", -1) != window_start:
                self.local_state[key] = {
                    "counter": 0,
                    "window": window_start
                }
            
            # Limit kontrolü
            state = self.local_state[key]
            if state["counter"] + cost <= rule.requests:
                state["counter"] += cost
                return True, int(rule.requests - state["counter"]), 0
            else:
                retry_after = rule.period - (now - window_start)
                return False, 0, retry_after
    
    async def _check_sliding_window(
        self, 
        key: str, 
        rule: RateLimitRule,
        cost: float = 1.0
    ) -> Tuple[bool, int, int]:
        """
        Sliding window algoritması ile limit kontrolü
        
        Returns:
            Tuple[bool, int, int]: (allowed, remaining, retry_after)
        """
        now = time.time()
        
        if self.redis:
            # Redis'te dağıtık işleme - Sorted Set kullanarak zaman damgalarını sakla
            lua_script = """
            local key = KEYS[1]
            local now = tonumber(ARGV[1])
            local window = tonumber(ARGV[2])
            local capacity = tonumber(ARGV[3])
            local cost = tonumber(ARGV[4])
            
            -- Pencere dışındaki eski değerleri temizle
            redis.call('zremrangebyscore', key, '-inf', now - window)
            
            -- Mevcut sayım
            local count = tonumber(redis.call('zcard', key))
            
            -- Limit kontrolü
            local allowed = 0
            local remaining = 0
            local retry_after = 0
            
            if count + cost <= capacity then
                -- İşlemi onayla
                for i = 1, cost do
                    redis.call('zadd', key, now + i/1000, now .. '-' .. i)
                end
                redis.call('expire', key, window)
                allowed = 1
                remaining = capacity - (count + cost)
            else
                -- En eski öğeyi bul ve tekrar deneme süresini hesapla
                local oldest = redis.call('zrange', key, 0, 0, 'WITHSCORES')
                if #oldest >= 2 then
                    retry_after = math.ceil(tonumber(oldest[2]) + window - now)
                else
                    retry_after = window
                end
                remaining = 0
            end
            
            return {allowed, remaining, retry_after}
            """
            
            # Lua script çalıştır
            result = await self.redis.eval(
                lua_script,
                1,  # key sayısı
                f"{key}:sliding",
                now,
                rule.period,
                rule.requests,
                cost
            )
            
            allowed, remaining, retry_after = result
            return bool(allowed), remaining, retry_after
        else:
            # Yerel işleme - zaman damgalarını listede sakla
            if key not in self.local_state:
                self.local_state[key] = []
            
            # Pencere dışındakileri temizle
            window_start = now - rule.period
            self.local_state[key] = [ts for ts in self.local_state[key] if ts > window_start]
            
            # Limit kontrolü
            if len(self.local_state[key]) + cost <= rule.requests:
                # İşlemi onayla
                for _ in range(int(cost)):
                    self.local_state[key].append(now)
                return True, int(rule.requests - len(self.local_state[key])), 0
            else:
                # En eski zaman damgasına göre tekrar deneme süresini hesapla
                if len(self.local_state[key]) > 0:
                    oldest = min(self.local_state[key])
                    retry_after = int(oldest + rule.period - now) + 1
                else:
                    retry_after = int(rule.period)
                return False, 0, retry_after
    
    async def _check_leaky_bucket(
        self, 
        key: str, 
        rule: RateLimitRule,
        cost: float = 1.0
    ) -> Tuple[bool, int, int]:
        """
        Leaky bucket algoritması ile limit kontrolü
        
        Returns:
            Tuple[bool, int, int]: (allowed, remaining, retry_after)
        """
        level_key = f"{key}:level"
        last_leak_key = f"{key}:last_leak"
        
        now = time.time()
        
        if self.redis:
            # Redis'te dağıtık işleme
            lua_script = """
            local level_key = KEYS[1]
            local last_leak_key = KEYS[2]
            local capacity = tonumber(ARGV[1])
            local leak_rate = tonumber(ARGV[2])
            local now = tonumber(ARGV[3])
            local cost = tonumber(ARGV[4])
            
            local last_leak = tonumber(redis.call('get', last_leak_key) or now)
            local level = tonumber(redis.call('get', level_key) or 0)
            
            -- Geçen zamana göre sızıntıyı hesapla
            local elapsed = now - last_leak
            local leaked = math.min(level, elapsed * leak_rate)
            level = level - leaked
            
            -- Limit kontrolü
            local allowed = 0
            local remaining = 0
            local retry_after = 0
            
            if level + cost <= capacity then
                -- İşlemi onayla
                level = level + cost
                allowed = 1
                remaining = math.floor(capacity - level)
            else
                -- Yeterli alan yok, gereken süreyi hesapla
                retry_after = math.ceil((level + cost - capacity) / leak_rate)
                remaining = 0
            end
            
            -- Değerleri güncelle
            local ttl = math.ceil(capacity / leak_rate * 2)
            redis.call('setex', level_key, ttl, level)
            redis.call('setex', last_leak_key, ttl, now)
            
            return {allowed, remaining, retry_after}
            """
            
            # Leak rate hesapla (tokens per second)
            capacity = rule.requests
            leak_rate = capacity / rule.period
            
            # Lua script çalıştır
            result = await self.redis.eval(
                lua_script,
                2,  # key sayısı
                level_key,
                last_leak_key,
                capacity,
                leak_rate,
                now,
                cost
            )
            
            allowed, remaining, retry_after = result
            return bool(allowed), remaining, retry_after
        else:
            # Yerel işleme
            if key not in self.local_state:
                self.local_state[key] = {
                    "level": 0,
                    "last_leak": now
                }
            
            # Geçen zamana göre sızıntıyı hesapla
            state = self.local_state[key]
            elapsed = now - state["last_leak"]
            leak_rate = rule.requests / rule.period
            leaked = min(state["level"], elapsed * leak_rate)
            state["level"] -= leaked
            state["last_leak"] = now
            
            # Limit kontrolü
            if state["level"] + cost <= rule.requests:
                state["level"] += cost
                return True, int(rule.requests - state["level"]), 0
            else:
                retry_after = (state["level"] + cost - rule.requests) / leak_rate
                return False, 0, int(retry_after) + 1
    
    async def _check_rate_limit(
        self, 
        key: str, 
        rule: RateLimitRule,
        cost: float = 1.0
    ) -> Tuple[bool, int, int]:
        """
        Rate limit kontrolü yapar
        
        Args:
            key: Rate limit anahtarı
            rule: Uygulanacak kural
            cost: İstek maliyeti
            
        Returns:
            Tuple[bool, int, int]: (allowed, remaining, retry_after)
        """
        strategy = rule.strategy
        
        if strategy == LimitStrategy.TOKEN_BUCKET:
            return await self._check_token_bucket(key, rule, cost)
        elif strategy == LimitStrategy.FIXED_WINDOW:
            return await self._check_fixed_window(key, rule, cost)
        elif strategy == LimitStrategy.SLIDING_WINDOW:
            return await self._check_sliding_window(key, rule, cost)
        elif strategy == LimitStrategy.LEAKY_BUCKET:
            return await self._check_leaky_bucket(key, rule, cost)
        else:
            raise ValueError(f"Unsupported rate limit strategy: {strategy}")
            
    async def dispatch(self, request: Request, call_next):
        # Path kontrolü
        path = request.url.path
        if self._is_exempt(path):
            # Muaf
            return await call_next(request)
        
        # Kural seç
        rule = self._get_rule_for_path(path)
        
        # Rate limit anahtarı
        key = f"ratelimit:{self.key_function(request)}"
        
        # İstek maliyetini hesapla
        cost = 1.0
        if rule.cost_function:
            cost = rule.cost_function(request)
        
        # Rate limit kontrolü
        allowed, remaining, retry_after = await self._check_rate_limit(key, rule, cost)
        
        if allowed:
            # İsteğe izin verildi
            response = await call_next(request)
            
            # Yanıt başlıklarını ekle (isteğe bağlı)
            if self.response_headers:
                response.headers["X-RateLimit-Limit"] = str(rule.requests)
                response.headers["X-RateLimit-Remaining"] = str(remaining)
                response.headers["X-RateLimit-Reset"] = str(int(time.time() + retry_after))
                
            return response
        else:
            # Rate limit aşıldı
            content = {
                "detail": "Rate limit exceeded",
                "retry_after": retry_after
            }
            
            response = Response(
                content=json.dumps(content),
                status_code=429,
                media_type="application/json"
            )
            
            # Başlıkları ekle
            if self.response_headers:
                response.headers["X-RateLimit-Limit"] = str(rule.requests)
                response.headers["X-RateLimit-Remaining"] = "0"
                response.headers["X-RateLimit-Reset"] = str(int(time.time() + retry_after))
                response.headers["Retry-After"] = str(retry_after)
                
            return response