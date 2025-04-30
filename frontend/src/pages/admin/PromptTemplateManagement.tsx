// Last reviewed: 2025-04-30 13:00:37 UTC (User: TeeksssPrompt)
import React, { useState } from 'react';
import { Container, Row, Col, Card, Table, Button, Badge, Modal, Form, Alert } from 'react-bootstrap';
import { FaPlus, FaEdit, FaTrash, FaStar, FaCheck, FaRegStar } from 'react-icons/fa';
import { useTranslation } from 'react-i18next';
import { formatDate } from '../../utils/formatters';
import ContentLoader from '../../components/common/ContentLoader';
import { 
  usePromptTemplates, 
  useCreatePromptTemplate, 
  useUpdatePromptTemplate,
  useDeletePromptTemplate,
  useSetDefaultPromptTemplate,
  CreatePromptTemplateInput,
  UpdatePromptTemplateInput,
  PromptTemplate
} from '../../services/promptTemplateService';
import { errorHandlingService } from '../../services/errorHandlingService';
import { analyticsService, EventCategory } from '../../services/analyticsService';

const PromptTemplateManagement: React.FC = () => {
  const { t } = useTranslation();
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create');
  const [currentTemplate, setCurrentTemplate] = useState<PromptTemplate | null>(null);
  const [formData, setFormData] = useState<CreatePromptTemplateInput>({
    name: '',
    description: '',
    systemPrompt: '',
    userPrompt: '',
    category: 'general',
    isDefault: false
  });
  
  // Prompt şablonlarını getir
  const { 
    data: templates = [], 
    isLoading, 
    error, 
    refetch 
  } = usePromptTemplates();
  
  // Mutations
  const { mutate: createTemplate, isLoading: isCreating } = useCreatePromptTemplate();
  const { mutate: updateTemplate, isLoading: isUpdating } = useUpdatePromptTemplate();
  const { mutate: deleteTemplate, isLoading: isDeleting } = useDeletePromptTemplate();
  const { mutate: setDefaultTemplate, isLoading: isSettingDefault } = useSetDefaultPromptTemplate();
  
  // Form submit handler
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      if (modalMode === 'create') {
        createTemplate(formData, {
          onSuccess: () => {
            setShowModal(false);
            resetForm();
            analyticsService.trackEvent({
              category: EventCategory.ADMIN,
              action: 'CreatePromptTemplate',
              label: formData.name
            });
          }
        });
      } else if (currentTemplate) {
        const updateData: UpdatePromptTemplateInput = {
          name: formData.name,
          description: formData.description,
          systemPrompt: formData.systemPrompt,
          userPrompt: formData.userPrompt,
          category: formData.category
        };
        
        updateTemplate({ id: currentTemplate.id, data: updateData }, {
          onSuccess: () => {
            setShowModal(false);
            resetForm();
            analyticsService.trackEvent({
              category: EventCategory.ADMIN,
              action: 'UpdatePromptTemplate',
              label: formData.name
            });
          }
        });
      }
    } catch (error) {
      errorHandlingService.handleError({
        message: modalMode === 'create' 
          ? 'Failed to create prompt template' 
          : 'Failed to update prompt template',
        details: error
      });
    }
  };
  
  // Delete prompt template
  const handleDelete = (template: PromptTemplate) => {
    if (window.confirm(t('admin.promptTemplates.confirmDelete', { name: template.name }))) {
      try {
        deleteTemplate(template.id, {
          onSuccess: () => {
            analyticsService.trackEvent({
              category: EventCategory.ADMIN,
              action: 'DeletePromptTemplate',
              label: template.name
            });
          }
        });
      } catch (error) {
        errorHandlingService.handleError({
          message: 'Failed to delete prompt template',
          details: error
        });
      }
    }
  };
  
  // Set default template
  const handleSetDefault = (template: PromptTemplate) => {
    try {
      setDefaultTemplate(template.id, {
        onSuccess: () => {
          analyticsService.trackEvent({
            category: EventCategory.ADMIN,
            action: 'SetDefaultPromptTemplate',
            label: template.name
          });
        }
      });
    } catch (error) {
      errorHandlingService.handleError({
        message: 'Failed to set default prompt template',
        details: error
      });
    }
  };
  
  // Edit template
  const handleEdit = (template: PromptTemplate) => {
    setCurrentTemplate(template);
    setFormData({
      name: template.name,
      description: template.description,
      systemPrompt: template.systemPrompt,
      userPrompt: template.userPrompt,
      category: template.category,
      isDefault: template.isDefault || false
    });
    setModalMode('edit');
    setShowModal(true);
  };
  
  // Reset form
  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      systemPrompt: '',
      userPrompt: '',
      category: 'general',
      isDefault: false
    });
    setCurrentTemplate(null);
  };
  
  // Form input change handler
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };
  
  // Form checkbox change handler
  const handleCheckboxChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: checked
    }));
  };
  
  return (
    <Container fluid>
      <Row className="mb-4 align-items-center">
        <Col>
          <h1 className="page-title">{t('admin.promptTemplates.title')}</h1>
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
            {t('admin.promptTemplates.create')}
          </Button>
        </Col>
      </Row>
      
      <Card>
        <ContentLoader
          isLoading={isLoading}
          error={error ? 'Failed to load prompt templates' : undefined}
          onRetry={refetch}
        >
          {templates.length === 0 ? (
            <Alert variant="info" className="m-3">
              {t('admin.promptTemplates.noTemplates')}
            </Alert>
          ) : (
            <Table responsive hover className="mb-0">
              <thead>
                <tr>
                  <th style={{ width: '1%' }}>{t('admin.promptTemplates.default')}</th>
                  <th>{t('admin.promptTemplates.name')}</th>
                  <th>{t('admin.promptTemplates.category')}</th>
                  <th>{t('admin.promptTemplates.description')}</th>
                  <th>{t('admin.promptTemplates.variables')}</th>
                  <th>{t('admin.promptTemplates.createdAt')}</th>
                  <th style={{ width: '1%' }}>{t('common.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {templates.map(template => (
                  <tr key={template.id}>
                    <td className="text-center">
                      {template.isDefault ? (
                        <FaStar className="text-warning" title={t('admin.promptTemplates.isDefault')} />
                      ) : (
                        <Button
                          variant="link"
                          className="p-0"
                          onClick={() => handleSetDefault(template)}
                          disabled={isSettingDefault}
                          title={t('admin.promptTemplates.setDefault')}
                        >
                          <FaRegStar className="text-muted" />
                        </Button>
                      )}
                    </td>
                    <td>{template.name}</td>
                    <td>
                      <Badge bg="info">{template.category}</Badge>
                    </td>
                    <td>{template.description}</td>
                    <td>
                      {template.variables.map(variable => (
                        <Badge key={variable} bg="secondary" className="me-1">
                          {variable}
                        </Badge>
                      ))}
                    </td>
                    <td>{formatDate(template.createdAt)}</td>
                    <td>
                      <div className="d-flex">
                        <Button
                          variant="link"
                          className="p-0 me-2"
                          onClick={() => handleEdit(template)}
                          disabled={isUpdating}
                        >
                          <FaEdit />
                        </Button>
                        <Button
                          variant="link"
                          className="p-0 text-danger"
                          onClick={() => handleDelete(template)}
                          disabled={isDeleting || template.isDefault}
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
        <Form onSubmit={handleSubmit}>
          <Modal.Header closeButton>
            <Modal.Title>
              {modalMode === 'create' 
                ? t('admin.promptTemplates.createTitle')
                : t('admin.promptTemplates.editTitle', { name: currentTemplate?.name })}
            </Modal.Title>
          </Modal.Header>
          <Modal.Body>
            <Form.Group className="mb-3">
              <Form.Label>{t('admin.promptTemplates.name')}</Form.Label>
              <Form.Control 
                type="text" 
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                required
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>{t('admin.promptTemplates.description')}</Form.Label>
              <Form.Control 
                as="textarea" 
                rows={2}
                name="description"
                value={formData.description}
                onChange={handleInputChange}
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>{t('admin.promptTemplates.category')}</Form.Label>
              <Form.Select
                name="category"
                value={formData.category}
                onChange={handleInputChange}
              >
                <option value="general">General</option>
                <option value="qa">Question Answering</option>
                <option value="summarization">Summarization</option>
                <option value="classification">Classification</option>
                <option value="extraction">Information Extraction</option>
                <option value="custom">Custom</option>
              </Form.Select>
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>{t('admin.promptTemplates.systemPrompt')}</Form.Label>
              <Form.Control 
                as="textarea" 
                rows={5}
                name="systemPrompt"
                value={formData.systemPrompt}
                onChange={handleInputChange}
                required
                placeholder="Instructions for the AI model..."
              />
              <Form.Text className="text-muted">
                {t('admin.promptTemplates.systemPromptHelp')}
              </Form.Text>
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>{t('admin.promptTemplates.userPrompt')}</Form.Label>
              <Form.Control 
                as="textarea" 
                rows={5}
                name="userPrompt"
                value={formData.userPrompt}
                onChange={handleInputChange}
                required
                placeholder="Template for user queries, e.g. 'Answer this question: {{question}}'"
              />
              <Form.Text className="text-muted">
                {t('admin.promptTemplates.userPromptHelp')}
              </Form.Text>
            </Form.Group>
            
            {modalMode === 'create' && (
              <Form.Group className="mb-3">
                <Form.Check
                  type="checkbox"
                  id="isDefault"
                  name="isDefault"
                  label={t('admin.promptTemplates.isDefault')}
                  checked={formData.isDefault}
                  onChange={handleCheckboxChange}
                />
              </Form.Group>
            )}
          </Modal.Body>
          <Modal.Footer>
            <Button
              variant="secondary"
              onClick={() => setShowModal(false)}
            >
              {t('common.cancel')}
            </Button>
            <Button
              variant="primary"
              type="submit"
              disabled={isCreating || isUpdating}
            >
              {isCreating || isUpdating ? (
                <>
                  <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                  {t('common.saving')}
                </>
              ) : (
                <>
                  <FaCheck className="me-2" />
                  {t('common.save')}
                </>
              )}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>
    </Container>
  );
};

export default PromptTemplateManagement;