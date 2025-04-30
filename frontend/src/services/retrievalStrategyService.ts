// Last reviewed: 2025-04-30 12:48:55 UTC (User: TeeksssLLM)
import { api } from './api';
import { errorHandlingService } from './errorHandlingService';
import { useQuery, useMutation } from 'react-query';
import { queryClient } from './queryService';
import { useEffect } from 'react';
import { useUserPreferences } from '../contexts/GlobalStateContext';

// Retrieval stratejisi tipi
export interface RetrievalStrategy {
  id: string;
  name: string;
  description: string;
  configuration: RetrievalConfig;
  isDefault?: boolean;
  createdAt: string;
  updatedAt: string;
}

// Retrieval yapılandırması
export interface RetrievalConfig {
  top_k: number;
  min_score: number;
  use_reranker: boolean;
  reranker_top_k?: number;
  reranker_threshold?: number;
  query_expansion_method?: 'none' | 'wordnet' | 'conceptnet' | 'gpt' | 'hybrid';
  query_expansion_depth?: number;
  multi_query_variants?: boolean;
  multi_query_count?: number;
  fallback_strategies?: {
    min_results_threshold: number;  // En az bu kadar sonuç bulunamazsa fallback stratejiye geçilir
    relaxation_steps: Array<{
      min_score: number;  // min_score'u kademeli olarak düşür
      top_k: number;      // top_k'yı kademeli olarak artır
    }>;
    use_keyword_search_fallback: boolean;
  };
}

// Öntanımlı retrieval yapılandırması
export const DEFAULT_RETRIEVAL_CONFIG: RetrievalConfig = {
  top_k: 5,
  min_score: 0.7,
  use_reranker: true,
  reranker_top_k: 10,
  reranker_threshold: 0.5,
  query_expansion_method: 'none',
  query_expansion_depth: 1,
  multi_query_variants: false,
  multi_query_count: 3,
  fallback_strategies: {
    min_results_threshold: 2,
    relaxation_steps: [
      { min_score: 0.5, top_k: 10 },
      { min_score: 0.3, top_k: 20 }
    ],
    use_keyword_search_fallback: true
  }
};

// Yeni retrieval stratejisi oluşturma için tip
export interface CreateRetrievalStrategyInput {
  name: string;
  description: string;
  configuration: Partial<RetrievalConfig>;
  isDefault?: boolean;
}

// Retrieval stratejisi güncelleme için tip
export type UpdateRetrievalStrategyInput = Partial<CreateRetrievalStrategyInput>;

// Retrieval strategy service
export class RetrievalStrategyService {
  // Retrieval stratejilerini getir
  static async getRetrievalStrategies(): Promise<RetrievalStrategy[]> {
    try {
      const response = await api.get('/retrieval-strategies');
      return response.data;
    } catch (error) {
      errorHandlingService.handleError({
        message: 'Failed to load retrieval strategies',
        details: error
      });
      throw error;
    }
  }
  
  // Varsayılan retrieval stratejisini getir
  static async getDefaultRetrievalStrategy(): Promise<RetrievalStrategy> {
    try {
      const response = await api.get('/retrieval-strategies/default');
      return response.data;
    } catch (error) {
      errorHandlingService.handleError({
        message: 'Failed to load default retrieval strategy',
        details: error
      });
      
      // API başarısız olursa default config ile bir strateji döndür
      return {
        id: 'default',
        name: 'Default Strategy',
        description: 'System default retrieval strategy',
        configuration: DEFAULT_RETRIEVAL_CONFIG,
        isDefault: true,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      };
    }
  }
  
  // Belirli bir retrieval stratejisini getir
  static async getRetrievalStrategy(id: string): Promise<RetrievalStrategy> {
    try {
      const response = await api.get(`/retrieval-strategies/${id}`);
      return response.data;
    } catch (error) {
      errorHandlingService.handleError({
        message: 'Failed to load retrieval strategy',
        details: error
      });
      throw error;
    }
  }
  
  // Yeni retrieval stratejisi oluştur
  static async createRetrievalStrategy(data: CreateRetrievalStrategyInput): Promise<RetrievalStrategy> {
    try {
      // Eksik alanları varsayılan değerlerle doldur
      const config = {
        ...DEFAULT_RETRIEVAL_CONFIG,
        ...data.configuration
      };
      
      const response = await api.post('/retrieval-strategies', {
        ...data,
        configuration: config
      });
      
      return response.data;
    } catch (error) {
      errorHandlingService.handleError({
        message: 'Failed to create retrieval strategy',
        details: error
      });
      throw error;
    }
  }
  
  // Retrieval stratejisi güncelle
  static async updateRetrievalStrategy(id: string, data: UpdateRetrievalStrategyInput): Promise<RetrievalStrategy> {
    try {
      // Konfigürasyon varsa, sadece belirtilen alanları güncelle
      if (data.configuration) {
        // Önce mevcut stratejiyi getir
        const currentStrategy = await this.getRetrievalStrategy(id);
        
        // Mevcut konfigürasyonu yeni ayarlarla birleştir
        data.configuration = {
          ...currentStrategy.configuration,
          ...data.configuration
        };
      }
      
      const response = await api.patch(`/retrieval-strategies/${id}`, data);
      return response.data;
    } catch (error) {
      errorHandlingService.handleError({
        message: 'Failed to update retrieval strategy',
        details: error
      });
      throw error;
    }
  }
  
  // Retrieval stratejisi sil
  static async deleteRetrievalStrategy(id: string): Promise<void> {
    try {
      await api.delete(`/retrieval-strategies/${id}`);
    } catch (error) {
      errorHandlingService.handleError({
        message: 'Failed to delete retrieval strategy',
        details: error
      });
      throw error;
    }
  }
  
  // Varsayılan retrieval stratejisi olarak ayarla
  static async setDefaultRetrievalStrategy(id: string): Promise<RetrievalStrategy> {
    try {
      const response = await api.post(`/retrieval-strategies/${id}/set-default`);
      return response.data;
    } catch (error) {
      errorHandlingService.handleError({
        message: 'Failed to set default retrieval strategy',
        details: error
      });
      throw error;
    }
  }
}

// React Query Hooks

// Tüm retrieval stratejileri için hook
export function useRetrievalStrategies() {
  return useQuery(
    ['retrievalStrategies'],
    () => RetrievalStrategyService.getRetrievalStrategies(),
    {
      staleTime: 5 * 60 * 1000, // 5 dakika
    }
  );
}

// Varsayılan retrieval stratejisi için hook
export function useDefaultRetrievalStrategy() {
  return useQuery(
    ['retrievalStrategy', 'default'],
    () => RetrievalStrategyService.getDefaultRetrievalStrategy(),
    {
      staleTime: 5 * 60 * 1000, // 5 dakika
      refetchOnWindowFocus: false,
    }
  );
}

// Belirli bir retrieval stratejisi için hook
export function useRetrievalStrategy(id: string | undefined) {
  return useQuery(
    ['retrievalStrategy', id],
    () => RetrievalStrategyService.getRetrievalStrategy(id!),
    {
      enabled: !!id,
      staleTime: 5 * 60 * 1000, // 5 dakika
    }
  );
}

// Retrieval stratejisi oluşturma hook'u
export function useCreateRetrievalStrategy() {
  return useMutation(
    (data: CreateRetrievalStrategyInput) => RetrievalStrategyService.createRetrievalStrategy(data),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('retrievalStrategies');
      }
    }
  );
}

// Retrieval stratejisi güncelleme hook'u
export function useUpdateRetrievalStrategy() {
  return useMutation(
    ({ id, data }: { id: string; data: UpdateRetrievalStrategyInput }) => 
      RetrievalStrategyService.updateRetrievalStrategy(id, data),
    {
      onSuccess: (_, { id }) => {
        queryClient.invalidateQueries('retrievalStrategies');
        queryClient.invalidateQueries(['retrievalStrategy', id]);
        
        // Varsayılan strateji değiştiyse, o da yenilensin
        queryClient.invalidateQueries(['retrievalStrategy', 'default']);
      }
    }
  );
}

// Retrieval stratejisi silme hook'u
export function useDeleteRetrievalStrategy() {
  return useMutation(
    (id: string) => RetrievalStrategyService.deleteRetrievalStrategy(id),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('retrievalStrategies');
        // Varsayılan strateji değiştiyse, o da yenilensin
        queryClient.invalidateQueries(['retrievalStrategy', 'default']);
      }
    }
  );
}

// Varsayılan retrieval stratejisi ayarlama hook'u
export function useSetDefaultRetrievalStrategy() {
  return useMutation(
    (id: string) => RetrievalStrategyService.setDefaultRetrievalStrategy(id),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('retrievalStrategies');
        // Varsayılan strateji değişti, yenileyelim
        queryClient.invalidateQueries(['retrievalStrategy', 'default']);
      }
    }
  );
}

// Kullanıcının tercih ettiği retrieval stratejisini tutan hook
export function useUserRetrievalStrategy() {
  const { userPreferences, updateUserPreferences } = useUserPreferences();
  const { data: defaultStrategy, isLoading } = useDefaultRetrievalStrategy();
  
  // Kullanıcı tercihi olarak kaydedilen veya varsayılan strateji ID'si
  const strategyId = userPreferences.preferredRetrievalStrategyId || 'default';
  
  // Eğer kullanıcı varsayılan stratejiyi tercih ediyorsa, direkt defaultStrategy'yi kullan
  const { data: userStrategy } = useRetrievalStrategy(
    strategyId !== 'default' ? strategyId : undefined
  );
  
  // strategyId 'default' ise defaultStrategy'yi kullan, değilse userStrategy'yi
  const strategy = strategyId === 'default' ? defaultStrategy : userStrategy;
  
  // Kullanıcı stratejisini değiştir
  const setUserStrategy = (id: string) => {
    updateUserPreferences({
      preferredRetrievalStrategyId: id
    });
  };
  
  // Varsayılan strateji değiştiğinde ve kullanıcı stratejisi yoksa, güncelle
  useEffect(() => {
    if (!isLoading && defaultStrategy && !userPreferences.preferredRetrievalStrategyId) {
      updateUserPreferences({
        preferredRetrievalStrategyId: 'default'
      });
    }
  }, [defaultStrategy, isLoading, userPreferences.preferredRetrievalStrategyId, updateUserPreferences]);
  
  return {
    strategy,
    strategyId,
    setUserStrategy,
    isLoading: isLoading || (strategyId !== 'default' && !userStrategy)
  };
}

// Default export (statik sınıf metotları için erişim kolaylığı)
export default RetrievalStrategyService;