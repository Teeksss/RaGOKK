// Last reviewed: 2025-04-30 12:48:55 UTC (User: TeeksssLLM)
import React, { useState, useCallback } from 'react';
import { Form, Button, Card, Row, Col, Alert, Accordion } from 'react-bootstrap';
import { FaSave, FaUndo, FaCog, FaPlus, FaTrash, FaExclamationTriangle } from 'react-icons/fa';
import { useTranslation } from 'react-i18next';
import { RetrievalConfig, DEFAULT_RETRIEVAL_CONFIG } from '../../services/retrievalStrategyService';

interface RetrievalConfigEditorProps {
  initialConfig?: Partial<RetrievalConfig>;
  onSave: (config: RetrievalConfig) => void;
  isLoading?: boolean;
  isAdmin?: boolean;
}

const RetrievalConfigEditor: React.FC<RetrievalConfigEditorProps> = ({
  initialConfig,
  onSave,
  isLoading = false,
  isAdmin = false
}) => {
  const { t } = useTranslation();
  const [config, setConfig] = useState<RetrievalConfig>({
    ...DEFAULT_RETRIEVAL_CONFIG,
    ...initialConfig
  });
  const [advanced, setAdvanced] = useState<boolean>(false);
  
  // Temel config değişikliği
  const handleChange = useCallback((path: string, value: any) => {
    setConfig(prev => {
      const newConfig = { ...prev };
      
      // Nokta notasyonu ile nested property'lere eriş
      const keys = path.split('.');
      let current = newConfig as any;
      
      // Son key'e kadar ilerle
      for (let i = 0; i < keys.length - 1; i++) {
        if (!current[keys[i]]) {
          current[keys[i]] = {};
        }
        current = current[keys[i]];
      }
      
      // Son key'e değeri ata
      current[keys[keys.length - 1]] = value;
      
      return newConfig;
    });
  }, []);
  
  // Sayısal input değerini doğrulayıp ayarla
  const handleNumberChange = useCallback((path: string, value: string, min: number = 0, max: number = Infinity) => {
    const numValue = Number(value);
    
    if (!isNaN(numValue)) {
      const constrainedValue = Math.max(min, Math.min(max, numValue));
      handleChange(path, constrainedValue);
    }
  }, [handleChange]);
  
  // Checkbox değişimini handle et
  const handleCheckboxChange = useCallback((path: string, checked: boolean) => {
    handleChange(path, checked);
  }, [handleChange]);
  
  // Select değişimini handle et
  const handleSelectChange = useCallback((path: string, value: string) => {
    handleChange(path, value);
  }, [handleChange]);
  
  // Fallback adımı ekle
  const addFallbackStep = useCallback(() => {
    setConfig(prev => {
      const steps = [...(prev.fallback_strategies?.relaxation_steps || [])];
      
      // Yeni adım için default değerler
      const lastStep = steps[steps.length - 1];
      const newStep = {
        min_score: lastStep ? Math.max(0, lastStep.min_score - 0.1) : 0.5,
        top_k: lastStep ? lastStep.top_k + 5 : 10
      };
      
      // Yeni adımı ekle
      steps.push(newStep);
      
      return {
        ...prev,
        fallback_strategies: {
          ...(prev.fallback_strategies || DEFAULT_RETRIEVAL_CONFIG.fallback_strategies!),
          relaxation_steps: steps
        }
      };
    });
  }, []);
  
  // Fallback adımını kaldır
  const removeFallbackStep = useCallback((index: number) => {
    setConfig(prev => {
      const steps = [...(prev.fallback_strategies?.relaxation_steps || [])];
      
      if (index >= 0 && index < steps.length) {
        steps.splice(index, 1);
      }
      
      return {
        ...prev,
        fallback_strategies: {
          ...(prev.fallback_strategies || DEFAULT_RETRIEVAL_CONFIG.fallback_strategies!),
          relaxation_steps: steps
        }
      };
    });
  }, []);
  
  // Varsayılan ayarlara sıfırla
  const resetToDefault = useCallback(() => {
    setConfig(DEFAULT_RETRIEVAL_CONFIG);
  }, []);
  
  // Yapılandırmayı kaydet
  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    onSave(config);
  }, [config, onSave]);
  
  // Multi-query etkinleştirildiğinde uyarı göster
  const showMultiQueryWarning = config.multi_query_variants && config.multi_query_count > 1;
  
  return (
    <Form onSubmit={handleSubmit}>
      <Card className="mb-4">
        <Card.Header>
          <h5 className="mb-0">{t('retrievalConfig.basicSettings')}</h5>
        </Card.Header>
        <Card.Body>
          <Row className="mb-3">
            <Col md={6}>
              <Form.Group controlId="topK">
                <Form.Label>{t('retrievalConfig.topK.label')}</Form.Label>
                <Form.Control
                  type="number"
                  value={config.top_k}
                  onChange={(e) => handleNumberChange('top_k', e.target.value, 1, 100)}
                  min={1}
                  max={100}
                  disabled={isLoading}
                />
                <Form.Text className="text-muted">
                  {t('retrievalConfig.topK.help')}
                </Form.Text>
              </Form.Group>
            </Col>
            <Col md={6}>
              <Form.Group controlId="minScore">
                <Form.Label>{t('retrievalConfig.minScore.label')}</Form.Label>
                <Form.Control
                  type="number"
                  value={config.min_score}
                  onChange={(e) => handleNumberChange('min_score', e.target.value, 0, 1)}
                  step="0.01"
                  min={0}
                  max={1}
                  disabled={isLoading}
                />
                <Form.Text className="text-muted">
                  {t('retrievalConfig.minScore.help')}
                </Form.Text>
              </Form.Group>
            </Col>
          </Row>
          
          <Form.Group className="mb-3">
            <Form.Check
              type="switch"
              id="useReranker"
              label={t('retrievalConfig.useReranker.label')}
              checked={config.use_reranker}
              onChange={(e) => handleCheckboxChange('use_reranker', e.target.checked)}
              disabled={isLoading}
            />
            <Form.Text className="text-muted">
              {t('retrievalConfig.useReranker.help')}
            </Form.Text>
          </Form.Group>
          
          {config.use_reranker && (
            <Row>
              <Col md={6}>
                <Form.Group controlId="rerankerTopK">
                  <Form.Label>{t('retrievalConfig.rerankerTopK.label')}</Form.Label>
                  <Form.Control
                    type="number"
                    value={config.reranker_top_k}
                    onChange={(e) => handleNumberChange('reranker_top_k', e.target.value, 1, 100)}
                    min={1}
                    max={100}
                    disabled={isLoading}
                  />
                  <Form.Text className="text-muted">
                    {t('retrievalConfig.rerankerTopK.help')}
                  </Form.Text>
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group controlId="rerankerThreshold">
                  <Form.Label>{t('retrievalConfig.rerankerThreshold.label')}</Form.Label>
                  <Form.Control
                    type="number"
                    value={config.reranker_threshold}
                    onChange={(e) => handleNumberChange('reranker_threshold', e.target.value, 0, 1)}
                    step="0.01"
                    min={0}
                    max={1}
                    disabled={isLoading}
                  />
                  <Form.Text className="text-muted">
                    {t('retrievalConfig.rerankerThreshold.help')}
                  </Form.Text>
                </Form.Group>
              </Col>
            </Row>
          )}
        </Card.Body>
      </Card>
      
      <Button
        variant="secondary"
        className="mb-4 d-flex align-items-center"
        onClick={() => setAdvanced(!advanced)}
        disabled={isLoading}
        aria-expanded={advanced}
      >
        <FaCog className="me-2" />
        {advanced ? t('retrievalConfig.hideAdvanced') : t('retrievalConfig.showAdvanced')}
      </Button>
      
      {advanced && (
        <>
          <Card className="mb-4">
            <Card.Header>
              <h5 className="mb-0">{t('retrievalConfig.queryExpansion.title')}</h5>
            </Card.Header>
            <Card.Body>
              <Form.Group className="mb-3">
                <Form.Label>{t('retrievalConfig.queryExpansion.method.label')}</Form.Label>
                <Form.Select
                  value={config.query_expansion_method}
                  onChange={(e) => handleSelectChange('query_expansion_method', e.target.value)}
                  disabled={isLoading || !isAdmin}
                >
                  <option value="none">{t('retrievalConfig.queryExpansion.method.none')}</option>
                  <option value="wordnet">{t('retrievalConfig.queryExpansion.method.wordnet')}</option>
                  <option value="conceptnet">{t('retrievalConfig.queryExpansion.method.conceptnet')}</option>
                  <option value="gpt">{t('retrievalConfig.queryExpansion.method.gpt')}</option>
                  <option value="hybrid">{t('retrievalConfig.queryExpansion.method.hybrid')}</option>
                </Form.Select>
                <Form.Text className="text-muted">
                  {t('retrievalConfig.queryExpansion.method.help')}
                </Form.Text>
              </Form.Group>
              
              {config.query_expansion_method !== 'none' && (
                <Form.Group className="mb-3">
                  <Form.Label>{t('retrievalConfig.queryExpansion.depth.label')}</Form.Label>
                  <Form.Control
                    type="number"
                    value={config.query_expansion_depth}
                    onChange={(e) => handleNumberChange('query_expansion_depth', e.target.value, 1, 3)}
                    min={1}
                    max={3}
                    disabled={isLoading || !isAdmin}
                  />
                  <Form.Text className="text-muted">
                    {t('retrievalConfig.queryExpansion.depth.help')}
                  </Form.Text>
                </Form.Group>
              )}
              
              <Form.Group className="mb-3">
                <Form.Check
                  type="switch"
                  id="multiQueryVariants"
                  label={t('retrievalConfig.multiQueryVariants.label')}
                  checked={config.multi_query_variants}
                  onChange={(e) => handleCheckboxChange('multi_query_variants', e.target.checked)}
                  disabled={isLoading || !isAdmin}
                />
                <Form.Text className="text-muted">
                  {t('retrievalConfig.multiQueryVariants.help')}
                </Form.Text>
              </Form.Group>
              
              {config.multi_query_variants && (
                <Form.Group className="mb-3">
                  <Form.Label>{t('retrievalConfig.multiQueryCount.label')}</Form.Label>
                  <Form.Control
                    type="number"
                    value={config.multi_query_count}
                    onChange={(e) => handleNumberChange('multi_query_count', e.target.value, 1, 5)}
                    min={1}
                    max={5}
                    disabled={isLoading || !isAdmin}
                  />
                  <Form.Text className="text-muted">
                    {t('retrievalConfig.multiQueryCount.help')}
                  </Form.Text>
                </Form.Group>
              )}
              
              {showMultiQueryWarning && (
                <Alert variant="warning">
                  <FaExclamationTriangle className="me-2" />
                  {t('retrievalConfig.multiQueryWarning')}
                </Alert>
              )}
            </Card.Body>
          </Card>
          
          <Card className="mb-4">
            <Card.Header>
              <h5 className="mb-0">{t('retrievalConfig.fallbackStrategies.title')}</h5>
            </Card.Header>
            <Card.Body>
              <Form.Group className="mb-3">
                <Form.Label>{t('retrievalConfig.fallbackStrategies.minResultsThreshold.label')}</Form.Label>
                <Form.Control
                  type="number"
                  value={config.fallback_strategies?.min_results_threshold}
                  onChange={(e) => handleNumberChange('fallback_strategies.min_results_threshold', e.target.value, 1, 10)}
                  min={1}
                  max={10}
                  disabled={isLoading}
                />
                <Form.Text className="text-muted">
                  {t('retrievalConfig.fallbackStrategies.minResultsThreshold.help')}
                </Form.Text>
              </Form.Group>
              
              <Form.Group className="mb-3">
                <Form.Check
                  type="switch"
                  id="useKeywordSearchFallback"
                  label={t('retrievalConfig.fallbackStrategies.useKeywordSearch.label')}
                  checked={config.fallback_strategies?.use_keyword_search_fallback}
                  onChange={(e) => handleCheckboxChange('fallback_strategies.use_keyword_search_fallback', e.target.checked)}
                  disabled={isLoading}
                />
                <Form.Text className="text-muted">
                  {t('retrievalConfig.fallbackStrategies.useKeywordSearch.help')}
                </Form.Text>
              </Form.Group>
              
              <div className="mb-3">
                <h6>{t('retrievalConfig.fallbackStrategies.relaxationSteps.title')}</h6>
                <p className="text-muted small">
                  {t('retrievalConfig.fallbackStrategies.relaxationSteps.help')}
                </p>
                
                {config.fallback_strategies?.relaxation_steps?.map((step, index) => (
                  <Card key={index} className="mb-2">
                    <Card.Body className="py-2">
                      <Row className="align-items-center">
                        <Col>
                          <div className="d-flex align-items-center">
                            <span className="badge bg-secondary me-2">{index + 1}</span>
                            <span>
                              {t('retrievalConfig.fallbackStrategies.relaxationSteps.step', {
                                minScore: (step.min_score * 100).toFixed(0),
                                topK: step.top_k
                              })}
                            </span>
                          </div>
                        </Col>
                        <Col xs="auto">
                          <Button
                            variant="outline-danger"
                            size="sm"
                            onClick={() => removeFallbackStep(index)}
                            disabled={isLoading}
                          >
                            <FaTrash />
                          </Button>
                        </Col>
                      </Row>
                    </Card.Body>
                  </Card>
                ))}
                
                <Button
                  variant="outline-secondary"
                  size="sm"
                  onClick={addFallbackStep}
                  disabled={isLoading || (config.fallback_strategies?.relaxation_steps?.length || 0) >= 3}
                  className="mt-2"
                >
                  <FaPlus className="me-1" />
                  {t('retrievalConfig.fallbackStrategies.relaxationSteps.add')}
                </Button>
              </div>
            </Card.Body>
          </Card>
        </>
      )}
      
      <div className="d-flex justify-content-between mt-4">
        <Button
          variant="outline-secondary"
          type="button"
          onClick={resetToDefault}
          disabled={isLoading}
          className="d-flex align-items-center"
        >
          <FaUndo className="me-2" />
          {t('common.resetToDefault')}
        </Button>
        
        <Button
          variant="primary"
          type="submit"
          disabled={isLoading}
          className="d-flex align-items-center"
        >
          <FaSave className="me-2" />
          {t('common.save')}
        </Button>
      </div>
    </Form>
  );
};

export default RetrievalConfigEditor;