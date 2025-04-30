// Last reviewed: 2025-04-30 11:17:29 UTC (User: TeeksssYüksek)
import React from 'react';
import { Button } from 'react-bootstrap';
import { errorHandlingService, ErrorType } from '../../services/errorHandlingService';
import { Link } from 'react-router-dom';

interface GlobalErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface GlobalErrorBoundaryState {
  hasError: boolean;
  error?: Error;
  errorInfo?: React.ErrorInfo;
  errorType?: ErrorType;
}

export class GlobalErrorBoundary extends React.Component<GlobalErrorBoundaryProps, GlobalErrorBoundaryState> {
  constructor(props: GlobalErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false
    };
  }

  static getDerivedStateFromError(error: Error): GlobalErrorBoundaryState {
    // Hata durumunu güncelle
    return {
      hasError: true,
      error
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    // Hata detaylarını güncelle
    this.setState({
      errorInfo,
      errorType: this.determineErrorType(error)
    });

    // Hata servisine bildir
    errorHandlingService.handleError({
      message: error.message,
      details: {
        name: error.name,
        stack: error.stack,
        componentStack: errorInfo.componentStack
      }
    }, false);
  }

  // Hata tipini belirle
  private determineErrorType(error: Error): ErrorType {
    if (error.message.includes('network') || error.message.includes('connection')) {
      return ErrorType.NETWORK;
    }

    if (error.message.includes('permission') || error.message.includes('unauthorized') || error.message.includes('forbidden')) {
      return ErrorType.AUTHORIZATION;
    }

    if (error.message.includes('not found') || error.message.includes('404')) {
      return ErrorType.NOT_FOUND;
    }

    if (error.message.includes('validation') || error.message.includes('invalid')) {
      return ErrorType.VALIDATION;
    }

    return ErrorType.CLIENT;
  }

  // Uygulamayı yeniden yükle
  handleReload = (): void => {
    window.location.reload();
  };

  // Ana sayfaya dön
  handleGoHome = (): void => {
    window.location.href = '/';
  };

  render(): React.ReactNode {
    if (this.state.hasError) {
      // Özel fallback varsa onu göster
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Hata tipine göre uygun mesajı göster
      let title = 'Something went wrong';
      let message = 'The application encountered an error. Please try again later.';
      let primaryAction = this.handleReload;
      let primaryActionText = 'Reload Page';

      switch (this.state.errorType) {
        case ErrorType.NETWORK:
          title = 'Network Error';
          message = 'Unable to connect to the server. Please check your internet connection and try again.';
          break;
        
        case ErrorType.AUTHORIZATION:
          title = 'Access Denied';
          message = 'You do not have permission to access this feature.';
          primaryAction = this.handleGoHome;
          primaryActionText = 'Go to Home';
          break;
        
        case ErrorType.NOT_FOUND:
          title = 'Not Found';
          message = 'The requested resource could not be found.';
          primaryAction = this.handleGoHome;
          primaryActionText = 'Go to Home';
          break;
        
        case ErrorType.VALIDATION:
          title = 'Validation Error';
          message = 'There was an issue with the data format. Please check your inputs and try again.';
          break;
      }

      return (
        <div className="error-boundary container py-5">
          <div className="row justify-content-center">
            <div className="col-md-8">
              <div className="card border-danger">
                <div className="card-header bg-danger text-white">
                  <h4 className="mb-0">{title}</h4>
                </div>
                <div className="card-body">
                  <div className="text-center mb-4">
                    <svg width="128" height="128" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path fillRule="evenodd" clipRule="evenodd" d="M24 4C12.9543 4 4 12.9543 4 24C4 35.0457 12.9543 44 24 44C35.0457 44 44 35.0457 44 24C44 12.9543 35.0457 4 24 4ZM24 36C22.8954 36 22 35.1046 22 34C22 32.8954 22.8954 32 24 32C25.1046 32 26 32.8954 26 34C26 35.1046 25.1046 36 24 36ZM24 28C22.8954 28 22 27.1046 22 26V16C22 14.8954 22.8954 14 24 14C25.1046 14 26 14.8954 26 16V26C26 27.1046 25.1046 28 24 28Z" fill="#dc3545"/>
                    </svg>
                  </div>
                  <p className="lead text-center mb-4">{message}</p>
                  <div className="d-flex justify-content-center gap-3">
                    <Button variant="primary" onClick={primaryAction}>
                      {primaryActionText}
                    </Button>
                    <Button variant="outline-secondary" as={Link} to="/help">
                      Get Help
                    </Button>
                  </div>
                </div>
                {process.env.NODE_ENV !== 'production' && this.state.error && (
                  <div className="card-footer bg-light">
                    <p className="text-danger fw-bold mb-2">{this.state.error.message}</p>
                    <div className="error-details">
                      <h6 className="mb-1">Stack Trace</h6>
                      <pre className="bg-dark text-light p-3 rounded small" style={{ maxHeight: '200px', overflow: 'auto' }}>
                        {this.state.error.stack}
                      </pre>
                      {this.state.errorInfo && (
                        <>
                          <h6 className="mb-1 mt-3">Component Stack</h6>
                          <pre className="bg-dark text-light p-3 rounded small" style={{ maxHeight: '200px', overflow: 'auto' }}>
                            {this.state.errorInfo.componentStack}
                          </pre>
                        </>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Sayfaya özel hata sınırı bileşeni
export const PageErrorBoundary: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <GlobalErrorBoundary
      fallback={
        <div className="page-error p-4 bg-light rounded-3">
          <div className="text-center">
            <h3 className="text-danger mb-3">Oops! Something went wrong</h3>
            <p className="mb-4">We encountered an error while loading this page.</p>
            <div className="d-flex justify-content-center gap-2">
              <Button variant="primary" onClick={() => window.location.reload()}>
                Refresh Page
              </Button>
              <Button variant="outline-secondary" as={Link} to="/">
                Go to Dashboard
              </Button>
            </div>
          </div>
        </div>
      }
    >
      {children}
    </GlobalErrorBoundary>
  );
};

// Kompakt bileşen hata sınırı
export const ComponentErrorBoundary: React.FC<{ children: React.ReactNode; name: string }> = ({ children, name }) => {
  return (
    <GlobalErrorBoundary
      fallback={
        <div className="component-error p-3 border border-warning rounded bg-light">
          <div className="text-center py-3">
            <p className="mb-2">Failed to load {name} component</p>
            <Button size="sm" variant="warning" onClick={() => window.location.reload()}>
              Try Again
            </Button>
          </div>
        </div>
      }
    >
      {children}
    </GlobalErrorBoundary>
  );
};