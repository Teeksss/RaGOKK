// Last reviewed: 2025-04-30 08:34:14 UTC (User: Teeksss)
import React from 'react';
import { Container, Row, Col, Button, Card } from 'react-bootstrap';
import { FaLock, FaHome, FaArrowLeft } from 'react-icons/fa';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';

const UnauthorizedPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user } = useAuth();
  
  return (
    <Container className="py-5">
      <Row className="justify-content-center">
        <Col md={8} lg={6}>
          <Card className="shadow border-0">
            <Card.Body className="text-center p-5">
              <div className="unauthorized-icon mb-4">
                <FaLock className="text-danger" size={60} />
              </div>
              
              <h2 className="mt-4">{t('common.unauthorized')}</h2>
              <p className="text-muted mb-4">
                {t('common.noPermissionToAccess')}
              </p>
              
              {user && (
                <div className="user-info mb-4 p-3 bg-light rounded">
                  <h6>{t('common.yourAccess')}:</h6>
                  <p className="mb-1">
                    <strong>{t('common.roles')}:</strong> {user.roles.join(', ')}
                  </p>
                  {user.permissions && user.permissions.length > 0 && (
                    <p className="mb-0">
                      <strong>{t('common.permissions')}:</strong> {user.permissions.join(', ')}
                    </p>
                  )}
                </div>
              )}
              
              <div className="d-flex justify-content-center gap-3">
                <Button
                  variant="primary"
                  onClick={() => navigate('/')}
                >
                  <FaHome className="me-2" />
                  {t('common.backToHome')}
                </Button>
                
                <Button
                  variant="outline-secondary"
                  onClick={() => navigate(-1)}
                >
                  <FaArrowLeft className="me-2" />
                  {t('common.goBack')}
                </Button>
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default UnauthorizedPage;