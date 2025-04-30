// Last reviewed: 2025-04-30 11:32:10 UTC (User: TeeksssOrta)
import { useState, useEffect, useCallback, useMemo } from 'react';

/**
 * Async işlemi memorize eden özel hook
 * @param asyncFn Memorize edilecek async fonksiyon
 * @param deps Bağımlılık dizisi
 * @param options Seçenekler
 * @returns [data, loading, error, refresh] tuple'ı
 */
interface AsyncMemoOptions {
  refreshInterval?: number;
  initialData?: any;
  cacheKey?: string;
  cacheTTL?: number;
  onSuccess?: (data: any) => void;
  onError?: (error: Error) => void;
  retry?: {
    count: number;
    delay: number;
  };
}

export function useAsyncMemo<T>(
  asyncFn: () => Promise<T>,
  deps: any[] = [],
  options: AsyncMemoOptions = {}
): [T | undefined, boolean, Error | null, () => Promise<void>] {
  const [data, setData] = useState<T | undefined>(options.initialData);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);
  const [retries, setRetries] = useState<number>(0);

  // Çağrı sayısını ve son çağrı zamanını takip et
  const callCountRef = React.useRef<number>(0);
  const lastCallTimeRef = React.useRef<number>(Date.now());

  // Cache'den veri yükleme
  useEffect(() => {
    if (options.cacheKey) {
      try {
        const cachedItem = localStorage.getItem(`async_memo_${options.cacheKey}`);
        if (cachedItem) {
          const { data: cachedData, timestamp } = JSON.parse(cachedItem);
          const isExpired = options.cacheTTL 
            ? Date.now() - timestamp > options.cacheTTL 
            : false;
          
          if (!isExpired) {
            setData(cachedData);
            setLoading(false);
            return;
          }
        }
      } catch (error) {
        console.warn('Error reading from cache:', error);
      }
    }
  }, [options.cacheKey, options.cacheTTL]);

  // İşlevi hafızaya alarak performans iyileştirmesi
  const memoizedCallback = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    // Çağrı sayısını artır ve son çağrı zamanını güncelle
    callCountRef.current += 1;
    lastCallTimeRef.current = Date.now();

    try {
      const result = await asyncFn();
      
      // Cache'e kaydet
      if (options.cacheKey) {
        try {
          localStorage.setItem(
            `async_memo_${options.cacheKey}`,
            JSON.stringify({
              data: result,
              timestamp: Date.now()
            })
          );
        } catch (error) {
          console.warn('Error writing to cache:', error);
        }
      }
      
      setData(result);
      setRetries(0);
      
      // Başarı callback'i
      if (options.onSuccess) {
        options.onSuccess(result);
      }
    } catch (error) {
      console.error('Async memo error:', error);
      setError(error as Error);
      
      // Yeniden deneme
      if (options.retry && retries < options.retry.count) {
        setTimeout(() => {
          setRetries(prev => prev + 1);
        }, options.retry.delay);
        
        return;
      }
      
      // Hata callback'i
      if (options.onError) {
        options.onError(error as Error);
      }
    } finally {
      setLoading(false);
    }
  }, [asyncFn, options, retries]);
  
  // Yeniden deneme sayısı değiştiğinde işlevi tekrar çalıştır
  useEffect(() => {
    if (retries > 0) {
      memoizedCallback();
    }
  }, [retries, memoizedCallback]);

  // İlk yükleme ve bağımlılık değişikliklerinde çalıştır
  useEffect(() => {
    memoizedCallback();
    
    // Belirli aralıklarla yenileme
    let intervalId: NodeJS.Timeout | null = null;
    
    if (options.refreshInterval) {
      intervalId = setInterval(() => {
        memoizedCallback();
      }, options.refreshInterval);
    }
    
    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [...deps, memoizedCallback]);

  // Manuel yenileme fonksiyonu
  const refresh = useCallback(async () => {
    // Son çağrıdan bu yana geçen süre
    const timeSinceLastCall = Date.now() - lastCallTimeRef.current;
    
    // Debounce: Son çağrıdan bu yana 500ms geçmediyse engelle
    if (timeSinceLastCall < 500) {
      console.warn('Refresh call debounced, too many calls in short time');
      return;
    }
    
    await memoizedCallback();
  }, [memoizedCallback]);

  // Performans metrikleri
  useEffect(() => {
    // 100 çağrıdan sonra performans metriklerini raporla
    if (callCountRef.current === 100) {
      console.info(`Performance metrics for useAsyncMemo:`, {
        callCount: callCountRef.current,
        avgTimeBetweenCalls: Date.now() - lastCallTimeRef.current / callCountRef.current,
      });
    }
  }, [loading]);

  return [data, loading, error, refresh];
}

/**
 * Seçici useMemo hook'u
 * @param factory Değer üreten fonksiyon
 * @param deps Bağımlılık dizisi
 * @param compareFn Özel karşılaştırma fonksiyonu
 * @returns Memorize edilmiş değer
 */
export function useMemoCompare<T>(
  factory: () => T,
  deps: any[],
  compareFn: (prevDeps: any[], nextDeps: any[]) => boolean
): T {
  const ref = React.useRef<{ deps: any[]; value: T }>({
    deps: [],
    value: undefined as unknown as T,
  });

  const depsChanged = !ref.current.deps.length || 
    ref.current.deps.length !== deps.length || 
    !compareFn(ref.current.deps, deps);

  if (depsChanged) {
    ref.current.deps = deps;
    ref.current.value = factory();
  }

  return ref.current.value;
}

/**
 * Derin karşılaştırma yapan useMemo
 * @param factory Değer üreten fonksiyon
 * @param deps Bağımlılık dizisi
 * @returns Memorize edilmiş değer
 */
export function useDeepMemo<T>(factory: () => T, deps: any[]): T {
  return useMemoCompare(factory, deps, (prevDeps, nextDeps) => {
    return JSON.stringify(prevDeps) === JSON.stringify(nextDeps);
  });
}

/**
 * Ağır hesaplama işlevlerini önbelleğe alan bir yardımcı
 * @param cacheKey Önbellek anahtarı
 * @param computeFn Hesaplama işlevi
 * @param ttl Geçerlilik süresi (ms)
 * @returns Hesaplanmış veya önbellekten alınan değer
 */
export function memoizedComputation<T>(
  cacheKey: string,
  computeFn: () => T,
  ttl: number = 60000
): T {
  try {
    const cachedItem = localStorage.getItem(`memoized_${cacheKey}`);
    if (cachedItem) {
      const { value, timestamp } = JSON.parse(cachedItem);
      const isExpired = Date.now() - timestamp > ttl;
      
      if (!isExpired) {
        return value as T;
      }
    }
  } catch (error) {
    console.warn('Error reading from memoized computation cache:', error);
  }
  
  // Hesapla
  const result = computeFn();
  
  // Önbelleğe kaydet
  try {
    localStorage.setItem(
      `memoized_${cacheKey}`,
      JSON.stringify({
        value: result,
        timestamp: Date.now()
      })
    );
  } catch (error) {
    console.warn('Error writing to memoized computation cache:', error);
  }
  
  return result;
}