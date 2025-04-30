// Last reviewed: 2025-04-30 11:32:10 UTC (User: TeeksssOrta)
// ... existing imports
import * as serviceWorker from './serviceWorker';
import { analyticsService, EventCategory } from './services/analyticsService';

// ... ReactDOM.render code

// Service Worker'ı kaydet
serviceWorker.register({
  onSuccess: (registration) => {
    console.log('Service Worker registered successfully!');
    analyticsService.trackEvent({
      category: EventCategory.PERFORMANCE,
      action: 'ServiceWorkerRegistered',
      label: 'Success'
    });
  },
  onUpdate: (registration) => {
    console.log('New version available!');
    analyticsService.trackEvent({
      category: EventCategory.PERFORMANCE,
      action: 'ServiceWorkerUpdate',
      label: 'Available'
    });
  },
  onOffline: () => {
    console.log('Application is now offline');
    analyticsService.trackEvent({
      category: EventCategory.USER,
      action: 'ConnectionStatus',
      label: 'Offline'
    });
  },
  onOnline: () => {
    console.log('Application is now online');
    analyticsService.trackEvent({
      category: EventCategory.USER,
      action: 'ConnectionStatus',
      label: 'Online'
    });
  }
});

// Web vitals reporting...