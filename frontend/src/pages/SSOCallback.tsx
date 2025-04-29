// Last reviewed: 2025-04-29 13:23:09 UTC (User: TeeksssSSO)
import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation, Navigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';
import { Container, Alert, Spinner } from 'react-bootstrap';
import { useToast } from '../contexts/ToastContext';

/**
 * SSO oturum açma işlemi sonrası yönlendirilen callback sayfası
 * URL'deki token bilgilerini alıp kullanıcıyı giriş yaparak yönlendirir
 */
const SSOCallback: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, loginWithTokens } = useAuth();
  const { showToast } = useToast();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const processCallback = async () => {
      try {
        // URL parametrelerini analiz et
        const params = new URLSearchParams(location.search);
        const accessToken = params.get('access_token');
        const refreshToken = params.get('refresh_token');
        const provider = params.get('provider');
        
        if (!accessToken || !refreshToken) {
          throw new Error('Missing authentication tokens');
        }
        
        // Token bilgileriyle giriş yap
        await loginWithTokens(accessToken, refreshToken);
        
        // Başarılı giriş mesajı
        showToast(
          t('auth.ssoLoginSuccess', {
            provider: provider?.charAt(0).toUpperCase() + provider?.slice(1) || 'SSO'
          }),
          'success'
        );
        
        // Kullanıcıyı yönlendir
        const returnUrl = localStorage.getItem('returnUrl') || '/dashboard';
        localStorage.removeItem('returnUrl'); // Temizle
        navigate(returnUrl);
      } catch (err) {
        console.error('SSO callback error:', err);
        setError(err instanceof Error ? err.message : 'Authentication failed');
        showToast(t('auth.ssoLoginError'), 'error');
      } finally {
        setLoading(false);
      }
    };

    processCallback();
  }, [location.search, loginWithTokens, navigate, showToast, t]);

  if (isAuthenticated) {
    // Zaten giriş yapılmışsa yönlendir
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <Container className="d-flex flex-column justify-content-center align-items-center py-5" style={{ minHeight: '70vh' }}>
      {loading ? (
        <div className="text-center">
          <Spinner animation="border" variant="primary" className="mb-3" />
          <p>{t('auth.authenticating')}</p>
        </div>
      ) : error ? (
        <Alert variant="danger" className="text-center">
          <h4>{t('auth.ssoError')}</h4>
          <p>{error}</p>
          <button 
            className="btn btn-outline-danger mt-3"
            onClick={() => navigate('/login')}
          >
            {t('auth.backToLogin')}
          </button>
        </Alert>
      ) : null}
    </Container>
  );
};

export default SSOCallback;