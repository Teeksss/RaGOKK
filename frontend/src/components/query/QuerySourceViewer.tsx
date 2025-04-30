// Last reviewed: 2025-04-30 12:48:55 UTC (User: TeeksssLLM)
import React, { useState, useMemo, useCallback } from 'react';
import { Card, Badge, Button, Collapse, Nav, Tab, Row, Col, Form } from 'react-bootstrap';
import { FaFileAlt, FaLink, FaChevronDown, FaChevronUp, FaStar, FaExternalLinkAlt } from 'react-icons/fa';
import { useTranslation } from 'react-i18next';
import { useDocument } from '../../services/queryService';
import { formatDate, formatBytes } from '../../utils/formatters';
import { analyticsService, EventCategory } from '../../services/analyticsService';

export interface QuerySource {
  id: string;
  documentId: string;
  documentTitle: string;
  chunkId: string;
  score: number;
  text: string;
  page?: number;
  metadata?: Record<string, any>;
}

interface QuerySourceViewerProps {
  sources: QuerySource[];
  queryId: string;
  className?: string;
  minScore?: number;
  showScoreSlider?: boolean;
}

const QuerySourceViewer: React.FC<QuerySourceViewerProps> = ({ 
  sources, 
  queryId,
  className = '',
  minScore = 0,
  showScoreSlider = true
}) => {
  const { t } = useTranslation();
  const [activeKey, setActiveKey] = useState<string>(sources.length > 0 ? sources[0].id : '');
  const [expanded, setExpanded] = useState<boolean>(false);
  const [scoreThreshold, setScoreThreshold] = useState<number>(minScore);
  
  // Normalize scores to a 0-100 scale for better readability
  const normalizedSources = useMemo(() => {
    if (sources.length === 0) return [];
    
    const maxScore = Math.max(...sources.map(s => s.score));
    const minScore = Math.min(...sources.map(s => s.score));
    const range = maxScore - minScore;
    
    return sources.map(source => ({
      ...source,
      normalizedScore: range > 0 
        ? Math.round(((source.score - minScore) / range) * 100) 
        : 100
    }));
  }, [sources]);
  
  // Filter sources based on score threshold
  const filteredSources = useMemo(() => {
    return normalizedSources.filter(source => source.normalizedScore >= scoreThreshold);
  }, [normalizedSources, scoreThreshold]);
  
  // Get the active source
  const activeSource = useMemo(() => {
    return filteredSources.find(source => source.id === activeKey);
  }, [filteredSources, activeKey]);
  
  // Get document details for the active source
  const { data: documentDetails } = useDocument(activeSource?.documentId);
  
  // Handle source selection
  const handleSourceSelect = useCallback((sourceId: string) => {
    setActiveKey(sourceId);
    
    // Track analytics
    analyticsService.trackEvent({
      category: EventCategory.QUERY,
      action: 'ViewSource',
      label: sourceId,
      dimensions: {
        queryId
      }
    });
  }, [queryId]);
  
  // Toggle expanded state
  const toggleExpanded = useCallback(() => {
    setExpanded(prev => !prev);
    
    analyticsService.trackEvent({
      category: EventCategory.INTERACTION,
      action: expanded ? 'CollapseSourcesPanel' : 'ExpandSourcesPanel',
      dimensions: {
        queryId
      }
    });
  }, [expanded, queryId]);
  
  // Handle score threshold change
  const handleScoreChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    setScoreThreshold(Number(event.target.value));
    
    analyticsService.trackEvent({
      category: EventCategory.INTERACTION,
      action: 'AdjustSourceScoreThreshold',
      value: Number(event.target.value),
      dimensions: {
        queryId
      }
    });
  }, [queryId]);
  
  // Render confidence badge with appropriate color
  const renderConfidenceBadge = useCallback((score: number) => {
    let variant = 'secondary';
    
    if (score >= 90) variant = 'success';
    else if (score >= 70) variant = 'info';
    else if (score >= 50) variant = 'warning';
    else variant = 'danger';
    
    return (
      <Badge bg={variant} className="ms-2 align-middle">
        {t('query.sourceConfidence')}: {score}%
      </Badge>
    );
  }, [t]);
  
  // If there are no sources, don't render anything
  if (sources.length === 0) {
    return null;
  }
  
  return (
    <Card className={`query-source-viewer mt-4 ${className}`}>
      <Card.Header className="d-flex justify-content-between align-items-center">
        <div className="d-flex align-items-center">
          <FaFileAlt className="me-2" />
          <h5 className="mb-0">{t('query.sourceDocuments')}</h5>
          <Badge bg="primary" className="ms-2">{filteredSources.length}/{sources.length}</Badge>
        </div>
        <div className="d-flex align-items-center">
          <Button 
            variant="link" 
            className="text-decoration-none p-0 ms-2"
            onClick={toggleExpanded}
            aria-expanded={expanded}
          >
            {expanded ? (
              <>
                {t('common.collapse')}
                <FaChevronUp className="ms-1" />
              </>
            ) : (
              <>
                {t('common.expand')}
                <FaChevronDown className="ms-1" />
              </>
            )}
          </Button>
        </div>
      </Card.Header>
      
      <Collapse in={expanded}>
        <div>
          {showScoreSlider && (
            <Card.Body className="border-bottom pt-3 pb-3">
              <Form.Group controlId="scoreThreshold">
                <Form.Label>
                  {t('query.scoreThreshold')}: {scoreThreshold}%
                </Form.Label>
                <Form.Range
                  min={0}
                  max={100}
                  value={scoreThreshold}
                  onChange={handleScoreChange}
                  className="mt-1"
                />
              </Form.Group>
            </Card.Body>
          )}
          
          <Tab.Container activeKey={activeKey} onSelect={(k) => k && handleSourceSelect(k)}>
            <Row className="g-0">
              <Col md={4}>
                <div className="source-list p-0 border-end">
                  <Nav variant="pills" className="flex-column">
                    {filteredSources.map(source => (
                      <Nav.Item key={source.id}>
                        <Nav.Link 
                          eventKey={source.id} 
                          className="d-flex justify-content-between align-items-center"
                        >
                          <div className="source-title text-truncate">
                            {source.documentTitle}
                            {source.page && <small className="ms-1 text-muted">p. {source.page}</small>}
                          </div>
                          <div className="source-score">
                            {renderConfidenceBadge(source.normalizedScore)}
                          </div>
                        </Nav.Link>
                      </Nav.Item>
                    ))}
                  </Nav>
                </div>
              </Col>
              <Col md={8}>
                <Tab.Content>
                  {filteredSources.map(source => (
                    <Tab.Pane key={source.id} eventKey={source.id}>
                      <div className="source-content p-3">
                        <div className="source-header mb-3">
                          <h6 className="fw-bold mb-2">{source.documentTitle}</h6>
                          <div className="source-meta d-flex flex-wrap gap-3">
                            {source.page && (
                              <div className="source-page">
                                <small>
                                  <strong>{t('document.page')}:</strong> {source.page}
                                </small>
                              </div>
                            )}
                            <div className="source-chunk">
                              <small>
                                <strong>{t('document.chunkId')}:</strong> {source.chunkId}
                              </small>
                            </div>
                            <div className="source-score">
                              <small>
                                <strong>{t('query.score')}:</strong> {source.normalizedScore}% ({source.score.toFixed(4)})
                              </small>
                            </div>
                            <div className="ms-auto">
                              <Button
                                variant="outline-primary"
                                size="sm"
                                href={`/documents/${source.documentId}`}
                                target="_blank"
                                className="d-flex align-items-center"
                              >
                                <FaExternalLinkAlt className="me-1" />
                                {t('common.openDocument')}
                              </Button>
                            </div>
                          </div>
                        </div>
                        
                        <div className="source-text bg-light p-3 rounded">
                          {source.text}
                        </div>
                        
                        {documentDetails && (
                          <div className="document-details mt-3 small">
                            <Row>
                              <Col md={6}>
                                <dl className="row mb-0">
                                  <dt className="col-sm-4">{t('document.type')}</dt>
                                  <dd className="col-sm-8">
                                    <Badge bg="secondary">{documentDetails.type}</Badge>
                                  </dd>
                                  
                                  <dt className="col-sm-4">{t('document.created')}</dt>
                                  <dd className="col-sm-8">{formatDate(documentDetails.createdAt)}</dd>
                                  
                                  {documentDetails.owner && (
                                    <>
                                      <dt className="col-sm-4">{t('document.owner')}</dt>
                                      <dd className="col-sm-8">{documentDetails.owner.name}</dd>
                                    </>
                                  )}
                                </dl>
                              </Col>
                              <Col md={6}>
                                <dl className="row mb-0">
                                  {documentDetails.size && (
                                    <>
                                      <dt className="col-sm-4">{t('document.size')}</dt>
                                      <dd className="col-sm-8">{formatBytes(documentDetails.size)}</dd>
                                    </>
                                  )}
                                  
                                  {documentDetails.pages && (
                                    <>
                                      <dt className="col-sm-4">{t('document.pages')}</dt>
                                      <dd className="col-sm-8">{documentDetails.pages}</dd>
                                    </>
                                  )}
                                  
                                  {documentDetails.tags && documentDetails.tags.length > 0 && (
                                    <>
                                      <dt className="col-sm-4">{t('document.tags')}</dt>
                                      <dd className="col-sm-8">
                                        {documentDetails.tags.map(tag => (
                                          <Badge key={tag} bg="info" className="me-1">{tag}</Badge>
                                        ))}
                                      </dd>
                                    </>
                                  )}
                                </dl>
                              </Col>
                            </Row>
                          </div>
                        )}
                      </div>
                    </Tab.Pane>
                  ))}
                </Tab.Content>
              </Col>
            </Row>
          </Tab.Container>
        </div>
      </Collapse>
      
      {!expanded && activeSource && (
        <Card.Footer className="source-summary d-flex justify-content-between align-items-center">
          <div className="d-flex align-items-center">
            <FaStar className="text-warning me-2" />
            <span className="small">
              {t('query.topSource')}: <strong>{activeSource.documentTitle}</strong>
              {activeSource.page && <span className="text-muted"> ({t('document.page')} {activeSource.page})</span>}
              {renderConfidenceBadge(activeSource.normalizedScore)}
            </span>
          </div>
          <Button
            variant="outline-secondary"
            size="sm"
            href={`/documents/${activeSource.documentId}`}
            target="_blank"
            className="d-flex align-items-center"
          >
            <FaLink className="me-1" />
            {t('common.viewDocument')}
          </Button>
        </Card.Footer>
      )}
    </Card>
  );
};

export default React.memo(QuerySourceViewer);