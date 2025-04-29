// Last reviewed: 2025-04-29 13:14:42 UTC (User: TeeksssAPI)
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Dropdown } from 'react-bootstrap';
import { locales, changeLanguage, getSortedLocales } from '../i18n/i18n';

interface LanguageSelectorProps {
  variant?: 'dropdown' | 'buttons' | 'select';
  size?: 'sm' | 'md' | 'lg';
  showFlags?: boolean;
  showNames?: boolean;
  className?: string;
}

export const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  variant = 'dropdown',
  size = 'md',
  showFlags = true,
  showNames = true,
  className = ''
}) => {
  const { i18n } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const currentLanguage = i18n.language;
  
  // Dil değiştirme işleyicisi
  const handleChangeLanguage = async (language: string) => {
    await changeLanguage(language);
    setIsOpen(false);
  };
  
  // Dil listesini al
  const sortedLocales = getSortedLocales();
  
  // Mevcut seçili dilin bilgilerini al
  const currentLocale = locales[currentLanguage as keyof typeof locales] || locales.en;
  
  // Dropdown varyantı
  if (variant === 'dropdown') {
    return (
      <Dropdown show={isOpen} onToggle={(isOpen) => setIsOpen(isOpen)} className={className}>
        <Dropdown.Toggle 
          variant="outline-secondary" 
          id="language-dropdown"
          size={size === 'lg' ? 'lg' : size === 'sm' ? 'sm' : undefined}
        >
          {showFlags && <span className="me-1">{currentLocale.flag}</span>}
          {showNames && <span>{currentLocale.nativeName}</span>}
        </Dropdown.Toggle>

        <Dropdown.Menu>
          {sortedLocales.map((locale) => (
            <Dropdown.Item 
              key={locale.code}
              onClick={() => handleChangeLanguage(locale.code)}
              active={currentLanguage === locale.code}
            >
              {showFlags && <span className="me-2">{locale.flag}</span>}
              {locale.nativeName}
            </Dropdown.Item>
          ))}
        </Dropdown.Menu>
      </Dropdown>
    );
  }
  
  // Butonlar varyantı
  if (variant === 'buttons') {
    return (
      <div className={`btn-group ${className}`}>
        {sortedLocales.map((locale) => (
          <button
            key={locale.code}
            type="button"
            className={`btn ${currentLanguage === locale.code ? 'btn-primary' : 'btn-outline-secondary'}`}
            onClick={() => handleChangeLanguage(locale.code)}
          >
            {showFlags && <span className="me-1">{locale.flag}</span>}
            {showNames && <span>{locale.nativeName}</span>}
          </button>
        ))}
      </div>
    );
  }
  
  // Select varyantı
  return (
    <select
      value={currentLanguage}
      onChange={(e) => handleChangeLanguage(e.target.value)}
      className={`form-select ${size === 'lg' ? 'form-select-lg' : size === 'sm' ? 'form-select-sm' : ''} ${className}`}
      aria-label="Language selector"
    >
      {sortedLocales.map((locale) => (
        <option key={locale.code} value={locale.code}>
          {showFlags ? `${locale.flag} ` : ''}{locale.nativeName}
        </option>
      ))}
    </select>
  );
};

export default LanguageSelector;