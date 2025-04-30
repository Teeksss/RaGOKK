// Last reviewed: 2025-04-30 11:32:10 UTC (User: TeeksssOrta)
import React, { useState, useEffect } from 'react';
import { Modal, Button } from 'react-bootstrap';
import { FaDownload, FaMobile, FaDesktop, FaTimes } from 'react-icons/fa';
import { useTranslation } from 'react-i18next';
import { analyticsService, EventCategory } from '../../services/analyticsService';

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed'; platform: string }>;
}

const InstallPrompt: React.FC = () => {
  const { t } = useTranslation();
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [showModal, setShowModal] = useState<boolean>(false);
  const [installable, setInstallable] = useState<boolean>(false);
  const [installDisabled, setInstallDisabled] = useState<boolean>(true);
  const [platform, setPlatform] = useState<'ios' | 'android' | 'desktop' | undefined>(undefined);

  useEffect(() => {
    // Kurulum isteği olayını yakala
    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      setInstallable(true);
      setInstallDisabled(false);

      // Kullanıcı daha önce reddettiyse 7 gün boyunca gösterme
      const lastPromptTime = localStorage.getItem('pwa_install_prompt_time');
      const hasDeclined = localStorage.getItem('pwa_install_declined') === 'true';
      
      if (lastPromptTime && hasDeclined) {
        const daysSinceLastPrompt = (Date.now() - parseInt(lastPromptTime)) / (1000 * 60 * 60 * 24);
        if (daysSinceLastPrompt < 7) {
          return;
        }
      }

      // Platform tespiti
      const userAgent = navigator.userAgent.toLowerCase();
      if (/iphone|ipad|ipod/.test(userAgent)) {
        setPlatform('ios');
      } else if (/android/.test(userAgent)) {
        setPlatform('android');
      } else {
        setPlatform('desktop');
      }

      // Kurulum istemini göster, ancak kullanıcının etkileşimden sonra
      // Kullanıcının etkileşime geçmesini bekle
      setTimeout(() => {
        if (document.visibilityState === 'visible') {
          setShowModal(true);
        }
      }, 3000);

      // Analitik
      analyticsService.trackEvent({
        category: EventCategory.USER,
        action: 'PWAInstallPromptShown',
        label: platform || 'unknown'
      });
    };

    // Kullanıcının uygulamayı yükleyip yüklemediğini kontrol et
    const handleAppInstalled = () => {
      setInstallable(false);
      setShowModal(false);
      
      // Analitik
      analyticsService.trackEvent({
        category: EventCategory.USER,
        action: 'PWAInstalled',
        label: platform || 'unknown'
      });

      // Kurulduğunu kaydet
      localStorage.setItem('pwa_installed', 'true');
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    window.addEventListener('appinstalled', handleAppInstalled);

    // Temizleme
    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
      window.removeEventListener('appinstalled', handleAppInstalled);
    };
  }, [platform]);

  // PWA kurulum isteği
  const handleInstallClick = async () => {
    if (!deferredPrompt) {
      return;
    }

    // Analitik
    analyticsService.trackEvent({
      category: EventCategory.USER,
      action: 'PWAInstallClicked',
      label: platform || 'unknown'
    });

    // Kurulum istemi
    deferredPrompt.prompt();
    setInstallDisabled(true);

    // Kullanıcının cevabını bekle
    const choiceResult = await deferredPrompt.userChoice;
    setDeferredPrompt(null);
    
    if (choiceResult.outcome === 'accepted') {
      console.log('PWA kurulumu kabul edildi');
      // Analitik
      analyticsService.trackEvent({
        category: EventCategory.USER,
        action: 'PWAInstallAccepted',
        label: platform || 'unknown'
      });
    } else {
      console.log('PWA kurulumu reddedildi');
      // Analitik
      analyticsService.trackEvent({
        category: EventCategory.USER,
        action: 'PWAInstallRejected',
        label: platform || 'unknown'
      });

      // Reddetme durumunu kaydet
      localStorage.setItem('pwa_install_declined', 'true');
      localStorage.setItem('pwa_install_prompt_time', Date.now().toString());
    }

    // Modalı kapat
    setShowModal(false);
  };

  // Kurulum istemini kapat
  const handleClose = () => {
    setShowModal(false);
    
    // Analitik
    analyticsService.trackEvent({
      category: EventCategory.USER,
      action: 'PWAInstallDismissed',
      label: platform || 'unknown'
    });

    // Reddetme durumunu kaydet
    localStorage.setItem('pwa_install_declined', 'true');
    localStorage.setItem('pwa_install_prompt_time', Date.now().toString());
  };

  if (!installable || !platform) {
    return null;
  }

  // iOS için özel talimatlar
  const renderIOSInstructions = () => (
    <div className="ios-instructions mt-3">
      <ol className="ps-3">
        <li>{t('pwa.ios.step1')}</li>
        <li>{t('pwa.ios.step2')}</li>
        <li>{t('pwa.ios.step3')}</li>
      </ol>
      <div className="text-center mt-3">
        <img
          src="/images/ios-install-pwa.png"
          alt="iOS Installation Instructions"
          className="img-fluid rounded"
          style={{ maxHeight: '200px' }}
        />
      </div>
    </div>
  );

  return (
    <Modal show={showModal} onHide={handleClose} centered>
      <Modal.Header closeButton>
        <Modal.Title>
          {platform === 'ios' ? <FaMobile className="me-2" /> : <FaDesktop className="me-2" />}
          {t('pwa.installTitle')}
        </Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <p className="lead">{t('pwa.installMessage')}</p>
        <ul className="pwa-benefits mt-3">
          <li>{t('pwa.benefit1')}</li>
          <li>{t('pwa.benefit2')}</li>
          <li>{t('pwa.benefit3')}</li>
        </ul>
        
        {platform === 'ios' && renderIOSInstructions()}
      </Modal.Body>
      <Modal.Footer>
        <Button variant="outline-secondary" onClick={handleClose}>
          <FaTimes className="me-1" />
          {t('common.notNow')}
        </Button>
        
        {platform !== 'ios' && (
          <Button
            variant="primary"
            onClick={handleInstallClick}
            disabled={installDisabled}
          >
            <FaDownload className="me-1" />
            {t('pwa.installButton')}
          </Button>
        )}
      </Modal.Footer>
    </Modal>
  );
};

export default InstallPrompt;