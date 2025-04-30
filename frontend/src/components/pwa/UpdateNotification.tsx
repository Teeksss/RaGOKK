// Last reviewed: 2025-04-30 11:32:10 UTC (User: TeeksssOrta)
import React, { useState, useEffect } from 'react';
import { Toast, Button } from 'react-bootstrap';
import { FaDownload, FaWrench } from 'react-icons/fa';
import { useTranslation } from 'react-i18next';
import { checkForUpdates, activateUpdate } from '../../serviceWorker';

const UpdateNotification: React.FC = () => {
  const { t } = useTranslation();
  const [showUpdateToast, setShowUpdateToast] = useState<boolean>(false);
  const [updating, setUpdating] = useState<boolean>(false);

  // Uygulama başlatıldığında ve belirli aralıklarla
  // service worker güncellemelerini kontrol et
  useEffect(() => {
    const checkUpdate = () => {
      checkForUpdates((hasUpdate) => {
        if (hasUpdate) {
          setShowUpdateToast(true);
        }
      });
    };

    // İlk kontrol
    checkUpdate();

    // Her 60 dakikada bir güncelleme kontrolü
    const interval = setInterval(checkUpdate, 60 * 60 * 1000);

    return () => clearInterval(interval);
  }, []);

  // Güncellemeyi etkinleştir
  const handleUpdate = () => {
    setUpdating(true);
    
    // Mevcut işlemlerin tamamlanmasını bekle
    setTimeout(() => {
      activateUpdate();
    }, 1000);
  };

  if (!showUpdateToast) {
    return null;
  }

  return (
    <Toast
      className="position-fixed top-0 end-0 m-3 pwa-update-toast"
      onClose={() => setShowUpdateToast(false)}
      show={showUpdateToast}
      delay={25000}
      autohide
    >
      <Toast.Header>
        <FaWrench className="me-2" />
        <strong className="me-auto">{t('pwa.updateAvailable')}</strong>
      </Toast.Header>
      <Toast.Body>
        <p>{t('pwa.updateAvailableMessage')}</p>
        <div className="d-flex justify-content-end mt-2">
          <Button
            variant="outline-secondary"
            size="sm"
            className="me-2"
            onClick={() => setShowUpdateToast(false)}
          >
            {t('common.later')}
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleUpdate}
            disabled={updating}
          >
            {updating ? (
              <>
                <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                {t('pwa.updating')}
              </>
            ) : (
              <>
                <FaDownload className="me-1" />
                {t('pwa.update')}
              </>
            )}
          </Button>
        </div>
      </Toast.Body>
    </Toast>
  );
};

export default UpdateNotification;