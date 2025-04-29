// Last reviewed: 2025-04-29 11:06:31 UTC (User: Teekssseksiklikleri)
import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import ConfigEditor from '../ConfigEditor';
import './AdminSettings.css';

const AdminSettings = () => {
  const { isAdmin } = useAuth();
  const [activeTab, setActiveTab] = useState('config');
  
  // Admin kontrolü
  if (!isAdmin) {
    return (
      <div className="admin-settings">
        <h2>Yönetici Ayarları</h2>
        <div className="no-access">
          <p>Bu sayfaya erişmek için yönetici yetkilerine sahip olmanız gerekmektedir.</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="admin-settings">
      <h2>Yönetici Ayarları</h2>
      
      <div className="admin-tabs">
        <button
          className={`admin-tab ${activeTab === 'config' ? 'active' : ''}`}
          onClick={() => setActiveTab('config')}
        >
          Sistem Konfigürasyonu
        </button>
        <button
          className={`admin-tab ${activeTab === 'users' ? 'active' : ''}`}
          onClick={() => setActiveTab('users')}
        >
          Kullanıcı Yönetimi
        </button>
        <button
          className={`admin-tab ${activeTab === 'logs' ? 'active' : ''}`}
          onClick={() => setActiveTab('logs')}
        >
          Sistem Logları
        </button>
      </div>
      
      <div className="admin-content">
        {activeTab === 'config' && <ConfigEditor />}
        {activeTab === 'users' && <div>Kullanıcı yönetimi ekranı yapım aşamasında.</div>}
        {activeTab === 'logs' && <div>Sistem logları ekranı yapım aşamasında.</div>}
      </div>
    </div>
  );
};

export default AdminSettings;