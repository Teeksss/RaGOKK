// Last reviewed: 2025-04-30 07:48:16 UTC (User: Teeksss)
import React, { useState, useEffect } from 'react';
import { Container, Card, Button, Form, Alert, Spinner } from 'react-bootstrap';
import { FaKey, FaLock, FaArrowLeft } from 'react-icons/fa';
import { useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import API from '../../api/api';

interface LocationState {
  user_id?: string;
  email?: string;
  from?: string;
}

const TwoFactorAuth: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();
  
  // Location state'den kullanıcı bilgilerini al
  const state = location.state as LocationState;
  const userId = state?.user_id;
  const email = state?.email;
  const redirectPath = state?.from || '/';
  
  // State
  const [verificationCode, setVerificationCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Kullanıcı bilgisi yoksa login sayfasına yönlendir
  useEffect(() => {
    if (!userId && !email) {
      navigate('/login');
    }
  }, [userId, email, navigate]);
  
  // Doğrulama
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!verificationCode || verificationCode.length !== 6) {
      setError(t('auth.2fa.invalidCode'));
      return;
    }
    
    setIsLoading(true);
    setError('');
    
    try {
      const response = await API.post('/auth/2fa/login-verify', {
        code: verificationCode
      });
      
      // Token bilgilerini kaydet
      if (response.data.access_token && login) {
        await login(response.data.access_token);
        
        // Yönlendir
        navigate(redirectPath);
      } else {
        setError(t('auth.2fa.loginFailed'));
      }
    } catch (err: any) {
      console.error('Error verifying 2FA code:', err);
      setError(err?.response?.data?.detail || t('auth.2fa.verifyError'));
    } finally {
      setIsLoading(false);
    }
  };
  
  return (
    <Container className="py-5">
      <Card className="mx-auto" style={{ maxWidth: '400px' }}>
        <Card.Header className="bg-primary text-white">
          <h4 className="mb-0">
            <FaKey className="me-2" />
            {t('auth.2fa.verification')}
          </h4>
        </Card.Header>
        
        <Card.Body>
          {error && (
            <Alert variant="danger" className="mb-4">
              {error}
            </Alert>
          )}
          
          <p>
            {t('auth.2fa.enterVerificationCode')}{' '}
            {email && <strong>{email}</strong>}
          </p>
          
          <Form onSubmit={handleSubmit}>
            <Form.Group className="mb-4">
              <div className="d-flex align-items-center">
                <FaLock className="me-2 text-muted" />
                <Form.Control
                  type="text"
                  placeholder="000000"
                  value={verificationCode}
                  onChange={(e) => setVerificationCode(e.target.value)}
                  maxLength={6}
                  required
                  autoComplete="one-time-code"
                />
              </div>
              <Form.Text className="text-muted">
                {t('auth.2fa.codeFromApp')}
              </Form.Text>
            </Form.Group>
            
            <div className="d-grid gap-2">
              <Button 
                type="submit" 
                variant="primary" 
                disabled={isLoading || !verificationCode || verificationCode.length !== 6}
              >
                {isLoading ? (
                  <>
                    <Spinner animation="border" size="sm" className="me-2" />
                    {t('common.verifying')}
                  </>
                ) : (
                  t('auth.2fa.verify')
                )}
              </Button>
              
              <Button 
                variant="outline-secondary" 
                onClick={() => navigate('/login')}
                disabled={isLoading}
              >
                <FaArrowLeft className="me-2" />
                {t('auth.backToLogin')}
              </Button>
            </div>
          </Form>
        </Card.Body>
      </Card>
    </Container>
  );
};

export default TwoFactorAuth;