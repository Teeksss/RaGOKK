// Last reviewed: 2025-04-30 11:17:29 UTC (User: TeeksssYüksek)
// Analytics Service - Kullanıcı davranışlarını ve uygulama kullanımını izlemek için

// Google Analytics ve diğer analitik platformlar için tip tanımları
declare global {
  interface Window {
    gtag: (...args: any[]) => void;
    _paq: any[];
    dataLayer: any[];
  }
}

// Analitik etkinlik kategorileri
export enum EventCategory {
  USER = 'user',
  DOCUMENT = 'document',
  QUERY = 'query',
  INTERACTION = 'interaction',
  NAVIGATION = 'navigation',
  ERROR = 'error',
  PERFORMANCE = 'performance'
}

// Analitik etkinlik aksiyonları
export enum EventAction {
  // Kullanıcı aksiyonları
  LOGIN = 'login',
  LOGOUT = 'logout',
  REGISTER = 'register',
  UPDATE_PROFILE = 'update_profile',
  CHANGE_PASSWORD = 'change_password',
  ENABLE_2FA = 'enable_2fa',
  DISABLE_2FA = 'disable_2fa',
  
  // Belge aksiyonları
  UPLOAD = 'upload',
  DOWNLOAD = 'download',
  DELETE = 'delete',
  SHARE = 'share',
  VIEW = 'view',
  EDIT = 'edit',
  
  // Sorgu aksiyonları
  SEARCH = 'search',
  QUERY_TEXT = 'query_text',
  QUERY_MULTIMODAL = 'query_multimodal',
  REFINE_QUERY = 'refine_query',
  SAVE_QUERY = 'save_query',
  
  // Etkileşim aksiyonları
  CLICK = 'click',
  HOVER = 'hover',
  SCROLL = 'scroll',
  SUBMIT = 'submit',
  CANCEL = 'cancel',
  
  // Navigasyon aksiyonları
  PAGE_VIEW = 'page_view',
  ROUTE_CHANGE = 'route_change',
  
  // Hata aksiyonları
  ERROR = 'error',
  WARNING = 'warning',
  VALIDATION_ERROR = 'validation_error',
  
  // Performans aksiyonları
  PAGE_LOAD = 'page_load',
  COMPONENT_RENDER = 'component_render',
  NETWORK_REQUEST = 'network_request',
  RESOURCE_LOAD = 'resource_load'
}

// Analitik olay tipi
export interface AnalyticsEvent {
  category: EventCategory;
  action: EventAction | string;
  label?: string;
  value?: number;
  nonInteraction?: boolean;
  dimensions?: Record<string, string | number | boolean>;
}

// Kullanıcı özellikleri
export interface UserProperties {
  userId?: string;
  userType?: string;
  organization?: string;
  roles?: string[];
  language?: string;
  isNewUser?: boolean;
  createdAt?: string;
  lastLogin?: string;
  [key: string]: any;
}

// Analitik konfigürasyonu
export interface AnalyticsConfig {
  enabled: boolean;
  googleAnalyticsId?: string;
  matomoUrl?: string;
  matomoSiteId?: string;
  segmentWriteKey?: string;
  customEndpoint?: string;
  samplingRate?: number; // 0-1 arası
  debugMode?: boolean;
  excludePaths?: string[]; // İzlenmeyen URL path'leri
  includeUtm?: boolean; // UTM parametreleri izleme
  enableUserId?: boolean; // Kullanıcı ID'sini izleme
  anonymizeIp?: boolean; // IP anonimleştirme
}

// Analitik servisi
export class AnalyticsService {
  private static instance: AnalyticsService;
  private initialized: boolean = false;
  private anonymousId: string;
  private userProperties: UserProperties = {};
  
  private config: AnalyticsConfig = {
    enabled: process.env.NODE_ENV === 'production', // Production'da varsayılan olarak etkin
    samplingRate: 1.0, // Varsayılan olarak tüm kullanıcılar
    debugMode: process.env.NODE_ENV === 'development',
    includeUtm: true,
    enableUserId: true,
    anonymizeIp: true,
    excludePaths: ['/login', '/register', '/forgot-password', '/reset-password']
  };
  
  private constructor() {
    this.anonymousId = this.generateAnonymousId();
  }
  
  // Singleton örneğini getir
  public static getInstance(): AnalyticsService {
    if (!AnalyticsService.instance) {
      AnalyticsService.instance = new AnalyticsService();
    }
    return AnalyticsService.instance;
  }
  
  // Analitik servislerini yapılandır ve başlat
  public initialize(config: Partial<AnalyticsConfig>): void {
    if (this.initialized) {
      return;
    }
    
    this.config = {
      ...this.config,
      ...config
    };
    
    // Örnekleme oranına göre etkinleştir/devre dışı bırak
    if (Math.random() > (this.config.samplingRate || 1.0)) {
      this.config.enabled = false;
      return;
    }
    
    if (!this.config.enabled) {
      return;
    }
    
    // Google Analytics
    if (this.config.googleAnalyticsId) {
      this.initGoogleAnalytics();
    }
    
    // Matomo
    if (this.config.matomoUrl && this.config.matomoSiteId) {
      this.initMatomo();
    }
    
    // Segment
    if (this.config.segmentWriteKey) {
      this.initSegment();
    }
    
    // Sayfa görüntüleme izleme
    this.trackPageView();
    
    // Rota değişikliklerini izleme
    this.setupRouteChangeListener();
    
    this.initialized = true;
    
    // Debug modunda log
    if (this.config.debugMode) {
      console.debug('Analytics service initialized with config:', this.config);
    }
  }
  
  // Google Analytics kurulumu
  private initGoogleAnalytics(): void {
    const gtagScript = document.createElement('script');
    gtagScript.async = true;
    gtagScript.src = `https://www.googletagmanager.com/gtag/js?id=${this.config.googleAnalyticsId}`;
    document.head.appendChild(gtagScript);
    
    // gtag fonksiyonu
    window.dataLayer = window.dataLayer || [];
    window.gtag = function() {
      window.dataLayer.push(arguments);
    };
    
    window.gtag('js', new Date());
    window.gtag('config', this.config.googleAnalyticsId!, {
      send_page_view: false, // Sayfa görüntülemelerini manuel olarak izleyeceğiz
      anonymize_ip: this.config.anonymizeIp
    });
  }
  
  // Matomo kurulumu
  private initMatomo(): void {
    window._paq = window._paq || [];
    
    window._paq.push(['trackPageView']);
    window._paq.push(['enableLinkTracking']);
    
    if (this.config.anonymizeIp) {
      window._paq.push(['setDoNotTrack', true]);
    }
    
    const matomoScript = document.createElement('script');
    matomoScript.type = 'text/javascript';
    matomoScript.async = true;
    matomoScript.defer = true;
    matomoScript.src = `${this.config.matomoUrl}/matomo.js`;
    document.head.appendChild(matomoScript);
    
    const trackerScript = document.createElement('script');
    trackerScript.type = 'text/javascript';
    trackerScript.innerHTML = `
      var u="${this.config.matomoUrl}/";
      _paq.push(['setTrackerUrl', u+'matomo.php']);
      _paq.push(['setSiteId', '${this.config.matomoSiteId}']);
    `;
    document.head.appendChild(trackerScript);
  }
  
  // Segment kurulumu
  private initSegment(): void {
    // Segment snippet
    const segmentScript = document.createElement('script');
    segmentScript.type = 'text/javascript';
    segmentScript.innerHTML = `
      !function(){var analytics=window.analytics=window.analytics||[];if(!analytics.initialize)if(analytics.invoked)window.console&&console.error&&console.error("Segment snippet included twice.");else{analytics.invoked=!0;analytics.methods=["trackSubmit","trackClick","trackLink","trackForm","pageview","identify","reset","group","track","ready","alias","debug","page","once","off","on","addSourceMiddleware","addIntegrationMiddleware","setAnonymousId","addDestinationMiddleware"];analytics.factory=function(e){return function(){var t=Array.prototype.slice.call(arguments);t.unshift(e);analytics.push(t);return analytics}};for(var e=0;e<analytics.methods.length;e++){var key=analytics.methods[e];analytics[key]=analytics.factory(key)}analytics.load=function(key,e){var t=document.createElement("script");t.type="text/javascript";t.async=!0;t.src="https://cdn.segment.com/analytics.js/v1/" + key + "/analytics.min.js";var n=document.getElementsByTagName("script")[0];n.parentNode.insertBefore(t,n);analytics._loadOptions=e};analytics._writeKey="${this.config.segmentWriteKey}";analytics.SNIPPET_VERSION="4.13.2";
      analytics.load("${this.config.segmentWriteKey}");
      }}();
    `;
    document.head.appendChild(segmentScript);
    
    // Anonymous ID ayarla
    if (window.analytics) {
      window.analytics.setAnonymousId(this.anonymousId);
    }
  }
  
  // Sayfa görüntüleme izleme
  public trackPageView(path?: string, title?: string): void {
    if (!this.config.enabled || this.isExcludedPath(path || window.location.pathname)) {
      return;
    }
    
    const currentPath = path || window.location.pathname;
    const pageTitle = title || document.title;
    
    // Google Analytics
    if (window.gtag && this.config.googleAnalyticsId) {
      window.gtag('event', 'page_view', {
        page_path: currentPath,
        page_title: pageTitle,
        page_location: window.location.href
      });
    }
    
    // Matomo
    if (window._paq) {
      window._paq.push(['setCustomUrl', currentPath]);
      window._paq.push(['setDocumentTitle', pageTitle]);
      window._paq.push(['trackPageView']);
    }
    
    // Segment
    if (window.analytics) {
      window.analytics.page(pageTitle, {
        path: currentPath,
        url: window.location.href,
        title: pageTitle
      });
    }
    
    // Özel endpoint
    if (this.config.customEndpoint) {
      this.sendToCustomEndpoint('page_view', {
        path: currentPath,
        title: pageTitle,
        url: window.location.href,
        referrer: document.referrer
      });
    }
    
    // Debug modunda log
    if (this.config.debugMode) {
      console.debug(`Analytics: Tracked page view - ${pageTitle} (${currentPath})`);
    }
  }
  
  // Etkinlik izleme
  public trackEvent(event: AnalyticsEvent): void {
    if (!this.config.enabled || this.isExcludedPath(window.location.pathname)) {
      return;
    }
    
    const { category, action, label, value, nonInteraction, dimensions } = event;
    
    // Google Analytics
    if (window.gtag && this.config.googleAnalyticsId) {
      window.gtag('event', action, {
        event_category: category,
        event_label: label,
        value: value,
        non_interaction: nonInteraction || false,
        ...dimensions
      });
    }
    
    // Matomo
    if (window._paq) {
      window._paq.push(['trackEvent', category, action, label, value]);
      
      // Özel boyutlar
      if (dimensions) {
        Object.entries(dimensions).forEach(([key, val]) => {
          window._paq.push(['setCustomDimension', key, String(val)]);
        });
      }
    }
    
    // Segment
    if (window.analytics) {
      window.analytics.track(action, {
        category,
        label,
        value,
        nonInteraction,
        ...dimensions
      });
    }
    
    // Özel endpoint
    if (this.config.customEndpoint) {
      this.sendToCustomEndpoint('event', {
        category,
        action,
        label,
        value,
        nonInteraction,
        dimensions
      });
    }
    
    // Debug modunda log
    if (this.config.debugMode) {
      console.debug(`Analytics: Tracked event - ${category} / ${action}`, { label, value, dimensions });
    }
  }
  
  // Kullanıcı tanımlama
  public identifyUser(userId: string, properties: UserProperties = {}): void {
    if (!this.config.enabled || !this.config.enableUserId) {
      return;
    }
    
    this.userProperties = {
      ...this.userProperties,
      userId,
      ...properties
    };
    
    // Google Analytics
    if (window.gtag && this.config.googleAnalyticsId) {
      window.gtag('set', 'user_properties', {
        user_id: userId,
        ...properties
      });
      window.gtag('config', this.config.googleAnalyticsId, {
        user_id: userId
      });
    }
    
    // Matomo
    if (window._paq) {
      window._paq.push(['setUserId', userId]);
      
      // Özel değişkenler
      Object.entries(properties).forEach(([key, value]) => {
        window._paq.push(['setCustomVariable', 1, key, String(value), 'visit']);
      });
    }
    
    // Segment
    if (window.analytics) {
      window.analytics.identify(userId, properties);
    }
    
    // Özel endpoint
    if (this.config.customEndpoint) {
      this.sendToCustomEndpoint('identify', {
        userId,
        ...properties
      });
    }
    
    // Debug modunda log
    if (this.config.debugMode) {
      console.debug(`Analytics: Identified user - ${userId}`, properties);
    }
  }
  
  // Rota değişikliği izleme
  private setupRouteChangeListener(): void {
    // History API ile rota değişikliklerini yakala
    const originalPushState = history.pushState;
    const originalReplaceState = history.replaceState;
    
    history.pushState = function(...args) {
      const result = originalPushState.apply(this, args);
      window.dispatchEvent(new Event('locationchange'));
      return result;
    };
    
    history.replaceState = function(...args) {
      const result = originalReplaceState.apply(this, args);
      window.dispatchEvent(new Event('locationchange'));
      return result;
    };
    
    window.addEventListener('popstate', () => {
      window.dispatchEvent(new Event('locationchange'));
    });
    
    window.addEventListener('locationchange', () => {
      setTimeout(() => {
        this.trackPageView();
        this.trackEvent({
          category: EventCategory.NAVIGATION,
          action: EventAction.ROUTE_CHANGE,
          label: window.location.pathname
        });
      }, 300);
    });
  }
  
  // Özel breakpoint'e veri gönderme
  private sendToCustomEndpoint(type: string, data: any): void {
    if (!this.config.customEndpoint) {
      return;
    }
    
    const payload = {
      type,
      timestamp: new Date().toISOString(),
      sessionId: this.getSessionId(),
      anonymousId: this.anonymousId,
      ...this.getUserUtm(),
      ...this.userProperties,
      data
    };
    
    // Beacon API kullan (sayfa kapatılsa bile çalışır)
    try {
      navigator.sendBeacon(
        this.config.customEndpoint,
        JSON.stringify(payload)
      );
    } catch (error) {
      // Beacon başarısız olursa fetch ile dene
      fetch(this.config.customEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload),
        keepalive: true
      }).catch(() => {
        // Sessizce hata yönet - analitik hataları kullanıcı deneyimini etkilememeli
      });
    }
  }
  
  // Oturum kimliği oluştur/getir
  private getSessionId(): string {
    let sessionId = sessionStorage.getItem('analytics_session_id');
    
    if (!sessionId) {
      sessionId = Date.now().toString(36) + Math.random().toString(36).substr(2);
      sessionStorage.setItem('analytics_session_id', sessionId);
    }
    
    return sessionId;
  }
  
  // Anonim kullanıcı kimliği oluştur
  private generateAnonymousId(): string {
    let anonId = localStorage.getItem('analytics_anonymous_id');
    
    if (!anonId) {
      anonId = Date.now().toString(36) + Math.random().toString(36).substr(2);
      localStorage.setItem('analytics_anonymous_id', anonId);
    }
    
    return anonId;
  }
  
  // UTM parametrelerini al
  private getUserUtm(): Record<string, string> {
    if (!this.config.includeUtm) {
      return {};
    }
    
    const urlParams = new URLSearchParams(window.location.search);
    const utmParams: Record<string, string> = {};
    
    ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content'].forEach(param => {
      const value = urlParams.get(param);
      if (value) {
        utmParams[param] = value;
      }
    });
    
    return utmParams;
  }
  
  // Bir URL yolunun izleme dışında bırakılıp bırakılmadığını kontrol et
  private isExcludedPath(path: string): boolean {
    if (!this.config.excludePaths || this.config.excludePaths.length === 0) {
      return false;
    }
    
    return this.config.excludePaths.some(excludedPath => {
      if (excludedPath.endsWith('*')) {
        return path.startsWith(excludedPath.slice(0, -1));
      }
      return path === excludedPath;
    });
  }
}

// Analitik servis örneği
export const analyticsService = AnalyticsService.getInstance();

// React hook
import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

export const useAnalytics = () => {
  const location = useLocation();
  
  // Sayfa görüntüleme izleme
  useEffect(() => {
    analyticsService.trackPageView(location.pathname);
  }, [location.pathname]);
  
  return {
    // Etkinlik izleme
    trackEvent: (event: AnalyticsEvent) => {
      analyticsService.trackEvent(event);
    },
    // Kullanıcı tanımlama
    identifyUser: (userId: string, properties?: UserProperties) => {
      analyticsService.identifyUser(userId, properties);
    }
  };
};