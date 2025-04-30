// Last reviewed: 2025-04-30 07:48:16 UTC (User: Teeksss)
import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

interface PermissionProtectedRouteProps {
  children: React.ReactNode;
  permission: string;
  redirectPath?: string;
}

const PermissionProtectedRoute: React.FC<PermissionProtectedRouteProps> = ({
  children,
  permission,
  redirectPath = '/login'
}) => {
  const { isLoggedIn, user } = useAuth();
  
  // Kullanıcı giriş yapmamışsa, login sayfasına yönlendir
  if (!isLoggedIn) {
    return <Navigate to={redirectPath} state={{ from: window.location.pathname }} replace />;
  }
  
  // Kullanıcı rollerini ve izinlerini kontrol et
  const userRoles = user?.roles || [];
  const userPermissions = user?.permissions || [];
  
  // 'admin' rolü her zaman tüm izinlere sahiptir
  if (userRoles.includes('admin')) {
    return <>{children}</>;
  }
  
  // Kullanıcının doğrudan izni var mı?
  if (userPermissions.includes(permission)) {
    return <>{children}</>;
  }
  
  // Rol bazlı izin kontrolü
  const roleBasedPermissions: Record<string, string[]> = {
    'org_admin': [
      'view:users', 'create:user', 'edit:user', 'delete:user',
      'view:organization', 'manage:organization',
      'view:documents', 'create:document', 'edit:document', 'delete:document',
      'view:analytics'
    ],
    'editor': [
      'view:documents', 'create:document', 'edit:document', 'delete:document',
      'run:queries', 'view:query_history'
    ],
    'viewer': [
      'view:documents', 'run:queries', 'view:query_history'
    ],
    'user': [
      'view:documents', 'create:document', 'edit:document',
      'run:queries', 'view:query_history', 'view:analytics'
    ]
  };
  
  // Kullanıcının rollerine göre izin kontrolü
  const hasPermissionViaRole = userRoles.some(role => {
    if (role in roleBasedPermissions) {
      return roleBasedPermissions[role].includes(permission);
    }
    return false;
  });
  
  if (hasPermissionViaRole) {
    return <>{children}</>;
  }
  
  // İzin yoksa yetkisiz sayfasına yönlendir
  return <Navigate to="/unauthorized" replace />;
};

export default PermissionProtectedRoute;