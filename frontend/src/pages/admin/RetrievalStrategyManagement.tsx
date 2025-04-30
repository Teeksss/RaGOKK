// Last reviewed: 2025-04-30 13:00:37 UTC (User: TeeksssPrompt)
import React, { useState } from 'react';
import { Container, Row, Col, Card, Table, Button, Badge, Modal, Alert } from 'react-bootstrap';
import { FaPlus, FaEdit, FaTrash, FaStar, FaRegStar, FaCheck, FaCog } from 'react-icons/fa';
import { useTranslation } from 'react-i18next';
import ContentLoader from '../../components/common/ContentLoader';
import { formatDate } from '../../utils/formatters';
import { 
  useRetrievalStrategies, 
  useCreateRetrievalStrategy, 
  useUpdateRetrievalStrategy, 
  useDeleteRetrievalStrategy, 
  useSetDefaultRetrievalStrategy,
  CreateRetrievalStrategyInput,
  UpdateRetrievalStrategyInput,
  RetrievalStrategy,
  RetrievalConfig,
  DEFAULT_RETRIEVAL_CONFIG 
} from '../../services/retrievalStrategyService';
import { errorHandlingService } from '../../services/errorHandlingService';
import { analyticsService, EventCategory } from '../../services/analyticsService';
import RetrievalConfigEditor from '../../components/admin/RetrievalConfigEditor';

const RetrievalStrategyManagement: React.FC = () => {
  const { t } = useTranslation();
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create');
  const [currentStrategy, setCurrentStrategy] = useState<RetrievalStrategy | null>(null);
  const [formData, setFormData] = useState<CreateRetrievalStrategyInput>({
    name: '',
    description: '',
    configuration: DEFAULT_RETRIEVAL_CONFIG,
    isDefault: false
  });
  
  // Retrieval stratejilerini getir
  const { 
    data: strategies = [], 
    isLoading, 
    error, 
    refetch 
  } = useRetrievalStrategies();
  
  // Mutations
  const { mutate: createStrategy, isLoading: isCreating } = useCreateRetrievalStrategy();
  const { mutate: updateStrategy, isLoading: isUpdating } = useUpdateRetrievalStrategy();
  const { mutate: deleteStrategy, isLoading: isDeleting } = useDeleteRetrievalStrategy();
  const { mutate: setDefaultStrategy, isLoading: isSettingDefault } = useSetDefaultRetrievalStrategy();
  
  // Create strategy
  const handleCreate = (name: string, description: string, config: RetrievalConfig) => {
    try {
      createStrategy({
        name,
        description,
        configuration: config
      }, {
        onSuccess: () => {
          setShowModal(false);
          resetForm();
          analyticsService.trackEvent({
            category: EventCategory.ADMIN,
            action: 'CreateRetrievalStrategy',
            label: name
          });
        }
      });
    } catch (error) {
      errorHandlingService.handleError({
        message: 'Failed to create retrieval strategy',
        details: error
      });
    }
  };
  
  // Update strategy
  const handleUpdate = (id: string, name: string, description: string, config: RetrievalConfig) => {
    try {
      updateStrategy({
        id,
        data: {
          name,
          description,
          configuration: config
        }
      }, {
        onSuccess: () => {
          setShowModal(false);
          resetForm();
          analyticsService.trackEvent({
            category: EventCategory.ADMIN,
            action: 'UpdateRetrievalStrategy',
            label: name
          });
        }
      });
    } catch (error) {
      errorHandlingService.handleError({
        message: 'Failed to update retrieval strategy',
        details: error
      });
    }
  };
  
  // Delete strategy
  const handleDelete = (strategy: RetrievalStrategy) => {
    if (window.confirm(t('admin.retrievalStrategies.confirmDelete', { name: strategy.name }))) {
      try {
        deleteStrategy(strategy.id, {
          onSuccess: () => {
            analyticsService.trackEvent({
              category: EventCategory.ADMIN,
              action: 'DeleteRetrievalStrategy',
              label: strategy.name
            });
          }
        });
      } catch (error) {
        errorHandlingService.handleError({
          message: 'Failed to delete retrieval strategy',
          details: error
        });
      }
    }
  };
  
  // Set default strategy
  const handleSetDefault = (strategy: RetrievalStrategy) => {
    try {
      setDefaultStrategy(strategy.id, {
        onSuccess: () => {
          analyticsService.trackEvent({
            category: EventCategory.ADMIN,
            action: 'SetDefaultRetrievalStrategy',
            label: strategy.name
          });
        }
      });
    } catch (error) {
      errorHandlingService.handleError({
        message: 'Failed to set default retrieval strategy',
        details: error
      });
    }
  };
  
  // Edit strategy
  const handleEdit = (strategy: RetrievalStrategy) => {
    setCurrentStrategy(strategy);
    setFormData({
      name: strategy.name,
      description: strategy.description,
      configuration: strategy.configuration,
      isDefault: strategy.isDefault || false
    });
    setModalMode('edit');
    setShowModal(true);
  };
  
  // Reset form
  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      configuration: DEFAULT_RETRIEVAL_CONFIG,
      isDefault: false
    });
    setCurrentStrategy(null);
  };
  
  // Handle config save
  const handleConfigSave = (config: RetrievalConfig) => {
    if (modalMode === 'create') {
      handleCreate(formData.name, formData.description, config);
    } else if (currentStrategy) {
      handleUpdate(currentStrategy.id, formData.name, formData.description, config);
    }
  };
  
  // Form input change handler
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };
  
  return (
    <Container fluid>
      <Row className="mb-4 align-items-center">
        <Col>
          <h1 className="page-title">{t('admin.retrievalStrategies.title')}</h1>
        </Col>
        <Col xs="auto">
          <Button 
            variant="primary" 
            onClick={() => {
              resetForm();
              setModalMode('create');
              setShowModal(true);
            }}
            disabled={isCreating || isUpdating || isDeleting || isSettingDefault}
          >
            <FaPlus className="me-2" />
            {t('admin.retrievalStrategies.create')}
          </Button>
        </Col>
      </Row>
      
      <Card>
        <ContentLoader
          isLoading={isLoading}
          error={error ? 'Failed to load retrieval strategies' : undefined}
          onRetry={refetch}
        >
          {strategies.length === 0 ? (
            <Alert variant="info" className="m-3">
              {t('admin.retrievalStrategies.noStrategies')}
            </Alert>
          ) : (
            <Table responsive hover className="mb-0">
              <thead>
                <tr>
                  <th style={{ width: '1%' }}>{t('admin.retrievalStrategies.default')}</th>
                  <th>{t('admin.retrievalStrategies.name')}</th>
                  <th>{t('admin.retrievalStrategies.description')}</th>
                  <th>{t('admin.retrievalStrategies.config')}</th>
                  <th>{t('admin.retrievalStrategies.createdAt')}</th>
                  <th style={{ width: '1%' }}>{t('common.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {strategies.map(strategy => (
                  <tr key={strategy.id}>
                    <td className="text-center">
                      {strategy.isDefault ? (
                        <FaStar className="text-warning" title={t('admin.retrievalStrategies.isDefault')} />
                      ) : (
                        <Button
                          variant="link"
                          className="p-0"
                          onClick={() => handleSetDefault(strategy)}
                          disabled={isSettingDefault}
                          title={t('admin.retrievalStrategies.setDefault')}
                        >
                          <FaRegStar className="text-muted" />
                        </Button>
                      )}
                    </td>
                    <td>{strategy.name}</td>
                    <td>{strategy.description}</td>
                    <td>
                      <div className="d-flex flex-wrap gap-1">
                        <Badge bg="primary" title={`Top K: ${strategy.configuration.top_k}`}>
                          K={strategy.configuration.top_k}
                        </Badge>
                        <Badge bg="secondary" title={`Min Score: ${strategy.configuration.min_score}`}>
                          S≥{strategy.configuration.min_score}
                        </Badge>
                        {strategy.configuration.use_reranker && (
                          <Badge bg="success" title="Uses reranker">
                            Reranker
                          </Badge>
                        )}
                        {strategy.configuration.query_expansion_method !== 'none' && (
                          <Badge bg="info" title={`Query expansion: ${strategy.configuration.query_expansion_method}`}>
                            Expansion
                          </Badge>
                        )}
                        {strategy.configuration.multi_query_variants && (
                          <Badge bg="warning" title={`Multi-query: ${strategy.configuration.multi_query_count} variants`}>
                            Multi-query
                          </Badge>
                        )}
                      </div>
                    </td>
                    <td>{formatDate(strategy.createdAt)}</td>
                    <td>
                      <div className="d-flex">
                        <Button
                          variant="link"
                          className="p-0 me-2"
                          onClick={() => handleEdit(strategy)}
                          disabled={isUpdating}
                        >
                          <FaEdit />
                        </Button>
                        <Button
                          variant="link"
                          className="p-0 text-danger"
                          onClick={() => handleDelete(strategy)}
                          disabled={isDeleting || strategy.isDefault}
                        >
                          <FaTrash />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </ContentLoader>
      </Card>
      
      {/* Create/Edit Modal */}
      <Modal
        show={showModal}
        onHide={() => setShowModal(false)}
        backdrop="static"
        size="lg"
      >
        <Modal.Header closeButton>
          <Modal.Title className="d-flex align-items-center">
            <FaCog className="me-2" />
            {modalMode === 'create' 
              ? t('admin.retrievalStrategies.createTitle')
              : t('admin.retrievalStrategies.editTitle', { name: currentStrategy?.name })}
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <div className="mb-4">
            <div className="mb-3">
              <label htmlFor="name" className="form-label">
                {t('admin.retrievalStrategies.name')}
              </label>
              <input
                type="text"
                className="form-control"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                required
              />
            </div>
            
            <div className="mb-3">
              <label htmlFor="description" className="form-label">
                {t('admin.retrievalStrategies.description')}
              </label>
              <textarea
                className="form-control"
                id="description"
                name="description"
                rows={2}
                value={formData.description}
                onChange={handleInputChange}
              />
            </div>
          </div>
          
          <hr className="mb-4" />
          
          <h5 className="mb-3">{t('admin.retrievalStrategies.configEditor')}</h5>
          <RetrievalConfigEditor
            initialConfig={formData.configuration}
            onSave={handleConfigSave}
            isLoading={isCreating || isUpdating}
            isAdmin={true}
          />
        </Modal.Body>
      </Modal>
    </Container>
  );
};

export default RetrievalStrategyManagement;