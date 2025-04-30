// Last reviewed: 2025-04-29 14:19:03 UTC (User: TeeksssRAG)
import React, { useState, useEffect } from 'react';
import { Form, Button, Card, Alert, Row, Col, Spinner, Modal } from 'react-bootstrap';
import { useTranslation } from 'react-i18next';
import { FaSave, FaCheck, FaTimes, FaInfoCircle } from 'react-icons/fa';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';

// API istemcisi
import API from '../api/api';

// Tip tanımları
interface PromptTemplate {
  id: string;
  name: string;
  description: string;
  template: string;
  is_system: boolean;
  user_id?: string;
  organization_id?: string;
  created_at: string;
  updated_at: string;
}

interface PromptTemplateEditorProps {
  templateId?: string;  // Düzenleme modunda template ID'si 
  onSave?: (template: PromptTemplate) => void;
  onCancel?: () => void;
}

// Form doğrulama şeması
const schema = yup.object({
  name: yup.string().required('Name is required').min(3, 'Name must be at least 3 characters'),
  description: yup.string().required('Description is required'),
  template: yup.string().required('Template content is required')
    .min(20, 'Template content must be at least 20 characters')
    .test('has-variables', 'Template must contain {context} and {question} variables', 
      (value) => value && value.includes('{context}') && value.includes('{question}'))
});

const PromptTemplateEditor: React.FC<PromptTemplateEditorProps> = ({
  templateId,
  onSave,
  onCancel
}) => {
  const { t } = useTranslation();
  
  // Form durumları
  const [loading, setLoading] = useState(false);
  const [savingTemplate, setSavingTemplate] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showHelp, setShowHelp] = useState(false);
  
  // React Hook Form entegrasyonu
  const { register, handleSubmit, setValue, watch, formState: { errors } } = useForm({
    resolver: yupResolver(schema),
    defaultValues: {
      name: '',
      description: '',
      template: ''
    }
  });
  
  // Template değişkenlerini izle
  const templateText = watch('template');
  
  // Template varsa yükleme
  useEffect(() => {
    const loadTemplate = async () => {
      if (!templateId) return;
      
      setLoading(true);
      setError(null);
      
      try {
        const response = await API.get(`/prompts/${templateId}`);
        const template = response.data;
        
        setValue('name', template.name);
        setValue('description', template.description);
        setValue('template', template.template);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load template');
        console.error('Error loading template:', err);
      } finally {
        setLoading(false);
      }
    };
    
    loadTemplate();
  }, [templateId, setValue]);
  
  // Form gönderimi
  const onSubmit = async (data: any) => {
    setSavingTemplate(true);
    setError(null);
    
    try {
      let response;
      
      if (templateId) {
        // Mevcut şablonu güncelle
        response = await API.put(`/prompts/${templateId}`, data);
      } else {
        // Yeni şablon oluştur
        response = await API.post('/prompts', data);
      }
      
      if (onSave) {
        onSave(response.data);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save template');
      console.error('Error saving template:', err);
    } finally {
      setSavingTemplate(false);
    }
  };
  
  // Template değişkenlerinin kontrol edilmesi
  const checkTemplateVariables = () => {
    const template = templateText || '';
    const hasContext = template.includes('{context}');
    const hasQuestion = template.includes('{question}');
    
    return { hasContext, hasQuestion };
  };
  
  const { hasContext, hasQuestion } = checkTemplateVariables();
  
  // Yükleniyor durumu
  if (loading) {
    return (
      <Card className="shadow-sm">
        <Card.Body className="text-center p-5">
          <Spinner animation="border" />
          <p className="mt-3">{t('prompts.loading')}</p>
        </Card.Body>
      </Card>
    );
  }
  
  return (
    <>
      <Card className="shadow-sm">
        <Card.Header className="bg-light py-3">
          <div className="d-flex justify-content-between align-items-center">
            <h5 className="mb-0">
              {templateId ? t('prompts.editTemplate') : t('prompts.createTemplate')}
            </h5>
            <Button 
              variant="link" 
              className="p-0" 
              onClick={() => setShowHelp(true)}
            >
              <FaInfoCircle /> {t('common.help')}
            </Button>
          </div>
        </Card.Header>
        
        <Card.Body>
          {error && (
            <Alert variant="danger" className="mb-4">
              {error}
            </Alert>
          )}
          
          <Form onSubmit={handleSubmit(onSubmit)}>
            <Form.Group className="mb-3" controlId="templateName">
              <Form.Label>{t('prompts.name')}</Form.Label>
              <Form.Control
                type="text"
                placeholder={t('prompts.namePlaceholder')}
                {...register('name')}
                isInvalid={!!errors.name}
              />
              {errors.name && (
                <Form.Control.Feedback type="invalid">
                  {errors.name.message}
                </Form.Control.Feedback>
              )}
            </Form.Group>
            
            <Form.Group className="mb-3" controlId="templateDescription">
              <Form.Label>{t('prompts.description')}</Form.Label>
              <Form.Control
                as="textarea"
                rows={2}
                placeholder={t('prompts.descriptionPlaceholder')}
                {...register('description')}
                isInvalid={!!errors.description}
              />
              {errors.description && (
                <Form.Control.Feedback type="invalid">
                  {errors.description.message}
                </Form.Control.Feedback>
              )}
            </Form.Group>
            
            <Form.Group className="mb-3" controlId="templateContent">
              <Form.Label>{t('prompts.template')}</Form.Label>
              <Form.Control
                as="textarea"
                rows={10}
                placeholder={t('prompts.templatePlaceholder')}
                {...register('template')}
                isInvalid={!!errors.template}
                className="font-monospace"
              />
              {errors.template && (
                <Form.Control.Feedback type="invalid">
                  {errors.template.message}
                </Form.Control.Feedback>
              )}
              
              <div className="mt-2">
                <div className="d-flex gap-3">
                  <div className="d-flex align-items-center">
                    {hasContext ? (
                      <FaCheck className="text-success me-1" />
                    ) : (
                      <FaTimes className="text-danger me-1" />
                    )}
                    <span className={hasContext ? 'text-success' : 'text-danger'}>
                      {'{context}'} {hasContext ? t('common.found') : t('common.missing')}
                    </span>
                  </div>
                  <div className="d-flex align-items-center">
                    {hasQuestion ? (
                      <FaCheck className="text-success me-1" />
                    ) : (
                      <FaTimes className="text-danger me-1" />
                    )}
                    <span className={hasQuestion ? 'text-success' : 'text-danger'}>
                      {'{question}'} {hasQuestion ? t('common.found') : t('common.missing')}
                    </span>
                  </div>
                </div>
              </div>
            </Form.Group>
            
            <div className="d-flex justify-content-end gap-2 mt-4">
              {onCancel && (
                <Button 
                  variant="outline-secondary" 
                  onClick={onCancel}
                  disabled={savingTemplate}
                >
                  {t('common.cancel')}
                </Button>
              )}
              <Button 
                type="submit" 
                variant="primary"
                disabled={savingTemplate}
              >
                {savingTemplate ? (
                  <>
                    <Spinner as="span" size="sm" animation="border" className="me-2" />
                    {t('common.saving')}
                  </>
                ) : (
                  <>
                    <FaSave className="me-2" />
                    {t('common.save')}
                  </>
                )}
              </Button>
            </div>
          </Form>
        </Card.Body>
      </Card>
      
      {/* Yardım modal */}
      <Modal show={showHelp} onHide={() => setShowHelp(false)} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>{t('prompts.helpTitle')}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <h5>{t('prompts.variablesTitle')}</h5>
          <p>{t('prompts.variablesDescription')}</p>
          
          <Alert variant="info">
            <strong>{'{context}'}</strong>: {t('prompts.contextVariable')}
            <br />
            <strong>{'{question}'}</strong>: {t('prompts.questionVariable')}
          </Alert>
          
          <h5 className="mt-4">{t('prompts.exampleTitle')}</h5>
          <pre className="bg-light p-3 rounded">
            {`Sen yardımcı bir asistansın.
Sana bir soru ve ilgili belge bağlamı verildi.

Bağlam:
{context}

Soru:
{question}

Yukarıdaki bağlamdan soru için en iyi cevabı kısa ve öz olarak ver.
Eğer bağlamda cevap yoksa, bilmediğini söyle.
Yanıtını madde madde düzenli bir şekilde ver.`}
          </pre>
          
          <h5 className="mt-4">{t('prompts.bestPracticesTitle')}</h5>
          <ul>
            <li>{t('prompts.bestPractice1')}</li>
            <li>{t('prompts.bestPractice2')}</li>
            <li>{t('prompts.bestPractice3')}</li>
            <li>{t('prompts.bestPractice4')}</li>
            <li>{t('prompts.bestPractice5')}</li>
          </ul>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="primary" onClick={() => setShowHelp(false)}>
            {t('common.close')}
          </Button>
        </Modal.Footer>
      </Modal>
    </>
  );
};

export default PromptTemplateEditor;