// Last reviewed: 2025-04-30 08:53:57 UTC (User: Teeksss)
import React, { useState } from 'react';
import { Card, Dropdown, Nav, Button } from 'react-bootstrap';
import { 
  Chart as ChartJS, 
  CategoryScale, 
  LinearScale, 
  PointElement, 
  LineElement, 
  BarElement,
  ArcElement,
  Title, 
  Tooltip, 
  Legend,
  ChartData,
  ChartOptions
} from 'chart.js';
import { Line, Bar, Pie, Doughnut } from 'react-chartjs-2';
import { FaDownload, FaCog, FaRedoAlt } from 'react-icons/fa';
import { useTranslation } from 'react-i18next';
import ContentLoader, { LoaderType } from '../common/ContentLoader';

// Register ChartJS components
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

// Chart types
export enum ChartType {
  LINE = 'line',
  BAR = 'bar',
  PIE = 'pie',
  DOUGHNUT = 'doughnut'
}

// Chart period
export enum ChartPeriod {
  DAY = 'day',
  WEEK = 'week',
  MONTH = 'month',
  QUARTER = 'quarter',
  YEAR = 'year',
  ALL = 'all'
}

// Props interface
interface EnhancedChartsProps {
  data: any;
  type?: ChartType;
  title?: string;
  subtitle?: string;
  showLegend?: boolean;
  isLoading?: boolean;
  error?: string | null;
  height?: number;
  options?: ChartOptions<any>;
  availableTypes?: ChartType[];
  availablePeriods?: ChartPeriod[];
  defaultPeriod?: ChartPeriod;
  onPeriodChange?: (period: ChartPeriod) => void;
  onTypeChange?: (type: ChartType) => void;
  onRefresh?: () => void;
  className?: string;
  tooltipFormat?: string;
  transformData?: (data: any, type: ChartType, period: ChartPeriod) => ChartData<any>;
}

// Default chart themes/colors
const chartColors = [
  'rgba(54, 162, 235, 0.8)', // Blue
  'rgba(255, 99, 132, 0.8)',  // Red
  'rgba(75, 192, 192, 0.8)',  // Green
  'rgba(255, 159, 64, 0.8)',  // Orange
  'rgba(153, 102, 255, 0.8)', // Purple
  'rgba(255, 205, 86, 0.8)',  // Yellow
  'rgba(201, 203, 207, 0.8)', // Grey
  'rgba(100, 181, 246, 0.8)', // Light Blue
  'rgba(255, 138, 101, 0.8)', // Deep Orange
  'rgba(156, 204, 101, 0.8)'  // Lime
];

// Border colors (darker versions)
const borderColors = chartColors.map(color => color.replace('0.8', '1'));

const EnhancedCharts: React.FC<EnhancedChartsProps> = ({
  data,
  type = ChartType.LINE,
  title,
  subtitle,
  showLegend = true,
  isLoading = false,
  error = null,
  height = 300,
  options = {},
  availableTypes = [ChartType.LINE, ChartType.BAR],
  availablePeriods = [
    ChartPeriod.DAY, 
    ChartPeriod.WEEK, 
    ChartPeriod.MONTH, 
    ChartPeriod.YEAR
  ],
  defaultPeriod = ChartPeriod.MONTH,
  onPeriodChange,
  onTypeChange,
  onRefresh,
  className = '',
  tooltipFormat,
  transformData
}) => {
  const { t } = useTranslation();
  
  // State
  const [chartType, setChartType] = useState<ChartType>(type);
  const [period, setPeriod] = useState<ChartPeriod>(defaultPeriod);
  
  // Handle period change
  const handlePeriodChange = (newPeriod: ChartPeriod) => {
    setPeriod(newPeriod);
    if (onPeriodChange) {
      onPeriodChange(newPeriod);
    }
  };
  
  // Handle chart type change
  const handleTypeChange = (newType: ChartType) => {
    setChartType(newType);
    if (onTypeChange) {
      onTypeChange(newType);
    }
  };
  
  // Download chart as image
  const handleDownloadImage = () => {
    const canvas = document.querySelector('.chart-container canvas') as HTMLCanvasElement;
    if (!canvas) return;
    
    // Create download link
    const link = document.createElement('a');
    link.download = `${title || 'chart'}-${new Date().toISOString().slice(0, 10)}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  };
  
  // Transform data for charts
  const chartData = transformData ? transformData(data, chartType, period) : data;
  
  // Default options by chart type
  const getDefaultOptions = () => {
    const baseOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: showLegend,
          position: 'top' as const
        },
        title: {
          display: !!title,
          text: title
        },
        subtitle: {
          display: !!subtitle,
          text: subtitle,
          padding: {
            bottom: 10
          }
        },
        tooltip: {
          callbacks: {}
        }
      }
    };
    
    // Add specific options based on chart type
    if (chartType === ChartType.LINE || chartType === ChartType.BAR) {
      return {
        ...baseOptions,
        scales: {
          y: {
            beginAtZero: true
          }
        }
      };
    }
    
    return baseOptions;
  };
  
  // Merge default with custom options
  const mergedOptions = {
    ...getDefaultOptions(),
    ...options
  };
  
  // Render chart based on type
  const renderChart = () => {
    switch (chartType) {
      case ChartType.BAR:
        return <Bar data={chartData} options={mergedOptions} />;
      case ChartType.PIE:
        return <Pie data={chartData} options={mergedOptions} />;
      case ChartType.DOUGHNUT:
        return <Doughnut data={chartData} options={mergedOptions} />;
      case ChartType.LINE:
      default:
        return <Line data={chartData} options={mergedOptions} />;
    }
  };
  
  // Translate period for display
  const getPeriodLabel = (p: ChartPeriod) => {
    return t(`charts.periods.${p}`);
  };
  
  // Translate chart type for display
  const getChartTypeLabel = (ct: ChartType) => {
    return t(`charts.types.${ct}`);
  };
  
  return (
    <Card className={`enhanced-chart ${className}`}>
      <Card.Header className="d-flex justify-content-between align-items-center">
        <div className="chart-title-area">
          {title && <h5 className="chart-title mb-0">{title}</h5>}
          {subtitle && <div className="chart-subtitle text-muted small">{subtitle}</div>}
        </div>
        
        <div className="chart-controls d-flex">
          {/* Period selector */}
          {availablePeriods.length > 1 && (
            <Nav variant="pills" className="period-selector me-2">
              {availablePeriods.map(p => (
                <Nav.Item key={p}>
                  <Nav.Link 
                    active={period === p}
                    onClick={() => handlePeriodChange(p)}
                  >
                    {getPeriodLabel(p)}
                  </Nav.Link>
                </Nav.Item>
              ))}
            </Nav>
          )}
          
          {/* Chart type selector */}
          {availableTypes.length > 1 && (
            <Dropdown className="me-2">
              <Dropdown.Toggle variant="outline-secondary" size="sm">
                {getChartTypeLabel(chartType)}
              </Dropdown.Toggle>
              
              <Dropdown.Menu>
                {availableTypes.map(ct => (
                  <Dropdown.Item 
                    key={ct} 
                    onClick={() => handleTypeChange(ct)}
                    active={chartType === ct}
                  >
                    {getChartTypeLabel(ct)}
                  </Dropdown.Item>
                ))}
              </Dropdown.Menu>
            </Dropdown>
          )}
          
          {/* Actions dropdown */}
          <Dropdown>
            <Dropdown.Toggle variant="outline-secondary" size="sm">
              <FaCog />
            </Dropdown.Toggle>
            
            <Dropdown.Menu>
              <Dropdown.Item onClick={handleDownloadImage}>
                <FaDownload className="me-2" />
                {t('charts.downloadImage')}
              </Dropdown.Item>
              
              {onRefresh && (
                <Dropdown.Item onClick={onRefresh}>
                  <FaRedoAlt className="me-2" />
                  {t('charts.refresh')}
                </Dropdown.Item>
              )}
            </Dropdown.Menu>
          </Dropdown>
        </div>
      </Card.Header>
      
      <Card.Body>
        <ContentLoader 
          isLoading={isLoading} 
          error={error}
          type={LoaderType.SPINNER}
          onRetry={onRefresh}
        >
          <div className="chart-container" style={{ height: `${height}px` }}>
            {renderChart()}
          </div>
        </ContentLoader>
      </Card.Body>
    </Card>
  );
};

export default EnhancedCharts;