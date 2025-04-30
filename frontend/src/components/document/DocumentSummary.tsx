// Last reviewed: 2025-04-30 07:59:11 UTC (User: Teeksss)
import React, { useState, useEffect } from 'react';
import { Card, Button, Spinner, Badge, Accordion, Alert } from 'react-bootstrap';
import { FaSyncAlt, FaFile, FaList, FaLightbulb, FaQuestionCircle } from 'react-icons/fa';
import { formatDistanceToNow } from 'date-fns';
import { tr, enUS } from 'date-fns/locale';
import { useTranslation } from 'react-i18next';

import API from '../../api/api';
import { useToast } from '../../contexts/ToastContext';

interface DocumentSummaryProps {
  documentId: string;
  showRefreshButton?: boolean;
}

interface SummaryData {
  general_content: string;
  key_concepts: string[];
  author_purpose: string;
}

interface SummaryResponse {
  document_id: string;
  title: string;
  summary: SummaryData;
  generated_at: string;
  is_new: boolean;
}

const DocumentSummary: React.FC<DocumentSummaryProps> = ({ 
  documentId,
  showRefreshButton = true
}) => {
  const { t, i18n } = useTranslation();
  const { showToast } = useToast();
  
  // State
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [title, setTitle] = useState<string>('');
  const [generatedAt, setGeneratedAt] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  
  // date-fns locale
  const locale = i18n.language === 'tr' ? tr : enUS;
  
  // Özet yükle
  useEffect(() => {
    if (documentId) {
      loadSummary();
    }
  }, [documentId]);
  
  // Özeti yükle
  const loadSummary = async (forceRefresh: boolean = false) => {
    if (!documentId) return;
    
    try {
      setLoading(true);
      
      const response = await API.get(
        `/document-summary/${documentId}${forceRefresh ? '?force_refresh=true' : ''}`
      );
      
      const data: SummaryResponse = response.data;
      
      setTitle(data.title);
      setSummary(data.summary);
      setGeneratedAt(data.generated_at);
      setError(null);
      
      if (data.is_new && forceRefresh) {
        showToast('success', t('document.summary.refreshSuccess'));
      }
      
    } catch (err: any) {
      console.error('Error loading document summary:', err);
      setError(err.response?.data?.detail || t('document.summary.loadError'));
      setSummary(null);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };
  
  // Özet yenileme
  const handleRefreshSummary = async () => {
    setRefreshing(true);
    await loadSummary(true);
  };
  
  // Yükleniyor durumu
  if (loading) {
    return (
      <Card className="mb-3">
        <Card.Body className="text-center py-4">
          <Spinner animation="border" />
          <p className="mt-3 text-muted">{t('document.summary.loading')}</p>
        </Card.Body>
      </Card>
    );
  }
  
  // Hata durumu
  if (error) {
    return (
      <Alert variant="danger">
        <Alert.Heading>{t('document.summary.error')}</Alert.Heading>
        <p>{error}</p>
        <div className="d-flex justify-content-end">
          <Button 
            variant="outline-danger" 
            size="sm"
            onClick={() => loadSummary()}
          >
            <FaSyncAlt className="me-1" /> {t('common.tryAgain')}
          </Button>
        </div>
      </Alert>
    );
  }
  
  // Özet yok
  if (!summary) {
    return (
      <Card className="mb-3">
        <Card.Body>
          <Card.Title>{t('document.summary.notAvailable')}</Card.Title>
          <p>{t('document.summary.notGeneratedYet')}</p>
          <Button 
            variant="primary" 
            onClick={handleRefreshSummary}
            disabled={refreshing}
          >
            {refreshing ? (
              <>
                <Spinner animation="border" size="sm" className="me-2" />
                {t('document.summary.generating')}
              </>
            ) : (
              <>
                <FaSyncAlt className="me-1" />
                {t('document.summary.generate')}
              </>
            )}
          </Button>
        </Card.Body>
      </Card>
    );
  }
  
  // Özet bilgisi
  return (
    <Card className="mb-3 document-summary-card">
      <Card.Header>
        <div className="d-flex justify-content-between align-items-center">
          <h5 className="mb-0">
            <FaFile className="me-2" />
            {t('document.summary.title')}
          </h5>
          
          {showRefreshButton && (
            <Button
              variant="outline-secondary"
              size="sm"
              onClick={handleRefreshSummary}
              disabled={refreshing}
              title={t('document.summary.refresh')}
            >
              {refreshing ? (
                <Spinner animation="border" size="sm" />
              ) : (
                <FaSyncAlt />
              )}
            </Button>
          )}
        </div>
      </Card.Header>
      
      <Card.Body>
        <div className="document-title mb-3">
          <h5>{title}</h5>
          {generatedAt && (
            <small className="text-muted">
              {t('document.summary.generatedAgo', {
                time: formatDistanceToNow(new Date(generatedAt), { addSuffix: true, locale })
              })}
            </small>
          )}
        </div>
        
        <Accordion defaultActiveKey="0" className="mb-3">
          <Accordion.Item eventKey="0">
            <Accordion.Header>
              <FaFile className="me-2" />
              {t('document.summary.generalContent')}
            </Accordion.Header>
            <Accordion.Body>
              {summary.general_content}
            </Accordion.Body>
          </Accordion.Item>
          
          <Accordion.Item eventKey="1">
            <Accordion.Header>
              <FaList className="me-2" />
              {t('document.summary.keyConcepts')}
            </Accordion.Header>
            <Accordion.Body>
              <div className="d-flex flex-wrap gap-2">
                {summary.key_concepts.map((concept, index) => (
                  <Badge key={index} bg="info" className="px-3 py-2">
                    {concept}
                  </Badge>
                ))}
              </div>
            </Accordion.Body>
          </Accordion.Item>
          
          <Accordion.Item eventKey="2">
            <Accordion.Header>
              <FaLightbulb className="me-2" />
              {t('document.summary.authorPurpose')}
            </Accordion.Header>
            <Accordion.Body>
              {summary.author_purpose}
            </Accordion.Body>
          </Accordion.Item>
        </Accordion>
        
        <div className="summary-help text-muted">
          <FaQuestionCircle className="me-1" />
          <small>{t('document.summary.help')}</small>
        </div>
      </Card.Body>
    </Card>
  );
};

export default DocumentSummary;