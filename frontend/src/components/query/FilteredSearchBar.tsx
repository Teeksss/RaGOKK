// Last reviewed: 2025-04-30 07:00:22 UTC (User: Teeksss)
import React, { useState, useEffect } from 'react';
import { Form, Button, InputGroup, Dropdown, Badge, Spinner, Accordion } from 'react-bootstrap';
import { FaSearch, FaFilter, FaTags, FaFile, FaCalendarAlt, FaImage, FaBolt } from 'react-icons/fa';
import { useTranslation } from 'react-i18next';
import API from '../../api/api';
import { useToast } from '../../contexts/ToastContext';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';

interface DocumentFilters {
  tags?: string[];
  document_types?: string[];
  document_ids?: string[];
  date_after?: Date;
  date_before?: Date;
}

interface FilteredSearchBarProps {
  onSearch: (question: string, filters: DocumentFilters, useMultimodal: boolean) => void;
  loading?: boolean;
  defaultQuestion?: string;
  defaultFilters?: DocumentFilters;
}

const FilteredSearchBar: React.FC<FilteredSearchBarProps> = ({
  onSearch,
  loading = false,
  defaultQuestion = '',
  defaultFilters
}) => {
  const { t } = useTranslation();
  const { showToast } = useToast();
  
  // Durum
  const [question, setQuestion] = useState<string>(defaultQuestion);
  const [showFilters, setShowFilters] = useState<boolean>(false);
  const [filters, setFilters] = useState<DocumentFilters>(defaultFilters || {});
  const [availableTags, setAvailableTags] = useState<string[]>([]);
  const [availableTypes, setAvailableTypes] = useState<string[]>([]);
  const [isLoadingTags, setIsLoadingTags] = useState<boolean>(false);
  const [isLoadingTypes, setIsLoadingTypes] = useState<boolean>(false);
  const [useMultimodal, setUseMultimodal] = useState<boolean>(false);
  
  // Filtre bilgilerini yükle
  useEffect(() => {
    loadFilterData();
  }, []);
  
  // Varsayılan filtreler değişirse güncelle
  useEffect(() => {
    if (defaultFilters) {
      setFilters(defaultFilters);
    }
  }, [defaultFilters]);
  
  // Belge filtreleme bilgilerini yükle
  const loadFilterData = async () => {
    try {
      // Etiketleri yükle
      setIsLoadingTags(true);
      const tagsResponse = await API.get('/filtered-queries/document-tags');
      setAvailableTags(tagsResponse.data);
      setIsLoadingTags(false);
      
      // Belge türlerini yükle
      setIsLoadingTypes(true);
      const typesResponse = await API.get('/filtered-queries/document-types');
      setAvailableTypes(typesResponse.data);
      setIsLoadingTypes(false);
      
    } catch (err: any) {
      console.error('Error loading filter data:', err);
      showToast('error', t('query.filters.loadError'));
      setIsLoadingTags(false);
      setIsLoadingTypes(false);
    }
  };
  
  // Etiket değişimi
  const handleTagChange = (tag: string) => {
    setFilters(prev => {
      const currentTags = prev.tags || [];
      
      // Tag varsa kaldır yoksa ekle
      if (currentTags.includes(tag)) {
        return {
          ...prev,
          tags: currentTags.filter(t => t !== tag)
        };
      } else {
        return {
          ...prev,
          tags: [...currentTags, tag]
        };
      }
    });
  };
  
  // Belge türü değişimi
  const handleTypeChange = (type: string) => {
    setFilters(prev => {
      const currentTypes = prev.document_types || [];
      
      // Type varsa kaldır yoksa ekle
      if (currentTypes.includes(type)) {
        return {
          ...prev,
          document_types: currentTypes.filter(t => t !== type)
        };
      } else {
        return {
          ...prev,
          document_types: [...currentTypes, type]
        };
      }
    });
  };
  
  // Tarih değişimi
  const handleDateChange = (field: 'date_after' | 'date_before', date: Date | null) => {
    setFilters(prev => ({
      ...prev,
      [field]: date || undefined
    }));
  };
  
  // Aramayı temizle
  const handleClearSearch = () => {
    setQuestion('');
    setFilters({});
    setUseMultimodal(false);
  };
  
  // Aramayı gönder
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!question.trim()) {
      showToast('warning', t('query.emptyQuestion'));
      return;
    }
    
    // Aktif filtreleri kontrol et
    const hasActiveFilters = Object.values(filters).some(val => 
      Array.isArray(val) ? val.length > 0 : val !== undefined
    );
    
    // Aramayı çalıştır
    onSearch(question, hasActiveFilters ? filters : {}, useMultimodal);
  };
  
  // Filtreleme açıklaması
  const getFilterDescription = (): string => {
    const parts = [];
    
    if (filters.tags && filters.tags.length > 0) {
      parts.push(`${t('query.filters.tags')}: ${filters.tags.join(', ')}`);
    }
    
    if (filters.document_types && filters.document_types.length > 0) {
      parts.push(`${t('query.filters.types')}: ${filters.document_types.join(', ')}`);
    }
    
    if (filters.date_after) {
      parts.push(`${t('query.filters.afterDate')}: ${filters.date_after.toLocaleDateString()}`);
    }
    
    if (filters.date_before) {
      parts.push(`${t('query.filters.beforeDate')}: ${filters.date_before.toLocaleDateString()}`);
    }
    
    return parts.join(' | ');
  };
  
  return (
    <div className="filtered-search-bar mb-4">
      <Form onSubmit={handleSubmit}>
        <InputGroup className="mb-2">
          <Form.Control
            type="text"
            placeholder={t('query.questionPlaceholder')}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={loading}
            className="py-2"
          />
          
          <Button 
            variant="outline-secondary" 
            onClick={() => setShowFilters(!showFilters)}
            aria-expanded={showFilters}
          >
            <FaFilter />
          </Button>
          
          <Button 
            variant={useMultimodal ? "info" : "outline-info"}
            onClick={() => setUseMultimodal(!useMultimodal)}
            title={t('query.useMultimodal')}
          >
            <FaImage />
          </Button>
          
          <Button 
            type="submit" 
            variant="primary" 
            disabled={loading || !question.trim()}
          >
            {loading ? (
              <Spinner animation="border" size="sm" />
            ) : (
              <FaSearch />
            )}
          </Button>
        </InputGroup>
        
        {/* Filtre metni */}
        {Object.values(filters).some(val => 
          Array.isArray(val) ? val.length > 0 : val !== undefined
        ) && (
          <div className="active-filters mb-2">
            <small className="text-muted">
              <FaFilter className="me-1" />
              {getFilterDescription()}
              <Button 
                variant="link" 
                size="sm" 
                className="py-0 px-1" 
                onClick={() => setFilters({})}
                title={t('query.filters.clear')}
              >
                ×
              </Button>
            </small>
          </div>
        )}
        
        {/* Multimodal bilgisi */}
        {useMultimodal && (
          <div className="multimodal-info mb-2">
            <small className="text-info">
              <FaImage className="me-1" />
              {t('query.multimodalEnabled')}
              <Button 
                variant="link" 
                size="sm" 
                className="py-0 px-1" 
                onClick={() => setUseMultimodal(false)}
                title={t('query.filters.disable')}
              >
                ×
              </Button>
            </small>
          </div>
        )}
        
        {/* Filtre paneli */}
        {showFilters && (
          <div className="filter-panel p-3 border rounded mb-3 bg-light">
            <h6 className="mb-3">{t('query.filters.title')}</h6>
            
            <div className="row">
              {/* Etiket filtreleri */}
              <div className="col-md-6 mb-3">
                <Form.Label className="d-flex align-items-center">
                  <FaTags className="me-1" />
                  {t('query.filters.tags')}
                </Form.Label>
                
                {isLoadingTags ? (
                  <div className="text-center py-2">
                    <Spinner animation="border" size="sm" />
                  </div>
                ) : availableTags.length > 0 ? (
                  <div className="tag-list d-flex flex-wrap gap-2">
                    {availableTags.map(tag => (
                      <Badge 
                        key={tag}
                        bg={filters.tags?.includes(tag) ? "primary" : "light"}
                        text={filters.tags?.includes(tag) ? "white" : "dark"}
                        className="p-2 cursor-pointer"
                        onClick={() => handleTagChange(tag)}
                      >
                        {tag}
                      </Badge>
                    ))}
                  </div>
                ) : (
                  <div className="text-muted">
                    {t('query.filters.noTags')}
                  </div>
                )}
              </div>
              
              {/* Belge türü filtreleri */}
              <div className="col-md-6 mb-3">
                <Form.Label className="d-flex align-items-center">
                  <FaFile className="me-1" />
                  {t('query.filters.documentTypes')}
                </Form.Label>
                
                {isLoadingTypes ? (
                  <div className="text-center py-2">
                    <Spinner animation="border" size="sm" />
                  </div>
                ) : availableTypes.length > 0 ? (
                  <div className="type-list d-flex flex-wrap gap-2">
                    {availableTypes.map(type => (
                      <Badge 
                        key={type}
                        bg={filters.document_types?.includes(type) ? "success" : "light"}
                        text={filters.document_types?.includes(type) ? "white" : "dark"}
                        className="p-2 cursor-pointer"
                        onClick={() => handleTypeChange(type)}
                      >
                        {type.toUpperCase()}
                      </Badge>
                    ))}
                  </div>
                ) : (
                  <div className="text-muted">
                    {t('query.filters.noTypes')}
                  </div>
                )}
              </div>
              
              {/* Tarih filtreleri */}
              <div className="col-md-6 mb-3">
                <Form.Label className="d-flex align-items-center">
                  <FaCalendarAlt className="me-1" />
                  {t('query.filters.dateRange')}
                </Form.Label>
                
                <div className="d-flex gap-2">
                  <div className="flex-grow-1">
                    <DatePicker
                      selected={filters.date_after}
                      onChange={(date) => handleDateChange('date_after', date)}
                      placeholderText={t('query.filters.fromDate')}
                      dateFormat="yyyy-MM-dd"
                      className="form-control"
                      isClearable
                    />
                  </div>
                  
                  <div className="flex-grow-1">
                    <DatePicker
                      selected={filters.date_before}
                      onChange={(date) => handleDateChange('date_before', date)}
                      placeholderText={t('query.filters.toDate')}
                      dateFormat="yyyy-MM-dd"
                      className="form-control"
                      isClearable
                      minDate={filters.date_after}
                    />
                  </div>
                </div>
              </div>
              
              {/* Filtreler ile ilgili ipuçları */}
              <div className="col-12 mt-2">
                <Accordion>
                  <Accordion.Item eventKey="0">
                    <Accordion.Header>{t('query.filters.searchTips')}</Accordion.Header>
                    <Accordion.Body>
                      <p>{t('query.filters.tipsDescription')}</p>
                      <ul>
                        <li><code>tag:2023_rapor</code> - {t('query.filters.tagTip')}</li>
                        <li><code>type:pdf</code> - {t('query.filters.typeTip')}</li>
                        <li><code>date>2023-01-01</code> - {t('query.filters.dateTip')}</li>
                      </ul>
                    </Accordion.Body>
                  </Accordion.Item>
                </Accordion>
              </div>
            </div>
            
            <div className="d-flex justify-content-end mt-3">
              <Button 
                variant="secondary" 
                size="sm" 
                className="me-2" 
                onClick={() => setFilters({})}
              >
                {t('query.filters.clearAll')}
              </Button>
              
              <Button 
                variant="primary" 
                size="sm" 
                onClick={() => setShowFilters(false)}
              >
                {t('query.filters.apply')}
              </Button>
            </div>
          </div>
        )}
      </Form>
    </div>
  );
};

export default FilteredSearchBar;