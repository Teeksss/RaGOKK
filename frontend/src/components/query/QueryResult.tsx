// Last reviewed: 2025-04-30 06:38:22 UTC (User: Teeksss)
import React, { useState, useEffect, useRef } from 'react';
import { Card, Badge, Button, Collapse, Alert, Tabs, Tab, OverlayTrigger, Tooltip } from 'react-bootstrap';
import { 
  FaQuestionCircle, 
  FaInfoCircle, 
  FaBookOpen, 
  FaChevronDown, 
  FaChevronUp, 
  FaExternalLinkAlt, 
  FaRegLightbulb,
  FaCode,
  FaChartBar,
  FaRegThumbsUp,
  FaClock,
  FaPercentage,
  FaTags
} from 'react-icons/fa';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { useTranslation } from 'react-i18next';
import { formatDistanceToNow } from 'date-fns';
import { tr, enUS } from 'date-fns/locale';

import QueryFeedback from './QueryFeedback';

interface SourceMetadata {
  segment_id: string;
  segment_index: number;
  segment_type: string;
  source_filename: string;
  page_number?: number;
  section_title?: string;
  upload_user_id: string;
  document_tags?: string[];
  char_count?: number;
  word_count?: number;
  [key: string]: any;
}

interface Source {
  id: string;
  document_id?: string;
  document_title?: string;
  content?: string;
  content_snippet?: string;
  similarity_score?: number;
  similarity_percentage?: number;
  page_number?: number;
  retriever?: string;
  metadata?: SourceMetadata;
  dense_score?: number;
  sparse_score?: number;
  truncated?: boolean;
}

interface RetrieverStats {
  search_type: string;
  processing_time_ms: number;
  most_effective_retriever: string;
  result_count: number;
  hybrid_method?: string;
}

interface QueryResultProps {
  id: string;
  question: string;
  answer?: string;
  sources?: Source[];
  created_at: string;
  processing_time_ms?: number;
  has_error: boolean;
  error_message?: string;
  onViewDocument?: (documentId: string) => void;
  retriever_stats?: RetrieverStats;
  metadata?: Record<string, any>;
  onRetry?: () => void;
}

// SourceCard bileşeni - her bir kaynak için görselleştirme
const SourceCard: React.FC<{
  source: Source;
  index: number;
  sourceColors: string[];
  onViewDocument?: (documentId: string) => void;
}> = ({ source, index, sourceColors, onViewDocument }) => {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState<boolean>(false);
  
  // Retriever badge rengini belirle
  const getRetrieverBadgeVariant = (retriever?: string): string => {
    if (!retriever) return "secondary";
    
    if (retriever === "dense") return "primary";
    if (retriever === "sparse") return "success";
    if (retriever.includes("+")) return "info";
    return "secondary";
  };
  
  // Retriever adını görüntüle
  const getRetrieverName = (retriever?: string): string => {
    if (!retriever) return t('query.retriever.unknown');
    
    if (retriever === "dense") return t('query.retriever.semantic');
    if (retriever === "sparse") return t('query.retriever.keyword');
    if (retriever.includes("+")) return t('query.retriever.hybrid');
    return retriever;
  };
  
  // Skor temelli arkaplan rengi (daha yüksek score = daha koyu arkaplan)
  const getScoreBackground = (score?: number): string => {
    if (!score || score < 0.5) return "rgba(0,0,0,0)";
    // Belli bir eşiğin (0.5) üzerindeki skorlar için açık sarıdan koyuya
    const intensity = Math.min(100, Math.round((score - 0.5) * 200));
    return `rgba(255, 251, 235, ${intensity/100})`;
  };
  
  return (
    <Card 
      key={source.id} 
      className="mb-3 source-card" 
      style={{
        backgroundColor: getScoreBackground(source.similarity_score),
        borderLeft: `4px solid ${sourceColors[index % sourceColors.length]}`
      }}
    >
      <Card.Header 
        className="d-flex justify-content-between align-items-center py-2"
      >
        <div className="d-flex align-items-center flex-grow-1">
          <span className="me-2 source-number fw-bold" style={{ color: sourceColors[index % sourceColors.length] }}>
            [{index + 1}]
          </span>
          <div className="source-title-container">
            <strong className="d-block">{source.document_title || t('query.unknownDocument')}</strong>
            <div className="source-badges d-flex flex-wrap gap-2 align-items-center mt-1">
              {source.page_number && (
                <OverlayTrigger
                  placement="top"
                  overlay={<Tooltip>{t('query.pageTooltip')}</Tooltip>}
                >
                  <Badge bg="light" text="dark" className="me-1">
                    <FaBookOpen className="me-1" size={10} />
                    {t('query.page')} {source.page_number}
                  </Badge>
                </OverlayTrigger>
              )}
              
              {source.metadata?.section_title && (
                <OverlayTrigger
                  placement="top"
                  overlay={<Tooltip>{t('query.sectionTooltip')}</Tooltip>}
                >
                  <Badge bg="light" text="dark" className="me-1">
                    <FaRegLightbulb className="me-1" size={10} />
                    {source.metadata.section_title}
                  </Badge>
                </OverlayTrigger>
              )}
              
              {source.metadata?.segment_type && (
                <OverlayTrigger
                  placement="top"
                  overlay={<Tooltip>{t('query.segmentTypeTooltip')}</Tooltip>}
                >
                  <Badge bg="light" text="dark" className="me-1 d-none d-sm-inline-block">
                    <FaCode className="me-1" size={10} />
                    {source.metadata.segment_type}
                  </Badge>
                </OverlayTrigger>
              )}
              
              {source.retriever && (
                <OverlayTrigger
                  placement="top"
                  overlay={<Tooltip>{t('query.retrieverTooltip')}</Tooltip>}
                >
                  <Badge bg={getRetrieverBadgeVariant(source.retriever)} className="me-1">
                    {getRetrieverName(source.retriever)}
                  </Badge>
                </OverlayTrigger>
              )}
              
              {source.similarity_percentage !== undefined && (
                <OverlayTrigger
                  placement="top"
                  overlay={<Tooltip>{t('query.similarityTooltip')}</Tooltip>}
                >
                  <Badge bg="warning" text="dark" className="me-1">
                    <FaPercentage className="me-1" size={10} />
                    {source.similarity_percentage}%
                  </Badge>
                </OverlayTrigger>
              )}
              
              {source.metadata?.document_tags && source.metadata.document_tags.length > 0 && (
                <div className="d-none d-md-flex flex-wrap gap-1">
                  {source.metadata.document_tags.slice(0, 2).map((tag, tagIndex) => (
                    <OverlayTrigger
                      key={tagIndex}
                      placement="top"
                      overlay={<Tooltip>{t('document.tagTooltip')}</Tooltip>}
                    >
                      <Badge key={tagIndex} bg="light" text="dark" pill>
                        <FaTags className="me-1" size={8} />
                        {tag}
                      </Badge>
                    </OverlayTrigger>
                  ))}
                  {source.metadata.document_tags.length > 2 && (
                    <Badge bg="light" text="dark" pill>
                      +{source.metadata.document_tags.length - 2}
                    </Badge>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
        
        <div className="d-flex align-items-center ms-2">
          {source.document_id && onViewDocument && (
            <Button 
              variant="outline-primary" 
              size="sm"
              className="me-1"
              onClick={() => onViewDocument(source.document_id!)}
            >
              {t('query.viewDocument')}
            </Button>
          )}
          
          <Button
            variant="outline-secondary"
            size="sm"
            onClick={() => setExpanded(!expanded)}
            aria-expanded={expanded}
          >
            {expanded ? <FaChevronUp /> : <FaChevronDown />}
          </Button>
        </div>
      </Card.Header>
      
      <Collapse in={expanded}>
        <div>
          <Card.Body>
            <div className="source-content">
              {source.content || source.content_snippet || t('query.noContent')}
              {source.truncated && (
                <div className="text-muted mt-2 small">
                  <em>{t('query.contentTruncated')}</em>
                </div>
              )}
            </div>
            
            {source.metadata && (
              <div className="source-metadata mt-3 pt-2 border-top">
                <h6>{t('query.metadata')}</h6>
                <div className="row">
                  {source.metadata.source_filename && (
                    <div className="col-md-6 mb-1">
                      <small className="text-muted">{t('document.details.fileName')}:</small>{' '}
                      <small>{source.metadata.source_filename}</small>
                    </div>
                  )}
                  
                  {source.metadata.char_count && (
                    <div className="col-md-6 mb-1">
                      <small className="text-muted">{t('query.charCount')}:</small>{' '}
                      <small>{source.metadata.char_count.toLocaleString()}</small>
                    </div>
                  )}
                  
                  {source.metadata.word_count && (
                    <div className="col-md-6 mb-1">
                      <small className="text-muted">{t('query.wordCount')}:</small>{' '}
                      <small>{source.metadata.word_count.toLocaleString()}</small>
                    </div>
                  )}
                  
                  {source.metadata.upload_user_id && (
                    <div className="col-md-6 mb-1">
                      <small className="text-muted">{t('document.details.owner')}:</small>{' '}
                      <small>{source.metadata.upload_user_id}</small>
                    </div>
                  )}
                </div>
                
                {/* Hybrid arama için skor detayları */}
                {(source.dense_score !== undefined || source.sparse_score !== undefined) && (
                  <div className="score-details mt-2">
                    <h6>{t('query.scoreDetails')}</h6>
                    <div className="row">
                      {source.dense_score !== undefined && (
                        <div className="col-md-6 mb-1">
                          <small className="text-muted">{t('query.denseScore')}:</small>{' '}
                          <small>{(source.dense_score * 100).toFixed(1)}%</small>
                        </div>
                      )}
                      
                      {source.sparse_score !== undefined && (
                        <div className="col-md-6 mb-1">
                          <small className="text-muted">{t('query.sparseScore')}:</small>{' '}
                          <small>{(source.sparse_score * 100).toFixed(1)}%</small>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </Card.Body>
        </div>
      </Collapse>
      
      {!expanded && (
        <Card.Footer className="py-1 px-3">
          <div className="d-flex justify-content-between align-items-center">
            <small className="text-muted">{t('query.clickToExpand')}</small>
            
            {source.similarity_percentage !== undefined && (
              <small className="text-muted">
                {t('query.relevance')}: {source.similarity_percentage}%
              </small>
            )}
          </div>
        </Card.Footer>
      )}
    </Card>
  );
};

// Ana QueryResult bileşeni
const QueryResult: React.FC<QueryResultProps> = ({
  id,
  question,
  answer,
  sources = [],
  created_at,
  processing_time_ms,
  has_error,
  error_message,
  onViewDocument,
  retriever_stats,
  metadata,
  onRetry
}) => {
  const { t, i18n } = useTranslation();
  const [showSources, setShowSources] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<string>("answer");
  const answerRef = useRef<HTMLDivElement>(null);
  
  // date-fns için locale ayarı
  const dateLocale = i18n.language === 'tr' ? tr : enUS;
  
  // Yanıt içindeki kaynak referansları için renk kodları (en fazla 10 kaynak)
  const sourceColors = [
    '#007bff', '#28a745', '#dc3545', '#ffc107', '#17a2b8',
    '#6610f2', '#fd7e14', '#20c997', '#e83e8c', '#6c757d'
  ];
  
  // Cevabı işle - kaynak referanslarını vurgula
  const processAnswer = (text?: string): string => {
    if (!text) return '';
    
    // [1], [2] gibi referansları renklendir
    let processedText = text;
    sources.forEach((_, index) => {
      const sourceNum = index + 1;
      const regex = new RegExp(`\\[${sourceNum}\\]`, 'g');
      processedText = processedText.replace(
        regex, 
        `<span class="source-reference" style="color: ${sourceColors[index % sourceColors.length]}; font-weight: bold;">[${sourceNum}]</span>`
      );
    });
    
    return processedText;
  };
  
  // İşlenmiş cevap
  const processedAnswer = processAnswer(answer);
  
  // Kaynaklar bölümü görünürlüğünü izle
  useEffect(() => {
    // İlk kaynağı otomatik genişletmek için seçenek eklenebilir
    if (sources.length > 0 && !has_error) {
      setShowSources(true);
    }
  }, [sources, has_error]);
  
  // Kaynak referanslarına tıklandığında ilgili kaynağa kaydırma
  useEffect(() => {
    if (answerRef.current) {
      const sourceReferences = answerRef.current.querySelectorAll('.source-reference');
      
      sourceReferences.forEach((element, index) => {
        element.addEventListener('click', () => {
          // İlgili kaynak kartını bul ve görünür değilse görünür yap
          const sourceId = `source-card-${index}`;
          const sourceElement = document.getElementById(sourceId);
          
          if (sourceElement) {
            // Kaynaklar görünür değilse görünür yap
            if (!showSources) {
              setShowSources(true);
              // DOM güncellemesi için biraz bekle sonra kaydır
              setTimeout(() => {
                sourceElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
              }, 300);
            } else {
              sourceElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
          }
        });
      });
    }
  }, [processedAnswer, showSources]);
  
  return (
    <Card className="mb-4 shadow-sm query-result">
      <Card.Header className="bg-light">
        <div className="d-flex justify-content-between align-items-center">
          <div className="d-flex align-items-center">
            <FaQuestionCircle className="text-primary me-2" />
            <h5 className="mb-0">{t('query.question')}</h5>
          </div>
          <div>
            <small className="text-muted">
              {formatDistanceToNow(new Date(created_at), { addSuffix: true, locale: dateLocale })}
            </small>
            {processing_time_ms && (
              <OverlayTrigger
                placement="top"
                overlay={<Tooltip>{t('query.processingTimeTooltip')}</Tooltip>}
              >
                <Badge bg="secondary" className="ms-2">
                  <FaClock className="me-1" size={10} />
                  {(processing_time_ms / 1000).toFixed(2)} s
                </Badge>
              </OverlayTrigger>
            )}
          </div>
        </div>
      </Card.Header>
      
      <Card.Body>
        <div className="query-question mb-4">
          <p className="lead">{question}</p>
          
          {/* Yeniden yazılmış sorgu varsa göster */}
          {metadata && metadata.original_question && metadata.rewritten_question && metadata.original_question !== metadata.rewritten_question && (
            <div className="rewritten-query mt-2 small">
              <Badge bg="info" className="me-2">{t('query.rewrittenQuery')}</Badge>
              <em className="text-muted">{metadata.rewritten_question}</em>
            </div>
          )}
        </div>
        
        {has_error ? (
          <Alert variant="danger">
            <Alert.Heading>{t('query.errorOccurred')}</Alert.Heading>
            <p>{error_message || t('query.genericError')}</p>
            {onRetry && (
              <div className="d-flex justify-content-end">
                <Button variant="outline-danger" size="sm" onClick={onRetry}>
                  {t('query.tryAgain')}
                </Button>
              </div>
            )}
          </Alert>
        ) : (
          <>
            <Tabs
              activeKey={activeTab}
              onSelect={(k) => setActiveTab(k || "answer")}
              className="mb-3"
            >
              <Tab eventKey="answer" title={<span><FaInfoCircle className="me-1" />{t('query.answer')}</span>}>
                <div className="query-answer mb-4">
                  <div className="markdown-content" ref={answerRef}>
                    <ReactMarkdown 
                      children={processedAnswer}
                      remarkPlugins={[remarkGfm]}
                      rehypePlugins={[rehypeHighlight]}
                      components={{
                        // Özel bileşen eklemeleri
                        a: ({ node, ...props }) => (
                          <a target="_blank" rel="noopener noreferrer" {...props}>
                            {props.children} <FaExternalLinkAlt size={12} />
                          </a>
                        ),
                        pre: ({ node, ...props }) => (
                          <pre className="pre-code bg-light p-3 rounded" {...props} />
                        ),
                        code: ({ node, inline, ...props }) => (
                          inline ? 
                            <code className="code-inline bg-light px-1 rounded" {...props} /> : 
                            <code {...props} />
                        )
                      }}
                    />
                  </div>
                </div>
                
                {/* Geri bildirim bileşeni */}
                <div className="query-feedback-container mt-4 pt-3 border-top">
                  <h6>{t('feedback.title')}</h6>
                  <QueryFeedback queryId={id} variant="thumbs" />
                </div>
              </Tab>
              
              <Tab eventKey="sources" title={<span><FaBookOpen className="me-1" />{t('query.sources')} ({sources.length})</span>}>
                <div className="query-sources">
                  {sources.length > 0 ? (
                    <div className="source-list">
                      {sources.map((source, index) => (
                        <SourceCard
                          key={source.id}
                          source={source}
                          index={index}
                          sourceColors={sourceColors}
                          onViewDocument={onViewDocument}
                        />
                      ))}
                    </div>
                  ) : (
                    <Alert variant="info">
                      {t('query.noSources')}
                    </Alert>
                  )}
                </div>
              </Tab>
              
              <Tab eventKey="stats" title={<span><FaChartBar className="me-1" />{t('query.stats')}</span>}>
                <div className="query-stats">
                  <Card className="mb-3">
                    <Card.Header>
                      <h6 className="mb-0">{t('query.retrievalStats')}</h6>
                    </Card.Header>
                    <Card.Body>
                      {retriever_stats ? (
                        <div className="row">
                          <div className="col-md-6 mb-3">
                            <h6>{t('query.searchType')}</h6>
                            <Badge bg="primary" className="px-3 py-2">
                              {retriever_stats.search_type}
                            </Badge>
                          </div>
                          
                          <div className="col-md-6 mb-3">
                            <h6>{t('query.mostEffectiveRetriever')}</h6>
                            <Badge 
                              bg={
                                retriever_stats.most_effective_retriever === "dense" ? "primary" : 
                                retriever_stats.most_effective_retriever === "sparse" ? "success" :
                                retriever_stats.most_effective_retriever === "hybrid" ? "info" : "secondary"
                              }
                              className="px-3 py-2"
                            >
                              {retriever_stats.most_effective_retriever}
                            </Badge>
                          </div>
                          
                          {retriever_stats.search_type === "hybrid" && retriever_stats.hybrid_method && (
                            <div className="col-md-6 mb-3">
                              <h6>{t('query.hybridMethod')}</h6>
                              <Badge bg="dark" className="px-3 py-2">
                                {retriever_stats.hybrid_method}
                              </Badge>
                            </div>
                          )}
                          
                          <div className="col-md-6 mb-3">
                            <h6>{t('query.searchTime')}</h6>
                            <Badge bg="secondary" className="px-3 py-2">
                              {retriever_stats.processing_time_ms} ms
                            </Badge>
                          </div>
                          
                          <div className="col-md-6 mb-3">
                            <h6>{t('query.resultCount')}</h6>
                            <Badge bg="info" className="px-3 py-2">
                              {retriever_stats.result_count}
                            </Badge>
                          </div>
                        </div>
                      ) : (
                        <Alert variant="warning">
                          {t('query.statsNotAvailable')}
                        </Alert>
                      )}
                    </Card.Body>
                  </Card>
                  
                  {/* Token kullanımı bilgisi */}
                  {metadata && metadata.prompt_tokens && (
                    <Card>
                      <Card.Header>
                        <h6 className="mb-0">{t('query.tokenUsage')}</h6>
                      </Card.Header>
                      <Card.Body>
                        <div className="row">
                          <div className="col-md-4 mb-3">
                            <h6>{t('query.promptTokens')}</h6>
                            <Badge bg="primary" className="px-3 py-2">
                              {metadata.prompt_tokens}
                            </Badge>
                          </div>
                          
                          <div className="col-md-4 mb-3">
                            <h6>{t('query.completionTokens')}</h6>
                            <Badge bg="success" className="px-3 py-2">
                              {metadata.completion_tokens}
                            </Badge>
                          </div>
                          
                          <div className="col-md-4 mb-3">
                            <h6>{t('query.totalTokens')}</h6>
                            <Badge bg="info" className="px-3 py-2">
                              {metadata.total_tokens}
                            </Badge>
                          </div>
                          
                          {metadata.context_tokens && (
                            <div className="col-md-4 mb-3">
                              <h6>{t('query.contextTokens')}</h6>
                              <Badge bg="secondary" className="px-3 py-2">
                                {metadata.context_tokens}
                              </Badge>
                            </div>
                          )}
                          
                          {metadata.used_results_count && (
                            <div className="col-md-4 mb-3">
                              <h6>{t('query.usedSourcesCount')}</h6>
                              <Badge bg="warning" text="dark" className="px-3 py-2">
                                {metadata.used_results_count}
                              </Badge>
                            </div>
                          )}
                        </div>
                      </Card.Body>
                    </Card>
                  )}
                </div>
              </Tab>
            </Tabs>
          </>
        )}
      </Card.Body>
    </Card>
  );
};

export default QueryResult;