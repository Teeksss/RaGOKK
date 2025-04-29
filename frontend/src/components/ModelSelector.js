// Last reviewed: 2025-04-29 08:53:08 UTC (User: Teekssseskikleri)
import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import useApi from '../hooks/useApi';
import './ModelSelector.css';

const ModelSelector = ({ onModelChange, className = '' }) => {
  const { isLoggedIn, isAdmin } = useAuth();
  const { showToast } = useToast();
  const { apiRequest, isLoading } = useApi();
  
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState(null);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedModelInfo, setSelectedModelInfo] = useState(null);
  
  // Model listesini yükle
  useEffect(() => {
    if (isLoggedIn) {
      loadModels();
    }
  }, [isLoggedIn]);
  
  const loadModels = async () => {
    try {
      const data = await apiRequest('/api/models/available');
      
      // Sadece aktif modelleri filtrele
      const activeModels = data.filter(model => model.is_active);
      setModels(activeModels);
      
      // Varsayılan modeli seç
      if (activeModels.length > 0) {
        const defaultModel = activeModels.find(m => m.id === 'default');
        if (defaultModel) {
          setSelectedModel(defaultModel.id);
          setSelectedModelInfo(defaultModel);
          if (onModelChange) onModelChange(defaultModel.id);
        }
      }
    } catch (error) {
      console.error('Model listesi yükleme hatası:', error);
    }
  };
  
  const handleModelSelect = (modelId) => {
    const model = models.find(m => m.id === modelId);
    if (!model) return;
    
    // Admin değilse ve admin-only model ise engelle
    if (!isAdmin && model.is_admin_only) {
      showToast('Bu modele erişim izniniz yok', 'error');
      return;
    }
    
    setSelectedModel(modelId);
    setSelectedModelInfo(model);
    setIsOpen(false);
    
    if (onModelChange) {
      onModelChange(modelId);
    }
    
    showToast(`Model değiştirildi: ${model.name}`, 'info');
  };
  
  const getModelIcon = (model) => {
    const family = model.family || 'other';
    
    switch (family) {
      case 'gpt':
        return '🤖';
      case 'llama':
        return '🦙';
      case 'mistral':
        return '🌪️';
      case 'phi':
        return '🔬';
      case 'falcon':
        return '🦅';
      case 't5':
        return '📊';
      default:
        return '🧠';
    }
  };
  
  if (!isLoggedIn || models.length === 0) {
    return null;
  }
  
  return (
    <div className={`model-selector ${className}`}>
      <div className="model-selector-label">Model:</div>
      <div className="model-dropdown-container">
        <button 
          className="model-dropdown-button" 
          onClick={() => setIsOpen(!isOpen)}
          disabled={isLoading}
        >
          {selectedModelInfo && (
            <>
              <span className="model-icon">{getModelIcon(selectedModelInfo)}</span>
              <span className="model-name">{selectedModelInfo.name}</span>
            </>
          )}
          <span className="dropdown-arrow">{isOpen ? '▲' : '▼'}</span>
        </button>
        
        {isOpen && (
          <div className="model-dropdown-menu">
            {models.map(model => (
              <div 
                key={model.id} 
                className={`model-option ${model.id === selectedModel ? 'selected' : ''} ${!isAdmin && model.is_admin_only ? 'disabled' : ''}`}
                onClick={() => handleModelSelect(model.id)}
              >
                <span className="model-icon">{getModelIcon(model)}</span>
                <div className="model-details">
                  <div className="model-name">{model.name}</div>
                  <div className="model-type">
                    {model.type === 'local' && 'Yerel model'}
                    {model.type === 'openai' && 'OpenAI API'}
                    {model.type === 'finetuned' && 'Fine-tuned model'}
                    {model.family && ` - ${model.family.toUpperCase()}`}
                  </div>
                </div>
                {model.is_admin_only && <div className="admin-badge">Admin</div>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ModelSelector;