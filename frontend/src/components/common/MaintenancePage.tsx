// Last reviewed: 2025-04-30 08:31:26 UTC (User: Teeksss)
import React from 'react';
import { Container, Row, Col, Card, Button } from 'react-bootstrap';
import { FaTools, FaClock, FaExclamationTriangle } from 'react-icons/fa';
import { useTranslation } from 'react-i18next';

const MaintenancePage: React.FC = () => {
  const { t } = useTranslation();
  
  return (
    <div className="maintenance-page">
      <Container className="py-5">
        <Row className="justify-content-center mt-5">
          <Col md={8} lg={6}>
            <Card className="text-center shadow-lg">
              <Card.Body className="p-5">
                <div className="maintenance-icon mb-4">
                  <FaTools size={60} className="text-primary" />
                </div>
                
                <h1>{t('common.maintenance.title')}</h1>
                
                <p className="lead mb-4">
                  {t('common.maintenance.message')}
                </p>
                
                <div className="d-flex align-items-center justify-content-center mb-4">
                  <FaClock className="text-warning me-2" />
                  <span>{t('common.maintenance.estimatedTime')}</span>
                </div>
                
                <div className="alert alert-info" role="alert">
                  <FaExclamationTriangle className="me-2" />
                  {t('common.maintenance.adminMessage')}
                </div>
                
                <div className="mt-4">
                  <Button
                    variant="outline-primary"
                    onClick={() => window.location.reload()}
                  >
                    {t('common.maintenance.refresh')}
                  </Button>
                </div>
              </Card.Body>
              
              <Card.Footer className="text-muted">
                <small>RAG Base © 2025</small>
              </Card.Footer>
            </Card>
          </Col>
        </Row>
      </Container>
    </div>
  );
};

export default MaintenancePage;