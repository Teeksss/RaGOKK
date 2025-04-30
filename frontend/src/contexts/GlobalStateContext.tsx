// Last reviewed: 2025-04-30 11:32:10 UTC (User: TeeksssOrta)
import React, { createContext, useReducer, useContext, useMemo, useCallback, ReactNode } from 'react';

// State tipi
interface GlobalState {
  theme: 'light' | 'dark' | 'system';
  sidebarOpen: boolean;
  notifications: Array<{
    id: string;
    type: 'info' | 'success' | 'warning' | 'error';
    message: string;
    timestamp: number;
  }>;
  isOffline: boolean;
  performanceWarnings: Array<{
    id: string;
    type: string;
    message: string;
    timestamp: number;
  }>;
  queryHistory: {
    recent: string[];
    favorites: string[];
  };
  userPreferences: {
    fontSize: 'small' | 'medium' | 'large';
    highContrast: boolean;
    animations: boolean;
  };
}

// Action tipi
type ActionType =
  | { type: 'SET_THEME'; payload: 'light' | 'dark' | 'system' }
  | { type: 'TOGGLE_SIDEBAR' }
  | { type: 'SET_SIDEBAR'; payload: boolean }
  | { type: 'ADD_NOTIFICATION'; payload: Omit<GlobalState['notifications'][number], 'id' | 'timestamp'> }
  | { type: 'REMOVE_NOTIFICATION'; payload: string }
  | { type: 'CLEAR_NOTIFICATIONS' }
  | { type: 'SET_OFFLINE_STATUS'; payload: boolean }
  | { type: 'ADD_PERFORMANCE_WARNING'; payload: Omit<GlobalState['performanceWarnings'][number], 'id' | 'timestamp'> }
  | { type: 'REMOVE_PERFORMANCE_WARNING'; payload: string }
  | { type: 'ADD_RECENT_QUERY'; payload: string }
  | { type: 'ADD_FAVORITE_QUERY'; payload: string }
  | { type: 'REMOVE_FAVORITE_QUERY'; payload: string }
  | { type: 'UPDATE_USER_PREFERENCES'; payload: Partial<GlobalState['userPreferences']> };

// Başlangıç durumu
const initialState: GlobalState = {
  theme: 'system',
  sidebarOpen: false,
  notifications: [],
  isOffline: !navigator.onLine,
  performanceWarnings: [],
  queryHistory: {
    recent: [],
    favorites: [],
  },
  userPreferences: {
    fontSize: 'medium',
    highContrast: false,
    animations: true,
  },
};

// Reducer fonksiyonu
function globalReducer(state: GlobalState, action: ActionType): GlobalState {
  switch (action.type) {
    case 'SET_THEME':
      return { ...state, theme: action.payload };
      
    case 'TOGGLE_SIDEBAR':
      return { ...state, sidebarOpen: !state.sidebarOpen };
      
    case 'SET_SIDEBAR':
      return { ...state, sidebarOpen: action.payload };
      
    case 'ADD_NOTIFICATION':
      return {
        ...state,
        notifications: [
          {
            id: Date.now().toString(),
            ...action.payload,
            timestamp: Date.now(),
          },
          ...state.notifications.slice(0, 9), // En fazla 10 bildirim
        ],
      };
      
    case 'REMOVE_NOTIFICATION':
      return {
        ...state,
        notifications: state.notifications.filter(
          (notification) => notification.id !== action.payload
        ),
      };
      
    case 'CLEAR_NOTIFICATIONS':
      return { ...state, notifications: [] };
      
    case 'SET_OFFLINE_STATUS':
      return { ...state, isOffline: action.payload };
      
    case 'ADD_PERFORMANCE_WARNING':
      // Duplicate kontrolü
      if (
        state.performanceWarnings.some(
          (warning) => warning.type === action.payload.type
        )
      ) {
        return state;
      }
      
      return {
        ...state,
        performanceWarnings: [
          {
            id: Date.now().toString(),
            ...action.payload,
            timestamp: Date.now(),
          },
          ...state.performanceWarnings.slice(0, 4), // En fazla 5 uyarı
        ],
      };
      
    case 'REMOVE_PERFORMANCE_WARNING':
      return {
        ...state,
        performanceWarnings: state.performanceWarnings.filter(
          (warning) => warning.id !== action.payload
        ),
      };
      
    case 'ADD_RECENT_QUERY':
      return {
        ...state,
        queryHistory: {
          ...state.queryHistory,
          recent: [
            action.payload,
            ...state.queryHistory.recent.filter((q) => q !== action.payload).slice(0, 9), // En fazla 10 sorgu
          ],
        },
      };
      
    case 'ADD_FAVORITE_QUERY':
      if (state.queryHistory.favorites.includes(action.payload)) {
        return state;
      }
      
      return {
        ...state,
        queryHistory: {
          ...state.queryHistory,
          favorites: [...state.queryHistory.favorites, action.payload],
        },
      };
      
    case 'REMOVE_FAVORITE_QUERY':
      return {
        ...state,
        queryHistory: {
          ...state.queryHistory,
          favorites: state.queryHistory.favorites.filter(
            (query) => query !== action.payload
          ),
        },
      };
      
    case 'UPDATE_USER_PREFERENCES':
      return {
        ...state,
        userPreferences: {
          ...state.userPreferences,
          ...action.payload,
        },
      };
      
    default:
      return state;
  }
}

// Context oluşturma
interface GlobalStateContextType {
  state: GlobalState;
  dispatch: React.Dispatch<ActionType>;
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  addNotification: (notification: Omit<GlobalState['notifications'][number], 'id' | 'timestamp'>) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
  setOfflineStatus: (isOffline: boolean) => void;
  addPerformanceWarning: (warning: Omit<GlobalState['performanceWarnings'][number], 'id' | 'timestamp'>) => void;
  removePerformanceWarning: (id: string) => void;
  addRecentQuery: (query: string) => void;
  addFavoriteQuery: (query: string) => void;
  removeFavoriteQuery: (query: string) => void;
  updateUserPreferences: (preferences: Partial<GlobalState['userPreferences']>) => void;
}

const GlobalStateContext = createContext<GlobalStateContextType | undefined>(undefined);

// Provider bileşeni
interface GlobalStateProviderProps {
  children: ReactNode;
  initialData?: Partial<GlobalState>;
}

export const GlobalStateProvider: React.FC<GlobalStateProviderProps> = ({ children, initialData }) => {
  const [state, dispatch] = useReducer(globalReducer, {
    ...initialState,
    ...initialData,
  });

  // Memoize edilmiş action creators
  const setTheme = useCallback((theme: 'light' | 'dark' | 'system') => {
    dispatch({ type: 'SET_THEME', payload: theme });
  }, []);

  const toggleSidebar = useCallback(() => {
    dispatch({ type: 'TOGGLE_SIDEBAR' });
  }, []);

  const setSidebarOpen = useCallback((open: boolean) => {
    dispatch({ type: 'SET_SIDEBAR', payload: open });
  }, []);

  const addNotification = useCallback(
    (notification: Omit<GlobalState['notifications'][number], 'id' | 'timestamp'>) => {
      dispatch({ type: 'ADD_NOTIFICATION', payload: notification });
    },
    []
  );

  const removeNotification = useCallback((id: string) => {
    dispatch({ type: 'REMOVE_NOTIFICATION', payload: id });
  }, []);

  const clearNotifications = useCallback(() => {
    dispatch({ type: 'CLEAR_NOTIFICATIONS' });
  }, []);

  const setOfflineStatus = useCallback((isOffline: boolean) => {
    dispatch({ type: 'SET_OFFLINE_STATUS', payload: isOffline });
  }, []);

  const addPerformanceWarning = useCallback(
    (warning: Omit<GlobalState['performanceWarnings'][number], 'id' | 'timestamp'>) => {
      dispatch({ type: 'ADD_PERFORMANCE_WARNING', payload: warning });
    },
    []
  );

  const removePerformanceWarning = useCallback((id: string) => {
    dispatch({ type: 'REMOVE_PERFORMANCE_WARNING', payload: id });
  }, []);

  const addRecentQuery = useCallback((query: string) => {
    dispatch({ type: 'ADD_RECENT_QUERY', payload: query });
  }, []);

  const addFavoriteQuery = useCallback((query: string) => {
    dispatch({ type: 'ADD_FAVORITE_QUERY', payload: query });
  }, []);

  const removeFavoriteQuery = useCallback((query: string) => {
    dispatch({ type: 'REMOVE_FAVORITE_QUERY', payload: query });
  }, []);

  const updateUserPreferences = useCallback(
    (preferences: Partial<GlobalState['userPreferences']>) => {
      dispatch({ type: 'UPDATE_USER_PREFERENCES', payload: preferences });
    },
    []
  );

  // Context değeri memoization
  const contextValue = useMemo(
    () => ({
      state,
      dispatch,
      setTheme,
      toggleSidebar,
      setSidebarOpen,
      addNotification,
      removeNotification,
      clearNotifications,
      setOfflineStatus,
      addPerformanceWarning,
      removePerformanceWarning,
      addRecentQuery,
      addFavoriteQuery,
      removeFavoriteQuery,
      updateUserPreferences,
    }),
    [
      state,
      setTheme,
      toggleSidebar,
      setSidebarOpen,
      addNotification,
      removeNotification,
      clearNotifications,
      setOfflineStatus,
      addPerformanceWarning,
      removePerformanceWarning,
      addRecentQuery,
      addFavoriteQuery,
      removeFavoriteQuery,
      updateUserPreferences,
    ]
  );

  return (
    <GlobalStateContext.Provider value={contextValue}>
      {children}
    </GlobalStateContext.Provider>
  );
};

// Context hook'u
export const useGlobalState = () => {
  const context = useContext(GlobalStateContext);
  if (context === undefined) {
    throw new Error('useGlobalState must be used within a GlobalStateProvider');
  }
  return context;
};

// Seçici hook'lar - yeniden render optimizasyonu için
export const useTheme = () => {
  const context = useContext(GlobalStateContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a GlobalStateProvider');
  }
  return {
    theme: context.state.theme,
    setTheme: context.setTheme,
  };
};

export const useSidebar = () => {
  const context = useContext(GlobalStateContext);
  if (context === undefined) {
    throw new Error('useSidebar must be used within a GlobalStateProvider');
  }
  return {
    sidebarOpen: context.state.sidebarOpen,
    toggleSidebar: context.toggleSidebar,
    setSidebarOpen: context.setSidebarOpen,
  };
};

export const useNotifications = () => {
  const context = useContext(GlobalStateContext);
  if (context === undefined) {
    throw new Error('useNotifications must be used within a GlobalStateProvider');
  }
  return {
    notifications: context.state.notifications,
    addNotification: context.addNotification,
    removeNotification: context.removeNotification,
    clearNotifications: context.clearNotifications,
  };
};

export const useOfflineStatus = () => {
  const context = useContext(GlobalStateContext);
  if (context === undefined) {
    throw new Error('useOfflineStatus must be used within a GlobalStateProvider');
  }
  return {
    isOffline: context.state.isOffline,
    setOfflineStatus: context.setOfflineStatus,
  };
};

export const usePerformanceWarnings = () => {
  const context = useContext(GlobalStateContext);
  if (context === undefined) {
    throw new Error('usePerformanceWarnings must be used within a GlobalStateProvider');
  }
  return {
    performanceWarnings: context.state.performanceWarnings,
    addPerformanceWarning: context.addPerformanceWarning,
    removePerformanceWarning: context.removePerformanceWarning,
  };
};

export const useQueryHistory = () => {
  const context = useContext(GlobalStateContext);
  if (context === undefined) {
    throw new Error('useQueryHistory must be used within a GlobalStateProvider');
  }
  return {
    recentQueries: context.state.queryHistory.recent,
    favoriteQueries: context.state.queryHistory.favorites,
    addRecentQuery: context.addRecentQuery,
    addFavoriteQuery: context.addFavoriteQuery,
    removeFavoriteQuery: context.removeFavoriteQuery,
  };
};

export const useUserPreferences = () => {
  const context = useContext(GlobalStateContext);
  if (context === undefined) {
    throw new Error('useUserPreferences must be used within a GlobalStateProvider');
  }
  return {
    userPreferences: context.state.userPreferences,
    updateUserPreferences: context.updateUserPreferences,
  };
};