// Last reviewed: 2025-04-29 08:53:08 UTC (User: Teekssseskikleri)
import React, { useState } from 'react';
import './Results.css';

const Results = ({ answer, retrievedDocs, hallucination_detected, confidence_score, citations, tool_calls }) => {
  const [activeTab, setActiveTab] = useState('answer');
  
  // Yanıt metnini formatlayarak rendering için hazırla
  const formatAnswer = (text) => {
    // Referanslar için bağlantılar ekle
    if (citations && citations.length > 0) {
      const citationRegex = /\[\[(\d+)\]\]|\[(\d+)\]|\[(?:Kaynak|Ref)\s*(\d+)\]/g;
      
      // Her referans için HTML elementi oluştur
      return text.replace(citationRegex, (match, p1, p2, p3) => {
        const refNum = p1 || p2 || p3;
        return `<span class="citation" data-citation="${refNum}">[${refNum}]</span>`;
      });
    }
    
    // Tool results göster
    if (tool_calls && tool_calls.length > 0) {
      // Tool çağrı sonuçlarını göster
      let formattedText = text;
      
      // Tool sonuçlarını düzenlenmiş metinde belirgin hale getir
      tool_calls.forEach(tool => {
        const toolPattern = new RegExp(`\\[\\[ToolResult: ${tool.name}\\]\\]([\\s\\S]*?)\\[\\[\\/ToolResult\\]\\]`, 'g');
        formattedText = formattedText.replace(toolPattern, (match, content) => {
          return `<div class="tool-result"><div class="tool-name">${tool.name} sonucu:</div><pre class="tool-content">${content}</pre></div>`;
        });
      });
      
      return formattedText;
    }
    
    return text;
  };
  
  // Yanıt metnini HTML olarak oluştur
  const formattedAnswer = formatAnswer(answer);
  
  // Hallucination uyarısı göster (eğer varsa)
  const showHallucinationWarning = hallucination_detected === true;
  
  // Güven skoruna göre renk belirle
  const getConfidenceColor = (score) => {
    if (score >= 0.8) return 'high-confidence';
    if (score >= 0.5) return 'medium-confidence';
    return 'low-confidence';
  };
  
  return (
    <div className="results-container">
      <div className="results-tabs">
        <button 
          className={`tab-button ${activeTab === 'answer' ? 'active' : ''}`} 
          onClick={() => setActiveTab('answer')}
        >
          Yanıt
        </button>
        <button 
          className={`tab-button ${activeTab === 'docs' ? 'active' : ''}`} 
          onClick={() => setActiveTab('docs')}
        >
          Kaynaklar ({retrievedDocs.length})
        </button>
      </div>
      
      <div className="results-content">
        {activeTab === 'answer' && (
          <div className="answer-container">
            {showHallucinationWarning && (
              <div className="hallucination-warning">
                <span className="warning-icon">⚠️</span>
                <span>Bu yanıt, verilen belgelerde bulunmayan bilgiler içeriyor olabilir.</span>
              </div>
            )}
            
            {confidence_score !== undefined && (
              <div className={`confidence-indicator ${getConfidenceColor(confidence_score)}`}>
                <span className="confidence-label">Güven Skoru:</span>
                <span className="confidence-value">{Math.round(confidence_score * 100)}%</span>
              </div>
            )}
            
            <div className="answer-text" 
                dangerouslySetInnerHTML={{ __html: formattedAnswer }} 
            />
            
            {citations && citations.length > 0 && (
              <div className="citations-section">
                <h3>Referanslar</h3>
                <ul className="citation-list">
                  {citations.map((citation, index) => (
                    <li key={`citation-${index}`} className="citation-item" id={`citation-${citation.id}`}>
                      [{citation.id}] <span className="citation-text">{citation.text}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
        
        {activeTab === 'docs' && (
          <div className="docs-container">
            <h3>Bulunan Kaynaklar</h3>
            
            {retrievedDocs.length > 0 ? (
              <ul className="docs-list">
                {retrievedDocs.map((doc, index) => (
                  <li key={`doc-${index}`} className="doc-item">
                    <div className="doc-header">
                      <h4 className="doc-title">
                        {doc.source_info && doc.source_info.title 
                          ? doc.source_info.title 
                          : `Belge #${index + 1}`}
                      </h4>
                      {doc.score !== undefined && (
                        <span className="doc-score">Skor: {doc.score.toFixed(2)}</span>
                      )}
                    </div>
                    
                    <div className="doc-meta">
                      {doc.source_info && doc.source_info.source_type && (
                        <span className="meta-tag source-type">
                          {doc.source_info.source_type}
                        </span>
                      )}
                      
                      {doc.timestamp && (
                        <span className="meta-tag timestamp">
                          {new Date(doc.timestamp).toLocaleDateString()}
                        </span>
                      )}
                      
                      {doc.category && (
                        <span className="meta-tag category">
                          {doc.category}
                        </span>
                      )}
                      
                      {doc.author && (
                        <span className="meta-tag author">
                          Yazar: {doc.author}
                        </span>
                      )}
                    </div>
                    
                    <div className="doc-text">{doc.text}</div>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="empty-docs">Hiç belge bulunamadı.</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Results;