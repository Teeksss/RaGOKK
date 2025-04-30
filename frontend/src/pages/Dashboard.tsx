// Last reviewed: 2025-04-30 12:17:45 UTC (User: Teeksssdevam et.)
import React, { useState, useEffect, useMemo } from 'react';
import { Container, Row, Col, Card, Alert } from 'react-bootstrap';
import { FaFileAlt, FaSearch, FaUser, FaTag, FaClock, FaDatabase } from 'react-icons/fa';
import { useTranslation } from 'react-i18next';
import { useDocumentStats, useQueryStats, useSystemMetrics } from '../services/graphqlClient';
import { useStats } from '../services/queryService';
import DataVisualization, { ChartType } from '../components/dashboard/DataVisualization';
import StatCard from '../components/dashboard/StatCard';
import RecentActivityList from '../components/dashboard/RecentActivityList';
import { ChartData } from 'chart.js';
import { usePerformanceMonitoring } from '../services/performanceService';
import { useDeepMemo } from '../utils/memoization';
import { format } from 'date-fns';
import { errorHandlingService } from '../services/errorHandlingService';

const Dashboard: React.FC = () => {
  const { t } = useTranslation();
  const [period, setPeriod] = useState<string>('week');
  const { measureOperation } = usePerformanceMonitoring('DashboardPage');
  
  // Fetch general stats
  const { 
    data: generalStats,
    isLoading: isStatsLoading,
    error: statsError
  } = useStats(period);
  
  // Fetch document stats with GraphQL
  const {
    data: documentStatsData,
    isLoading: isDocumentStatsLoading,
    error: documentStatsError,
    refetch: refetchDocumentStats
  } = useDocumentStats(period);
  
  // Fetch query stats with GraphQL
  const {
    data: queryStatsData,
    isLoading: isQueryStatsLoading,
    error: queryStatsError,
    refetch: refetchQueryStats
  } = useQueryStats(period);
  
  // Fetch system metrics with GraphQL
  const {
    data: systemMetricsData,
    isLoading: isSystemMetricsLoading,
    error: systemMetricsError,
    refetch: refetchSystemMetrics
  } = useSystemMetrics(period);
  
  // Handle errors
  useEffect(() => {
    if (documentStatsError) {
      errorHandlingService.handleError({
        message: 'Failed to load document statistics',
        details: documentStatsError
      });
    }
    
    if (queryStatsError) {
      errorHandlingService.handleError({
        message: 'Failed to load query statistics',
        details: queryStatsError
      });
    }
    
    if (systemMetricsError) {
      errorHandlingService.handleError({
        message: 'Failed to load system metrics',
        details: systemMetricsError
      });
    }
  }, [documentStatsError, queryStatsError, systemMetricsError]);
  
  // Prepare document stats chart data
  const documentChartData = useDeepMemo<ChartData<'line'>>(() => {
    if (!documentStatsData?.documentStats) {
      return {
        labels: [],
        datasets: []
      };
    }
    
    const stopMeasuring = measureOperation('PrepareDocumentChart');
    
    const { documentsOverTime } = documentStatsData.documentStats;
    
    const result = {
      labels: documentsOverTime.map(point => format(new Date(point.date), 'MMM d')),
      datasets: [
        {
          label: t('dashboard.documents.uploads'),
          data: documentsOverTime.map(point => point.count),
          borderColor: 'rgb(53, 162, 235)',
          backgroundColor: 'rgba(53, 162, 235, 0.5)',
          tension: 0.2,
          fill: true
        }
      ]
    };
    
    stopMeasuring();
    return result;
  }, [documentStatsData, t, measureOperation]);
  
  // Prepare document types chart data
  const documentTypesChartData = useDeepMemo<ChartData<'pie'>>(() => {
    if (!documentStatsData?.documentStats) {
      return {
        labels: [],
        datasets: []
      };
    }
    
    const stopMeasuring = measureOperation('PrepareDocumentTypesChart');
    
    const { documentsByType } = documentStatsData.documentStats;
    
    const result = {
      labels: documentsByType.map(item => item.type),
      datasets: [
        {
          data: documentsByType.map(item => item.count),
          backgroundColor: [
            'rgba(255, 99, 132, 0.7)',
            'rgba(54, 162, 235, 0.7)',
            'rgba(255, 206, 86, 0.7)',
            'rgba(75, 192, 192, 0.7)',
            'rgba(153, 102, 255, 0.7)',
            'rgba(255, 159, 64, 0.7)',
            'rgba(199, 199, 199, 0.7)',
          ],
        }
      ]
    };
    
    stopMeasuring();
    return result;
  }, [documentStatsData, measureOperation]);
  
  // Prepare query stats chart data
  const queryChartData = useDeepMemo<ChartData<'line'>>(() => {
    if (!queryStatsData?.queryStats) {
      return {
        labels: [],
        datasets: []
      };
    }
    
    const stopMeasuring = measureOperation('PrepareQueryChart');
    
    const { queriesOverTime } = queryStatsData.queryStats;
    
    const result = {
      labels: queriesOverTime.map(point => format(new Date(point.date), 'MMM d')),
      datasets: [
        {
          label: t('dashboard.queries.count'),
          data: queriesOverTime.map(point => point.count),
          borderColor: 'rgb(75, 192, 192)',
          backgroundColor: 'rgba(75, 192, 192, 0.5)',
          tension: 0.2,
          fill: true
        }
      ]
    };
    
    stopMeasuring();
    return result;
  }, [queryStatsData, t, measureOperation]);
  
  // Prepare query types chart data
  const queryTypesChartData = useDeepMemo<ChartData<'doughnut'>>(() => {
    if (!queryStatsData?.queryStats) {
      return {
        labels: [],
        datasets: []
      };
    }
    
    const stopMeasuring = measureOperation('PrepareQueryTypesChart');
    
    const { queriesByType } = queryStatsData.queryStats;
    
    const result = {
      labels: queriesByType.map(item => item.type),
      datasets: [
        {
          data: queriesByType.map(item => item.count),
          backgroundColor: [
            'rgba(75, 192, 192, 0.7)',
            'rgba(153, 102, 255, 0.7)',
            'rgba(255, 159, 64, 0.7)',
          ],
        }
      ]
    };
    
    stopMeasuring();
    return result;
  }, [queryStatsData, measureOperation]);
  
  // Prepare system metrics chart data
  const systemMetricsChartData = useDeepMemo<ChartData<'line'>>(() => {
    if (!systemMetricsData?.systemMetrics) {
      return {
        labels: [],
        datasets: []
      };
    }
    
    const stopMeasuring = measureOperation('PrepareSystemMetricsChart');
    
    const { cpuUsage, memoryUsage } = systemMetricsData.systemMetrics;
    
    const timestamps = cpuUsage.map(point => format(new Date(point.timestamp), 'HH:mm'));
    
    const result = {
      labels: timestamps,
      datasets: [
        {
          label: t('dashboard.system.cpu'),
          data: cpuUsage.map(point => point.value),
          borderColor: 'rgb(255, 99, 132)',
          backgroundColor: 'rgba(255, 99, 132, 0.5)',
          tension: 0.1,
          yAxisID: 'y'
        },
        {
          label: t('dashboard.system.memory'),
          data: memoryUsage.map(point => point.value),
          borderColor: 'rgb(53, 162, 235)',
          backgroundColor: 'rgba(53, 162, 235, 0.5)',
          tension: 0.1,
          yAxisID: 'y'
        }
      ]
    };
    
    stopMeasuring();
    return result;
  }, [systemMetricsData, t, measureOperation]);
  
  // Prepare performance metrics chart data
  const performanceMetricsChartData = useDeepMemo<ChartData<'line'>>(() => {
    if (!systemMetricsData?.systemMetrics) {
      return {
        labels: [],
        datasets: []
      };
    }
    
    const stopMeasuring = measureOperation('PreparePerformanceMetricsChart');
    
    const { requestRate, responseTime } = systemMetricsData.systemMetrics;
    
    const timestamps = requestRate.map(point => format(new Date(point.timestamp), 'HH:mm'));
    
    const result = {
      labels: timestamps,
      datasets: [
        {
          label: t('dashboard.system.requests'),
          data: requestRate.map(point => point.value),
          borderColor: 'rgb(255, 205, 86)',
          backgroundColor: 'rgba(255, 205, 86, 0.5)',
          tension: 0.1,
          yAxisID: 'y'
        },
        {
          label: t('dashboard.system.responseTime'),
          data: responseTime.map(point => point.value),
          borderColor: 'rgb(153, 102, 255)',
          backgroundColor: 'rgba(153, 102, 255, 0.5)',
          tension: 0.1,
          yAxisID: 'y1'
        }
      ]
    };
    
    stopMeasuring();
    return result;
  }, [systemMetricsData, t, measureOperation]);
  
  // Performance metrics chart options
  const performanceMetricsOptions = useMemo(() => {
    return {
      scales: {
        y: {
          type: 'linear' as const,
          display: true,
          position: 'left' as const,
          title: {
            display: true,
            text: t('dashboard.system.requestsPerMinute')
          }
        },
        y1: {
          type: 'linear' as const,
          display: true,
          position: 'right' as const,
          title: {
            display: true,
            text: t('dashboard.system.responseTimeMs')
          },
          grid: {
            drawOnChartArea: false,
          },
        },
      },
    };
  }, [t]);
  
  // Handle period change
  const handlePeriodChange = (newPeriod: string) => {
    const stopMeasuring = measureOperation('PeriodChange');
    setPeriod(newPeriod);
    stopMeasuring();
  };
  
  // Get summary stats
  const summaryStats = useMemo(() => {
    if (!generalStats || !documentStatsData?.documentStats || !queryStatsData?.queryStats) {
      return {
        documents: 0,
        queries: 0,
        users: 0,
        tags: 0
      };
    }
    
    return {
      documents: documentStatsData.documentStats.totalDocuments,
      queries: queryStatsData.queryStats.totalQueries,
      users: generalStats.usersCount || 0,
      tags: documentStatsData.documentStats.topTags.length
    };
  }, [generalStats, documentStatsData, queryStatsData]);
  
  return (
    <div className="dashboard-page">
      <Container fluid>
        <h1 className="page-title mb-4">{t('dashboard.title')}</h1>
        
        {/* Summary Stats Cards */}
        <Row className="g-4 mb-4">
          <Col sm={6} md={3}>
            <StatCard 
              title={t('dashboard.summary.documents')}
              value={summaryStats.documents}
              icon={<FaFileAlt />}
              color="primary"
              isLoading={isDocumentStatsLoading}
            />
          </Col>
          <Col sm={6} md={3}>
            <StatCard 
              title={t('dashboard.summary.queries')}
              value={summaryStats.queries}
              icon={<FaSearch />}
              color="success"
              isLoading={isQueryStatsLoading}
            />
          </Col>
          <Col sm={6} md={3}>
            <StatCard 
              title={t('dashboard.summary.users')}
              value={summaryStats.users}
              icon={<FaUser />}
              color="info"
              isLoading={isStatsLoading}
            />
          </Col>
          <Col sm={6} md={3}>
            <StatCard 
              title={t('dashboard.summary.tags')}
              value={summaryStats.tags}
              icon={<FaTag />}
              color="warning"
              isLoading={isDocumentStatsLoading}
            />
          </Col>
        </Row>
        
        {/* Document Statistics */}
        <Row className="g-4 mb-4">
          <Col md={8}>
            <DataVisualization
              title={t('dashboard.documents.activityTitle')}
              data={documentChartData}
              isLoading={isDocumentStatsLoading}
              error={documentStatsError ? 'Failed to load document statistics' : null}
              onRetry={() => refetchDocumentStats()}
              onPeriodChange={handlePeriodChange}
              height={300}
            />
          </Col>
          <Col md={4}>
            <DataVisualization
              title={t('dashboard.documents.typesTitle')}
              data={documentTypesChartData}
              type="pie"
              isLoading={isDocumentStatsLoading}
              error={documentStatsError ? 'Failed to load document statistics' : null}
              onRetry={() => refetchDocumentStats()}
              onPeriodChange={handlePeriodChange}
              height={300}
            />
          </Col>
        </Row>
        
        {/* Query Statistics */}
        <Row className="g-4 mb-4">
          <Col md={8}>
            <DataVisualization
              title={t('dashboard.queries.activityTitle')}
              data={queryChartData}
              isLoading={isQueryStatsLoading}
              error={queryStatsError ? 'Failed to load query statistics' : null}
              onRetry={() => refetchQueryStats()}
              onPeriodChange={handlePeriodChange}
              height={300}
            />
          </Col>
          <Col md={4}>
            <DataVisualization
              title={t('dashboard.queries.typesTitle')}
              data={queryTypesChartData}
              type="doughnut"
              isLoading={isQueryStatsLoading}
              error={queryStatsError ? 'Failed to load query statistics' : null}
              onRetry={() => refetchQueryStats()}
              onPeriodChange={handlePeriodChange}
              height={300}
            />
          </Col>
        </Row>
        
        {/* System Metrics */}
        <Row className="g-4 mb-4">
          <Col md={6}>
            <DataVisualization
              title={t('dashboard.system.resourceUsageTitle')}
              data={systemMetricsChartData}
              isLoading={isSystemMetricsLoading}
              error={systemMetricsError ? 'Failed to load system metrics' : null}
              onRetry={() => refetchSystemMetrics()}
              onPeriodChange={handlePeriodChange}
              height={300}
            />
          </Col>
          <Col md={6}>
            <DataVisualization
              title={t('dashboard.system.performanceTitle')}
              data={performanceMetricsChartData}
              options={performanceMetricsOptions}
              isLoading={isSystemMetricsLoading}
              error={systemMetricsError ? 'Failed to load system metrics' : null}
              onRetry={() => refetchSystemMetrics()}
              onPeriodChange={handlePeriodChange}
              height={300}
            />
          </Col>
        </Row>
        
        {/* Recent Activity */}
        <Row className="g-4">
          <Col md={12}>
            <Card>
              <Card.Header className="d-flex align-items-center">
                <FaClock className="me-2" />
                <h5 className="mb-0">{t('dashboard.recentActivity.title')}</h5>
              </Card.Header>
              <Card.Body>
                <RecentActivityList 
                  isLoading={isStatsLoading || isQueryStatsLoading || isDocumentStatsLoading}
                  error={statsError ? 'Failed to load recent activity' : null}
                />
              </Card.Body>
            </Card>
          </Col>
        </Row>
      </Container>
    </div>
  );
};

export default Dashboard;