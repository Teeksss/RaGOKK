// Last reviewed: 2025-04-30 06:11:15 UTC (User: Teeksss)
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import Backend from 'i18next-http-backend';
import { format as formatDate, formatDistanceToNow, formatRelative } from 'date-fns';
import { tr, enUS } from 'date-fns/locale';

// i18next yapılandırması
i18n
  // HTTP backend yükleyicisi
  .use(Backend)
  // Tarayıcı dili tespiti
  .use(LanguageDetector)
  // React entegrasyonu
  .use(initReactI18next)
  // Yapılandırma
  .init({
    // Varsayılan dil
    fallbackLng: 'en',
    // Debug modu (geliştirme ortamında aktif)
    debug: process.env.NODE_ENV === 'development',
    
    // Çeviri dosyası namespace'i
    defaultNS: 'translation',
    
    // Desteklenen diller
    supportedLngs: ['en', 'tr'],
    
    // İçiçe çevirilerin bölücü karakteri
    keySeparator: '.',
    
    // Çeviri sağlayıcı yapılandırması
    backend: {
      // Çeviri dosyalarının yolu
      loadPath: '/locales/{{lng}}/{{ns}}.json',
    },
    
    // Çeviri dosyalarında eksik anahtarlar için (sadece geliştirme için)
    saveMissing: process.env.NODE_ENV === 'development',
    
    // Dil tespiti
    detection: {
      // Dil tespit sırası
      order: ['localStorage', 'cookie', 'navigator', 'htmlTag'],
      // Varsayılan olarak tarayıcı dilini kullanma
      lookupFromPathIndex: 0,
      // Cookie'de saklanan dil kodu
      lookupCookie: 'i18next',
      // LocalStorage'de saklanan dil kodu
      lookupLocalStorage: 'i18nextLng',
      // Cookie ayarları
      cookieOptions: { 
        expires: 365, // 1 yıl
        path: '/' 
      }
    },
    
    // React seçenekleri
    react: {
      // Suspense kullanımı
      useSuspense: true,
    },
    
    // Enterpolasyon seçenekleri
    interpolation: {
      // React XSS korumasını gereksiz kılar
      escapeValue: false,
      // Özel enterpolasyon formatları
      format: (value, format, lng) => {
        // Date-fns ile tarih formatları
        if (value instanceof Date) {
          const locale = lng === 'tr' ? tr : enUS;
          
          // Tarih formatları
          if (format === 'relative') {
            return formatRelative(value, new Date(), { locale });
          }
          
          if (format === 'ago') {
            return formatDistanceToNow(value, { addSuffix: true, locale });
          }
          
          // Custom veya varsayılan formatlar
          return formatDate(value, format || 'PPpp', { locale });
        }
        
        return value;
      }
    }
  });

export default i18n;