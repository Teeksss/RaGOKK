import axios, { AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';
import { CacheService, OfflineService } from '../services/cacheService';
import { addCsrfToken, sanitizeParams } from '../utils/security';

// Temel API yapılandırması
const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// İstek öncesi interceptor
api.interceptors.request.use(
  (config: AxiosRequestConfig) => {
    // Parametre sanitizasyonu
    if (config.params) {
      config.params = sanitizeParams(config.params);
    }
    
    // Body sanitizasyonu (POST, PUT, PATCH istekleri için)
    if (config.data && typeof config.data === 'object') {
      config.data = sanitizeParams(config.data);
    }
    
    // JWT token ekle (mevcutsa)
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers = {
        ...config.headers,
        Authorization: `Bearer ${token}`
      };
    }
    
    // CSRF koruması
    config.headers = addCsrfToken(config.headers || {});
    
    // İstek tarihçesi koruması için istekler arasına rastgele bir değer ekle
    config.headers['X-Request-ID'] = Date.now().toString(36) + Math.random().toString(36).substr(2);
    
    // Çevrimdışı kontrolü
    if (OfflineService.isOffline() && !config.headers?.['Allow-Offline']) {
      return Promise.reject({ isOffline: true, config });
    }
    
    return config;
  },
  (error) => Promise.reject(error)
);

// Yanıt güvenliği için iyileştirmeler (enhancedApi içinden)
export const safeJsonParse = (jsonString: string): any => {
  try {
    // JSON.parse yerine daha güvenli bir alternatif
    return JSON.parse(jsonString, (key, value) => {
      // Prototip zehirlenmesine karşı kontrol
      if (key === '__proto__' || key === 'constructor' || key === 'prototype') {
        return undefined;
      }
      return value;
    });
  } catch (error) {
    console.error('Error parsing JSON:', error);
    throw new Error('Invalid JSON response');
  }
};

// Güvenli GET isteği - Content-Security-Policy header'ı ekleme
export const getWithCSP = async <T>(url: string, config?: AxiosRequestConfig): Promise<T> => {
  const response = await api.get<T>(url, {
    ...config,
    headers: {
      ...config?.headers,
      'Content-Security-Policy': "default-src 'self'"
    }
  });
  return response.data;
};