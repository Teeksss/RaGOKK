// Last reviewed: 2025-04-30 07:59:11 UTC (User: Teeksss)
import React, { useState, useEffect, useRef } from 'react';
import { Button, Tabs, Tab, Spinner, Alert, Card, Dropdown } from 'react-bootstrap';
import { FaDownload, FaExpand, FaCompress, FaSearchPlus, FaSearchMinus, FaPrint, FaFilePdf, FaRegFileImage, FaRegFileAlt, FaHistory } from 'react-icons/fa';
import { useTranslation } from 'react-i18next';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';

// PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.js`;

interface DocumentViewerProps {
  documentUrl: string;
  fileName: string;
  fileType: string;
  documentId: string;
  onShowVersions?: () => void;
}

const DocumentViewer: React.FC<DocumentViewerProps> = ({
  documentUrl,
  fileName,
  fileType,
  documentId,
  onShowVersions
}) => {
  const { t } = useTranslation();
  
  // State
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [scale, setScale] = useState<number>(1.0);
  const [activeTab, setActiveTab] = useState<string>('document');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  
  // Refs
  const viewerRef = useRef<HTMLDivElement>(null);
  
  // Determine content type
  const isImage = fileType === 'jpg' || fileType === 'jpeg' || fileType === 'png' || fileType === 'gif';
  const isPdf = fileType === 'pdf';
  const isText = !isImage && !isPdf;
  
  // Handle document load success
  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setLoading(false);
  };
  
  // Handle document load error
  const onDocumentLoadError = (error: Error) => {
    console.error('Error loading document:', error);
    setError(t('document.viewer.loadError'));
    setLoading(false);
  };
  
  // Handle fullscreen toggle
  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      if (viewerRef.current?.requestFullscreen) {
        viewerRef.current.requestFullscreen().catch(err => {
          console.error(`Error attempting to enable fullscreen: ${err.message}`);
        });
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      }
    }
  };
  
  // Listen to fullscreen changes
  useEffect(() => {
    const onFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    
    document.addEventListener('fullscreenchange', onFullscreenChange);
    
    return () => {
      document.removeEventListener('fullscreenchange', onFullscreenChange);
    };
  }, []);
  
  // Zoom in/out handlers
  const zoomIn = () => {
    setScale(prevScale => Math.min(prevScale + 0.2, 3));
  };
  
  const zoomOut = () => {
    setScale(prevScale => Math.max(prevScale - 0.2, 0.5));
  };
  
  // Page navigation handlers
  const goToPreviousPage = () => {
    setPageNumber(prevPage => Math.max(prevPage - 1, 1));
  };
  
  const goToNextPage = () => {
    if (numPages) {
      setPageNumber(prevPage => Math.min(prevPage + 1, numPages));
    }
  };
  
  // Handle print
  const handlePrint = () => {
    const printWindow = window.open(documentUrl);
    if (printWindow) {
      printWindow.onload = () => {
        printWindow.print();
      };
    }
  };
  
  // Render functions for different file types
  const renderPdfViewer = () => (
    <div className="pdf-viewer">
      {loading && (
        <div className="text-center py-5">
          <Spinner animation="border" />
          <p className="mt-3">{t('document.viewer.loading')}</p>
        </div>
      )}
      
      {error && (
        <Alert variant="danger" className="my-3">
          {error}
        </Alert>
      )}
      
      <Document
        file={documentUrl}
        onLoadSuccess={onDocumentLoadSuccess}
        onLoadError={onDocumentLoadError}
        loading={<Spinner animation="border" />}
      >
        <Page 
          pageNumber={pageNumber} 
          scale={scale}
          renderTextLayer={true}
          renderAnnotationLayer={true}
        />
      </Document>
      
      {numPages && (
        <div className="pdf-navigation mt-3">
          <div className="d-flex justify-content-between align-items-center">
            <Button 
              variant="outline-secondary" 
              onClick={goToPreviousPage} 
              disabled={pageNumber <= 1}
            >
              {t('document.viewer.previousPage')}
            </Button>
            
            <div className="page-info">
              {t('document.viewer.pageInfo', { current: pageNumber, total: numPages })}
            </div>
            
            <Button 
              variant="outline-secondary" 
              onClick={goToNextPage} 
              disabled={pageNumber >= numPages}
            >
              {t('document.viewer.nextPage')}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
  
  const renderImageViewer = () => (
    <div className="image-viewer text-center">
      {loading && <Spinner animation="border" />}
      
      <img 
        src={documentUrl} 
        alt={fileName} 
        style={{ maxWidth: '100%', transform: `scale(${scale})`, transformOrigin: 'top center' }}
        onLoad={() => setLoading(false)}
        onError={() => {
          setError(t('document.viewer.imageLoadError'));
          setLoading(false);
        }}
      />
    </div>
  );
  
  const renderTextViewer = () => (
    <div className="text-viewer">
      <iframe 
        src={documentUrl} 
        title={fileName}
        style={{ width: '100%', height: '600px', border: '1px solid #dee2e6' }}
        onLoad={() => setLoading(false)}
        onError={() => {
          setError(t('document.viewer.textLoadError'));
          setLoading(false);
        }}
      />
    </div>
  );
  
  return (
    <div className="document-viewer" ref={viewerRef}>
      <Card>
        <Card.Header>
          <div className="d-flex justify-content-between align-items-center">
            <div className="document-info">
              <h5 className="mb-0">
                {isPdf && <FaFilePdf className="me-2" />}
                {isImage && <FaRegFileImage className="me-2" />}
                {isText && <FaRegFileAlt className="me-2" />}
                {fileName}
              </h5>
            </div>
            
            <div className="viewer-actions">
              <Button
                variant="outline-secondary"
                size="sm"
                className="me-2"
                onClick={zoomOut}
                title={t('document.viewer.zoomOut')}
              >
                <FaSearchMinus />
              </Button>
              
              <Button
                variant="outline-secondary"
                size="sm"
                className="me-2"
                onClick={zoomIn}
                title={t('document.viewer.zoomIn')}
              >
                <FaSearchPlus />
              </Button>
              
              <Button
                variant="outline-secondary"
                size="sm"
                className="me-2"
                onClick={toggleFullscreen}
                title={t('document.viewer.fullscreen')}
              >
                {isFullscreen ? <FaCompress /> : <FaExpand />}
              </Button>
              
              <Dropdown className="d-inline">
                <Dropdown.Toggle variant="outline-secondary" size="sm" id="document-actions">
                  {t('document.viewer.actions')}
                </Dropdown.Toggle>
                
                <Dropdown.Menu>
                  <Dropdown.Item href={documentUrl} download={fileName}>
                    <FaDownload className="me-2" />
                    {t('document.viewer.download')}
                  </Dropdown.Item>
                  
                  <Dropdown.Item onClick={handlePrint}>
                    <FaPrint className="me-2" />
                    {t('document.viewer.print')}
                  </Dropdown.Item>
                  
                  {onShowVersions && (
                    <Dropdown.Item onClick={onShowVersions}>
                      <FaHistory className="me-2" />
                      {t('document.viewer.versions')}
                    </Dropdown.Item>
                  )}
                </Dropdown.Menu>
              </Dropdown>
            </div>
          </div>
        </Card.Header>
        
        <Card.Body className="p-2">
          <Tabs
            activeKey={activeTab}
            onSelect={(k) => k && setActiveTab(k)}
            className="mb-3"
          >
            <Tab eventKey="document" title={t('document.viewer.document')}>
              <div className="document-content p-2">
                {isPdf && renderPdfViewer()}
                {isImage && renderImageViewer()}
                {isText && renderTextViewer()}
              </div>
            </Tab>
          </Tabs>
        </Card.Body>
      </Card>
    </div>
  );
};

export default DocumentViewer;