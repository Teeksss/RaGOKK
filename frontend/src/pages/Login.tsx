// Last reviewed: 2025-04-29 14:12:11 UTC (User: TeeksssKullanıcı)
import React, { useState, useEffect } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { Form, Button, Card, Alert, Container, Row, Col, Spinner } from 'react-bootstrap';
import { useAuth } from '../contexts/AuthContext';
import { useTranslation } from 'react-i18next';
import { FaGoogle, FaMicrosoft, FaGithub } from 'react-icons/fa';
import LanguageSelector from '../components/LanguageSelector';
import { motion } from 'framer-motion';
import API from '../api/api';

const Login: React.FC = () => {
  const { t } = useTranslation();
  const { login, loginWithTokens, isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [ssoProviders, setSsoProviders] = useState<Array<any>>([]);
  const [loadingSso, setLoadingSso] = useState(true);
  
  // Yönlendirme URL'si (giriş sonrası)
  const returnUrl = new URLSearchParams(location.search).get('returnUrl') || '/dashboard';
  
  // Eğer kullanıcı zaten oturum açmışsa, dashboard'a yönlendir
  useEffect(() => {
    if (isAuthenticated) {
      navigate(returnUrl);
    }
  }, [isAuthenticated, navigate, returnUrl]);
  
  // SSO sağlayıcıları getir
  useEffect(() => {
    const fetchSsoProviders = async () => {
      try {
        const response = await API.get('/auth/sso/providers');
        setSsoProviders(Object.values(response.data.providers || {}));
      } catch (error) {
        console.error('Error fetching SSO providers:', error);
      } finally {
        setLoadingSso(false);
      }
    };
    
    fetchSsoProviders();
  }, []);
  
  // Yükleniyor durumu
  if (isLoading) {
    return (
      <Container className="d-flex justify-content-center align-items-center" style={{ height: '100vh' }}>
        <Spinner animation="border" />
      </Container>
    );
  }
  
  // Form gönderimi
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!email.trim() || !password.trim()) {
      setError(t('auth.errors.fillAllFields'));
      return;
    }
    
    try {
      setError(null);
      setSubmitting(true);
      
      const success = await login(email, password);
      
      if (success) {
        // Local storage returnUrl varsa kullan ve temizle
        const storedReturnUrl = localStorage.getItem('returnUrl');
        localStorage.removeItem('returnUrl');
        
        navigate(storedReturnUrl || returnUrl);
      } else {
        // login fonksiyonu hata mesajını gösterdi
      }
    } catch (error) {
      setError(t('auth.errors.generic'));
      console.error('Login error:', error);
    } finally {
      setSubmitting(false);
    }
  };
  
  // SSO ile giriş
  const handleSsoLogin = (provider: string) => {
    // returnUrl'i localStorage'a kaydet (SSO callback sonrası kullanmak için)
    localStorage.setItem('returnUrl', returnUrl);
    
    // SSO sağlayıcısına yönlendir
    window.location.href = `/api/auth/sso/${provider}`;
  };
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <Container className="py-5">
        <Row className="justify-content-center">
          <Col md={6} lg={5} xl={4}>
            <div className="text-end mb-3">
              <LanguageSelector variant="dropdown" size="sm" />
            </div>
            
            <Card className="shadow">
              <Card.Body className="p-4">
                <div className="text-center mb-4">
                  <img 
                    src="/logo.svg" 
                    alt="RAG Base Logo" 
                    className="mb-3" 
                    style={{ height: '60px' }} 
                  />
                  <h2 className="h4 mb-0">{t('auth.loginTitle')}</h2>
                  <p className="text-muted small">{t('auth.loginSubtitle')}</p>
                </div>
                
                {error && (
                  <Alert variant="danger" className="mb-4">
                    {error}
                  </Alert>
                )}
                
                <Form onSubmit={handleSubmit}>
                  <Form.Group className="mb-3" controlId="formEmail">
                    <Form.Label>{t('auth.emailOrUsername')}</Form.Label>
                    <Form.Control
                      type="text"
                      placeholder={t('auth.emailOrUsernamePlaceholder')}
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                    />
                  </Form.Group>
                  
                  <Form.Group className="mb-4" controlId="formPassword">
                    <div className="d-flex justify-content-between align-items-center mb-1">
                      <Form.Label className="mb-0">{t('auth.password')}</Form.Label>
                      <Link to="/forgot-password" className="small">
                        {t('auth.forgotPassword')}
                      </Link>
                    </div>
                    <Form.Control
                      type="password"
                      placeholder={t('auth.passwordPlaceholder')}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                    />
                  </Form.Group>
                  
                  <Button
                    variant="primary"
                    type="submit"
                    className="w-100 mb-3"
                    disabled={submitting}
                  >
                    {submitting ? (
                      <>
                        <Spinner
                          as="span"
                          animation="border"
                          size="sm"
                          role="status"
                          aria-hidden="true"
                          className="me-2"
                        />
                        {t('auth.loggingIn')}
                      </>
                    ) : (
                      t('auth.login')
                    )}
                  </Button>
                </Form>
                
                {/* SSO ile giriş seçenekleri */}
                {ssoProviders.length > 0 && (
                  <div className="mt-4">
                    <div className="text-center mb-3">
                      <span className="text-muted small">{t('auth.continueWith')}</span>
                    </div>
                    
                    <div className="d-flex justify-content-center gap-2">
                      {ssoProviders.map((provider: any) => (
                        <Button
                          key={provider.provider_type}
                          variant="outline-secondary"
                          className="d-flex align-items-center justify-content-center"
                          onClick={() => handleSsoLogin(provider.provider_type)}
                          style={{ width: '50px', height: '50px', padding: 0 }}
                        >
                          {provider.provider_type === 'google' && <FaGoogle size={24} />}
                          {provider.provider_type === 'microsoft' && <FaMicrosoft size={24} />}
                          {provider.provider_type === 'github' && <FaGithub size={24} />}
                          {provider.provider_type !== 'google' && 
                           provider.provider_type !== 'microsoft' && 
                           provider.provider_type !== 'github' && provider.name?.charAt(0)}
                        </Button>
                      ))}
                    </div>
                  </div>
                )}
                
                <div className="mt-4 text-center">
                  <p className="mb-0 small">
                    {t('auth.noAccount')}{' '}
                    <Link to="/register" className="fw-medium">
                      {t('auth.register')}
                    </Link>
                  </p>
                </div>
              </Card.Body>
            </Card>
            
            <div className="text-center mt-4 small text-muted">
              <p>
                &copy; {new Date().getFullYear()} RAG Base.{' '}
                <Link to="/terms" className="text-muted">
                  {t('footer.terms')}
                </Link>{' '}
                &bull;{' '}
                <Link to="/privacy" className="text-muted">
                  {t('footer.privacy')}
                </Link>
              </p>
            </div>
          </Col>
        </Row>
      </Container>
    </motion.div>
  );
};

export default Login;