// Last reviewed: 2025-04-30 06:02:16 UTC (User: Teeksss)
import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Form, Button, Spinner, Alert } from 'react-bootstrap';
import { FaPaperPlane, FaHistory, FaSearch } from 'react-icons/fa';
import { useTranslation } from 'react-i18next';
import API from '../api/api';
import { useToast } from '../contexts/ToastContext';
import QueryResult from '../components/query/QueryResult';
import QueryHistory from '../components/QueryHistory';
import { useNavigate, useSearchParams } from 'react-router-dom';
import '../styles/query-results.css';

interface QueryResponse {
  id: string;
  question: string;
  answer?: string;
  sources?: Array<{
    id: string;
    document_id?: string;
    document_title?: string;
    content_snippet?: string;
    similarity_score?: number;
    page_number?: number;
  }>;
  created_at: string;
  processing_time_ms?: number;
  has_error: boolean;
  error_message?: string;
}

const QueryPage: React.FC = () => {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  // State
  const [question, setQuestion] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  // URL'den sorgu kimliğini al
  useEffect(() => {
    const queryId = searchParams.get('id');
    if (queryId) {
      // Belirli bir sorguyu yükle
      loadQueryById(queryId);
    }
  }, [searchParams]);
  
  // Belirli bir sorguyu ID ile yükle
  const loadQueryById = async (queryId: string) => {
    try {
      setIsSubmitting(true);
      setError(null);
      
      const response = await API.get(`/queries/${queryId}`);
      setResult(response.data);
      
      // Sorguyu form alanına da yerleştir
      setQuestion(response.data.question);
      
    } catch (err: any) {
      console.error('Error loading query:', err);
      setError(err.response?.data?.detail || t('query.loadError'));
      showToast('error', t('query.loadError'));
      
    } finally {
      setIsSubmitting(false);
    }
  };
  
  // Soru gönderme işleyicisi
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!question.trim()) {
      showToast('warning', t('query.emptyQuestion'));
      return;
    }
    
    setIsSubmitting(true);
    setError(null);
    
    try {
      const response = await API.post('/queries/', {
        question: question.trim(),
        search_type: 'semantic',
        include_sources: true
      });
      
      setResult(response.data);
      
      // URL'i güncelle
      navigate(`/query?id=${response.data.id}`, { replace: true });
      
    } catch (err: any) {
      console.error('Error submitting query:', err);
      setError(err.response?.data?.detail || t('query.submitError'));
      showToast('error', t('query.submitError'));
      
    } finally {
      setIsSubmitting(false);
    }
  };
  
  // Geçmiş sorguyu seçme işleyicisi
  const handleSelectQuery = (selectedQuestion: string) => {
    setQuestion(selectedQuestion);
    // Formu görünür alana kaydır
    document.getElementById('query-form')?.scrollIntoView({ behavior: 'smooth' });
  };
  
  // Belge görüntüleme işleyicisi
  const handleViewDocument = (documentId: string) => {
    navigate(`/documents/${documentId}`);
  };
  
  return (
    <Container fluid className="py-4">
      <Row className="mb-4">
        <Col>
          <h1 className="h3">
            <FaSearch className="me-2" />
            {t('query.title')}
          </h1>
          <p className="text-muted">{t('query.subtitle')}</p>
        </Col>
      </Row>
      
      <Row>
        {/* Ana içerik */}
        <Col lg={8} className="mb-4">
          {/* Soru formu */}
          <Form onSubmit={handleSubmit} className="mb-4" id="query-form">
            <Form.Group className="mb-3">
              <Form.Label><strong>{t('query.askQuestion')}</strong></Form.Label>
              <Form.Control
                as="textarea"
                rows={3}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder={t('query.questionPlaceholder')}
                disabled={isSubmitting}
              />
            </Form.Group>
            
            <div className="d-grid">
              <Button 
                variant="primary" 
                type="submit" 
                disabled={isSubmitting || !question.trim()}
                size="lg"
              >
                {isSubmitting ? (
                  <>
                    <Spinner animation="border" size="sm" className="me-2" />
                    {t('query.processing')}
                  </>
                ) : (
                  <>
                    <FaPaperPlane className="me-2" />
                    {t('query.submit')}
                  </>
                )}
              </Button>
            </div>
          </Form>
          
          {/* Hata mesajı */}
          {error && (
            <Alert variant="danger" className="mb-4">
              {error}
            </Alert>
          )}
          
          {/* Sorgu sonucu */}
          {result && (
            <QueryResult
              id={result.id}
              question={result.question}
              answer={result.answer}
              sources={result.sources}
              created_at={result.created_at}
              processing_time_ms={result.processing_time_ms}
              has_error={result.has_error}
              error_message={result.error_message}
              onViewDocument={handleViewDocument}
            />
          )}
        </Col>
        
        {/* Sağ kenar çubuğu - Sorgu geçmişi */}
        <Col lg={4}>
          <div className="sticky-top pt-3" style={{ top: '1rem' }}>
            <h5 className="mb-3">
              <FaHistory className="me-2" />
              {t('query.history')}
            </h5>
            
            <QueryHistory onSelectQuery={handleSelectQuery} />
          </div>
        </Col>
      </Row>
    </Container>
  );
};

export default QueryPage;