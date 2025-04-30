// Last reviewed: 2025-04-30 12:17:45 UTC (User: Teeksssdevam et.)
import { 
  QueryClient, 
  QueryCache, 
  MutationCache,
  useQuery,
  useMutation,
  useQueryClient,
  UseQueryOptions,
  UseMutationOptions,
} from 'react-query';
import { api } from './api';
import { errorHandlingService } from './errorHandlingService';
import { analyticsService, EventCategory } from './analyticsService';

// QueryClient yapılandırması
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 dakika
      cacheTime: 1000 * 60 * 30, // 30 dakika
      retry: 2,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      refetchOnWindowFocus: process.env.NODE_ENV === 'production',
      refetchOnMount: true,
      refetchOnReconnect: true,
      suspense: false,
      useErrorBoundary: false,
      onError: (error: any) => {
        errorHandlingService.handleError({
          message: error?.message || 'An error occurred while fetching data',
          details: error
        });
      }
    },
    mutations: {
      retry: 1,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      onError: (error: any) => {
        errorHandlingService.handleError({
          message: error?.message || 'An error occurred while updating data',
          details: error
        });
      }
    }
  },
  queryCache: new QueryCache({
    onError: (error, query) => {
      // Global hata yakalama
      if (query.state.data !== undefined) {
        errorHandlingService.log('error', `Background query failed: ${error?.message}`, {
          queryKey: query.queryKey
        });
      }
    }
  }),
  mutationCache: new MutationCache({
    onError: (error, _variables, _context, mutation) => {
      // Global hata yakalama
      const mutationName = mutation.options.mutationKey || 'unknown';
      errorHandlingService.log('error', `Mutation failed: ${error?.message}`, {
        mutationName
      });
    }
  })
});

// Özel Query Hook'ları
export function useDocuments(filters?: Record<string, any>, options?: UseQueryOptions<any>) {
  return useQuery(
    ['documents', filters],
    () => api.get('/documents', { params: filters }),
    {
      select: (data) => data.data,
      onSuccess: (data) => {
        analyticsService.trackEvent({
          category: EventCategory.DOCUMENT,
          action: 'ListDocuments',
          label: `Filter: ${JSON.stringify(filters)}`,
          value: data.length
        });
      },
      ...options
    }
  );
}

export function useDocument(id?: string, options?: UseQueryOptions<any>) {
  return useQuery(
    ['document', id],
    () => api.get(`/documents/${id}`),
    {
      enabled: !!id,
      select: (data) => data.data,
      onSuccess: (data) => {
        analyticsService.trackEvent({
          category: EventCategory.DOCUMENT,
          action: 'ViewDocument',
          label: data.title,
          dimensions: {
            documentId: id,
            documentType: data.type
          }
        });
      },
      ...options
    }
  );
}

export function useDocumentHistory(id?: string, options?: UseQueryOptions<any>) {
  return useQuery(
    ['document-history', id],
    () => api.get(`/documents/${id}/history`),
    {
      enabled: !!id,
      select: (data) => data.data,
      ...options
    }
  );
}

export function useQueries(filters?: Record<string, any>, options?: UseQueryOptions<any>) {
  return useQuery(
    ['queries', filters],
    () => api.get('/queries', { params: filters }),
    {
      select: (data) => data.data,
      ...options
    }
  );
}

export function useQuery(id?: string, options?: UseQueryOptions<any>) {
  return useQuery(
    ['query', id],
    () => api.get(`/queries/${id}`),
    {
      enabled: !!id,
      select: (data) => data.data,
      ...options
    }
  );
}

export function useUsers(filters?: Record<string, any>, options?: UseQueryOptions<any>) {
  return useQuery(
    ['users', filters],
    () => api.get('/users', { params: filters }),
    {
      select: (data) => data.data,
      ...options
    }
  );
}

export function useUser(id?: string, options?: UseQueryOptions<any>) {
  return useQuery(
    ['user', id],
    () => api.get(`/users/${id}`),
    {
      enabled: !!id,
      select: (data) => data.data,
      ...options
    }
  );
}

export function useUserProfile(options?: UseQueryOptions<any>) {
  return useQuery(
    ['profile'],
    () => api.get('/profile'),
    {
      select: (data) => data.data,
      ...options
    }
  );
}

export function useStats(period?: string, options?: UseQueryOptions<any>) {
  return useQuery(
    ['stats', period],
    () => api.get('/stats', { params: { period } }),
    {
      select: (data) => data.data,
      ...options
    }
  );
}

export function useSystemSettings(options?: UseQueryOptions<any>) {
  return useQuery(
    ['system-settings'],
    () => api.get('/system/settings'),
    {
      select: (data) => data.data,
      ...options
    }
  );
}

// Mutasyon Hook'ları
export function useUploadDocument() {
  const queryClient = useQueryClient();
  
  return useMutation(
    (data: FormData) => api.post('/documents', data, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    }),
    {
      onSuccess: () => {
        // Belge listesini yeniden getir
        queryClient.invalidateQueries('documents');
        
        // Analitik
        analyticsService.trackEvent({
          category: EventCategory.DOCUMENT,
          action: 'UploadDocument',
          label: 'Success'
        });
      }
    }
  );
}

export function useUpdateDocument(id?: string) {
  const queryClient = useQueryClient();
  
  return useMutation(
    (data: any) => api.patch(`/documents/${id}`, data),
    {
      onSuccess: () => {
        // Belge ve belge listesini yeniden getir
        queryClient.invalidateQueries(['document', id]);
        queryClient.invalidateQueries('documents');
        
        // Analitik
        analyticsService.trackEvent({
          category: EventCategory.DOCUMENT,
          action: 'UpdateDocument',
          label: 'Success',
          dimensions: {
            documentId: id
          }
        });
      }
    }
  );
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  
  return useMutation(
    (id: string) => api.delete(`/documents/${id}`),
    {
      onSuccess: () => {
        // Belge listesini yeniden getir
        queryClient.invalidateQueries('documents');
        
        // Analitik
        analyticsService.trackEvent({
          category: EventCategory.DOCUMENT,
          action: 'DeleteDocument',
          label: 'Success'
        });
      }
    }
  );
}

export function useSubmitQuery() {
  const queryClient = useQueryClient();
  
  return useMutation(
    (data: any) => api.post('/queries', data),
    {
      onSuccess: () => {
        // Sorgu listesini yeniden getir
        queryClient.invalidateQueries('queries');
        
        // Analitik
        analyticsService.trackEvent({
          category: EventCategory.QUERY,
          action: 'SubmitQuery',
          label: 'Success',
          dimensions: {
            queryType: data.multimodal ? 'Multimodal' : 'Text'
          }
        });
      }
    }
  );
}

export function useUpdateUserProfile() {
  const queryClient = useQueryClient();
  
  return useMutation(
    (data: any) => api.patch('/profile', data),
    {
      onSuccess: () => {
        // Profil bilgisini yeniden getir
        queryClient.invalidateQueries('profile');
        
        // Analitik
        analyticsService.trackEvent({
          category: EventCategory.USER,
          action: 'UpdateProfile',
          label: 'Success'
        });
      }
    }
  );
}

export function useUpdateSystemSettings() {
  const queryClient = useQueryClient();
  
  return useMutation(
    (data: any) => api.patch('/system/settings', data),
    {
      onSuccess: () => {
        // Sistem ayarlarını yeniden getir
        queryClient.invalidateQueries('system-settings');
        
        // Analitik
        analyticsService.trackEvent({
          category: EventCategory.SYSTEM,
          action: 'UpdateSettings',
          label: 'Success'
        });
      }
    }
  );
}

// React Query Provider
import { QueryClientProvider } from 'react-query';
import { ReactQueryDevtools } from 'react-query/devtools';
import React from 'react';

export const QueryServiceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {process.env.NODE_ENV === 'development' && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  );
};