// Last reviewed: 2025-04-30 08:46:51 UTC (User: Teeksss)
import React, { useState, useEffect, useContext } from 'react';
import { Toast, ToastContainer } from 'react-bootstrap';
import { FaCheckCircle, FaExclamationTriangle, FaInfoCircle, FaExclamationCircle, FaTimes } from 'react-icons/fa';
import { useTranslation } from 'react-i18next';

export enum NotificationType {
  SUCCESS = 'success',
  ERROR = 'error',
  WARNING = 'warning',
  INFO = 'info'
}

export interface Notification {
  id: string;
  title?: string;
  message: string;
  type: NotificationType;
  autoClose?: boolean;
  duration?: number; // in milliseconds
  timestamp: Date;
  onAction?: () => void;
  actionText?: string;
}

interface NotificationContextType {
  notifications: Notification[];
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
}

// Create context
const NotificationContext = React.createContext<NotificationContextType | undefined>(undefined);

// Provider component
export const NotificationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const { t } = useTranslation();
  
  // Add new notification
  const addNotification = (
    notification: Omit<Notification, 'id' | 'timestamp'>
  ) => {
    const id = Math.random().toString(36).substring(2, 11);
    const timestamp = new Date();
    
    // Create complete notification object
    const newNotification: Notification = {
      ...notification,
      id,
      timestamp,
      autoClose: notification.autoClose !== false, // default to true
      duration: notification.duration || 5000 // default to 5 seconds
    };
    
    // Add to list
    setNotifications(prev => [...prev, newNotification]);
    
    // If auto close enabled, set timeout
    if (newNotification.autoClose) {
      setTimeout(() => {
        removeNotification(id);
      }, newNotification.duration);
    }
  };
  
  // Remove notification by id
  const removeNotification = (id: string) => {
    setNotifications(prev => prev.filter(notification => notification.id !== id));
  };
  
  // Clear all notifications
  const clearNotifications = () => {
    setNotifications([]);
  };
  
  // Add keyboard event listener for accessibility
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Escape key clears all notifications
      if (e.key === 'Escape' && notifications.length > 0) {
        clearNotifications();
      }
    };
    
    document.addEventListener('keydown', handleKeyDown);
    
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [notifications.length]);
  
  return (
    <NotificationContext.Provider
      value={{
        notifications,
        addNotification,
        removeNotification,
        clearNotifications
      }}
    >
      {children}
      <NotificationDisplay />
    </NotificationContext.Provider>
  );
};

// Custom hook for using the notification context
export const useNotification = () => {
  const context = useContext(NotificationContext);
  
  if (!context) {
    throw new Error('useNotification must be used within a NotificationProvider');
  }
  
  return context;
};

// Helper method for easier notification creation
export const useNotify = () => {
  const { addNotification } = useNotification();
  const { t } = useTranslation();
  
  const notify = {
    success: (message: string, options?: Partial<Omit<Notification, 'id' | 'timestamp' | 'type' | 'message'>>) => {
      addNotification({
        type: NotificationType.SUCCESS,
        message,
        title: options?.title || t('notifications.success'),
        ...options
      });
    },
    
    error: (message: string, options?: Partial<Omit<Notification, 'id' | 'timestamp' | 'type' | 'message'>>) => {
      addNotification({
        type: NotificationType.ERROR,
        message,
        title: options?.title || t('notifications.error'),
        autoClose: false, // Errors don't auto-close by default
        ...options
      });
    },
    
    warning: (message: string, options?: Partial<Omit<Notification, 'id' | 'timestamp' | 'type' | 'message'>>) => {
      addNotification({
        type: NotificationType.WARNING,
        message,
        title: options?.title || t('notifications.warning'),
        ...options
      });
    },
    
    info: (message: string, options?: Partial<Omit<Notification, 'id' | 'timestamp' | 'type' | 'message'>>) => {
      addNotification({
        type: NotificationType.INFO,
        message,
        title: options?.title || t('notifications.info'),
        ...options
      });
    }
  };
  
  return notify;
};

// Component to display notifications
const NotificationDisplay: React.FC = () => {
  const { notifications, removeNotification } = useNotification();
  
  // Get icon based on notification type
  const getIcon = (type: NotificationType) => {
    switch (type) {
      case NotificationType.SUCCESS:
        return <FaCheckCircle className="notification-icon" />;
      case NotificationType.ERROR:
        return <FaExclamationCircle className="notification-icon" />;
      case NotificationType.WARNING:
        return <FaExclamationTriangle className="notification-icon" />;
      case NotificationType.INFO:
      default:
        return <FaInfoCircle className="notification-icon" />;
    }
  };
  
  // Get class name based on notification type
  const getClassName = (type: NotificationType) => {
    return `notification-${type}`;
  };
  
  return (
    <ToastContainer className="notification-container p-3" position="top-end">
      {notifications.map(notification => (
        <Toast 
          key={notification.id}
          onClose={() => removeNotification(notification.id)}
          className={`notification ${getClassName(notification.type)}`}
          animation={true}
          autohide={false}
        >
          <Toast.Header>
            {getIcon(notification.type)}
            <strong className="me-auto">{notification.title}</strong>
            <small>
              {notification.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </small>
          </Toast.Header>
          <Toast.Body>
            <div className="notification-message">
              {notification.message}
            </div>
            
            {notification.onAction && (
              <button 
                className="btn btn-sm btn-link notification-action mt-2" 
                onClick={notification.onAction}
              >
                {notification.actionText || 'Action'}
              </button>
            )}
          </Toast.Body>
        </Toast>
      ))}
    </ToastContainer>
  );
};

export default NotificationProvider;