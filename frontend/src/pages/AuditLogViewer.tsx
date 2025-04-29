// Last reviewed: 2025-04-29 13:59:34 UTC (User: TeeksssAPI)
import React, { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Container,
  Card,
  Table,
  Form,
  Button,
  Row,
  Col,
  Badge,
  Pagination,
  Spinner,
  Alert,
  Dropdown,
  Modal
} from 'react-bootstrap';
import { useQuery } from 'react-query';
import DatePicker from 'react-datepicker';
import { format } from 'date-fns';
import { FaSearch, FaFilter, FaDownload, FaChartBar, FaEye, FaTrash } from 'react-icons/fa';
import { Line, Bar } from 'react-chartjs-2';

import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import AuditLogAPI from '../api/AuditLogAPI';
import { JsonViewer } from '../components/JsonViewer';
import { ExportModal } from '../components/ExportModal';
import { AuditLogFilterForm } from '../components/AuditLogFilterForm';
import { PermissionGuard } from '../components/PermissionGuard';

// Grafik için requires
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  TimeScale
);

// Denetim kaydı türleri için renk haritası
const eventTypeColors = {
  auth: 'primary',
  data: 'info',
  admin: 'dark',
  system: 'secondary',
  security: 'danger',
  api: 'warning',
  integration: 'success'
};

// Denetim kaydı durumları için renk haritası
const statusColors = {
  success: 'success',
  failure: 'danger',
  warning: 'warning',
  info: 'info'
};

const AuditLogViewer: React.FC = () => {
  const { t } = useTranslation();
  const { currentUser, hasPermission } = useAuth();
  const { showToast } = useToast();

  // Filtre durumu
  const [filters, setFilters] = useState({
    userId: '',
    resourceType: '',
    resourceId: '',
    action: '',
    eventType: '',
    startDate: null as Date | null,
    endDate: null as Date | null,
    ipAddress: '',
    organizationId: currentUser?.organizationId || ''
  });

  // Sayfalama
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  // Seçili kayıt
  const [selectedLog, setSelectedLog] = useState<any>(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);

  // İstatistik grafikleri
  const [showStatsModal, setShowStatsModal] = useState(false);
  const [statsData, setStatsData] = useState<any>(null);
  const [statsLoading, setStatsLoading] = useState(false);

  // Dışa aktarma
  const [showExportModal, setShowExportModal] = useState(false);
  const [exportFormat, setExportFormat] = useState('json');
  const [exportIncludeDetails, setExportIncludeDetails] = useState(true);

  // Filtreleme modali
  const [showFilterModal, setShowFilterModal] = useState(false);

  // Filtre uygulama
  const applyFilters = (newFilters: any) => {
    setFilters({...filters, ...newFilters});
    setPage(1); // Filtreleme yapıldığında ilk sayfaya dön
    setShowFilterModal(false);
  };

  // Kayıtları getir
  const { data, isLoading, error, refetch } = useQuery(
    ['auditLogs', filters, page, pageSize],
    () => AuditLogAPI.getAuditLogs({
      page,
      pageSize,
      ...filters,
      startDate: filters.startDate ? format(filters.startDate, 'yyyy-MM-dd\'T\'HH:mm:ss') : undefined,
      endDate: filters.endDate ? format(filters.endDate, 'yyyy-MM-dd\'T\'HH:mm:ss') : undefined
    }),
    {
      keepPreviousData: true,
      staleTime: 60000, // 1 dakika
      refetchOnWindowFocus: false
    }
  );

  // Sayfa değişimi
  const handlePageChange = (pageNumber: number) => {
    setPage(pageNumber);
  };

  // Sayfa başına kayıt sayısı değişimi
  const handlePageSizeChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setPageSize(Number(event.target.value));
    setPage(1);
  };

  // Detayları göster
  const showDetails = (log: any) => {
    setSelectedLog(log);
    setShowDetailsModal(true);
  };

  // İstatistikleri getir ve göster
  const loadStats = async () => {
    try {
      setStatsLoading(true);
      const stats = await AuditLogAPI.getAuditLogStats({
        resourceType: filters.resourceType || undefined,
        userId: filters.userId || undefined,
        organizationId: filters.organizationId || undefined,
        startDate: filters.startDate ? format(filters.startDate, 'yyyy-MM-dd\'T\'HH:mm:ss') : undefined,
        endDate: filters.endDate ? format(filters.endDate, 'yyyy-MM-dd\'T\'HH:mm:ss') : undefined
      });
      
      setStatsData(stats);
      setShowStatsModal(true);
    } catch (err) {
      showToast(t('auditLog.errors.statsLoadFailed'), 'error');
      console.error('Failed to load audit log stats:', err);
    } finally {
      setStatsLoading(false);
    }
  };

  // Dışa aktarma
  const exportLogs = async () => {
    try {
      const exportData = await AuditLogAPI.exportAuditLogs({
        format: exportFormat,
        includeDetails: exportIncludeDetails,
        filters: {
          ...filters,
          startDate: filters.startDate ? format(filters.startDate, 'yyyy-MM-dd\'T\'HH:mm:ss') : undefined,
          endDate: filters.endDate ? format(filters.endDate, 'yyyy-MM-dd\'T\'HH:mm:ss') : undefined
        }
      });
      
      // Dosya indir
      const fileName = `audit-logs-export-${format(new Date(), 'yyyy-MM-dd-HH-mm')}`;
      const fileExtension = exportFormat === 'json' ? 'json' : 'csv';
      const blob = new Blob([exportData], { type: exportFormat === 'json' ? 'application/json' : 'text/csv' });
      const url = URL.createObjectURL(blob);
      
      const a = document.createElement('a');
      a.href = url;
      a.download = `${fileName}.${fileExtension}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      setShowExportModal(false);
      showToast(t('auditLog.exportSuccess'), 'success');
    } catch (err) {
      showToast(t('auditLog.errors.exportFailed'), 'error');
      console.error('Failed to export audit logs:', err);
    }
  };

  // İstatistik grafiğı için veri hazırlama
  const statsChartData = useMemo(() => {
    if (!statsData) return null;

    // Olay türlerine göre dağılım grafiği
    const eventTypeData = {
      labels: Object.keys(statsData.eventTypeCounts || {}),
      datasets: [
        {
          label: t('auditLog.stats.byEventType'),
          data: Object.values(statsData.eventTypeCounts || {}),
          backgroundColor: Object.keys(statsData.eventTypeCounts || {}).map(
            key => {
              const colorKey = key as keyof typeof eventTypeColors;
              return `var(--bs-${eventTypeColors[colorKey] || 'primary'})`;
            }
          ),
          borderWidth: 1,
        },
      ],
    };

    // Zaman bazlı aktivite grafiği
    const timeSeriesData = {
      labels: statsData.timeSeries?.map((item: any) => item.date) || [],
      datasets: [
        {
          label: t('auditLog.stats.activityOverTime'),
          data: statsData.timeSeries?.map((item: any) => item.count) || [],
          fill: false,
          borderColor: 'rgb(75, 192, 192)',
          backgroundColor: 'rgba(75, 192, 192, 0.2)',
          tension: 0.1,
        },
      ],
    };

    return {
      eventTypeData,
      timeSeriesData
    };
  }, [statsData, t]);
  
  // Yetki kontrolü
  if (!hasPermission('audit_logs:view')) {
    return (
      <Container className="py-4">
        <Alert variant="warning">
          {t('common.noPermission')}
        </Alert>
      </Container>
    );
  }

  return (
    <Container fluid className="py-4">
      <Card>
        <Card.Header className="d-flex justify-content-between align-items-center">
          <h3>{t('auditLog.title')}</h3>
          <div className="d-flex gap-2">
            <Button 
              variant="outline-primary" 
              onClick={() => setShowFilterModal(true)}
              title={t('auditLog.actions.filter')}
            >
              <FaFilter /> <span className="d-none d-md-inline">{t('auditLog.actions.filter')}</span>
            </Button>
            
            <PermissionGuard permission="audit_logs:export">
              <Button 
                variant="outline-secondary" 
                onClick={() => setShowExportModal(true)}
                title={t('auditLog.actions.export')}
              >
                <FaDownload /> <span className="d-none d-md-inline">{t('auditLog.actions.export')}</span>
              </Button>
            </PermissionGuard>
            
            <PermissionGuard permission="audit_logs:stats">
              <Button 
                variant="outline-info" 
                onClick={loadStats}
                disabled={statsLoading}
                title={t('auditLog.actions.showStats')}
              >
                {statsLoading ? <Spinner size="sm" animation="border" /> : <FaChartBar />}{' '}
                <span className="d-none d-md-inline">{t('auditLog.actions.showStats')}</span>
              </Button>
            </PermissionGuard>
          </div>
        </Card.Header>
        
        <Card.Body>
          {isLoading ? (
            <div className="text-center p-5">
              <Spinner animation="border" />
              <p className="mt-3">{t('common.loading')}</p>
            </div>
          ) : error ? (
            <Alert variant="danger">
              {t('auditLog.errors.loadFailed')}
            </Alert>
          ) : data?.items?.length === 0 ? (
            <Alert variant="info">
              {t('auditLog.noResults')}
            </Alert>
          ) : (
            <>
              <div className="table-responsive">
                <Table hover striped>
                  <thead>
                    <tr>
                      <th>{t('auditLog.fields.timestamp')}</th>
                      <th>{t('auditLog.fields.eventType')}</th>
                      <th>{t('auditLog.fields.action')}</th>
                      <th>{t('auditLog.fields.user')}</th>
                      <th>{t('auditLog.fields.resource')}</th>
                      <th>{t('auditLog.fields.status')}</th>
                      <th>{t('common.actions')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.map((log: any) => (
                      <tr key={log.id}>
                        <td>{new Date(log.timestamp).toLocaleString()}</td>
                        <td>
                          <Badge bg={eventTypeColors[log.event_type as keyof typeof eventTypeColors] || 'primary'}>
                            {log.event_type}
                          </Badge>
                        </td>
                        <td>{log.action}</td>
                        <td>{log.user_id}</td>
                        <td>
                          {log.resource_type && (
                            <small className="text-muted">{log.resource_type}:</small>
                          )}{' '}
                          {log.resource_id}
                        </td>
                        <td>
                          <Badge bg={statusColors[log.status as keyof typeof statusColors] || 'secondary'}>
                            {log.status}
                          </Badge>
                        </td>
                        <td>
                          <Button
                            size="sm"
                            variant="outline-secondary"
                            onClick={() => showDetails(log)}
                            title={t('common.details')}
                          >
                            <FaEye />
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </div>
              
              {/* Sayfalama */}
              <div className="d-flex justify-content-between align-items-center mt-3">
                <div className="d-flex align-items-center">
                  <span className="me-2">{t('pagination.show')}</span>
                  <Form.Select
                    value={pageSize}
                    onChange={handlePageSizeChange}
                    className="form-select-sm"
                    style={{ width: '70px' }}
                  >
                    <option value="10">10</option>
                    <option value="20">20</option>
                    <option value="50">50</option>
                    <option value="100">100</option>
                  </Form.Select>
                  <span className="ms-2">
                    {t('pagination.showing', { 
                      start: (page - 1) * pageSize + 1, 
                      end: Math.min(page * pageSize, data.total), 
                      total: data.total
                    })}
                  </span>
                </div>
                
                <Pagination className="mb-0">
                  <Pagination.First
                    disabled={page === 1}
                    onClick={() => handlePageChange(1)}
                  />
                  <Pagination.Prev
                    disabled={page === 1}
                    onClick={() => handlePageChange(page - 1)}
                  />
                  
                  {/* Sayfa numaraları */}
                  {Array.from({ length: Math.ceil(data.total / pageSize) }).slice(
                    Math.max(0, page - 3),
                    Math.min(Math.ceil(data.total / pageSize), page + 2)
                  ).map((_, idx) => {
                    const pageNum = Math.max(1, page - 2) + idx;
                    return (
                      <Pagination.Item
                        key={pageNum}
                        active={pageNum === page}
                        onClick={() => handlePageChange(pageNum)}
                      >
                        {pageNum}
                      </Pagination.Item>
                    );
                  })}
                  
                  <Pagination.Next
                    disabled={page >= Math.ceil(data.total / pageSize)}
                    onClick={() => handlePageChange(page + 1)}
                  />
                  <Pagination.Last
                    disabled={page >= Math.ceil(data.total / pageSize)}
                    onClick={() => handlePageChange(Math.ceil(data.total / pageSize))}
                  />
                </Pagination>
              </div>
            </>
          )}
        </Card.Body>
      </Card>
      
      {/* Detay Modal */}
      <Modal
        show={showDetailsModal}
        onHide={() => setShowDetailsModal(false)}
        size="lg"
        centered
      >
        <Modal.Header closeButton>
          <Modal.Title>{t('auditLog.detailsTitle')}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {selectedLog && (
            <div>
              <Row className="mb-3">
                <Col md={6}>
                  <h5>{t('auditLog.fields.timestamp')}</h5>
                  <p>{new Date(selectedLog.timestamp).toLocaleString()}</p>
                </Col>
                <Col md={6}>
                  <h5>{t('auditLog.fields.id')}</h5>
                  <p className="text-monospace">{selectedLog.id}</p>
                </Col>
              </Row>
              
              <Row className="mb-3">
                <Col md={6}>
                  <h5>{t('auditLog.fields.eventType')}</h5>
                  <Badge bg={eventTypeColors[selectedLog.event_type as keyof typeof eventTypeColors] || 'primary'}>
                    {selectedLog.event_type}
                  </Badge>
                </Col>
                <Col md={6}>
                  <h5>{t('auditLog.fields.status')}</h5>
                  <Badge bg={statusColors[selectedLog.status as keyof typeof statusColors] || 'secondary'}>
                    {selectedLog.status}
                  </Badge>
                </Col>
              </Row>
              
              <Row className="mb-3">
                <Col md={6}>
                  <h5>{t('auditLog.fields.user')}</h5>
                  <p>{selectedLog.user_id || '-'}</p>
                </Col>
                <Col md={6}>
                  <h5>{t('auditLog.fields.action')}</h5>
                  <p>{selectedLog.action || '-'}</p>
                </Col>
              </Row>
              
              <Row className="mb-3">
                <Col md={6}>
                  <h5>{t('auditLog.fields.resource')}</h5>
                  <p>
                    {selectedLog.resource_type && (
                      <span className="text-muted">{selectedLog.resource_type}: </span>
                    )}
                    {selectedLog.resource_id || '-'}
                  </p>
                </Col>
                <Col md={6}>
                  <h5>{t('auditLog.fields.organization')}</h5>
                  <p>{selectedLog.organization_id || '-'}</p>
                </Col>
              </Row>
              
              <Row className="mb-3">
                <Col md={6}>
                  <h5>{t('auditLog.fields.ipAddress')}</h5>
                  <p>{selectedLog.ip_address || '-'}</p>
                </Col>
                <Col md={12}>
                  <h5>{t('auditLog.fields.userAgent')}</h5>
                  <p className="text-truncate">{selectedLog.user_agent || '-'}</p>
                </Col>
              </Row>
              
              {selectedLog.details && (
                <div className="mb-3">
                  <h5>{t('auditLog.fields.details')}</h5>
                  <JsonViewer data={selectedLog.details} expandLevel={1} />
                </div>
              )}
            </div>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowDetailsModal(false)}>
            {t('common.close')}
          </Button>
        </Modal.Footer>
      </Modal>
      
      {/* İstatistik Modal */}
      <Modal
        show={showStatsModal}
        onHide={() => setShowStatsModal(false)}
        size="lg"
        centered
      >
        <Modal.Header closeButton>
          <Modal.Title>{t('auditLog.stats.title')}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {statsLoading ? (
            <div className="text-center p-5">
              <Spinner animation="border" />
              <p className="mt-3">{t('common.loading')}</p>
            </div>
          ) : !statsData ? (
            <Alert variant="info">
              {t('auditLog.stats.noData')}
            </Alert>
          ) : (
            <>
              <Row>
                <Col md={6} className="mb-4">
                  <Card>
                    <Card.Header>{t('auditLog.stats.summary')}</Card.Header>
                    <Card.Body>
                      <div className="d-flex justify-content-between mb-2">
                        <div>{t('auditLog.stats.totalEvents')}:</div>
                        <div className="fw-bold">{statsData.totalCount || 0}</div>
                      </div>
                      <div className="d-flex justify-content-between mb-2">
                        <div>{t('auditLog.stats.uniqueUsers')}:</div>
                        <div className="fw-bold">{statsData.uniqueUsers || 0}</div>
                      </div>
                      <div className="d-flex justify-content-between mb-2">
                        <div>{t('auditLog.stats.successRate')}:</div>
                        <div className="fw-bold">
                          {statsData.successRate ? `${(statsData.successRate * 100).toFixed(1)}%` : '-'}
                        </div>
                      </div>
                      <div className="d-flex justify-content-between">
                        <div>{t('auditLog.stats.dateRange')}:</div>
                        <div className="fw-bold">
                          {statsData.oldestLog && statsData.newestLog ? (
                            `${new Date(statsData.oldestLog).toLocaleDateString()} - ${new Date(statsData.newestLog).toLocaleDateString()}`
                          ) : '-'}
                        </div>
                      </div>
                    </Card.Body>
                  </Card>
                </Col>
                
                <Col md={6} className="mb-4">
                  <Card>
                    <Card.Header>{t('auditLog.stats.byEventType')}</Card.Header>
                    <Card.Body style={{ height: '220px' }}>
                      {statsChartData && <Bar data={statsChartData.eventTypeData} options={{ maintainAspectRatio: false }} />}
                    </Card.Body>
                  </Card>
                </Col>
                
                <Col md={12} className="mb-4">
                  <Card>
                    <Card.Header>{t('auditLog.stats.activityOverTime')}</Card.Header>
                    <Card.Body style={{ height: '300px' }}>
                      {statsChartData && <Line data={statsChartData.timeSeriesData} options={{ maintainAspectRatio: false }} />}
                    </Card.Body>
                  </Card>
                </Col>
              </Row>
            </>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowStatsModal(false)}>
            {t('common.close')}
          </Button>
        </Modal.Footer>
      </Modal>
      
      {/* Filtre Modal */}
      <AuditLogFilterForm
        show={showFilterModal}
        onHide={() => setShowFilterModal(false)}
        filters={filters}
        onApplyFilters={applyFilters}
        onReset={() => setFilters({
          userId: '',
          resourceType: '',
          resourceId: '',
          action: '',
          eventType: '',
          startDate: null,
          endDate: null,
          ipAddress: '',
          organizationId: currentUser?.organizationId || ''
        })}
      />
      
      {/* Dışa Aktarma Modal */}
      <Modal
        show={showExportModal}
        onHide={() => setShowExportModal(false)}
        centered
      >
        <Modal.Header closeButton>
          <Modal.Title>{t('auditLog.export.title')}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form>
            <Form.Group className="mb-3">
              <Form.Label>{t('auditLog.export.format')}</Form.Label>
              <Form.Select
                value={exportFormat}
                onChange={(e) => setExportFormat(e.target.value)}
              >
                <option value="json">JSON</option>
                <option value="csv">CSV</option>
              </Form.Select>
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Check
                type="checkbox"
                label={t('auditLog.export.includeDetails')}
                checked={exportIncludeDetails}
                onChange={(e) => setExportIncludeDetails(e.target.checked)}
              />
            </Form.Group>
            
            <Alert variant="info" className="mb-0">
              <small>
                {t('auditLog.export.note')}
              </small>
            </Alert>
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowExportModal(false)}>
            {t('common.cancel')}
          </Button>
          <Button variant="primary" onClick={exportLogs}>
            {t('auditLog.export.downloadButton')}
          </Button>
        </Modal.Footer>
      </Modal>
    </Container>
  );
};

export default AuditLogViewer;