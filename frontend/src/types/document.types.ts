// Last reviewed: 2025-04-30 12:03:45 UTC (User: TeeksssBelgeleri)

// Belge Tipi
export type DocumentType = 'pdf' | 'docx' | 'doc' | 'txt' | 'xlsx' | 'xls' | 'pptx' | 'ppt' | 'csv' | 'json' | 'xml' | 'html' | 'md' | 'rtf' | 'image' | 'other';

// Belge Durumu
export type DocumentStatus = 'processing' | 'indexed' | 'failed' | 'pending' | 'deleted';

// Belge Listesi Parametreleri
export interface ListDocumentsParams {
  page?: number;
  perPage?: number;
  sortBy?: string;
  sortDirection?: 'asc' | 'desc';
  searchQuery?: string;
  documentTypes?: DocumentType[];
  tags?: string[];
  owner?: string;
  createdAfter?: Date;
  createdBefore?: Date;
  isIndexed?: boolean;
  folderId?: string;
}

// Belge Yanıtı
export interface Document {
  id: string;
  title: string;
  description?: string;
  type: DocumentType;
  size: number;
  pages?: number;
  contentHash?: string;
  owner: {
    id: string;
    name: string;
    email?: string;
    avatar?: string;
  };
  tags: string[];
  createdAt: string;
  updatedAt: string;
  isIndexed: boolean;
  indexingStatus?: DocumentStatus;
  storageLocation?: string;
  thumbnailUrl?: string;
  downloadUrl?: string;
  previewUrl?: string;
  folder?: {
    id: string;
    name: string;
  };
  accessLevel?: 'private' | 'shared' | 'public';
  sharedWith?: {
    users?: {
      id: string;
      name: string;
      email: string;
      avatar?: string;
    }[];
    groups?: {
      id: string;
      name: string;
    }[];
  };
  metadata?: Record<string, any>;
}

// Belge Listesi Yanıtı
export interface ListDocumentsResponse {
  data: Document[];
  meta: {
    pagination: {
      total: number;
      perPage: number;
      currentPage: number;
      totalPages: number;
      nextPage: number | null;
      prevPage: number | null;
    };
    filters?: {
      appliedFilters: Record<string, any>;
      availableFilters: {
        documentTypes: DocumentType[];
        tags: string[];
        owners: {
          id: string;
          name: string;
        }[];
      };
    };
  };
}

// Belge Silme Yanıtı
export interface DeleteDocumentResponse {
  success: boolean;
  message: string;
  documentId?: string;
}

// Belge Önizleme Parametreleri
export interface DocumentPreviewParams {
  page?: number;
  format?: 'html' | 'image' | 'text';
  resolution?: 'low' | 'medium' | 'high';
}

// Belge Önizleme Yanıtı
export interface DocumentPreviewResponse {
  documentId: string;
  page: number;
  totalPages: number;
  format: 'html' | 'image' | 'text';
  content: string; // HTML içeriği veya Base64 kodlu görüntü
  textContent?: string; // Format 'image' olduğunda, sayfanın metin içeriği (OCR)
  mimeType?: string;
  width?: number;
  height?: number;
  ocrConfidence?: number;
}

// Belge Yükleme Parametreleri
export interface UploadDocumentParams {
  file: File;
  title?: string;
  description?: string;
  tags?: string[];
  folderId?: string;
  accessLevel?: 'private' | 'shared' | 'public';
  shareWithUserIds?: string[];
  shareWithGroupIds?: string[];
  indexImmediately?: boolean;
  customMetadata?: Record<string, any>;
}

// Belge Yükleme Yanıtı
export interface UploadDocumentResponse {
  documentId: string;
  uploadStatus: 'success' | 'partial' | 'failed';
  message?: string;
  document: Document;
  processingStatus?: {
    status: DocumentStatus;
    message?: string;
    estimatedTimeSeconds?: number;
  };
}