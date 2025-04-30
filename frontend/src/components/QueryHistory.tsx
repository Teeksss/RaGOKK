// Last reviewed: 2025-04-30 05:29:35 UTC (User: Teeksss)
import React, { useState, useEffect } from 'react';
import { Card, ListGroup, Button, Badge, Spinner, Form, Alert } from 'react-bootstrap';
import { FaHistory, FaTrash, FaSearch, FaChevronDown, FaChevronUp, FaShare } from 'react-icons/fa';
import { useTranslation } from 'react-i18next';
import API from '../api/api';
import { useToast } from '../contexts/ToastContext';
import { formatDistanceToNow } from 'date-fns';
import { tr, enUS } from 'date-fns/locale';

interface Query {
  id: string;
  question: string;
  answer?: string;
  created_at: string;
  has_error: boolean;
  processing_time_ms?: number;
}

interface QueryHistoryProps {
  onSelectQuery?: (question: string) => void;
  maxItems?: number;
  showFull?: boolean;
  userId?: string;
}

const QueryHistory: React.FC<QueryHistoryProps> = ({ 
  onSelectQuery, 
  maxItems = 10,
  showFull = false,
  userId
}) => {
  const { t, i18n } = useTranslation();
  const { showToast } = useToast();
  
  // State
  const [queries, setQueries] = useState<Query[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<boolean>(showFull);
  const [selectedQueries, setSelectedQueries] = useState<Set<string>>(new Set());
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [page, setPage] = useState<number>(1);
  const [hasMore, setHasMore] = useState<boolean>(true);
  
  // Sorguları yükle
  const loadQueries = async (resetExisting: boolean = false, searchQuery: string = searchTerm) => {
    if (resetExisting) {
      setPage(1);
      setQueries([]);
    }
    
    const currentPage = resetExisting ? 1 : page;
    setLoading(true);
    setError(null);
    
    try {
      // API çağrısı ile sorgu geçmişini al
      const params = new URLSearchParams();
      params.append('page', currentPage.toString());
      params.append('page_size', maxItems.toString());
      
      if (searchQuery) {
        params.append('search', searchQuery);
      }
      
      if (userId) {
        params.append('user_id', userId);
      }
      
      const response = await API.get(`/queries/history?${params.toString()}`);
      
      if (response.data && response.data.items) {
        if (resetExisting) {
          setQueries(response.data.items);
        } else {
          setQueries(prev => [...prev, ...response.data.items]);
        }
        
        // Daha fazla sonuç var mı kontrol et
        setHasMore(response.data.items.length === maxItems);
        
        // Sayfa numarasını güncelle
        if (!resetExisting && response.data.items.length > 0) {
          setPage(currentPage + 1);
        }
      }
    } catch (err: any) {
      console.error('Error loading query history:', err);
      setError(err.response?.data?.detail || t('queryHistory.loadError'));
      showToast('error', t('queryHistory.loadError'));
    } finally {
      setLoading(false);
      setIsSearching(false);
    }
  };
  
  // İlk yükleme
  useEffect(() => {
    loadQueries(true);
  }, []);
  
  // Arama fonksiyonu
  const handleSearch = () => {
    setIsSearching(true);
    loadQueries(true, searchTerm);
  };
  
  // Daha fazla sorgu yükle
  const loadMore = () => {
    loadQueries();
  };
  
  // Sorgu seçme işlemleri
  const toggleSelectQuery = (id: string) => {
    const newSelected = new Set(selectedQueries);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedQueries(newSelected);
  };
  
  // Tüm sorguları seç/kaldır
  const toggleSelectAll = () => {
    if (selectedQueries.size > 0) {
      setSelectedQueries(new Set());
    } else {
      const allIds = queries.map(q => q.id);
      setSelectedQueries(new Set(allIds));
    }
  };
  
  // Seçili sorguları sil
  const deleteSelectedQueries = async () => {
    if (selectedQueries.size === 0) return;
    
    try {
      // API çağrısı ile seçili sorguları sil
      const queryIds = Array.from(selectedQueries);
      await API.post('/queries/delete-multiple', { query_ids: queryIds });
      
      // Silinen sorguları listeden kaldır
      setQueries(prev => prev.filter(query => !selectedQueries.has(query.id)));
      
      // Seçili sorguları temizle
      setSelectedQueries(new Set());
      
      showToast('success', t('queryHistory.deleteSuccess'));
    } catch (err: any) {
      console.error('Error deleting queries:', err);
      showToast('error', t('queryHistory.deleteError'));
    }
  };
  
  // Date-fns için dil ayarı
  const dateLocale = i18n.language === 'tr' ? tr : enUS;
  
  // Formatlama fonksiyonları
  const formatTime = (dateString: string) => {
    try {
      return formatDistanceToNow(new Date(dateString), { addSuffix: true, locale: dateLocale });
    } catch (e) {
      return dateString;
    }
  };
  
  // Tarih gruplandırması
  const groupQueriesByDate = () => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    yesterday.setHours(0, 0, 0, 0);
    
    const lastWeek = new Date();
    lastWeek.setDate(lastWeek.getDate() - 7);
    lastWeek.setHours(0, 0, 0, 0);
    
    const grouped: { [key: string]: Query[] } = {
      today: [],
      yesterday: [],
      lastWeek: [],
      older: []
    };
    
    queries.forEach(query => {
      const queryDate = new Date(query.created_at);
      
      if (queryDate >= today) {
        grouped.today.push(query);
      } else if (queryDate >= yesterday) {
        grouped.yesterday.push(query);
      } else if (queryDate >= lastWeek) {
        grouped.lastWeek.push(query);
      } else {
        grouped.older.push(query);
      }
    });
    
    return grouped;
  };
  
  // Sorgu gruplama
  const groupedQueries = groupQueriesByDate();
  
  // Gösterilecek sorgu sayısı
  const visibleQueries = expanded ? queries : queries.slice(0, Math.min(5, queries.length));
  
  return (
    <Card className="shadow-sm">
      <Card.Header className="d-flex justify-content-between align-items-center">
        <div className="d-flex align-items-center">
          <FaHistory className="me-2 text-primary" />
          <h5 className="mb-0">{t('queryHistory.title')}</h5>
        </div>
        {selectedQueries.size > 0 && (
          <Button 
            variant="outline-danger" 
            size="sm" 
            onClick={deleteSelectedQueries}
            title={t('queryHistory.deleteSelected')}
          >
            <FaTrash className="me-1" /> {t('queryHistory.delete')} ({selectedQueries.size})
          </Button>
        )}
      </Card.Header>
      
      <Card.Body className="p-0">
        {/* Arama alanı */}
        <div className="p-3 border-bottom">
          <Form onSubmit={(e) => { e.preventDefault(); handleSearch(); }}>
            <div className="d-flex">
              <Form.Control
                type="text"
                placeholder={t('queryHistory.searchPlaceholder')}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                disabled={loading}
                className="me-2"
              />
              <Button 
                variant="primary" 
                onClick={handleSearch} 
                disabled={loading || isSearching}
              >
                {isSearching ? (
                  <Spinner animation="border" size="sm" />
                ) : (
                  <FaSearch />
                )}
              </Button>
            </div>
          </Form>
        </div>
        
        {/* Hata mesajı */}
        {error && (
          <Alert variant="danger" className="m-3">
            {error}
          </Alert>
        )}
        
        {/* Sorgu listesi */}
        {loading && queries.length === 0 ? (
          <div className="text-center p-4">
            <Spinner animation="border" variant="primary" />
            <p className="mt-2 text-muted">{t('queryHistory.loading')}</p>
          </div>
        ) : queries.length === 0 ? (
          <div className="text-center p-4">
            <p className="text-muted">{t('queryHistory.noQueries')}</p>
          </div>
        ) : (
          <div className="overflow-auto query-history-list" style={{ maxHeight: showFull ? 'none' : '500px' }}>
            <ListGroup variant="flush">
              {/* Bugün */}
              {groupedQueries.today.length > 0 && (
                <>
                  <div className="bg-light p-2 ps-3 small text-muted">
                    {t('queryHistory.groupToday')}
                  </div>
                  {groupedQueries.today.map(query => (
                    <QueryHistoryItem 
                      key={query.id}
                      query={query}
                      onSelect={onSelectQuery}
                      isSelected={selectedQueries.has(query.id)}
                      onToggleSelect={() => toggleSelectQuery(query.id)}
                      formatTime={formatTime}
                    />
                  ))}
                </>
              )}
              
              {/* Dün */}
              {groupedQueries.yesterday.length > 0 && (
                <>
                  <div className="bg-light p-2 ps-3 small text-muted">
                    {t('queryHistory.groupYesterday')}
                  </div>
                  {groupedQueries.yesterday.map(query => (
                    <QueryHistoryItem 
                      key={query.id}
                      query={query}
                      onSelect={onSelectQuery}
                      isSelected={selectedQueries.has(query.id)}
                      onToggleSelect={() => toggleSelectQuery(query.id)}
                      formatTime={formatTime}
                    />
                  ))}
                </>
              )}
              
              {/* Geçen hafta */}
              {groupedQueries.lastWeek.length > 0 && (
                <>
                  <div className="bg-light p-2 ps-3 small text-muted">
                    {t('queryHistory.groupLastWeek')}
                  </div>
                  {groupedQueries.lastWeek.map(query => (
                    <QueryHistoryItem 
                      key={query.id}
                      query={query}
                      onSelect={onSelectQuery}
                      isSelected={selectedQueries.has(query.id)}
                      onToggleSelect={() => toggleSelectQuery(query.id)}
                      formatTime={formatTime}
                    />
                  ))}
                </>
              )}
              
              {/* Daha eski */}
              {groupedQueries.older.length > 0 && (
                <>
                  <div className="bg-light p-2 ps-3 small text-muted">
                    {t('queryHistory.groupOlder')}
                  </div>
                  {groupedQueries.older.map(query => (
                    <QueryHistoryItem 
                      key={query.id}
                      query={query}
                      onSelect={onSelectQuery}
                      isSelected={selectedQueries.has(query.id)}
                      onToggleSelect={() => toggleSelectQuery(query.id)}
                      formatTime={formatTime}
                    />
                  ))}
                </>
              )}
              
              {/* Daha fazla yükle butonu */}
              {hasMore && (
                <div className="text-center p-3 border-top">
                  <Button 
                    variant="outline-primary" 
                    size="sm" 
                    onClick={loadMore}
                    disabled={loading}
                  >
                    {loading ? (
                      <Spinner animation="border" size="sm" />
                    ) : (
                      <>{t('queryHistory.loadMore')}</>
                    )}
                  </Button>
                </div>
              )}
            </ListGroup>
          </div>
        )}
      </Card.Body>
      
      {/* Genişlet/Daralt butonu */}
      {!showFull && queries.length > 5 && (
        <Card.Footer className="text-center p-2">
          <Button 
            variant="link" 
            size="sm" 
            onClick={() => setExpanded(!expanded)}
            className="text-decoration-none"
          >
            {expanded ? (
              <><FaChevronUp className="me-1" /> {t('queryHistory.showLess')}</>
            ) : (
              <><FaChevronDown className="me-1" /> {t('queryHistory.showMore')}</>
            )}
          </Button>
        </Card.Footer>
      )}
    </Card>
  );
};

// Sorgu öğesi bileşeni
interface QueryHistoryItemProps {
  query: Query;
  onSelect?: (question: string) => void;
  isSelected: boolean;
  onToggleSelect: () => void;
  formatTime: (dateString: string) => string;
}

const QueryHistoryItem: React.FC<QueryHistoryItemProps> = ({
  query,
  onSelect,
  isSelected,
  onToggleSelect,
  formatTime
}) => {
  const { t } = useTranslation();
  
  return (
    <ListGroup.Item className="py-3 px-3 query-history-item">
      <div className="d-flex align-items-start">
        <Form.Check
          type="checkbox"
          className="mt-1 me-2"
          checked={isSelected}
          onChange={onToggleSelect}
          aria-label={t('queryHistory.selectQuery')}
        />
        <div className="flex-grow-1 overflow-hidden">
          <div className="mb-1 query-history-text">{query.question}</div>
          <div className="d-flex mt-2 align-items-center gap-1">
            <small className="text-muted query-history-date">{formatTime(query.created_at)}</small>
            
            {query.has_error && (
              <Badge bg="danger" pill className="ms-2">
                {t('queryHistory.error')}
              </Badge>
            )}
            
            {query.processing_time_ms && (
              <small className="text-muted ms-2">
                {query.processing_time_ms} ms
              </small>
            )}
          </div>
        </div>
        <div className="ms-2">
          <Button
            variant="outline-primary"
            size="sm"
            onClick={() => onSelect && onSelect(query.question)}
            title={t('queryHistory.reuse')}
            className="touch-target d-flex align-items-center justify-content-center"
          >
            <FaShare />
          </Button>
        </div>
      </div>
    </ListGroup.Item>
  );
};

export default QueryHistory;