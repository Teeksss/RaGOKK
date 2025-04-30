// Last reviewed: 2025-04-30 09:17:40 UTC (User: Teeksss)
import React, { useState, useRef, useEffect } from 'react';

// Hareket yönü
export enum SwipeDirection {
  LEFT = 'left',
  RIGHT = 'right',
  UP = 'up',
  DOWN = 'down'
}

// Hareket tipi
export enum GestureType {
  SWIPE = 'swipe',
  TAP = 'tap',
  DOUBLE_TAP = 'doubleTap',
  LONG_PRESS = 'longPress',
  PINCH = 'pinch'
}

interface TouchPoint {
  x: number;
  y: number;
  time: number;
}

interface TouchGestureProps {
  onSwipe?: (direction: SwipeDirection) => void;
  onTap?: (x: number, y: number) => void;
  onDoubleTap?: (x: number, y: number) => void;
  onLongPress?: (x: number, y: number) => void;
  onPinch?: (scale: number) => void;
  swipeThreshold?: number;
  longPressDelay?: number;
  disabled?: boolean;
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

const TouchGestures: React.FC<TouchGestureProps> = ({
  onSwipe,
  onTap,
  onDoubleTap,
  onLongPress,
  onPinch,
  swipeThreshold = 50,
  longPressDelay = 500,
  disabled = false,
  children,
  className = '',
  style = {}
}) => {
  // Dokunma referansları
  const touchStartRef = useRef<TouchPoint | null>(null);
  const lastTapRef = useRef<TouchPoint | null>(null);
  const longPressTimerRef = useRef<NodeJS.Timeout | null>(null);
  const initialTouchesRef = useRef<React.Touch[]>([]);
  
  // Hareket durumları
  const [isTouching, setIsTouching] = useState<boolean>(false);
  const [isLongPressed, setIsLongPressed] = useState<boolean>(false);
  
  // Temizleme fonksiyonu
  const clearLongPressTimer = () => {
    if (longPressTimerRef.current) {
      clearTimeout(longPressTimerRef.current);
      longPressTimerRef.current = null;
    }
  };
  
  // Component unmount olduğunda temizle
  useEffect(() => {
    return () => {
      clearLongPressTimer();
    };
  }, []);
  
  // Dokunma başladığında
  const handleTouchStart = (e: React.TouchEvent) => {
    if (disabled || e.touches.length === 0) return;
    
    // Tek parmak dokunma
    if (e.touches.length === 1) {
      const touch = e.touches[0];
      const touchPoint: TouchPoint = {
        x: touch.clientX,
        y: touch.clientY,
        time: Date.now()
      };
      
      touchStartRef.current = touchPoint;
      setIsTouching(true);
      
      // Uzun dokunma zamanlayıcısı
      if (onLongPress) {
        clearLongPressTimer();
        
        longPressTimerRef.current = setTimeout(() => {
          setIsLongPressed(true);
          onLongPress(touchPoint.x, touchPoint.y);
        }, longPressDelay);
      }
    }
    
    // Çoklu dokunma (pinch için)
    if (e.touches.length === 2 && onPinch) {
      initialTouchesRef.current = Array.from(e.touches);
    }
  };
  
  // Dokunma hareket ediyor
  const handleTouchMove = (e: React.TouchEvent) => {
    if (disabled || !touchStartRef.current || e.touches.length === 0) return;
    
    // Uzun dokunma iptal (kullanıcı hareket ettiyse)
    const touch = e.touches[0];
    const touchStart = touchStartRef.current;
    const dx = touch.clientX - touchStart.x;
    const dy = touch.clientY - touchStart.y;
    
    // Hareket eşiğini aştıysa, uzun dokunma iptal
    if (Math.abs(dx) > 10 || Math.abs(dy) > 10) {
      clearLongPressTimer();
    }
    
    // Pinch hareketi
    if (e.touches.length === 2 && onPinch && initialTouchesRef.current.length === 2) {
      const initialTouches = initialTouchesRef.current;
      const currentTouches = Array.from(e.touches);
      
      // İlk mesafeyi hesapla
      const initialDistance = Math.hypot(
        initialTouches[1].clientX - initialTouches[0].clientX,
        initialTouches[1].clientY - initialTouches[0].clientY
      );
      
      // Mevcut mesafeyi hesapla
      const currentDistance = Math.hypot(
        currentTouches[1].clientX - currentTouches[0].clientX,
        currentTouches[1].clientY - currentTouches[0].clientY
      );
      
      // Ölçek faktörünü hesapla
      const scale = currentDistance / initialDistance;
      onPinch(scale);
    }
  };
  
  // Dokunma bitti
  const handleTouchEnd = (e: React.TouchEvent) => {
    if (disabled || !touchStartRef.current) return;
    
    // Uzun dokunma zamanlayıcısını temizle
    clearLongPressTimer();
    
    const touchEnd = {
      x: e.changedTouches[0].clientX,
      y: e.changedTouches[0].clientY,
      time: Date.now()
    };
    
    const touchStart = touchStartRef.current;
    const dx = touchEnd.x - touchStart.x;
    const dy = touchEnd.y - touchStart.y;
    const duration = touchEnd.time - touchStart.time;
    
    // Uzun dokunma yapılmadıysa ve eşik aşılmadıysa dokunma olarak işle
    if (!isLongPressed && Math.abs(dx) < 10 && Math.abs(dy) < 10 && duration < 500) {
      // Çift dokunma kontrolü
      if (onDoubleTap && lastTapRef.current) {
        const lastTap = lastTapRef.current;
        const timeSinceLastTap = touchEnd.time - lastTap.time;
        
        if (timeSinceLastTap < 300) {
          onDoubleTap(touchEnd.x, touchEnd.y);
          lastTapRef.current = null;
          return;
        }
      }
      
      // Tek dokunma
      if (onTap) {
        onTap(touchEnd.x, touchEnd.y);
      }
      
      // Son dokunmayı kaydet (çift dokunma için)
      lastTapRef.current = touchEnd;
    }
    
    // Kaydırma yönünü belirle
    if (onSwipe && Math.abs(dx) > swipeThreshold || Math.abs(dy) > swipeThreshold) {
      if (Math.abs(dx) > Math.abs(dy)) {
        // Yatay kaydırma
        onSwipe(dx > 0 ? SwipeDirection.RIGHT : SwipeDirection.LEFT);
      } else {
        // Dikey kaydırma
        onSwipe(dy > 0 ? SwipeDirection.DOWN : SwipeDirection.UP);
      }
    }
    
    // Durumu sıfırla
    touchStartRef.current = null;
    initialTouchesRef.current = [];
    setIsTouching(false);
    setIsLongPressed(false);
  };
  
  return (
    <div
      className={`touch-gesture-container ${className}`}
      style={style}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      {children}
    </div>
  );
};

export default TouchGestures;