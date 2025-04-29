// Last reviewed: 2025-04-29 10:51:12 UTC (User: TeeksssPrioritizationTest.js)
import React, { useState } from 'react';
import { useToast } from '../contexts/ToastContext';
import useApi from '../hooks/useApi';
import './PrioritizationTest.css';

const PrioritizationTest = () => {
  const { showToast } = useToast();
  const { apiRequest, isLoading } = useApi();
  
  const [query, setQuery] = useState('');
  const [searchType, setSearchType] = useState('hybrid');
  const [expandResults, setExpandResults] = useState(true);
  const [expandQuery, setExpandQuery] = useState(true);
  const [topK, setTopK] = useState(10);
  const [results, setResults] = useState(null);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!query.trim()) {
      showToast('Lütfen bir sorgu girin', 'warning');
      return;
    }
    
    try {
      const data = await apiRequest('/api/query/prioritization-test', {
        method: 'POST',
        body: JSON.stringify({ query: query.trim() }),
        urlParams: new URLSearchParams({
          top_k: topK,
          search_type: searchType,
          expand_results: expandResults,
          expand_query: expandQuery
        }).toString()
      });
      
      setResults(data);
    } catch (error) {
      showToast('Test sırasında bir hata oluştu', 'error');
    }
  };
  
  const getScoreDifference = (std, priority) => {
    const diff = priority - std;
    const percent = (diff / std) * 100;
    return `${diff.toFixed(2)} (${percent.toFixed(0)}%)`;
  };
  
  return (
    <div className="prioritization-test">
      <h2>Kurumsal Belge Önceliklendirme Testi</h2>
      <p className="description">
        Bu araç, kurumsal kaynaklardan gelen belgelerin nasıl önceliklendirildiğini test etmenize olanak tanır.
        Sorgu sonuçları, yapılandırılmış önceliklendirme kurallarına göre normal ve öncelikli versiyonları ile karşılaştırılır.
      </p>
      
      <form onSubmit={handleSubmit} className="test-form">
        <div className="input-group">
          <input 
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Test sorgusu girin..."
            className="query-input"
          />
          
          <button 
            type="submit" 
            className="test-button"
            disabled={isLoading}
          >
            {isLoading ? 'Test Ediliyor...' : 'Test Et'}
          </button>
        </div>
        
        <div className="test-options">
          <div className="option-group">
            <label>Arama Tipi:</label>
            <select
              value={searchType}
              onChange={(e) => setSearchType(e.target.value)}
            >
              <option value="hybrid">Hybrid (BM25 + Semantic)</option>
              <option value="semantic">Semantic</option>
              <option value="bm25">BM25</option>
            </select>
          </div>
          
          <div className="option-group">
            <label>Sonuç Sayısı:</label>
            <select
              value={topK}
              onChange={(e) => setTopK(parseInt(e.target.value))}
            >
              <option value="5">5</option>
              <option value="10">10</option>
              <option value="20">20</option>
            </select>
          </div>
          
          <div className="option-group checkbox">
            <label>
              <input 
                type="checkbox"
                checked={expandResults}
                onChange={(e) => setExpandResults(e.target.checked)}
              />
              <span>Sonuçları Genişlet</span>
            </label>
          </div>
          
          <div className="option-group checkbox">
            <label>
              <input 
                type="checkbox"
                checked={expandQuery}
                onChange={(e) => setExpandQuery(e.target.checked)}
              />
              <span>Sorguyu Genişlet</span>
            </label>
          </div>
        </div>
      </form>
      
      {results && (
        <div className="test-results">
          <h3>Test Sonuçları</h3>
          
          <div className="settings-info">
            <h4>Önceliklendirme Ayarları</h4>
            <div className="settings-grid">
              <div className="setting-item">
                <div className="setting-label">Kurumsal Alan Adları:</div>
                <div className="setting-value">
                  {results.priority_settings.corporate_domains.join(', ')}
                </div>
              </div>
              
              <div className="setting-item">
                <div className="setting-label">Kurumsal Belge Çarpanı:</div>
                <div className="setting-value">{results.priority_settings.corporate_boost}</div>
              </div>
              
              <div className="setting-item">
                <div className="setting-label">Yeni Belge Çarpanı:</div>
                <div className="setting-value">{results.priority_settings.recent_boost}</div>
              </div>
              
              <div className="setting-item">
                <div className="setting-label">İncelenmiş Belge Çarpanı:</div>
                <div className="setting-value">{results.priority_settings.reviewed_boost}</div>
              </div>
            </div>
          </div>
          
          <div className="comparison-table-container">
            <table className="comparison-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Başlık/Belge</th>
                  <th>Standart Skor</th>
                  <th>Öncelikli Skor</th>
                  <th>Fark</th>
                  <th>Öncelik Faktörleri</th>
                </tr>
              </thead>
              <tbody>
                {results.comparison_results.map((item, index) => (
                  <tr key={index} className={item.boost_factor > 1 ? 'prioritized' : ''}>
                    <td>{index + 1}</td>
                    <td>
                      <div className="document-title">{item.title || 'Başlıksız Belge'}</div>
                      {item.url && (
                        <div className="document-url">
                          <a href={item.url} target="_blank" rel="noopener noreferrer">
                            {item.url}
                          </a>
                        </div>
                      )}
                    </td>
                    <td className="score">{item.standard_score.toFixed(2)}</td>
                    <td className="score">{item.prioritized_score.toFixed(2)}</td>
                    <td className={item.boost_factor > 1 ? 'positive-diff' : ''}>
                      {getScoreDifference(item.standard_score, item.prioritized_score)}
                    </td>
                    <td>
                      <div className="factor-badges">
                        {item.is_corporate && (
                          <span className="factor-badge corporate" title="Kurumsal Kaynak">
                            Kurumsal
                          </span>
                        )}
                        {item.is_recent && (
                          <span className="factor-badge recent" title="Son 30 gün içinde oluşturuldu">
                            Yeni
                          </span>
                        )}
                        {item.is_reviewed && (
                          <span className="factor-badge reviewed" title="İncelenmiş belge">
                            İncelenmiş
                          </span>
                        )}
                        {item.priority_reasons && item.priority_reasons.map((reason, i) => (
                          <span key={i} className="reason">{reason}</span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          <div className="results-summary">
            <h4>Önceliklendirme Özeti</h4>
            <p>
              Bu test sonuçlarında, kurumsal belgelere {results.priority_settings.corporate_boost}x, 
              son 30 gün içindeki belgelere {results.priority_settings.recent_boost}x, 
              ve incelenmiş belgelere {results.priority_settings.reviewed_boost}x çarpan uygulanmıştır.
            </p>
            <p>
              {results.comparison_results.filter(item => item.boost_factor > 1).length} adet belge 
              önceliklendirilmiş ve skorları artırılmıştır.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default PrioritizationTest;