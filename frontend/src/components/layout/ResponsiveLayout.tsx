// Last reviewed: 2025-04-30 05:22:47 UTC (User: Teeksss)
import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Button, Navbar, Nav } from 'react-bootstrap';
import { FaBars, FaTimes, FaArrowUp, FaArrowDown } from 'react-icons/fa';
import { useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import '../../styles/responsive.css';

interface ResponsiveLayoutProps {
  children: React.ReactNode;
  showSidebar?: boolean;
  fluid?: boolean;
}

const ResponsiveLayout: React.FC<ResponsiveLayoutProps> = ({ 
  children, 
  showSidebar = true,
  fluid = false 
}) => {
  const [sidebarVisible, setSidebarVisible] = useState(false);
  const [showScrollButtons, setShowScrollButtons] = useState(false);
  const [lastScrollTop, setLastScrollTop] = useState(0);
  const [scrollingDown, setScrollingDown] = useState(false);
  const location = useLocation();
  
  // URL değiştiğinde sidebar'ı kapat
  useEffect(() => {
    setSidebarVisible(false);
  }, [location.pathname]);
  
  // Scroll butonları için olay dinleyici
  useEffect(() => {
    const handleScroll = () => {
      const st = window.pageYOffset || document.documentElement.scrollTop;
      const windowHeight = window.innerHeight;
      const documentHeight = Math.max(
        document.body.scrollHeight,
        document.documentElement.scrollHeight,
        document.body.offsetHeight,
        document.documentElement.offsetHeight,
        document.body.clientHeight,
        document.documentElement.clientHeight
      );
      
      // Scroll butonlarını sadece belge boyutu ekran boyutunun iki katından büyükse göster
      if (documentHeight > windowHeight * 1.5) {
        setShowScrollButtons(true);
        setScrollingDown(st > lastScrollTop);
        setLastScrollTop(st);
      } else {
        setShowScrollButtons(false);
      }
    };
    
    window.addEventListener('scroll', handleScroll);
    return () => {
      window.removeEventListener('scroll', handleScroll);
    };
  }, [lastScrollTop]);
  
  // Sayfa başına git
  const scrollToTop = () => {
    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    });
  };
  
  // Sayfa sonuna git
  const scrollToBottom = () => {
    window.scrollTo({
      top: document.documentElement.scrollHeight,
      behavior: 'smooth'
    });
  };
  
  // Sidebar'ı aç/kapat
  const toggleSidebar = () => {
    setSidebarVisible(!sidebarVisible);
  };
  
  return (
    <div className="responsive-layout">
      {/* Mobil menü butonu */}
      <div className="position-fixed d-lg-none" style={{ 
        top: '0.5rem', 
        left: '0.5rem', 
        zIndex: 1040,
        display: showSidebar ? 'block' : 'none'
      }}>
        <Button 
          variant="light" 
          className="rounded-circle shadow-sm p-2" 
          onClick={toggleSidebar}
          aria-label={sidebarVisible ? "Close sidebar" : "Open sidebar"}
        >
          {sidebarVisible ? <FaTimes /> : <FaBars />}
        </Button>
      </div>
      
      {/* Sidebar */}
      {showSidebar && (
        <>
          <div className={`sidebar ${sidebarVisible ? 'show' : ''}`}>
            <Sidebar />
          </div>
          <div 
            className="sidebar-overlay" 
            onClick={() => setSidebarVisible(false)}
            aria-hidden="true"
          />
        </>
      )}
      
      {/* Ana içerik */}
      <div className={`main-content ${showSidebar ? 'd-lg-flex' : 'w-100'}`}>
        <Container fluid={fluid} className="py-3 px-md-4">
          <Row>
            <Col>
              {children}
            </Col>
          </Row>
        </Container>
      </div>
      
      {/* Mobil yukarı/aşağı hareket butonları */}
      {showScrollButtons && (
        <div className="mobile-nav-buttons">
          <button 
            className="mobile-nav-button" 
            onClick={scrollToTop}
            aria-label="Scroll to top"
          >
            <FaArrowUp />
          </button>
          <button 
            className="mobile-nav-button" 
            onClick={scrollToBottom}
            aria-label="Scroll to bottom"
          >
            <FaArrowDown />
          </button>
        </div>
      )}
    </div>
  );
};

export default ResponsiveLayout;