// Last reviewed: 2025-04-30 08:16:40 UTC (User: Teeksss)
import React from 'react';
import { Container, Row, Col, Card } from 'react-bootstrap';
import MonitoringDashboard from '../../components/admin/MonitoringDashboard';
import { useTranslation } from 'react-i18next';

const SystemMonitoring: React.FC = () => {
  const { t } = useTranslation();
  
  return (
    <Container fluid>
      <h1 className="mb-4">{t('admin.systemMonitoring.title')}</h1>
      
      <Row>
        <Col>
          <Card className="mb-4">
            <Card.Body>
              <MonitoringDashboard />
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default SystemMonitoring;