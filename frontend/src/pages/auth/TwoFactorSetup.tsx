// Last reviewed: 2025-04-30 07:48:16 UTC (User: Teeksss)
import React, { useState, useEffect } from 'react';
import { Container, Card, Button, Form, Alert, Spinner } from 'react-bootstrap';
import { FaQrcode, FaKey, FaCheck, FaArrowLeft } from 'react-icons/fa';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import { useToast } from '../../contexts/ToastContext';
import API from '../../api/api';

const TwoFactorSetup: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { user, updateUser } = useAuth();
  
  // State
  const [isLoading, setIsLoading] = useState(false);
  const [setupData, setSetupData] = useState<any>(null);
  const [verificationCode, setVerificationCode] = useState('');
  const [error, setError] = useState('');
  const [isChecking2FAStatus, setIsChecking2FAStatus] = useState(true);
  
  // 2FA durumunu kontrol et
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const response = await API.get('/auth/2fa/status');
        
        // 2FA zaten aktif mi?
        if (response.data.has_2fa) {
          showToast('info', t('auth.2fa.alreadyEnabled'));
          navigate('/profile');
        }
        
        setIsChecking2FAStatus(false);
      } catch (err: any) {
        console.error('Error checking 2FA status:', err);
        setError(err?.response?.data?.detail || t('auth.2fa.errorChecking'));
        setIsChecking2FAStatus(false);
      }
    };
    
    checkStatus();
  }, []);
  
  // 2FA kurulumu başlat
  const startSetup = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      const response = await API.post('/auth/2fa/setup');
      setSetupData(response.data);
    } catch (err: any) {
      console.error('Error setting up 2FA:', err);
      setError(err?.response?.data?.detail || t('auth.2fa.setupError'));
    } finally {
      setIsLoading(false);
    }
  };
  
  // Doğrulama kodu gönder
  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!verificationCode || verificationCode.length !== 6) {
      setError(t('auth.2fa.invalidCode'));
      return;
    }
    
    setIsLoading(true);
    setError('');
    
    try {
      await API.post('/auth/2fa/verify', { code: verificationCode });
      
      // Kullanıcı bilgisini güncelle
      if (user && updateUser) {
        updateUser({
          ...user,
          has_2fa: true
        });
      }
      
      showToast('success', t('auth.2fa.setupSuccess'));
      navigate('/profile');
    } catch (err: any) {
      console.error('Error verifying 2FA code:', err);
      setError(err?.response?.data?.detail || t('auth.2fa.verifyError'));
    } finally {
      setIsLoading(false);
    }
  };
  
  // Yükleniyor durumu
  if (isChecking2FAStatus) {
    return (
      <Container className="d-flex justify-content-center align-items-center" style={{ minHeight: '70vh' }}>
        <Spinner animation="border" />
      </Container>
    );
  }
  
  return (
    <Container className="py-4">
      <Card className="mx-auto" style={{ maxWidth: '500px' }}>
        <Card.Header className="bg-primary text-white">
          <h4 className="mb-0">
            <FaKey className="me-2" />
            {t('auth.2fa.setup')}
          </h4>
        </Card.Header>
        
        <Card.Body>
          {error && (
            <Alert variant="danger" className="mb-4">
              {error}
            </Alert>
          )}
          
          {!setupData ? (
            // Adım 1: Kurulum başlangıcı
            <div className="text-center">
              <p className="mb-4">{t('auth.2fa.setupDescription')}</p>
              
              <div className="d-grid gap-2">
                <Button 
                  variant="primary" 
                  size="lg" 
                  onClick={startSetup}
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <>
                      <Spinner animation="border" size="sm" className="me-2" />
                      {t('common.loading')}
                    </>
                  ) : (
                    <>
                      <FaQrcode className="me-2" />
                      {t('auth.2fa.startSetup')}
                    </>
                  )}
                </Button>
                
                <Button 
                  variant="outline-secondary" 
                  onClick={() => navigate('/profile')}
                  disabled={isLoading}
                >
                  <FaArrowLeft className="me-2" />
                  {t('common.back')}
                </Button>
              </div>
            </div>
          ) : (
            // Adım 2: QR kod tarama ve doğrulama
            <div>
              <p className="mb-3">{t('auth.2fa.scanQrCode')}</p>
              
              <div className="text-center mb-4">
                <img 
                  src={setupData.qr_code} 
                  alt="2FA QR Code" 
                  className="img-thumbnail" 
                  style={{ maxWidth: '250px' }} 
                />
              </div>
              
              <Alert variant="info" className="mb-4">
                <p className="mb-1"><strong>{t('auth.2fa.manualSetup')}</strong></p>
                <p className="mb-0"><small>{t('auth.2fa.secretKey')}:</small></p>
                <code className="d-block p-2 bg-light">{setupData.secret}</code>
              </Alert>
              
              <Form onSubmit={handleVerify}>
                <Form.Group className="mb-4">
                  <Form.Label>{t('auth.2fa.verificationCode')}</Form.Label>
                  <Form.Control
                    type="text"
                    placeholder="000000"
                    value={verificationCode}
                    onChange={(e) => setVerificationCode(e.target.value)}
                    maxLength={6}
                    required
                    autoComplete="one-time-code"
                  />
                  <Form.Text className="text-muted">
                    {t('auth.2fa.enterCode')}
                  </Form.Text>
                </Form.Group>
                
                <div className="d-grid gap-2">
                  <Button 
                    type="submit" 
                    variant="success" 
                    disabled={isLoading || !verificationCode || verificationCode.length !== 6}
                  >
                    {isLoading ? (
                      <>
                        <Spinner animation="border" size="sm" className="me-2" />
                        {t('common.verifying')}
                      </>
                    ) : (
                      <>
                        <FaCheck className="me-2" />
                        {t('auth.2fa.verify')}
                      </>
                    )}
                  </Button>
                </div>
              </Form>
            </div>
          )}
        </Card.Body>
      </Card>
    </Container>
  );
};

export default TwoFactorSetup;