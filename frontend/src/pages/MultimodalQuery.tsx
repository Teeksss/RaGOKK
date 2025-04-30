// Last reviewed: 2025-04-30 08:34:14 UTC (User: Teeksss)
import React, { useState, useRef } from 'react';
import { Container, Row, Col, Card, Form, Button, Alert, Spinner } from 'react-bootstrap';
import { FaUpload, FaTrash, FaSearch, FaImage, FaExclamationTriangle } from 'react-icons/fa';
import { useTranslation } from 'react-i18next';

import API from '../api/api';
import { useToast } from '../contexts/ToastContext';
import { useQuery } from '../contexts/QueryContext';
import StreamingQueryResult from '../components/query/StreamingQueryResult';

const MultimodalQuery: React.FC = () => {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const { addToHistory } = useQuery();
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // State
  const [query, setQuery] = useState<string>('');
  const [images, setImages] = useState<File[]>([]);
  const [previewUrls, setPreviewUrls] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [documentFilter, setDocumentFilter] = useState<string[]>([]);
  const [documentOptions, setDocumentOptions] = useState<{ value: string, label: string }[]>([]);
  
  // Belge seçeneklerini yükle
  React.useEffect(() => {
    const fetchDocuments = async () => {
      try {
        const response = await API.get('/documents');
        const options = response.data.map((doc: any) => ({
          value: doc.id,
          label: doc.title || doc.file_name
        }));
        setDocumentOptions(options);
      } catch (err) {
        console.error('Error loading documents:', err);
      }
    };
    
    fetchDocuments();
  }, []);
  
  // Dosya yükleme işlemi
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      // Mevcut sayı kontrolü
      if (images.length + e.target.files.length > 5) {
        showToast('warning', t('multimodal.maxImagesError'));
        return;
      }
      
      // Dosya tipleri kontrolü
      const validFiles: File[] = [];
      const validPreviewUrls: string[] = [];
      
      Array.from(e.target.files).forEach(file => {
        if (file.type.startsWith('image/')) {
          validFiles.push(file);
          validPreviewUrls.push(URL.createObjectURL(file));
        } else {
          showToast('warning', t('multimodal.invalidFileType', { filename: file.name }));
        }
      });
      
      // Geçerli dosyaları ekle
      setImages(prev => [...prev, ...validFiles]);
      setPreviewUrls(prev => [...prev, ...validPreviewUrls]);
    }
  };
  
  // Resim silme
  const removeImage = (index: number) => {
    setImages(prev => prev.filter((_, i) => i !== index));
    
    // URL nesnesini temizle
    URL.revokeObjectURL(previewUrls[index]);
    setPreviewUrls(prev => prev.filter((_, i) => i !== index));
  };
  
  // Dosya seçme butonunu tetikle
  const triggerFileInput = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };
  
  // Multimodal sorgu gönderme
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!query.trim()) {
      showToast('warning', t('multimodal.emptyQueryError'));
      return;
    }
    
    if (images.length === 0) {
      showToast('warning', t('multimodal.noImagesError'));
      return;
    }
    
    setLoading(true);
    setError(null);
    setResult(null);
    
    try {
      // Form data hazırla
      const formData = new FormData();
      formData.append('query', query);
      
      // Görselleri ekle
      images.forEach(image => formData.append('images', image));
      
      // Belge filtreleri ekle
      if (documentFilter.length > 0) {
        formData.append('document_ids', JSON.stringify(documentFilter));
      }
      
      // Multimodal API'sine gönder
      const response = await API.post('/multimodal/query', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      // Sonucu işle
      setResult(response.data);
      
      // Geçmişe ekle
      if (response.data.success && addToHistory) {
        addToHistory({
          id: Date.now().toString(),
          query,
          type: 'multimodal',
          timestamp: new Date().toISOString(),
          answer: response.data.answer,
          metadata: {
            imageCount: images.length,
            documentFilter: documentFilter
          }
        });
      }
      
    } catch (err: any) {
      console.error('Error submitting multimodal query:', err);
      setError(err.response?.data?.detail || t('multimodal.apiError'));
      setResult(null);
    } finally {
      setLoading(false);
    }
  };
  
  // Form temizle
  const handleClear = () => {
    setQuery('');
    
    // URL nesnelerini temizle
    previewUrls.forEach(url => URL.revokeObjectURL(url));
    
    setImages([]);
    setPreviewUrls([]);
    setResult(null);
    setError(null);
    setDocumentFilter([]);
  };
  
  // Belge filtresi değişimi
  const handleDocumentFilterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const values = Array.from(e.target.selectedOptions).map(option => option.value);
    setDocumentFilter(values);
  };
  
  return (
    <Container>
      <h1 className="mb-4">{t('multimodal.title')}</h1>
      
      <Card className="mb-4">
        <Card.Body>
          <Form onSubmit={handleSubmit}>
            {/* Soru Giriş Alanı */}
            <Form.Group className="mb-4">
              <Form.Label>{t('multimodal.queryLabel')}</Form.Label>
              <Form.Control
                as="textarea"
                rows={3}
                placeholder={t('multimodal.queryPlaceholder')}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                disabled={loading}
                required
              />
              <Form.Text className="text-muted">
                {t('multimodal.queryHelp')}
              </Form.Text>
            </Form.Group>
            
            {/* Belge Filtreleme */}
            <Form.Group className="mb-4">
              <Form.Label>{t('multimodal.documentFilterLabel')}</Form.Label>
              <Form.Select 
                multiple
                value={documentFilter}
                onChange={handleDocumentFilterChange}
                disabled={loading}
              >
                {documentOptions.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </Form.Select>
              <Form.Text className="text-muted">
                {t('multimodal.documentFilterHelp')}
              </Form.Text>
            </Form.Group>
            
            {/* Resim Yükleme */}
            <Form.Group className="mb-4">
              <Form.Label>{t('multimodal.imagesLabel')}</Form.Label>
              
              <div className="d-flex mb-3">
                <Button
                  variant="outline-primary"
                  onClick={triggerFileInput}
                  disabled={loading || images.length >= 5}
                  className="me-2"
                >
                  <FaUpload className="me-2" />
                  {t('multimodal.selectImages')}
                </Button>
                
                <Form.Control
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  accept="image/*"
                  multiple
                  className="d-none"
                  disabled={loading || images.length >= 5}
                />
                
                <Form.Text className="text-muted d-flex align-items-center">
                  {images.length}/5 {t('multimodal.imagesSelected')}
                </Form.Text>
              </div>
              
              {/* Önizlemeler */}
              {previewUrls.length > 0 && (
                <Row className="image-previews g-2 mb-3">
                  {previewUrls.map((url, index) => (
                    <Col key={index} xs={6} md={4} lg={3} className="preview-item">
                      <div className="preview-container position-relative">
                        <img src={url} alt={`Preview ${index + 1}`} className="img-thumbnail preview-image" />
                        
                        <Button
                          variant="danger"
                          size="sm"
                          className="position-absolute top-0 end-0 m-1"
                          onClick={() => removeImage(index)}
                          disabled={loading}
                        >
                          <FaTrash />
                        </Button>
                      </div>
                    </Col>
                  ))}
                </Row>
              )}
              
              <Form.Text className="text-muted">
                {t('multimodal.imagesHelp')}
              </Form.Text>
            </Form.Group>
            
            {/* Butonlar */}
            <div className="d-flex">
              <Button
                type="submit"
                variant="primary"
                className="me-2"
                disabled={loading || !query.trim() || images.length === 0}
              >
                {loading ? (
                  <>
                    <Spinner animation="border" size="sm" className="me-2" />
                    {t('common.processing')}
                  </>
                ) : (
                  <>
                    <FaSearch className="me-2" />
                    {t('multimodal.submit')}
                  </>
                )}
              </Button>
              
              <Button
                type="button"
                variant="outline-secondary"
                onClick={handleClear}
                disabled={loading}
              >
                {t('common.clear')}
              </Button>
            </div>
          </Form>
        </Card.Body>
      </Card>
      
      {/* Hata Gösterimi */}
      {error && (
        <Alert variant="danger" className="mb-4">
          <FaExclamationTriangle className="me-2" />
          {error}
        </Alert>
      )}
      
      {/* Sonuç Gösterimi */}
      {result && (
        <Card className="mb-4">
          <Card.Header>
            <div className="d-flex justify-content-between align-items-center">
              <h5 className="mb-0">
                <FaImage className="me-2" />
                {t('multimodal.result')}
              </h5>
              
              <span className="text-muted small">
                {new Date(result.timestamp).toLocaleString()}
              </span>
            </div>
          </Card.Header>
          
          <Card.Body>
            {result.success ? (
              <div className="multimodal-answer">
                <div className="query mb-3">
                  <strong>{t('multimodal.yourQuestion')}:</strong>
                  <p>{result.query}</p>
                </div>
                
                <div className="answer">
                  <strong>{t('multimodal.answer')}:</strong>
                  <div className="answer-content mt-2">
                    <pre className="bg-light p-3 rounded" style={{ whiteSpace: 'pre-wrap' }}>
                      {result.answer}
                    </pre>
                  </div>
                </div>
              </div>
            ) : (
              <Alert variant="warning">
                <FaExclamationTriangle className="me-2" />
                {result.error || t('multimodal.processingError')}
              </Alert>
            )}
          </Card.Body>
        </Card>
      )}
      
      {/* Bilgi Kartı */}
      <Card className="mb-4 bg-light">
        <Card.Body>
          <h5>{t('multimodal.aboutTitle')}</h5>
          <p>{t('multimodal.aboutDescription')}</p>
          
          <h6>{t('multimodal.exampleTitle')}</h6>
          <ul>
            <li>{t('multimodal.example1')}</li>
            <li>{t('multimodal.example2')}</li>
            <li>{t('multimodal.example3')}</li>
          </ul>
        </Card.Body>
      </Card>
    </Container>
  );
};

export default MultimodalQuery;