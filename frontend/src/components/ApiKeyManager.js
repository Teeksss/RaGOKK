// Last reviewed: 2025-04-29 09:15:13 UTC (User: TeeksssAPI)
import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import useApi from '../hooks/useApi';
import './ApiKeyManager.css';

const ApiKeyManager = () => {
  const { isAdmin } = useAuth();
  const { showToast } = useToast();
  const { apiRequest, isLoading } = useApi();

  const [providers, setProviders] = useState([]);
  const [apiKeys, setApiKeys] = useState([]);
  const [keyStatus, setKeyStatus] = useState({});
  const [selectedProvider, setSelectedProvider] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState({
    provider: '',
    api_key: '',
    description: '',
    is_active: true,
    metadata: {}
  });
  const [isEditing, setIsEditing] = useState(false);
  const [showKey, setShowKey] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [verificationResult, setVerificationResult] = useState(null);

  // API sağlayıcıları ve mevcut anahtarların durumunu yükle
  useEffect(() => {
    if (isAdmin) {
      loadApiProviders();
      loadApiKeyStatus();
    }
  }, [isAdmin]);

  const loadApiProviders = async () => {
    try {
      const data = await apiRequest('/api/api-providers');
      setProviders(data || []);
    } catch (error) {
      showToast(`API sağlayıcıları yüklenemedi: ${error.message}`, 'error');
    }
  };

  const loadApiKeyStatus = async () => {
    try {
      const data = await apiRequest('/api/api-keys/status');
      setKeyStatus(data || {});
      
      // Admin ise tam anahtar listesini de yükle
      if (isAdmin) {
        loadApiKeys();
      }
    } catch (error) {
      showToast(`API anahtarı durumu yüklenemedi: ${error.message}`, 'error');
    }
  };

  const loadApiKeys = async () => {
    try {
      const data = await apiRequest('/api/api-keys');
      setApiKeys(data || []);
    } catch (error) {
      showToast(`API anahtarları yüklenemedi: ${error.message}`, 'error');
    }
  };

  // Anahtar detaylarını yükle
  const loadKeyDetails = async (provider) => {
    try {
      const data = await apiRequest(`/api/api-keys/${provider}`);
      setSelectedProvider(data);
    } catch (error) {
      showToast(`API anahtarı detayları yüklenemedi: ${error.message}`, 'error');
    }
  };

  // Anahtar oluştur veya güncelle
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      if (isEditing) {
        // Sadece değiştirilen alanları içerecek şekilde güncelleme verisi oluştur
        const updateData = {};
        if (formData.api_key) updateData.api_key = formData.api_key;
        if (formData.description !== selectedProvider.description) updateData.description = formData.description;
        if (formData.is_active !== selectedProvider.is_active) updateData.is_active = formData.is_active;
        
        // API Anahtarı güncelle
        await apiRequest(`/api/api-keys/${formData.provider}`, {
          method: 'PUT',
          body: JSON.stringify(updateData)
        });
        showToast('API anahtarı güncellendi', 'success');
      } else {
        // Yeni API anahtarı oluştur
        await apiRequest('/api/api-keys', {
          method: 'POST',
          body: JSON.stringify(formData)
        });
        showToast('API anahtarı eklendi', 'success');
      }
      
      // Modal kapat ve veri yenile
      setIsModalOpen(false);
      loadApiKeys();
      loadApiKeyStatus();
      resetForm();
    } catch (error) {
      showToast(`API anahtarı kaydedilemedi: ${error.message}`, 'error');
    }
  };

  // Anahtar sil
  const handleDelete = async () => {
    try {
      await apiRequest(`/api/api-keys/${selectedProvider.provider}`, {
        method: 'DELETE'
      });
      showToast('API anahtarı silindi', 'success');
      
      // Modal kapat ve veri yenile
      setIsModalOpen(false);
      setIsDeleting(false);
      loadApiKeys();
      loadApiKeyStatus();
      setSelectedProvider(null);
    } catch (error) {
      showToast(`API anahtarı silinemedi: ${error.message}`, 'error');
    }
  };

  // API anahtarını doğrula
  const verifyApiKey = async (provider) => {
    setIsVerifying(true);
    setVerificationResult(null);
    
    try {
      const result = await apiRequest(`/api/api-keys/verify/${provider}`);
      setVerificationResult(result);
      
      if (result.is_valid) {
        showToast('API anahtarı doğrulandı', 'success');
      } else {
        showToast(`API anahtarı doğrulanamadı: ${result.message}`, 'warning');
      }
    } catch (error) {
      showToast(`API anahtarı doğrulanırken hata oluştu: ${error.message}`, 'error');
    } finally {
      setIsVerifying(false);
    }
  };

  // Form alanları değiştiğinde state güncelle
  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData({
      ...formData,
      [name]: type === 'checkbox' ? checked : value
    });
  };

  // Form resetle
  const resetForm = () => {
    setFormData({
      provider: '',
      api_key: '',
      description: '',
      is_active: true,
      metadata: {}
    });
    setIsEditing(false);
    setShowKey(false);
  };

  // Modal'ı aç - Yeni anahtar ekleme
  const openAddModal = (provider) => {
    setSelectedProvider(null);
    setIsEditing(false);
    resetForm();
    setFormData({ ...formData, provider });
    setIsModalOpen(true);
  };

  // Modal'ı aç - Anahtar düzenleme
  const openEditModal = (provider) => {
    const key = apiKeys.find(k => k.provider === provider);
    setSelectedProvider(key);
    setIsEditing(true);
    setFormData({
      provider: key.provider,
      api_key: '',  // API anahtarı güncellenmeyecekse boş bırakılır
      description: key.description || '',
      is_active: key.is_active,
      metadata: key.metadata || {}
    });
    setIsModalOpen(true);
  };

  // Modal'ı kapat
  const closeModal = () => {
    setIsModalOpen(false);
    resetForm();
  };

  // API anahtarı durumuna göre renk ve icon belirle
  const getStatusInfo = (provider) => {
    const status = keyStatus[provider];
    if (!status) return { color: 'gray', icon: '❓', text: 'Bilinmiyor' };
    
    if (isAdmin) {
      if (!status.is_configured) return { color: 'gray', icon: '🔘', text: 'Yapılandırılmamış' };
      if (!status.is_active) return { color: 'red', icon: '⛔', text: 'Devre Dışı' };
      return { color: 'green', icon: '✅', text: 'Etkin' };
    } else {
      if (!status.is_available) return { color: 'gray', icon: '🔘', text: 'Kullanılamıyor' };
      return { color: 'green', icon: '✅', text: 'Kullanılabilir' };
    }
  };

  // Modal içeriğini göster
  const renderModalContent = () => {
    if (isDeleting) {
      return (
        <div className="api-key-modal-content">
          <h2>API Anahtarını Sil</h2>
          <p><strong>Uyarı:</strong> "{selectedProvider.provider}" sağlayıcısına ait API anahtarını silmek istediğinizden emin misiniz?</p>
          <p>Bu işlem geri alınamaz ve ilgili servislerle bağlantıyı kesebilir.</p>
          
          <div className="modal-footer">
            <button
              className="delete-button"
              onClick={handleDelete}
              disabled={isLoading}
            >
              {isLoading ? 'İşleniyor...' : 'Evet, Sil'}
            </button>
            <button
              className="cancel-button"
              onClick={() => setIsDeleting(false)}
              disabled={isLoading}
            >
              İptal
            </button>
          </div>
        </div>
      );
    }
    
    return (
      <div className="api-key-modal-content">
        <h2>{isEditing ? 'API Anahtarını Düzenle' : 'API Anahtarı Ekle'}</h2>
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Sağlayıcı:</label>
            <select
              name="provider"
              value={formData.provider}
              onChange={handleInputChange}
              disabled={isEditing}
              required
            >
              <option value="">Seçiniz</option>
              {providers.map(provider => (
                <option key={provider.id} value={provider.id}>{provider.name}</option>
              ))}
            </select>
          </div>
          
          <div className="form-group">
            <label>API Anahtarı:</label>
            <div className="password-input-container">
              <input
                name="api_key"
                type={showKey ? "text" : "password"}
                value={formData.api_key}
                onChange={handleInputChange}
                placeholder={isEditing ? "(değiştirmek için girin)" : "API anahtarını girin"}
                required={!isEditing}
              />
              <button
                type="button"
                className="toggle-password"
                onClick={() => setShowKey(!showKey)}
              >
                {showKey ? "🔒" : "👁️"}
              </button>
            </div>
          </div>
          
          <div className="form-group">
            <label>Açıklama:</label>
            <input
              name="description"
              type="text"
              value={formData.description}
              onChange={handleInputChange}
              placeholder="API anahtarı hakkında açıklama"
            />
          </div>
          
          <div className="form-group checkbox">
            <label>
              <input
                name="is_active"
                type="checkbox"
                checked={formData.is_active}
                onChange={handleInputChange}
              />
              Etkin
            </label>
          </div>
          
          <div className="modal-footer">
            <button
              type="submit"
              className="save-button"
              disabled={isLoading}
            >
              {isLoading ? 'Kaydediliyor...' : 'Kaydet'}
            </button>
            <button
              type="button"
              className="cancel-button"
              onClick={closeModal}
              disabled={isLoading}
            >
              İptal
            </button>
          </div>
        </form>
      </div>
    );
  };

  if (!isAdmin) {
    return (
      <div className="api-key-manager">
        <h2>API Servisleri</h2>
        <p>API servislerinin durumunu görüntüleyebilirsiniz.</p>
        
        <div className="api-providers-list">
          {providers.map(provider => {
            const status = getStatusInfo(provider.id);
            
            return (
              <div key={provider.id} className="api-provider-card">
                <div className="provider-icon">
                  <img src={`/assets/icons/${provider.icon}`} alt={provider.name} />
                </div>
                <div className="provider-details">
                  <h3>{provider.name}</h3>
                  <p className="provider-description">{provider.description}</p>
                  <div className="provider-status">
                    <span className={`status-indicator ${status.color}`}>
                      {status.icon} {status.text}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  return (
    <div className="api-key-manager">
      <h2>API Anahtarları Yönetimi</h2>
      <p>Çeşitli servisler için API anahtarlarını yönetin.</p>
      
      <div className="api-providers-grid">
        {providers.map(provider => {
          const status = getStatusInfo(provider.id);
          const apiKey = apiKeys.find(k => k.provider === provider.id);
          const isConfigured = keyStatus[provider.id]?.is_configured || false;
          
          return (
            <div key={provider.id} className="api-provider-card">
              <div className="provider-icon">
                <img src={`/assets/icons/${provider.icon}`} alt={provider.name} />
              </div>
              <div className="provider-details">
                <h3>{provider.name}</h3>
                <div className="provider-category">{provider.category}</div>
                <div className="provider-status">
                  <span className={`status-indicator ${status.color}`}>
                    {status.icon} {status.text}
                  </span>
                </div>
                {apiKey && (
                  <div className="api-key-info">
                    <div className="key-last-updated">
                      Son güncelleme: {new Date(apiKey.updated_at || apiKey.created_at).toLocaleString()}
                    </div>
                  </div>
                )}
              </div>
              <div className="provider-actions">
                {!isConfigured ? (
                  <button 
                    className="add-key-button"
                    onClick={() => openAddModal(provider.id)}
                  >
                    API Anahtarı Ekle
                  </button>
                ) : (
                  <div className="action-buttons">
                    <button 
                      className="verify-key-button"
                      onClick={() => verifyApiKey(provider.id)}
                      disabled={isVerifying}
                    >
                      {isVerifying ? 'Doğrulanıyor...' : 'Doğrula'}
                    </button>
                    <button 
                      className="edit-key-button"
                      onClick={() => openEditModal(provider.id)}
                    >
                      Düzenle
                    </button>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Modal */}
      {isModalOpen && (
        <div className="api-key-modal-overlay">
          <div className="api-key-modal">
            <button className="close-modal" onClick={closeModal}>&times;</button>
            {renderModalContent()}
          </div>
        </div>
      )}
      
      {/* Doğrulama Sonuçları */}
      {verificationResult && (
        <div className={`verification-result ${verificationResult.is_valid ? 'success' : 'error'}`}>
          <h3>Doğrulama Sonucu: {verificationResult.provider}</h3>
          <p><strong>Durum:</strong> {verificationResult.is_valid ? 'Geçerli' : 'Geçersiz'}</p>
          <p><strong>Mesaj:</strong> {verificationResult.message}</p>
          {verificationResult.details && (
            <div className="verification-details">
              <strong>Detaylar:</strong>
              <pre>{JSON.stringify(verificationResult.details, null, 2)}</pre>
            </div>
          )}
          <button onClick={() => setVerificationResult(null)}>Kapat</button>
        </div>
      )}
    </div>
  );
};

export default ApiKeyManager;