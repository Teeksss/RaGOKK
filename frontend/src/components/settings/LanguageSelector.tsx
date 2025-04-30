// Last reviewed: 2025-04-30 06:11:15 UTC (User: Teeksss)
import React from 'react';
import { Dropdown } from 'react-bootstrap';
import { useTranslation } from 'react-i18next';
import { FaGlobe } from 'react-icons/fa';

interface LanguageSelectorProps {
  showLabel?: boolean;
  className?: string;
  variant?: 'dropdown' | 'buttons';
  size?: 'sm' | 'md' | 'lg';
}

const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  showLabel = false,
  className = '',
  variant = 'dropdown',
  size = 'md'
}) => {
  const { t, i18n } = useTranslation();
  
  // Desteklenen diller
  const languages = [
    { code: 'en', name: t('settings.language.english'), flag: '🇬🇧' },
    { code: 'tr', name: t('settings.language.turkish'), flag: '🇹🇷' }
  ];
  
  // Dili değiştir
  const changeLanguage = (langCode: string) => {
    i18n.changeLanguage(langCode)
      .then(() => {
        // Dil tercihini localStorage'a kaydet
        localStorage.setItem('i18nextLng', langCode);
      })
      .catch(err => {
        console.error('Error changing language:', err);
      });
  };
  
  // Mevcut dil
  const currentLanguage = languages.find(lang => lang.code === i18n.language) || languages[0];
  
  // Buton varyantı
  if (variant === 'buttons') {
    return (
      <div className={`d-flex align-items-center gap-2 ${className}`}>
        {showLabel && (
          <span className="me-2">{t('settings.language.label')}:</span>
        )}
        
        {languages.map((language) => (
          <button
            key={language.code}
            className={`btn ${i18n.language === language.code ? 'btn-primary' : 'btn-outline-secondary'} ${size === 'sm' ? 'btn-sm' : ''}`}
            onClick={() => changeLanguage(language.code)}
          >
            <span className="me-2">{language.flag}</span>
            {language.name}
          </button>
        ))}
      </div>
    );
  }
  
  // Dropdown varyantı (varsayılan)
  return (
    <Dropdown className={className}>
      <Dropdown.Toggle
        variant="outline-secondary"
        size={size}
        id="language-dropdown"
      >
        <FaGlobe className="me-2" />
        {showLabel ? currentLanguage.name : currentLanguage.flag}
      </Dropdown.Toggle>
      
      <Dropdown.Menu>
        {languages.map((language) => (
          <Dropdown.Item
            key={language.code}
            onClick={() => changeLanguage(language.code)}
            active={i18n.language === language.code}
          >
            <span className="me-2">{language.flag}</span>
            {language.name}
          </Dropdown.Item>
        ))}
      </Dropdown.Menu>
    </Dropdown>
  );
};

export default LanguageSelector;