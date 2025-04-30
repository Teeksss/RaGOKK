// Last reviewed: 2025-04-29 14:19:03 UTC (User: TeeksssRAG)
import React, { useState, useEffect } from 'react';
import { Card, Button, Alert, Spinner, Badge, Accordion, Toast } from 'react-bootstrap';
import { useTranslation } from 'react-i18next';
import { FaLink, FaCopy, FaInfoCircle, FaChevronDown, FaChevronRight, FaExclamationCircle, FaCheck } from 'react-icons/fa';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';

// Tip tanımları
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

interface RAGQueryResultProps {
  response: RAGResponse;
  isLoading: boolean;
  error?: string;
  onRetry?: () => void;
}

const RAGQueryResult: React.FC<RAGQueryResultProps> = ({
  response,
  isLoading,
  error,
  onRetry
}) => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  
  const [showSources, setShowSources] = useState(true);
  const [copySuccess, setCopySuccess] = useState(false);
  
  // Cevabı kopyalama işlevi
  const copyToClipboard = () => {
    navigator.clipboard.writeText(response?.answer || '');
    setCopySuccess(true);
    setTimeout(() => setCopySuccess(false), 2000);
  };
  
  // Kaynak URL'sini normalize et
  const normalizeSourceUrl = (url?: string): string => {
    if (!url) return '#';
    if (url.startsWith('http')) return url;
    return url;
  };
  
  // Kaynağa tıklama işlevi
  const handleSourceClick = (source: RAGSource) => {
    if (source.url && !source.url.startsWith('http')) {
      navigate(source.url);
    }
  };
  
  // Kaynakları ilgililik skoruna göre sırala
  const sortedSources = response?.sources
    ? [...response.sources].sort((a, b) => 
        (b.relevance_score || 0) - (a.relevance_score || 0)
      )
    : [];
  
  // Yükleniyor durumu
  if (isLoading) {
    return (
      <Card className="shadow-sm mb-4">
        <Card.Body className="text-center p-5">
          <Spinner animation="border" variant="primary" />
          <p className="mt-3">{t('rag.loading')}</p>
        </Card.Body>
      </Card>
    );
  }
  
  // Hata durumu
  if (error || response?.error) {
    return (
      <Alert variant="danger" className="mb-4">
        <div className="d-flex align-items-center mb-2">
          <FaExclamationCircle className="me-2" size={24} />
          <h5 className="mb-0">{t('rag.errorTitle')}</h5>
        </div>
        <p>{error || response?.error || t('rag.unknownError')}</p>
        {onRetry && (
          <Button variant="outline-danger" size="sm" onClick={onRetry}>
            {t('common.retry')}
          </Button>
        )}
      </Alert>
    );
  }
  
  // Cevap yok durumu
  if (!response) {
    return null;
  }
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* Kopyalama bildirim toast'u */}
      <Toast
        show={copySuccess}
        onClose={() => setCopySuccess(false)}
        style={{
          position: 'fixed',
          top: 20,
          right: 20,
          zIndex: 9999
        }}
        delay={2000}
        autohide
      >
        <Toast.Header>
          <FaCheck className="me-2 text-success" />
          <strong className="me-auto">{t('common.success')}</strong>
        </Toast.Header>
        <Toast.Body>{t('rag.copiedToClipboard')}</Toast.Body>
      </Toast>
    
      {/* Cevap kartı */}
      <Card className="shadow-sm mb-4 rag-answer-card">
        {/* Soru başlığı */}
        <Card.Header className="bg-light py-3">
          <div className="d-flex justify-content-between align-items-center">
            <h5 className="mb-0">
              <span className="text-primary me-2">Q:</span> 
              {response.question}
            </h5>
            <Button 
              variant="outline-secondary" 
              size="sm"
              onClick={copyToClipboard}
              title={t('common.copy')}
            >
              <FaCopy />
            </Button>
          </div>
        </Card.Header>
        
        {/* Cevap içeriği */}
        <Card.Body className="rag-answer-content pt-4">
          <div className="mb-4">
            <ReactMarkdown 
              remarkPlugins={[remarkGfm]}
              className="markdown-content"
            >
              {response.answer}
            </ReactMarkdown>
          </div>
          
          {/* Kaynaklar bölümü */}
          {sortedSources.length > 0 && (
            <div className="mt-4 pt-3 border-top">
              <div 
                className="d-flex justify-content-between align-items-center mb-3"
                style={{ cursor: 'pointer' }}
                onClick={() => setShowSources(!showSources)}
              >
                <h6 className="mb-0">
                  <Badge bg="light" text="dark" className="me-2">
                    {sortedSources.length}
                  </Badge>
                  {t('rag.sources')}
                </h6>
                {showSources ? <FaChevronDown size={12} /> : <FaChevronRight size={12} />}
              </div>
              
              {showSources && (
                <div className="sources-container">
                  {sortedSources.map((source, index) => (
                    <div 
                      key={source.id || index} 
                      className="source-item p-2 mb-2 rounded border"
                      onClick={() => handleSourceClick(source)}
                      style={{ cursor: source.url ? 'pointer' : 'default' }}
                    >
                      <div className="d-flex justify-content-between align-items-start">
                        <div className="d-flex align-items-center">
                          {source.url && <FaLink className="me-2 text-secondary" size={14} />}
                          <span className="source-title">
                            {source.title}
                          </span>
                        </div>
                        
                        {source.relevance_score !== undefined && (
                          <Badge 
                            bg={source.relevance_score > 0.8 ? "success" : 
                               source.relevance_score > 0.5 ? "primary" : "secondary"}
                            className="ms-2"
                          >
                            {Math.round(source.relevance_score * 100)}%
                          </Badge>
                        )}
                      </div>
                      
                      {source.snippet && (
                        <div className="source-snippet text-muted mt-1 small">
                          {source.snippet}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </Card.Body>
        
        {/* Kart alt bilgi */}
        <Card.Footer className="bg-white border-top text-muted d-flex justify-content-between align-items-center">
          <div className="small">
            {new Date(response.created_at).toLocaleString()}
          </div>
          <div className="d-flex align-items-center">
            <FaInfoCircle className="me-1" size={14} />
            <span className="small">{t('rag.aiGenerated')}</span>
          </div>
        </Card.Footer>
      </Card>
    </motion.div>
  );
};

export default RAGQueryResult;