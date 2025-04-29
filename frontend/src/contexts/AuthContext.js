// Last reviewed: 2025-04-29 07:31:24 UTC (User: TeeksssLogin)
import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { useToast } from './ToastContext';

const AuthContext = createContext(null);
const API_URL = 'http://localhost:8000'; // Base URL

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('authToken'));
  const [isLoading, setIsLoading] = useState(true);
  const { showToast } = useToast();
  
  // Token ile kullanıcı bilgisini al
  const fetchUserInfo = useCallback(async () => {
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }
    
    try {
      const response = await fetch(`${API_URL}/users/me`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        if (response.status === 401) {
          // Token geçersiz, logout
          showToast('Oturumunuz sonlandı, lütfen tekrar giriş yapın', 'warning');
          localStorage.removeItem('authToken');
          setToken(null);
          setUser(null);
        }
        throw new Error('Kullanıcı bilgisi alınamadı');
      }
      
      const userData = await response.json();
      setUser(userData);
      showToast(`Hoş geldiniz, ${userData.username}!`, 'success');
    } catch (error) {
      console.error('Kullanıcı bilgisi alma hatası:', error);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, [token, showToast]);
  
  // CSRF token al
  const fetchCsrfToken = useCallback(async () => {
    try {
      await fetch(`${API_URL}/csrf-token`, {
        credentials: 'include' // Cookie alabilmek için
      });
      return true;
    } catch (error) {
      console.error('CSRF token alınamadı:', error);
      return false;
    }
  }, []);
  
  // Token değiştiğinde kullanıcı bilgisini al
  useEffect(() => {
    fetchUserInfo();
  }, [token, fetchUserInfo]);
  
  // Login fonksiyonu
  const login = useCallback(async (username, password) => {
    setIsLoading(true);
    
    try {
      // Önce CSRF token al
      await fetchCsrfToken();
      
      // Login isteği gönder
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);
      
      const response = await fetch(`${API_URL}/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: formData,
        credentials: 'include' // Cookie için
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage;
        
        try {
          // JSON parse edip hata mesajını al
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.detail || 'Giriş hatası';
        } catch {
          // JSON parse edilemezse raw text kullan
          errorMessage = response.status === 401 
            ? 'Kullanıcı adı veya şifre yanlış' 
            : `Giriş hatası (${response.status})`;
        }
        
        throw new Error(errorMessage);
      }
      
      const data = await response.json();
      const newToken = data.access_token;
      
      // Token'ı localStorage'a kaydet
      localStorage.setItem('authToken', newToken);
      setToken(newToken);
      
      // Kullanıcı bilgisini almak için fetchUserInfo beklemeden dön
      // fetchUserInfo zaten token değiştiğinde çağrılacak
      return data;
    } catch (error) {
      setIsLoading(false);
      throw error;
    }
  }, [fetchCsrfToken]);
  
  // Logout fonksiyonu
  const logout = useCallback(() => {
    localStorage.removeItem('authToken');
    setToken(null);
    setUser(null);
    showToast('Başarıyla çıkış yaptınız', 'info');
  }, [showToast]);
  
  // Context value
  const value = {
    user,
    token,
    isLoggedIn: !!user,
    isLoading,
    login,
    logout,
    refreshUser: fetchUserInfo,
    isAdmin: user ? user.roles.includes('admin') : false
  };
  
  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth hook must be used within an AuthProvider');
  }
  return context;
};