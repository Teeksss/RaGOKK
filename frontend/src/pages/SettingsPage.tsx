// Last reviewed: 2025-04-30 06:11:15 UTC (User: Teeksss)
import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Card, Form, Button, Alert, Tabs, Tab } from 'react-bootstrap';
import { FaCog, FaPalette, FaBell, FaShieldAlt, FaLanguage } from 'react-icons/fa';
import { useTranslation } from 'react-i18next';
import { useToast } from '../contexts/ToastContext';
import { useAuth } from '../contexts/AuthContext';
import API from '../api/api';
import LanguageSelector from '../components/settings/LanguageSelector';

const SettingsPage: React.FC = () => {
  const { t, i18n } = useTranslation();
  const { showToast } = useToast();
  const { user } = useAuth();
  
  // State
  const [activeTab, setActiveTab] = useState<string>('appearance');
  const [theme, setTheme] = useState<string>(
    localStorage.getItem('theme') || 'light'
  );
  const [emailAlerts, setEmailAlerts] = useState<boolean>(
    localStorage.getItem('emailAlerts') === 'true'
  );
  const [systemNotifications, setSystemNotifications] = useState<boolean>(
    localStorage.getItem('systemNotifications') !== 'false'
  );
  const [dataSharing, setDataSharing] = useState<boolean>(
    localStorage.getItem('dataSharing') === 'true'
  );
  const [analyticsCollection, setAnalyticsCollection] = useState<boolean>(
    localStorage.getItem('analyticsCollection') !== 'false'
  );
  
  const [saving, setSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<boolean>(false);
  
  // Ayarları kaydet
  const handleSaveSettings = async () => {
    setSaving(true);
    setError(null);
    setSuccess(false);
    
    try {
      // Tema ayarı
      localStorage.setItem('theme', theme);
      document.documentElement.setAttribute('data-theme', theme);
      
      if (theme === 'dark') {
        document.documentElement.classList.add('dark-theme');
      } else {
        document.documentElement.classList.remove('dark-theme');
      }
      
      // Bildirim ayarları
      localStorage.setItem('emailAlerts', emailAlerts.toString());
      localStorage.setItem('systemNotifications', systemNotifications.toString());
      
      // Gizlilik ayarları
      localStorage.setItem('dataSharing', dataSharing.toString());
      localStorage.setItem('analyticsCollection', analyticsCollection.toString());
      
      // Dil tercihini localStorage'a kaydet (i18next'in yaptığı ile aynı işlem)
      localStorage.setItem('i18nextLng', i18n.language);
      
      // Kullanıcı tercihlerini sunucuya kaydet (giriş yapmış kullanıcılar için)
      if (user?.id) {
        await API.post('/users/preferences', {
          theme,
          notifications: {
            email_alerts: emailAlerts,
            system_notifications: systemNotifications
          },
          privacy: {
            data_sharing: dataSharing,
            analytics_collection: analyticsCollection
          },
          locale: i18n.language
        });
      }
      
      setSuccess(true);
      showToast('success', t('settings.saveSuccess'));
      
    } catch (err: any) {
      console.error('Error saving settings:', err);
      setError(err.response?.data?.detail || t('settings.saveError'));
      showToast('error', t('settings.saveError'));
      
    } finally {
      setSaving(false);
    }
  };
  
  // Tercihler değiştiğinde otomatik kaydet
  useEffect(() => {
    // Tema değiştiğinde
    document.documentElement.setAttribute('data-theme', theme);
    
    if (theme === 'dark') {
      document.documentElement.classList.add('dark-theme');
    } else {
      document.documentElement.classList.remove('dark-theme');
    }
  }, [theme]);
  
  return (
    <Container className="py-4">
      <Row className="mb-4">
        <Col>
          <h1 className="h3 mb-0">
            <FaCog className="me-2" />
            {t('settings.title')}
          </h1>
          <p className="text-muted">{t('settings.general')}</p>
        </Col>
      </Row>
      
      <Row>
        <Col lg={3} className="mb-4">
          <Card>
            <Card.Body className="p-0">
              <div className="list-group list-group-flush">
                <button
                  className={`list-group-item list-group-item-action d-flex align-items-center ${activeTab === 'appearance' ? 'active' : ''}`}
                  onClick={() => setActiveTab('appearance')}
                >
                  <FaPalette className="me-2" />
                  {t('settings.appearance')}
                </button>
                <button
                  className={`list-group-item list-group-item-action d-flex align-items-center ${activeTab === 'language' ? 'active' : ''}`}
                  onClick={() => setActiveTab('language')}
                >
                  <FaLanguage className="me-2" />
                  {t('profile.language')}
                </button>
                <button
                  className={`list-group-item list-group-item-action d-flex align-items-center ${activeTab === 'notifications' ? 'active' : ''}`}
                  onClick={() => setActiveTab('notifications')}
                >
                  <FaBell className="me-2" />
                  {t('settings.notifications.title')}
                </button>
                <button
                  className={`list-group-item list-group-item-action d-flex align-items-center ${activeTab === 'privacy' ? 'active' : ''}`}
                  onClick={() => setActiveTab('privacy')}
                >
                  <FaShieldAlt className="me-2" />
                  {t('settings.privacy')}
                </button>
              </div>
            </Card.Body>
          </Card>
        </Col>
        
        <Col lg={9}>
          <Card className="shadow-sm">
            <Card.Body>
              {/* Başarı ve hata mesajları */}
              {success && (
                <Alert variant="success" dismissible onClose={() => setSuccess(false)}>
                  {t('settings.saveSuccess')}
                </Alert>
              )}
              
              {error && (
                <Alert variant="danger" dismissible onClose={() => setError(null)}>
                  {error}
                </Alert>
              )}
              
              {/* Görünüm ayarları sekmesi */}
              {activeTab === 'appearance' && (
                <div>
                  <h4>{t('settings.appearance')}</h4>
                  <hr />
                  
                  <Form>
                    <Form.Group className="mb-4">
                      <Form.Label>{t('settings.theme.label')}</Form.Label>
                      <div>
                        <Form.Check
                          inline
                          type="radio"
                          id="theme-light"
                          name="theme"
                          label={t('settings.theme.light')}
                          checked={theme === 'light'}
                          onChange={() => setTheme('light')}
                          className="me-3"
                        />
                        <Form.Check
                          inline
                          type="radio"
                          id="theme-dark"
                          name="theme"
                          label={t('settings.theme.dark')}
                          checked={theme === 'dark'}
                          onChange={() => setTheme('dark')}
                          className="me-3"
                        />
                        <Form.Check
                          inline
                          type="radio"
                          id="theme-system"
                          name="theme"
                          label={t('settings.theme.system')}
                          checked={theme === 'system'}
                          onChange={() => setTheme('system')}
                        />
                      </div>
                    </Form.Group>
                  </Form>
                </div>
              )}
              
              {/* Dil ayarları sekmesi */}
              {activeTab === 'language' && (
                <div>
                  <h4>{t('profile.language')}</h4>
                  <hr />
                  
                  <Form>
                    <Form.Group className="mb-4">
                      <Form.Label>{t('settings.language.label')}</Form.Label>
                      <div>
                        <LanguageSelector variant="buttons" showLabel={false} />
                      </div>
                      <Form.Text className="text-muted">
                        {t('settings.language.label')} {i18n.language === 'en' ? t('settings.language.english') : t('settings.language.turkish')}
                      </Form.Text>
                    </Form.Group>
                  </Form>
                </div>
              )}
              
              {/* Bildirim ayarları sekmesi */}
              {activeTab === 'notifications' && (
                <div>
                  <h4>{t('settings.notifications.title')}</h4>
                  <hr />
                  
                  <Form>
                    <Form.Group className="mb-3">
                      <Form.Check
                        type="switch"
                        id="email-alerts"
                        label={t('settings.notifications.emailAlerts')}
                        checked={emailAlerts}
                        onChange={(e) => setEmailAlerts(e.target.checked)}
                      />
                      <Form.Text className="text-muted">
                        {t('settings.notifications.emailDescription')}
                      </Form.Text>
                    </Form.Group>
                    
                    <Form.Group className="mb-3">
                      <Form.Check
                        type="switch"
                        id="system-notifications"
                        label={t('settings.notifications.systemNotifications')}
                        checked={systemNotifications}
                        onChange={(e) => setSystemNotifications(e.target.checked)}
                      />
                      <Form.Text className="text-muted">
                        {t('settings.notifications.systemDescription')}
                      </Form.Text>
                    </Form.Group>
                  </Form>
                </div>
              )}
              
              {/* Gizlilik ayarları sekmesi */}
              {activeTab === 'privacy' && (
                <div>
                  <h4>{t('settings.privacy')}</h4>
                  <hr />
                  
                  <Form>
                    <Form.Group className="mb-3">
                      <Form.Check
                        type="switch"
                        id="data-sharing"
                        label={t('settings.dataSharing')}
                        checked={dataSharing}
                        onChange={(e) => setDataSharing(e.target.checked)}
                      />
                      <Form.Text className="text-muted">
                        {t('settings.dataSharingDescription')}
                      </Form.Text>
                    </Form.Group>
                    
                    <Form.Group className="mb-3">
                      <Form.Check
                        type="switch"
                        id="analytics-collection"
                        label={t('settings.analytics')}
                        checked={analyticsCollection}
                        onChange={(e) => setAnalyticsCollection(e.target.checked)}
                      />
                      <Form.Text className="text-muted">
                        {t('settings.analyticsDescription')}
                      </Form.Text>
                    </Form.Group>
                  </Form>
                </div>
              )}
              
              {/* Kaydet butonu */}
              