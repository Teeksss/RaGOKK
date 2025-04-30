// Last reviewed: 2025-04-30 08:34:14 UTC (User: Teeksss)
import React, { createContext, useState, useContext, useEffect } from 'react';

// Query türleri
export type QueryType = 'text' | 'multimodal';

// Sorgu geçmişi öğesi
export interface QueryHistoryItem {
  id: string;
  query: string;
  answer?: string;
  type: QueryType;
  timestamp: string;
  metadata?: {
    documentId?: string;
    documentTitle?: string;
    imageCount?: number;
    documentFilter?: string[];
    success?: boolean;
  };
}

// Context tipi
interface QueryContextType {
  history: QueryHistoryItem[];
  recentQueries: string[];
  addToHistory: (item: QueryHistoryItem) => void;
  clearHistory: () => void;
  removeFromHistory: (id: string) => void;
  getSimilarQueries: (query: string) => string[];
}

// Context oluşturma
const QueryContext = createContext<QueryContextType | undefined>(undefined);

// Local storage anahtarı
const HISTORY_STORAGE_KEY = 'rag_base_query_history';
const RECENT_QUERIES_LIMIT = 20;
const MAX_HISTORY_SIZE = 100;

// Provider bileşeni
export const QueryProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Geçmiş state'i
  const [history, setHistory] = useState<QueryHistoryItem[]>([]);
  const [recentQueries, setRecentQueries] = useState<string[]>([]);
  
  // Local storage'dan yükleme
  useEffect(() => {
    const storedHistory = localStorage.getItem(HISTORY_STORAGE_KEY);
    
    if (storedHistory) {
      try {
        const parsedHistory = JSON.parse(storedHistory) as QueryHistoryItem[];
        setHistory(parsedHistory);
        
        // Son sorguları ayrıca çıkar
        const queries = parsedHistory
          .map(item => item.query)
          .filter(Boolean)
          .filter((value, index, self) => self.indexOf(value) === index) // Yinelemeleri temizle
          .slice(0, RECENT_QUERIES_LIMIT);
          
        setRecentQueries(queries);
        
      } catch (error) {
        console.error('Error loading query history:', error);
        // Hata durumunda local storage'ı temizle
        localStorage.removeItem(HISTORY_STORAGE_KEY);
      }
    }
  }, []);
  
  // Local storage'a kaydetme
  useEffect(() => {
    if (history.length > 0) {
      localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(history));
      
      // Son sorguları güncelle
      const queries = history
        .map(item => item.query)
        .filter(Boolean)
        .filter((value, index, self) => self.indexOf(value) === index)
        .slice(0, RECENT_QUERIES_LIMIT);
        
      setRecentQueries(queries);
    }
  }, [history]);
  
  // Geçmişe ekleme
  const addToHistory = (item: QueryHistoryItem) => {
    setHistory(prevHistory => {
      // Maksimum boyutu aşıyorsa eski öğeleri kaldır
      const updatedHistory = [item, ...prevHistory];
      
      if (updatedHistory.length > MAX_HISTORY_SIZE) {
        return updatedHistory.slice(0, MAX_HISTORY_SIZE);
      }
      
      return updatedHistory;
    });
  };
  
  // Geçmişi temizleme
  const clearHistory = () => {
    setHistory([]);
    localStorage.removeItem(HISTORY_STORAGE_KEY);
  };
  
  // Geçmişten kaldırma
  const removeFromHistory = (id: string) => {
    setHistory(prevHistory => prevHistory.filter(item => item.id !== id));
  };
  
  // Benzer sorguları getirme
  const getSimilarQueries = (query: string): string[] => {
    if (!query || query.length < 3) {
      return [];
    }
    
    // En son 5 benzeri bul
    const normalizedQuery = query.toLowerCase().trim();
    
    return recentQueries
      .filter(q => q.toLowerCase().includes(normalizedQuery))
      .slice(0, 5);
  };
  
  return (
    <QueryContext.Provider 
      value={{
        history,
        recentQueries,
        addToHistory,
        clearHistory,
        removeFromHistory,
        getSimilarQueries
      }}
    >
      {children}
    </QueryContext.Provider>
  );
};

// Custom hook
export const useQuery = (): QueryContextType => {
  const context = useContext(QueryContext);
  
  if (context === undefined) {
    throw new Error('useQuery must be used within a QueryProvider');
  }
  
  return context;
};