// Last reviewed: 2025-04-29 10:07:48 UTC (User: TeeksssJina)
import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import useApi from '../hooks/useApi';
import ResponseFormatSelector from './ResponseFormatSelector';
import ModelSelector from './ModelSelector';
import Results from './Results';
import './AdvancedSearch.css';

const AdvancedSearch = () => {
  const { isLoggedIn } = useAuth();
  const { showToast } = useToast();
  const { apiRequest, isLoading } = useApi();
  
  const [query, setQuery] = useState('');
  const [searchEngine, setSearchEngine] = useState('elasticsearch'); // elasticsearch, weaviate, jina
  const [searchType, setSearchType] = useState('hybrid'); // hybrid, semantic, bm25, tf-idf
  const [embeddingProvider, setEmbeddingProvider] = useState('sentence_transformer'); 
  const [language, setLanguage] = useState('auto');
  const [topK, setTopK] = useState(5);
  const [timeFilter, setTimeFilter] = useState('');
  const [selectedFormat, setSelectedFormat] = useState('default');
  const [selectedModel, setSelectedModel] = useState(null);
  const [useTools, setUseTools] = useState(false);
  const [expandResults, setExpandResults] = useState(true);
  const [expandQuery, setExpandQuery] = useState(true);
  const [preventHallucination, setPreventHallucination] = useState(true);
  const [reranking, setReranking] = useState(false);
  
  const [results, setResults] = useState(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState(null);
  const [availableEngines, setAvailableEngines] = useState({
    elasticsearch: true,
    weaviate: false,
    jina: false
  });
  const [providers, setProviders] = useState([]);
  
  // Sistem durumunu yükle
  useEffect(() => {
    if (isLoggedIn) {
      loadSystemInfo();
      loadProviders();
    }
  }, [isLoggedIn]);
  
  const loadSystemInfo = async () => {
    try {
      const data = await apiRequest('/system/info');
      
      // Weaviate durumu
      if (data.retrieval && data.retrieval.vector_db) {
        setAvailableEngines(prev => ({
          ...prev,
          weaviate: data.retrieval.vector_db.weaviate_available
        }));
      }
      
    } catch (error) {
      console.error('System info loading error:', error);
    }
  };
  
  const loadProviders = async () => {
    try {
      const providersList = [
        { id: 'sentence_transformer', name: 'Sentence Transformer (Lokal)', type: 'local' },
        { id: 'openai', name: 'OpenAI Embeddings', type: 'api' },
        { id: 'cohere', name: 'Cohere Embeddings', type: 'api' },
        { id: 'jina', name: 'Jina AI Embeddings', type: 'api' }
      ];
      
      // API key durumunu kontrol et
      const keyStatus = await apiRequest('/api/api-keys/status');
      
      // API anahtarı durumuna göre sağlayıcıları düzenle
      const updatedProviders = providersList.map(provider => {
        if (provider.type === 'api') {
          const isAvailable = keyStatus[provider.id.toUpperCase()]?.is_available || false;
          return { ...provider, disabled: !isAvailable };
        }
        return provider;
      });
      
      setProviders(updatedProviders);
      
      // Jina API durumuna göre jina search engine'i etkinleştir
      const jinaAvailable = keyStatus.JINA?.is_available || false;
      setAvailableEngines(prev => ({
        ...prev,
        jina: jinaAvailable
      }));
      
    } catch (error) {
      console.error('Providers loading error:', error);
    }
  };
  
  const handleSearch = async (e) => {
    e.preventDefault();
    
    if (!query.trim()) return;
    
    setSearching(true);
    setError(null);
    setResults(null);
    
    try {
      // Arama motoru ve türüne göre endpoint belirle
      let endpoint = '/api/query';
      let method = 'POST';
      let body = {
        query: query.trim(),
        response_format: selectedFormat,
        use_tools: useTools,
        prevent_hallucination: preventHallucination,
        expand_results: expandResults,
        expand_query: expandQuery,
        time_filter: timeFilter || undefined
      };
      
      // URL parametreleri
      let params = new URLSearchParams();
      params.append('search_type', searchType);
      params.append('top_k', topK);
      params.append('reranking', reranking);
      
      // Model seçilmişse ve default değilse ekle
      if (selectedModel && selectedModel !== 'default') {
        params.append('model', selectedModel);
      }
      
      // Arama motoru seçimine göre özelleştirme
      if (searchEngine === 'weaviate') {
        endpoint = '/api/weaviate/search';
        body = {
          query: query.trim(),
          provider: embeddingProvider
        };
      } else if (searchEngine === 'jina') {
        endpoint = '/api/search/jina';
        body = {
          query: query.trim(),
          language: language === 'auto' ? detectLanguage(query) : language
        };
      }
      
      // Aramayı yap
      const response = await apiRequest(`${endpoint}?${params.toString()}`, {
        method,
        body: JSON.stringify(body)
      });
      
      // Sonuçları işle
      if (searchEngine === 'elasticsearch') {
        setResults(response);
      } else {
        // Weaviate ve Jina sonuçlarını results formatına çevir
        setResults({
          answer: response.results.map(r => r.text).join('\n\n---\n\n'),
          retrieved_documents: response.results.map(r => ({
            id: r.id,
            text: r.text,
            source_info: r.source_info || {},
            score: r.score
          })),
          query_time_ms: response.query_time_ms
        });
      }
      
    } catch (error) {
      setError(error.message || 'Arama sırasında bir hata oluştu');
      showToast(error.message || 'Arama sırasında bir hata oluştu', 'error');
    } finally {
      setSearching(false);
    }
  };
  
  const detectLanguage = (text) => {
    // Basit bir dil tespiti
    const turkishChars = ['ç', 'ğ', 'ı', 'ö', 'ş', 'ü', 'Ç', 'Ğ', 'İ', 'Ö', 'Ş', 'Ü'];
    
    if (turkishChars.some(char => text.includes(char))) {
      return 'tr';
    }
    
    return 'en';
  };
  
  return (
    <div className="advanced-search">
      <h2>Gelişmiş Arama</h2>
      
      <form onSubmit={handleSearch} className="search-form">
        <div className="search-input-wrapper">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Sorunuzu girin..."
            className="search-input"
            disabled={searching}
          />
          
          <button
            type="submit"
            className="search-button"
            disabled={searching || !query.trim()}
          >
            {searching ? 'Aranıyor...' : 'Ara'}
          </button>
        </div>
        
        <div className="search-options">
          <div className="option-group">
            <label>Arama Motoru:</label>
            <div className="select-wrapper">
              <select
                value={searchEngine}
                onChange={(e) => setSearchEngine(e.target.value)}
                disabled={searching}
              >
                <option value="elasticsearch">Elasticsearch (Varsayılan)</option>
                <option value="weaviate" disabled={!availableEngines.weaviate}>
                  Weaviate {!availableEngines.weaviate && '(Yapılandırılmamış)'}
                </option>
                <option value="jina" disabled={!availableEngines.jina}>
                  Jina AI {!availableEngines.jina && '(API Anahtarı Eksik)'}
                </option>
              </select>
            </div>
          </div>
          
          <div className="option-group">
            <label>Arama Türü:</label>
            <div className="select-wrapper">
              <select
                value={searchType}
                onChange={(e) => setSearchType(e.target.value)}
                disabled={searching || searchEngine !== 'elasticsearch'}
              >
                <option value="hybrid">Hybrid (Semantic + BM25)</option>
                <option value="semantic">Semantic (Dense)</option>
                <option value="bm25">BM25 (Sparse)</option>
                <option value="tf-idf">TF-IDF (Sparse)</option>
              </select>
            </div>
          </div>
          
          <div className="option-group">
            <label>Embedding Provider:</label>
            <div className="select-wrapper">
              <select
                value={embeddingProvider}
                onChange={(e) => setEmbeddingProvider(e.target.value)}
                disabled={searching || searchEngine === 'jina'}
              >
                {providers.map(provider => (
                  <option 
                    key={provider.id} 
                    value={provider.id}
                    disabled={provider.disabled}
                  >
                    {provider.name} {provider.disabled ? '(API Anahtarı Eksik)' : ''}
                  </option>
                ))}
              </select>
            </div>
          </div>
          
          <div className="option-group">
            <label>Dil:</label>
            <div className="select-wrapper">
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                disabled={searching || searchEngine !== 'jina'}
              >
                <option value="auto">Otomatik Tespit</option>
                <option value="en">İngilizce</option>
                <option value="tr">Türkçe</option>
                <option value="fr">Fransızca</option>
                <option value="de">Almanca</option>
                <option value="es">İspanyolca</option>
                <option value="it">İtalyanca</option>
              </select>
            </div>
          </div>
          
          <div className="option-group">
            <label>Sonuç Sayısı:</label>
            <div className="select-wrapper">
              <select
                value={topK}
                onChange={(e) => setTopK(parseInt(e.target.value))}
                disabled={searching}
              >
                <option value="3">3</option>
                <option value="5">5</option>
                <option value="10">10</option>
                <option value="20">20</option>
              </select>
            </div>
          </div>
          
          <div className="option-group">
            <label>Tarih Filtresi:</label>
            <div className="select-wrapper">
              <select
                value={timeFilter}
                onChange={(e) => setTimeFilter(e.target.value)}
                disabled={searching || searchEngine !== 'elasticsearch'}
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
        
        {searchEngine === 'elasticsearch' && (
          <div className="advanced-toggles">
            <div className="toggle-group">
              <label>
                <input
                  type="checkbox"
                  checked={useTools}
                  onChange={(e) => setUseTools(e.target.checked)}
                  disabled={searching}
                />
                <span>Harici Araçlar</span>
              </label>
              <div className="toggle-description">
                Hesaplama, web sayfası okuma gibi araçlara erişim sağlar
              </div>
            </div>
            
            <div className="toggle-group">
              <label>
                <input
                  type="checkbox"
                  checked={preventHallucination}
                  onChange={(e) => setPreventHallucination(e.target.checked)}
                  disabled={searching}
                />
                <span>Hallucination Önleme</span>
              </label>
              <div className="toggle-description">
                Belgede olmayan bilgileri yanıta eklemesini engeller
              </div>
            </div>
            
            <div className="toggle-group">
              <label>
                <input
                  type="checkbox"
                  checked={expandResults}
                  onChange={(e) => setExpandResults(e.target.checked)}
                  disabled={searching}
                />
                <span>Sonuç Genişletme</span>
              </label>
              <div className="toggle-description">
                En iyi sonuçlar için ilişkili belgeler de dahil edilir
              </div>
            </div>
            
            <div className="toggle-group">
              <label>
                <input
                  type="checkbox"
                  checked={expandQuery}
                  onChange={(e) => setExpandQuery(e.target.checked)}
                  disabled={searching}
                />
                <span>Sorgu Genişletme</span>
              </label>
              <div className="toggle-description">
                Sorguyu eşanlamlı terimlerle zenginleştirir
              </div>
            </div>
            
            <div className="toggle-group">
              <label>
                <input
                  type="checkbox"
                  checked={reranking}
                  onChange={(e) => setReranking(e.target.checked)}
                  disabled={searching}
                />
                <span>Yeniden Sıralama</span>
              </label>
              <div className="toggle-description">
                Sonuçları alakalılık ve yakınlık bazında yeniden sıralar
              </div>
            </div>
          </div>
        )}
        
        <div className="model-response-settings">
          {searchEngine === 'elasticsearch' && (
            <>
              <ResponseFormatSelector onFormatChange={setSelectedFormat} />
              <ModelSelector onModelChange={setSelectedModel} />
            </>
          )}
        </div>
      </form>
      
      {error && (
        <div className="search-error">
          <p>{error}</p>
        </div>
      )}
      
      {results && !error && (
        <div className="search-results">
          <Results
            answer={results.answer}
            retrievedDocs={results.retrieved_documents}
            hallucination_detected={results.hallucination_detected}
            confidence_score={results.confidence_score}
            citations={results.citations}
            tool_calls={results.tool_calls}
          />
        </div>
      )}
    </div>
  );
};

export default AdvancedSearch;