// Last reviewed: 2025-04-29 13:36:58 UTC (User: TeeksssMobil)
import React, { useState, useEffect } from 'react';
import { Sidebar } from './Sidebar';
import { Navbar } from './Navbar';
import { useMediaQuery } from '../hooks/useMediaQuery';

interface ResponsiveLayoutProps {
  children: React.ReactNode;
}

export const ResponsiveLayout: React.FC<ResponsiveLayoutProps> = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const isMobile = useMediaQuery('(max-width: 768px)');
  
  // Mobil cihazlarda sayfa değişikliğinde sidebar'ı otomatik kapat
  useEffect(() => {
    if (isMobile && sidebarOpen) {
      setSidebarOpen(false);
    }
  }, [location.pathname, isMobile]);

  // Ekran boyutu değiştiğinde sidebar durumunu ayarla
  useEffect(() => {
    if (!isMobile) {
      setSidebarOpen(true);
    } else {
      setSidebarOpen(false);
    }
  }, [isMobile]);
  
  // Sidebar toggle işlevi
  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  return (
    <div className="app-container">
      <Navbar 
        toggleSidebar={toggleSidebar}
        isMobile={isMobile}
      />
      
      <div className="app-content">
        <Sidebar 
          isOpen={sidebarOpen}
          isMobile={isMobile}
          onClose={() => setSidebarOpen(false)}
        />
        
        <main className={`main-content ${sidebarOpen && !isMobile ? 'with-sidebar' : 'sidebar-closed'}`}>
          {children}
        </main>
      </div>
    </div>
  );
};