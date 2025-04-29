// Last reviewed: 2025-04-29 08:20:31 UTC (User: Teekssstüm)
import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import useApi from '../hooks/useApi';
import Spinner from './ui/Spinner';
import './ModelManagement.css';

const ModelManagement = () => {
  const { isAdmin } = useAuth();
  const { showToast } = useToast();
  const { apiRequest, isLoading } = useApi();
  
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState(null);
  const [isModelDetailsOpen, setIsModelDetailsOpen] = useState(false);
  
  // Model listesini yükle
  const loadModels = useCallback(async () => {
    try {
      const data = await apiRequest("/api/models");
      setModels(data || []);
    } catch (error) {
      showToast(`Model listesi yüklenemedi: ${error.message}`, 'error');
    }
  }, [apiRequest, showToast]);
  
  useEffect(() => {
    loadModels();
  }, [loadModels]);
  
  const formatSize = (sizeKb) => {
    if (sizeKb < 1024) {
      return `${sizeKb} KB`;
    } else {
      return `${(sizeKb / 1024).toFixed(2)} MB`;
    }
  };
  
  const handleModelSelect = (model) => {
    setSelectedModel(model);
    setIsModelDetailsOpen(true);
  };
  
  if (!isAdmin) {
    return null;
  }
  
  return (
    <div className="model-management-container">
      <h2>Model Yönetimi</h2>
      
      {isLoading ? (
        <div className="loading-container">
          <Spinner /> <span>Modeller yükleniyor...</span>
        </div>
      ) : models.length === 0 ? (
        <div className="no-models">
          <p>Henüz kaydedilmiş model yok.</p>
        </div>
      ) : (
        <div className="models-grid">
          {models.map(model => (
            <div 
              key={model.id} 
              className="model-card"
              onClick={() => handleModelSelect(model)}
            >
              <div className="model-header">
                <h3 className="model-name">{model.name}</h3>
                <span className={`model-status ${model.is_active ? 'active' : 'inactive'}`}>
                  {model.is_active ? 'Aktif' : 'Pasif'}
                </span>
              </div>
              <div className="model-info">
                <p><strong>Baz Model:</strong> {model.base_model}</p>
                <p><strong>Tür:</strong> {model.type}</p>
                <p><strong>Boyut:</strong> {formatSize(model.size_kb)}</p>
                <p><strong>Oluşturulma:</strong> {new Date(model.created_at).toLocaleDateString()}</p>
              </div>
            </div>
          ))}
        </div>
      )}
      
      {isModelDetailsOpen && selectedModel && (
        <div className="model-details-modal">
          <div className="model-details-content">
            <div className="modal-header">
              <h3>{selectedModel.name}</h3>
              <button 
                className="close-button" 
                onClick={() => setIsModelDetailsOpen(false)}
              >
                &times;
              </button>
            </div>
            <div className="model-details-body">
              <div className="details-section">
                <h4>Genel Bilgiler</h4>
                <ul>
                  <li><strong>Model ID:</strong> {selectedModel.id}</li>
                  <li><strong>Baz Model:</strong> {selectedModel.base_model}</li>
                  <li><strong>Tür:</strong> {selectedModel.type}</li>
                  <li><strong>Boyut:</strong> {formatSize(selectedModel.size_kb)}</li>
                  <li><strong>Oluşturulma:</strong> {new Date(selectedModel.created_at).toLocaleDateString()}</li>
                  <li><strong>Sahip:</strong> {selectedModel.owner || 'Sistem'}</li>
                </ul>
              </div>
              
              {selectedModel.metrics && (
                <div className="details-section">
                  <h4>Performans Metrikleri</h4>
                  <ul>
                    {Object.entries(selectedModel.metrics).map(([key, value]) => (
                      <li key={key}><strong>{key}:</strong> {typeof value === 'number' ? value.toFixed(4) : value}</li>
                    ))}
                  </ul>
                </div>
              )}
              
              {selectedModel.parameters && (
                <div className="details-section">
                  <h4>Parametreler</h4>
                  <pre>{JSON.stringify(selectedModel.parameters, null, 2)}</pre>
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button 
                className="primary-button"
                onClick={() => {
                  // Model seçme/etkinleştirme fonksiyonelliği
                  showToast(`Model seçildi: ${selectedModel.name}`, 'success');
                  setIsModelDetailsOpen(false);
                }}
              >
                Bu Modeli Kullan
              </button>
              <button 
                className="secondary-button"
                onClick={() => setIsModelDetailsOpen(false)}
              >
                Kapat
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ModelManagement;