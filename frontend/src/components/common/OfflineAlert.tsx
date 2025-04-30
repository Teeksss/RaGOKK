// Last reviewed: 2025-04-30 10:37:40 UTC (User: Teeksss)
import React, { useState, useEffect } from 'react';
import { Alert, Button, Spinner } from 'react-bootstrap';
import { FaWifi, FaExclamationTriangle, FaSync, FaCheck, FaBan } from 'react-icons/fa';
import { useTranslation } from 'react-i18next';
import { useOfflineStatus } from '../../api/enhancedApi';
import { OfflineService } from '../../services/cacheService';

interface OfflineAlertProps {
  showPendingOperations?: boolean;
  className?: string;
}

const OfflineAlert: React.FC<OfflineAlertProps> = ({
  showPendingOperations = true,
  className = ''
}) => {
  const { t } = useTranslation();
  const isOffline = useOfflineStatus();
  
  const [pendingOperations, setPendingOperations] = useState<number>(0);
  const [syncing, setSyncing] = useState<boolean>(false);
  const [expanded, setExpanded] = useState<boolean>(false);
  
  // Bekleyen işlem sayısını güncelle
  useEffect(() => {
    const checkPendingOperations = async () => {
      if (showPendingOperations && isOffline === false) {
        const operations = await OfflineService.getPendingOperations();
        setPendingOperations(operations.length);
      }
    };
    
    checkPendingOperations();
    
    // 30 saniyede bir kontrol et
    const interval = setInterval(checkPendingOperations, 30000);
    
    return () => clearInterval(interval);
  }, [isOffline, showPendingOperations]);
  
  // Çevrimdışı çalışan yoksa gösterme
  if (!isOffline && pendingOperations === 0) {
    return null;
  }
  
  // Senkronizasyon işlemi
  const handleSync = async () => {
    if (syncing) return;
    
    setSyncing(true);
    
    try {
      // EnhancedApi'den offline kuyruğu işle
      const { processOfflineQueue } = await import('../../api/enhancedApi');
      await processOfflineQueue();
      
      // Başarılı senkronizasyon
      setPendingOperations(0);
      setExpanded(false);
      
      // Başarı bildirimi göster
      // showToast('success', t('offline.syncSuccess'));
    } catch (error) {
      console.error('Sync error:', error);
      // showToast('error', t('offline.syncError'));
    } finally {
      setSyncing(false);
    }
  };
  
  return (
    <div className={`offline-alert-container ${className}`}>
      <Alert 
        variant={isOffline ? "warning" : "info"}
        className="offline-status-alert mb-0"
      >
        <div className="d-flex justify-content-between align-items-center">
          <div className="d-flex align-items-center">
            {isOffline ? (
              <>
                <FaBan className="me-2" />
                <span>{t('offline.youAreOffline')}</span>
              </>
            ) : pendingOperations > 0 ? (
              <>
                <FaWifi className="me-2 text-success" />
                <span>
                  {t('offline.pendingSync', { count: pendingOperations })}
                </span>
              </>
            ) : null}
          </div>
          
          <div>
            {!isOffline && pendingOperations > 0 && (
              <Button 
                size="sm" 
                variant="outline-primary" 
                onClick={handleSync}
                disabled={syncing}
                className="me-2"
              >
                {syncing ? (
                  <>
                    <Spinner size="sm" animation="border" className="me-1" />
                    {t('offline.syncing')}
                  </>
                ) : (
                  <>
                    <FaSync className="me-1" />
                    {t('offline.sync')}
                  </>
                )}
              </Button>
            )}
            
            <Button 
              size="sm" 
              variant="link" 
              onClick={() => setExpanded(!expanded)}
              aria-expanded={expanded}
              className="text-dark p-0"
            >
              {expanded ? t('common.hide') : t('common.details')}
            </Button>
          </div>
        </div>
        
        {expanded && (
          <div className="offline-details mt-3">
            {isOffline ? (
              <>
                <p>{t('offline.offlineDescription')}</p>
                <ul className="mb-0">
                  <li>{t('offline.availableFeatures.browse')}</li>
                  <li>{t('offline.availableFeatures.view')}</li>
                  <li>{t('offline.availableFeatures.queue')}</li>
                </ul>
              </>
            ) : pendingOperations > 0 ? (
              <>
                <p>{t('offline.syncDescription')}</p>
                <div className="d-grid gap-2 d-sm-flex justify-content-sm-center">
                  <Button 
                    variant="success" 
                    onClick={handleSync}
                    disabled={syncing}
                  >
                    {syncing ? (
                      <>
                        <Spinner size="sm" animation="border" className="me-2" />
                        {t('offline.syncingOperations')}
                      </>
                    ) : (
                      <>
                        <FaCheck className="me-2" />
                        {t('offline.syncNow')}
                      </>
                    )}
                  </Button>
                </div>
              </>
            ) : null}
          </div>
        )}
      </Alert>
    </div>
  );
};

export default OfflineAlert;