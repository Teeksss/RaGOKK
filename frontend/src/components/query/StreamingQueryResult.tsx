// Last reviewed: 2025-04-30 07:12:47 UTC (User: Teeksss)
import React, { useState, useEffect, useRef } from 'react';
import { Card, Spinner, Badge, Alert, Button } from 'react-bootstrap';
import { FaSync, FaQuestionCircle, FaInfoCircle, FaExternalLinkAlt } from 'react-icons/fa';
import { useTranslation } from 'react-i18next';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { useToast } from '../../contexts/ToastContext';

// WebSocket URL
const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';

interface StreamingQueryResultProps {
  query: string;
  filters?: any;
  searchType?: string;
  sources?: any[];
  onComplete?: (answer: string, references: string[]) => void;
  onViewDocument?: (documentId: string) => void;
  token?: string;  // JWT token
}

interface SourceInfo {
  document_id: string;
  title: string;
  page_number?: number;
  content: string;
  source_id: string;
}

const StreamingQueryResult: React.FC<StreamingQueryResultProps> = ({ 
  query, 
  filters = {}, 
  searchType = 'hybrid',
  sources = [],
  onComplete,
  onViewDocument,
  token
}) => {
  const { t } = useTranslation();
  const { showToast } = useToast();
  
  // State
  const [answer, setAnswer] = useState<string>('');
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [socketConnected, setSocketConnected] = useState<boolean>(false);
  const [activeSourceId, setActiveSourceId] = useState<string | null>(null);
  const [currentReferences, setCurrentReferences] = useState<string[]>([]);
  const [sourceMap, setSourceMap] = useState<Record<string, SourceInfo>>({});
  
  // WebSocket referansı
  const socketRef = useRef<WebSocket | null>(null);
  
  // Renk sınıfları
  const sourceColorClasses = [
    'text-primary',
    'text-success',
    'text-danger',
    'text-warning',
    'text-info',
    'text-dark',
    'text-secondary'
  ];
  
  // WebSocket bağlantısını kur
  useEffect(() => {
    startStreaming();
    
    // Temizleme
    return () => {
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
    };
  }, [query, filters, searchType]);
  
  // Kaynak haritası oluştur
  useEffect(() => {
    if (sources && sources.length > 0) {
      const sourceMapping: Record<string, SourceInfo> = {};
      
      sources.forEach((source, index) => {
        const sourceId = String(index + 1);
        sourceMapping[sourceId] = {
          document_id: source.document_id || '',
          title: source.document_title || 'Belge',
          page_number: source.metadata?.page_number,
          content: source.content || '',
          source_id: sourceId
        };
      });
      
      setSourceMap(sourceMapping);
    }
  }, [sources]);
  
  // Streaming başlat
  const startStreaming = () => {
    // Önceki bağlantıyı temizle
    if (socketRef.current) {
      socketRef.current.close();
    }
    
    // State'i temizle
    setAnswer('');
    setError(null);
    setIsStreaming(true);
    setSocketConnected(false);
    setActiveSourceId(null);
    setCurrentReferences([]);
    
    try {
      // Sorgu parametreleri
      const queryParams = new URLSearchParams({
        query: query
      });
      
      // Ek filtreleri ekle
      if (Object.keys(filters).length > 0) {
        queryParams.append('filters', JSON.stringify(filters));
      }
      
      // Arama türünü ekle
      if (searchType) {
        queryParams.append('search_type', searchType);
      }
      
      // WebSocket bağlantısı oluştur
      const socketUrl = `${WS_URL}/api/v1/streaming/query?${queryParams.toString()}`;
      socketRef.current = new WebSocket(socketUrl);
      
      // Token ekle
      if (token) {
        socketRef.current.onopen = () => {
          if (socketRef.current) {
            socketRef.current.send(JSON.stringify({ token }));
          }
        };
      }
      
      // Bağlantı açıldı
      socketRef.current.onopen = () => {
        setSocketConnected(true);
      };
      
      // Mesaj geldi
      socketRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // Mesaj türüne göre işle
          if (data.type === 'chunk') {
            // Yanıt parçası
            setAnswer(prev => prev + (data.content || ''));
            
            // Kaynaklar
            if (data.current_references) {
              setCurrentReferences(data.current_references);
            }
            
            // Aktif kaynak
            if (data.source_id !== undefined) {
              setActiveSourceId(data.source_id);
            }
            
            // Tamamlandı mı?
            if (data.done) {
              setIsStreaming(false);
              if (onComplete) {
                onComplete(answer + (data.content || ''), data.current_references || []);
              }
            }
          } else if (data.type === 'info') {
            // Bilgi mesajı
            console.log('Info:', data.content);
          } else if (data.type === 'error') {
            // Hata mesajı
            setError(data.content || 'An error occurred');
            setIsStreaming(false);
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
          setError('Error parsing response data');
          setIsStreaming(false);
        }
      };
      
      // Bağlantı kapandı
      socketRef.current.onclose = (event) => {
        setSocketConnected(false);
        setIsStreaming(false);
        
        // Anormal kapanma
        if (event.code !== 1000) {
          setError(`WebSocket closed abnormally: ${event.reason || 'Unknown reason'}`);
        }
      };
      
      // Bağlantı hatası
      socketRef.current.onerror = () => {
        setSocketConnected(false);
        setIsStreaming(false);
        setError('WebSocket connection error');
      };
      
    } catch (err) {
      setError('Error setting up WebSocket connection');
      setIsStreaming(false);
      console.error('WebSocket error:', err);
    }
  };
  
  // Streaming yanıtı işle ve kaynakları renklendirme
  const processStreamingAnswer = () => {
    if (!answer) return '';
    
    // Kaynak referanslarını renklendirme
    let processedText = answer;
    
    Object.keys(sourceMap).forEach((sourceId, index) => {
      const colorClass = sourceColorClasses[index % sourceColorClasses.length];
      const pattern = new RegExp(`\\[${sourceId}\\]`, 'g');
      processedText = processedText.replace(
        pattern, 
        `<span class="${colorClass} source-reference" data-source="${sourceId}">[${sourceId}]</span>`
      );
    });
    
    return processedText;
  };
  
  // Referans tıklama işleyicisi
  useEffect(() => {
    const handleReferenceClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (target.classList.contains('source-reference')) {
        const sourceId = target.getAttribute('data-source');
        if (sourceId && sourceMap[sourceId] && onViewDocument) {
          onViewDocument(sourceMap[sourceId].document_id);
        }
      }
    };
    
    document.addEventListener('click', handleReferenceClick);
    
    return () => {
      document.removeEventListener('click', handleReferenceClick);
    };
  }, [sourceMap, onViewDocument]);
  
  // Yeniden deneme
  const handleRetry = () => {
    startStreaming();
  };
  
  return (
    <Card className="mb-4 shadow-sm streaming-query-result">
      <Card.Header className="d-flex justify-content-between align-items-center bg-light">
        <div className="d-flex align-items-center">
          <FaQuestionCircle className="text-primary me-2" />
          <h5 className="mb-0">{t('query.question')}</h5>
        </div>
        
        {isStreaming && (
          <Badge bg="info" className="d-flex align-items-center p-2">
            <Spinner animation="border" size="sm" className="me-2" />
            {t('query.streaming')}
          </Badge>
        )}
      </Card.Header>
      
      <Card.Body>
        {/* Soru */}
        <div className="query-question mb-4">
          <p className="lead">{query}</p>
        </div>
        
        {/* Hata mesajı */}
        {error && (
          <Alert variant="danger">
            <Alert.Heading>{t('query.error')}</Alert.Heading>
            <p>{error}</p>
            <div className="d-flex justify-content-end">
              <Button 
                variant="outline-danger" 
                size="sm"
                onClick={handleRetry}
              >
                <FaSync className="me-1" /> {t('common.tryAgain')}
              </Button>
            </div>
          </Alert>
        )}
        
        {/* Yanıt yanıtı */}
        {(answer || isStreaming) && (
          <div className="query-answer mb-4">
            <Card.Subtitle className="mb-3 d-flex align-items-center">
              <FaInfoCircle className="text-primary me-2" />
              {t('query.answer')}
              
              {isStreaming && (
                <Spinner animation="border" size="sm" className="ms-2" />
              )}
            </Card.Subtitle>
            
            <div 
              className={`answer-content ${activeSourceId ? `highlight-source-${activeSourceId}` : ''}`}
              dangerouslySetInnerHTML={{ __html: processStreamingAnswer() }}
            />
            
            {/* Kaynak göstergesi */}
            {activeSourceId && sourceMap[activeSourceId] && (
              <div className="source-indicator mt-3">
                <div className="small text-muted">
                  {t('query.currentSource')}:
                  <Badge bg="light" text="dark" className="ms-2">
                    {sourceMap[activeSourceId].title}
                    {sourceMap[activeSourceId].page_number && ` (${t('query.page')} ${sourceMap[activeSourceId].page_number})`}
                  </Badge>
                </div>
              </div>
            )}
            
            {/* Aktif referanslar */}
            {currentReferences.length > 0 && (
              <div className="current-references mt-3">
                <div className="small">
                  {t('query.references')}:
                  {currentReferences.map((refId, index) => (
                    sourceMap[refId] && (
                      <Badge 
                        key={refId}
                        bg="light" 
                        text="dark"
                        className="ms-2 mb-1 p-2"
                        onClick={() => onViewDocument && onViewDocument(sourceMap[refId].document_id)}
                        style={{ cursor: 'pointer' }}
                      >
                        <span className={sourceColorClasses[parseInt(refId) % sourceColorClasses.length]}>
                          [{refId}]
                        </span>
                        {' '}
                        {sourceMap[refId].title}
                        {sourceMap[refId].page_number && ` (${t('query.page')} ${sourceMap[refId].page_number})`}
                      </Badge>
                    )
                  ))}
                </div>
              </div>
            )}
            
            {/* Streaming durumu */}
            {isStreaming && (
              <div className="streaming-status mt-3">
                <div className="d-flex align-items-center small text-muted">
                  <Spinner animation="grow" size="sm" variant="primary" className="me-2" />
                  {socketConnected ? t('query.generatingResponse') : t('query.connecting')}
                </div>
              </div>
            )}
          </div>
        )}
      </Card.Body>
    </Card>
  );
};

export default StreamingQueryResult;