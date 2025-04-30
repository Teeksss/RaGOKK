# Last reviewed: 2025-04-30 05:43:44 UTC (User: Teeksss)
import React, { useState } from 'react';
import { Nav, NavDropdown } from 'react-bootstrap';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

interface NavItem {
  title: string;
  path: string;
  icon?: React.ReactNode;
  requiredRoles?: string[];
  children?: NavItem[];
}

interface RoleBasedNavigationProps {
  items: NavItem[];
  vertical?: boolean;
  onItemClick?: () => void;
}

const RoleBasedNavigation: React.FC<RoleBasedNavigationProps> = ({
  items,
  vertical = false,
  onItemClick
}) => {
  const { hasRole, isAuthenticated } = useAuth();
  const location = useLocation();
  
  const [expandedDropdowns, setExpandedDropdowns] = useState<{ [key: string]: boolean }>({});
  
  // Erişim kontrolü - rol kontrolü yapar
  const hasAccess = (item: NavItem): boolean => {
    // Kimliği doğrulanmamış kullanıcılar için
    if (!isAuthenticated) {
      return false;
    }
    
    // Rol gerektirmeyen öğeler
    if (!item.requiredRoles || item.requiredRoles.length === 0) {
      return true;
    }
    
    // Rol kontrolü
    return hasRole(item.requiredRoles);
  };
  
  // Alt menü varsa dropdown olarak göster
  const renderDropdown = (item: NavItem, index: number) => {
    // Erişim kontrolü
    if (!hasAccess(item) || !item.children || item.children.length === 0) {
      return null;
    }
    
    // Erişilebilir alt öğeleri filtrele
    const accessibleChildren = item.children.filter(child => hasAccess(child));
    
    if (accessibleChildren.length === 0) {
      return null;
    }
    
    const isExpanded = expandedDropdowns[item.title] || false;
    const hasActiveChild = accessibleChildren.some(child => 
      location.pathname === child.path || location.pathname.startsWith(`${child.path}/`)
    );
    
    const toggleDropdown = () => {
      setExpandedDropdowns(prev => ({
        ...prev,
        [item.title]: !prev[item.title]
      }));
    };
    
    return (
      <NavDropdown
        key={`dropdown-${index}`}
        title={
          <span>
            {item.icon && <span className="nav-icon me-2">{item.icon}</span>}
            {item.title}
          </span>
        }
        id={`nav-dropdown-${index}`}
        className={hasActiveChild ? 'active' : ''}
        show={vertical ? isExpanded : undefined}
        onClick={vertical ? toggleDropdown : undefined}
      >
        {accessibleChildren.map((child, childIndex) => (
          <NavDropdown.Item
            key={`dropdown-item-${index}-${childIndex}`}
            as={Link}
            to={child.path}
            active={location.pathname === child.path || location.pathname.startsWith(`${child.path}/`)}
            onClick={onItemClick}
          >
            {child.icon && <span className="nav-icon me-2">{child.icon}</span>}
            {child.title}
          </NavDropdown.Item>
        ))}
      </NavDropdown>
    );
  };
  
  // Tekli menü öğesi
  const renderNavItem = (item: NavItem, index: number) => {
    // Erişim kontrolü
    if (!hasAccess(item)) {
      return null;
    }
    
    // Alt menü varsa dropdown
    if (item.children && item.children.length > 0) {
      return renderDropdown(item, index);
    }
    
    // Tekli öğe
    return (
      <Nav.Item key={`nav-item-${index}`}>
        <Nav.Link
          as={Link}
          to={item.path}
          active={location.pathname === item.path || location.pathname.startsWith(`${item.path}/`)}
          onClick={onItemClick}
        >
          {item.icon && <span className="nav-icon me-2">{item.icon}</span>}
          {item.title}
        </Nav.Link>
      </Nav.Item>
    );
  };
  
  return (
    <Nav className={vertical ? 'flex-column' : ''}>
      {items.map((item, index) => renderNavItem(item, index))}
    </Nav>
  );
};

export default RoleBasedNavigation;