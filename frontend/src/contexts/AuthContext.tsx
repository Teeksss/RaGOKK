// Last reviewed: 2025-04-30 05:36:04 UTC (User: TeeksssJWT)
import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import API from '../api/api';
import { useNavigate, useLocation } from 'react-router-dom';
import { useToast } from './ToastContext';

// AuthContext için tip tanımları
interface User {
  id: string;
  email: string;
  username: string | null;
  full_name: string | null;
  is_superuser: boolean;
  roles: string[];
  organization_id: string | null;
}

interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  loading: boolean;
  tokenExpiresAt: number | null;
}

interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  logout: (options?: { revokeAll?: boolean }) => Promise<void>;
  refreshToken: () => Promise<boolean>;
  hasRole: (role: string | string[]) => boolean;
  isSuperuser: () => boolean;
}

// Context oluştur
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Context sağlayıcı bileşeni
export const AuthProvider: React.FC<{children: ReactNode}> = ({ children }) => {
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    user: null,
    token: null,
    loading: true,
    tokenExpiresAt: null,
  });
  const [refreshTimerId, setRefreshTimerId] = useState<NodeJS.Timeout | null>(null);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [sessionTimeoutWarningShown, setSessionTimeoutWarningShown] = useState<boolean>(false);
  
  const { showToast } = useToast();
  const navigate = useNavigate();
  const location = useLocation();

  // Token bilgilerini local storage'dan yükleme
  useEffect(() => {
    const loadAuthState = () => {
      const token = localStorage.getItem('token');
      const userJSON = localStorage.getItem('user');
      const expiration = localStorage.getItem('tokenExpiresAt');
      
      if (token && userJSON && expiration) {
        try {
          const user = JSON.parse(userJSON);
          const expiresAt = parseInt(expiration, 10);
          
          // Token süresi dolmuş mu kontrol et
          if (expiresAt > Date.now()) {
            // API istemcisine token'ı ayarla
            API.defaults.headers.common['Authorization'] = `Bearer ${token}`;
            
            setAuthState({
              isAuthenticated: true,
              user,
              token,
              loading: false,
              tokenExpiresAt: expiresAt
            });
            
            // Otomatik token yenileme zamanlayıcısını ayarla
            scheduleTokenRefresh(expiresAt);
          } else {
            // Token süresi dolmuşsa oturumu temizle
            clearAuthState();
          }
        } catch (error) {
          console.error('Error parsing auth data:', error);
          clearAuthState();
        }
      } else {
        setAuthState(prev => ({ ...prev, loading: false }));
      }
    };
    
    loadAuthState();
    
    // Temizleme fonksiyonu
    return () => {
      if (refreshTimerId) {
        clearTimeout(refreshTimerId);
      }
    };
  }, []);
  
  // Token yenileme zamanlayıcısını ayarla
  const scheduleTokenRefresh = useCallback((expiresAt: number) => {
    if (refreshTimerId) {
      clearTimeout(refreshTimerId);
    }
    
    // Token süresinin %75'i geçince yenileme işlemini başlat
    const currentTime = Date.now();
    const expirationTime = expiresAt;
    const timeUntilExpiry = expirationTime - currentTime;
    const refreshTime = timeUntilExpiry * 0.75; // Sürenin %75'i kadar bekle
    
    // Uyarı gösterme zamanlayıcısı - 1 dakika kaldığında
    const warningTime = timeUntilExpiry - 60000; // 1 dakika öncesinde uyar
    
    if (warningTime > 0) {
      setTimeout(() => {
        showSessionTimeoutWarning();
      }, warningTime);
    }
    
    if (refreshTime <= 0) {
      // Eğer zaten süre dolmak üzereyse hemen yenile
      refreshToken();
    } else {
      // Yoksa zamanlayıcı ayarla
      const timerId = setTimeout(() => {
        refreshToken();
      }, refreshTime);
      
      setRefreshTimerId(timerId);
    }
  }, [refreshTimerId]);
  
  // Oturum zaman aşımı uyarısını göster
  const showSessionTimeoutWarning = () => {
    if (!sessionTimeoutWarningShown) {
      setSessionTimeoutWarningShown(true);
      
      showToast(
        'warning', 
        'Oturumunuzun süresi dolmak üzere. Devam etmek için lütfen sayfayı yenileyin veya bir işlem yapın.',
        10000 // 10 saniye göster
      );
      
      // Kullanıcı işlem yaparsa uyarıyı sıfırla
      const resetWarning = () => {
        setSessionTimeoutWarningShown(false);
      };
      
      window.addEventListener('click', resetWarning, { once: true });
    }
  };
  
  // Token yenileme fonksiyonu
  const refreshToken = useCallback(async (): Promise<boolean> => {
    // Eğer zaten yenileme işlemi yapılıyorsa bekle
    if (refreshing) {
      return false;
    }
    
    try {
      setRefreshing(true);
      
      // Token yenileme isteği yap
      const response = await API.post<LoginResponse>('/auth/refresh');
      
      if (response.data) {
        const { access_token, expires_in, user } = response.data;
        const expiresAt = Date.now() + (expires_in * 1000);
        
        // Token ve kullanıcı bilgilerini güncelle
        localStorage.setItem('token', access_token);
        localStorage.setItem('user', JSON.stringify(user));
        localStorage.setItem('tokenExpiresAt', expiresAt.toString());
        
        // API istemcisine yeni token'ı ayarla
        API.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
        
        // Auth durumunu güncelle
        setAuthState({
          isAuthenticated: true,
          user,
          token: access_token,
          loading: false,
          tokenExpiresAt: expiresAt
        });
        
        // Yeni zamanlayıcı ayarla
        scheduleTokenRefresh(expiresAt);
        
        setRefreshing(false);
        setSessionTimeoutWarningShown(false);
        return true;
      }
      
      setRefreshing(false);
      return false;
      
    } catch (error) {
      console.error('Error refreshing token:', error);
      
      // Yenileme başarısız olursa oturumu kapat
      clearAuthState();
      
      // Hata mesajı göster
      showToast('error', 'Oturumunuzun süresi doldu. Lütfen tekrar giriş yapın.', 5000);
      
      // Giriş sayfasına yönlendir, mevcut konumu sakla
      navigate('/login', { state: { from: location.pathname } });
      
      setRefreshing(false);
      return false;
    }
  }, [navigate, location, refreshing]);
  
  // Giriş fonksiyonu
  const login = async (email: string, password: string): Promise<void> => {
    try {
      // Form verileri oluştur
      const formData = new FormData();
      formData.append('username', email); // OAuth2 standardı username field kullanıyor
      formData.append('password', password);
      
      const response = await API.post<LoginResponse>('/auth/token', formData);
      const { access_token, expires_in, user } = response.data;
      
      // Token süresi hesapla (saniyeden milisaniyeye)
      const expiresAt = Date.now() + (expires_in * 1000);
      
      // Token ve kullanıcı bilgilerini sakla
      localStorage.setItem('token', access_token);
      localStorage.setItem('user', JSON.stringify(user));
      localStorage.setItem('tokenExpiresAt', expiresAt.toString());
      
      // API istemcisine token'ı ayarla
      API.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      // Auth durumunu güncelle
      setAuthState({
        isAuthenticated: true,
        user,
        token: access_token,
        loading: false,
        tokenExpiresAt: expiresAt
      });
      
      // Token yenileme zamanlayıcısını ayarla
      scheduleTokenRefresh(expiresAt);
      
      // Başarı mesajı göster
      showToast('success', 'Başarıyla giriş yapıldı!');
      
    } catch (error: any) {
      console.error('Login error:', error);
      
      // Hata mesajı göster
      let errorMessage = 'Giriş yapılırken bir hata oluştu.';
      
      if (error.response?.data?.detail) {
        if (typeof error.response.data.detail === 'object' && error.response.data.detail.message) {
          errorMessage = error.response.data.detail.message;
        } else {
          errorMessage = error.response.data.detail;
        }
      }
      
      throw new Error(errorMessage);
    }
  };
  
  // Çıkış fonksiyonu
  const logout = async (options: { revokeAll?: boolean } = {}): Promise<void> => {
    try {
      if (authState.token) {
        // Çıkış isteği gönder
        await API.post('/auth/logout', { revoke_all: options.revokeAll });
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Auth durumunu temizle
      clearAuthState();
      
      // Başarı mesajı göster
      showToast('success', 'Başarıyla çıkış yapıldı.');
      
      // Ana sayfaya yönlendir
      navigate('/');
    }
  };
  
  // Auth durumunu temizleme
  const clearAuthState = () => {
    // Local storage'dan token bilgilerini temizle
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('tokenExpiresAt');
    
    // API istemcisinden token'ı kaldır
    delete API.defaults.headers.common['Authorization'];
    
    // Auth durumunu güncelle
    setAuthState({
      isAuthenticated: false,
      user: null,
      token: null,
      loading: false,
      tokenExpiresAt: null
    });
    
    // Zamanlayıcıyı temizle
    if (refreshTimerId) {
      clearTimeout(refreshTimerId);
      setRefreshTimerId(null);
    }
  };
  
  // Rol kontrolü fonksiyonu
  const hasRole = useCallback((role: string | string[]): boolean => {
    if (!authState.isAuthenticated || !authState.user) {
      return false;
    }
    
    // Süper kullanıcı her zaman tüm rollere sahiptir
    if (authState.user.is_superuser) {
      return true;
    }
    
    const userRoles = authState.user.roles || [];
    
    if (Array.isArray(role)) {
      // Birden fazla rolden en az birine sahip mi kontrol et
      return role.some(r => userRoles.includes(r));
    } else {
      // Tek bir role sahip mi kontrol et
      return userRoles.includes(role);
    }
  }, [authState.isAuthenticated, authState.user]);
  
  // Süper kullanıcı kontrolü
  const isSuperuser = useCallback((): boolean => {
    return Boolean(authState.isAuthenticated && authState.user?.is_superuser);
  }, [authState.isAuthenticated, authState.user]);
  
  // Context değerleri
  const value = {
    ...authState,
    login,
    logout,
    refreshToken,
    hasRole,
    isSuperuser
  };
  
  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

// Auth context hook
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  
  return context;
};

// İzin kontrolü hooks'u
export const useRequireAuth = () => {
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  
  useEffect(() => {
    if (!auth.loading && !auth.isAuthenticated) {
      // Kullanıcı giriş yapmamışsa, giriş sayfasına yönlendir
      navigate('/login', { state: { from: location.pathname } });
    }
  }, [auth.loading, auth.isAuthenticated, navigate, location]);
  
  return auth;
};

// Rol kontrolü hooks'u
export const useRequireRole = (requiredRole: string | string[]) => {
  const auth = useAuth();
  const navigate = useNavigate();
  const { showToast } = useToast();
  
  useEffect(() => {
    if (!auth.loading && auth.isAuthenticated) {
      // Kullanıcı giriş yapmış ama gerekli role sahip değilse
      if (!auth.hasRole(requiredRole)) {
        showToast('error', 'Bu sayfaya erişim izniniz bulunmamaktadır.');
        navigate('/'); // Ana sayfaya yönlendir
      }
    }
  }, [auth.loading, auth.isAuthenticated, auth.hasRole, requiredRole, navigate, showToast]);
  
  return auth;
};