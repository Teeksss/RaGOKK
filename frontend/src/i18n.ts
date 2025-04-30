// Last reviewed: 2025-04-30 08:34:14 UTC (User: Teeksss)
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// Dil dosyaları
import translationEN from './locales/en/translation.json';
import translationTR from './locales/tr/translation.json';

// Kaynaklar
const resources = {
  en: {
    translation: translationEN
  },
  tr: {
    translation: translationTR
  }
};

i18n
  // Tarayıcı dil algılama
  .use(LanguageDetector)
  // React eklentisi
  .use(initReactI18next)
  // Ayarları başlat
  .init({
    resources,
    fallbackLng: 'en',
    debug: process.env.NODE_ENV === 'development',
    interpolation: {
      escapeValue: false, // React zaten XSS koruması sağlar
    },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage']
    }
  });

export default i18n;