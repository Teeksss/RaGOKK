// Last reviewed: 2025-04-30 12:48:55 UTC (User: TeeksssLLM)
// ... diğer importlar
import QuerySourceViewer, { QuerySource } from './QuerySourceViewer';

// QueryResults bileşen prop'ları
interface QueryResultsProps {
  result: {
    text: string;
    sources: QuerySource[];  // Kaynak dokümanlar eklendi
  };
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  queryId: string;
  className?: string;
}

const QueryResults: React.FC<QueryResultsProps> = ({
  result,
  isLoading = false,
  error = null,
  onRetry,
  queryId,
  className = '',
}) => {
  const { t } = useTranslation();
  
  // ... mevcut kodlar
  
  return (
    <div className={`query-results ${className}`}>
      <ContentLoader
        isLoading={isLoading}
        error={error}
        onRetry={onRetry}
      >
        <Card>
          <Card.Body>
            <div className="query-response">
              {renderMarkdown(result.text)}
            </div>
          </Card.Body>
          <Card.Footer className="d-flex justify-content-between border-top">
            <div className="actions d-flex gap-2">
              {/* ... mevcut butonlar */}
            </div>
            {result.sources && result.sources.length > 0 && (
              <Badge bg="info" className="d-flex align-items-center">
                <FaFileAlt className="me-1" />
                {t('query.sourcesCount', { count: result.sources.length })}
              </Badge>
            )}
          </Card.Footer>
        </Card>
        
        {/* Kaynak görüntüleyici bileşeni */}
        {result.sources && result.sources.length > 0 && (
          <QuerySourceViewer 
            sources={result.sources} 
            queryId={queryId}
            minScore={30}
            showScoreSlider={true}
          />
        )}
      </ContentLoader>
    </div>
  );
};