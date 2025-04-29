// Last reviewed: 2025-04-29 10:59:14 UTC (User: Teekssseksiklikleri)
import React, { useState, useEffect } from 'react';
import { useToast } from '../contexts/ToastContext';
import useApi from '../hooks/useApi';
import './ConfigEditor.css';

const ConfigEditor = () => {
  const { showToast } = useToast();
  const { apiRequest, isLoading } = useApi();
  
  const [configItems, setConfigItems] = useState([]);
  const [editedConfig, setEditedConfig] = useState({});
  const [activeCategory, setActiveCategory] = useState('retrieval');
  const [isEditing, setIsEditing] = useState(false);
  
  // Kategori listesi
  const categories = [
    { id: 'retrieval', name: 'Retrieval Ayarları' },
    { id: 'priority', name: 'Önceliklendirme Ayarları' },
    { id: 'hybrid_search', name: 'Hibrit Arama Ayarları' },
    { id: 'api_keys', name: 'API Anahtar Ayarları' },
    { id: 'security', name: 'Güvenlik Ayarları' },
    { id: 'notifications', name: 'Bildirim Ayarları' }
  ];
  
  // Kategoriye göre konfigürasyon açıklamaları
  const configDescriptions = {
    // Retrieval ayarları
    'ES_KNN_K': 'İlk arama aşamasında kaç belge getirileceğini belirler',
    'ES_KNN_K_MULTIPLIER': 'KNN aday çarpanı',
    'ES_KNN_NUM_CANDIDATES': 'KNN sorgusunda incelenecek aday sayısı',
    'VECTOR_DIMENSION': 'Vektör embed boyutu',
    
    // Önceliklendirme ayarları
    'PRIORITY_CORPORATE_DOCS': 'Kurumsal belgelere uygulanacak skor çarpanı',
    'PRIORITY_RECENT_DOCS': 'Son 30 günlük belgelere uygulanacak skor çarpanı',
    'PRIORITY_REVIEWED_DOCS': 'İncelenmiş belgelere uygulanacak skor çarpanı',
    'PRIORITY_DOMAINS': 'Öncelikli alan adları (virgülle ayrılmış)',
    
    // Hibrit arama ayarları
    'BM25_BOOST': 'BM25 algoritması ağırlığı',
    'SEMANTIC_BOOST': 'Anlamsal algoritma ağırlığı',
    'HYBRID_METHOD': 'Hibrit arama yöntemi',
    'PERSONALIZATION_WEIGHT': 'Kişiselleştirme ağırlığı',
    
    // API anahtar ayarları
    'API_CACHING_TTL': 'API anahtarı önbellek süresi (saniye)',
    'API_VERIFY_INTERVAL': 'API anahtarı doğrulama aralığı (saat)',
    'API_MAX_FAILURES': 'Maksimum başarısız API doğrulama sayısı',
    
    // Güvenlik ayarları
    'ACCESS_TOKEN_EXPIRE_MINUTES': 'Erişim token süresi (dakika)',
    'SECURITY_LOG_RETENTION': 'Güvenlik loglarının tutulma süresi (gün)',
    'RATE_LIMIT_DEFAULT': 'Varsayılan rate limit (dakika başına istek)',
    
    // Bildirim ayarları
    'EMAIL_NOTIFICATIONS_ENABLED': 'E-posta bildirimleri',
    'WEBHOOK_NOTIFICATIONS_ENABLED': 'Webhook bildirimleri',
    'NOTIFICATION_MIN_SEVERITY': 'Minimum bildirim seviyesi',
  };
  
  // Karşılık gelen ayar grupları
  const categoryConfigMapping = {
    'retrieval': ['ES_KNN_K', 'ES_KNN_K_MULTIPLIER', 'ES_KNN_NUM_CANDIDATES', 'VECTOR_DIMENSION'],
    'priority': ['PRIORITY_CORPORATE_DOCS', 'PRIORITY_RECENT_DOCS', 'PRIORITY_REVIEWED_DOCS', 'PRIORITY_DOMAINS'],
    'hybrid_search': ['BM25_BOOST', 'SEMANTIC_BOOST', 'HYBRID_METHOD', 'PERSONALIZATION_WEIGHT'],
    'api_keys': ['API_CACHING_TTL', 'API_VERIFY_INTERVAL', 'API_MAX_FAILURES'],
    'security': ['ACCESS_TOKEN_EXPIRE_MINUTES', 'SECURITY_LOG_RETENTION', 'RATE_LIMIT_DEFAULT'],
    'notifications': ['EMAIL_NOTIFICATIONS_ENABLED', 'WEBHOOK_NOTIFICATIONS_ENABLED', 'NOTIFICATION_MIN_SEVERITY']
  };
  
  // Form alan tipleri
  const configTypes = {
    'PRIORITY_CORPORATE_DOCS': 'number',
    'PRIORITY_RECENT_DOCS': 'number',
    'PRIORITY_REVIEWED_DOCS': 'number',
    'PRIORITY_DOMAINS': 'text',
    'BM25_BOOST': 'number',
    'SEMANTIC_BOOST': 'number',
    'PERSONALIZATION_WEIGHT': 'number',
    'ES_KNN_K': 'number',
    'ES_KNN_K_MULTIPLIER': 'number',
    'ES_KNN_NUM_CANDIDATES': 'number',
    'VECTOR_DIMENSION': 'number',
    'API_CACHING_TTL': 'number',
    'API_VERIFY_INTERVAL': 'number',
    'API_MAX_FAILURES': 'number',
    'ACCESS_TOKEN_EXPIRE_MINUTES': 'number',
    'SECURITY_LOG_RETENTION': 'number',
    'RATE_LIMIT_DEFAULT': 'number',
    'HYBRID_METHOD': 'select',
    'EMAIL_NOTIFICATIONS_ENABLED': 'boolean',
    'WEBHOOK_NOTIFICATIONS_ENABLED': 'boolean',
    'NOTIFICATION_MIN_SEVERITY': 'select'
  };
  
  // Select alanları için seçenekler
  const configOptions = {
    'HYBRID_METHOD': [
      { value: 'rank_fusion', label: 'Rank Fusion' },
      { value: 'rrf', label: 'Reciprocal Rank Fusion' },
      { value: 'linear_combination', label: 'Linear Combination' }
    ],
    'NOTIFICATION_MIN_SEVERITY': [
      { value: 'info', label: 'Bilgi (Info)' },
      { value: 'warning', label: 'Uyarı (Warning)' },
      { value: 'error', label: 'Hata (Error)' },
      { value: 'critical', label: 'Kritik (Critical)' }
    ]
  };
  
  // İlk yüklemede ayarları al
  useEffect(() => {
    fetchConfigs();
  }, []);
  
  const fetchConfigs = async () => {
    try {
      const data = await apiRequest('/api/admin/config');
      setConfigItems(data.items || []);
      
      // Düzenleme için başlangıç değerlerini ayarla
      const initialValues = {};
      data.items.forEach(item => {
        initialValues[item.key] = item.value;
      });
      
      setEditedConfig(initialValues);
    } catch (error) {
      showToast('Konfigürasyon yüklenirken hata oluştu', 'error');
    }
  };
  
  const handleEditClick = () => {
    setIsEditing(true);
  };
  
  const handleCancelClick = () => {
    setIsEditing(false);
    
    // Değerleri sıfırla
    const initialValues = {};
    configItems.forEach(item => {
      initialValues[item.key] = item.value;
    });
    
    setEditedConfig(initialValues);
  };
  
  const handleSaveClick = async () => {
    try {
      // Sadece değiştirilen değerleri gönder
      const changes = {};
      for (const [key, value] of Object.entries(editedConfig)) {
        const originalItem = configItems.find(item => item.key === key);
        if (originalItem && originalItem.value !== value) {
          changes[key] = value;
        }
      }
      
      // Değişiklik yoksa erken çık
      if (Object.keys(changes).length === 0) {
        showToast('Değişiklik yapılmadı', 'info');
        setIsEditing(false);
        return;
      }
      
      await apiRequest('/api/admin/config', {
        method: 'POST',
        body: JSON.stringify({ changes })
      });
      
      showToast('Konfigürasyon başarıyla güncellendi', 'success');
      setIsEditing(false);
      
      // Yeni ayarları yükle
      fetchConfigs();
    } catch (error) {
      showToast('Konfigürasyon güncellenirken hata oluştu', 'error');
    }
  };
  
  const handleConfigChange = (key, value) => {
    setEditedConfig(prev => ({
      ...prev,
      [key]: value
    }));
  };
  
  const renderConfigInput = (key, value) => {
    const type = configTypes[key] || 'text';
    
    switch (type) {
      case 'number':
        return (
          <input
            type="number"
            value={value}
            onChange={(e) => handleConfigChange(key, parseFloat(e.target.value))}
            disabled={!isEditing}
            step="0.1"
            className="config-input"
          />
        );
        
      case 'boolean':
        return (
          <select
            value={String(value)}
            onChange={(e) => handleConfigChange(key, e.target.value === 'true')}
            disabled={!isEditing}
            className="config-select"
          >
            <option value="true">Aktif</option>
            <option value="false">Pasif</option>
          </select>
        );
        
      case 'select':
        return (
          <select
            value={value}
            onChange={(e) => handleConfigChange(key, e.target.value)}
            disabled={!isEditing}
            className="config-select"
          >
            {configOptions[key].map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        );
        
      default:
        return (
          <input
            type="text"
            value={value}
            onChange={(e) => handleConfigChange(key, e.target.value)}
            disabled={!isEditing}
            className="config-input"
          />
        );
    }
  };
  
  // Aktif kategoriye ait konfigürasyon anahtarlarını filtrele
  const filteredConfigItems = configItems.filter(item => 
    categoryConfigMapping[activeCategory]?.includes(item.key)
  );
  
  return (
    <div className="config-editor">
      <h2>Sistem Konfigürasyonu</h2>
      
      <div className="config-editor-toolbar">
        <div className="category-tabs">
          {categories.map(category => (
            <button
              key={category.id}
              className={`category-tab ${activeCategory === category.id ? 'active' : ''}`}
              onClick={() => setActiveCategory(category.id)}
            >
              {category.name}
            </button>
          ))}
        </div>
        
        <div className="action-buttons">
          {!isEditing ? (
            <button 
              className="edit-button"
              onClick={handleEditClick}
            >
              <i className="fa fa-edit"></i> Düzenle
            </button>
          ) : (
            <>
              <button 
                className="save-button"
                onClick={handleSaveClick}
                disabled={isLoading}
              >
                <i className="fa fa-save"></i> Kaydet
              </button>
              <button 
                className="cancel-button"
                onClick={handleCancelClick}
              >
                <i className="fa fa-times"></i> İptal
              </button>
            </>
          )}
        </div>
      </div>
      
      <div className="config-list">
        <div className="category-title">{categories.find(c => c.id === activeCategory)?.name}</div>
        
        {filteredConfigItems.length === 0 && (
          <p className="no-items">Bu kategoride yapılandırma öğesi bulunamadı.</p>
        )}
        
        {filteredConfigItems.map(item => (
          <div key={item.key} className="config-item">
            <div className="config-info">
              <div className="config-key">{item.key}</div>
              <div className="config-description">{configDescriptions[item.key] || "Açıklama yok"}</div>
            </div>
            <div className="config-value">
              {renderConfigInput(item.key, editedConfig[item.key] !== undefined ? editedConfig[item.key] : item.value)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ConfigEditor;