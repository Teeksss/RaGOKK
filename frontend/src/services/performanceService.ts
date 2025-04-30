// Last reviewed: 2025-04-30 11:17:29 UTC (User: TeeksssYüksek)
import { getCLS, getFID, getLCP, getFCP, getTTFB } from 'web-vitals';

// Performans metrik tipi
export type MetricName = 'CLS' | 'FID' | 'LCP' | 'FCP' | 'TTFB' | 'JSHeapSize' | 'DOMNodes' | 'LayoutDuration' | 'Custom';

// Performans metrik değeri
export interface PerformanceMetric {
  name: MetricName;
  value: number;
  delta?: number;
  id?: string;
  timestamp: number;
  navigationType?: string;
}

// Performans izleme konfigürasyonu
export interface PerformanceConfig {
  reportInterval?: number;         // Ölçüm raporlama aralığı (ms)
  apiEndpoint?: string;            // Metriklerin gönderileceği API endpoint'i
  sampleRate?: number;             // Örnekleme oranı (0-1 arası)
  trackMemory?: boolean;           // Bellek kullanımını izle
  trackLayoutShifts?: boolean;     // Layout değişikliklerini izle
  trackLongTasks?: boolean;        // Uzun görevleri izle
  trackResourceTiming?: boolean;   // Kaynak zamanlama bilgilerini izle
  minInteractionDelay?: number;    // Minimum etkileşim gecikmesi (ms)
}

// Performans izleme servisi
export class PerformanceService {
  private static instance: PerformanceService;
  private metrics: PerformanceMetric[] = [];
  private resourceTimings: PerformanceResourceTiming[] = [];
  private longTasks: PerformanceMeasure[] = [];
  private interactionDelays: number[] = [];
  private reportingInterval: NodeJS.Timeout | null = null;
  
  private config: PerformanceConfig = {
    reportInterval: 60000, // 1 dakika
    apiEndpoint: '/api/v1/metrics',
    sampleRate: 1.0,       // %100
    trackMemory: true,
    trackLayoutShifts: true,
    trackLongTasks: true,
    trackResourceTiming: true,
    minInteractionDelay: 100 // 100ms
  };
  
  private constructor() {}
  
  public static getInstance(): PerformanceService {
    if (!PerformanceService.instance) {
      PerformanceService.instance = new PerformanceService();
    }
    return PerformanceService.instance;
  }
  
  // Performans izlemeyi başlat
  public initialize(config?: Partial<PerformanceConfig>): void {
    // Konfigürasyonu güncelle
    this.config = {
      ...this.config,
      ...config
    };
    
    // Kullanıcı örnekleme oranına göre izleme yapıp yapmama kararı
    if (Math.random() > this.config.sampleRate!) {
      console.debug('Performance monitoring skipped based on sample rate');
      return;
    }
    
    // Core Web Vitals'ı izle
    this.initCoreWebVitals();
    
    // Eğer yapılandırıldıysa diğer metrikleri izle
    if (this.config.trackMemory) {
      this.initMemoryMonitoring();
    }
    
    if (this.config.trackLayoutShifts) {
      this.initLayoutShiftMonitoring();
    }
    
    if (this.config.trackLongTasks) {
      this.initLongTaskMonitoring();
    }
    
    if (this.config.trackResourceTiming) {
      this.initResourceTimingMonitoring();
    }
    
    // İnteraksiyon gecikmesini izle
    this.initInteractionMonitoring();
    
    // Raporlama aralığını başlat
    this.startReporting();
    
    // Sayfa kapanırken metrikleri gönder
    window.addEventListener('unload', () => {
      this.sendMetrics(true);
    });
  }
  
  // Özel performans metriği ekle
  public addCustomMetric(name: string, value: number): void {
    this.metrics.push({
      name: 'Custom',
      value,
      timestamp: Date.now(),
      id: name
    });
  }
  
  // Zamanlayıcı başlat
  public startTimer(label: string): () => void {
    const startTime = performance.now();
    
    // Zamanlayıcıyı durdur ve süreyi kaydet
    return () => {
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      this.addCustomMetric(label, duration);
    };
  }
  
  // Tüm metrikleri al
  public getMetrics(): PerformanceMetric[] {
    return [...this.metrics];
  }
  
  // Performans raporunu al
  public getPerformanceReport(): any {
    return {
      metrics: this.metrics,
      resourceTimings: this.resourceTimings.slice(0, 50), // Sınırlı sayıda kaynak zamanlaması
      longTasks: this.longTasks,
      interactionDelays: this.interactionDelays,
      userAgent: navigator.userAgent,
      connectionType: this.getConnectionInfo(),
      deviceMemory: (navigator as any).deviceMemory || 'unknown',
      timestamp: Date.now(),
      url: window.location.href,
      screenSize: `${window.innerWidth}x${window.innerHeight}`
    };
  }
  
  // Core Web Vitals izleme
  private initCoreWebVitals(): void {
    // Cumulative Layout Shift (CLS)
    getCLS(metric => {
      this.metrics.push({
        name: 'CLS',
        value: metric.value,
        delta: metric.delta,
        id: metric.id,
        timestamp: Date.now(),
        navigationType: metric.navigationType
      });
    });
    
    // First Input Delay (FID)
    getFID(metric => {
      this.metrics.push({
        name: 'FID',
        value: metric.value,
        delta: metric.delta,
        id: metric.id,
        timestamp: Date.now(),
        navigationType: metric.navigationType
      });
    });
    
    // Largest Contentful Paint (LCP)
    getLCP(metric => {
      this.metrics.push({
        name: 'LCP',
        value: metric.value,
        delta: metric.delta,
        id: metric.id,
        timestamp: Date.now(),
        navigationType: metric.navigationType
      });
    });
    
    // First Contentful Paint (FCP)
    getFCP(metric => {
      this.metrics.push({
        name: 'FCP',
        value: metric.value,
        delta: metric.delta,
        id: metric.id,
        timestamp: Date.now(),
        navigationType: metric.navigationType
      });
    });
    
    // Time to First Byte (TTFB)
    getTTFB(metric => {
      this.metrics.push({
        name: 'TTFB',
        value: metric.value,
        delta: metric.delta,
        id: metric.id,
        timestamp: Date.now(),
        navigationType: metric.navigationType
      });
    });
  }
  
  // Bellek kullanım izleme
  private initMemoryMonitoring(): void {
    // Her 30 saniyede bir bellek durumunu kontrol et
    setInterval(() => {
      if (performance && (performance as any).memory) {
        const memory = (performance as any).memory;
        this.metrics.push({
          name: 'JSHeapSize',
          value: memory.usedJSHeapSize / (1024 * 1024), // MB cinsinden
          timestamp: Date.now()
        });
      }
    }, 30000);
  }
  
  // Layout değişikliklerini izleme
  private initLayoutShiftMonitoring(): void {
    // Layout Stability API
    let layoutShiftScore = 0;
    
    const observer = new PerformanceObserver(list => {
      for (const entry of list.getEntries()) {
        // Kullanıcı etkileşimine bağlı olmayan layout değişikliklerini izle
        if (!(entry as any).hadRecentInput) {
          layoutShiftScore += (entry as any).value;
        }
      }
    });
    
    observer.observe({ type: 'layout-shift', buffered: true });
    
    // Her 10 saniyede bir layout değişiklik skorunu kaydet
    setInterval(() => {
      if (layoutShiftScore > 0) {
        this.addCustomMetric('LayoutShiftScore', layoutShiftScore);
        layoutShiftScore = 0; // Skoru sıfırla
      }
    }, 10000);
  }
  
  // Uzun görevleri izleme
  private initLongTaskMonitoring(): void {
    const observer = new PerformanceObserver(list => {
      for (const entry of list.getEntries()) {
        // 50ms'den uzun süren görevleri kaydet
        if (entry.duration > 50) {
          this.longTasks.push(entry as PerformanceMeasure);
          
          // Custom metrik olarak da ekle
          this.addCustomMetric('LongTask', entry.duration);
        }
      }
    });
    
    observer.observe({ type: 'longtask', buffered: true });
  }
  
  // Kaynak zamanlama bilgilerini izleme
  private initResourceTimingMonitoring(): void {
    const observer = new PerformanceObserver(list => {
      const entries = list.getEntries();
      // Yalnızca en yavaş yüklenen kaynakları kaydet
      entries
        .filter(entry => entry.duration > 500) // 500ms'den uzun süren kaynaklar
        .forEach(entry => {
          this.resourceTimings.push(entry as PerformanceResourceTiming);
        });
    });
    
    observer.observe({ type: 'resource', buffered: true });
  }
  
  // İnteraksiyon gecikmesini izleme
  private initInteractionMonitoring(): void {
    // Kullanıcı etkileşimini izle
    const eventTypes = ['click', 'mousedown', 'keydown', 'touchstart', 'pointerdown'];
    const minDelay = this.config.minInteractionDelay || 100;
    
    eventTypes.forEach(type => {
      window.addEventListener(type, () => {
        const before = performance.now();
        
        window.requestAnimationFrame(() => {
          const after = performance.now();
          const delay = after - before;
          
          // Minimum gecikmeden uzunsa kaydet
          if (delay > minDelay) {
            this.interactionDelays.push(delay);
            this.addCustomMetric(`InteractionDelay-${type}`, delay);
          }
        });
      });
    });
  }
  
  // Metrikleri göndermeye başla
  private startReporting(): void {
    if (this.reportingInterval) {
      clearInterval(this.reportingInterval);
    }
    
    this.reportingInterval = setInterval(() => {
      this.sendMetrics();
    }, this.config.reportInterval);
  }
  
  // Metrikleri gönder
  private sendMetrics(isFinal: boolean = false): void {
    // Göndermek için metrik yoksa çık
    if (this.metrics.length === 0 && this.resourceTimings.length === 0 && this.longTasks.length === 0) {
      return;
    }
    
    // Performans raporunu hazırla
    const report = this.getPerformanceReport();
    report.isFinal = isFinal;
    
    // API'ye gönder
    if (this.config.apiEndpoint) {
      try {
        // Beacon API kullanarak gönder (sayfa kapatılsa bile isteklerin tamamlanmasını sağlar)
        const sent = navigator.sendBeacon(
          this.config.apiEndpoint,
          JSON.stringify(report)
        );
        
        if (!sent) {
          // Beacon başarısız olursa fetch ile dene
          fetch(this.config.apiEndpoint, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(report),
            keepalive: true
          }).catch(err => {
            console.error('Failed to send performance metrics:', err);
          });
        }
      } catch (err) {
        console.error('Failed to send performance metrics:', err);
      }
    }
    
    // Gönderilen metrikleri temizle
    if (!isFinal) {
      this.metrics = [];
      this.resourceTimings = [];
      this.longTasks = [];
      this.interactionDelays = [];
    }
  }
  
  // Bağlantı bilgisini al
  private getConnectionInfo(): string {
    if (navigator.connection) {
      const conn = navigator.connection as any;
      return `${conn.effectiveType || 'unknown'} (rtt: ${conn.rtt || 'unknown'}, downlink: ${conn.downlink || 'unknown'})`;
    }
    return 'unknown';
  }
}

// Performans servis örneği
export const performanceService = PerformanceService.getInstance();

// Performans hook'u
import { useEffect, useRef } from 'react';

export const usePerformanceMonitoring = (componentName: string) => {
  const renderStartTime = useRef<number>(performance.now());
  
  // Component render süresini ölç
  useEffect(() => {
    const renderTime = performance.now() - renderStartTime.current;
    performanceService.addCustomMetric(`RenderTime-${componentName}`, renderTime);
    
    // Component temizlendiğinde süreyi ölç
    return () => {
      const totalMountedTime = performance.now() - renderStartTime.current;
      performanceService.addCustomMetric(`MountedTime-${componentName}`, totalMountedTime);
    };
  }, [componentName]);
  
  return {
    // Component içindeki işlemleri zamanlama için
    measureOperation: (operationName: string) => {
      return performanceService.startTimer(`${componentName}-${operationName}`);
    },
    // Özel metrik eklemek için
    addCustomMetric: (name: string, value: number) => {
      performanceService.addCustomMetric(`${componentName}-${name}`, value);
    }
  };
};

// Düşük performans uyarı bileşeni
import React, { useState } from 'react';

export const PerformanceWarningBanner: React.FC = () => {
  const [show, setShow] = useState<boolean>(false);
  const [message, setMessage] = useState<string>('');
  
  useEffect(() => {
    // LCP değeri 2.5 saniyeden fazlaysa uyarı göster
    getLCP(metric => {
      if (metric.value > 2500) {
        setMessage('Page is loading slower than expected. You may experience reduced performance.');
        setShow(true);
      }
    });
    
    // FID değeri 100ms'den fazlaysa uyarı göster
    getFID(metric => {
      if (metric.value > 100) {
        setMessage('Page is responding slowly to interactions. You may experience delays.');
        setShow(true);
      }
    });
    
    // Memory kullanımı yüksekse uyarı göster
    if (performance && (performance as any).memory) {
      setInterval(() => {
        const memory = (performance as any).memory;
        const usedHeapSizeMB = memory.usedJSHeapSize / (1024 * 1024);
        const totalHeapSizeMB = memory.totalJSHeapSize / (1024 * 1024);
        
        if (usedHeapSizeMB > totalHeapSizeMB * 0.9) { // %90'dan fazla bellek kullanımı
          setMessage('Application is using high memory. Consider refreshing the page.');
          setShow(true);
        }
      }, 30000);
    }
  }, []);
  
  if (!show) {
    return null;
  }
  
  return (
    <div className="performance-warning-banner alert alert-warning alert-dismissible fade show" role="alert">
      <strong>Performance Warning:</strong> {message}
      <button type="button" className="btn-close" onClick={() => setShow(false)} aria-label="Close"></button>
    </div>
  );
};