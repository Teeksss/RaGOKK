// Last reviewed: 2025-04-30 08:46:51 UTC (User: Teeksss)
import React, { useState } from 'react';
import { Button, Offcanvas, Form, Row, Col, Stack } from 'react-bootstrap';
import { 
  FaUniversalAccess, 
  FaTextHeight, 
  FaAdjust, 
  FaMoon, 
  FaSun, 
  FaFont, 
  FaMousePointer, 
  FaKeyboard 
} from 'react-icons/fa';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../../contexts/ThemeContext';

interface AccessibilityToolsProps {
  placement?: 'start' | 'end' | 'top' | 'bottom';
}

const AccessibilityTools: React.FC<AccessibilityToolsProps> = ({ 
  placement = 'end' 
}) => {
  const { t } = useTranslation();
  const { 
    theme, 
    fontSize, 
    highContrast, 
    setTheme, 
    setFontSize, 
    toggleHighContrast 
  } = useTheme();
  
  const [show, setShow] = useState(false);
  const [cursorSize, setCursorSize] = useState('normal');
  const [focusIndicator, setFocusIndicator] = useState(true);
  const [reducedMotion, setReducedMotion] = useState(false);
  
  const handleClose = () => setShow(false);
  const handleShow = () => setShow(true);
  
  // Apply cursor size
  const handleCursorSizeChange = (size: string) => {
    setCursorSize(size);
    
    // Apply CSS class to html element
    document.documentElement.classList.remove('cursor-large', 'cursor-xlarge');
    if (size !== 'normal') {
      document.documentElement.classList.add(`cursor-${size}`);
    }
  };
  
  // Apply focus indicator
  const handleFocusIndicatorChange = (enabled: boolean) => {
    setFocusIndicator(enabled);
    document.documentElement.classList.toggle('hide-focus-indicator', !enabled);
  };
  
  // Apply reduced motion
  const handleReducedMotionChange = (enabled: boolean) => {
    setReducedMotion(enabled);
    document.documentElement.classList.toggle('reduced-motion', enabled);
  };
  
  return (
    <>
      <Button 
        variant="outline-primary" 
        onClick={handleShow} 
        className="accessibility-button"
        aria-label={t('accessibility.toggle')}
      >
        <FaUniversalAccess />
      </Button>

      <Offcanvas 
        show={show} 
        onHide={handleClose} 
        placement={placement}
        backdrop={true}
        scroll={true}
        className="accessibility-panel"
      >
        <Offcanvas.Header closeButton>
          <Offcanvas.Title>
            <FaUniversalAccess className="me-2" />
            {t('accessibility.title')}
          </Offcanvas.Title>
        </Offcanvas.Header>
        <Offcanvas.Body>
          <Stack gap={4}>
            {/* Theme Section */}
            <div className="accessibility-section">
              <h5 className="section-title">
                {theme === 'dark' ? <FaMoon className="me-2" /> : <FaSun className="me-2" />}
                {t('accessibility.theme')}
              </h5>
              
              <Form.Group>
                <div className="d-flex justify-content-between theme-toggles">
                  <Button 
                    variant={theme === 'light' ? 'primary' : 'outline-primary'}
                    onClick={() => setTheme('light')}
                    className="theme-button light-theme-button"
                  >
                    <FaSun className="me-2" />
                    {t('settings.appearance.lightTheme')}
                  </Button>
                  
                  <Button 
                    variant={theme === 'dark' ? 'primary' : 'outline-primary'}
                    onClick={() => setTheme('dark')}
                    className="theme-button dark-theme-button"
                  >
                    <FaMoon className="me-2" />
                    {t('settings.appearance.darkTheme')}
                  </Button>
                  
                  <Button 
                    variant={theme === 'system' ? 'primary' : 'outline-primary'}
                    onClick={() => setTheme('system')}
                    className="theme-button system-theme-button"
                  >
                    <FaAdjust className="me-2" />
                    {t('settings.appearance.systemTheme')}
                  </Button>
                </div>
              </Form.Group>
            </div>
            
            {/* Contrast Section */}
            <div className="accessibility-section">
              <h5 className="section-title">{t('accessibility.contrast')}</h5>
              
              <Form.Check
                type="switch"
                id="contrast-switch"
                label={t('accessibility.highContrast')}
                checked={highContrast}
                onChange={() => toggleHighContrast()}
              />
              
              <div className="text-muted small">
                {t('accessibility.highContrastDescription')}
              </div>
            </div>
            
            {/* Font Size Section */}
            <div className="accessibility-section">
              <h5 className="section-title">
                <FaTextHeight className="me-2" />
                {t('accessibility.fontSize')}
              </h5>
              
              <Form.Group>
                <div className="d-flex justify-content-between font-size-options">
                  <Button 
                    variant={fontSize === 'small' ? 'primary' : 'outline-primary'}
                    onClick={() => setFontSize('small')}
                    className="font-size-button small-font-button"
                  >
                    <span className="font-size-label">A</span>
                    <span className="font-size-text">{t('settings.text.small')}</span>
                  </Button>
                  
                  <Button 
                    variant={fontSize === 'medium' ? 'primary' : 'outline-primary'}
                    onClick={() => setFontSize('medium')}
                    className="font-size-button medium-font-button"
                  >
                    <span className="font-size-label">A</span>
                    <span className="font-size-text">{t('settings.text.medium')}</span>
                  </Button>
                  
                  <Button 
                    variant={fontSize === 'large' ? 'primary' : 'outline-primary'}
                    onClick={() => setFontSize('large')}
                    className="font-size-button large-font-button"
                  >
                    <span className="font-size-label">A</span>
                    <span className="font-size-text">{t('settings.text.large')}</span>
                  </Button>
                </div>
              </Form.Group>
            </div>
            
            {/* Cursor Section */}
            <div className="accessibility-section">
              <h5 className="section-title">
                <FaMousePointer className="me-2" />
                {t('accessibility.cursor')}
              </h5>
              
              <Form.Group>
                <Form.Label>{t('accessibility.cursorSize')}</Form.Label>
                <Form.Select 
                  value={cursorSize}
                  onChange={(e) => handleCursorSizeChange(e.target.value)}
                >
                  <option value="normal">{t('accessibility.cursorNormal')}</option>
                  <option value="large">{t('accessibility.cursorLarge')}</option>
                  <option value="xlarge">{t('accessibility.cursorXLarge')}</option>
                </Form.Select>
              </Form.Group>
            </div>
            
            {/* Focus & Motion Section */}
            <div className="accessibility-section">
              <h5 className="section-title">
                <FaKeyboard className="me-2" />
                {t('accessibility.navigation')}
              </h5>
              
              <Form.Check
                type="switch"
                id="focus-indicator-switch"
                label={t('accessibility.focusIndicator')}
                checked={focusIndicator}
                onChange={(e) => handleFocusIndicatorChange(e.target.checked)}
                className="mb-2"
              />
              
              <Form.Check
                type="switch"
                id="reduced-motion-switch"
                label={t('accessibility.reducedMotion')}
                checked={reducedMotion}
                onChange={(e) => handleReducedMotionChange(e.target.checked)}
              />
            </div>
          </Stack>
          
          <div className="mt-4">
            <Button variant="primary" onClick={handleClose} className="w-100">
              {t('common.close')}
            </Button>
          </div>
        </Offcanvas.Body>
      </Offcanvas>
    </>
  );
};

export default AccessibilityTools;