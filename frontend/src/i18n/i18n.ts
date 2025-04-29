// Last reviewed: 2025-04-29 13:14:42 UTC (User: TeeksssAPI)
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import Backend from 'i18next-http-backend';
import { format as formatDate, formatRelative, formatDistance } from 'date-fns';
import { enUS, tr, de, es, fr, ja, zhCN } from 'date-fns/locale';

// Desteklenen diller için date-fns yerelleri
const dateFnsLocales: { [key: string]: Locale } = {
  en: enUS,
  tr: tr,
  de: de,
  es: es,
  fr: fr,
  ja: ja,
  'zh-CN': zhCN
};

// i18next için tarih formatlamasını kolaylaştıran yardımcı fonksiyonlar
i18n
  .use(Backend)  // Dil dosyalarını sunucudan yüklemek için
  .use(LanguageDetector)  // Tarayıcıdaki dil tercihini otomatik algılamak için
  .use(initReactI18next)  // react-i18next ile entegrasyon için
  .init({
    // Varsayılan ayarlar
    fallbackLng: 'en',
    supportedLngs: ['en', 'tr', 'de', 'es', 'fr', 'ja', 'zh-CN'],
    
    // Tercümeleri yüklemek için backend ayarları
    backend: {
      loadPath: '/locales/{{lng}}/{{ns}}.json'
    },
    
    // Varsayılan namespace'ler
    ns: ['common', 'documents', 'auth', 'search', 'settings', 'errors'],
    defaultNS: 'common',
    
    // Geliştirme ayarları
    debug: process.env.NODE_ENV === 'development',
    
    // React özel ayarları
    react: {
      useSuspense: true,
      bindI18n: 'languageChanged loaded',
    },
    
    // Ara format fonksiyonları tanımlama
    interpolation: {
      escapeValue: false,  // React zaten XSS koruması sağlıyor
      
      // Tarih formatlama için özel formatlar
      format: (value, format, lng) => {
        if (value instanceof Date) {
          const locale = dateFnsLocales[lng || 'en'] || dateFnsLocales.en;
          
          // Kullanılabilecek tarih formatları
          if (format === 'short') {
            return formatDate(value, 'P', { locale });
          }
          
          if (format === 'long') {
            return formatDate(value, 'PPpp', { locale });
          }
          
          if (format === 'relative') {
            return formatRelative(value, new Date(), { locale });
          }
          
          if (format === 'ago') {
            return formatDistance(value, new Date(), { 
              locale, 
              addSuffix: true 
            });
          }
          
          // Özel format kullanma (date-fns formatı)
          return formatDate(value, format, { locale });
        }
        
        return value;
      }
    }
  });

export default i18n;

// Tipleri kolaylaştıran yardımcı fonksiyonlar
export const locales = {
  en: { name: 'English', nativeName: 'English', flag: '🇺🇸' },
  tr: { name: 'Turkish', nativeName: 'Türkçe', flag: '🇹🇷' },
  de: { name: 'German', nativeName: 'Deutsch', flag: '🇩🇪' },
  es: { name: 'Spanish', nativeName: 'Español', flag: '🇪🇸' },
  fr: { name: 'French', nativeName: 'Français', flag: '🇫🇷' },
  ja: { name: 'Japanese', nativeName: '日本語', flag: '🇯🇵' },
  'zh-CN': { name: 'Chinese (Simplified)', nativeName: '中文 (简体)', flag: '🇨🇳' }
};

// Adlarına göre sıralanmış dilleri döndür
export const getSortedLocales = () => {
  return Object.entries(locales)
    .map(([code, info]) => ({ code, ...info }))
    .sort((a, b) => a.name.localeCompare(b.name));
};

// Geçerli dili değiştir
export const changeLanguage = async (language: string) => {
  await i18n.changeLanguage(language);
  // Tarih yerelleştirmesi için HTML lang attibute'unu güncelle 
  document.documentElement.setAttribute('lang', language);
  // Kullanıcı tercihini kaydet
  localStorage.setItem('i18nextLng', language);
};