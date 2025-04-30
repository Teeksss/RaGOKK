// Last reviewed: 2025-04-30 08:34:14 UTC (User: Teeksss)
import React, { createContext, useState, useContext, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import jwt_decode from 'jwt-decode';

import API from '../api/api';
import { useToast } from './ToastContext';

interface UserData {
  id: string;
  email: string;
  roles: string[];
  permissions?: string[];
  organization_id?: string;
  preferences?: {
    theme?: string;
    fontSize?: string;
    accentColor?: string;
    highContrast?: boolean;
    language?: string;
    notifications?: {
      email?: boolean;
      push?: boolean;
    };
  };
  has_2fa?: boolean;
}

interface TokenData {
  exp: number;
  iat: number;
  sub: string;
  id: string;
  email: string;
  roles: string[];
  permissions?: string[];
  organization_id?: string;
}

interface AuthContextType {
  isLoggedIn: boolean;
  user: UserData | null;
  login: (token: string) => Promise<void>;
  logout: () => Promise<void>;
  updateUser: (userData: UserData) => void;
  getAccessToken: () => string | null;
  checkTokenExpiration: () => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Helper to get token from localStorage
const getToken = () => localStorage.getItem('auth_token');

// Provider component
export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isLoggedIn, setIsLoggedIn] = useState<boolean>(false);
  const [user, setUser] = useState<UserData | null>(null);
  const navigate = useNavigate();
  const { showToast } = useToast();
  
  // Check if user is already logged in on mount
  useEffect(() => {
    const token = getToken();
    if (token) {
      try {
        // Decode token to get user data
        const decodedToken = jwt_decode<TokenData>(token);
        
        // Check if token is still valid
        if (decodedToken.exp * 1000 < Date.now()) {
          // Token expired, remove it
          localStorage.removeItem('auth_token');
          
          // Show toast notification
          showToast('error', 'Your session has expired. Please login again.');
          
          return;
        }
        
        // Get user data from decoded token
        const userData: UserData = {
          id: decodedToken.id,
          email: decodedToken.email,
          roles: decodedToken.roles || ['user'],
          permissions: decodedToken.permissions || [],
          organization_id: decodedToken.organization_id
        };
        
        // Set user data and login state
        setUser(userData);
        setIsLoggedIn(true);
        
        // Configure axios with token
        API.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        
        // Fetch additional user data
        fetchUserData(userData.id);
        
      } catch (error) {
        console.error('Error decoding token:', error);
        localStorage.removeItem('auth_token');
      }
    }
  }, []);
  
  // Function to fetch additional user data
  const fetchUserData = async (userId: string) => {
    try {
      const response = await API.get(`/users/${userId}`);
      
      // Update user with additional data
      setUser(prev => {
        if (!prev) return null;
        
        return {
          ...prev,
          ...response.data,
        };
      });
    } catch (error) {
      console.error('Error fetching user data:', error);
    }
  };
  
  // Login function
  const login = async (token: string) => {
    try {
      // Decode token to get user data
      const decodedToken = jwt_decode<TokenData>(token);
      
      // Get user data from decoded token
      const userData: UserData = {
        id: decodedToken.id,
        email: decodedToken.email,
        roles: decodedToken.roles || ['user'],
        permissions: decodedToken.permissions || [],
        organization_id: decodedToken.organization_id
      };
      
      // Save token to local storage
      localStorage.setItem('auth_token', token);
      
      // Set user data and login state
      setUser(userData);
      setIsLoggedIn(true);
      
      // Configure axios with token
      API.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      
      // Fetch additional user data
      await fetchUserData(userData.id);
      
      // Navigate to dashboard or to the requested page
      navigate('/');
    } catch (error) {
      console.error('Error logging in:', error);
      throw error;
    }
  };
  
  // Logout function
  const logout = async () => {
    try {
      // Call logout API
      await API.post('/auth/logout');
    } catch (error) {
      console.error('Error logging out:', error);
    } finally {
      // Remove token from local storage
      localStorage.removeItem('auth_token');
      
      // Remove token from axios headers
      delete API.defaults.headers.common['Authorization'];
      
      // Reset user data and login state
      setUser(null);
      setIsLoggedIn(false);
      
      // Navigate to login page
      navigate('/login');
    }
  };
  
  // Update user data
  const updateUser = (userData: UserData) => {
    setUser(userData);
  };
  
  // Get access token
  const getAccessToken = () => {
    return getToken();
  };
  
  // Check if token is expired
  const checkTokenExpiration = () => {
    const token = getToken();
    if (!token) return false;
    
    try {
      const decodedToken = jwt_decode<TokenData>(token);
      return decodedToken.exp * 1000 > Date.now();
    } catch (error) {
      console.error('Error checking token expiration:', error);
      return false;
    }
  };
  
  return (
    <AuthContext.Provider
      value={{
        isLoggedIn,
        user,
        login,
        logout,
        updateUser,
        getAccessToken,
        checkTokenExpiration
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

// Custom hook
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  
  return context;
};