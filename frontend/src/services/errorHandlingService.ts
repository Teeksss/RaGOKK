// Global error handling service
import { NotificationType } from '../components/common/NotificationSystem';

// Hata tipleri
export enum ErrorType {
  NETWORK = 'network',
  AUTHENTICATION = 'authentication',
  AUTHORIZATION = 'authorization',
  VALIDATION = 'validation',
  SERVER = 'server',
  NOT_FOUND = 'not_found',
  CLIENT = 'client',
  UNKNOWN = 'unknown'
}

// Hata durumu
export interface ErrorState {
  type: ErrorType;
  message: string;
  code?: string | number;
  timestamp: number;
  path?: string;
  details?: any;
  handled?: boolean;
}

// Error logger servisi
type LogLevel = 'info' | 'warn' | 'error' | 'debug';

interface LogEntry {
  level: LogLevel;
  message: string;
  timestamp: number;
  data?: any;
  userId?: string;
  sessionId?: string;
  url?: string;
}

// Bağımlılık enjeksiyonu için notificationType callback'i
type ShowNotification = (type: NotificationType, message: string, title?: string, duration?: number) => void;

export class ErrorHandlingService {
  private static instance: ErrorHandlingService;
  private errors: ErrorState[] = [];
  private logs: LogEntry[] = [];
  private showNotification: ShowNotification | null = null;
  private readonly MAX_ERRORS = 50;
  private readonly MAX_LOGS = 100;
  private sessionId: string;
  
  private constructor() {
    this.sessionId = this.generateSessionId();
    this.setupGlobalErrorHandler();
  }
  
  public static getInstance(): ErrorHandlingService {
    if (!ErrorHandlingService.instance) {
      ErrorHandlingService.instance = new ErrorHandlingService();
    }
    
    return ErrorHandlingService.instance;
  }
  
  // Bildirim gösterme fonksiyonunu ayarla (bağımlılık enjeksiyonu)
  public setNotificationFunction(notifyFn: ShowNotification): void {
    this.showNotification = notifyFn;
  }
  
  // Hata işleme
  public handleError(error: any, showNotification = true): ErrorState {
    const errorState = this.parseError(error);
    
    // Log error
    this.log('error', errorState.message, { 
      errorType: errorState.type,
      errorCode: errorState.code,
      details: errorState.details
    });
    
    // Store error
    this.storeError(errorState);
    
    // Show notification if needed
    if (showNotification && this.showNotification) {
      this.showErrorNotification(errorState);
    }
    
    // Handle specific error types
    switch (errorState.type) {
      case ErrorType.AUTHENTICATION:
        this.handleAuthenticationError(errorState);
        break;
      case ErrorType.AUTHORIZATION:
        this.handleAuthorizationError(errorState);
        break;
      case ErrorType.NETWORK:
        this.handleNetworkError(errorState);
        break;
    }
    
    return errorState;
  }
  
  // Log mesajı
  public log(level: LogLevel, message: string, data?: any): void {
    const logEntry: LogEntry = {
      level,
      message,
      timestamp: Date.now(),
      data,
      userId: this.getCurrentUserId(),
      sessionId: this.sessionId,
      url: window.location.href
    };
    
    // Add log to memory
    this.logs.unshift(logEntry);
    
    // Limit logs array size
    if (this.logs.length > this.MAX_LOGS) {
      this.logs = this.logs.slice(0, this.MAX_LOGS);
    }
    
    // Console log for development
    if (process.env.NODE_ENV !== 'production') {
      console[level](message, data || '');
    }
    
    // Send to monitoring service in production
    if (process.env.NODE_ENV === 'production' && (level === 'error' || level === 'warn')) {
      this.sendToMonitoring(logEntry);
    }
  }
  
  // Son hatalar
  public getRecentErrors(): ErrorState[] {
    return [...this.errors];
  }
  
  // Son loglar
  public getRecentLogs(): LogEntry[] {
    return [...this.logs];
  }
  
  // Hataları temizle
  public clearErrors(): void {
    this.errors = [];
  }
  
  // Hatayı ayrıştır
  private parseError(error: any): ErrorState {
    const now = Date.now();
    
    // Network error
    if (!error) {
      return {
        type: ErrorType.UNKNOWN,
        message: 'An unknown error occurred',
        timestamp: now
      };
    }
    
    // Axios error
    if (error.isAxiosError) {
      if (!error.response) {
        return {
          type: ErrorType.NETWORK,
          message: 'Network error occurred. Please check your connection.',
          timestamp: now,
          details: {
            request: error.config
          }
        };
      }
      
      const { status, data } = error.response;
      
      // Authentication error
      if (status === 401) {
        return {
          type: ErrorType.AUTHENTICATION,
          message: data.message || 'Authentication failed. Please login again.',
          code: status,
          timestamp: now,
          path: error.config.url
        };
      }
      
      // Authorization error
      if (status === 403) {
        return {
          type: ErrorType.AUTHORIZATION,
          message: data.message || 'You do not have permission to perform this action.',
          code: status,
          timestamp: now,
          path: error.config.url
        };
      }
      
      // Validation error
      if (status === 400 || status === 422) {
        return {
          type: ErrorType.VALIDATION,
          message: data.message || 'Invalid input data.',
          code: status,
          timestamp: now,
          details: data.errors || data,
          path: error.config.url
        };
      }
      
      // Not found
      if (status === 404) {
        return {
          type: ErrorType.NOT_FOUND,
          message: data.message || 'The requested resource was not found.',
          code: status,
          timestamp: now,
          path: error.config.url
        };
      }
      
      // Server error
      if (status >= 500) {
        return {
          type: ErrorType.SERVER,
          message: 'A server error occurred. Please try again later.',
          code: status,
          timestamp: now,
          path: error.config.url
        };
      }
      
      // Other HTTP errors
      return {
        type: ErrorType.CLIENT,
        message: data.message || 'An error occurred.',
        code: status,
        timestamp: now,
        path: error.config.url,
        details: data
      };
    }
    
    // Standard error object
    if (error instanceof Error) {
      return {
        type: ErrorType.CLIENT,
        message: error.message,
        timestamp: now,
        details: {
          stack: error.stack
        }
      };
    }
    
    // String error
    if (typeof error === 'string') {
      return {
        type: ErrorType.CLIENT,
        message: error,
        timestamp: now
      };
    }
    
    // Object with message
    if (typeof error === 'object' && error.message) {
      return {
        type: ErrorType.CLIENT,
        message: error.message,
        timestamp: now,
        details: error
      };
    }
    
    // Unknown error
    return {
      type: ErrorType.UNKNOWN,
      message: 'An unexpected error occurred',
      timestamp: now,
      details: error
    };
  }
  
  // Hata depolama
  private storeError(error: ErrorState): void {
    this.errors.unshift({
      ...error,
      handled: true
    });
    
    // Limit errors array size
    if (this.errors.length > this.MAX_ERRORS) {
      this.errors = this.errors.slice(0, this.MAX_ERRORS);
    }
  }
  
  // Hata bildirimi göster
  private showErrorNotification(error: ErrorState): void {
    if (!this.showNotification) return;
    
    let title: string;
    let duration = 5000;
    
    switch (error.type) {
      case ErrorType.AUTHENTICATION:
        title = 'Authentication Error';
        break;
      case ErrorType.AUTHORIZATION:
        title = 'Access Denied';
        break;
      case ErrorType.VALIDATION:
        title = 'Validation Error';
        break;
      case ErrorType.NETWORK:
        title = 'Network Error';
        duration = 8000; // Longer duration for network errors
        break;
      case ErrorType.SERVER:
        title = 'Server Error';
        break;
      case ErrorType.NOT_FOUND:
        title = 'Not Found';
        break;
      default:
        title = 'Error';
    }
    
    this.showNotification('error', error.message, title, duration);
  }
  
  // Oturum kimliği oluştur
  private generateSessionId(): string {
    return Date.now().toString(36) + Math.random().toString(36).substring(2);
  }
  
  // Mevcut kullanıcı kimliğini al
  private getCurrentUserId(): string | undefined {
    try {
      const user = JSON.parse(localStorage.getItem('user') || '{}');
      return user.id;
    } catch {
      return undefined;
    }
  }
  
  // Global hata işleyici kur
  private setupGlobalErrorHandler(): void {
    window.addEventListener('error', (event) => {
      this.handleError({
        message: event.message,
        details: {
          filename: event.filename,
          lineno: event.lineno,
          colno: event.colno,
          error: event.error
        }
      }, false); // Don't show notification for global errors
      
      return false; // Let the default handler run
    });
    
    window.addEventListener('unhandledrejection', (event) => {
      this.handleError({
        message: 'Unhandled Promise Rejection',
        details: event.reason
      }, false); // Don't show notification for unhandled rejections
      
      return false; // Let the default handler run
    });
  }
  
  // Kimlik doğrulama hatası
  private handleAuthenticationError(error: ErrorState): void {
    // Redirect to login if not already there
    if (!window.location.pathname.includes('/login')) {
      localStorage.removeItem('auth_token');
      window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname)}&message=session_expired`;
    }
  }
  
  // Yetkilendirme hatası
  private handleAuthorizationError(error: ErrorState): void {
    // Redirect to unauthorized page if needed
    if (!window.location.pathname.includes('/unauthorized')) {
      window.location.href = '/unauthorized';
    }
  }
  
  // Ağ hatası
  private handleNetworkError(error: ErrorState): void {
    // Check connection and retry options could be implemented here
  }
  
  // İzleme servisine gönder
  private sendToMonitoring(logEntry: LogEntry): void {
    // Implementation for sending logs to a monitoring service
    // This would be connected to a real monitoring service in production
    try {
      const beaconData = {
        ...logEntry,
        app: 'rag-base-frontend',
        version: process.env.REACT_APP_VERSION || '1.0.0',
        environment: process.env.NODE_ENV
      };
      
      // Use Navigator.sendBeacon for better performance and reliability
      if (navigator.sendBeacon) {
        navigator.sendBeacon('/api/v1/logs', JSON.stringify(beaconData));
      } else {
        // Fallback to fetch
        fetch('/api/v1/logs', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(beaconData),
          keepalive: true // Ensure the request is sent even if page is unloading
        }).catch(() => {
          // Silent catch - we don't want errors from the error logger
        });
      }
    } catch (e) {
      // Silent catch - we don't want errors from the error logger
    }
  }
}

// Singleton instance export
export const errorHandlingService = ErrorHandlingService.getInstance();

// Global error handling hook
export const useErrorHandler = () => {
  return {
    handleError: (error: any, showNotification = true) => {
      return errorHandlingService.handleError(error, showNotification);
    },
    log: (level: LogLevel, message: string, data?: any) => {
      errorHandlingService.log(level, message, data);
    },
    getRecentErrors: () => {
      return errorHandlingService.getRecentErrors();
    },
    getRecentLogs: () => {
      return errorHandlingService.getRecentLogs();
    },
    clearErrors: () => {
      errorHandlingService.clearErrors();
    }
  };
};

// ErrorBoundary component for React components
import React from 'react';

interface ErrorBoundaryProps {
  fallback?: React.ReactNode;
  children: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false
    };
  }
  
  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      error
    };
  }
  
  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    // Log the error
    errorHandlingService.handleError({
      message: error.message,
      details: {
        error,
        errorInfo,
        componentStack: errorInfo.componentStack
      }
    }, false);
  }
  
  render(): React.ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      
      return (
        <div className="error-boundary p-4 bg-light rounded-3 text-center">
          <h2>Oops! Something went wrong</h2>
          <p className="text-muted">
            We apologize for the inconvenience. Please try refreshing the page or contact support if the issue persists.
          </p>
          <div className="mt-3">
            <button
              className="btn btn-primary"
              onClick={() => window.location.reload()}
            >
              Refresh Page
            </button>
          </div>
          {process.env.NODE_ENV !== 'production' && this.state.error && (
            <div className="mt-4 text-start">
              <p className="text-danger fw-bold">{this.state.error.message}</p>
              <pre className="bg-dark text-light p-3 rounded small overflow-auto" style={{ maxHeight: '200px' }}>
                {this.state.error.stack}
              </pre>
            </div>
          )}
        </div>
      );
    }
    
    return this.props.children;
  }
}