// Last reviewed: 2025-04-29 12:43:06 UTC (User: TeeksssKullanıcı Davranışları İzleme)
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  Card, Button, ProgressBar, Alert, Row, Col, Form, Badge, Spinner
} from 'react-bootstrap';
import { FileIcon } from './FileIcon';
import { useDropzone } from 'react-dropzone';
import { useToast } from '../contexts/ToastContext';
import { TagsInput } from './TagsInput';
import { apiRequest } from '../utils/api';
import { formatFileSize, getFileTypeIcon } from '../utils/fileUtils';
import '../styles/AdvancedUploader.css';

interface FilePreview {
  file: File;
  id: string;
  progress: number;
  status: 'idle' | 'uploading' | 'success' | 'error' | 'canceled';
  error?: string;
  preview?: string;
  type: string;
  size: string;
  uploadStartTime?: number;
  estimatedTimeRemaining?: number;
  documentId?: number;
}

interface UploadResponse {
  document_id: number;
  success: boolean;
  title: string;
  is_processed: boolean;
}

interface AdvancedUploaderProps {
  onUploaded?: (documentIds: number[]) => void;
  onCancel?: () => void;
  maxFiles?: number;
  maxFileSize?: number; // in bytes
  allowMultiple?: boolean;
  acceptedFileTypes?: string[];
  defaultTags?: string[];
  onError?: (message: string) => void;
}

export const AdvancedUploader: React.FC<AdvancedUploaderProps> = ({
  onUploaded,
  onCancel,
  maxFiles = 10,
  maxFileSize = 100 * 1024 * 1024, // 100 MB
  allowMultiple = true,
  acceptedFileTypes = [
    'application/pdf', 
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain', 
    'text/html', 
    'application/xml',
    'application/json',
    'text/csv',
    'image/jpeg',
    'image/png',
    'image/tiff'
  ],
  defaultTags = [],
  onError
}) => {
  const [files, setFiles] = useState<FilePreview[]>([]);
  const [commonTags, setCommonTags] = useState<string[]>(defaultTags);
  const [isPublic, setIsPublic] = useState<boolean>(false);
  const [autoProcess, setAutoProcess] = useState<boolean>(true);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [globalError, setGlobalError] = useState<string | null>(null);
  const abortControllers = useRef<Map<string, AbortController>>(new Map());
  const { showToast } = useToast();

  // Dosya sürükle-bırak için React-Dropzone
  const onDrop = useCallback((acceptedFiles: File[]) => {
    // Zaten yükleme yapılıyorsa yeni dosyaları kabul etme
    if (isUploading) {
      showToast('Şu anda yükleme yapılıyor, lütfen bekleyin.', 'warning');
      return;
    }

    // Maksimum dosya sayısı kontrolü
    if (files.length + acceptedFiles.length > maxFiles) {
      showToast(`En fazla ${maxFiles} dosya yükleyebilirsiniz.`, 'warning');
      return;
    }
    
    // Dosyaları işle
    const newFiles = acceptedFiles.map(file => {
      // Dosya boyutu kontrolü
      if (file.size > maxFileSize) {
        showToast(`"${file.name}" dosyası çok büyük (maksimum ${formatFileSize(maxFileSize)}).`, 'error');
        return null;
      }

      // Önizleme URL'si oluştur
      let preview: string | undefined = undefined;
      if (file.type.startsWith('image/')) {
        preview = URL.createObjectURL(file);
      }
      
      // Dosya adından başlık önerisi oluştur
      let suggestedTitle = file.name.split('.').slice(0, -1).join('.');
      
      return {
        file,
        id: `file-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        progress: 0,
        status: 'idle' as const,
        preview,
        type: file.type,
        size: formatFileSize(file.size),
        title: suggestedTitle
      };
    }).filter(Boolean) as FilePreview[];
    
    setFiles(prev => [...prev, ...newFiles]);
  }, [files.length, isUploading, maxFileSize, maxFiles, showToast]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: acceptedFileTypes.reduce((acc, type) => {
      acc[type] = [];
      return acc;
    }, {} as Record<string, string[]>),
    maxFiles: maxFiles - files.length,
    disabled: isUploading || files.length >= maxFiles,
    multiple: allowMultiple
  });
  
  // Dosya kaldırma
  const removeFile = useCallback((fileId: string) => {
    setFiles(prevFiles => prevFiles.filter(file => file.id !== fileId));
    
    // Eğer AbortController varsa, yüklemeyi iptal et
    if (abortControllers.current.has(fileId)) {
      abortControllers.current.get(fileId)?.abort();
      abortControllers.current.delete(fileId);
    }
  }, []);
  
  // Tüm dosyaları temizle
  const clearAllFiles = useCallback(() => {
    // Devam eden yüklemeleri iptal et
    files.forEach(file => {
      if (file.status === 'uploading' && abortControllers.current.has(file.id)) {
        abortControllers.current.get(file.id)?.abort();
      }
    });
    
    abortControllers.current.clear();
    setFiles([]);
  }, [files]);
  
  // Başlık güncelleme
  const updateFileTitle = useCallback((fileId: string, title: string) => {
    setFiles(prevFiles => 
      prevFiles.map(file => 
        file.id === fileId ? { ...file, title } : file
      )
    );
  }, []);
  
  // Dosya etiketlerini güncelleme
  const updateFileTags = useCallback((fileId: string, tags: string[]) => {
    setFiles(prevFiles => 
      prevFiles.map(file => 
        file.id === fileId ? { ...file, tags } : file
      )
    );
  }, []);
  
  // Tek dosya yükleme
  const uploadFile = async (file: FilePreview): Promise<boolean> => {
    try {
      // Dosyanın durumunu güncelle
      setFiles(prevFiles => 
        prevFiles.map(f => 
          f.id === file.id ? { ...f, status: 'uploading', progress: 0, uploadStartTime: Date.now() } : f
        )
      );
      
      // FormData oluştur
      const formData = new FormData();
      formData.append('file', file.file);
      formData.append('title', file.title || file.file.name.split('.')[0]);
      
      if (file.tags) {
        formData.append('tags', JSON.stringify(file.tags));
      } else if (commonTags.length > 0) {
        formData.append('tags', JSON.stringify(commonTags));
      }
      
      formData.append('is_public', String(isPublic));
      formData.append('auto_process', String(autoProcess));
      
      // Yükleme için AbortController oluştur
      const abortController = new AbortController();
      abortControllers.current.set(file.id, abortController);
      
      // Yükleme yap
      const response = await apiRequest<UploadResponse>('/api/documents/upload', {
        method: 'POST',
        body: formData,
        includeAuth: true,
        signal: abortController.signal,
        onProgress: (progress) => {
          // İlerleme durumunu ve tahmini kalan süreyi güncelle
          const now = Date.now();
          const elapsedMs = now - (file.uploadStartTime || now);
          let estimatedTimeRemaining;
          
          if (progress > 0 && elapsedMs > 0) {
            // Tahmini kalan süreyi hesapla (ms cinsinden)
            estimatedTimeRemaining = elapsedMs * ((100 - progress) / progress);
          }
          
          setFiles(prevFiles => 
            prevFiles.map(f => 
              f.id === file.id ? { 
                ...f, 
                progress, 
                estimatedTimeRemaining 
              } : f
            )
          );
        }
      });
      
      // AbortController'ı temizle
      abortControllers.current.delete(file.id);
      
      if (response.success && response.document_id) {
        // Başarılı yükleme
        setFiles(prevFiles => 
          prevFiles.map(f => 
            f.id === file.id ? { 
              ...f, 
              status: 'success', 
              progress: 100,
              documentId: response.document_id
            } : f
          )
        );
        
        showToast(`"${file.file.name}" başarıyla yüklendi.`, 'success');
        return true;
      } else {
        throw new Error('Doküman ID alınamadı');
      }
    } catch (err: any) {
      // İptal edildi mi?
      if (err.name === 'AbortError') {
        setFiles(prevFiles => 
          prevFiles.map(f => 
            f.id === file.id ? { ...f, status: 'canceled', progress: 0 } : f
          )
        );
        return false;
      }
      
      // Diğer hatalar
      const errorMessage = err.message || 'Bilinmeyen hata';
      setFiles(prevFiles => 
        prevFiles.map(f => 
          f.id === file.id ? { ...f, status: 'error', error: errorMessage } : f
        )
      );
      
      showToast(`"${file.file.name}" yüklenemedi: ${errorMessage}`, 'error');
      return false;
    }
  };
  
  // Tüm dosyaları yükle
  const uploadAllFiles = async () => {
    // Hiç dosya yoksa hata göster
    if (files.length === 0) {
      setGlobalError('Lütfen en az bir dosya seçin.');
      return;
    }
    
    // Yükleme durumunda değilsek başlat
    if (!isUploading) {
      setIsUploading(true);
      setGlobalError(null);
      
      let successCount = 0;
      let failCount = 0;
      let documentIds: number[] = [];
      
      // Her dosyayı sırayla yükle
      for (const file of files) {
        // Sadece idle veya error durumundaki dosyaları yükle
        if (file.status === 'idle' || file.status === 'error') {
          const success = await uploadFile(file);
          
          if (success) {
            successCount++;
            if (file.documentId) documentIds.push(file.documentId);
          } else {
            failCount++;
          }
        } else if (file.status === 'success' && file.documentId) {
          // Zaten başarılı yüklenmiş
          successCount++;
          documentIds.push(file.documentId);
        }
      }
      
      setIsUploading(false);
      
      // Sonucu bildir
      if (successCount > 0) {
        showToast(`${successCount} dosya başarıyla yüklendi.`, 'success');
        
        // Başarılı yükleme callback'ini çağır
        if (onUploaded) {
          onUploaded(documentIds);
        }
      }
      
      if (failCount > 0) {
        showToast(`${failCount} dosya yüklenemedi.`, 'error');
      }
    }
  };
  
  // Component temizliği
  useEffect(() => {
    // Önizleme URL'lerini temizle
    return () => {
      files.forEach(file => {
        if (file.preview) {
          URL.revokeObjectURL(file.preview);
        }
      });
      
      // Devam eden yüklemel