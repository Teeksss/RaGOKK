// Last reviewed: 2025-04-29 10:34:18 UTC (User: Teekssseksikleri)
import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import useApi from '../hooks/useApi';
import './ApiKeysMonitor.css';

const ApiKeysMonitor = () => {
  const { isAdmin } = useAuth();
  const { showToast } = useToast();
  const { apiRequest, isLoading } = useApi();
  
  const [keyStatus, setKeyStatus] = useState({});
  const [securityLogs, setSecurityLogs] = useState([]);
  const [logsPage, setLogsPage] = useState(1);
  const [totalLogs, setTotalLogs] = useState(0);
  const [logsPerPage, setLogsPerPage] = useState(10);
  const [refreshInterval, setRefreshInterval] = useState(60); // saniye
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [filterProvider, setFilterProvider] = useState('all');
  const [filterAction, setFilterAction] = useState('all');
  const [filterSuccess, setFilterSuccess] = useState('all');
  
  const intervalRef = useRef(null);
  
  // İlk yükleme
  useEffect(() => {
    loadData();
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);
  
  // Oto-yenileme
  useEffect(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
    
    if (autoRefresh && refreshInterval > 0) {
      intervalRef.current = setInterval(() => {
        loadData();
      }, refreshInterval * 1000);
    }
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [autoRefresh, refreshInterval]);
  
  // Sayfa değişiminde logları güncelle
  useEffect(() => {
    loadSecurityLogs();
  }, [logsPage, logsPerPage, filterProvider, filterAction, filterSuccess]);
  
  const loadData = async () => {
    await loadApiKeyStatus();
    await loadSecurityLogs();
    setLastUpdated(new Date());
  };
  
  const loadApiKeyStatus = async () => {
    try {
      const data = await apiRequest('/api/api-keys/status');
      setKeyStatus(data || {});
    } catch (error) {
      console.error('API key status loading error:', error);
    }
  };
  
  const loadSecurityLogs = async () => {
    if (!isAdmin) {
      return;
    }
    
    try {
      // Filtre parametreleri hazırla
      const params = new URLSearchParams({
        page: logsPage,
        limit: logsPerPage,
        log_type: 'api_key'
      });
      
      // Provider filtresi
      if (filterProvider !== 'all') {
        params.append('resource_id', filterProvider);
      }
      
      // Action filtresi
      if (filterAction !== 'all') {
        params.append('action', filterAction);
      }
      
      // Success filtresi
      if (filterSuccess !== 'all') {
        params.append('success', filterSuccess === 'true');
      }
      
      const response = await apiRequest(`/api/security-logs?${params.toString()}`);
      
      setSecurityLogs(response.logs || []);
      setTotalLogs(response.total || 0);
    } catch (error) {
      console.error('Security logs loading error:', error);
      showToast('Güvenlik logları yüklenirken hata oluştu', 'error');
    }
  };
  
  const handleRefresh = () => {
    loadData();
  };
  
  const formatDateTime = (dateTimeStr) => {
    if (!dateTimeStr) return 'N/A';
    
    const date = new Date(dateTimeStr);
    return date.toLocaleString();
  };
  
  const getStatusColor = (provider) => {
    const status = keyStatus[provider];
    if (!status) return 'gray';
    
    if (!status.is_configured) return 'gray';
    if (!status.is_active) return 'red';
    return 'green';
  };
  
  const getStatusLabel = (provider) => {
    const status = keyStatus[provider];
    if (!status) return 'Bilinmiyor';
    
    if (!status.is_configured) return 'Yapılandırılmamış';
    if (!status.is_active) return 'Devre Dışı';
    return 'Etkin';
  };
  
  const getLastUsed = (provider) => {
    const status = keyStatus[provider];
    if (!status || !status.last_used) return 'Hiç kullanılmamış';
    
    return formatDateTime(status.last_used);
  };
  
  const getLastUpdated = (provider) => {
    const status = keyStatus[provider];
    if (!status || !status.last_updated) return 'Bilinmiyor';
    
    return formatDateTime(status.last_updated);
  };
  
  const getProviderDisplayName = (provider) => {
    const providerNames = {
      'OPENAI': 'OpenAI',
      'COHERE': 'Cohere',
      'JINA': 'Jina AI',
      'WEAVIATE': 'Weaviate',
      'GOOGLE': 'Google Cloud',
      'AZURE': 'Azure OpenAI',
      'AWS': 'AWS',
      'HUGGINGFACE': 'Hugging Face',
      'TWITTER': 'Twitter',
      'FACEBOOK': 'Facebook',
      'LINKEDIN': 'LinkedIn'
    };
    
    return providerNames[provider] || provider;
  };
  
  const getActionDisplayName = (action) => {
    const actionNames = {
      'access': 'Erişim',
      'validate': 'Doğrulama',
      'verify': 'Doğrulama (API)',
      'create': 'Oluşturma',
      'update': 'Güncelleme',
      'delete': 'Silme'
    };
    
    return actionNames[action] || action;
  };
  
  const formatRelativeTime = (dateTimeStr) => {
    if (!dateTimeStr) return 'N/A';
    
    const date = new Date(dateTimeStr);
    const now = new Date();
    const diffMs = now - date;
    
    // Saniye cinsinden fark
    const diffSec = Math.floor(diffMs / 1000);
    
    if (diffSec < 60) {
      return `${diffSec} saniye önce`;
    }
    
    // Dakika cinsinden fark
    const diffMin = Math.floor(diffSec / 60);
    
    if (diffMin < 60) {
      return `${diffMin} dakika önce`;
    }
    
    // Saat cinsinden fark
    const diffHour = Math.floor(diffMin / 60);
    
    if (diffHour < 24) {
      return `${diffHour} saat önce`;
    }
    
    // Gün cinsinden fark
    const diffDay = Math.floor(diffHour / 24);
    
    return `${diffDay} gün önce`;
  };
  
  // Admin yetkisi yoksa monitör gösterme
  if (!isAdmin) {
    return (
      <div className="api-keys-monitor">
        <h2>API Anahtarları İzleme</h2>
        <p>Bu sayfayı görüntülemek için admin yetkisi gereklidir.</p>
      </div>
    );
  }
  
  return (
    <div className="api-keys-monitor">
      <div className="monitor-header">
        <h2>API Anahtarları İzleme</h2>
        
        <div className="monitor-toolbar">
          <div className="refresh-settings">
            <label className="auto-refresh-label">
              <input 
                type="checkbox" 
                checked={autoRefresh} 
                onChange={(e) => setAutoRefresh(e.target.checked)}
              />
              <span>Otomatik Yenile</span>
            </label>
            
            <select 
              value={refreshInterval} 
              onChange={(e) => setRefreshInterval(parseInt(e.target.value))}
              disabled={!autoRefresh}
            >
              <option value="30">30 saniye</option>
              <option value="60">1 dakika</option>
              <option value="300">5 dakika</option>
              <option value="600">10 dakika</option>
            </select>
            
            <button 
              className="refresh-button" 
              onClick={handleRefresh}
              disabled={isLoading}
            >
              {isLoading ? 'Yenileniyor...' : 'Yenile'}
            </button>
          </div>
          
          {lastUpdated && (
            <div className="last-updated">
              Son güncelleme: {formatDateTime(lastUpdated)}
            </div>
          )}
        </div>
      </div>
      
      <div className="status-panel">
        <h3>API Anahtarı Durumu</h3>
        
        <div className="status-cards">
          {Object.keys(keyStatus).map(provider => (
            <div key={provider} className="status-card">
              <div className="card-header">
                <h4>{getProviderDisplayName(provider)}</h4>
                <span className={`status-badge ${getStatusColor(provider)}`}>
                  {getStatusLabel(provider)}
                </span>
              </div>
              
              <div className="card-body">
                <div className="status-item">
                  <div className="status-label">Son Kullanım:</div>
                  <div className="status-value">{getLastUsed(provider)}</div>
                </div>
                
                <div className="status-item">
                  <div className="status-label">Son Güncelleme:</div>
                  <div className="status-value">{getLastUpdated(provider)}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
      
      <div className="security-logs-panel">
        <h3>API Anahtarı Erişim Logları</h3>
        
        <div className="filters">
          <div className="filter-group">
            <label>Sağlayıcı:</label>
            <select value={filterProvider} onChange={(e) => setFilterProvider(e.target.value)}>
              <option value="all">Tümü</option>
              {Object.keys(keyStatus).map(provider => (
                <option key={provider} value={provider.toLowerCase()}>
                  {getProviderDisplayName(provider)}
                </option>
              ))}
            </select>
          </div>
          
          <div className="filter-group">
            <label>İşlem:</label>
            <select value={filterAction} onChange={(e) => setFilterAction(e.target.value)}>
              <option value="all">Tümü</option>
              <option value="access">Erişim</option>
              <option value="validate">Doğrulama</option>
              <option value="verify">API Doğrulama</option>
              <option value="create">Oluşturma</option>
              <option value="update">Güncelleme</option>
              <option value="delete">Silme</option>
            </select>
          </div>
          
          <div className="filter-group">
            <label>Sonuç:</label>
            <select value={filterSuccess} onChange={(e) => setFilterSuccess(e.target.value)}>
              <option value="all">Tümü</option>
              <option value="true">Başarılı</option>
              <option value="false">Başarısız</option>
            </select>
          </div>
        </div>
        
        <div className="logs-table-container">
          <table className="logs-table">
            <thead>
              <tr>
                <th>Zaman</th>
                <th>Sağlayıcı</th>
                <th>İşlem</th>
                <th>Kullanıcı</th>
                <th>Durum</th>
                <th>IP Adresi</th>
                <th>Detaylar</th>
              </tr>
            </thead>
            <tbody>
              {securityLogs.length === 0 ? (
                <tr>
                  <td colSpan="7" className="no-logs">
                    {isLoading ? 'Yükleniyor...' : 'Hiç log kaydı bulunamadı'}
                  </td>
                </tr>
              ) : (
                securityLogs.map(log => (
                  <tr key={log.id} className={log.success ? 'success' : 'error'}>
                    <td className="timestamp" title={formatDateTime(log.timestamp)}>
                      {formatRelativeTime(log.timestamp)}
                    </td>
                    <td className="provider">{getProviderDisplayName(log.resource_id)}</td>
                    <td className="action">{getActionDisplayName(log.action)}</td>
                    <td className="user">{log.user_id || '-'}</td>
                    <td className="status">
                      <span className={`status-dot ${log.success ? 'success' : 'error'}`}></span>
                      {log.success ? 'Başarılı' : 'Başarısız'}
                    </td>
                    <td className="ip">{log.ip_address || '-'}</td>
                    <td className="details">
                      {log.details ? (
                        <details>
                          <summary>Detaylar</summary>
                          <pre>{JSON.stringify(log.details, null, 2)}</pre>
                        </details>
                      ) : '-'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        
        <div className="pagination">
          <div className="pagination-info">
            Toplam {totalLogs} kayıt, sayfa {logsPage} / {Math.ceil(totalLogs / logsPerPage)}
          </div>
          
          <div className="pagination-controls">
            <button 
              onClick={() => setLogsPage(1)}
              disabled={logsPage === 1}
            >
              &laquo; İlk
            </button>
            
            <button 
              onClick={() => setLogsPage(page => Math.max(1, page - 1))}
              disabled={logsPage === 1}
            >
              &lsaquo; Önceki
            </button>
            
            <select 
              value={logsPerPage} 
              onChange={(e) => {
                setLogsPerPage(parseInt(e.target.value));
                setLogsPage(1); // Sayfa boyutu değişince ilk sayfaya dön
              }}
            >
              <option value="5">5 / sayfa</option>
              <option value="10">10 / sayfa</option>
              <option value="25">25 / sayfa</option>
              <option value="50">50 / sayfa</option>
              <option value="100">100 / sayfa</option>
            </select>
            
            <button 
              onClick={() => setLogsPage(page => Math.min(Math.ceil(totalLogs / logsPerPage), page + 1))}
              disabled={logsPage >= Math.ceil(totalLogs / logsPerPage)}
            >
              Sonraki &rsaquo;
            </button>
            
            <button 
              onClick={() => setLogsPage(Math.ceil(totalLogs / logsPerPage))}
              disabled={logsPage >= Math.ceil(totalLogs / logsPerPage)}
            >
              Son &raquo;
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ApiKeysMonitor;