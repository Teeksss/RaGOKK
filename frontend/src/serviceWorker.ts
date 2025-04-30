// Last reviewed: 2025-04-30 11:32:10 UTC (User: TeeksssOrta)
// This service worker is used to enable offline functionality and PWA capabilities

// Tip tanımları
type Config = {
  onSuccess?: (registration: ServiceWorkerRegistration) => void;
  onUpdate?: (registration: ServiceWorkerRegistration) => void;
  onOffline?: () => void;
  onOnline?: () => void;
};

// Service worker kaydı için öncelikle ortamı kontrol et
export function register(config?: Config) {
  if (process.env.NODE_ENV === 'production' && 'serviceWorker' in navigator) {
    // URL constructor URL'leri işlemek için kullanılır
    const publicUrl = new URL(process.env.PUBLIC_URL || '', window.location.href);
    
    // Service Worker başka bir originden geliyorsa çalışmayacaktır
    // Bu durumda CDN kullanıyorsak dikkatli olmalıyız
    if (publicUrl.origin !== window.location.origin) {
      return;
    }

    window.addEventListener('load', () => {
      const swUrl = `${process.env.PUBLIC_URL}/service-worker.js`;

      if (isLocalhost) {
        // Localhost'ta çalışıyorken, service worker'ın varlığını kontrol et
        checkValidServiceWorker(swUrl, config);

        // Localhost'ta ek log çıktısı ver
        navigator.serviceWorker.ready.then(() => {
          console.log(
            'This web app is being served cache-first by a service ' +
              'worker. To learn more, visit https://cra.link/PWA'
          );
        });
      } else {
        // Yerel bir host değilse, service worker'ı kaydet
        registerValidSW(swUrl, config);
      }
    });

    // Ağ bağlantı durumunu izle
    handleConnectionChanges(config);
  }
}

// Bağlantı değişikliklerini izleme
function handleConnectionChanges(config?: Config) {
  window.addEventListener('online', () => {
    console.log('App is online');
    if (config?.onOnline) {
      config.onOnline();
    }
  });

  window.addEventListener('offline', () => {
    console.log('App is offline');
    if (config?.onOffline) {
      config.onOffline();
    }
  });
}

// Bu aşağıdaki 'isLocalhost' tanımlaması, bir üretim ortamında değil, 
// bir geliştirme ortamında çalışıp çalışmadığımızı belirlemek içindir.
const isLocalhost = Boolean(
  window.location.hostname === 'localhost' ||
    // [::1] IPv6 için localhost adresidir
    window.location.hostname === '[::1]' ||
    // 127.0.0.0/8 bir IPv4 içindir (bu durumda localhost)
    window.location.hostname.match(/^127(?:\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}$/)
);

// Service worker'ı kaydet
function registerValidSW(swUrl: string, config?: Config) {
  navigator.serviceWorker
    .register(swUrl)
    .then((registration) => {
      // Service worker güncelleme buldukça izle
      registration.onupdatefound = () => {
        const installingWorker = registration.installing;
        if (installingWorker == null) {
          return;
        }
        installingWorker.onstatechange = () => {
          if (installingWorker.state === 'installed') {
            if (navigator.serviceWorker.controller) {
              // Bu noktada, eski içerik önbelleğe alınacak
              // ve yeni içerik indirilecektir
              console.log(
                'New content is available and will be used when all ' +
                  'tabs for this page are closed. See https://cra.link/PWA.'
              );

              // Callback'i çalıştır
              if (config && config.onUpdate) {
                config.onUpdate(registration);
              }
            } else {
              // Bu nokta her şey önbelleğe alındığında
              // içerik offline kullanım için hazır olduğunda
              console.log('Content is cached for offline use.');

              // Callback'i çalıştır
              if (config && config.onSuccess) {
                config.onSuccess(registration);
              }
            }
          }
        };
      };
    })
    .catch((error) => {
      console.error('Error during service worker registration:', error);
    });
}

// Service worker'ın geçerli olup olmadığını kontrol et
function checkValidServiceWorker(swUrl: string, config?: Config) {
  // Service worker varsa kontrol et
  fetch(swUrl, {
    headers: { 'Service-Worker': 'script' },
  })
    .then((response) => {
      // JS dosyası alındığından emin ol
      const contentType = response.headers.get('content-type');
      if (
        response.status === 404 ||
        (contentType != null && contentType.indexOf('javascript') === -1)
      ) {
        // Geçersiz service worker - muhtemelen farklı bir uygulama
        // Yenile ve tekrar dene
        navigator.serviceWorker.ready.then((registration) => {
          registration.unregister().then(() => {
            window.location.reload();
          });
        });
      } else {
        // Geçerli service worker - kaydet
        registerValidSW(swUrl, config);
      }
    })
    .catch(() => {
      console.log('No internet connection found. App is running in offline mode.');
    });
}

// Service worker kaydını kaldır
export function unregister() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.ready
      .then((registration) => {
        registration.unregister();
      })
      .catch((error) => {
        console.error(error.message);
      });
  }
}

// Service Worker'ı kontrol et (yeni bir sürüm var mı diye)
export function checkForUpdates(callback: (hasUpdate: boolean) => void) {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.ready
      .then((registration) => {
        registration.update().then(() => {
          if (registration.waiting) {
            callback(true); // Güncelleme var
          } else {
            callback(false); // Güncelleme yok
          }
        });
      })
      .catch((error) => {
        console.error('Error checking for service worker updates:', error);
        callback(false);
      });
  } else {
    callback(false);
  }
}

// Yeni Service Worker'ı etkinleştir
export function activateUpdate() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.ready.then((registration) => {
      if (registration.waiting) {
        // skipWaiting mesajını gönder
        registration.waiting.postMessage({ type: 'SKIP_WAITING' });
        
        // Sayfa yenileme için
        window.location.reload();
      }
    });
  }
}