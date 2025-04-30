// Last reviewed: 2025-04-30 12:17:45 UTC (User: Teeksssdevam et.)
import React, { useState, useMemo } from 'react';
import { Container, Row, Col, Button, Card, Alert } from 'react-bootstrap';
import { useTranslation } from 'react-i18next';
import { FaFileUpload, FaFilter, FaSort } from 'react-icons/fa';
import { useDocuments, useDeleteDocument } from '../services/queryService';
import DocumentCard from '../components/document/DocumentCard';
import DocumentUploadModal from '../components/document/DocumentUploadModal';
import EnhancedSearchBar from '../components/search/EnhancedSearchBar';
import ContentLoader from '../components/common/ContentLoader';
import VirtualList from '../components/data/VirtualList';
import { usePerformanceMonitoring } from '../services/performanceService';

const Documents: React.FC = () => {
  const { t } = useTranslation();
  const [showUploadModal, setShowUploadModal] = useState<boolean>(false);
  const [filters, setFilters] = useState<Record<string, any>>({});
  const [sortField, setSortField] = useState<string>('createdAt');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  
  // Performance monitoring
  const { measureOperation } = usePerformanceMonitoring('DocumentsPage');
  
  // Fetch documents with React Query
  const {
    data: documents = [],
    isLoading,
    isError,
    error,
    refetch
  } = useDocuments({
    ...filters,
    sort: sortField,
    order: sortDirection
  });
  
  // Delete document mutation
  const { mutate: deleteDocument, isLoading: isDeleting } = useDeleteDocument();
  
  // Filter options for search bar
  const filterOptions = useMemo(() => [
    { field: 'type', label: t('documents.filters.type'), options: ['PDF', 'DOCX', 'TXT', 'MD', 'HTML'] },
    { field: 'owner', label: t('documents.filters.owner') },
    { field: 'tags', label: t('documents.filters.tags') },
    { field: 'createdAfter', label: t('documents.filters.createdAfter') },
    { field: 'createdBefore', label: t('documents.filters.createdBefore') }
  ], [t]);
  
  // Sort options for search bar
  const sortOptions = useMemo(() => [
    { field: 'createdAt', label: t('documents.sort.createdAt') },
    { field: 'updatedAt', label: t('documents.sort.updatedAt') },
    { field: 'title', label: t('documents.sort.title') },
    { field: 'size', label: t('documents.sort.size') }
  ], [t]);
  
  // Handle search
  const handleSearch = (query: any) => {
    const stopMeasuring = measureOperation('SearchOperation');
    
    const newFilters: Record<string, any> = {};
    
    // Add text search
    if (query.text) {
      newFilters.query = query.text;
    }
    
    // Add filters
    if (query.filters && query.filters.length > 0) {
      query.filters.forEach((filter: any) => {
        newFilters[filter.field] = filter.value;
      });
    }
    
    // Add sort
    if (query.sort) {
      setSortField(query.sort.field);
      setSortDirection(query.sort.direction);
    }
    
    setFilters(newFilters);
    stopMeasuring();
  };
  
  // Handle document deletion
  const handleDeleteDocument = (id: string) => {
    if (window.confirm(t('documents.deleteConfirmation'))) {
      deleteDocument(id);
    }
  };
  
  return (
    <div className="documents-page">
      <Container fluid>
        <Row className="mb-4 align-items-center">
          <Col>
            <h1 className="page-title">{t('documents.title')}</h1>
          </Col>
          <Col xs="auto">
            <Button 
              variant="primary" 
              onClick={() => setShowUploadModal(true)}
              className="d-flex align-items-center"
            >
              <FaFileUpload className="me-2" />
              {t('documents.uploadButton')}
            </Button>
          </Col>
        </Row>
        
        <Card className="mb-4">
          <Card.Body>
            <EnhancedSearchBar
              onSearch={handleSearch}
              placeholder={t('documents.searchPlaceholder')}
              availableFilters={filterOptions}
              initialFilters={[]}
              showSortOptions={true}
              sortOptions={sortOptions}
              isLoading={isLoading}
            />
          </Card.Body>
        </Card>
        
        <ContentLoader
          isLoading={isLoading}
          error={isError ? (error as Error)?.message : undefined}
          onRetry={refetch}
        >
          {documents.length > 0 ? (
            <VirtualList
              items={documents}
              itemHeight={250} // Card height estimation
              renderItem={(document) => (
                <DocumentCard
                  key={document.id}
                  document={document}
                  onDelete={() => handleDeleteDocument(document.id)}
                  isDeleting={isDeleting}
                  className="mb-4"
                />
              )}
              keyExtractor={(document) => document.id}
              className="document-list"
              endReachedThreshold={500}
            />
          ) : (
            <Alert variant="info" className="text-center py-5">
              {t('documents.noDocuments')}
            </Alert>
          )}
        </ContentLoader>
      </Container>
      
      <DocumentUploadModal
        show={showUploadModal}
        onHide={() => setShowUploadModal(false)}
        onSuccess={() => {
          setShowUploadModal(false);
          refetch();
        }}
      />
    </div>
  );
};

export default Documents;