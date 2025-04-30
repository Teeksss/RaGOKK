// Last reviewed: 2025-04-30 05:56:23 UTC (User: Teeksss)
import React, { useState, useRef } from 'react';
import { Form, Button, ProgressBar, Alert, Card, Spinner } from 'react-bootstrap';
import { useTranslation } from 'react-i18next';
import { FaUpload, FaFile, FaCog } from 'react-icons/fa';
import API from '../api/api';
import { useToast } from '../contexts/ToastContext';

interface DocumentUploaderProps {
  onUploadComplete?: (documentId: string) => void;
  maxFileSizeMB?: number;
  allowedFileTypes?: string[];
}

const DocumentUploader: React.FC<DocumentUploaderProps> = ({
  onUploadComplete,
  maxFileSizeMB = 10, // Varsayılan maksimum dosya boyutu: 10MB
  allowedFileTypes = ['.pdf', '.docx', '.doc', '.txt', '.md', '.jpg', '.jpeg', '.png']
}) => {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [title, setTitle] = useState<string>('');
  const [applyOcr, setApplyOcr] = useState<boolean>(false);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<boolean>(false);
  
  // Dosya seçimi işleyici
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) {
      setSelectedFile(null);
      return;
    }
    
    const file = files[0];
    
    // Dosya boyutu kontrolü
    const fileSizeInMB = file.size / (1024 * 1024);
    if (fileSizeInMB > maxFileSizeMB) {
      setError(t('document.fileSizeError', { maxSize: maxFileSizeMB }));
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      return;
    }
    
    // Varsayılan başlık olarak dosya adını ayarla (uzantı olmadan)
    const fileName = file.name;
    const fileNameWithoutExt = fileName.substring(0, fileName.lastIndexOf('.')) || fileName;
    setTitle(fileNameWithoutExt);
    
    setSelectedFile(file);
    setError(null);
    setSuccess(false);
    
    // Dosya türüne göre OCR seçeneğini varsayılan olarak ayarla
    const fileExtension = fileName.toLowerCase().split('.').pop() || '';
    const isImageOrPdf = ['jpg', 'jpeg', 'png', 'pdf', 'tiff', 'webp'].includes(fileExtension);
    setApplyOcr(isImageOrPdf);
  };
  
  // Dosya yükleme işleyici
  const handleUpload = async (event: React.FormEvent) => {
    event.preventDefault();
    
    if (!selectedFile) {
      setError(t('document.noFileSelected'));
      return;
    }
    
    if (!title.trim()) {
      setError(t('document.titleRequired'));
      return;
    }
    
    setUploading(true);
    setError(null);
    setSuccess(false);
    
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('title', title);
      formData.append('apply_ocr', applyOcr.toString());
      
      const response = await API.post('/documents/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / (progressEvent.total || 1));
          setUploadProgress(percentCompleted);
        }
      });
      
      // Başarılı yükleme
      setSuccess(true);
      setSelectedFile(null);
      setTitle('');
      setUploadProgress(0);
      
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      
      // Callback fonksiyonu çağır
      if (onUploadComplete && response.data && response.data.id) {
        onUploadComplete(response.data.id);
      }
      
      showToast('success', t('document.uploadSuccess'));
      
    } catch (err: any) {
      setError(
        err.response?.data?.detail || 
        err.message || 
        t('document.uploadError')
      );
      showToast('error', t('document.uploadError'));
      
      // Özel hata durumları
      if (err.response?.status === 409) {
        // Yinelenen belge hatası
        showToast('warning', t('document.duplicateDocument'));
      }
      
    } finally {
      setUploading(false);
    }
  };
  
  // Dosya türü kontrolü için kabul edilen formatların string'i
  const acceptedFileTypes = allowedFileTypes.join(',');
  
  return (
    <Card className="shadow-sm">
      <Card.Header className="d-flex justify-content-between align-items-center">
        <h5 className="mb-0">
          <FaUpload className="me-2" />
          {t('document.uploadDocument')}
        </h5>
      </Card.Header>
      
      <Card.Body>
        <Form onSubmit={handleUpload}>
          {/* Dosya seçimi */}
          <Form.Group className="mb-3">
            <Form.Label>{t('document.selectFile')}</Form.Label>
            <Form.Control
              type="file"
              ref={fileInputRef}
              onChange={handleFileSelect}
              accept={acceptedFileTypes}
              disabled={uploading}
            />
            <Form.Text className="text-muted">
              {t('document.allowedFileTypes')}: {allowedFileTypes.join(', ')}
            </Form.Text>
            <Form.Text className="text-muted d-block">
              {t('document.maxFileSize')}: {maxFileSizeMB} MB
            </Form.Text>
          </Form.Group>
          
          {/* Belge başlığı */}
          <Form.Group className="mb-3">
            <Form.Label>{t('document.title')}</Form.Label>
            <Form.Control
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={t('document.enterTitle')}
              disabled={uploading}
              required
            />
          </Form.Group>
          
          {/* OCR seçeneği */}
          <Form.Group className="mb-4">
            <Form.Check
              type="checkbox"
              id="apply-ocr"
              label={t('document.applyOcr')}
              checked={applyOcr}
              onChange={(e) => setApplyOcr(e.target.checked)}
              disabled={uploading}
            />
            <Form.Text className="text-muted">
              {t('document.ocrDescription')}
            </Form.Text>
          </Form.Group>
          
          {/* İlerleme durumu */}
          {uploading && (
            <div className="mb-3">
              <ProgressBar
                now={uploadProgress}
                label={`${uploadProgress}%`}
                variant="primary"
                animated
              />
            </div>
          )}
          
          {/* Hata mesajı */}
          {error && (
            <Alert variant="danger" className="mb-3">
              {error}
            </Alert>
          )}
          
          {/* Başarı mesajı */}
          {success && (
            <Alert variant="success" className="mb-3">
              {t('document.uploadSuccess')}
            </Alert>
          )}
          
          {/* Yükleme butonu */}
          <div className="d-grid gap-2">
            <Button
              variant="primary"
              type="submit"
              disabled={!selectedFile || uploading || !title.trim()}
            >
              {uploading ? (
                <>
                  <Spinner animation="border" size="sm" className="me-2" />
                  {t('document.uploading')}
                </>
              ) : (
                <>
                  <FaUpload className="me-2" />
                  {t('document.upload')}
                </>
              )}
            </Button>
          </div>
        </Form>
      </Card.Body>
    </Card>
  );
};

export default DocumentUploader;