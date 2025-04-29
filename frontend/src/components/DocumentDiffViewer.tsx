// Last reviewed: 2025-04-29 12:35:57 UTC (User: TeeksssVisual Diff)
import React, { useState, useEffect, useMemo } from 'react';
import { Button, Card, Nav, Row, Col, Badge, Form, Spinner } from 'react-bootstrap';
import { useParams, useNavigate } from 'react-router-dom';
import { diffLines, diffWords, diffChars } from 'diff';
import { apiRequest } from '../utils/api';
import { toast } from 'react-toastify';

// Diff veri türleri
interface DiffPart {
  value: string;
  added?: boolean;
  removed?: boolean;
}

interface VersionInfo {
  id: number;
  document_id: number;
  version_label: string;
  created_at: string;
  created_by: string;
  change_description: string;
}

interface DiffViewerProps {
  leftVersionId: number | null;
  rightVersionId: number | null;
  documentId: number;
  onLoadError?: (error: string) => void;
}

export const DocumentDiffViewer: React.FC<DiffViewerProps> = ({
  leftVersionId,
  rightVersionId,
  documentId,
  onLoadError
}) => {
  // State tanımlamaları
  const [loading, setLoading] = useState(true);
  const [leftContent, setLeftContent] = useState<string>('');
  const [rightContent, setRightContent] = useState<string>('');
  const [leftVersion, setLeftVersion] = useState<VersionInfo | null>(null);
  const [rightVersion, setRightVersion] = useState<VersionInfo | null>(null);
  const [diffMode, setDiffMode] = useState<'lines' | 'words' | 'chars'>('lines');
  const [showWhitespace, setShowWhitespace] = useState(false);
  const [versions, setVersions] = useState<VersionInfo[]>([]);
  
  // İçerik yükleme
  useEffect(() => {
    const fetchVersions = async () => {
      try {
        setLoading(true);
        // Tüm versiyonları getir
        const response = await apiRequest(`/api/documents/${documentId}/versions`, {
          method: 'GET',
          includeAuth: true
        });
        
        if (response.versions && Array.isArray(response.versions)) {
          setVersions(response.versions);
          
          // Belirtilen versiyonları yükle
          if (leftVersionId !== null && rightVersionId !== null) {
            await loadVersionContent(leftVersionId, rightVersionId);
          } else if (response.versions.length >= 2) {
            // Varsayılan olarak son iki versiyonu göster
            const sortedVersions = [...response.versions].sort((a, b) => 
              new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
            );
            await loadVersionContent(sortedVersions[1].id, sortedVersions[0].id);
          }
        }
      } catch (error) {
        console.error('Failed to load document versions:', error);
        if (onLoadError) onLoadError('Doküman versiyonları yüklenemedi.');
        toast.error('Doküman versiyonları yüklenemedi.');
      } finally {
        setLoading(false);
      }
    };
    
    fetchVersions();
  }, [documentId, leftVersionId, rightVersionId]);
  
  // Belirli versiyonların içeriğini yükle
  const loadVersionContent = async (leftId: number, rightId: number) => {
    try {
      setLoading(true);
      
      // Sol versiyon
      const leftResponse = await apiRequest(`/api/documents/${documentId}/versions/${leftId}`, {
        method: 'GET',
        includeAuth: true
      });
      
      if (leftResponse) {
        setLeftContent(leftResponse.content || '');
        setLeftVersion(leftResponse);
      }
      
      // Sağ versiyon
      const rightResponse = await apiRequest(`/api/documents/${documentId}/versions/${rightId}`, {
        method: 'GET',
        includeAuth: true
      });
      
      if (rightResponse) {
        setRightContent(rightResponse.content || '');
        setRightVersion(rightResponse);
      }
      
    } catch (error) {
      console.error('Failed to load version content:', error);
      if (onLoadError) onLoadError('Versiyon içeriği yüklenemedi.');
      toast.error('Versiyon içeriği yüklenemedi.');
    } finally {
      setLoading(false);
    }
  };
  
  // Diff hesaplama
  const diff = useMemo(() => {
    let diffResult: DiffPart[] = [];
    
    if (!leftContent || !rightContent) {
      return diffResult;
    }
    
    let leftText = leftContent;
    let rightText = rightContent;
    
    // Whitespace karakterleri görünür yap
    if (showWhitespace) {
      leftText = leftText
        .replace(/\r\n/g, '↵\n')
        .replace(/\n/g, '↵\n')
        .replace(/\t/g, '→\t')
        .replace(/ /g, '·');
        
      rightText = rightText
        .replace(/\r\n/g, '↵\n')
        .replace(/\n/g, '↵\n')
        .replace(/\t/g, '→\t')
        .replace(/ /g, '·');
    }
    
    // Diff modu seçimi
    switch (diffMode) {
      case 'lines':
        diffResult = diffLines(leftText, rightText);
        break;
      case 'words':
        diffResult = diffWords(leftText, rightText);
        break;
      case 'chars':
        diffResult = diffChars(leftText, rightText);
        break;
    }
    
    return diffResult;
  }, [leftContent, rightContent, diffMode, showWhitespace]);
  
  // Versiyon seçimlerini güncelle
  const handleVersionChange = (side: 'left' | 'right', versionId: number) => {
    if (side === 'left') {
      loadVersionContent(versionId, rightVersion?.id || 0);
    } else {
      loadVersionContent(leftVersion?.id || 0, versionId);
    }
  };
  
  // Yükleniyor gösterimi
  if (loading) {
    return (
      <div className="text-center p-5">
        <Spinner animation="border" variant="primary" />
        <p className="mt-3">Versiyonlar yükleniyor...</p>
      </div>
    );
  }
  
  // Diff oluşturulmamış - seçim yapılmamış
  if (!leftVersion || !rightVersion) {
    return (
      <div className="alert alert-info">
        Karşılaştırmak için iki versiyon seçin.
      </div>
    );
  }
  
  return (
    <Card className="mb-4 shadow-sm">
      <Card.Header>
        <Row className="align-items-center">
          <Col>
            <h5 className="mb-0">Doküman Versiyon Karşılaştırma</h5>
          </Col>
          <Col md="auto">
            <Form.Group className="d-flex align-items-center">
              <Form.Label className="me-2 mb-0">Diff Modu:</Form.Label>
              <Form.Select 
                size="sm" 
                value={diffMode} 
                onChange={(e) => setDiffMode(e.target.value as 'lines' | 'words' | 'chars')}
                style={{ width: 'auto' }}
              >
                <option value="lines">Satır bazlı</option>
                <option value="words">Kelime bazlı</option>
                <option value="chars">Karakter bazlı</option>
              </Form.Select>
              
              <Form.Check 
                className="ms-3" 
                type="switch"
                id="whitespace-switch"
                label="Boşlukları göster"
                checked={showWhitespace}
                onChange={() => setShowWhitespace(!showWhitespace)}
              />
            </Form.Group>
          </Col>
        </Row>
      </Card.Header>
      
      <Card.Body>
        {/* Versiyon seçiciler */}
        <Row className="mb-4">
          <Col md={6}>
            <Form.Group>
              <Form.Label>Eski Versiyon:</Form.Label>
              <Form.Select 
                value={leftVersion?.id || ''} 
                onChange={(e) => handleVersionChange('left', Number(e.target.value))}
              >
                {versions.map((version) => (
                  <option key={`left-${version.id}`} value={version.id}>
                    {version.version_label} ({new Date(version.created_at).toLocaleString()})
                  </option>
                ))}
              </Form.Select>
            </Form.Group>
            {leftVersion && (
              <div className="mt-2">
                <Badge bg="secondary" className="me-2">Oluşturan: {leftVersion.created_by}</Badge>
                <Badge bg="info">{new Date(leftVersion.created_at).toLocaleString()}</Badge>
                {leftVersion.change_description && (
                  <p className="mt-2 small text-muted">{leftVersion.change_description}</p>
                )}
              </div>
            )}
          </Col>
          <Col md={6}>
            <Form.Group>
              <Form.Label>Yeni Versiyon:</Form.Label>
              <Form.Select 
                value={rightVersion?.id || ''} 
                onChange={(e) => handleVersionChange('right', Number(e.target.value))}
              >
                {versions.map((version) => (
                  <option key={`right-${version.id}`} value={version.id}>
                    {version.version_label} ({new Date(version.created_at).toLocaleString()})
                  </option>
                ))}
              </Form.Select>
            </Form.Group>
            {rightVersion && (
              <div className="mt-2">
                <Badge bg="secondary" className="me-2">Oluşturan: {rightVersion.created_by}</Badge>
                <Badge bg="info">{new Date(rightVersion.created_at).toLocaleString()}</Badge>
                {rightVersion.change_description && (
                  <p className="mt-2 small text-muted">{rightVersion.change_description}</p>
                )}
              </div>
            )}
          </Col>
        </Row>
        
        {/* Özet bilgiler */}
        {diff.length > 0 && (
          <Row className="mb-3">
            <Col>
              <div className="diff-stats p-2 border rounded">
                <span className="me-3">
                  <Badge bg="success">Eklenen</Badge>
                  <span className="ms-1">
                    {diff.filter(d => d.added).reduce((sum, d) => sum + (d.value.split('\n').length - 1), 0)} satır
                  </span>
                </span>
                <span className="me-3">
                  <Badge bg="danger">Silinen</Badge>
                  <span className="ms-1">
                    {diff.filter(d => d.removed).reduce((sum, d) => sum + (d.value.split('\n').length - 1), 0)} satır
                  </span>
                </span>
                <span>
                  <Badge bg="secondary">Değişmeyen</Badge>
                  <span className="ms-1">
                    {diff.filter(d => !d.added && !d.removed).reduce((sum, d) => sum + (d.value.split('\n').length - 1), 0)} satır
                  </span>
                </span>
              </div>
            </Col>
          </Row>
        )}
        
        {/* Diff görünümü */}
        <Row>
          <Col>
            <div className="diff-container border rounded">
              {diffMode === 'lines' ? (
                <div className="diff-lines">
                  {diff.map((part, index) => (
                    <div 
                      key={index}
                      className={`diff-part ${part.added ? 'diff-added' : part.removed ? 'diff-removed' : 'diff-unchanged'}`}
                    >
                      {part.value.split('\n').map((line, lineIndex, lines) => 
                        lineIndex < lines.length - 1 || line ? (
                          <div className="diff-line" key={`${index}-${lineIndex}`}>
                            <span className="diff-line-prefix">
                              {part.added ? '+ ' : part.removed ? '- ' : '  '}
                            </span>
                            <span className="diff-line-content">{line}</span>
                          </div>
                        ) : null
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="diff-inline">
                  {diff.map((part, index) => (
                    <span 
                      key={index}
                      className={`diff-part ${part.added ? 'diff-added' : part.removed ? 'diff-removed' : ''}`}
                    >
                      {part.value}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </Col>
        </Row>
        
        {/* Açıklamalar */}
        <div className="mt-3">
          <div className="diff-legend">
            <span className="legend-item">
              <span className="legend-color added"></span> Eklenen
            </span>
            <span className="legend-item">
              <span className="legend-color removed"></span> Silinen
            </span>
            <span className="legend-item">
              <span className="legend-color unchanged"></span> Değişmeyen
            </span>
          </div>
        </div>
      </Card.Body>
    </Card>
  );
};

// Sayfa bileşeni
export const DocumentVersionCompare: React.FC = () => {
  const { documentId, leftVersionId, rightVersionId } = useParams();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  
  return (
    <div className="container py-4">
      <h1 className="mb-4">Doküman Versiyonları Karşılaştırma</h1>
      
      {error && <div className="alert alert-danger">{error}</div>}
      
      <DocumentDiffViewer 
        documentId={Number(documentId)}
        leftVersionId={leftVersionId ? Number(leftVersionId) : null}
        rightVersionId={rightVersionId ? Number(rightVersionId) : null}
        onLoadError={setError}
      />
      
      <div className="mt-3">
        <Button 
          variant="secondary" 
          onClick={() => navigate(`/documents/${documentId}`)}
        >
          Doküman Sayfasına Dön
        </Button>
      </div>
    </div>
  );
};