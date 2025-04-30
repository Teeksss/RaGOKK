// Last reviewed: 2025-04-30 09:04:08 UTC (User: Teeksss)
import React, { useState, useEffect, useMemo } from 'react';
import { 
  Table, 
  Form, 
  InputGroup, 
  Button, 
  Dropdown, 
  Row, 
  Col, 
  Badge, 
  Card
} from 'react-bootstrap';
import { 
  FaSearch, 
  FaSort, 
  FaSortUp, 
  FaSortDown, 
  FaFilter, 
  FaDownload, 
  FaCog, 
  FaColumns, 
  FaChartBar
} from 'react-icons/fa';
import { useTranslation } from 'react-i18next';
import { CSVLink } from 'react-csv';
import ContentLoader, { LoaderType } from '../common/ContentLoader';

// Data types
type SortDirection = 'asc' | 'desc' | null;

interface ColumnConfig {
  key: string;
  label: string;
  type?: 'text' | 'number' | 'date' | 'boolean' | 'custom';
  sortable?: boolean;
  filterable?: boolean;
  width?: string;
  formatter?: (value: any, row: any) => React.ReactNode;
  visible?: boolean;
  className?: string;
  filterOptions?: string[] | number[];
}

interface TableState {
  page: number;
  pageSize: number;
  sortKey: string | null;
  sortDirection: SortDirection;
  filters: Record<string, any>;
  searchTerm: string;
  visibleColumns: string[];
}

interface EnhancedDataTableProps {
  data: any[];
  columns: ColumnConfig[];
  title?: string;
  isLoading?: boolean;
  error?: string | null;
  onRefresh?: () => void;
  defaultPageSize?: number;
  pageSizeOptions?: number[];
  rowsPerPageLabel?: string;
  searchPlaceholder?: string;
  emptyMessage?: string;
  defaultSort?: { key: string; direction: SortDirection };
  onRowClick?: (row: any) => void;
  className?: string;
  showToolbar?: boolean;
  showPagination?: boolean;
  showSearch?: boolean;
  showColumnToggle?: boolean;
  showExport?: boolean;
  exportFilename?: string;
  rowClassName?: (row: any) => string;
  heightLimit?: string;
}

const EnhancedDataTable: React.FC<EnhancedDataTableProps> = ({
  data,
  columns,
  title,
  isLoading = false,
  error = null,
  onRefresh,
  defaultPageSize = 10,
  pageSizeOptions = [5, 10, 25, 50, 100],
  rowsPerPageLabel,
  searchPlaceholder,
  emptyMessage,
  defaultSort,
  onRowClick,
  className = '',
  showToolbar = true,
  showPagination = true,
  showSearch = true,
  showColumnToggle = true,
  showExport = true,
  exportFilename = 'data-export',
  rowClassName,
  heightLimit
}) => {
  const { t } = useTranslation();
  
  // Initialize state
  const [tableState, setTableState] = useState<TableState>({
    page: 1,
    pageSize: defaultPageSize,
    sortKey: defaultSort?.key || null,
    sortDirection: defaultSort?.direction || null,
    filters: {},
    searchTerm: '',
    visibleColumns: columns.filter(col => col.visible !== false).map(col => col.key)
  });
  
  // Set initial column visibility
  const initialVisibleColumns = useMemo(() => {
    return columns.filter(col => col.visible !== false).map(col => col.key);
  }, [columns]);
  
  useEffect(() => {
    setTableState(prev => ({
      ...prev,
      visibleColumns: initialVisibleColumns
    }));
  }, [initialVisibleColumns]);
  
  // Derived state
  const filteredData = useMemo(() => {
    // Start with all data
    let result = [...data];
    
    // Apply search term
    if (tableState.searchTerm.trim() !== '') {
      const searchLower = tableState.searchTerm.toLowerCase();
      result = result.filter(row => {
        // Search across all visible columns
        return tableState.visibleColumns.some(colKey => {
          const column = columns.find(c => c.key === colKey);
          const value = row[colKey];
          
          // Skip null or undefined values
          if (value === null || value === undefined) return false;
          
          // Format value for search if formatter exists
          const formattedValue = column?.formatter
            ? column.formatter(value, row)
            : value;
          
          // Convert to string and check if it includes the search term
          const stringValue = 
            React.isValidElement(formattedValue)
              ? '' // Skip React elements for search
              : String(formattedValue).toLowerCase();
              
          return stringValue.includes(searchLower);
        });
      });
    }
    
    // Apply filters
    Object.entries(tableState.filters).forEach(([key, value]) => {
      if (value !== null && value !== undefined && value !== '') {
        result = result.filter(row => {
          const rowValue = row[key];
          
          // Handle different filter types based on column type
          const column = columns.find(c => c.key === key);
          switch (column?.type) {
            case 'number':
              return rowValue === Number(value);
            case 'boolean':
              return rowValue === (value === 'true');
            case 'date':
              // Simple date comparison (could be enhanced)
              return new Date(rowValue).toLocaleDateString() === new Date(value).toLocaleDateString();
            default:
              // Default string contains
              return String(rowValue).toLowerCase().includes(String(value).toLowerCase());
          }
        });
      }
    });
    
    // Apply sorting
    if (tableState.sortKey) {
      const sortKey = tableState.sortKey;
      const sortDirection = tableState.sortDirection;
      
      result.sort((a, b) => {
        let aValue = a[sortKey];
        let bValue = b[sortKey];
        
        // Handle different data types
        const column = columns.find(col => col.key === sortKey);
        switch (column?.type) {
          case 'number':
            aValue = Number(aValue);
            bValue = Number(bValue);
            break;
          case 'date':
            aValue = new Date(aValue).getTime();
            bValue = new Date(bValue).getTime();
            break;
          default:
            // Convert to string for default comparison
            aValue = String(aValue || '').toLowerCase();
            bValue = String(bValue || '').toLowerCase();
        }
        
        // Compare based on direction
        if (sortDirection === 'asc') {
          return aValue > bValue ? 1 : aValue < bValue ? -1 : 0;
        } else {
          return aValue < bValue ? 1 : aValue > bValue ? -1 : 0;
        }
      });
    }
    
    return result;
  }, [data, tableState, columns]);
  
  // Pagination
  const paginatedData = useMemo(() => {
    if (!showPagination) return filteredData;
    
    const start = (tableState.page - 1) * tableState.pageSize;
    return filteredData.slice(start, start + tableState.pageSize);
  }, [filteredData, tableState.page, tableState.pageSize, showPagination]);
  
  // Total pages
  const totalPages = useMemo(() => {
    return Math.ceil(filteredData.length / tableState.pageSize);
  }, [filteredData.length, tableState.pageSize]);
  
  // Handle page change
  const handlePageChange = (newPage: number) => {
    setTableState(prev => ({
      ...prev,
      page: newPage
    }));
  };
  
  // Handle page size change
  const handlePageSizeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newSize = Number(e.target.value);
    setTableState(prev => ({
      ...prev,
      pageSize: newSize,
      page: 1 // Reset to first page when changing page size
    }));
  };
  
  // Handle sorting
  const handleSort = (key: string) => {
    setTableState(prev => {
      // If sorting by a different column, start with ascending
      if (prev.sortKey !== key) {
        return {
          ...prev,
          sortKey: key,
          sortDirection: 'asc'
        };
      }
      
      // Toggle direction or clear if already sorted desc
      const nextDirection: SortDirection = 
        prev.sortDirection === 'asc' ? 'desc' : 
        prev.sortDirection === 'desc' ? null : 'asc';
        
      return {
        ...prev,
        sortKey: nextDirection === null ? null : key,
        sortDirection: nextDirection
      };
    });
  };
  
  // Handle search
  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    const searchTerm = e.target.value;
    setTableState(prev => ({
      ...prev,
      searchTerm,
      page: 1 // Reset to first page when searching
    }));
  };
  
  // Handle filter change
  const handleFilterChange = (key: string, value: any) => {
    setTableState(prev => ({
      ...prev,
      filters: {
        ...prev.filters,
        [key]: value
      },
      page: 1 // Reset to first page when filtering
    }));
  };
  
  // Handle column visibility toggle
  const handleColumnToggle = (columnKey: string) => {
    setTableState(prev => {
      const isCurrentlyVisible = prev.visibleColumns.includes(columnKey);
      
      if (isCurrentlyVisible) {
        // Don't allow hiding all columns
        if (prev.visibleColumns.length === 1) {
          return prev;
        }
        
        // Hide column
        return {
          ...prev,
          visibleColumns: prev.visibleColumns.filter(key => key !== columnKey)
        };
      } else {
        // Show column
        return {
          ...prev,
          visibleColumns: [...prev.visibleColumns, columnKey]
        };
      }
    });
  };
  
  // Clear filters
  const handleClearFilters = () => {
    setTableState(prev => ({
      ...prev,
      filters: {},
      searchTerm: '',
      page: 1
    }));
  };
  
  // Reset all (filters, sorting, pagination)
  const handleResetAll = () => {
    setTableState({
      page: 1,
      pageSize: defaultPageSize,
      sortKey: defaultSort?.key || null,
      sortDirection: defaultSort?.direction || null,
      filters: {},
      searchTerm: '',
      visibleColumns: initialVisibleColumns
    });
    
    if (onRefresh) {
      onRefresh();
    }
  };
  
  // Prepare data for export
  const exportData = useMemo(() => {
    return filteredData.map(row => {
      const exportRow: Record<string, any> = {};
      
      // Only include visible columns
      tableState.visibleColumns.forEach(colKey => {
        const column = columns.find(c => c.key === colKey);
        if (column) {
          // For custom formatted columns, we need to use the raw value
          exportRow[column.label] = row[colKey];
        }
      });
      
      return exportRow;
    });
  }, [filteredData, tableState.visibleColumns, columns]);
  
  // Render sort icon
  const renderSortIcon = (columnKey: string) => {
    if (tableState.sortKey !== columnKey) {
      return <FaSort className="sort-icon" />;
    }
    
    return tableState.sortDirection === 'asc' ? (
      <FaSortUp className="sort-icon active" />
    ) : (
      <FaSortDown className="sort-icon active" />
    );
  };
  
  // Render filter badge
  const renderFilterBadge = () => {
    const filterCount = Object.values(tableState.filters).filter(
      value => value !== null && value !== undefined && value !== ''
    ).length;
    
    if (filterCount > 0) {
      return (
        <Badge bg="primary" className="ms-2">
          {filterCount}
        </Badge>
      );
    }
    
    return null;
  };
  
  return (
    <div className={`enhanced-data-table ${className}`}>
      {/* Table title and toolbar */}
      {(title || showToolbar) && (
        <div className="table-header mb-3">
          {title && <h5 className="table-title">{title}</h5>}
          
          {showToolbar && (
            <div className="table-toolbar">
              {/* Search bar */}
              {showSearch && (
                <div className="table-search">
                  <InputGroup>
                    <InputGroup.Text>
                      <FaSearch />
                    </InputGroup.Text>
                    <Form.Control
                      type="text"
                      placeholder={searchPlaceholder || t('dataTable.search')}
                      value={tableState.searchTerm}
                      onChange={handleSearch}
                    />
                  </InputGroup>
                </div>
              )}
              
              {/* Filters dropdown */}
              <Dropdown>
                <Dropdown.Toggle variant="outline-secondary">
                  <FaFilter className="me-1" />
                  {t('dataTable.filter')}
                  {renderFilterBadge()}
                </Dropdown.Toggle>
                
                <Dropdown.Menu className="filter-dropdown">
                  {columns
                    .filter(col => col.filterable !== false)
                    .map(column => (
                      <div key={`filter-${column.key}`} className="px-3 py-2">
                        <Form.Group>
                          <Form.Label>{column.label}</Form.Label>
                          
                          {/* Render different filter inputs based on column type */}
                          {column.filterOptions ? (
                            // Select dropdown for predefined options
                            <Form.Select
                              size="sm"
                              value={tableState.filters[column.key] || ''}
                              onChange={(e) => handleFilterChange(column.key, e.target.value)}
                            >
                              <option value="">{t('dataTable.all')}</option>
                              {column.filterOptions.map((option, idx) => (
                                <option key={idx} value={option}>
                                  {option}
                                </option>
                              ))}
                            </Form.Select>
                          ) : column.type === 'boolean' ? (
                            // Boolean filter
                            <Form.Select
                              size="sm"
                              value={tableState.filters[column.key] || ''}
                              onChange={(e) => handleFilterChange(column.key, e.target.value)}
                            >
                              <option value="">{t('dataTable.all')}</option>
                              <option value="true">{t('common.yes')}</option>
                              <option value="false">{t('common.no')}</option>
                            </Form.Select>
                          ) : column.type === 'date' ? (
                            // Date filter
                            <Form.Control
                              type="date"
                              size="sm"
                              value={tableState.filters[column.key] || ''}
                              onChange={(e) => handleFilterChange(column.key, e.target.value)}
                            />
                          ) : column.type === 'number' ? (
                            // Number filter (could be enhanced with range)
                            <Form.Control
                              type="number"
                              size="sm"
                              value={tableState.filters[column.key] || ''}
                              onChange={(e) => handleFilterChange(column.key, e.target.value)}
                            />
                          ) : (
                            // Text filter
                            <Form.Control
                              type="text"
                              size="sm"
                              value={tableState.filters[column.key] || ''}
                              onChange={(e) => handleFilterChange(column.key, e.target.value)}
                            />
                          )}
                        </Form.Group>
                      </div>
                    ))}
                  
                  <Dropdown.Divider />
                  
                  <div className="px-3 py-2 d-flex justify-content-end">
                    <Button 
                      size="sm" 
                      variant="outline-secondary" 
                      onClick={handleClearFilters}
                    >
                      {t('dataTable.clearFilters')}
                    </Button>
                  </div>
                </Dropdown.Menu>
              </Dropdown>
              
              {/* Column visibility toggle */}
              {showColumnToggle && (
                <Dropdown>
                  <Dropdown.Toggle variant="outline-secondary">
                    <FaColumns className="me-1" />
                    {t('dataTable.columns')}
                  </Dropdown.Toggle>
                  
                  <Dropdown.Menu>
                    {columns.map(column => (
                      <Dropdown.Item 
                        key={`col-toggle-${column.key}`}
                        onClick={() => handleColumnToggle(column.key)}
                      >
                        <Form.Check
                          type="checkbox"
                          label={column.label}
                          checked={tableState.visibleColumns.includes(column.key)}
                          onChange={() => {}} // Handled by parent click
                        />
                      </Dropdown.Item>
                    ))}
                  </Dropdown.Menu>
                </Dropdown>
              )}
              
              {/* CSV Export */}
              {showExport && (
                <CSVLink 
                  data={exportData} 
                  filename={`${exportFilename}.csv`}
                  className="btn btn-outline-secondary"
                >
                  <FaDownload className="me-1" />
                  {t('dataTable.export')}
                </CSVLink>
              )}
              
              {/* Settings dropdown */}
              <Dropdown>
                <Dropdown.Toggle variant="outline-secondary">
                  <FaCog />
                </Dropdown.Toggle>
                
                <Dropdown.Menu>
                  {/* Analytics option */}
                  <Dropdown.Item>
                    <FaChartBar className="me-2" />
                    {t('dataTable.analytics')}
                  </Dropdown.Item>
                  
                  <Dropdown.Divider />
                  
                  {/* Reset option */}
                  <Dropdown.Item onClick={handleResetAll}>
                    {t('dataTable.resetAll')}
                  </Dropdown.Item>
                </Dropdown.Menu>
              </Dropdown>
            </div>
          )}
        </div>
      )}
      
      {/* Table content */}
      <div className="table-container" style={heightLimit ? { maxHeight: heightLimit, overflow: 'auto' } : {}}>
        <ContentLoader
          isLoading={isLoading}
          error={error}
          type={LoaderType.SPINNER}
          onRetry={onRefresh}
        >
          <Table striped hover responsive className="mb-0">
            <thead>
              <tr>
                {columns
                  .filter(col => tableState.visibleColumns.includes(col.key))
                  .map(column => (
                    <th 
                      key={column.key} 
                      style={{ width: column.width }}
                      className={column.className}
                    >
                      {column.sortable !== false ? (
                        <div 
                          className="sortable-header" 
                          onClick={() => handleSort(column.key)}
                        >
                          {column.label}
                          <span className="sort-icon-container">
                            {renderSortIcon(column.key)}
                          </span>
                        </div>
                      ) : (
                        column.label
                      )}
                    </th>
                  ))}
              </tr>
            </thead>
            <tbody>
              {paginatedData.length > 0 ? (
                paginatedData.map((row, rowIndex) => (
                  <tr 
                    key={`row-${rowIndex}`} 
                    onClick={() => onRowClick && onRowClick(row)}
                    className={`${onRowClick ? 'clickable-row' : ''} ${rowClassName ? rowClassName(row) : ''}`}
                  >
                    {columns
                      .filter(col => tableState.visibleColumns.includes(col.key))
                      .map(column => (
                        <td key={`cell-${rowIndex}-${column.key}`} className={column.className}>
                          {column.formatter ? 
                            column.formatter(row[column.key], row) : 
                            row[column.key]}
                        </td>
                      ))}
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={tableState.visibleColumns.length} className="text-center py-4">
                    {emptyMessage || t('dataTable.noData')}
                  </td>
                </tr>
              )}
            </tbody>
          </Table>
        </ContentLoader>
      </div>
      
      {/* Pagination */}
      {showPagination && filteredData.length > 0 && (
        <div className="table-footer mt-3">
          <div className="pagination-info">
            {t('dataTable.showing')} {(tableState.page - 1) * tableState.pageSize + 1} - {Math.min(tableState.page * tableState.pageSize, filteredData.length)} {t('dataTable.of')} {filteredData.length} {t('dataTable.entries')}
          </div>
          
          <div className="pagination-controls d-flex align-items-center">
            {/* Page size select */}
            <div className="page-size-control me-3">
              <Form.Select
                size="sm"
                value={tableState.pageSize}
                onChange={handlePageSizeChange}
                aria-label={rowsPerPageLabel || t('dataTable.rowsPerPage')}
              >
                {pageSizeOptions.map(size => (
                  <option key={size} value={size}>
                    {size}
                  </option>
                ))}
              </Form.Select>
              <span className="ms-2 text-muted">{rowsPerPageLabel || t('dataTable.rowsPerPage')}</span>
            </div>
            
            {/* Page navigation */}
            <div className="pagination-nav">
              <Button
                variant="outline-secondary"
                size="sm"
                onClick={() => handlePageChange(1)}
                disabled={tableState.page === 1}
              >
                &laquo;
              </Button>
              
              <Button
                variant="outline-secondary"
                size="sm"
                onClick={() => handlePageChange(tableState.page - 1)}
                disabled={tableState.page === 1}
              >
                &lsaquo;
              </Button>
              
              <span className="mx-3">
                {t('dataTable.page')} {tableState.page} {t('dataTable.of')} {totalPages}
              </span>
              
              <Button
                variant="outline-secondary"
                size="sm"
                onClick={() => handlePageChange(tableState.page + 1)}
                disabled={tableState.page === totalPages}
              >
                &rsaquo;
              </Button>
              
              <Button
                variant="outline-secondary"
                size="sm"
                onClick={() => handlePageChange(totalPages)}
                disabled={tableState.page === totalPages}
              >
                &raquo;
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default EnhancedDataTable;