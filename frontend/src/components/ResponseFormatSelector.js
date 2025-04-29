// Last reviewed: 2025-04-29 08:53:08 UTC (User: Teekssseskikleri)
import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import useApi from '../hooks/useApi';
import './ResponseFormatSelector.css';

const ResponseFormatSelector = ({ onFormatChange, className = '' }) => {
  const { isLoggedIn } = useAuth();
  const { showToast } = useToast();
  const { apiRequest, isLoading } = useApi();
  
  const [formats, setFormats] = useState([]);
  const [selectedFormat, setSelectedFormat] = useState('default');
  const [isOpen, setIsOpen] = useState(false);
  
  // Format bilgilerini yükle
  useEffect(() => {
    if (isLoggedIn) {
      loadFormats();
    }
  }, [isLoggedIn]);
  
  const loadFormats = async () => {
    try {
      const data = await apiRequest('/api/response-formats');
      setFormats(data);
      
      // Varsayılan formatı seç
      const defaultFormat = data.find(f => f.is_default) || data.find(f => f.id === 'default');
      if (defaultFormat) {
        setSelectedFormat(defaultFormat.id);
        if (onFormatChange) onFormatChange(defaultFormat.id);
      }
    } catch (error) {
      console.error('Format yükleme hatası:', error);
    }
  };
  
  const handleFormatSelect = async (formatId) => {
    setSelectedFormat(formatId);
    setIsOpen(false);
    
    if (onFormatChange) {
      onFormatChange(formatId);
    }
    
    // Varsayılan format olarak kaydet
    try {
      await apiRequest('/api/response-format-preference', {
        method: 'POST',
        body: JSON.stringify({ format_id: formatId })
      });
      showToast('Yanıt biçimi tercihiniz kaydedildi', 'success');
    } catch (error) {
      console.error('Format tercihi kaydetme hatası:', error);
    }
  };
  
  if (!isLoggedIn || formats.length === 0) {
    return null;
  }
  
  const selectedFormatInfo = formats.find(f => f.id === selectedFormat) || formats[0];
  
  return (
    <div className={`response-format-selector ${className}`}>
      <div className="format-selector-label">Yanıt biçimi:</div>
      <div className="format-dropdown-container">
        <button 
          className="format-dropdown-button" 
          onClick={() => setIsOpen(!isOpen)}
          disabled={isLoading}
        >
          <span>{selectedFormatInfo.name}</span>
          <span className="dropdown-arrow">{isOpen ? '▲' : '▼'}</span>
        </button>
        
        {isOpen && (
          <div className="format-dropdown-menu">
            {formats.map(format => (
              <div 
                key={format.id} 
                className={`format-option ${format.id === selectedFormat ? 'selected' : ''}`}
                onClick={() => handleFormatSelect(format.id)}
              >
                <div className="format-name">{format.name}</div>
                <div className="format-description">{format.description}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ResponseFormatSelector;