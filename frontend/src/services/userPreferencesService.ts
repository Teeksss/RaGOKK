// Last reviewed: 2025-04-30 10:37:40 UTC (User: Teeksss)
import localforage from 'localforage';
import enhancedApi from '../api/enhancedApi';
import { debounce } from 'lodash';

// Önizleme türü
export enum PreviewMode {
  INLINE = 'inline',
  MODAL = 'modal',
  SIDEBAR = 'sidebar',
  NONE = 'none'
}

// Sonuçları gruplama türü
export enum GroupingMode {
  DOCUMENT = 'document',
  SIMILARITY = 'similarity',
  TOPIC = 'topic',
  NONE = 'none'
}

// Dashboard düzeni
export enum DashboardLayout {
  GRID = 'grid',
  LIST = 'list',
  COMPACT = 'compact',
  DETAILED = 'detailed'
}

// Belge sıralaması
export enum SortMode {
  DATE_CREATED_DESC = 'date_created_desc',
  DATE_CREATED_ASC = 'date_created_asc',
  ALPHABETICAL_ASC = 'alphabetical_asc',
  ALPHABETICAL_DESC = 'alphabetical_desc',
  SIZE_DESC = 'size_desc',
  SIZE_ASC = 'size_asc',
  RELEVANCE = 'relevance'
}

// Tam kullanıcı tercihleri
export interface UserPreferences {
  // Görünüm tercihleri
  appearance: {
    theme: string;
    fontSize: string;
    accentColor: string;
    highContrast: boolean;
    reducedMotion: boolean;
    darkCode: boolean;
  };
  
  // Dil tercihleri
  language: {
    locale: string;
    dateFormat: string;
    timeFormat: string;
    timeZone: string;
  };
  
  // Belge görüntüleme tercihleri
  documents: {
    defaultView: 'grid' | 'list';
    previewMode: PreviewMode;
    sortMode: SortMode;
    showTags: boolean;
    showMetadata: boolean;
    documentPageSize: number;
  };
  
  // Sorgu tercihleri
  querying: {
    modelName: string;
    temperature: number;
    defaultContext: number;
    groupingMode: GroupingMode;
    includeCitations: boolean;
    showSourceContext: boolean;
    streamResponses: boolean;
  };
  
  // Dashboard tercihleri
  dashboard: {
    layout: DashboardLayout;
    showWelcomeMessage: boolean;
    showStats: boolean;
    showRecentDocuments: boolean;
    showRecentQueries: boolean;
    documentCount: number;
    queryCount: number;
  };
  
  // Bildirim tercihleri
  notifications: {
    email: boolean;
    push: boolean;
    inApp: boolean;
    sounds: boolean;
    showWhenProcessingComplete: boolean;
  };
  
  // Klavye kısayolları
  shortcuts: {
    enabled: boolean;
    custom: Record<string, string>;
  };
  
  // Erişilebilirlik tercihleri
  accessibility: {
    screenReader: boolean;
    captions: boolean;
    cursorSize: 'normal' | 'large' | 'xlarge';
    focusIndicator: boolean;
  };
}

// Varsayılan tercihler
const defaultPreferences: UserPreferences = {
  appearance: {
    theme: 'system',
    fontSize: 'medium',
    accentColor: 'blue',
    highContrast: false,
    reducedMotion: false,
    darkCode: true
  },
  language: {
    locale: 'en',
    dateFormat: 'MM/DD/YYYY',
    timeFormat: '12h',
    timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
  },
  documents: {
    defaultView: 'grid',
    previewMode: PreviewMode.MODAL,
    sortMode: SortMode.DATE_CREATED_DESC,
    showTags: true,
    showMetadata: true,
    documentPageSize: 20
  },
  querying: {
    modelName: 'default',
    temperature: 0.7,
    defaultContext: 5,
    groupingMode: GroupingMode.DOCUMENT,
    includeCitations: true,
    showSourceContext: true,
    streamResponses: true
  },
  dashboard: {
    layout: DashboardLayout.GRID,
    showWelcomeMessage: true,
    showStats: true,
    showRecentDocuments: true,
    showRecentQueries: true,
    documentCount: 5,
    queryCount: 5
  },
  notifications: {
    email: true,
    push: true,
    inApp: true,
    sounds: true,
    showWhenProcessingComplete: true
  },
  shortcuts: {
    enabled: true,
    custom: {}
  },
  accessibility: {
    screenReader: false,
    captions: false,
    cursorSize: 'normal',
    focusIndicator: true
  }
};

// Kullanıcı tercihleri servisi
const UserPreferencesService = {
  /**
   * Tüm kullanıcı tercihlerini yükle
   */
  async loadPreferences(): Promise<UserPreferences> {
    try {
      // Önce yerel depolamadan kontrol et
      const cachedPrefs = await localforage.getItem<UserPreferences>('user_preferences');
      
      // Oturum açmış kullanıcı için sunucudan en güncel tercihleri getir
      const authToken = localStorage.getItem('auth_token');
      
      if (authToken) {
        try {
          const serverPrefs = await enhancedApi.get<{ preferences: UserPreferences }>('/users/preferences');
          
          // Sunucudan gelen tercihleri yerel depoda güncelle
          const mergedPrefs = this.mergeWithDefaults(serverPrefs.preferences);
          await localforage.setItem('user_preferences', mergedPrefs);
          return mergedPrefs;
        } catch (error) {
          console.error('Error loading preferences from server:', error);
          
          // Yerel tercihler varsa onları kullan
          if (cachedPrefs) {
            return this.mergeWithDefaults(cachedPrefs);
          }
        }
      } else if (cachedPrefs) {
        // Token yoksa ama yerel tercihler varsa, onları kullan
        return this.mergeWithDefaults(cachedPrefs);
      }
      
      // Yoksa varsayılan değerleri kullan
      return { ...defaultPreferences };
    } catch (error) {
      console.error('Error loading preferences:', error);
      return { ...defaultPreferences };
    }
  },
  
  /**
   * Tüm tercihleri kaydet
   */
  async savePreferences(preferences: UserPreferences): Promise<void> {
    try {
      // Yerel depoya kaydet
      await localforage.setItem('user_preferences', preferences);
      
      // Oturum açmış kullanıcı için sunucuya da kaydet
      const authToken = localStorage.getItem('auth_token');
      
      if (authToken) {
        await this.debouncedSaveToServer(preferences);
      }
      
      // Tema değişikliklerini uygula
      this.applyThemePreferences(preferences.appearance);
      
      // Erişilebilirlik tercihlerini uygula
      this.applyAccessibilityPreferences(preferences.accessibility);
    } catch (error) {
      console.error('Error saving preferences:', error);
      throw error;
    }
  },
  
  /**
   * Tek bir tercih güncelle
   */
  async updatePreference<K extends keyof UserPreferences>(
    category: K, 
    updates: Partial<UserPreferences[K]>
  ): Promise<UserPreferences> {
    const preferences = await this.loadPreferences();
    
    const updatedPreferences = {
      ...preferences,
      [category]: {
        ...preferences[category],
        ...updates
      }
    };
    
    await this.savePreferences(updatedPreferences);
    return updatedPreferences;
  },
  
  /**
   * Sunucuya kaydetme işlemini geciktir (çok sık çağrı yapılırsa)
   */
  debouncedSaveToServer: debounce(async (preferences: UserPreferences) => {
    try {
      await enhancedApi.put('/users/preferences', { preferences });
    } catch (error) {
      console.error('Error saving preferences to server:', error);
    }
  }, 1000),
  
  /**
   * Varsayılan değerlerle birleştir (eksik alanlar için)
   */
  mergeWithDefaults(partialPrefs: Partial<UserPreferences>): UserPreferences {
    const result = { ...defaultPreferences };
    
    // Her kategorideki değerleri kontrol et ve varsa güncelle
    Object.keys(defaultPreferences).forEach((key) => {
      const category = key as keyof UserPreferences;
      
      if (partialPrefs[category]) {
        result[category] = {
          ...result[category],
          ...partialPrefs[category]
        };
      }
    });
    
    return result;
  },
  
  /**
   * Tema tercihlerini uygula
   */
  applyThemePreferences(appearance: UserPreferences['appearance']): void {
    // Tema değişikliği
    document.documentElement.setAttribute('data-bs-theme', 
      appearance.theme === 'system' 
        ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
        : appearance.theme
    );
    
    // Yazı boyutu
    document.documentElement.classList.remove('font-size-small', 'font-size-medium', 'font-size-large');
    document.documentElement.classList.add(`font-size-${appearance.fontSize}`);
    
    // Accent rengi
    document.documentElement.classList.remove(
      'accent-blue', 'accent-green', 'accent-purple', 
      'accent-orange', 'accent-teal'
    );
    document.documentElement.classList.add(`accent-${appearance.accentColor}`);
    
    // Yüksek kontrast
    document.documentElement.classList.toggle('high-contrast', appearance.highContrast);
    
    // Hareket azaltma
    document.documentElement.classList.toggle('reduced-motion', appearance.reducedMotion);
  },
  
  /**
   * Erişilebilirlik tercihlerini uygula
   */
  applyAccessibilityPreferences(accessibility: UserPreferences['accessibility']): void {
    // İmleç boyutu
    document.documentElement.classList.remove('cursor-large', 'cursor-xlarge');
    if (accessibility.cursorSize !== 'normal') {
      document.documentElement.classList.add(`cursor-${accessibility.cursorSize}`);
    }
    
    // Odak göstergesi
    document.documentElement.classList.toggle('hide-focus-indicator', !accessibility.focusIndicator);
  },
  
  /**
   * Tercihleri sıfırla
   */
  async resetPreferences(): Promise<void> {
    await localforage.removeItem('user_preferences');
    
    // Oturum açmış kullanıcı için sunucudaki tercihleri de sıfırla
    const authToken = localStorage.getItem('auth_token');
    if (authToken) {
      await enhancedApi.put('/users/preferences/reset', {});
    }
    
    // Varsayılan tercihleri uygula
    this.applyThemePreferences(defaultPreferences.appearance);
    this.applyAccessibilityPreferences(defaultPreferences.accessibility);
  }
};

export default UserPreferencesService;