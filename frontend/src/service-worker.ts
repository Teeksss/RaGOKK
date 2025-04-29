/// <reference lib="webworker" />
/* eslint-disable no-restricted-globals */

// Service worker tipi için TypeScript tanımları
export type {};
declare const self: ServiceWorkerGlobalScope;

// Cache adı ve sürümü - versiyon numarası değiştiğinde tüm önbellek yenilenir
const CACHE_NAME = 'ragbase-cache-v1';

// Önceden önbelleğe alınacak statik varlıklar
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/static/css/main.chunk.css',
  '/static/js/main.chunk.js',
  '/static/js/bundle.js',
  '/logo192.png',
  '/logo512.png',
  '/favicon.ico',
  '/static/media/logo.svg',
  '/locales/en/common.json',
  '/locales/tr/common.json'
];

// API istekleri için regex
const API_REGEX = /\/api\//;

// Service worker yüklendiğinde çalışır
self.addEventListener('install', (event) => {
  console.log('Service worker installing...');
  
  // Önbelleğe önceden statik varlıkları ekle
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .catch(err => console.error('Cache add error:', err))
  );
  
  // Hemen activate olmasını sağla
  self.skipWaiting();
});

// Service worker active olduğunda çalışır
self.addEventListener('activate', (event) => {
  console.log('Service worker activating...');
  
  // Eski cache'leri temizle
  event.waitUntil(
    caches.keys()
      .then(keys => {
        return Promise.all(
          keys.filter(key => key !== CACHE_NAME)
            .map(key => {
              console.log(`Deleting old cache: ${key}`);
              return caches.delete(key);
            })
        );
      })
      .then(() => {
        console.log('Service worker now active, controlling pages');
        // İstemcilerin kontrolünü ele al
        return self.clients.claim();
      })
  );
});

// Fetch olayı - ağ isteklerini yakalama
self.addEventListener('fetch', (event) => {
  // API istekleri için farklı bir strateji kullan
  if (API_REGEX.test(event.request.url)) {
    // Network First, sonra cache
    event.respondWith(networkFirstStrategy(event.request));
  } else {
    // Statik içerik için Cache First, sonra network
    event.respondWith(cacheFirstStrategy(event.request));
  }
});

// Network First stratejisi - önce ağdan dene, başarısız olursa cache'e bak
async function networkFirstStrategy(request: Request): Promise<Response> {
  try {
    // Önce ağdan getirmeyi dene
    const networkResponse = await fetch(request);
    
    // Başarılıysa cache'e kaydet ve yanıtı döndür
    if (networkResponse && networkResponse.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, networkResponse.clone());
      return networkResponse;
    }
    
    throw new Error('Network response not ok');
  } catch (error) {
    console.log('Network request failed, falling back to cache:', error);
    
    // Ağ hatası, cache'den dene
    const cachedResponse = await caches.match(request);
    
    // Cache'de varsa döndür, yoksa hata yanıtı döndür
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // Offline sayfa veya hata yanıtı
    return new Response(JSON.stringify({ error: 'Network request failed and no cache available' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

// Cache First stratejisi - önce cache'e bak, yoksa ağdan getir
async function cacheFirstStrategy(request: Request): Promise<Response> {
  // Cache'de var mı kontrol et
  const cachedResponse = await caches.match(request);
  
  if (cachedResponse) {
    return cachedResponse;
  }
  
  // Cache'de yoksa ağdan getir
  try {
    const networkResponse = await fetch(request);
    
    // Başarılıysa cache'e kaydet ve yanıtı döndür
    if (networkResponse && networkResponse.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, networkResponse.clone());
      return networkResponse;
    }
    
    throw new Error('Network response not ok');
  } catch (error) {
    console.error('Network request failed and no cache available:', error);
    
    // Statik dosyalar için düzgün 404 yanıtı
    if (request.url.match(/\.(js|css|png|jpg|jpeg|svg|ico)$/)) {
      return new Response('Resource not found', {
        status: 404,
        statusText: 'Not Found'
      });
    }
    
    // Sayfa isteklerinde index.html'e yönlendir (SPA için)
    if (request.mode === 'navigate') {
      const indexPage = await caches.match('/index.html');
      if (indexPage) {
        return indexPage;
      }
    }
    
    return new Response('Network error and no cache available', {
      status: 503,
      statusText: 'Service Unavailable'
    });
  }
}

// Push mesajları alma
self.addEventListener('push', (event) => {
  if (!(self.Notification && self.Notification.permission === 'granted')) {
    return;
  }
  
  try {
    const data = event.data?.json() || {};
    const title = data.title || 'RAG Base Notification';
    const options = {
      body: data.body || '',
      icon: data.icon || '/logo192.png',
      badge: data.badge || '/logo192.png',
      data: {
        url: data.url || '/'
      }
    };
    
    event.waitUntil(
      self.registration.showNotification(title, options)
    );
  } catch (err) {
    console.error('Push notification error:', err);
  }
});

// Notification tıklama olayı
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  
  const url = event.notification.data?.url || '/';
  
  event.waitUntil(
    self.clients.matchAll({ type: 'window' })
      .then((clientList) => {
        // Açık bir pencere var mı kontrol et
        for (const client of clientList) {
          if (client.url === url && 'focus' in client) {
            return client.focus();
          }
        }
        
        // Açık pencere yoksa yeni aç
        return self.clients.openWindow(url);
      })
  );
});

// Periyodik eşitleme
self.addEventListener('periodicsync', (event) => {
  if (event.tag === 'sync-documents') {
    event.waitUntil(syncDocuments());
  }
});

async function syncDocuments() {
  try {
    // Offline değişiklikleri senkronize et
    const offlineChanges = await getOfflineChanges();
    
    if (offlineChanges.length > 0) {
      await syncOfflineChanges(offlineChanges);
    }
    
    // Yeni dökümanları indir
    await fetchLatestDocuments();
    
    console.log('Background sync completed successfully');
  } catch (error) {
    console.error('Background sync failed:', error);
  }
}

async function getOfflineChanges(): Promise<any[]> {
  // IndexedDB'den offline değişiklikleri al
  // Bu örnek için boş bir implementasyon
  return [];
}

async function syncOfflineChanges(changes: any[]) {
  // Offline değişiklikleri sunucuya gönder
  // Bu örnek için boş bir implementasyon
}

async function fetchLatestDocuments() {
  // Son dökümanları al
  // Bu örnek için boş bir implementasyon
}