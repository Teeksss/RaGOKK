// Last reviewed: 2025-04-29 08:53:08 UTC (User: Teekssseskikleri)
import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import ResponseFormatSelector from './ResponseFormatSelector';
import ModelSelector from './ModelSelector';
import './SearchBar.css';

const SearchBar = ({ onSearchStart, onResults, onError, isSearching, apiRequest }) => {
  const [query, setQuery] = useState('');
  const [advancedOptions, setAdvancedOptions] = useState(false);
  const [searchHistory, setSearchHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [selectedFormat, setSelectedFormat] = useState('default');
  const [selectedModel, setSelectedModel] = useState(null);
  const [useTools, setUseTools] = useState(false);
  const [preventHallucination, setPreventHallucination] = useState(true);
  const [expandResults, setExpandResults] = useState(true);
  const [expandQuery, setExpandQuery] = useState(true);
  const [timeFilter, setTimeFilter] = useState('');
  
  const searchInputRef = useRef(null);
  const historyRef = useRef(null);
  const { isLoggedIn } = useAuth();
  
  // Load search history from localStorage
  useEffect(() => {
    if (isLoggedIn) {
      const history = JSON.parse(localStorage.getItem('searchHistory') || '[]');
      setSearchHistory(history.slice(0, 10)); // En son 10 sorguyu göster
    }
  }, [isLoggedIn]);
  
  // Close history dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (historyRef.current && !historyRef.current.contains(event.target) && 
          searchInputRef.current && !searchInputRef.current.contains(event.target)) {
        setShowHistory(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!query.trim()) return;
    
    try {
      // Arama başlangıcını bildir
      onSearchStart();
      
      // Tarih filtresini formatlama
      let formattedTimeFilter = null;
      if (timeFilter) {
        formattedTimeFilter = timeFilter;
      }
      
      // Arama isteği parametreleri
      const searchParams = {
        query: query.trim(),
        response_format: selectedFormat,
        use_tools: useTools,
        prevent_hallucination: preventHallucination,
        expand_results: expandResults,
        expand_query: expandQuery,
        time_filter: formattedTimeFilter
      };
      
      // Sorguyu gönder
      const queryParams = new URLSearchParams();
      
      // Model seçilmişse ve default değilse ekle
      if (selectedModel && selectedModel !== 'default') {
        queryParams.append('model', selectedModel);
      }
      
      const endpoint = `/api/query${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
      
      const response = await apiRequest(endpoint, {
        method: 'POST',
        body: JSON.stringify(searchParams)
      });
      
      // Sonuçları bildir
      onResults(response);
      
      // Arama geçmişine ekle ve localStorage'da güncelle
      const updatedHistory = [query.trim(), ...searchHistory.filter(q => q !== query.trim())].slice(0, 10);
      setSearchHistory(updatedHistory);
      localStorage.setItem('searchHistory', JSON.stringify(updatedHistory));
      
    } catch (error) {
      onError(error.message || 'Arama sırasında bir hata oluştu');
    }
  };
  
  const handleHistoryItemClick = (item) => {
    setQuery(item);
    setShowHistory(false);
    searchInputRef.current.focus();
  };
  
  return (
    <div className="search-container">
      <form onSubmit={handleSubmit} className="search-form">
        <div className="search-input-wrapper">
          <input
            ref={searchInputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Sorunuzu girin..."
            className="search-input"
            disabled={isSearching}
            onFocus={() => searchHistory.length > 0 && setShowHistory(true)}
          />
          
          {showHistory && searchHistory.length > 0 && (
            <div className="search-history-dropdown" ref={historyRef}>
              <div className="search-history-header">
                <div>Son Aramalar</div>
                <button 
                  type="button" 
                  className="clear-history-btn"
                  onClick={() => {
                    setSearchHistory([]);
                    localStorage.setItem('searchHistory', '[]');
                    setShowHistory(false);
                  }}
                >
                  Temizle
                </button>
              </div>
              <ul>
                {searchHistory.map((item, index) => (
                  <li 
                    key={index} 
                    onClick={() => handleHistoryItemClick(item)}
                    className="history-item"
                  >
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
        
        <button
          type="submit"
          className="search-button"
          disabled={isSearching || !query.trim()}
        >
          {isSearching ? 'Aranıyor...' : 'Ara'}
        </button>
      </form>
      
      <div className="advanced-options-toggle">
        <button
          type="button"
          className="toggle-button"
          onClick={() => setAdvancedOptions(!advancedOptions)}
        >
          {advancedOptions ? 'Gelişmiş Seçenekleri Gizle' : 'Gelişmiş Seçenekler'}
        </button>
      </div>
      
      {advancedOptions && (
        <div className="advanced-options">
          <div className="options-row">
            <ResponseFormatSelector onFormatChange={setSelectedFormat} />
            <ModelSelector onModelChange={setSelectedModel} />
          </div>
          
          <div className="options-row">
            <div className="option-group">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={useTools}
                  onChange={(e) => setUseTools(e.target.checked)}
                />
                <span>Harici Araçlar Kullan</span>
              </label>
              <div className="option-description">
                Hesaplama, web sayfası okuma gibi araçlara erişim sağlar
              </div>
            </div>
            
            <div className="option-group">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={preventHallucination}
                  onChange={(e) => setPreventHallucination(e.target.checked)}
                />
                <span>Hallucination Önleme</span>
              </label>
              <div className="option-description">
                Belgede olmayan bilgileri yanıta eklemesini engeller
              </div>
            </div>
          </div>
          
          <div className="options-row">
            <div className="option-group">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={expandResults}
                  onChange={(e) => setExpandResults(e.target.checked)}
                />
                <span>Sonuç Genişletme</span>
              </label>
              <div className="option-description">
                En iyi sonuçlar için ilişkili belgeler de dahil edilir
              </div>
            </div>
            
            <div className="option-group">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={expandQuery}
                  onChange={(e) => setExpandQuery(e.target.checked)}
                />
                <span>Sorgu Genişletme</span>
              </label>
              <div className="option-description">
                Sorguyu eşanlamlı terimlerle zenginleştirir
              </div>
            </div>
          </div>
          
          <div className="options-row">
            <div className="option-group full-width">
              <label className="select-label">Tarih Filtresi:</label>
              <select 
                className="time-filter-select"
                value={timeFilter}
                onChange={(e) => setTimeFilter(e.target.value)}
              >
                <option value="">Tüm zamanlar</option>
                <option value="last_1d">Son 24 saat</option>
                <option value="last_1w">Son 1 hafta</option>
                <option value="last_1m">Son 1 ay</option>
                <option value="last_6m">Son 6 ay</option>
                <option value="last_1y">Son 1 yıl</option>
              </select>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SearchBar;