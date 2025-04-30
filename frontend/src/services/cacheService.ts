// Last reviewed: 2025-04-30 09:17:40 UTC (User: Teeksss)
import localforage from 'localforage';

// Cache configurasyonu
localforage.config({
  name: 'ragbase-cache',
  version: 1.0,
  storeName: 'rag_base_cache',
  description: 'Cache for RAG Base application'
});

// Cache süresi sabitler (milisaniye)
export const CACHE_DURATION = {
  SHORT: 5 * 60 * 1000,       // 5 dakika
  MEDIUM: 30 * 60 * 1000,     // 30 dakika
  LONG: 24 * 60 * 60 * 1000,  // 1 gün
  WEEK: 7 * 24 * 60 * 60 * 1000  // 1 hafta
};

// Cache öğesi tipi
export interface CacheItem<T> {
  data: T;
  timestamp: number;
  expiry: number;
}

// API Caching Service
export const CacheService = {
  /**
   * Veriyi önbelleğe al
   * @param key Cache anahtarı
   * @param data Cache'lenecek veri
   * @param duration Cache süresi (ms)
   */
  async set<T>(key: string, data: T, duration: number = CACHE_DURATION.MEDIUM): Promise<void> {
    const now = Date.now();
    const cacheItem: CacheItem<T> = {
      data,
      timestamp: now,
      expiry: now + duration
    };
    
    await localforage.setItem(key, cacheItem);
  },
  
  /**
   * Önbellekten veriyi getir
   * @param key Cache anahtarı
   * @returns Cache'lenmiş veri veya null (süre dolmuşsa)
   */
  async get<T>(key: string): Promise<T | null> {
    try {
      const cacheItem: CacheItem<T> | null = await localforage.getItem(key);
      
      if (!cacheItem) {
        return null;
      }
      
      // Süre dolduysa cache'i temizle
      if (Date.now() > cacheItem.expiry) {
        await localforage.removeItem(key);
        return null;
      }
      
      return cacheItem.data;
    } catch (error) {
      console.error('Cache get error:', error);
      return null;
    }
  },
  
  /**
   * Önbellekten veriyi sil
   * @param key Cache anahtarı
   */
  async remove(key: string): Promise<void> {
    await localforage.removeItem(key);
  },
  
  /**
   * Önbelleği temizle
   */
  async clear(): Promise<void> {
    await localforage.clear();
  },
  
  /**
   * Süresi geçmiş önbelleği temizle
   */
  async clearExpired(): Promise<void> {
    const now = Date.now();
    const keys = await localforage.keys();
    
    for (const key of keys) {
      const cacheItem: CacheItem<any> | null = await localforage.getItem(key);
      if (cacheItem && now > cacheItem.expiry) {
        await localforage.removeItem(key);
      }
    }
  }
};

// Offline Tarayıcı
export const OfflineService = {
  /**
   * Çevrimdışı mi kontrol et
   */
  isOffline(): boolean {
    return !navigator.onLine;
  },
  
  /**
   * Çevrimdışı olayları dinle
   * @param onOffline Çevrimdışı olduğunda çalışacak callback
   * @param onOnline Çevrimiçi olduğunda çalışacak callback
   */
  listenToConnectionChanges(onOffline: () => void, onOnline: () => void): void {
    window.addEventListener('offline', onOffline);
    window.addEventListener('online', onOnline);
  },
  
  /**
   * Çevrimdışı olaylarını dinlemeyi bırak
   * @param onOffline Çevrimdışı callback
   * @param onOnline Çevrimiçi callback
   */
  removeConnectionListeners(onOffline: () => void, onOnline: () => void): void {
    window.removeEventListener('offline', onOffline);
    window.removeEventListener('online', onOnline);
  },
  
  /**
   * Çevrimdışı iş kuyruğu
   * @param operation Çevrimiçi olduğunda gerçekleştirilecek işlem
   * @param key İşlem için benzersiz anahtar
   */
  async queueOperation(operation: { type: string, data: any }, key?: string): Promise<void> {
    const queueKey = 'offline_operation_queue';
    const queue = await localforage.getItem<Array<{ id: string, operation: any }>>(queueKey) || [];
    
    queue.push({
      id: key || Date.now().toString(),
      operation
    });
    
    await localforage.setItem(queueKey, queue);
  },
  
  /**
   * Bekleyen çevrimdışı işlemleri getir
   */
  async getPendingOperations(): Promise<Array<{ id: string, operation: any }>> {
    return await localforage.getItem<Array<{ id: string, operation: any }>>('offline_operation_queue') || [];
  },
  
  /**
   * Çevrimdışı işlemi tamamla
   * @param id İşlem ID'si
   */
  async completeOperation(id: string): Promise<void> {
    const queueKey = 'offline_operation_queue';
    const queue = await localforage.getItem<Array<{ id: string, operation: any }>>(queueKey) || [];
    
    const updatedQueue = queue.filter(item => item.id !== id);
    await localforage.setItem(queueKey, updatedQueue);
  }
};

// Cache ile API isteği yap
export const cachedApiRequest = async <T>(
  cacheKey: string,
  apiFn: () => Promise<T>,
  cacheDuration: number = CACHE_DURATION.MEDIUM,
  forceRefresh = false
): Promise<T> => {
  // Önbellek kontrolü
  if (!forceRefresh) {
    const cachedData = await CacheService.get<T>(cacheKey);
    if (cachedData) {
      return cachedData;
    }
  }
  
  // API'den veriyi getir
  try {
    const data = await apiFn();
    // Veriyi önbelleğe al
    await CacheService.set(cacheKey, data, cacheDuration);
    return data;
  } catch (error) {
    // Çevrimdışıysa ve önbellekte varsa, süre dolmuş olsa bile kullan
    if (OfflineService.isOffline()) {
      const cachedItem: CacheItem<T> | null = await localforage.getItem(cacheKey);
      if (cachedItem) {
        return cachedItem.data;
      }
    }
    
    throw error;
  }
};

// Uygulamada önbellek temizleme zamanlaması
export const setupCacheCleanup = (): void => {
  // Uygulama çalışırken her 12 saatte bir
  setInterval(() => {
    CacheService.clearExpired()
      .catch(err => console.error('Cache cleanup error:', err));
  }, 12 * 60 * 60 * 1000); // 12 saat
  
  // Sayfa yüklendiğinde
  CacheService.clearExpired().catch(err => console.error('Initial cache cleanup error:', err));
};