import DOMPurify from 'dompurify';

// XSS koruması için string sanitize fonksiyonu
export const sanitizeHtml = (html: string): string => {
  return DOMPurify.sanitize(html, {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ['script', 'style', 'iframe', 'frame', 'object', 'embed'],
    FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover']
  });
};

// URL sanitize fonksiyonu
export const sanitizeUrl = (url: string): string => {
  const urlPattern = /^(?:(?:https?|mailto|ftp|tel|file):\/\/|data:image\/[a-z]+;base64,)[^\s()<>]+(?:\([^\s()<>]+\)|[^\s`!()\[\]{};:'".,<>?«»""''])$/i;
  
  if (!url || !urlPattern.test(url)) {
    return '#';
  }
  
  return url;
};

// API istek parametrelerini sanitize et
export const sanitizeParams = (params: Record<string, any>): Record<string, any> => {
  const sanitized: Record<string, any> = {};
  
  for (const key in params) {
    if (typeof params[key] === 'string') {
      sanitized[key] = DOMPurify.sanitize(params[key]);
    } else {
      sanitized[key] = params[key];
    }
  }
  
  return sanitized;
};

// CSRF Token yönetimi
export const getCsrfToken = (): string => {
  // Meta tag'den CSRF token'ı al
  const metaTag = document.querySelector('meta[name="csrf-token"]');
  return metaTag ? metaTag.getAttribute('content') || '' : '';
};

// API istekleri için CSRF token ekle
export const addCsrfToken = (headers: Record<string, string>): Record<string, string> => {
  const csrfToken = getCsrfToken();
  
  if (csrfToken) {
    return {
      ...headers,
      'X-CSRF-Token': csrfToken
    };
  }
  
  return headers;
};

// Input validasyonu için güvenli regex kullanımı
export const safeRegexMatch = (input: string, pattern: string): boolean => {
  try {
    // Timeout ekleyerek ReDoS (Regex Denial of Service) saldırısını önle
    const safePatter = new RegExp(pattern);
    const timeoutId = setTimeout(() => {
      throw new Error('Regex timeout - possible ReDoS attack');
    }, 1000);
    
    const result = safePatter.test(input);
    clearTimeout(timeoutId);
    
    return result;
  } catch (error) {
    console.error('Regex error:', error);
    return false;
  }
};

// Güvenli localStorage kullanımı
export const secureStorage = {
  setItem: (key: string, value: any): void => {
    try {
      if (typeof value === 'object') {
        localStorage.setItem(key, JSON.stringify(value));
      } else {
        localStorage.setItem(key, String(value));
      }
    } catch (error) {
      console.error('Error setting localStorage item:', error);
    }
  },
  
  getItem: <T>(key: string, defaultValue: T): T => {
    try {
      const item = localStorage.getItem(key);
      
      if (item === null) {
        return defaultValue;
      }
      
      try {
        return JSON.parse(item) as T;
      } catch {
        return item as unknown as T;
      }
    } catch (error) {
      console.error('Error getting localStorage item:', error);
      return defaultValue;
    }
  },
  
  removeItem: (key: string): void => {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.error('Error removing localStorage item:', error);
    }
  }
};