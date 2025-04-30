// Last reviewed: 2025-04-30 05:56:23 UTC (User: Teeksss)
import React, { useState } from 'react';
import { Modal, Button, Alert, Spinner } from 'react-bootstrap';
import { FaTrash, FaExclamationTriangle } from 'react-icons/fa';
import { useTranslation } from 'react-i18next';
import API from '../api/api';
import { useToast } from '../contexts/ToastContext';
import { useAuth } from '../contexts/AuthContext';

interface DeleteDocumentModalProps {
  show: boolean;
  onHide: () => void;
  documentId: string;
  documentTitle: string;
  documentOwnerId: string;
  onDeleted: () => void;
}

const DeleteDocumentModal: React.FC<DeleteDocumentModalProps> = ({
  show,
  onHide,
  documentId,
  documentTitle,
  documentOwnerId,
  onDeleted
}) => {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const { isSuperuser, user } = useAuth();
  
  // State
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  
  // Belge silme işlemini gerçekleştir
  const handleDelete = async () => {
    setIsDeleting(true);
    setError(null);
    
    try {
      // Belge sahibi kontrolü
      const isOwner = user?.id === documentOwnerId;
      
      // Süper kullanıcılar zorunlu silme yapabilir
      const forceDelete = isSuperuser() && !isOwner;
      
      // Belgeyi sil
      await API.delete(`/documents/${documentId}${forceDelete ? '?force=true' : ''}`);
      
      // Başarı bildirimi
      showToast('success', t('document.deleteSuccess'));
      
      // Modal'ı kapat ve callback'i çağır
      onHide();
      onDeleted();
      
    } catch (err: any) {
      // Hata mesajını ayarla
      setError(
        err.response?.data?.detail || 
        err.message || 
        t('document.deleteError')
      );
      
      // 403 hatası (izin reddedildi)
      if (err.response?.status === 403) {
        showToast('error', t('document.permissionDenied'));
      } else {
        showToast('error', t('document.deleteError'));
      }
      
    } finally {
      setIsDeleting(false);
    }
  };
  
  // Kullanıcı yetki kontrolü
  const canDelete = isSuperuser() || user?.id === documentOwnerId;
  
  return (
    <Modal show={show} onHide={onHide} centered backdrop="static">
      <Modal.Header closeButton>
        <Modal.Title>
          <FaTrash className="me-2 text-danger" />
          {t('document.deleteDocument')}
        </Modal.Title>
      </Modal.Header>
      
      <Modal.Body>
        <p>
          <FaExclamationTriangle className="me-2 text-warning" />
          {t('document.deleteConfirmation')}
        </p>
        
        <p className="fw-bold mb-4">
          {documentTitle}
        </p>
        
        {!canDelete && (
          <Alert variant="warning">
            {t('document.permissionDenied')}
          </Alert>
        )}
        
        {error && (
          <Alert variant="danger">
            {error}
          </Alert>
        )}
      </Modal.Body>
      
      <Modal.Footer>
        <Button variant="secondary" onClick={onHide} disabled={isDeleting}>
          {t('document.cancel')}
        </Button>
        
        <Button 
          variant="danger" 
          onClick={handleDelete} 
          disabled={isDeleting || !canDelete}
        >
          {isDeleting ? (
            <>
              <Spinner animation="border" size="sm" className="me-2" />
              {t('common.processing')}
            </>
          ) : (
            <>
              <FaTrash className="me-2" />
              {t('document.delete')}
            </>
          )}
        </Button>
      </Modal.Footer>
    </Modal>
  );
};

export default DeleteDocumentModal;