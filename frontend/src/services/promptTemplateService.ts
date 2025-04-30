// Last reviewed: 2025-04-30 12:48:55 UTC (User: TeeksssLLM)
import { api } from './api';
import { errorHandlingService } from './errorHandlingService';
import { useQuery, useMutation } from 'react-query';
import { queryClient } from './queryService';

// Prompt şablonu için tip tanımı
export interface PromptTemplate {
  id: string;
  name: string;
  description: string;
  systemPrompt: string;
  userPrompt: string;
  variables: string[];
  category: string;
  isDefault?: boolean;
  createdAt: string;
  updatedAt: string;
  createdBy?: {
    id: string;
    name: string;
  };
}

// Yeni prompt şablonu oluşturma için tip
export interface CreatePromptTemplateInput {
  name: string;
  description: string;
  systemPrompt: string;
  userPrompt: string;
  category: string;
  isDefault?: boolean;
}

// Prompt şablonu güncelleme için tip
export type UpdatePromptTemplateInput = Partial<CreatePromptTemplateInput>;

// Prompt şablonları için filtre
export interface PromptTemplateFilter {
  category?: string;
  query?: string;
  isDefault?: boolean;
}

// Prompt template service
export class PromptTemplateService {
  // Prompt şablonları getir
  static async getPromptTemplates(filters?: PromptTemplateFilter): Promise<PromptTemplate[]> {
    try {
      const response = await api.get('/prompt-templates', {
        params: filters
      });
      return response.data;
    } catch (error) {
      errorHandlingService.handleError({
        message: 'Failed to load prompt templates',
        details: error
      });
      throw error;
    }
  }
  
  // Prompt şablonu getir
  static async getPromptTemplate(id: string): Promise<PromptTemplate> {
    try {
      const response = await api.get(`/prompt-templates/${id}`);
      return response.data;
    } catch (error) {
      errorHandlingService.handleError({
        message: 'Failed to load prompt template',
        details: error
      });
      throw error;
    }
  }
  
  // Yeni prompt şablonu oluştur
  static async createPromptTemplate(data: CreatePromptTemplateInput): Promise<PromptTemplate> {
    try {
      const response = await api.post('/prompt-templates', data);
      return response.data;
    } catch (error) {
      errorHandlingService.handleError({
        message: 'Failed to create prompt template',
        details: error
      });
      throw error;
    }
  }
  
  // Prompt şablonu güncelle
  static async updatePromptTemplate(id: string, data: UpdatePromptTemplateInput): Promise<PromptTemplate> {
    try {
      const response = await api.patch(`/prompt-templates/${id}`, data);
      return response.data;
    } catch (error) {
      errorHandlingService.handleError({
        message: 'Failed to update prompt template',
        details: error
      });
      throw error;
    }
  }
  
  // Prompt şablonu sil
  static async deletePromptTemplate(id: string): Promise<void> {
    try {
      await api.delete(`/prompt-templates/${id}`);
    } catch (error) {
      errorHandlingService.handleError({
        message: 'Failed to delete prompt template',
        details: error
      });
      throw error;
    }
  }
  
  // Varsayılan prompt şablonunu ayarla
  static async setDefaultPromptTemplate(id: string): Promise<PromptTemplate> {
    try {
      const response = await api.post(`/prompt-templates/${id}/set-default`);
      return response.data;
    } catch (error) {
      errorHandlingService.handleError({
        message: 'Failed to set default prompt template',
        details: error
      });
      throw error;
    }
  }
  
  // Prompt şablonundan dinamik değişken çıkarma
  static extractVariables(template: string): string[] {
    const variableRegex = /\{\{(.*?)\}\}/g;
    const variables: string[] = [];
    let match;
    
    while ((match = variableRegex.exec(template)) !== null) {
      const variable = match[1].trim();
      if (!variables.includes(variable)) {
        variables.push(variable);
      }
    }
    
    return variables;
  }
  
  // Prompt şablonunu değişkenleriyle doldur
  static fillTemplate(template: string, variables: Record<string, string>): string {
    return template.replace(/\{\{(.*?)\}\}/g, (match, variable) => {
      const key = variable.trim();
      return variables[key] || match;
    });
  }
}

// React Query Hooks

// Prompt şablonları için hook
export function usePromptTemplates(filters?: PromptTemplateFilter) {
  return useQuery(
    ['promptTemplates', filters],
    () => PromptTemplateService.getPromptTemplates(filters),
    {
      staleTime: 5 * 60 * 1000, // 5 dakika
    }
  );
}

// Belirli bir prompt şablonu için hook
export function usePromptTemplate(id: string | undefined) {
  return useQuery(
    ['promptTemplate', id],
    () => PromptTemplateService.getPromptTemplate(id!),
    {
      enabled: !!id,
      staleTime: 5 * 60 * 1000, // 5 dakika
    }
  );
}

// Prompt şablonu oluşturma hook'u
export function useCreatePromptTemplate() {
  return useMutation(
    (data: CreatePromptTemplateInput) => PromptTemplateService.createPromptTemplate(data),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('promptTemplates');
      }
    }
  );
}

// Prompt şablonu güncelleme hook'u
export function useUpdatePromptTemplate() {
  return useMutation(
    ({ id, data }: { id: string; data: UpdatePromptTemplateInput }) => 
      PromptTemplateService.updatePromptTemplate(id, data),
    {
      onSuccess: (_, { id }) => {
        queryClient.invalidateQueries('promptTemplates');
        queryClient.invalidateQueries(['promptTemplate', id]);
      }
    }
  );
}

// Prompt şablonu silme hook'u
export function useDeletePromptTemplate() {
  return useMutation(
    (id: string) => PromptTemplateService.deletePromptTemplate(id),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('promptTemplates');
      }
    }
  );
}

// Varsayılan prompt şablonu ayarlama hook'u
export function useSetDefaultPromptTemplate() {
  return useMutation(
    (id: string) => PromptTemplateService.setDefaultPromptTemplate(id),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('promptTemplates');
      }
    }
  );
}

// Default export (statik sınıf metotları için erişim kolaylığı)
export default PromptTemplateService;