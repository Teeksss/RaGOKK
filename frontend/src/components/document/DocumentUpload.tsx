// Last reviewed: 2025-04-30 12:03:45 UTC (User: TeeksssBelgeleri)
import React, { useState, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { Form, Button, ProgressBar, Card, Alert } from 'react-bootstrap';
import { FaUpload, FaFileUpload, FaTimes, FaCheck, FaExclamationTriangle } from 'react-icons/fa';
import { useTranslation } from 'react-i18next';
import { errorHandlingService } from '../../services/errorHandlingService';
import { uploadDocument } from '../../services/documentService';
import { useAnalytics, EventCategory } from '../../services/analyticsService';
import { UploadDocumentParams, DocumentType } from '../../types/document.types';

// KB, MB, GB dönüşümleri
const KB = 1024;
const MB = KB * 1024;
const GB = MB * 1024;

// Dosya yükleme parametreleri
interface DocumentUploadProps {
  onUploadComplete?: (documentId: string) => void;
  onUploadStart?: () => void;
  onUploadError?: (error: Error) => void;
  maxFileSize?: number; // Bayt cinsinden
  allowedFileTypes?: string[];
  defaultTitle?: string;
  defaultTags?: string[];
  defaultFolderId?: string;
  showMetadataForm?: boolean;
  multipleFiles?: boolean;
  autoUpload?: boolean;
}

const DocumentUpload: React.FC<DocumentUploadProps> = ({
  onUploadComplete,
  onUploadStart,
  onUploadError,
  maxFileSize = 50 * MB, // Varsayılan 50MB
  allowedFileTypes = [
    'application/pdf', 
    'application/msword', 
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'text/csv',
    'application/json',
    'application/xml',
    'text/html',
    'text/markdown',
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp'
  ],
  defaultTitle = '',
  defaultTags = [],
  defaultFolderId,
  showMetadataForm = true,
  multipleFiles = false,
  autoUpload = false,
}) => {
  const { t } = useTranslation();
  const { trackEvent } = useAnalytics();
  
  // Dosya durum izleme
  const [files, setFiles] = useState<File[]>([]);
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({});
  const [uploadStatus, setUploadStatus] = useState<Record<string, 'pending' | 'uploading' | 'success' | 'error'>>({});
  const [uploadErrors, setUploadErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Form durum izleme
  const [title, setTitle] = useState(defaultTitle);
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState<string[]>(defaultTags);
  const [folderId, setFolderId] = useState(defaultFolderId);
  
  // Dosya doğrulama hataları
  const [fileValidationErrors, setFileValidationErrors] = useState<Record<string, string[]>>({});
  
  // Dosya doğrulama fonksiyonu
  const validateFile = (file: File): string[] => {
    const errors: string[] = [];
    
    // Dosya boyutu kontrolü
    if (file.size > maxFileSize) {
      errors.push(
        t('documents.upload.errors.fileSize', {
          max: maxFileSize < MB 
            ? t('common.sizeKB', { size: Math.round(maxFileSize / KB) })
            : t('common.sizeMB', { size: (maxFileSize / MB).toFixed(1) })
        })
      );
    }
    
    // Dosya tipi kontrolü
    if (!allowedFileTypes.includes(file.type)) {
      errors.push(t('documents.upload.errors.fileType'));
    }
    
    // Dosya uzantı kontrolü
    const extension = file.name.split('.').pop()?.toLowerCase();
    const allowedExtensions = [
      'pdf', 'doc', 'docx', 'txt', 'xls', 'xlsx', 'ppt', 'pptx', 
      'csv', 'json', 'xml', 'html', 'md', 'rtf', 'jpg', 'jpeg', 
      'png', 'gif', 'webp'
    ];
    
    if (extension && !allowedExtensions.includes(extension)) {
      errors.push(t('documents.upload.errors.fileExtension'));
    }
    
    // OCR'a uygunluk kontrolü
    if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(extension || '')) {
      // Görüntü dosyaları için boyut kontrolü (çok büyük görüntüler için uyarı)
      if (file.size > 20 * MB) {
        errors.push(t('documents.upload.errors.imageTooLarge'));
      }
    }
    
    return errors;
  };
  
  // Dropzone konfigürasyonu
  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
    // Kabul edilen dosyaları ekle
    const newValidationErrors: Record<string, string[]> = {};
    const newFiles = acceptedFiles.filter(file => {
      // Dosyayı doğrula
      const validationErrors = validateFile(file);
      if (validationErrors.length > 0) {
        newValidationErrors[file.name] = validationErrors;
        return false;
      }
      return true;
    });
    
    // Reddedilen dosyaları işle
    rejectedFiles.forEach(rejected => {
      newValidationErrors[rejected.file.name] = rejected.errors.map((err: any) => err.message);
    });
    
    // Tek dosya modu için, yeni dosya eski dosyanın yerini alır
    if (!multipleFiles) {
      setFiles(newFiles.slice(0, 1));
      
      // Eski dosya durumlarını temizle
      setUploadProgress({});
      setUploadStatus({});
      setUploadErrors({});
    } else {
      // Çoklu dosya modu için, yeni dosyaları ekle
      setFiles(prevFiles => [...prevFiles, ...newFiles]);
    }
    
    // Validasyon hatalarını güncelle
    setFileValidationErrors(newValidationErrors);
    
    // Otomatik yükleme modunda ve geçerli dosyalar varsa yüklemeyi başlat
    if (autoUpload && newFiles.length > 0) {
      handleUpload(newFiles);
    }
    
    // Analitik izleme
    trackEvent({
      category: EventCategory.DOCUMENT,
      action: 'FilesSelected',
      label: `Count: ${newFiles.length}`,
      value: newFiles.reduce((total, file) => total + file.size, 0)
    });
  }, [multipleFiles, autoUpload, validateFile, trackEvent]);
  
  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
      'application/vnd.ms-excel': ['.xls'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-powerpoint': ['.ppt'],
      'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
      'text/csv': ['.csv'],
      'application/json': ['.json'],
      'application/xml': ['.xml'],
      'text/html': ['.html'],
      'text/markdown': ['.md'],
      'application/rtf': ['.rtf'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
      'image/gif': ['.gif'],
      'image/webp': ['.webp']
    },
    multiple: multipleFiles,
    maxSize: maxFileSize
  });
  
  // Dosya kaldırma
  const handleRemoveFile = (index: number) => {
    setFiles(prev => {
      const newFiles = [...prev];
      const removedFile = newFiles.splice(index, 1)[0];
      
      // Dosya durumlarını temizle
      setUploadProgress(prev => {
        const newProgress = { ...prev };
        delete newProgress[removedFile.name];
        return newProgress;
      });
      
      setUploadStatus(prev => {
        const newStatus = { ...prev };
        delete newStatus[removedFile.name];
        return newStatus;
      });
      
      setUploadErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[removedFile.name];
        return newErrors;
      });
      
      setFileValidationErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[removedFile.name];
        return newErrors;