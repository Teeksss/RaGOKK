// Last reviewed: 2025-04-29 07:31:24 UTC (User: TeeksssLogin)
import React, { useState, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import useApi from '../hooks/useApi';
import useTaskManager from '../hooks/useTaskManager';
import DataSourceList from './DataSourceList';
import DataSourceUploadGrid from './DataSourceUploadGrid';
import Spinner from './ui/Spinner';
import './DataSourceSection.css';

const DataSourceSection = () => {
  const [dataSourcesKey, setDataSourcesKey] = useState(0);
  const [isReindexing, setIsReindexing] = useState(false);
  const [generalError, setGeneralError] = useState('');
  
  const { isLoggedIn, isAdmin } = useAuth();
  const { showToast } = useToast();
  const { apiRequest, isLoading: isApiLoading } = useApi();
  const { runningTasks } = useTaskManager();
  
  // Check if there's any running reindex task
  const reindexingTask = runningTasks.find(task => task.type === 'reindex');
  
  const refreshDataSources = useCallback(() => {
    setDataSourcesKey(prev => prev + 1);
  }, []);
  
  const handleUploadSuccess = useCallback((sourceName) => {
    showToast(`${sourceName} başarıyla işleme alındı.`, 'success');
    refreshDataSources();
  }, [refreshDataSources, showToast]);
  
  const handleUploadError = useCallback((sourceName, errorMsg) => {
    const displayError = errorMsg.includes("401") ? "Yetkilendirme hatası. Lütfen giriş yapın." :
                         errorMsg.includes("403") ? "Bu işlem için yetkiniz yok." :
                         errorMsg.includes("409") ? "Kaynak ID'si zaten mevcut (çakışma)." :
                         errorMsg.includes("413") ? "Dosya boyutu çok büyük." :
                         errorMsg.includes("503") ? "Servis geçici olarak kullanılamıyor." :
                         errorMsg.includes("Failed to fetch") ? "Sunucuya bağlanılamadı." :
                         errorMsg;
    
    setGeneralError(`Veri kaynağı eklenirken hata (${sourceName}): ${displayError}`);
    showToast(`Veri kaynağı hatası: ${displayError}`, 'error');
  }, [showToast]);
  
  const handleReindex = useCallback(async () => {
    setIsReindexing(true);
    setGeneralError('');
    
    try {
      const data = await apiRequest("/data_source/reindex", { method: "POST" });
      showToast(data.message || "Yeniden indeksleme arka planda başlatıldı.", 'info');
    } catch (error) {
      handleUploadError("Yeniden İndeksleme", error.message);
    } finally {
      setIsReindexing(false);
    }
  }, [apiRequest, handleUploadError, showToast]);
  
  if (!isLoggedIn) {
    return (
      <section className="data-source-section card">
        <h2>Veri Kaynakları Yönetimi</h2>
        <div className="login-required-message">
          <p>Veri kaynaklarını yönetmek için lütfen giriş yapın.</p>
        </div>
      </section>
    );
  }
  
  const isBusy = isReindexing || isApiLoading || !!reindexingTask;
  
  return (
    <section className="data-source-section card">
      <h2>Veri Kaynakları Yönetimi</h2>
      
      {generalError && !isBusy && (
        <div className="error-message global-error">
          Hata: {generalError}
        </div>
      )}
      
      <DataSourceUploadGrid
        onUploadSuccess={handleUploadSuccess}
        onUploadError={handleUploadError}
        apiRequest={apiRequest}
      />
      
      <div className="data-source-management">
        <h3>Mevcut Kaynaklar</h3>
        <DataSourceList
          key={dataSourcesKey}
          onDataSourceChange={refreshDataSources}
          onError={handleUploadError}
          apiRequest={apiRequest}
        />
        
        {isAdmin && (
          <button
            onClick={handleReindex}
            disabled={isBusy}
            className="action-button"
          >
            {isBusy ? (
              <><Spinner size="small" /> İndeksleniyor...</>
            ) : (
              'Verileri Yeniden İndeksle'
            )}
          </button>
        )}
        
        {reindexingTask && (
          <div className="reindex-progress">
            <div className="progress-bar" style={{ width: `${reindexingTask.progress}%` }}></div>
            <div className="progress-text">İndeksleniyor: {reindexingTask.progress}%</div>
          </div>
        )}
      </div>
    </section>
  );
};

export default DataSourceSection;