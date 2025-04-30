// Last reviewed: 2025-04-30 07:48:16 UTC (User: Teeksss)
import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

interface RoleProtectedRouteProps {
  children: React.ReactNode;
  roles: string[];
  redirectPath?: string;
}

const RoleProtectedRoute: React.FC<RoleProtectedRouteProps> = ({
  children,
  roles,
  redirectPath = '/login'
}) => {
  const { isLoggedIn, user } = useAuth();
  
  // Kullanıcı giriş yapmamışsa, login sayfasına yönlendir
  if (!isLoggedIn) {
    return <Navigate to={redirectPath} state={{ from: window.location.pathname }} replace />;
  }
  
  // Kullanıcı rollerini kontrol et
  const userRoles = user?.roles || [];
  
  // 'admin' rolü her zaman tüm sayfalara erişebilir
  if (userRoles.includes('admin')) {
    return <>{children}</>;
  }
  
  // Kullanıcının gerekli rollerden en az birine sahip olup olmadığını kontrol et
  const hasRequiredRole = roles.some(role => userRoles.includes(role));
  
  if (!hasRequiredRole) {
    return <Navigate to="/unauthorized" replace />;
  }
  
  return <>{children}</>;
};

export default RoleProtectedRoute;