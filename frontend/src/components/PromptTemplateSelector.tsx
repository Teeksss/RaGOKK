// Last reviewed: 2025-04-29 14:31:59 UTC (User: Teeksss)
import React, { useState, useEffect } from 'react';
import { Form, Spinner, Button, Modal, ListGroup, Badge } from 'react-bootstrap';
import { useTranslation } from 'react-i18next';
import { FaInfoCircle, FaPlusCircle, FaSearch } from 'react-icons/fa';
import API from '../api/api';
import { useToast } from '../contexts/ToastContext';

// Tipler
interface PromptTemplate {
  id: string;
  name: string;
  description: string;
  template: string;
  is_system: boolean;
  created_at: string;
  updated_at: string;
}

interface PromptTemplateListResponse {
  items: PromptTemplate[];
  total: number;
  page: number;
  page_size: number;
}

interface PromptTemplateSelectorProps {
  selectedTemplateId: string | null;
  onChange: (templateId: string | null) => void;
  showCreateButton?: boolean;
  onCreateTemplate?: () => void;
}

const PromptTemplateSelector: React.FC<PromptTemplateSelectorProps> = ({
  selectedTemplateId,
  onChange,
  showCreateButton = false,
  onCreateTemplate
}) => {
  const { t } = useTranslation();
  const { showToast } = useToast();
  
  // State
  const [templates, setTemplates] = useState<PromptTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showDetails, setShowDetails] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<PromptTemplate | null>(null);
  const [showBrowser, setShowBrowser] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredTemplates, setFilteredTemplates] = useState<PromptTemplate[]>([]);
  
  // Şablonları yükle
  useEffect(() => {
    const loadTemplates = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const response = await API.get<PromptTemplateListResponse>('/prompts');
        
        if (response.data && response.data.items) {
          setTemplates(response.data.items);
          setFilteredTemplates(response.data.items);
        } else {
          setTemplates([]);
          setFilteredTemplates([]);
        }
      } catch (err: any) {
        console.error('Error loading prompt templates:', err);
        setError(err.response?.data?.detail || t('prompts.loadError'));
      } finally {
        setLoading(false);
      }
    };
    
    loadTemplates();
  }, [t]);
  
  // Şablonu ID'ye göre getir
  const getTemplateById = (id: string): PromptTemplate | undefined => {
    return templates.find(template => template.id === id);
  };
  
  // Detayları göster/gizle
  const toggleDetails = (template?: PromptTemplate | null) => {
    if (template) {
      setSelectedTemplate(template);
      setShowDetails(true);
    } else {
      setShowDetails(false);
    }
  };
  
  // Şablon seçimi değiştiğinde
  const handleTemplateChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    onChange(value || null);
  };
  
  // Şablon tarama için arama işlevi
  const handleSearch = () => {
    if (!searchQuery.trim()) {
      setFilteredTemplates(templates);
      return;
    }
    
    const query = searchQuery.toLowerCase();
    const filtered = templates.filter(template => 
      template.name.toLowerCase().includes(query) || 
      template.description.toLowerCase().includes(query)
    );
    
    setFilteredTemplates(filtered);
  };
  
  // Şablon tarama modalında şablon seçimi
  const handleSelectTemplateFromBrowser = (template: PromptTemplate) => {
    onChange(template.id);
    setShowBrowser(false);
  };
  
  // Seçili şablonun adını göster
  const getSelectedTemplateName = (): string => {
    if (!selectedTemplateId) return t('prompts.defaultTemplate');
    
    const template = getTemplateById(selectedTemplateId);
    return template ? template.name : t('prompts.unknownTemplate');
  };
  
  return (
    <div className="prompt-template-selector">
      <div className="d-flex">
        <div className="flex-grow-1 me-2">
          {loading ? (
            <div className="text-center py-2">
              <Spinner animation="border" size="sm" />
            </div>
          ) : (
            <Form.Select
              value={selectedTemplateId || ''}
              onChange={handleTemplateChange}
              disabled={loading}
            >
              <option value="">{t('prompts.defaultTemplate')}</option>
              {templates.map((template) => (
                <option key={template.id} value={template.id}>
                  {template.name} {template.is_system ? `(${t('prompts.system')})` : ''}
                </option>
              ))}
            </Form.Select>
          )}
        </div>
        
        <div className="d-flex">
          <Button
            variant="outline-secondary"
            size="sm"
            onClick={() => {
              if (selectedTemplateId) {
                const template = getTemplateById(selectedTemplateId);
                if (template) {
                  toggleDetails(template);
                }
              } else {
                setShowBrowser(true);
              }
            }}
            title={selectedTemplateId ? t('prompts.viewDetails') : t('prompts.browse')}
          >
            <FaInfoCircle />
          </Button>
          
          {showCreateButton && onCreateTemplate && (
            <Button
              variant="outline-primary"
              size="sm"
              className="ms-1"
              onClick={onCreateTemplate}
              title={t('prompts.createNew')}
            >
              <FaPlusCircle />
            </Button>
          )}
        </div>
      </div>
      
      {error && <div className="text-danger small mt-1">{error}</div>}
      
      {/* Şablon detayları modalı */}
      <Modal
        show={showDetails}
        onHide={() => toggleDetails(null)}
        centered
        size="lg"
      >
        <Modal.Header closeButton>
          <Modal.Title>
            {selectedTemplate?.name}
            {selectedTemplate?.is_system && (
              <Badge bg="secondary" className="ms-2">
                {t('prompts.system')}
              </Badge>
            )}
          </Modal.Title>
        </Modal.Header>
        
        <Modal.Body>
          <p className="text-muted">{selectedTemplate?.description}</p>
          
          <h6>{t('prompts.template')}:</h6>
          <pre className="bg-light p-3 rounded border">
            {selectedTemplate?.template}
          </pre>
          
          <div className="d-flex justify-content-between text-muted small mt-3">
            <div>
              {t('prompts.created')}: {new Date(selectedTemplate?.created_at || '').toLocaleString()}
            </div>
            <div>
              {t('prompts.updated')}: {new Date(selectedTemplate?.updated_at || '').toLocaleString()}
            </div>
          </div>
        </Modal.Body>
        
        <Modal.Footer>
          <Button variant="secondary" onClick={() => toggleDetails(null)}>
            {t('common.close')}
          </Button>
          <Button 
            variant="primary" 
            onClick={() => {
              if (selectedTemplate) {
                onChange(selectedTemplate.id);
                toggleDetails(null);
              }
            }}
          >
            {t('prompts.select')}
          </Button>
        </Modal.Footer>
      </Modal>
      
      {/* Şablon tarayıcısı modalı */}
      <Modal
        show={showBrowser}
        onHide={() => setShowBrowser(false)}
        centered
        size="lg"
        scrollable
      >
        <Modal.Header closeButton>
          <Modal.Title>{t('prompts.browseTemplates')}</Modal.Title>
        </Modal.Header>
        
        <Modal.Body>
          <div className="mb-3">
            <div className="input-group">
              <Form.Control
                type="text"
                placeholder={t('prompts.searchPlaceholder')}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              />
              <Button variant="outline-secondary" onClick={handleSearch}>
                <FaSearch />
              </Button>
            </div>
          </div>
          
          {loading ? (
            <div className="text-center py-3">
              <Spinner animation="border" />
            </div>
          ) : filteredTemplates.length === 0 ? (
            <div className="text-center py-3 text-muted">
              {t('prompts.noTemplatesFound')}
            </div>
          ) : (
            <ListGroup>
              {filteredTemplates.map((template) => (
                <ListGroup.Item 
                  key={template.id}
                  action
                  onClick={() => handleSelectTemplateFromBrowser(template)}
                  active={template.id === selectedTemplateId}
                  className="d-flex justify-content-between align-items-center"
                >
                  <div>
                    <div className="d-flex align-items-center">
                      <strong>{template.name}</strong>
                      {template.is_system && (
                        <Badge bg="secondary" className="ms-2">
                          {t('prompts.system')}
                        </Badge>
                      )}
                    </div>
                    <div className="text-muted small mt-1">
                      {template.description}
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant="outline-secondary"
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleDetails(template);
                    }}
                  >
                    {t('common.details')}
                  </Button>
                </ListGroup.Item>
              ))}
            </ListGroup>
          )}
        </Modal.Body>
        
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowBrowser(false)}>
            {t('common.close')}
          </Button>
          {showCreateButton && onCreateTemplate && (
            <Button variant="primary" onClick={onCreateTemplate}>
              <FaPlusCircle className="me-1" />
              {t('prompts.createNew')}
            </Button>
          )}
        </Modal.Footer>
      </Modal>
    </div>
  );
};

export default PromptTemplateSelector;