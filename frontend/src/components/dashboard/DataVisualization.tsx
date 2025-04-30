// Last reviewed: 2025-04-30 12:17:45 UTC (User: Teeksssdevam et.)
import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Card, Form, Row, Col, Alert } from 'react-bootstrap';
import { Line, Bar, Pie, Doughnut } from 'react-chartjs-2';
import { Chart, ChartOptions, ChartData, CategoryScale, LinearScale, PointElement, LineElement, Title, ArcElement, Tooltip, Legend, BarElement, Colors } from 'chart.js';
import { FaCalendarAlt, FaChartLine, FaChartPie, FaChartBar } from 'react-icons/fa';
import { useTranslation } from 'react-i18next';
import ContentLoader, { LoaderType } from '../common/ContentLoader';
import { useTheme } from '../../contexts/GlobalStateContext';
import { usePerformanceMonitoring } from '../../services/performanceService';

// Register Chart.js components
Chart.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend, ArcElement, Colors);

export type ChartType = 'line' | 'bar' | 'pie' | 'doughnut';

interface DataVisualizationProps {
  title: string;
  data?: ChartData<any>;
  options?: ChartOptions<any>;
  type?: ChartType;
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  onPeriodChange?: (period: string) => void;
  onTypeChange?: (type: ChartType) => void;
  className?: string;
  height?: number;
  showControls?: boolean;
}

const DataVisualization: React.FC<DataVisualizationProps> = ({
  title,
  data,
  options,
  type = 'line',
  isLoading = false,
  error = null,
  onRetry,
  onPeriodChange,
  onTypeChange,
  className = '',
  height = 300,
  showControls = true,
}) => {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const chartRef = useRef<any>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<string>('week');
  const [selectedType, setSelectedType] = useState<ChartType>(type);
  const { measureOperation } = usePerformanceMonitoring('DataVisualization');
  const [isResizing, setIsResizing] = useState(false);

  // Memoize chart options to include theme colors
  const chartOptions = useMemo(() => {
    const isDarkTheme = theme === 'dark';
    
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top' as const,
          labels: {
            color: isDarkTheme ? '#e9ecef' : '#212529',
          },
        },
        title: {
          display: false,
        },
        tooltip: {
          mode: 'index',
          intersect: false,
          backgroundColor: isDarkTheme ? '#343a40' : '#ffffff',
          titleColor: isDarkTheme ? '#e9ecef' : '#212529',
          bodyColor: isDarkTheme ? '#e9ecef' : '#212529',
          borderColor: isDarkTheme ? '#6c757d' : '#ced4da',
          borderWidth: 1,
        },
      },
      scales: type === 'line' || type === 'bar' ? {
        x: {
          grid: {
            color: isDarkTheme ? '#495057' : '#e9ecef',
          },
          ticks: {
            color: isDarkTheme ? '#e9ecef' : '#212529',
          },
        },
        y: {
          grid: {
            color: isDarkTheme ? '#495057' : '#e9ecef',
          },
          ticks: {
            color: isDarkTheme ? '#e9ecef' : '#212529',
          },
          beginAtZero: true,
        },
      } : undefined,
      ...options,
    };
  }, [options, theme, type]);

  // Handle period change
  const handlePeriodChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const stopMeasuring = measureOperation('PeriodChange');
    const newPeriod = e.target.value;
    setSelectedPeriod(newPeriod);
    if (onPeriodChange) {
      onPeriodChange(newPeriod);
    }
    stopMeasuring();
  };

  // Handle chart type change
  const handleTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const stopMeasuring = measureOperation('TypeChange');
    const newType = e.target.value as ChartType;
    setSelectedType(newType);
    if (onTypeChange) {
      onTypeChange(newType);
    }
    stopMeasuring();
  };

  // Handle window resize
  useEffect(() => {
    const handleResize = () => {
      setIsResizing(true);
      if (chartRef.current) {
        chartRef.current.resize();
      }
      // Debounce the resize flag
      setTimeout(() => setIsResizing(false), 300);
    };

    window.addEventListener('resize', handleResize);
    
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  // Render chart based on type
  const renderChart = () => {
    if (!data || isResizing) {
      return null;
    }

    switch (selectedType) {
      case 'line':
        return <Line ref={chartRef} data={data} options={chartOptions} />;
      case 'bar':
        return <Bar ref={chartRef} data={data} options={chartOptions} />;
      case 'pie':
        return <Pie ref={chartRef} data={data} options={chartOptions} />;
      case 'doughnut':
        return <Doughnut ref={chartRef} data={data} options={chartOptions} />;
      default:
        return <Line ref={chartRef} data={data} options={chartOptions} />;
    }
  };

  return (
    <Card className={`data-visualization ${className}`}>
      <Card.Header className="d-flex justify-content-between align-items-center">
        <div className="d-flex align-items-center">
          {selectedType === 'line' && <FaChartLine className="me-2" />}
          {selectedType === 'bar' && <FaChartBar className="me-2" />}
          {(selectedType === 'pie' || selectedType === 'doughnut') && <FaChartPie className="me-2" />}
          <h5 className="mb-0">{title}</h5>
        </div>
        
        {showControls && (
          <div className="d-flex chart-controls">
            <Form.Group className="me-2">
              <Form.Select 
                size="sm"
                value={selectedPeriod} 
                onChange={handlePeriodChange}
                aria-label={t('dashboard.periodSelector')}
              >
                <option value="day">{t('dashboard.periods.day')}</option>
                <option value="week">{t('dashboard.periods.week')}</option>
                <option value="month">{t('dashboard.periods.month')}</option>
                <option value="quarter">{t('dashboard.periods.quarter')}</option>
                <option value="year">{t('dashboard.periods.year')}</option>
              </Form.Select>
            </Form.Group>
            
            <Form.Group>
              <Form.Select 
                size="sm"
                value={selectedType} 
                onChange={handleTypeChange}
                aria-label={t('dashboard.chartTypeSelector')}
              >
                <option value="line">{t('dashboard.chartTypes.line')}</option>
                <option value="bar">{t('dashboard.chartTypes.bar')}</option>
                <option value="pie">{t('dashboard.chartTypes.pie')}</option>
                <option value="doughnut">{t('dashboard.chartTypes.doughnut')}</option>
              </Form.Select>
            </Form.Group>
          </div>
        )}
      </Card.Header>
      
      <Card.Body>
        <ContentLoader
          isLoading={isLoading}
          error={error}
          onRetry={onRetry}
          type={LoaderType.SKELETON}
        >
          <div style={{ height: `${height}px` }}>
            {data?.datasets?.length === 0 ? (
              <Alert variant="info" className="h-100 d-flex align-items-center justify-content-center">
                {t('dashboard.noDataAvailable')}
              </Alert>
            ) : (
              renderChart()
            )}
          </div>
        </ContentLoader>
      </Card.Body>
    </Card>
  );
};

export default React.memo(DataVisualization);