// Last reviewed: 2025-04-30 07:41:30 UTC (User: Teeksss)
import React, { useState, useEffect, useRef } from 'react';
import { Card, Button, Alert, Spinner, Badge } from 'react-bootstrap';
import { FaSyncAlt, FaSearch, FaRegCopy, FaExternalLinkAlt, FaInfoCircle } from 'react-icons/fa';
import { useToast } from '../../contexts/ToastContext';
import { useTranslation } from 'react-i18next';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import './StreamingQuery.css';

// Base WebSocket URL
const WS_BASE_URL = process.env.REACT_APP_WS_BASE_URL || 'ws://localhost:8000';

interface StreamingQueryResultProps {
  query: string;
  accessToken?: string;
  onComplete?: (answer: string) => void;
  onSourceClick?: (sourceId: string, documentId: string) => void;
  onRetry?: () => void;
  filterDocumentIds?: string[];
}

interface Source {
  id: string;
  documentId: string;
  title: string;
  content: string;
  page?: number;
  color?: string;
}

interface StreamingChunk {
  type: 'chunk' | 'info' | 'error';
  content: string;
  source_id?: string | null;
  current_references?: string[];
  done?: boolean;
  metadata?: any;
}

const StreamingQueryResult: React.FC<StreamingQueryResultProps> = ({
  query,
  accessToken,
  onComplete,
  onSourceClick,
  onRetry,
  filterDocumentIds = []
}) => {
  const { t } = useTranslation();
  const { showToast } = useToast();
  
  // State
  const [answer, setAnswer] = useState<string>('');
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [sourceMap, setSourceMap] = useState<Record<string, Source>>({});
  const [currentSourceId, setCurrentSourceId] = useState<string | null>(null);
  const [references, setReferences] = useState<string[]>([]);
  
  // WebSocket ref
  const socketRef = useRef<WebSocket | null>(null);
  
  // Result ref for scrolling
  const resultRef = useRef<HTMLDivElement>(null);
  
  // Color palette for sources
  const sourceColors = [
    'source-blue',
    'source-green',
    'source-red',
    'source-purple',
    'source-orange',
    'source-teal'
  ];
  
  // Start streaming on component mount
  useEffect(() => {
    startStreaming();
    
    return () => {
      // Clean up on component unmount
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
    };
  }, [query]);
  
  // Start WebSocket connection
  const startStreaming = () => {
    setAnswer('');
    setIsStreaming(true);
    setError(null);
    setCurrentSourceId(null);
    setReferences([]);
    
    // Build query params
    const params = new URLSearchParams();
    params.append('query', query);
    
    // Add document filters if provided
    if (filterDocumentIds && filterDocumentIds.length > 0) {
      params.append('filters', JSON.stringify({ document_ids: filterDocumentIds }));
    }
    
    try {
      // Create WebSocket connection
      const wsUrl = `${WS_BASE_URL}/api/v1/streaming/query?${params.toString()}`;
      socketRef.current = new WebSocket(wsUrl);
      
      // Connection opened
      socketRef.current.onopen = () => {
        // Send authentication token if provided
        if (accessToken) {
          socketRef.current?.send(JSON.stringify({ token: accessToken }));
        }
      };
      
      // Listen for messages
      socketRef.current.onmessage = (event) => {
        try {
          const data: StreamingChunk = JSON.parse(event.data);
          
          switch (data.type) {
            case 'chunk':
              // Append content to answer
              setAnswer(prev => prev + (data.content || ''));
              
              // Update source info
              if (data.source_id !== undefined) {
                setCurrentSourceId(data.source_id);
              }
              
              // Update references
              if (data.current_references) {
                setReferences(data.current_references);
              }
              
              // Stream completed
              if (data.done) {
                setIsStreaming(false);
                if (onComplete) {
                  onComplete(answer + (data.content || ''));
                }
              }
              break;
              
            case 'info':
              // Information message
              console.log('Info:', data.content);
              
              // Sources info
              if (data.metadata?.sources) {
                const sourcesMap: Record<string, Source> = {};
                
                data.metadata.sources.forEach((source: any, index: number) => {
                  const sourceId = String(index + 1);
                  sourcesMap[sourceId] = {
                    id: sourceId,
                    documentId: source.document_id || '',
                    title: source.title || `Source ${sourceId}`,
                    content: source.content || '',
                    page: source.metadata?.page_number,
                    color: sourceColors[index % sourceColors.length]
                  };
                });
                
                setSourceMap(sourcesMap);
              }
              break;
              
            case 'error':
              // Error message
              setError(data.content || 'An error occurred');
              setIsStreaming(false);
              break;
          }
          
          // Scroll to bottom if needed
          if (resultRef.current) {
            resultRef.current.scrollTop = resultRef.current.scrollHeight;
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
          setError('Error processing response');
          setIsStreaming(false);
        }
      };
      
      // Handle socket closing
      socketRef.current.onclose = (event) => {
        setIsStreaming(false);
        
        // Abnormal close
        if (event.code !== 1000 && !error) {
          setError(`Connection closed: ${event.reason || 'Unknown reason'}`);
        }
      };
      
      // Handle connection error
      socketRef.current.onerror = () => {
        setError('WebSocket connection error');
        setIsStreaming(false);
      };
      
    } catch (err) {
      console.error('Error setting up WebSocket connection:', err);
      setError('Failed to connect to server');
      setIsStreaming(false);
    }
  };
  
  // Copy result to clipboard
  const handleCopyClick = () => {
    navigator.clipboard.writeText(answer)
      .then(() => showToast('success', t('query.copied')))
      .catch(() => showToast('error', t('query.copyFailed')));
  };
  
  // Handle retry
  const handleRetry = () => {
    if (onRetry) {
      onRetry();
    } else {
      startStreaming();
    }
  };
  
  // Render source badge
  const renderSourceBadge = (sourceId: string) => {
    const source = sourceMap[sourceId];
    
    if (!source) return null;
    
    return (
      <Badge
        key={sourceId}
        className={`source-badge ${source.color || ''}`}
        onClick={() => onSourceClick && source.documentId && onSourceClick(sourceId, source.documentId)}
        style={{ cursor: onSourceClick ? 'pointer' : 'default' }}
      >
        {source.title}
        {source.page && ` (${t('query.page')} ${source.page})`}
      </Badge>
    );
  };
  
  return (
    <Card className="streaming-result mb-4">
      <Card.Header className="d-flex justify-content-between align-items-center">
        <div>
          <FaSearch className="me-2" />
          <strong>{t('query.question')}</strong>
        </div>
        
        {isStreaming && (
          <div className="d-flex align-items-center">
            <Spinner animation="border" size="sm" className="me-2" />
            <span>{t('query.generating')}</span>
          </div>
        )}
      </Card.Header>
      
      <Card.Body>
        {/* Query */}
        <div className="query-text mb-3">
          <p>{query}</p>
        </div>
        
        {/* Error */}
        {error && (
          <Alert variant="danger" className="mb-3">
            <Alert.Heading>{t('query.error')}</Alert.Heading>
            <p>{error}</p>
            <div className="d-flex justify-content-end">
              <Button
                variant="outline-danger"
                size="sm"
                onClick={handleRetry}
              >
                <FaSyncAlt className="me-2" />
                {t('query.retry')}
              </Button>
            </div>
          </Alert>
        )}
        
        {/* Answer */}
        {(answer || isStreaming) && (
          <div className="answer-container">
            <div className="answer-header d-flex justify-content-between align-items-center mb-2">
              <h5>
                <FaInfoCircle className="me-2" />
                {t('query.answer')}
              </h5>
              
              <Button
                variant="outline-secondary"
                size="sm"
                onClick={handleCopyClick}
                disabled={!answer || isStreaming}
              >
                <FaRegCopy className="me-2" />
                {t('query.copy')}
              </Button>
            </div>
            
            {/* Answer content with source highlighting */}
            <div 
              className={`answer-content ${currentSourceId ? `highlight-source-${currentSourceId}` : ''}`}
              ref={resultRef}
            >
              <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkBreaks]}
                rehypePlugins={[rehypeHighlight]}
              >
                {answer || ' '}
              </ReactMarkdown>
              
              {/* Blinking cursor when streaming */}
              {isStreaming && <span className="cursor-blink">▌</span>}
            </div>
            
            {/* Current source indicator */}
            {currentSourceId && sourceMap[currentSourceId] && (
              <div className={`current-source-indicator ${sourceMap[currentSourceId].color || ''}`}>
                <small>
                  {t('query.currentSource')}: {sourceMap[currentSourceId].title}
                  {sourceMap[currentSourceId].page && ` (${t('query.page')} ${sourceMap[currentSourceId].page})`}
                </small>
              </div>
            )}
            
            {/* References */}
            {references.length > 0 && (
              <div className="references-container mt-3">
                <small className="text-muted">{t('query.references')}:</small>
                <div className="d-flex flex-wrap gap-2 mt-2">
                  {references.map(sourceId => renderSourceBadge(sourceId))}
                </div>
              </div>
            )}
          </div>
        )}
      </Card.Body>
      
      {/* Loading indicator */}
      {isStreaming && (
        <Card.Footer className="text-center">
          <Spinner animation="grow" size="sm" className="me-2" />
          <small className="text-muted">{t('query.thinkingAndWriting')}</small>
        </Card.Footer>
      )}
    </Card>
  );
};

export default StreamingQueryResult;