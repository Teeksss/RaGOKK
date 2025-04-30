// Last reviewed: 2025-04-30 08:46:51 UTC (User: Teeksss)
import React, { useState, useEffect } from 'react';
import { Spinner, Card, ProgressBar } from 'react-bootstrap';
import { FaExclamationTriangle, FaInfoCircle } from 'react-icons/fa';
import { useTranslation } from 'react-i18next';

export enum LoaderType {
  SPINNER = 'spinner',
  SKELETON = 'skeleton',
  PROGRESS = 'progress'
}

export enum LoaderSize {
  SMALL = 'sm',
  MEDIUM = 'md',
  LARGE = 'lg'
}

interface ContentLoaderProps {
  isLoading: boolean;
  error?: string | null;
  type?: LoaderType;
  size?: LoaderSize;
  progress?: number; // 0-100
  message?: string;
  overlay?: boolean;
  onRetry?: () => void;
  className?: string;
  children?: React.ReactNode;
}

const ContentLoader: React.FC<ContentLoaderProps> = ({
  isLoading,
  error,
  type = LoaderType.SPINNER,
  size = LoaderSize.MEDIUM,
  progress = -1,
  message,
  overlay = false,
  onRetry,
  className = '',
  children
}) => {
  const { t } = useTranslation();
  const [displayLoader, setDisplayLoader] = useState(isLoading);
  const [fastLoad, setFastLoad] = useState(false);
  
  // Delay showing loader for fast operations to avoid flicker
  useEffect(() => {
    if (isLoading) {
      const timer = setTimeout(() => {
        setDisplayLoader(true);
      }, 300); // 300ms delay before showing loader
      
      const fastTimer = setTimeout(() => {
        setFastLoad(true);
      }, 3000); // After 3s, consider this a longer operation
      
      return () => {
        clearTimeout(timer);
        clearTimeout(fastTimer);
      };
    } else {
      setDisplayLoader(false);
      setFastLoad(false);
    }
  }, [isLoading]);
  
  // Determine spinner size
  const spinnerSize = size === LoaderSize.SMALL ? 'sm' : undefined;
  
  // Progress determination
  const determineProgress = () => {
    if (progress >= 0 && progress <= 100) {
      return progress;
    }
    return null;
  };
  
  // Generate loading messages
  const getLoadingMessage = () => {
    if (message) return message;
    
    if (fastLoad) {
      return t('common.loading.takingLonger');
    }
    
    return t('common.loading.default');
  };
  
  // Render skeleton loading
  const renderSkeleton = () => {
    return (
      <div className={`skeleton-loader ${size}`}>
        <div className="skeleton-line" style={{ width: '80%' }}></div>
        <div className="skeleton-line" style={{ width: '90%' }}></div>
        <div className="skeleton-line" style={{ width: '60%' }}></div>
        <div className="skeleton-line" style={{ width: '75%' }}></div>
      </div>
    );
  };
  
  // Render error state
  const renderError = () => {
    return (
      <div className="text-center text-danger py-3">
        <div className="mb-2">
          <FaExclamationTriangle size={24} />
        </div>
        <p>{error || t('common.error.default')}</p>
        {onRetry && (
          <button 
            className="btn btn-sm btn-outline-primary" 
            onClick={onRetry}
          >
            {t('common.retry')}
          </button>
        )}
      </div>
    );
  };
  
  // Render loading content
  const renderLoader = () => {
    if (error) {
      return renderError();
    }
    
    if (displayLoader) {
      switch (type) {
        case LoaderType.SKELETON:
          return renderSkeleton();
          
        case LoaderType.PROGRESS:
          const currentProgress = determineProgress();
          return (
            <div className="text-center py-3">
              {currentProgress !== null ? (
                <ProgressBar 
                  now={currentProgress} 
                  label={`${Math.round(currentProgress)}%`} 
                  variant="primary"
                  animated
                />
              ) : (
                <ProgressBar animated now={100} variant="primary" />
              )}
              <div className="mt-2 text-muted small">{getLoadingMessage()}</div>
            </div>
          );
          
        case LoaderType.SPINNER:
        default:
          return (
            <div className="text-center py-3">
              <Spinner 
                animation="border" 
                variant="primary" 
                size={spinnerSize} 
                className="mb-2"
                role="status"
              >
                <span className="visually-hidden">{t('common.loading.screenReader')}</span>
              </Spinner>
              <div className="text-muted small">{getLoadingMessage()}</div>
            </div>
          );
      }
    }
    
    return children;
  };
  
  // If overlay mode is active
  if (overlay && displayLoader) {
    return (
      <div className={`position-relative ${className}`}>
        {children}
        <div className="loader-overlay">
          <div className="loader-content">
            {renderLoader()}
          </div>
        </div>
      </div>
    );
  }
  
  // Standard mode - replace content with loader
  return (
    <div className={className}>
      {displayLoader ? renderLoader() : children}
    </div>
  );
};

export default ContentLoader;