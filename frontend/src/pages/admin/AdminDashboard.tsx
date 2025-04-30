// Last reviewed: 2025-04-30 13:00:37 UTC (User: TeeksssPrompt)
// ... mevcut importlar ...

const AdminDashboard: React.FC = () => {
  // ... mevcut kodlar ...
  
  return (
    <Container fluid>
      <h1 className="page-title mb-4">{t('admin.dashboard.title')}</h1>
      
      <Row>
        <Col md={6} lg={3} className="mb-4">
          <Card as={Link} to="/admin/users" className="admin-card h-100 text-decoration-none">
            <Card.Body className="d-flex flex-column align-items-center p-4">
              <div className="icon-wrapper bg-primary mb-3">
                <FaUsers size={24} />
              </div>
              <h3 className="text-center">{t('admin.dashboard.users')}</h3>
              <p className="text-center text-muted mb-0">{t('admin.dashboard.usersDescription')}</p>
            </Card.Body>
          </Card>
        </Col>
        
        <Col md={6} lg={3} className="mb-4">
          <Card as={Link} to="/admin/organizations" className="admin-card h-100 text-decoration-none">
            <Card.Body className="d-flex flex-column align-items-center p-4">
              <div className="icon-wrapper bg-success mb-3">
                <FaBuilding size={24} />
              </div>
              <h3 className="text-center">{t('admin.dashboard.organizations')}</h3>
              <p className="text-center text-muted mb-0">{t('admin.dashboard.organizationsDescription')}</p>
            </Card.Body>
          </Card>
        </Col>
        
        {/* Yeni Prompt Template Kartı */}
        <Col md={6} lg={3} className="mb-4">
          <Card as={Link} to="/admin/prompt-templates" className="admin-card h-100 text-decoration-none">
            <Card.Body className="d-flex flex-column align-items-center p-4">
              <div className="icon-wrapper bg-info mb-3">
                <FaPen size={24} />
              </div>
              <h3 className="text-center">{t('admin.dashboard.promptTemplates')}</h3>
              <p className="text-center text-muted mb-0">{t('admin.dashboard.promptTemplatesDescription')}</p>
            </Card.Body>
          </Card>
        </Col>
        
        {/* Yeni Retrieval Strategy Kartı */}
        <Col md={6} lg={3} className="mb-4">
          <Card as={Link} to="/admin/retrieval-strategies" className="admin-card h-100 text-decoration-none">
            <Card.Body className="d-flex flex-column align-items-center p-4">
              <div className="icon-wrapper bg-warning mb-3">
                <FaSearch size={24} />
              </div>
              <h3 className="text-center">{t('admin.dashboard.retrievalStrategies')}</h3>
              <p className="text-center text-muted mb-0">{t('admin.dashboard.retrievalStrategiesDescription')}</p>
            </Card.Body>
          </Card>
        </Col>
        
        {/* ... mevcut kartlar ... */}
      </Row>
      
      {/* ... mevcut içerik ... */}
    </Container>
  );
};