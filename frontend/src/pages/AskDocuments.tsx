// Last reviewed: 2025-04-29 14:19:03 UTC (User: TeeksssRAG)
import React, { useState, useEffect } from 'react';
import { 
  Container, 
  Card, 
  Form, 
  Button, 
  Alert, 
  Spinner, 
  Row, 
  Col,
  InputGroup,
  Dropdown,
  Badge
} from 'react-bootstrap';
import { useTranslation } from 'react-i18next';
import { FaSearch, FaCog, FaHistory, FaStar, FaRegStar, FaPaperPlane } from 'react-icons/fa';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';

// Bileşenler
import RAGQueryResult from '../components/RAGQueryResult';
import PromptTemplateSelector from '../components/PromptTemplateSelector';
import QueryHistory from '../components/QueryHistory';

// API ve hooks
import API from '../api/api';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';

// Tipler
interface RAGSource {
  id: string;
  title: string;
  url?: string;
  snippet?: string;
  relevance_score?: number;
}

interface RAGResponse {
  query_id: string;
  question: string;
  answer: string;
  sources: RAGSource[];
  error?: string;
  created_at: string;
}

interface PromptTemplate {
  id: string;
  name: string;
  description: string;
  is_system: boolean;
  created_at: string;
}

interface SearchHistoryItem {
  id: string;
  question: string;
  created_at: string;
  sources_count: number;
  is_favorite: boolean;
}

const AskDocuments: React.FC = () => {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  
  // Form durumları
  const [question, setQuestion] = useState('');
  const [searchType, setSearchType] = useState('semantic');
  const [showSettings, setShowSettings] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [promptTemplateId, setPromptTemplateId] = useState<string | null>(null);
  const [maxResults, setMaxResults] = useState(5);
  
  // API durumları
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<RAGResponse | null>(null);
  
  // URL parametreleri ile durumu güncelle
  useEffect(() => {
    const queryParam = searchParams.get('q');
    if (queryParam) {
      setQuestion(queryParam);
      
      // Otomatik olarak arama yap
      if (queryParam.trim().length >= 3) {
        handleSearch(queryParam);
      }
    }
    
    // Diğer parametreleri de al
    const typeParam = searchParams.get('type');
    if (typeParam && (typeParam === 'semantic' || typeParam === 'keyword')) {
      setSearchType(typeParam);
    }
    
    const templateParam = searchParams.get('template');
    if (templateParam) {
      setPromptTemplateId(templateParam);
    }
    
    const resultsParam = searchParams.get('results');
    if (resultsParam) {
      setMaxResults(parseInt(resultsParam, 10) || 5);
    }
  }, [searchParams]);
  
  // Form gönderimi
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSearch();
  };
  
  // Arama işlemi
  const handleSearch = async (searchQuestion?: string) => {
    const queryText = (searchQuestion || question).trim();
    if (!queryText) return;
    
    try {
      setLoading(true);
      setError(null);
      
      // URL parametrelerini güncelle
      setSearchParams({
        q: queryText,
        type: searchType,
        ...(promptTemplateId ? { template: promptTemplateId } : {}),
        results: maxResults.toString()
      });
      
      // API isteği
      const response = await API.post('/rag/query', {
        question: queryText,
        search_type: searchType,
        prompt_template_id: promptTemplateId || undefined,
        max_results: maxResults
      });
      
      // Yanıtı ayarla
      setResponse(response.data);
    } catch (err: any) {
      console.error('Error searching documents:', err);
      setError(err.response?.data?.detail || t('rag.searchError'));
      showToast(t('rag.searchError'), 'error');
    } finally {
      setLoading(false);
    }
  };
  
  // Ayarları sıfırla
  const resetSettings = () => {
    setSearchType('semantic');
    setPromptTemplateId(null);
    setMaxResults(5);
    setShowSettings(false);
  };
  
  // Yeniden deneme işlemi
  const handleRetry = () => {
    handleSearch();
  };
  
  return (
    <Container className="py-4">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <Card className="shadow-sm mb-4">
          <Card.Body>
            <Form onSubmit={handleSubmit}>
              <Row>
                <Col>
                  <InputGroup className="mb-3">
                    <InputGroup.Text>
                      <FaSearch />
                    </InputGroup.Text>
                    <Form.Control
                      type="text"
                      placeholder={t('rag.questionPlaceholder')}
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      disabled={loading}
                      autoFocus
                    />
                    <Button 
                      variant="primary" 
                      type="submit"
                      disabled={loading || question.trim().length < 3}
                    >
                      {loading ? (
                        <Spinner animation="border" size="sm" />
                      ) : (
                        <FaPaperPlane />
                      )}
                    </Button>
                  </InputGroup>
                </Col>
                
                <Col xs="auto" className="d-flex">
                  <Button 
                    variant={showSettings ? "primary" : "outline-secondary"} 
                    className="me-2"
                    onClick={() => setShowSettings(!showSettings)}
                    title={t('rag.settings')}
                  >
                    <FaCog />
                  </Button>
                  
                  <Button
                    variant={showHistory ? "primary" : "outline-secondary"}
                    onClick={() => setShowHistory(!showHistory)}
                    title={t('rag.history')}
                  >
                    <FaHistory />
                  </Button>
                </Col>
              </Row>
              
              {showSettings && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <Card className="mt-3 border-light">
                    <Card.Body className="pt-3 pb-3">
                      <Row>
                        {/* Arama tipi seçimi */}
                        <Col md={4} className="mb-3 mb-md-0">
                          <Form.Group>
                            <Form.Label>{t('rag.searchType')}</Form.Label>
                            <div>
                              <Form.Check
                                inline
                                type="radio"
                                name="searchType"
                                id="semantic"
                                label={t('rag.semantic')}
                                checked={searchType === 'semantic'}
                                onChange={() => setSearchType('semantic')}
                              />
                              <Form.Check
                                inline
                                type="radio"
                                name="searchType"
                                id="keyword"
                                label={t('rag.keyword')}
                                checked={searchType === 'keyword'}
                                onChange={() => setSearchType('keyword')}
                              />
                            </div>
                          </Form.Group>
                        </Col>
                        
                        {/* Belge sayısı seçimi */}
                        <Col md={3} className="mb-3 mb-md-0">
                          <Form.Group>
                            <Form.Label>{t('rag.maxResults')}</Form.Label>
                            <Form.Select 
                              value={maxResults} 
                              onChange={(e) => setMaxResults(parseInt(e.target.value, 10))}
                            >
                              <option value="3">3</option>
                              <option value="5">5</option>
                              <option value="8">8</option>
                              <option value="10">10</option>
                              <option value="15">15</option>
                            </Form.Select>
                          </Form.Group>
                        </Col>
                        
                        {/* Prompt şablonu seçimi */}
                        <Col md={5}>
                          <Form.Group>
                            <Form.Label>{t('rag.promptTemplate')}</Form.Label>
                            <PromptTemplateSelector
                              selectedTemplateId={promptTemplateId}
                              onChange={(id) => setPromptTemplateId(id)}
                            />
                          </Form.Group>
                        </Col>
                      </Row>
                      
                      <div className="d-flex justify-content-end mt-3">
                        <Button 
                          variant="outline-secondary" 
                          size="sm" 
                          onClick={resetSettings}
                        >
                          {t('common.reset')}
                        </Button>
                      </div>
                    </Card.Body>
                  </Card>
                </motion.div>
              )}
              
              {showHistory && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="mt-3"
                >
                  <QueryHistory 
                    onSelectQuery={(query) => {
                      setQuestion(query);
                      handleSearch(query);
                      setShowHistory(false);
                    }}
                  />
                </motion.div>
              )}
            </Form>
          </Card.Body>
        </Card>
      </motion.div>
      
      {/* Sonuç görüntüleme */}
      {(loading || error || response) && (
        <RAGQueryResult
          response={response as RAGResponse}
          isLoading={loading}
          error={error || undefined}
          onRetry={handleRetry}
        />
      )}
      
      {/* İpuçları */}
      {!response && !loading && !error && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <Card className="border-0 bg-light">
            <Card.Body className="text-center py-5">
              <h3 className="mb-4">{t('rag.tipsTitle')}</h3>
              
              <Row className="justify-content-center gy-4">
                <Col md={4}>
                  <Card className="h-100 border-0 shadow-sm">
                    <Card.Body className="text-start">
                      <h5>{t('rag.tipSpecific')}</h5>
                      <p className="text-muted">{t('rag.tipSpecificDesc')}</p>
                      <div className="mt-3 bg-light p-2 rounded">
                        <strong>{t('rag.example')}:</strong> {t('rag.tipSpecificExample')}
                      </div>
                    </Card.Body>
                  </Card>
                </Col>
                
                <Col md={4}>
                  <Card className="h-100 border-0 shadow-sm">
                    <Card.Body className="text-start">
                      <h5>{t('rag.tipContext')}</h5>
                      <p className="text-muted">{t('rag.tipContextDesc')}</p>
                      <div className="mt-3 bg-light p-2 rounded">
                        <strong>{t('rag.example')}:</strong> {t('rag.tipContextExample')}
                      </div>
                    </Card.Body>
                  </Card>
                </Col>
                
                <Col md={4}>
                  <Card className="h-100 border-0 shadow-sm">
                    <Card.Body className="text-start">
                      <h5>{t('rag.tipKeywords')}</h5>
                      <p className="text-muted">{t('rag.tipKeywordsDesc')}</p>
                      <div className="mt-3 bg-light p-2 rounded">
                        <strong>{t('rag.example')}:</strong> {t('rag.tipKeywordsExample')}
                      </div>
                    </Card.Body>
                  </Card>
                </Col>
              </Row>
            </Card.Body>
          </Card>
        </motion.div>
      )}
    </Container>
  );
};

export default AskDocuments;