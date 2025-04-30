// Last reviewed: 2025-04-30 05:29:35 UTC (User: Teeksss)
import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Card, Button, Form, Tabs, Tab, Alert, Spinner, Badge } from 'react-bootstrap';
import { FaDownload, FaChartBar, FaUsers, FaFileAlt, FaSearch, FaServer } from 'react-icons/fa';
import { Line, Bar, Pie } from 'react-chartjs-2';
import { Chart, registerables } from 'chart.js';
import API from '../api/api';
import { useTranslation } from 'react-i18next';
import { useToast } from '../contexts/ToastContext';
import ResponsiveLayout from '../components/layout/ResponsiveLayout';
import { formatNumber, formatPercentage, formatDate } from '../utils/formatters';

// Chart.js bileşenlerini kaydet
Chart.register(...registerables);

const AnalyticsPage: React.FC = () => {
  const { t } = useTranslation();
  const { showToast } = useToast();
  
  // State yönetimi
  const [activeTab, setActiveTab] = useState<string>('user-activity');
  const [timeRange, setTimeRange] = useState<string>('last_30_days');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  
  // Analiz verileri
  const [userActivityData, setUserActivityData] = useState<any>(null);
  const [documentAnalyticsData, setDocumentAnalyticsData] = useState<any>(null);
  const [queryAnalyticsData, setQueryAnalyticsData] = useState<any>(null);
  const [systemUsageData, setSystemUsageData] = useState<any>(null);
  
  // Veri yükleme fonksiyonu
  const loadAnalyticsData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      switch(activeTab) {
        case 'user-activity':
          if (!userActivityData || userActivityData.time_range !== timeRange) {
            const response = await API.get(`/analytics/user-activity?time_range=${timeRange}`);
            setUserActivityData(response.data);
          }
          break;
          
        case 'document-analytics':
          if (!documentAnalyticsData || documentAnalyticsData.time_range !== timeRange) {
            const response = await API.get(`/analytics/document-analytics?time_range=${timeRange}`);
            setDocumentAnalyticsData(response.data);
          }
          break;
          
        case 'query-analytics':
          if (!queryAnalyticsData || queryAnalyticsData.time_range !== timeRange) {
            const response = await API.get(`/analytics/query-analytics?time_range=${timeRange}`);
            setQueryAnalyticsData(response.data);
          }
          break;
          
        case 'system-usage':
          if (!systemUsageData || systemUsageData.time_range !== timeRange) {
            const response = await API.get(`/analytics/system-usage?time_range=${timeRange}`);
            setSystemUsageData(response.data);
          }
          break;
      }
    } catch (err: any) {
      console.error('Error loading analytics data:', err);
      setError(err.response?.data?.message || t('analytics.loadError'));
      showToast('error', t('analytics.loadError'));
    } finally {
      setLoading(false);
    }
  };
  
  // Tab veya zaman aralığı değiştiğinde verileri yükle
  useEffect(() => {
    loadAnalyticsData();
  }, [activeTab, timeRange]);
  
  // Verileri dışa aktar
  const handleExport = async (format: string) => {
    try {
      // Rapor türünü belirle
      let reportType = '';
      switch(activeTab) {
        case 'user-activity': reportType = 'user_activity'; break;
        case 'document-analytics': reportType = 'document_analytics'; break;
        case 'query-analytics': reportType = 'query_analytics'; break;
        case 'system-usage': reportType = 'system_usage'; break;
      }
      
      // İndirme URL'ini oluştur ve dosyayı indir
      const url = `/analytics/export/${reportType}?format=${format}&time_range=${timeRange}`;
      
      // Fetch API ile verileri al ve dosya olarak indir
      const response = await API.get(url, { responseType: 'blob' });
      
      // Content-Disposition başlığından dosya adını al
      const contentDisposition = response.headers['content-disposition'];
      let filename = 'export.' + format.toLowerCase();
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1];
        }
      }
      
      // Blob nesnesini oluştur ve dosya indirme bağlantısını tıkla
      const blob = new Blob([response.data]);
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      showToast('success', t('analytics.exportSuccess'));
      
    } catch (err: any) {
      console.error('Error exporting data:', err);
      showToast('error', t('analytics.exportError'));
    }
  };
  
  // Chart stilleri
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom' as const,
        labels: {
          boxWidth: 12,
          padding: 15,
          font: {
            size: 11
          }
        }
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleFont: {
          size: 13
        },
        bodyFont: {
          size: 12
        },
        padding: 10,
        cornerRadius: 4
      }
    },
    scales: {
      y: {
        ticks: {
          font: {
            size: 10
          }
        },
        beginAtZero: true
      },
      x: {
        ticks: {
          font: {
            size: 10
          },
          maxRotation: 45,
          minRotation: 45
        }
      }
    }
  };
  
  // Kullanıcı etkinlik grafiği verileri
  const userActivityChartData = userActivityData ? {
    labels: userActivityData.daily_activity.map((item: any) => formatDate(item.date)),
    datasets: [
      {
        label: t('analytics.dailyActivity'),
        data: userActivityData.daily_activity.map((item: any) => item.count),
        backgroundColor: 'rgba(54, 162, 235, 0.5)',
        borderColor: 'rgb(54, 162, 235)',
        borderWidth: 1
      }
    ]
  } : null;
  
  // Etkinlik türleri pasta grafiği
  const eventTypeChartData = userActivityData ? {
    labels: userActivityData.event_types_distribution.map((item: any) => item.type),
    datasets: [
      {
        label: t('analytics.eventCount'),
        data: userActivityData.event_types_distribution.map((item: any) => item.count),
        backgroundColor: [
          'rgba(54, 162, 235, 0.7)',
          'rgba(75, 192, 192, 0.7)',
          'rgba(255, 206, 86, 0.7)',
          'rgba(255, 99, 132, 0.7)',
          'rgba(153, 102, 255, 0.7)',
          'rgba(255, 159, 64, 0.7)',
          'rgba(199, 199, 199, 0.7)'
        ],
        borderColor: [
          'rgba(54, 162, 235, 1)',
          'rgba(75, 192, 192, 1)',
          'rgba(255, 206, 86, 1)',
          'rgba(255, 99, 132, 1)',
          'rgba(153, 102, 255, 1)',
          'rgba(255, 159, 64, 1)',
          'rgba(199, 199, 199, 1)'
        ],
        borderWidth: 1
      }
    ]
  } : null;
  
  // Belge yükleme grafiği verileri
  const documentUploadsChartData = documentAnalyticsData ? {
    labels: documentAnalyticsData.daily_document_uploads.map((item: any) => formatDate(item.date)),
    datasets: [
      {
        label: t('analytics.documentUploads'),
        data: documentAnalyticsData.daily_document_uploads.map((item: any) => item.count),
        backgroundColor: 'rgba(75, 192, 192, 0.5)',
        borderColor: 'rgb(75, 192, 192)',
        borderWidth: 1
      }
    ]
  } : null;
  
  // Dosya türleri pasta grafiği
  const fileTypeChartData = documentAnalyticsData ? {
    labels: documentAnalyticsData.file_type_distribution.map((item: any) => item.type),
    datasets: [
      {
        label: t('analytics.fileCount'),
        data: documentAnalyticsData.file_type_distribution.map((item: any) => item.count),
        backgroundColor: [
          'rgba(255, 99, 132, 0.7)',
          'rgba(54, 162, 235, 0.7)',
          'rgba(255, 206, 86, 0.7)',
          'rgba(75, 192, 192, 0.7)',
          'rgba(153, 102, 255, 0.7)',
          'rgba(255, 159, 64, 0.7)',
          'rgba(199, 199, 199, 0.7)'
        ],
        borderColor: [
          'rgba(255, 99, 132, 1)',
          'rgba(54, 162, 235, 1)',
          'rgba(255, 206, 86, 1)',
          'rgba(75, 192, 192, 1)',
          'rgba(153, 102, 255, 1)',
          'rgba(255, 159, 64, 1)',
          'rgba(199, 199, 199, 1)'
        ],
        borderWidth: 1
      }
    ]
  } : null;
  
  // Günlük sorgu grafiği verileri
  const queryChartData = queryAnalyticsData ? {
    labels: queryAnalyticsData.daily_query_counts.map((item: any) => formatDate(item.date)),
    datasets: [
      {
        label: t('analytics.dailyQueries'),
        data: queryAnalyticsData.daily_query_counts.map((item: any) => item.count),
        backgroundColor: 'rgba(153, 102, 255, 0.5)',
        borderColor: 'rgb(153, 102, 255)',
        borderWidth: 1
      }
    ]
  } : null;
  
  // Sorgu türleri pasta grafiği
  const queryTypeChartData = queryAnalyticsData ? {
    labels: queryAnalyticsData.query_type_distribution.map((item: any) => item.type),
    datasets: [
      {
        label: t('analytics.queryCount'),
        data: queryAnalyticsData.query_type_distribution.map((item: any) => item.count),
        backgroundColor: [
          'rgba(153, 102, 255, 0.7)',
          'rgba(255, 99, 132, 0.7)',
          'rgba(54, 162, 235, 0.7)',
          'rgba(255, 206, 86, 0.7)',
          'rgba(75, 192, 192, 0.7)',
          'rgba(255, 159, 64, 0.7)',
          'rgba(199, 199, 199, 0.7)'
        ],
        borderColor: [
          'rgba(153, 102, 255, 1)',
          'rgba(255, 99, 132, 1)',
          'rgba(54, 162, 235, 1)',
          'rgba(255, 206, 86, 1)',
          'rgba(75, 192, 192, 1)',
          'rgba(255, 159, 64, 1)',
          'rgba(199, 199, 199, 1)'
        ],
        borderWidth: 1
      }
    ]
  } : null;
  
  // Saatlik aktivite grafiği verileri
  const hourlyActivityChartData = systemUsageData ? {
    labels: systemUsageData.hourly_activity_pattern.map((item: any) => `${item.hour}:00`),
    datasets: [
      {
        label: t('analytics.hourlyActivity'),
        data: systemUsageData.hourly_activity_pattern.map((item: any) => item.count),
        backgroundColor: 'rgba(255, 159, 64, 0.5)',
        borderColor: 'rgb(255, 159, 64)',
        borderWidth: 1
      }
    ]
  } : null;
  
  return (
    <ResponsiveLayout>
      <Container fluid className="px-md-4 py-3">
        <Row className="mb-4 align-items-center">
          <Col>
            <h1 className="h2 mb-0">
              <FaChartBar className="me-2" /> {t('analytics.title')}
            </h1>
            <p className="text-muted">{t('analytics.subtitle')}</p>
          </Col>
          
          <Col xs="12" md="auto" className="mt-2 mt-md-0">
            <div className="d-flex flex-column flex-md-row gap-2">
              <Form.Select 
                value={timeRange} 
                onChange={(e) => setTimeRange(e.target.value)}
                className="mb-2 mb-md-0 me-md-2"
              >
                <option value="today">{t('analytics.timeRange.today')}</option>
                <option value="yesterday">{t('analytics.timeRange.yesterday')}</option>
                <option value="last_7_days">{t('analytics.timeRange.last7Days')}</option>
                <option value="last_30_days">{t('analytics.timeRange.last30Days')}</option>
                <option value="this_month">{t('analytics.timeRange.thisMonth')}</option>
                <option value="last_month">{t('analytics.timeRange.lastMonth')}</option>
                <option value="this_quarter">{t('analytics.timeRange.thisQuarter')}</option>
                <option value="this_year">{t('analytics.timeRange.thisYear')}</option>
              </Form.Select>
              
              <div className="dropdown">
                <Button 
                  variant="outline-secondary" 
                  className="dropdown-toggle" 
                  data-bs-toggle="dropdown"
                  aria-expanded="false"
                >
                  <FaDownload className="me-1" /> {t('analytics.export')}
                </Button>
                <ul className="dropdown-menu dropdown-menu-end">
                  <li>
                    <button 
                      className="dropdown-item" 
                      onClick={() => handleExport('csv')}
                    >
                      CSV
                    </button>
                  </li>
                  <li>
                    <button 
                      className="dropdown-item" 
                      onClick={() => handleExport('excel')}
                    >
                      Excel
                    </button>
                  </li>
                  <li>
                    <button 
                      className="dropdown-item" 
                      onClick={() => handleExport('json')}
                    >
                      JSON
                    </button>
                  </li>
                </ul>
              </div>
            </div>
          </Col>
        </Row>
        
        {/* Sekmeler - mobil için yukarıdan aşağıya düzenlenmiş */}
        <Tabs
          activeKey={activeTab}
          onSelect={(k) => setActiveTab(k || 'user-activity')}
          className="mb-4 analytics-tabs flex-column flex-md-row"
          fill
        >
          <Tab 
            eventKey="user-activity" 
            title={
              <span>
                <FaUsers className="me-1 d-none d-sm-inline" />
                {t('analytics.tabs.userActivity')}
              </span>
            }
            tabClassName="py-2"
          />
          <Tab 
            eventKey="document-analytics" 
            title={
              <span>
                <FaFileAlt className="me-1 d-none d-sm-inline" />
                {t('analytics.tabs.documentAnalytics')}
              </span>
            }
            tabClassName="py-2"
          />
          <Tab 
            eventKey="query-analytics" 
            title={
              <span>
                <FaSearch className="me-1 d-none d-sm-inline" />
                {t('analytics.tabs.queryAnalytics')}
              </span>
            }
            tabClassName="py-2"
          />
          <Tab 
            eventKey="system-usage" 
            title={
              <span>
                <FaServer className="me-1 d-none d-sm-inline" />
                {t('analytics.tabs.systemUsage')}
              </span>
            }
            tabClassName="py-2"
          />
        </Tabs>
        
        {/* Hata mesajları */}
        {error && (
          <Alert variant="danger" className="mb-4">
            <Alert.Heading>{t('common.error')}</Alert.Heading>
            <p>{error}</p>
            <Button variant="outline-danger" onClick={loadAnalyticsData}>
              {t('common.tryAgain')}
            </Button>
          </Alert>
        )}
        
        {/* Yükleniyor göstergesi */}
        {loading && (
          <div className="text-center my-5">
            <Spinner animation="border" variant="primary" />
            <p className="mt-2 text-muted">{t('analytics.loading')}</p>
          </div>
        )}
        
        {/* Kullanıcı Etkinliği İçeriği */}
        {activeTab === 'user-activity' && !loading && userActivityData && (
          <>
            {/* Özet metrikler - mobil için satır halinde */}
            <Row className="mb-4 gy-3">
              <Col xs="12" md="4">
                <Card className="h-100 analytics-card">
                  <Card.Body className="d-flex flex-column align-items-center">
                    <h6 className="text-muted mb-2">{t('analytics.totalLogins')}</h6>
                    <div className="analytics-value">{formatNumber(userActivityData.total_logins)}</div>
                  </Card.Body>
                </Card>
              </Col>
              <Col xs="12" md="4">
                <Card className="h-100 analytics-card">
                  <Card.Body className="d-flex flex-column align-items-center">
                    <h6 className="text-muted mb-2">{t('analytics.activeUsers')}</h6>
                    <div className="analytics-value">
                      {formatNumber(userActivityData.active_users_count)}
                      <span className="text-muted small ms-2">/ {formatNumber(userActivityData.total_users_count)}</span>
                    </div>
                    <div className="text-success stat-change">
                      {formatPercentage(userActivityData.active_users_percentage)}%
                    </div>
                  </Card.Body>
                </Card>
              </Col>
              <Col xs="12" md="4">
                <Card className="h-100 analytics-card">
                  <Card.Body className="d-flex flex-column align-items-center">
                    <h6 className="text-muted mb-2">{t('analytics.averageEventsPerUser')}</h6>
                    <div className="analytics-value">
                      {formatNumber(userActivityData.top_active_users.length > 0 
                        ? userActivityData.top_active_users.reduce((sum: number, user: any) => sum + user.event_count, 0) / userActivityData.top_active_users.length
                        : 0
                      )}
                    </div>
                  </Card.Body>
                </Card>
              </Col>
            </Row>
            
            {/* Grafikler - mobil için tam genişlik */}
            <Row className="mb-4 gy-4">
              <Col xs="12" lg="8">
                <Card className="h-100">
                  <Card.Header>
                    <h5 className="mb-0">{t('analytics.dailyActivityTrend')}</h5>
                  </Card.Header>
                  <Card.Body>
                    <div className="chart-container" style={{ height: '300px' }}>
                      {userActivityChartData && (
                        <Line data={userActivityChartData} options={chartOptions} />
                      )}
                    </div>
                  </Card.Body>
                </Card>
              </Col>
              <Col xs="12" lg="4">
                <Card className="h-100">
                  <Card.Header>
                    <h5 className="mb-0">{t('analytics.eventTypeDistribution')}</h5>
                  </Card.Header>
                  <Card.Body>
                    <div className="chart-container" style={{ height: '300px' }}>
                      {eventTypeChartData && (
                        <Pie data={eventTypeChartData} options={chartOptions} />
                      )}
                    </div>
                  </Card.Body>
                </Card>
              </Col>
            </Row>
            
            {/* En aktif kullanıcılar - mobil için kaydırılabilir tablo */}
            <Card className="mb-4">
              <Card.Header>
                <h5 className="mb-0">{t('analytics.topActiveUsers')}</h5>
              </Card.Header>
              <div className="table-responsive">
                <table className="table table-hover mb-0">
                  <thead>
                    <tr>
                      <th>{t('analytics.user')}</th>
                      <th>{t('analytics.email')}</th>
                      <th className="text-end">{t('analytics.eventCount')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {userActivityData.top_active_users.map((user: any, index: number) => (
                      <tr key={user.user_id}>
                        <td>
                          <span className="fw-medium">
                            {user.full_name || user.username || t('analytics.anonymousUser')}
                          </span>
                        </td>
                        <td>{user.email}</td>
                        <td className="text-end">
                          <Badge bg="primary" pill>
                            {formatNumber(user.event_count)}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                    {userActivityData.top_active_users.length === 0 && (
                      <tr>
                        <td colSpan={3} className="text-center py-4">
                          {t('analytics.noActiveUsers')}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </Card>
          </>
        )}
        
        {/* Belge Analitikleri İçeriği */}
        {activeTab === 'document-analytics' && !loading && documentAnalyticsData && (
          <>
            {/* Özet metrikler - mobil için satır halinde */}
            <Row className="mb-4 gy-3">
              <Col xs="12" md="4">
                <Card className="h-100 analytics-card">
                  <Card.Body className="d-flex flex-column align-items-center">
                    <h6 className="text-muted mb-2">{t('analytics.totalDocuments')}</h6>
                    <div className="analytics-value">{formatNumber(documentAnalyticsData.total_documents)}</div>
                  </Card.Body>
                </Card>
              </Col>
              <Col xs="12" md="4">
                <Card className="h-100 analytics-card">
                  <Card.Body className="d-flex flex-column align-items-center">
                    <h6 className="text-muted mb-2">{t('analytics.newDocuments')}</h6>
                    <div className="analytics-value">
                      {formatNumber(documentAnalyticsData.new_documents)}
                    </div>
                    <div className="text-success stat-change">
                      {formatPercentage(documentAnalyticsData.documents_growth_percentage)}%
                    </div>
                  </Card.Body>
                </Card>
              </Col>
              <Col xs="12" md="4">
                <Card className="h-100 analytics-card">
                  <Card.Body className="d-flex flex-column align-items-center">
                    <h6 className="text-muted mb-2">{t('analytics.avgDocsPerDay')}</h6>
                    <div className="analytics-value">
                      {formatNumber(documentAnalyticsData.daily_document_uploads.length > 0
                        ? documentAnalyticsData.new_documents / documentAnalyticsData.daily_document_uploads.length
                        : 0
                      )}
                    </div>
                  </Card.Body>
                </Card>
              </Col>
            </Row>
            
            {/* Grafikler - mobil için tam genişlik */}
            <Row className="mb-4 gy-4">
              <Col xs="12" lg="8">
                <Card className="h-100">
                  <Card.Header>
                    <h5 className="mb-0">{t('analytics.documentUploadTrend')}</h5>
                  </Card.Header>
                  <Card.Body>
                    <div className="chart-container" style={{ height: '300px' }}>
                      {documentUploadsChartData && (
                        <Line data={documentUploadsChartData} options={chartOptions} />
                      )}
                    </div>
                  </Card.Body>
                </Card>
              </Col>
              <Col xs="12" lg="4">
                <Card className="h-100">
                  <Card.Header>
                    <h5 className="mb-0">{t('analytics.fileTypeDistribution')}</h5>
                  </Card.Header>
                  <Card.Body>
                    <div className="chart-container" style={{ height: '300px' }}>
                      {fileTypeChartData && (
                        <Pie data={fileTypeChartData} options={chartOptions} />
                      )}
                    </div>
                  </Card.Body>
                </Card>
              </Col>
            </Row>
            
            {/* En çok sorgulanan belgeler - mobil için kaydırılabilir tablo */}
            <Card className="mb-4">
              <Card.Header>
                <h5 className="mb-0">{t('analytics.topQueriedDocuments')}</h5>
              </Card.Header>
              <div className="table-responsive">
                <table className="table table-hover mb-0">
                  <thead>
                    <tr>
                      <th>{t('analytics.document')}</th>
                      <th className="text-end">{t('analytics.queryCount')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {documentAnalyticsData.top_queried_documents.map((doc: any, index: number) => (
                      <tr key={doc.document_id}>
                        <td className="fw-medium">
                          {doc.title || t('analytics.untitledDocument')}
                        </td>
                        <td className="text-end">
                          <Badge bg="primary" pill>
                            {formatNumber(doc.query_count)}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                    {documentAnalyticsData.top_queried_documents.length === 0 && (
                      <tr>
                        <td colSpan={2} className="text-center py-4">
                          {t('analytics.noQueriedDocuments')}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </Card>
            
            {/* Dosya boyutu dağılımı - mobil için kaydırılabilir */}
            <Card className="mb-4">
              <Card.Header>
                <h5 className="mb-0">{t('analytics.fileSizeDistribution')}</h5>
              </Card.Header>
              <div className="table-responsive">
                <table className="table table-bordered mb-0">
                  <thead>
                    <tr>
                      <th>{t('analytics.sizeRange')}</th>
                      <th className="text-end">{t('analytics.documentCount')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {documentAnalyticsData.file_size_distribution.map((item: any, index: number) => (
                      <tr key={index}>
                        <td>{item.range}</td>
                        <td className="text-end">{formatNumber(item.count)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </>
        )}
        
        {/* Sorgu Analitikleri İçeriği */}
        {activeTab === 'query-analytics' && !loading && queryAnalyticsData && (
          <>
            {/* Özet metrikler - mobil için satır halinde */}
            <Row className="mb-4 gy-3">
              <Col xs="12" md="4">
                <Card className="h-100 analytics-card">
                  <Card.Body className="d-flex flex-column align-items-center">
                    <h6 className="text-muted mb-2">{t('analytics.totalQueries')}</h6>
                    <div className="analytics-value">{formatNumber(queryAnalyticsData.total_queries)}</div>
                  </Card.Body>
                </Card>
              </Col>
              <Col xs="12" md="4">
                <Card className="h-100 analytics-card">
                  <Card.Body className="d-flex flex-column align-items-center">
                    <h6 className="text-muted mb-2">{t('analytics.avgQueryTime')}</h6>
                    <div className="analytics-value">
                      {formatNumber(queryAnalyticsData.average_query_time_ms)}
                      <span className="text-muted small ms-1">ms</span>
                    </div>
                  </Card.Body>
                </Card>
              </Col>
              <Col xs="12" md="4">
                <Card className="h-100 analytics-card">
                  <Card.Body className="d-flex flex-column align-items-center">
                    <h6 className="text-muted mb-2">{t('analytics.avgQueriesPerUser')}</h6>
                    <div className="analytics-value">{formatNumber(queryAnalyticsData.average_queries_per_user)}</div>
                  </Card.Body>
                </Card>
              </Col>
            </Row>
            
            {/* Grafikler - mobil için tam genişlik */}
            <Row className="mb-4 gy-4">
              <Col xs="12" lg="8">
                <Card className="h-100">
                  <Card.Header>
                    <h5 className="mb-0">{t('analytics.dailyQueries')}</h5>
                  </Card.Header>
                  <Card.Body>
                    <div className="chart-container" style={{ height: '300px' }}>
                      {queryChartData && (
                        <Line data={queryChartData} options={chartOptions} />
                      )}
                    </div>
                  </Card.Body>
                </Card>
              </Col>
              <Col xs="12" lg="4">
                <Card className="h-100">
                  <Card.Header>
                    <h5 className="mb-0">{t('analytics.queryTypeDistribution')}</h5>
                  </Card.Header>
                  <Card.Body>
                    <div className="chart-container" style={{ height: '300px' }}>
                      {queryTypeChartData && (
                        <Pie data={queryTypeChartData} options={chartOptions} />
                      )}
                    </div>
                  </Card.Body>
                </Card>
              </Col>
            </Row>
            
            {/* Popüler anahtar kelimeler - mobil için optimizasyon */}
            <Card className="mb-4">
              <Card.Header>
                <h5 className="mb-0">{t('analytics.popularKeywords')}</h5>
              </Card.Header>
              <Card.Body>
                <div className="d-flex flex-wrap gap-2">
                  {queryAnalyticsData.popular_keywords.map((keyword: any, index: number) => (
                    <Badge 
                      key={index}
                      bg="light" 
                      text="dark" 
                      className="fs-6 py-2 px-3 mb-1"
                      style={{ 
                        opacity: 0.7 + 0.3 * ((keyword.count) / (queryAnalyticsData.popular_keywords[0]?.count || 1))
                      }}
                    >
                      {keyword.keyword}
                      <span className="ms-2 text-muted small">
                        {formatNumber(keyword.count)}
                      </span>
                    </Badge>
                  ))}
                  {queryAnalyticsData.popular_keywords.length === 0 && (
                    <div className="text-muted text-center w-100 py-3">
                      {t('analytics.noKeywords')}
                    </div>
                  )}
                </div>
              </Card.Body>
            </Card>
          </>
        )}
        
        {/* Sistem Kullanımı İçeriği */}
        {activeTab === 'system-usage' && !loading && systemUsageData && (
          <>
            {/* Özet metrikler - mobil için satır halinde */}
            <Row className="mb-4 gy-3">
              <Col xs="12" md="4">
                <Card className="h-100 analytics-card">
                  <Card.Body className="d-flex flex-column align-items-center">
                    <h6 className="text-muted mb-2">{t('analytics.successRate')}</h6>
                    <div className="analytics-value">
                      {formatPercentage(systemUsageData.success_rate_percentage)}%
                    </div>
                    <div className="mt-1 text-muted">
                      <span className="text-success me-1">{formatNumber(systemUsageData.successful_queries)}</span>
                      <span className="small">/</span>
                      <span className="text-danger ms-1">{formatNumber(systemUsageData.failed_queries)}</span>
                    </div>
                  </Card.Body>
                </Card>
              </Col>
              <Col xs="12" md="4">
                <Card className="h-100 analytics-card">
                  <Card.Body className="d-flex flex-column align-items-center">
                    <h6 className="text-muted mb-2">{t('analytics.maxConcurrentSessions')}</h6>
                    <div className="analytics-value">{formatNumber(systemUsageData.max_concurrent_sessions)}</div>
                  </Card.Body>
                </Card>
              </Col>
              <Col xs="12" md="4">
                <Card className="h-100 analytics-card">
                  <Card.Body className="d-flex flex-column align-items-center">
                    <h6 className="text-muted mb-2">{t('analytics.avgConcurrentSessions')}</h6>
                    <div className="analytics-value">{formatNumber(systemUsageData.avg_concurrent_sessions)}</div>
                  </Card.Body>
                </Card>
              </Col>
            </Row>
            
            {/* Grafikler - mobil için tam genişlik */}
            <Row className="mb-4 gy-4">
              <Col xs="12" lg="6">
                <Card className="h-100">
                  <Card.Header>
                    <h5 className="mb-0">{t('analytics.hourlyActivityPattern')}</h5>
                  </Card.Header>
                  <Card.Body>
                    <div className="chart-container" style={{ height: '300px' }}>
                      {hourlyActivityChartData && (
                        <Bar data={hourlyActivityChartData} options={chartOptions} />
                      )}
                    </div>
                  </Card.Body>
                </Card>
              </Col>
              <Col xs="12" lg="6">
                <Card className="h-100">
                  <Card.Header>
                    <h5 className="mb-0">{t('analytics.weeklyActivityPattern')}</h5>
                  </Card.Header>
                  <Card.Body>
                    <div className="chart-container" style={{ height: '300px' }}>
                      {systemUsageData.weekly_activity_pattern && (
                        <Bar 
                          data={{
                            labels: systemUsageData.weekly_activity_pattern.map((item: any) => item.day_name),
                            datasets: [
                              {
                                label: t('analytics.eventCount'),
                                data: systemUsageData.weekly_activity_pattern.map((item: any) => item.count),
                                backgroundColor: 'rgba(255, 99, 132, 0.5)',
                                borderColor: 'rgb(255, 99, 132)',
                                borderWidth: 1
                              }
                            ]
                          }}
                          options={chartOptions}
                        />
                      )}
                    </div>
                  </Card.Body>
                </Card>
              </Col>
            </Row>
          </>
        )}
      </Container>
    </ResponsiveLayout>
  );
};

export default AnalyticsPage;