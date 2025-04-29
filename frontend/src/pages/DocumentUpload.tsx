// Last reviewed: 2025-04-29 11:44:12 UTC (User: Teekssseskikleri tamamla)
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card, Form, ProgressBar, Alert, Container, Row, Col } from 'react-bootstrap';
import { useToast } from '../contexts/ToastContext';
import { useAuth } from '../contexts/AuthContext';
import { TagsInput } from '../components/TagsInput';
import { apiRequest } from '../utils/api';
import { FileIcon } from '../components/FileIcon';
import '../styles/DocumentUpload.css';

interface FilePreview {
  file: File;
  preview: string | null;
  type: string;
  size: string;
}

export const DocumentUpload: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [filePreview, setFilePreview] = useState<FilePreview | null>(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [isPublic, setIsPublic] = useState(false);
  const [autoProcess, setAutoProcess] = useState(true);
  const [loading, setLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { showToast } = useToast();
  const { user } = useAuth();
  const navigate = useNavigate();
  
  // Dosya seçildiğinde önizleme oluştur
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;
    
    // Dosya türü kontrolü
    const supportedTypes = [
      'application/pdf', 
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/plain', 
      'text/html', 
      'application/xml',
      'application/json',
      'text/csv'
    ];
    
    if (!supportedTypes.includes(selectedFile.type)) {
      setError('Desteklenmeyen dosya türü. Lütfen PDF, DOCX, TXT, HTML, XML, JSON veya CSV dosyası seçin.');
      return;
    }
    
    setFile(selectedFile);
    
    // Dosya boyutunu formatlı göster
    const fileSize = formatFileSize(selectedFile.size);
    
    // Dosya önizlemesi için URL oluştur (sadece belirli türler için)
    let previewUrl = null;
    if (selectedFile.type.startsWith('text/') || selectedFile.type === 'application/json') {
      // Metin tabanlı dosyalar için bir önizleme oluşturulabilir
      const reader = new FileReader();
      reader.onload = (e) => {
        // Metin içeriğini thumbnail'e dönüştürme (ilk birkaç satır)
        setFilePreview({
          file: selectedFile,
          preview: e.target?.result as string,
          type: selectedFile.type,
          size: fileSize
        });
      };
      reader.readAsText(selectedFile);
    } else {
      // Diğer dosya türleri için sadece icon göster
      setFilePreview({
        file: selectedFile,
        preview: null,
        type: selectedFile.type,
        size: fileSize
      });
    }
    
    // Dosya adını başlık olarak ayarla (boşsa)
    if (!title) {
      // Uzantısız dosya adı
      const fileName = selectedFile.name.split('.').slice(0, -1).join('.');
      setTitle(fileName);
    }
  };
  
  // Dosya boyutunu formatlı hale getirir
  const formatFileSize = (size: number): string => {
    if (size < 1024) return `${size} B`;
    else if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
    else if (size < 1024 * 1024 * 1024) return `${(size / (1024 * 1024)).toFixed(1)} MB`;
    else return `${(size / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  };
  
  // Dosya yükleme işlemi
  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!file) {
      setError('Lütfen bir dosya seçin.');
      return;
    }
    
    if (!title.trim()) {
      setError('Lütfen bir başlık girin.');
      return;
    }
    
    try {
      setLoading(true);
      setError(null);
      
      // Form verilerini hazırla
      const formData = new FormData();
      formData.append('file', file);
      formData.append('title', title);
      
      if (description) {
        formData.append('description', description);
      }
      
      if (tags.length > 0) {
        formData.append('tags', JSON.stringify(tags));
      }
      
      formData.append('is_public', String(isPublic));
      formData.append('auto_process', String(autoProcess));
      
      // Upload simülasyonu (gerçek bir API olsaydı burada XHR veya fetch kullanılırdı)
      // Simüle edilmiş ilerleme
      const interval = setInterval(() => {
        setUploadProgress(prev => {
          const newProgress = prev + Math.floor(Math.random() * 15);
          return newProgress > 95 ? 95 : newProgress;
        });
      }, 200);
      
      // API'ye POST isteği
      const response = await apiRequest('/api/documents/upload', {
        method: 'POST',
        body: formData,
        includeAuth: true
      });
      
      clearInterval(interval);
      setUploadProgress(100);
      
      // Yükleme başarılı
      if (response.document_id) {
        showToast('Doküman başarıyla yüklendi.', 'success');
        
        // Kısa bir gecikme sonra doküman sayfasına yönlendir
        setTimeout(() => {
          navigate(`/documents/${response.document_id}`);
        }, 1000);
      } else {
        throw new Error('Doküman ID alınamadı.');
      }
      
    } catch (err: any) {
      setError(`Yükleme hatası: ${err.message || 'Bilinmeyen hata'}`);
      setUploadProgress(0);
    } finally {
      setLoading(false);
    }
  };
  
  // Browse butonuna tıklandığında input'u tetikle
  const handleBrowseClick = () => {
    fileInputRef.current?.click();
  };
  
  return (
    <Container className="document-upload-container">
      <h1>Doküman Yükle</h1>
      
      <Card>
        <Card.Body>
          {error && <Alert variant="danger">{error}</Alert>}
          
          <Form onSubmit={handleUpload}>
            {/* Dosya Seçme Alanı */}
            <div className="file-drop-area">
              {!filePreview ? (
                <>
                  <div className="file-message">
                    <i className="bi bi-cloud-arrow-up"></i>
                    <p>Dosya yüklemek için sürükleyip bırakın veya tıklayın</p>
                    <small>Desteklenen formatlar: PDF, DOCX, TXT, HTML, XML, JSON, CSV</small>
                  </div>
                  <input 
                    type="file" 
                    ref={fileInputRef}
                    onChange={handleFileChange} 
                    className="file-input" 
                    accept=".pdf,.docx,.txt,.html,.xml,.json,.csv"
                    disabled={loading}
                  />
                </>
              ) : (
                <div className="file-preview">
                  <div className="preview-header">
                    <FileIcon fileType={filePreview.type.split('/')[1]} />
                    <div className="file-info">
                      <strong>{filePreview.file.name}</strong>
                      <span>{filePreview.size}</span>
                    </div>
                    <Button 
                      variant="outline-danger" 
                      size="sm" 
                      onClick={() => {
                        setFile(null);
                        setFilePreview(null);
                        setUploadProgress(0);
                      }}
                      disabled={loading}
                    >
                      <i className="bi bi-x"></i>
                    </Button>
                  </div>
                  
                  {filePreview.preview && (
                    <div className="text-preview">
                      <pre className="preview-content">
                        {(filePreview.preview as string).substring(0, 500)}
                        {(filePreview.preview as string).length > 500 && '...'}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
            
            {/* Form Alanları */}
            <Row className="mt-4">
              <Col md={8}>
                <Form.Group className="mb-3">
                  <Form.Label>Başlık</Form.Label>
                  <Form.Control 
                    type="text" 
                    value={title} 
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="Doküman başlığı"
                    disabled={loading}
                    required
                  />
                </Form.Group>
              </Col>
              
              <Col md={4}>
                <Form.Group className="mb-3">
                  <Form.Label>Etiketler</Form.Label>
                  <TagsInput 
                    tags={tags} 
                    setTags={setTags}
                    disabled={loading} 
                  />
                </Form.Group>
              </Col>
            </Row>
            
            <Form.Group className="mb-3">
              <Form.Label>Açıklama</Form.Label>
              <Form.Control 
                as="textarea" 
                rows={3}
                value={description} 
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Doküman hakkında açıklama (opsiyonel)"
                disabled={loading}
              />
            </Form.Group>
            
            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Check 
                    type="switch"
                    id="public-switch"
                    label="Bu dokümanı herkese açık yap"
                    checked={isPublic}
                    onChange={() => setIsPublic(!isPublic)}
                    disabled={loading}
                  />
                </Form.Group>
              </Col>
              
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Check 
                    type="switch"
                    id="process-switch"
                    label="Otomatik işleme (embedding ve indeksleme)"
                    checked={autoProcess}
                    onChange={() => setAutoProcess(!autoProcess)}
                    disabled={loading}
                  />
                </Form.Group>
              </Col>
            </Row>
            
            {/* İlerleme Çubuğu */}
            {uploadProgress > 0 && (
              <ProgressBar 
                now={uploadProgress} 
                label={`${uploadProgress}%`} 
                className="mb-3" 
              />
            )}
            
            <div className="d-flex justify-content-between">
              <Button 
                variant="outline-secondary" 
                onClick={() => navigate('/documents')}
                disabled={loading}
              >
                İptal
              </Button>
              
              <div>
                <Button 
                  variant="outline-primary"
                  onClick={handleBrowseClick}
                  className="me-2"
                  disabled={loading}
                >
                  <i className="bi bi-file-earmark"></i> Dosya Seç
                </Button>
                
                <Button 
                  variant="primary" 
                  type="submit" 
                  disabled={!file || loading}
                >
                  {loading ? (
                    <>
                      <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                      Yükleniyor...
                    </>
                  ) : (
                    <>
                      <i className="bi bi-cloud-upload"></i> Yükle
                    </>
                  )}
                </Button>
              </div>
            </div>
          </Form>
        </Card.Body>
      </Card>
    </Container>
  );
};