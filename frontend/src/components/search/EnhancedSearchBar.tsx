// Last reviewed: 2025-04-30 10:37:40 UTC (User: Teeksss)
import React, { useState, useEffect, useRef } from 'react';
import { Form, InputGroup, Dropdown, Button, Badge, Spinner } from 'react-bootstrap';
import { 
  FaSearch, FaTimes, FaCog, FaFilter, 
  FaSortAmountDown, FaSortAmountUp, FaCalendarAlt,
  FaTag, FaUser, FaFileAlt, FaHistory
} from 'react-icons/fa';
import { useTranslation } from 'react-i18next';

// Arama operatörleri
export enum SearchOperator {
  AND = 'AND',
  OR = 'OR',
  NOT = 'NOT'
}

// Arama filtresi
export interface SearchFilter {
  field: string;
  value: string;
  operator?: SearchOperator;
  label?: string;
}

// Arama sorgusu
export interface SearchQuery {
  text: string;
  filters: SearchFilter[];
  sort?: string;
  sortDirection?: 'asc' | 'desc';
}

// Öneri tipi
export interface SearchSuggestion {
  text: string;
  type: 'history' | 'document' | 'tag' | 'person';
}

// Bileşen özellikleri
interface EnhancedSearchBarProps {
  onSearch: (query: SearchQuery) => void;
  placeholder?: string;
  initialQuery?: string;
  initialFilters?: SearchFilter[];
  availableFilters?: { field: string; label: string; options?: string[] }[];
  showSortOptions?: boolean;
  showFilterOptions?: boolean;
  showRecentSearches?: boolean;
  loading?: boolean;
  className?: string;
  getSuggestions?: (text: string) => Promise<SearchSuggestion[]>;
  onClear?: () => void;
  autoFocus?: boolean;
}

const EnhancedSearchBar: React.FC<EnhancedSearchBarProps> = ({
  onSearch,
  placeholder = 'Search...',
  initialQuery = '',
  initialFilters = [],
  availableFilters = [],
  showSortOptions = true,
  showFilterOptions = true,
  showRecentSearches = true,
  loading = false,
  className = '',
  getSuggestions,
  onClear,
  autoFocus = false
}) => {
  const { t } = useTranslation();
  const searchInputRef = useRef<HTMLInputElement>(null);
  
  // Durum değişkenleri
  const [searchText, setSearchText] = useState<string>(initialQuery);
  const [filters, setFilters] = useState<SearchFilter[]>(initialFilters);
  const [sort, setSort] = useState<string>('');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [showSuggestions, setShowSuggestions] = useState<boolean>(false);
  const [suggestions, setSuggestions] = useState<SearchSuggestion[]>([]);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
  const [suggestionsLoading, setSuggestionsLoading] = useState<boolean>(false);
  
  // Önceki aramaları yükle
  useEffect(() => {
    if (showRecentSearches) {
      const saved = localStorage.getItem('recent_searches');
      if (saved) {
        try {
          setRecentSearches(JSON.parse(saved));
        } catch (error) {
          console.error('Error loading recent searches:', error);
        }
      }
    }
  }, [showRecentSearches]);
  
  // Otomatik odaklanma
  useEffect(() => {
    if (autoFocus && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [autoFocus]);
  
  // Arama işlevi
  const handleSearch = () => {
    // Arama terimini temizle
    const trimmedText = searchText.trim();
    
    // Arama sorgusu oluştur
    const query: SearchQuery = {
      text: trimmedText,
      filters,
      sort,
      sortDirection
    };
    
    // Aramayı gerçekleştir
    onSearch(query);
    
    // Son aramalara ekle
    if (trimmedText && !recentSearches.includes(trimmedText)) {
      const updatedSearches = [trimmedText, ...recentSearches.slice(0, 9)];
      setRecentSearches(updatedSearches);
      localStorage.setItem('recent_searches', JSON.stringify(updatedSearches));
    }
    
    // Önerileri kapat
    setShowSuggestions(false);
  };
  
  // Enter tuşu ile arama
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };
  
  // Arama metni değiştiğinde önerileri güncelle
  const handleSearchChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchText(value);
    
    // Önerileri getir
    if (value.trim().length >= 2 && getSuggestions) {
      setSuggestionsLoading(true);
      setShowSuggestions(true);
      
      try {
        const newSuggestions = await getSuggestions(value.trim());
        setSuggestions(newSuggestions);
      } catch (error) {
        console.error('Error getting suggestions:', error);
        setSuggestions([]);
      } finally {
        setSuggestionsLoading(false);
      }
    } else {
      setShowSuggestions(false);
    }
  };
  
  // Filtreyi değiştir
  const handleFilterChange = (newFilter: SearchFilter) => {
    // Aynı alan için varsa güncelle, yoksa ekle
    const index = filters.findIndex(f => f.field === newFilter.field);
    
    if (index >= 0) {
      const updatedFilters = [...filters];
      updatedFilters[index] = newFilter;
      setFilters(updatedFilters);
    } else {
      setFilters([...filters, newFilter]);
    }
    
    // UI'ı güncelle ve aramayı otomatik yap
    setTimeout(() => {
      handleSearch();
    }, 100);
  };
  
  // Filtreyi kaldır
  const removeFilter = (field: string) => {
    setFilters(filters.filter(f => f.field !== field));
    
    // UI'ı güncelle ve aramayı otomatik yap
    setTimeout(() => {
      handleSearch();
    }, 100);
  };
  
  // Tüm filtreleri temizle
  const clearAllFilters = () => {
    setFilters([]);
    
    // UI'ı güncelle ve aramayı otomatik yap
    setTimeout(() => {
      handleSearch();
    }, 100);
  };
  
  // Sıralamayı değiştir
  const handleSortChange = (sortField: string) => {
    // Aynı alan seçilirse yönü değiştir, farklı alan seçilirse yeni alan ve varsayılan yön
    if (sort === sortField) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSort(sortField);
      setSortDirection('desc');
    }
    
    // UI'ı güncelle ve aramayı otomatik yap
    setTimeout(() => {
      handleSearch();
    }, 100);
  };
  
  // Her şeyi temizle
  const handleClear = () => {
    setSearchText('');
    setFilters([]);
    setSort('');
    setSortDirection('desc');
    
    if (onClear) {
      onClear();
    }
  };
  
  // Öneri seçme
  const selectSuggestion = (suggestion: SearchSuggestion) => {
    setSearchText(suggestion.text);
    setShowSuggestions(false);
    
    // Aramayı otomatik yap
    setTimeout(() => {
      handleSearch();
    }, 100);
  };
  
  // Son aramayı seç
  const selectRecentSearch = (search: string) => {
    setSearchText(search);
    setShowSuggestions(false);
    
    // Aramayı otomatik yap
    setTimeout(() => {
      handleSearch();
    }, 100);
  };
  
  // Filtre adı gösterimi
  const getFilterLabel = (field: string): string => {
    const filter = availableFilters.find(f => f.field === field);
    return filter?.label || field;
  };
  
  // Öneri simgesi
  const getSuggestionIcon = (type: string) => {
    switch (type) {
      case 'history': return <FaHistory className="me-2 text-secondary" />;
      case 'document': return <FaFileAlt className="me-2 text-primary" />;
      case 'tag': return <FaTag className="me-2 text-success" />;
      case 'person': return <FaUser className="me-2 text-info" />;
      default: return <FaSearch className="me-2 text-secondary" />;
    }
  };
  
  return (
    <div className={`enhanced-search-bar ${className}`}>
      <div className="search-input-container">
        <InputGroup>
          <InputGroup.Text>
            {loading ? (
              <Spinner animation="border" size="sm" />
            ) : (
              <FaSearch />
            )}
          </InputGroup.Text>
          
          <Form.Control
            type="text"
            placeholder={placeholder}
            value={searchText}
            onChange={handleSearchChange}
            onKeyDown={handleKeyDown}
            ref={searchInputRef}
            autoFocus={autoFocus}
          />
          
          {(searchText || filters.length > 0) && (
            <Button 
              variant="outline-secondary" 
              onClick={handleClear}
              title={t('search.clear')}
            >
              <FaTimes />
            </Button>
          )}
          
          <Button 
            variant="primary" 
            onClick={handleSearch}
            disabled={loading}
          >
            {t('search.search')}
          </Button>
          
          {showFilterOptions && (
            <Dropdown>
              <Dropdown.Toggle 
                variant="outline-secondary" 
                id="filter-dropdown"
                title={t('search.filter')}
              >
                <FaFilter />
                {filters.length > 0 && (
                  <Badge 
                    bg="primary" 
                    pill 
                    className="ms-1"
                  >
                    {filters.length}
                  </Badge>
                )}
              </Dropdown.Toggle>
              
              <Dropdown.Menu className="filter-menu">
                <Dropdown.Header>{t('search.filterBy')}</Dropdown.Header>
                
                {availableFilters.map((filterOption) => (
                  <React.Fragment key={filterOption.field}>
                    {filterOption.options ? (
                      <Dropdown.Item as="div" className="p-0">
                        <div className="px-3 py-2">
                          <Form.Group className="mb-0">
                            <Form.Label>{filterOption.label}</Form.Label>
                            <Form.Select 
                              size="sm"
                              value={filters.find(f => f.field === filterOption.field)?.value || ''}
                              onChange={(e) => handleFilterChange({
                                field: filterOption.field,
                                value: e.target.value,
                                label: filterOption.label
                              })}
                            >
                              <option value="">{t('search.all')}</option>
                              {filterOption.options.map(option => (
                                <option key={option} value={option}>
                                  {option}
                                </option>
                              ))}
                            </Form.Select>
                          </Form.Group>
                        </div>
                      </Dropdown.Item>
                    ) : (
                      <Dropdown.Item as="div" className="p-0">
                        <div className="px-3 py-2">
                          <Form.Group className="mb-0">
                            <Form.Label>{filterOption.label}</Form.Label>
                            <Form.Control 
                              type="text" 
                              size="sm"
                              value={filters.find(f => f.field === filterOption.field)?.value || ''}
                              onChange={(e) => handleFilterChange({
                                field: filterOption.field,
                                value: e.target.value,
                                label: filterOption.label
                              })}
                              placeholder={`${t('search.enter')} ${filterOption.label.toLowerCase()}`}
                            />
                          </Form.Group>
                        </div>
                      </Dropdown.Item>
                    )}
                    <Dropdown.Divider />
                  </React.Fragment>
                ))}
                
                {filters.length > 0 && (
                  <Dropdown.Item 
                    onClick={clearAllFilters}
                    className="text-danger"
                  >
                    <FaTimes className="me-2" />
                    {t('search.clearAllFilters')}
                  </Dropdown.Item>
                )}
              </Dropdown.Menu>
            </Dropdown>
          )}
          
          {showSortOptions && (
            <Dropdown>
              <Dropdown.Toggle 
                variant="outline-secondary" 
                id="sort-dropdown"
                title={t('search.sort')}
              >
                {sortDirection === 'asc' ? (
                  <FaSortAmountUp />
                ) : (
                  <FaSortAmountDown />
                )}
              </Dropdown.Toggle>
              
              <Dropdown.Menu>
                <Dropdown.Header>{t('search.sortBy')}</Dropdown.Header>
                <Dropdown.Item 
                  onClick={() => handleSortChange('relevance')}
                  active={sort === 'relevance'}
                >
                  {t('search.relevance')}
                </Dropdown.Item>
                <Dropdown.Item 
                  onClick={() => handleSortChange('date')}
                  active={sort === 'date'}
                >
                  <FaCalendarAlt className="me-2" />
                  {t('search.date')}
                </Dropdown.Item>
                <Dropdown.Item 
                  onClick={() => handleSortChange('name')}
                  active={sort === 'name'}
                >
                  {t('search.name')}
                </Dropdown.Item>
              </Dropdown.Menu>
            </Dropdown>
          )}
        </InputGroup>
        
        {/* Öneriler */}
        {showSuggestions && (
          <div className="search-suggestions">
            {suggestionsLoading ? (
              <div className="text-center p-3">
                <Spinner animation="border" size="sm" />
                <span className="ms-2">{t('search.loadingSuggestions')}</span>
              </div>
            ) : suggestions.length > 0 ? (
              <div className="suggestions-list">
                {suggestions.map((suggestion, index) => (
                  <div 
                    key={`${suggestion.type}-${index}`}
                    className="suggestion-item"
                    onClick={() => selectSuggestion(suggestion)}
                  >
                    {getSuggestionIcon(suggestion.type)}
                    <span>{suggestion.text}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center p-3">
                {t('search.noSuggestions')}
              </div>
            )}
          </div>
        )}
      </div>
      
      {/* Aktif filtreler */}
      {filters.length > 0 && (
        <div className="active-filters mt-2">
          {filters.map((filter) => (
            <Badge 
              key={filter.field}
              bg="light" 
              text="dark"
              className="me-2 mb-1 px-2 py-1"
            >
              <span className="filter-label">{filter.label || getFilterLabel(filter.field)}:</span>
              <span className="filter-value ms-1">{filter.value}</span>
              <FaTimes 
                className="ms-2" 
                role="button"
                onClick={() => removeFilter(filter.field)}
              />
            </Badge>
          ))}
          
          {filters.length > 1 && (
            <Button 
              variant="link" 
              size="sm"
              className="text-danger p-0 ms-2"
              onClick={clearAllFilters}
            >
              {t('search.clearAll')}
            </Button>
          )}
        </div>
      )}
      
      {/* Son aramalar */}
      {showRecentSearches && recentSearches.length > 0 && !showSuggestions && !searchText && (
        <div className="recent-searches mt-2">
          <div className="recent-searches-header d-flex justify-content-between align-items-center mb-1">
            <small className="text-muted">{t('search.recentSearches')}</small>
            <Button 
              variant="link" 
              size="sm"
              className="p-0 text-muted"
              onClick={() => {
                setRecentSearches([]);
                localStorage.removeItem('recent_searches');
              }}
            >
              {t('search.clearHistory')}
            </Button>
          </div>
          
          <div className="recent-searches-list">
            {recentSearches.slice(0, 5).map((search, index) => (
              <Badge 
                key={index}
                bg="light" 
                text="dark"
                className="me-2 mb-1 px-2 py-1"
                style={{ cursor: 'pointer' }}
                onClick={() => selectRecentSearch(search)}
              >
                <FaHistory className="me-1" />
                {search}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default EnhancedSearchBar;