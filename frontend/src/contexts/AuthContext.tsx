// Last reviewed: 2025-04-29 14:12:11 UTC (User: TeeksssKullanıcı)
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import jwtDecode from 'jwt-decode';
import API from '../api/api';
import { useToast } from './ToastContext';
import { useTranslation } from 'react-i18next';

// Auth durumu için tür tanımları
interface User {
  id: string;
  email: string;
  username: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  organization_id?: string;
  created_at?: string;
}

interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  tokens: AuthTokens | null;
  isLoading: boolean;
}

interface AuthContextProps extends AuthState {
  login: (email: string, password: string) => Promise<boolean>;
  logout: () => void;
  register: (userData: RegisterData) => Promise<boolean>;
  updateProfile: (userData: UpdateProfileData) => Promise<boolean>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<boolean>;
  loginWithTokens: (accessToken: string, refreshToken: string) => Promise<boolean>;
  refreshToken: () => Promise<boolean>;
  hasPermission: (permission: string | string[]) => boolean;
  getToken: () => string | null;
}

interface AuthProviderProps {
  children: ReactNode;
}

interface RegisterData {
  email: string;
  username: string;
  password: string;
  full_name: string;
}

interface UpdateProfileData {
  email?: string;
  username?: string;
  full_name?: string;
}

// Token içindeki JWT yapısı
interface JwtPayload {
  exp: number;
  sub: string;
  user_id: string;
  token_type: string;
}

// Auth Context oluştur
const AuthContext = createContext<AuthContextProps | undefined>(undefined);

// Local storage anahtar adları
const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';
const USER_KEY = 'user_data';

// Auth Provider bileşeni
export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const navigate = useNavigate();
  
  // Auth state
  const [state, setState] = useState<AuthState>({
    isAuthenticated: false,
    user: null,
    tokens: null,
    isLoading: true
  });
  
  // Token yenileme için interval
  const [refreshInterval, setRefreshInterval] = useState<NodeJS.Timeout | null>(null);
  
  // Başlangıçta localStorage'dan token ve kullanıcı bilgilerini yükle
  useEffect(() => {
    const loadAuthState = async () => {
      try {
        const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
        const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
        const userData = localStorage.getItem(USER_KEY);
        
        if (accessToken && refreshToken && userData) {
          // Token geçerli mi kontrol et
          const isValid = isTokenValid(accessToken);
          
          if (isValid) {
            // Token geçerliyse kullanıcı durumunu güncelle
            const user = JSON.parse(userData) as User;
            
            setState({
              isAuthenticated: true,
              user,
              tokens: {
                access_token: accessToken,
                refresh_token: refreshToken,
                token_type: 'bearer',
                expires_in: 3600
              },
              isLoading: false
            });
            
            // API için Authorization header'ı ayarla
            API.setAuthHeader(accessToken);
            
            // Token yenileme interval'i başlat
            startTokenRefreshInterval();
          } else {
            // Access token geçersiz, refresh token ile yenilemeyi dene
            const refreshed = await refreshTokenRequest(refreshToken);
            
            if (!refreshed) {
              // Yenileme başarısız, oturumu temizle
              clearAuthState();
            }
            
            setState(prev => ({ ...prev, isLoading: false }));
          }
        } else {
          // Token yok, oturumu temizle
          clearAuthState();
          setState(prev => ({ ...prev, isLoading: false }));
        }
      } catch (error) {
        console.error('Error loading auth state:', error);
        clearAuthState();
        setState(prev => ({ ...prev, isLoading: false }));
      }
    };
    
    loadAuthState();
    
    // Cleanup function
    return () => {
      if (refreshInterval) {
        clearInterval(refreshInterval);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  
  // Token'ın geçerli olup olmadığını kontrol et
  const isTokenValid = (token: string): boolean => {
    try {
      const decoded = jwtDecode<JwtPayload>(token);
      const currentTime = Math.floor(Date.now() / 1000);
      
      // Token süresi dolmadıysa ve access token ise geçerli
      return decoded.exp > currentTime && decoded.token_type === 'access';
    } catch (error) {
      console.error('Error decoding token:', error);
      return false;
    }
  };
  
  // Token yenileme interval'i başlat
  const startTokenRefreshInterval = () => {
    // Önce varsa eski interval'i temizle
    if (refreshInterval) {
      clearInterval(refreshInterval);
    }
    
    // Her 15 dakikada bir token'ı yenile
    const interval = setInterval(() => {
      refreshToken();
    }, 15 * 60 * 1000); // 15 dakika
    
    setRefreshInterval(interval);
  };
  
  // Refresh token ile yeni access token al
  const refreshTokenRequest = async (refreshToken: string): Promise<boolean> => {
    try {
      const response = await API.post('/auth/refresh', { refresh_token: refreshToken });
      
      const { access_token, refresh_token, user } = response.data;
      
      // Token ve kullanıcı bilgilerini güncelle
      localStorage.setItem(ACCESS_TOKEN_KEY, access_token);
      localStorage.setItem(REFRESH_TOKEN_KEY, refresh_token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      
      // API için Authorization header'ı güncelle
      API.setAuthHeader(access_token);
      
      // State'i güncelle
      setState({
        isAuthenticated: true,
        user,
        tokens: {
          access_token,
          refresh_token,
          token_type: 'bearer',
          expires_in: 3600
        },
        isLoading: false
      });
      
      return true;
    } catch (error) {
      console.error('Error refreshing token:', error);
      return false;
    }
  };
  
  // Auth state'i temizle
  const clearAuthState = () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    
    // API Authorization header'ı temizle
    API.clearAuthHeader();
    
    // State'i güncelle
    setState({
      isAuthenticated: false,
      user: null,
      tokens: null,
      isLoading: false
    });
    
    // Token yenileme interval'i temizle
    if (refreshInterval) {
      clearInterval(refreshInterval);
      setRefreshInterval(null);
    }
  };
  
  // Login fonksiyonu
  const login = async (email: string, password: string): Promise<boolean> => {
    try {
      setState(prev => ({ ...prev, isLoading: true }));
      
      // FormData kullanarak login isteği gönder (FastAPI OAuth2 ile uyumlu)
      const formData = new FormData();
      formData.append('username', email);
      formData.append('password', password);
      
      const response = await API.post('/auth/login', formData);
      
      const { access_token, refresh_token, user } = response.data;
      
      // Token ve kullanıcı bilgilerini kaydet
      localStorage.setItem(ACCESS_TOKEN_KEY, access_token);
      localStorage.setItem(REFRESH_TOKEN_KEY, refresh_token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      
      // API için Authorization header'ı ayarla
      API.setAuthHeader(access_token);
      
      // State'i güncelle
      setState({
        isAuthenticated: true,
        user,
        tokens: {
          access_token,
          refresh_token,
          token_type: 'bearer',
          expires_in: 3600
        },
        isLoading: false
      });
      
      // Token yenileme interval'i başlat
      startTokenRefreshInterval();
      
      showToast(t('auth.loginSuccess'), 'success');
      return true;
    } catch (error: any) {
      console.error('Login error:', error.response?.data || error);
      showToast(error.response?.data?.detail || t('auth.loginError'), 'error');
      setState(prev => ({ ...prev, isLoading: false }));
      return false;
    }
  };
  
  // Mevcut token'ları kullanarak giriş yap (SSO için)
  const loginWithTokens = async (accessToken: string, refreshToken: string): Promise<boolean> => {
    try {
      setState(prev => ({ ...prev, isLoading: true }));
      
      // Token geçerliliğini kontrol et
      if (!isTokenValid(accessToken)) {
        // Access token geçersiz, refresh token ile yenilemeyi dene
        const refreshed = await refreshTokenRequest(refreshToken);
        
        if (!refreshed) {
          // Yenileme başarısız
          setState(prev => ({ ...prev, isLoading: false }));
          return false;
        }
        
        return true;
      }
      
      // Token geçerliyse kullanıcı bilgilerini al
      API.setAuthHeader(accessToken);
      const response = await API.get('/auth/me');
      
      const user = response.data;
      
      // Token ve kullanıcı bilgilerini kaydet
      localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
      localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      
      // State'i güncelle
      setState({
        isAuthenticated: true,
        user,
        tokens: {
          access_token: accessToken,
          refresh_token: refreshToken,
          token_type: 'bearer',
          expires_in: 3600
        },
        isLoading: false
      });
      
      // Token yenileme interval'i başlat
      startTokenRefreshInterval();
      
      return true;
    } catch (error: any) {
      console.error('Token login error:', error.response?.data || error);
      setState(prev => ({ ...prev, isLoading: false }));
      return false;
    }
  };
  
  // Logout fonksiyonu
  const logout = async () => {
    try {
      // Backend'e logout isteği gönder (tercihen)
      if (state.isAuthenticated) {
        await API.post('/auth/logout');
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Auth state'i temizle
      clearAuthState();
      // Ana sayfaya yönlendir
      navigate('/login');
      showToast(t('auth.logoutSuccess'), 'info');
    }
  };
  
  // Kayıt fonksiyonu
  const register = async (userData: RegisterData): Promise<boolean> => {
    try {
      setState(prev => ({ ...prev, isLoading: true }));
      
      await API.post('/auth/register', userData);
      
      setState(prev => ({ ...prev, isLoading: false }));
      showToast(t('auth.registerSuccess'), 'success');
      return true;
    } catch (error: any) {
      console.error('Register error:', error.response?.data || error);
      showToast(error.response?.data?.detail || t('auth.registerError'), 'error');
      setState(prev => ({ ...prev, isLoading: false }));
      return false;
    }
  };
  
  // Profil güncelleme fonksiyonu
  const updateProfile = async (userData: UpdateProfileData): Promise<boolean> => {
    try {
      setState(prev => ({ ...prev, isLoading: true }));
      
      const response = await API.put('/auth/me', userData);
      
      // Kullanıcı bilgilerini güncelle
      const updatedUser = response.data;
      localStorage.setItem(USER_KEY, JSON.stringify(updatedUser));
      
      // State'i güncelle
      setState(prev => ({
        ...prev,
        user: updatedUser,
        isLoading: false
      }));
      
      showToast(t('auth.profileUpdateSuccess'), 'success');
      return true;
    } catch (error: any) {
      console.error('Profile update error:', error.response?.data || error);
      showToast(error.response?.data?.detail || t('auth.profileUpdateError'), 'error');
      setState(prev => ({ ...prev, isLoading: false }));
      return false;
    }
  };
  
  // Şifre değiştirme fonksiyonu
  const changePassword = async (currentPassword: string, newPassword: string): Promise<boolean> => {
    try {
      setState(prev => ({ ...prev, isLoading: true }));
      
      await API.put('/auth/me/password', {
        current_password: currentPassword,
        new_password: newPassword
      });
      
      setState(prev => ({ ...prev, isLoading: false }));
      showToast(t('auth.passwordChangeSuccess'), 'success');
      return true;
    } catch (error: any) {
      console.error('Password change error:', error.response?.data || error);
      showToast(error.response?.data?.detail || t('auth.passwordChangeError'), 'error');
      setState(prev => ({ ...prev, isLoading: false }));
      return false;
    }
  };
  
  // Token yenileme fonksiyonu (manuel)
  const refreshToken = async (): Promise<boolean> => {
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    
    if (!refreshToken) {
      return false;
    }
    
    return await refreshTokenRequest(refreshToken);
  };
  
  // Kullanıcının belirli izinlere sahip olup olmadığını kontrol et
  const hasPermission = (permission: string | string[]): boolean => {
    // Kullanıcı yoksa veya aktif değilse izin yok
    if (!state.user || !state.user.is_active) {
      return false;
    }
    
    // Süper kullanıcı ise tüm izinlere sahip
    if (state.user.is_superuser) {
      return true;
    }
    
    // TODO: İzin tabanlı kontrol sistemi geliştirilebilir
    // Şimdilik basit kontroller yapılıyor
    
    // Eğer bir dizi izin verilmişse, herhangi birine sahip olması yeterli
    if (Array.isArray(permission)) {
      return permission.some(p => hasPermission(p));
    }
    
    // Basit izin kontrolleri
    switch (permission) {
      case 'documents:view':
      case 'documents:search':
        return true; // Tüm aktif kullanıcılar belgeleri görüntüleyebilir ve arayabilir
        
      case 'documents:create':
      case 'documents:edit':
      case 'documents:delete':
        return true; // Tüm aktif kullanıcılar belge işlemleri yapabilir
        
      case 'admin:access':
      case 'users:manage':
      case 'organizations:manage':
        return state.user.is_superuser; // Sadece süper kullanıcılar
        
      default:
        return false; // Bilinmeyen izinler için varsayılan olarak reddetme
    }
  };
  
  // Geçerli access token'ı al
  const getToken = (): string | null => {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  };
  
  // Context value
  const value: AuthContextProps = {
    ...state,
    login,
    logout,
    register,
    updateProfile,
    changePassword,
    loginWithTokens,
    refreshToken,
    hasPermission,
    getToken
  };
  
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// Context hook'u
export const useAuth = (): AuthContextProps => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;