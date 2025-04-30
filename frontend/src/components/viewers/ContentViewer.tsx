// Last reviewed: 2025-04-30 09:17:40 UTC (User: Teeksss)
import React, { useState, useEffect } from 'react';
import { Card, Nav, Button, Spinner, Modal } from 'react-bootstrap';
import { 
  FaExpand, FaCompress, FaDownload, FaShare, 
  FaChevronLeft, FaChevronRight, FaSearchPlus, FaSearchMinus,
  FaFileAlt, FaFileImage, FaFilePdf, FaFileExcel, FaFilePowerpoint,
  FaFileWord, FaFileCode, FaFileArchive, FaFileVideo, FaFileAudio
} from 'react-icons/fa';
import { useTranslation } from 'react-i18next';
import { Document, Page } from 'react-pdf';

// PDF.js worker yüklemesi
import { pdfjs } from 'react-pdf';
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.js`;

// Görüntüleme modları
export enum ViewMode {
  TEXT = 'text',
  IMAGE = 'image', 
  PDF = 'pdf',
  CODE = 'code',
  AUDIO = 'audio',
  VIDEO = 'video',
  JSON = 'json',
  CSV = 'csv'
}

// Props tanımı
interface ContentViewerProps {
  url: string;
  title?: string;
  mode: ViewMode;
  height?: string;
  showToolbar?: boolean;
  allowFullscreen?: boolean;
  allowDownload?: boolean;
  allowShare?: boolean;
  allowZoom?: boolean;
  initialZoom?: number;
  onLoad?: () => void;
  onError?: (error: Error) => void;
  className?: string;
  style?: React.CSSProperties;
  highlightText?: string;
  syntaxHighlight?: boolean;
  codeLanguage?: string;
  thumbnail?: string;
}

const ContentViewer: React.FC<ContentViewerProps> = ({
  url,
  title,
  mode,
  height = '500px',
  showToolbar = true,
  allowFullscreen = true,
  allowDownload = true,
  allowShare = true,
  allowZoom = true,
  initialZoom = 1,
  onLoad,
  onError,
  className = '',
  style = {},
  highlightText = '',
  syntaxHighlight = true,
  codeLanguage,
  thumbnail
}) => {
  const { t } = useTranslation();
  
  // Durum değişkenleri
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [fullscreen, setFullscreen] = useState<boolean>(false);
  const [zoom, setZoom] = useState<number>(initialZoom);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [numPages, setNumPages] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<string>('content');
  const [jsonData, setJsonData] = useState<any>(null);
  const [csvData, setCsvData] = useState<string[][]>([]);
  
  // Yükleme durumu
  useEffect(() => {
    setLoading(true);
    setError(null);
    
    const loadContent = async () => {
      try {
        // JSON ve CSV için özel işleme
        if (mode === ViewMode.JSON) {
          const response = await fetch(url);
          const data = await response.json();
          setJsonData(data);
        } else if (mode === ViewMode.CSV) {
          const response = await fetch(url);
          const text = await response.text();
          const rows = text.split('\n').map(row => row.split(','));
          setCsvData(rows);
        }
        
        setLoading(false);
        if (onLoad) onLoad();
      } catch (err: any) {
        setLoading(false);
        setError(err.message || 'Error loading content');
        if (onError) onError(err);
      }
    };
    
    if (mode === ViewMode.JSON || mode === ViewMode.CSV) {
      loadContent();
    }
  }, [url, mode, onLoad, onError]);
  
  // Tam ekran değişimi
  useEffect(() => {
    const handleFullscreenChange = () => {
      setFullscreen(!!document.fullscreenElement);
    };
    
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, []);
  
  // Tam ekran işlevi
  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      const viewerElement = document.getElementById('content-viewer');
      if (viewerElement && viewerElement.requestFullscreen) {
        viewerElement.requestFullscreen().catch(err => {
          setError(`Error attempting to enable fullscreen: ${err.message}`);
        });
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      }
    }
  };
  
  // Yakınlaştırma
  const handleZoomIn = () => {
    setZoom(prevZoom => Math.min(prevZoom + 0.25, 3));
  };
  
  const handleZoomOut = () => {
    setZoom(prevZoom => Math.max(prevZoom - 0.25, 0.5));
  };
  
  // PDF sayfa değişimi
  const handlePrevPage = () => {
    setCurrentPage(prev => Math.max(prev - 1, 1));
  };
  
  const handleNextPage = () => {
    setCurrentPage(prev => Math.min(prev + 1, numPages || 1));
  };
  
  // PDF yükleme callback
  const handleDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setLoading(false);
    if (onLoad) onLoad();
  };
  
  // PDF yükleme hatası
  const handleDocumentLoadError = (error: Error) => {
    setLoading(false);
    setError(`Error loading PDF: ${error.message}`);
    if (onError) onError(error);
  };
  
  // İçerik türü simgesi
  const getContentIcon = () => {
    switch (mode) {
      case ViewMode.PDF: return <FaFilePdf className="me-2" />;
      case ViewMode.IMAGE: return <FaFileImage className="me-2" />;
      case ViewMode.CODE: return <FaFileCode className="me-2" />;
      case ViewMode.AUDIO: return <FaFileAudio className="me-2" />;
      case ViewMode.VIDEO: return <FaFileVideo className="me-2" />;
      case ViewMode.JSON: return <FaFileCode className="me-2" />;
      case ViewMode.CSV: return <FaFileExcel className="me-2" />;
      default: return <FaFileAlt className="me-2" />;
    }
  };
  
  // Dosya indirme işlevi
  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = url;
    link.download = title || 'download';
    link.click();
  };
  
  // Paylaş işlevi (navigator.share API'si)
  const handleShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: title || 'Shared content',
          url: url
        });
      } catch (error: any) {
        if (error.name !== 'AbortError') {
          setError(`Error sharing content: ${error.message}`);
        }
      }
    } else {
      // Fallback: URL'i panoya kopyala
      navigator.clipboard.writeText(url)
        .then(() => alert('URL copied to clipboard'))
        .catch(error => setError(`Error copying to clipboard: ${error}`));
    }
  };
  
  // İçerik render işlevi
  const renderContent = () => {
    if (loading) {
      return (
        <div className="content-loading d-flex flex-column justify-content-center align-items-center h-100">
          <Spinner animation="border" variant="primary" />
          <p className="mt-3">{t('common.loading')}</p>
        </div>
      );
    }
    
    if (error) {
      return (
        <div className="content-error text-center p-4">
          <div className="alert alert-danger">
            {error}
          </div>
          <Button 
            variant="outline-primary"
            onClick={() => window.location.reload()}
          >
            {t('common.tryAgain')}
          </Button>
        </div>
      );
    }
    
    switch (mode) {
      case ViewMode.TEXT:
        return (
          <div 
            className="content-text p-3 overflow-auto"
            style={{ height: '100%', maxHeight: '100%' }}
          >
            <pre style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
              {highlightText ? (
                <HighlightedText text={url} searchTerm={highlightText} />
              ) : (
                url // URL burada metin içeriğinin kendisi
              )}
            </pre>
          </div>
        );
        
      case ViewMode.IMAGE:
        return (
          <div 
            className="content-image d-flex justify-content-center align-items-center"
            style={{ height: '100%', overflow: 'auto' }}
          >
            <img 
              src={url} 
              alt={title || "Image content"} 
              style={{ 
                maxWidth: '100%', 
                maxHeight: '100%',
                transform: `scale(${zoom})`,
                transition: 'transform 0.2s ease'
              }}
              onLoad={() => { setLoading(false); if (onLoad) onLoad(); }}
              onError={(e) => { 
                setLoading(false); 
                setError('Failed to load image'); 
                if (onError) onError(new Error('Failed to load image')); 
              }}
            />
          </div>
        );
        
      case ViewMode.PDF:
        return (
          <div className="content-pdf h-100 d-flex flex-column">
            <div className="pdf-container flex-grow-1 d-flex justify-content-center overflow-auto">
              <Document
                file={url}
                onLoadSuccess={handleDocumentLoadSuccess}
                onLoadError={handleDocumentLoadError}
                loading={
                  <div className="d-flex justify-content-center align-items-center h-100">
                    <Spinner animation="border" variant="primary" />
                  </div>
                }
              >
                <Page 
                  pageNumber={currentPage} 
                  scale={zoom}
                  renderTextLayer
                  renderAnnotationLayer
                />
              </Document>
            </div>
            
            {numPages && numPages > 1 && (
              <div className="pdf-navigation d-flex justify-content-between align-items-center p-2 border-top">
                <Button 
                  variant="outline-secondary" 
                  size="sm"
                  onClick={handlePrevPage}
                  disabled={currentPage <= 1}
                >
                  <FaChevronLeft />
                </Button>
                
                <div className="pdf-page-info">
                  {t('common.page')} {currentPage} / {numPages}
                </div>
                
                <Button 
                  variant="outline-secondary" 
                  size="sm"
                  onClick={handleNextPage}
                  disabled={currentPage >= numPages}
                >
                  <FaChevronRight />
                </Button>
              </div>
            )}
          </div>
        );
        
      case ViewMode.CODE:
        return (
          <div 
            className="content-code p-3 overflow-auto"
            style={{ height: '100%', maxHeight: '100%' }}
          >
            {syntaxHighlight ? (
              <pre className="language-code">
                <code className={`language-${codeLanguage || 'javascript'}`}>
                  {url /* URL burada kod içeriğinin kendisi */}
                </code>
              </pre>
            ) : (
              <pre style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
                {url /* URL burada kod içeriğinin kendisi */}
              </pre>
            )}
          </div>
        );
        
      case ViewMode.AUDIO:
        return (
          <div className="content-audio d-flex justify-content-center align-items-center h-100">
            <div className="audio-player-container">
              {thumbnail && (
                <div className="audio-thumbnail mb-3">
                  <img 
                    src={thumbnail} 
                    alt="Audio thumbnail" 
                    className="img-fluid rounded"
                    style={{ maxHeight: '200px' }}
                  />
                </div>
              )}
              <audio 
                controls 
                className="w-100"
                onLoadedData={() => { setLoading(false); if (onLoad) onLoad(); }}
                onError={() => { 
                  setLoading(false); 
                  setError('Failed to load audio');
                  if (onError) onError(new Error('Failed to load audio')); 
                }}
              >
                <source src={url} />
                Your browser does not support the audio element.
              </audio>
            </div>
          </div>
        );
        
      case ViewMode.VIDEO:
        return (
          <div className="content-video d-flex justify-content-center align-items-center h-100">
            <video 
              controls 
              style={{ maxWidth: '100%', maxHeight: '100%' }}
              onLoadedData={() => { setLoading(false); if (onLoad) onLoad(); }}
              onError={() => { 
                setLoading(false); 
                setError('Failed to load video');
                if (onError) onError(new Error('Failed to load video')); 
              }}
            >
              <source src={url} />
              Your browser does not support the video element.
            </video>
          </div>
        );
        
      case ViewMode.JSON:
        return (
          <div 
            className="content-json p-3 overflow-auto"
            style={{ height: '100%', maxHeight: '100%' }}
          >
            <pre style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
              {JSON.stringify(jsonData, null, 2)}
            </pre>
          </div>
        );
        
      case ViewMode.CSV:
        return (
          <div 
            className="content-csv overflow-auto"
            style={{ height: '100%', maxHeight: '100%' }}
          >
            <table className="table table-striped table-bordered">
              <thead>
                <tr>
                  {csvData[0]?.map((header, index) => (
                    <th key={`header-${index}`}>{header}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {csvData.slice(1).map((row, rowIndex) => (
                  <tr key={`row-${rowIndex}`}>
                    {row.map((cell, cellIndex) => (
                      <td key={`cell-${rowIndex}-${cellIndex}`}>{cell}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
        
      default:
        return (
          <div className="content-unsupported text-center p-4">
            <div className="alert alert-warning">
              {t('contentViewer.unsupportedFormat')}
            </div>
          </div>
        );
    }
  };
  
  return (
    <div 
      id="content-viewer" 
      className={`content-viewer ${fullscreen ? 'fullscreen' : ''} ${className}`}
      style={{ 
        ...style,
        height: fullscreen ? '100%' : height
      }}
    >
      <Card className="h-100 d-flex flex-column">
        {showToolbar && (
          <Card.Header className="d-flex justify-content-between align-items-center">
            <div className="content-title d-flex align-items-center">
              {getContentIcon()}
              {title && <span className="fw-bold">{title}</span>}
            </div>
            
            <div className="content-toolbar d-flex">
              {allowZoom && (mode === ViewMode.PDF || mode === ViewMode.IMAGE) && (
                <>
                  <Button 
                    variant="outline-secondary"
                    size="sm"
                    className="me-1"
                    onClick={handleZoomOut}
                    disabled={zoom <= 0.5}
                    title={t('contentViewer.zoomOut')}
                  >
                    <FaSearchMinus />
                  </Button>
                  
                  <Button 
                    variant="outline-secondary"
                    size="sm"
                    className="me-1"
                    onClick={handleZoomIn}
                    disabled={zoom >= 3}
                    title={t('contentViewer.zoomIn')}
                  >
                    <FaSearchPlus />
                  </Button>
                </>
              )}
              
              {allowDownload && (
                <Button
                  variant="outline-secondary"
                  size="sm"
                  className="me-1"
                  onClick={handleDownload}
                  title={t('contentViewer.download')}
                >
                  <FaDownload />
                </Button>
              )}
              
              {allowShare && navigator.share && (
                <Button
                  variant="outline-secondary"
                  size="sm"
                  className="me-1"
                  onClick={handleShare}
                  title={t('contentViewer.share')}
                >
                  <FaShare />
                </Button>
              )}
              
              {allowFullscreen && (
                <Button
                  variant="outline-secondary"
                  size="sm"
                  onClick={toggleFullscreen}
                  title={t('contentViewer.toggleFullscreen')}
                >
                  {fullscreen ? <FaCompress /> : <FaExpand />}
                </Button>
              )}
            </div>
          </Card.Header>
        )}
        
        <Card.Body className="p-0 flex-grow-1 overflow-hidden">
          {renderContent()}
        </Card.Body>
      </Card>
    </div>
  );
};

// Metin arama işlevi
interface HighlightedTextProps {
  text: string;
  searchTerm: string;
}

const HighlightedText: React.FC<HighlightedTextProps> = ({ text, searchTerm }) => {
  if (!searchTerm.trim()) {
    return <>{text}</>;
  }
  
  const parts = text.split(new RegExp(`(${searchTerm})`, 'gi'));
  
  return (
    <>
      {parts.map((part, i) => 
        part.toLowerCase() === searchTerm.toLowerCase() ? 
          <mark key={i}>{part}</mark> : 
          <span key={i}>{part}</span>
      )}
    </>
  );
};

export default ContentViewer;