// Last reviewed: 2025-04-30 08:16:40 UTC (User: Teeksss)
import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Alert, Button, Spinner, Badge } from 'react-bootstrap';
import { Line, Bar, Doughnut } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, ArcElement, Title, Tooltip, Legend, ChartOptions } from 'chart.js';
import { FaSyncAlt, FaServer, FaMemory, FaHdd, FaNetworkWired, FaExclamationTriangle } from 'react-icons/fa';
import { useTranslation } from 'react-i18next';

import API from '../../api/api';
import { useToast } from '../../contexts/ToastContext';

// Chart.js kayıt
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

// Metrik tipi
interface Metric {
  timestamp: string;
  metrics: {
    cpu: {
      percent: number;
      count: number;
      load_avg_1m: number;
      load_avg_5m: number;
      load_avg_15m: number;
    };
    memory: {
      percent: number;
      used_mb: number;
      total_mb: number;
      free_mb: number;
    };
    disk: {
      percent: number;
      used_gb: number;
      total_gb: number;
      free_gb: number;
    };
    network: {
      bytes_sent: number;
      bytes_recv: number;
    };
    system: {
      uptime_seconds: number;
      hostname: string;
      os: string;
      os_version: string;
    };
    api?: {
      requests_total: number;
      errors_total: number;
      errors_by_path?: Record<string, number>;
      avg_duration_ms_by_path?: Record<string, number>;
    };
  };
}

// Renk paleti
const colors = {
  cpu: 'rgba(54, 162, 235, 0.7)',
  memory: 'rgba(255, 99, 132, 0.7)',
  disk: 'rgba(75, 192, 192, 0.7)',
  apiRequests: 'rgba(153, 102, 255, 0.7)',
  apiErrors: 'rgba(255, 159, 64, 0.7)',
  success: 'rgba(40, 167, 69, 0.7)',
  warning: 'rgba(255, 193, 7, 0.7)',
  danger: 'rgba(220, 53, 69, 0.7)',
};

const MonitoringDashboard: React.FC = () => {
  const { t } = useTranslation();
  const { showToast } = useToast();
  
  // State
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [currentMetric, setCurrentMetric] = useState<Metric | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshInterval, setRefreshInterval] = useState<number>(30); // saniye
  const [isMonitoringActive, setIsMonitoringActive] = useState<boolean>(false);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  
  // Otomatik yenileme için interval ID
  const refreshIntervalRef = React.useRef<NodeJS.Timeout | null>(null);
  
  // İlk yükleme
  useEffect(() => {
    fetchMetrics();
    
    // Monitoring durumunu kontrol et
    checkMonitoringStatus();
    
    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
    };
  }, []);
  
  // Otomatik yenileme
  useEffect(() => {
    if (autoRefresh) {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
      
      refreshIntervalRef.current = setInterval(() => {
        fetchMetrics();
      }, refreshInterval * 1000);
    } else if (refreshIntervalRef.current) {
      clearInterval(refreshIntervalRef.current);
    }
    
    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
    };
  }, [autoRefresh, refreshInterval]);
  
  // Monitoring durumunu kontrol et
  const checkMonitoringStatus = async () => {
    try {
      // Bu endpoint aslında monitoring servisinin aktif olup olmadığını kontrol etmeli
      // Şu an için basit şekilde metric dönüyorsa aktif kabul ediyoruz
      const response = await API.get('/monitoring/metrics');
      setIsMonitoringActive(true);
    } catch (err) {
      console.error('Error checking monitoring status:', err);
      setIsMonitoringActive(false);
    }
  };
  
  // Metrikleri getir
  const fetchMetrics = async () => {
    try {
      setError(null);
      
      // Mevcut metrikleri getir
      const currentResponse = await API.get('/monitoring/metrics');
      setCurrentMetric(currentResponse.data);
      
      // Metrik geçmişini getir (son 60 kayıt)
      const historyResponse = await API.get('/monitoring/metrics/history', {
        params: { count: 60 }
      });
      
      setMetrics(historyResponse.data);
      
    } catch (err: any) {
      console.error('Error fetching metrics:', err);
      setError(err?.response?.data?.detail || t('admin.monitoring.fetchError'));
    } finally {
      setLoading(false);
    }
  };
  
  // Monitoring servisini başlat/durdur
  const toggleMonitoringService = async () => {
    try {
      if (isMonitoringActive) {
        await API.post('/monitoring/stop');
        setIsMonitoringActive(false);
        showToast('success', t('admin.monitoring.stoppedSuccess'));
      } else {
        await API.post('/monitoring/start');
        setIsMonitoringActive(true);
        showToast('success', t('admin.monitoring.startedSuccess'));
        
        // Metrikleri hemen getir
        fetchMetrics();
      }
    } catch (err: any) {
      console.error('Error toggling monitoring service:', err);
      showToast('error', err?.response?.data?.detail || t('admin.monitoring.toggleError'));
    }
  };
  
  // Line chart için veri hazırla
  const prepareLineChartData = (
    dataKey: string, 
    label: string,
    color: string, 
    metricPath: string[]
  ) => {
    const timestamps = metrics.map(m => {
      const date = new Date(m.timestamp);
      return `${date.getHours()}:${date.getMinutes().toString().padStart(2, '0')}`;
    });
    
    const values = metrics.map(m => {
      // Nested path'ten değeri al (metrics.cpu.percent gibi)
      let value = m.metrics;
      for (const key of metricPath) {
        value = value?.[key as keyof typeof value];
      }
      return value as number;
    });
    
    return {
      labels: timestamps,
      datasets: [
        {
          label,
          data: values,
          backgroundColor: color,
          borderColor: color,
          fill: false,
          tension: 0.4
        }
      ]
    };
  };
  
  // Doughnut chart için veri hazırla
  const prepareDoughnutData = (used: number, free: number, label: string, color: string) => {
    return {
      labels: [`${label} ${t('admin.monitoring.used')}`, `${label} ${t('admin.monitoring.free')}`],
      datasets: [
        {
          data: [used, free],
          backgroundColor: [color, 'rgba(220, 220, 220, 0.7)'],
          borderColor: ['transparent', 'transparent'],
          hoverBackgroundColor: [color, 'rgba(200, 200, 200, 0.9)']
        }
      ]
    };
  };
  
  // Bar chart için veri hazırla
  const prepareBarChartData = (
    labels: string[],
    values: number[],
    label: string,
    color: string
  ) => {
    return {
      labels,
      datasets: [
        {
          label,
          data: values,
          backgroundColor: color,
          borderColor: 'rgba(0, 0, 0, 0.1)',
          borderWidth: 1
        }
      ]
    };
  };
  
  // Chart options
  const lineChartOptions: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      y: {
        beginAtZero: true
      }
    },
    plugins: {
      legend: {
        position: 'top' as const,
      }
    }
  };
  
  const doughnutChartOptions: ChartOptions<'doughnut'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      }
    }
  };
  
  const barChartOptions: ChartOptions<'bar'> = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      y: {
        beginAtZero: true
      }
    },
    plugins: {
      legend: {
        position: 'top' as const,
      }
    }
  };
  
  // Durum renk sınıfı
  const getStatusColorClass = (percent: number) => {
    if (percent >= 90) return 'danger';
    if (percent >= 75) return 'warning';
    return 'success';
  };
  
  // Formatlanmış zaman
  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    return `${days}d ${hours}h ${minutes}m`;
  };
  
  // Formatlanmış boyut
  const formatBytes = (bytes: number, decimals = 2) => {
    if (bytes === 0) return '0 B';
    
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  };
  
  // İçerik yükleniyor durumu
  if (loading) {
    return (
      <div className="text-center py-5">
        <Spinner animation="border" variant="primary" />
        <p className="mt-3">{t('admin.monitoring.loading')}</p>
      </div>
    );
  }
  
  return (
    <div className="monitoring-dashboard">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>
          <FaServer className="me-2" />
          {t('admin.monitoring.title')}
        </h2>
        
        <div>
          <Button
            variant={isMonitoringActive ? 'danger' : 'success'}
            size="sm"
            className="me-2"
            onClick={toggleMonitoringService}
          >
            {isMonitoringActive ? t('admin.monitoring.stop') : t('admin.monitoring.start')}
          </Button>
          
          <Button
            variant={autoRefresh ? 'primary' : 'outline-primary'}
            size="sm"
            className="me-2"
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            {autoRefresh ? t('admin.monitoring.autoRefreshOn') : t('admin.monitoring.autoRefreshOff')}
          </Button>
          
          <Button 
            variant="outline-secondary" 
            size="sm" 
            onClick={fetchMetrics}
          >
            <FaSyncAlt className="me-1" />
            {t('admin.monitoring.refresh')}
          </Button>
        </div>
      </div>
      
      {error && (
        <Alert variant="danger" className="mb-4">
          <FaExclamationTriangle className="me-2" />
          {error}
        </Alert>
      )}
      
      {!isMonitoringActive && (
        <Alert variant="warning" className="mb-4">
          <FaExclamationTriangle className="me-2" />
          {t('admin.monitoring.notActive')}
        </Alert>
      )}
      
      {currentMetric && (
        <>
          {/* Özet Kartlar */}
          <Row className="mb-4">
            <Col md={3}>
              <Card className="h-100">
                <Card.Body>
                  <h5 className="card-title">
                    <FaServer className="me-2" />
                    {t('admin.monitoring.cpu')}
                  </h5>
                  <h2 className={`text-${getStatusColorClass(currentMetric.metrics.cpu.percent)}`}>
                    {currentMetric.metrics.cpu.percent}%
                  </h2>
                  <div className="small text-muted">
                    {t('admin.monitoring.cores')}: {currentMetric.metrics.cpu.count}
                  </div>
                  <div className="small text-muted">
                    {t('admin.monitoring.loadAvg')}: {currentMetric.metrics.cpu.load_avg_1m.toFixed(2)}
                  </div>
                </Card.Body>
              </Card>
            </Col>
            
            <Col md={3}>
              <Card className="h-100">
                <Card.Body>
                  <h5 className="card-title">
                    <FaMemory className="me-2" />
                    {t('admin.monitoring.memory')}
                  </h5>
                  <h2 className={`text-${getStatusColorClass(currentMetric.metrics.memory.percent)}`}>
                    {currentMetric.metrics.memory.percent}%
                  </h2>
                  <div className="small text-muted">
                    {t('admin.monitoring.used')}: {(currentMetric.metrics.memory.used_mb / 1024).toFixed(1)} GB
                  </div>
                  <div className="small text-muted">
                    {t('admin.monitoring.total')}: {(currentMetric.metrics.memory.total_mb / 1024).toFixed(1)} GB
                  </div>
                </Card.Body>
              </Card>
            </Col>
            
            <Col md={3}>
              <Card className="h-100">
                <Card.Body>
                  <h5 className="card-title">
                    <FaHdd className="me-2" />
                    {t('admin.monitoring.disk')}
                  </h5>
                  <h2 className={`text-${getStatusColorClass(currentMetric.metrics.disk.percent)}`}>
                    {currentMetric.metrics.disk.percent}%
                  </h2>
                  <div className="small text-muted">
                    {t('admin.monitoring.used')}: {currentMetric.metrics.disk.used_gb.toFixed(1)} GB
                  </div>
                  <div className="small text-muted">
                    {t('admin.monitoring.free')}: {currentMetric.metrics.disk.free_gb.toFixed(1)} GB
                  </div>
                </Card.Body>
              </Card>
            </Col>
            
            <Col md={3}>
              <Card className="h-100">
                <Card.Body>
                  <h5 className="card-title">
                    <FaNetworkWired className="me-2" />
                    {t('admin.monitoring.system')}
                  </h5>
                  <div className="mb-2">
                    <Badge bg="info">{currentMetric.metrics.system.os}</Badge>
                  </div>
                  <div className="small text-muted">
                    {t('admin.monitoring.hostname')}: {currentMetric.metrics.system.hostname}
                  </div>
                  <div className="small text-muted">
                    {t('admin.monitoring.uptime')}: {formatUptime(currentMetric.metrics.system.uptime_seconds)}
                  </div>
                </Card.Body>
              </Card>
            </Col>
          </Row>
          
          {/* Çizelgeler */}
          <Row className="mb-4">
            <Col lg={8}>
              <Card className="h-100">
                <Card.Header>{t('admin.monitoring.resourceUsage')}</Card.Header>
                <Card.Body>
                  <div style={{ height: '300px' }}>
                    <Line 
                      data={{
                        labels: metrics.map(m => {
                          const date = new Date(m.timestamp);
                          return `${date.getHours()}:${date.getMinutes().toString().padStart(2, '0')}`;
                        }),
                        datasets: [
                          {
                            label: t('admin.monitoring.cpu'),
                            data: metrics.map(m => m.metrics.cpu.percent),
                            backgroundColor: colors.cpu,
                            borderColor: colors.cpu,
                            fill: false,
                            tension: 0.4
                          },
                          {
                            label: t('admin.monitoring.memory'),
                            data: metrics.map(m => m.metrics.memory.percent),
                            backgroundColor: colors.memory,
                            borderColor: colors.memory,
                            fill: false,
                            tension: 0.4
                          },
                          {
                            label: t('admin.monitoring.disk'),
                            data: metrics.map(m => m.metrics.disk.percent),
                            backgroundColor: colors.disk,
                            borderColor: colors.disk,
                            fill: false,
                            tension: 0.4
                          }
                        ]
                      }}
                      options={lineChartOptions}
                    />
                  </div>
                </Card.Body>
              </Card>
            </Col>
            
            <Col lg={4}>
              <Card className="h-100">
                <Card.Header>{t('admin.monitoring.diskUsage')}</Card.Header>
                <Card.Body>
                  <div style={{ height: '300px' }}>
                    <Doughnut 
                      data={prepareDoughnutData(
                        currentMetric.metrics.disk.used_gb, 
                        currentMetric.metrics.disk.free_gb, 
                        t('admin.monitoring.disk'),
                        colors.disk
                      )}
                      options={doughnutChartOptions}
                    />
                  </div>
                </Card.Body>
              </Card>
            </Col>
          </Row>
          
          {/* API İstatistikleri */}
          {currentMetric.metrics.api && (
            <Row className="mb-4">
              <Col md={6}>
                <Card>
                  <Card.Header>{t('admin.monitoring.apiRequests')}</Card.Header>
                  <Card.Body>
                    <div style={{ height: '250px' }}>
                      <Line 
                        data={prepareLineChartData(
                          'apiRequests',
                          t('admin.monitoring.apiRequests'),
                          colors.apiRequests,
                          ['api', 'requests_total']
                        )}
                        options={lineChartOptions}
                      />
                    </div>
                  </Card.Body>
                </Card>
              </Col>
              
              <Col md={6}>
                <Card>
                  <Card.Header>{t('admin.monitoring.apiErrors')}</Card.Header>
                  <Card.Body>
                    <div style={{ height: '250px' }}>
                      <Line 
                        data={prepareLineChartData(
                          'apiErrors',
                          t('admin.monitoring.apiErrors'),
                          colors.apiErrors,
                          ['api', 'errors_total']
                        )}
                        options={lineChartOptions}
                      />
                    </div>
                  </Card.Body>
                </Card>
              </Col>
            </Row>
          )}
          
          {/* API Yolu Bazlı İstatistikler */}
          {currentMetric.metrics.api?.errors_by_path && 
           Object.keys(currentMetric.metrics.api.errors_by_path).length > 0 && (
            <Row className="mb-4">
              <Col md={12}>
                <Card>
                  <Card.Header>{t('admin.monitoring.apiErrorsByPath')}</Card.Header>
                  <Card.Body>
                    <div style={{ height: '250px' }}>
                      <Bar 
                        data={prepareBarChartData(
                          Object.keys(currentMetric.metrics.api.errors_by_path),
                          Object.values(currentMetric.metrics.api.errors_by_path),
                          t('admin.monitoring.errorCount'),
                          colors.apiErrors
                        )}
                        options={barChartOptions}
                      />
                    </div>
                  </Card.Body>
                </Card>
              </Col>
            </Row>
          )}
          
          {/* Ağ Trafiği */}
          <Row>
            <Col md={12}>
              <Card>
                <Card.Header>{t('admin.monitoring.networkTraffic')}</Card.Header>
                <Card.Body>
                  <div className="d-flex justify-content-around mb-3">
                    <div className="text-center">
                      <h5>{t('admin.monitoring.bytesSent')}</h5>
                      <h3 className="text-primary">
                        {formatBytes(currentMetric.metrics.network.bytes_sent)}
                      </h3>
                    </div>
                    
                    <div className="text-center">
                      <h5>{t('admin.monitoring.bytesRecv')}</h5>
                      <h3 className="text-primary">
                        {formatBytes(currentMetric.metrics.network.bytes_recv)}
                      </h3>
                    </div>
                  </div>
                </Card.Body>
              </Card>
            </Col>
          </Row>
        </>
      )}
    </div>
  );
};

export default MonitoringDashboard;