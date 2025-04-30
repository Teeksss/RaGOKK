// Last reviewed: 2025-04-30 09:17:40 UTC (User: Teeksss)
import React, { useState, useEffect } from 'react';
import { CSSTransition } from 'react-transition-group';
import { useLocation } from 'react-router-dom';

// Geçiş türleri
export enum TransitionType {
  FADE = 'fade',
  SLIDE_LEFT = 'slide-left',
  SLIDE_RIGHT = 'slide-right',
  SLIDE_UP = 'slide-up',
  SLIDE_DOWN = 'slide-down',
  SCALE = 'scale',
  NONE = 'none'
}

interface PageTransitionProps {
  children: React.ReactNode;
  type?: TransitionType;
  timeout?: number;
  className?: string;
}

const PageTransition: React.FC<PageTransitionProps> = ({
  children,
  type = TransitionType.FADE,
  timeout = 300,
  className = ''
}) => {
  const location = useLocation();
  const [showPage, setShowPage] = useState(false);
  
  // Sayfa yüklendikten sonra geçiş efektini başlat
  useEffect(() => {
    setShowPage(false);
    
    // Kısa bir gecikme, yeni rota değişiminin yerleşmesine izin verir
    const timer = setTimeout(() => {
      setShowPage(true);
    }, 50);
    
    return () => clearTimeout(timer);
  }, [location.pathname]);
  
  // Geçiş türüne göre CSS sınıfları
  const getTransitionClasses = () => {
    switch (type) {
      case TransitionType.SLIDE_LEFT:
        return {
          enter: 'slide-left-enter',
          enterActive: 'slide-left-enter-active',
          exit: 'slide-left-exit',
          exitActive: 'slide-left-exit-active'
        };
      case TransitionType.SLIDE_RIGHT:
        return {
          enter: 'slide-right-enter',
          enterActive: 'slide-right-enter-active',
          exit: 'slide-right-exit',
          exitActive: 'slide-right-exit-active'
        };
      case TransitionType.SLIDE_UP:
        return {
          enter: 'slide-up-enter',
          enterActive: 'slide-up-enter-active',
          exit: 'slide-up-exit',
          exitActive: 'slide-up-exit-active'
        };
      case TransitionType.SLIDE_DOWN:
        return {
          enter: 'slide-down-enter',
          enterActive: 'slide-down-enter-active',
          exit: 'slide-down-exit',
          exitActive: 'slide-down-exit-active'
        };
      case TransitionType.SCALE:
        return {
          enter: 'scale-enter',
          enterActive: 'scale-enter-active',
          exit: 'scale-exit',
          exitActive: 'scale-exit-active'
        };
      case TransitionType.NONE:
        return {};
      case TransitionType.FADE:
      default:
        return {
          enter: 'fade-enter',
          enterActive: 'fade-enter-active',
          exit: 'fade-exit',
          exitActive: 'fade-exit-active'
        };
    }
  };
  
  // Geçiş yok ise doğrudan içeriği göster
  if (type === TransitionType.NONE) {
    return <>{children}</>;
  }
  
  return (
    <CSSTransition
      in={showPage}
      timeout={timeout}
      classNames={getTransitionClasses()}
      unmountOnExit
    >
      <div className={`page-transition ${className}`}>
        {children}
      </div>
    </CSSTransition>
  );
};

export default PageTransition;