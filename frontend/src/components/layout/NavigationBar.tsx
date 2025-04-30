// Last reviewed: 2025-04-30 06:11:15 UTC (User: Teeksss)
import React from 'react';
import { Navbar, Nav, Container, Button, Dropdown } from 'react-bootstrap';
import { Link, useNavigate } from 'react-router-dom';
import { FaUser, FaSignOutAlt, FaCog, FaQuestionCircle } from 'react-icons/fa';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import { useToast } from '../../contexts/ToastContext';
import logo from '../../assets/logo.svg';
import LanguageSelector from '../settings/LanguageSelector';

const NavigationBar: React.FC = () => {
  const { t } = useTranslation();
  const { isAuthenticated, user, logout } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await logout();
      showToast('success', t('auth.logout.success'));
      navigate('/login');
    } catch (error: any) {
      showToast('error', t('auth.logout.error'));
    }
  };

  return (
    <Navbar bg="light" expand="lg" className="shadow-sm">
      <Container fluid>
        <Navbar.Brand as={Link} to="/" className="d-flex align-items-center">
          <img
            src={logo}
            height="30"
            className="d-inline-block align-top me-2"
            alt={t('common.appName')}
          />
          <span className="d-none d-sm-inline">{t('common.appName')}</span>
        </Navbar.Brand>
        
        <Navbar.Toggle aria-controls="nav-collapse" />
        
        <Navbar.Collapse id="nav-collapse">
          <Nav className="me-auto">
            {isAuthenticated && (
              <>
                <Nav.Link as={Link} to="/">
                  {t('common.home')}
                </Nav.Link>
                <Nav.Link as={Link} to="/documents">
                  {t('document.list.title')}
                </Nav.Link>
                <Nav.Link as={Link} to="/query">
                  {t('query.title')}
                </Nav.Link>
                <Nav.Link as={Link} to="/analytics">
                  {t('analytics.title')}
                </Nav.Link>
              </>
            )}
          </Nav>
          
          {/* Dil seçimi */}
          <div className="me-3">
            <LanguageSelector size="sm" />
          </div>
          
          <Nav>
            {isAuthenticated ? (
              <Dropdown align="end">
                <Dropdown.Toggle
                  variant="light"
                  id="dropdown-user"
                  className="d-flex align-items-center"
                >
                  <div className="avatar bg-primary text-white rounded-circle d-flex justify-content-center align-items-center me-2" style={{ width: '32px', height: '32px' }}>
                    <span className="fw-bold">{user?.username?.charAt(0)?.toUpperCase() || user?.email?.charAt(0)?.toUpperCase()}</span>
                  </div>
                  <span className="d-none d-md-inline">{user?.username || user?.email}</span>
                </Dropdown.Toggle>
                
                <Dropdown.Menu>
                  <Dropdown.Item as={Link} to="/profile">
                    <FaUser className="me-2" /> {t('common.profile')}
                  </Dropdown.Item>
                  <Dropdown.Item as={Link} to="/settings">
                    <FaCog className="me-2" /> {t('common.settings')}
                  </Dropdown.Item>
                  <Dropdown.Item as={Link} to="/help">
                    <FaQuestionCircle className="me-2" /> {t('common.help')}
                  </Dropdown.Item>
                  <Dropdown.Divider />
                  <Dropdown.Item onClick={handleLogout}>
                    <FaSignOutAlt className="me-2" /> {t('common.logOut')}
                  </Dropdown.Item>
                </Dropdown.Menu>
              </Dropdown>
            ) : (
              <>
                <Nav.Item>
                  <Button
                    as={Link}
                    to="/login"
                    variant="outline-primary"
                    className="me-2"
                  >
                    {t('common.logIn')}
                  </Button>
                </Nav.Item>
                <Nav.Item>
                  <Button
                    as={Link}
                    to="/register"
                    variant="primary"
                  >
                    {t('common.signUp')}
                  </Button>
                </Nav.Item>
              </>
            )}
          </Nav>
        </Navbar.Collapse>
      </Container>
    </Navbar>
  );
};

export default NavigationBar;