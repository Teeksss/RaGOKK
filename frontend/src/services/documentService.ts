// Last reviewed: 2025-04-30 12:03:45 UTC (User: TeeksssBelgeleri)

/**
 * Belgeleri listeleme API çağrısı
 * @param params Listeleme parametreleri
 * @returns API yanıtı
 */
export const listDocuments = async (params: ListDocumentsParams): Promise<ListDocumentsResponse> => {
  const queryParams = new URLSearchParams();
  
  // Sayfalama
  if (params.page) queryParams.append('page', params.page.toString());
  if (params.perPage) queryParams.append('per_page', params.perPage.toString());
  
  // Sıralama
  if (params.sortBy) queryParams.append('sort', params.sortBy);
  if (params.sortDirection) queryParams.append('order', params.sortDirection);
  
  // Filtreleme
  if (params.searchQuery) queryParams.append('query', params.searchQuery);
  if (params.documentTypes && params.documentTypes.length > 0) {
    queryParams.append('type', params.documentTypes.join(','));
  }
  if (params.tags && params.tags.length > 0) {
    queryParams.append('tags', params.tags.join(','));
  }
  if (params.owner) queryParams.append('owner', params.owner);
  if (params.createdAfter) queryParams.append('created_after', params.createdAfter.toISOString());
  if (params.createdBefore) queryParams.append('created_before', params.createdBefore.toISOString());
  if (params.isIndexed !== undefined) queryParams.append('is_indexed', params.isIndexed.toString());
  if (params.folderId) queryParams.append('folder_id', params.folderId);
  
  // API çağrısı
  try {
    const response = await api.get<ListDocumentsResponse>(`/documents?${queryParams.toString()}`);
    return response.data;
  } catch (error) {
    errorHandlingService.handleError({
      message: 'Belgeler listelenirken bir hata oluştu',
      details: error
    });
    throw error;
  }
};

/**
 * Belge silme API çağrısı
 * @param documentId Silinecek belgenin ID'si
 * @returns API yanıtı
 */
export const deleteDocument = async (documentId: string): Promise<DeleteDocumentResponse> => {
  try {
    const response = await api.delete<DeleteDocumentResponse>(`/documents/${documentId}`);
    return response.data;
  } catch (error) {
    errorHandlingService.handleError({
      message: 'Belge silinirken bir hata oluştu',
      details: error
    });
    throw error;
  }
};

/**
 * Belge önizleme API çağrısı
 * @param documentId Önizlenecek belgenin ID'si
 * @param params Önizleme parametreleri
 * @returns API yanıtı
 */
export const getDocumentPreview = async (
  documentId: string, 
  params: DocumentPreviewParams = {}
): Promise<DocumentPreviewResponse> => {
  const queryParams = new URLSearchParams();
  
  // Sayfa parametresi
  if (params.page) queryParams.append('page', params.page.toString());
  
  // Format parametresi
  if (params.format) queryParams.append('format', params.format);
  
  // Çözünürlük parametresi
  if (params.resolution) queryParams.append('resolution', params.resolution);
  
  try {
    const response = await api.get<DocumentPreviewResponse>(
      `/documents/${documentId}/preview?${queryParams.toString()}`
    );
    return response.data;
  } catch (error) {
    errorHandlingService.handleError({
      message: 'Belge önizlemesi alınırken bir hata oluştu',
      details: error
    });
    throw error;
  }
};

/**
 * Belge indirme URL'si oluşturma
 * @param documentId İndirilecek belgenin ID'si
 * @returns İndirme URL'si
 */
export const getDocumentDownloadUrl = (documentId: string): string => {
  return `${api.defaults.baseURL}/documents/${documentId}/download?token=${getAuthToken()}`;
};