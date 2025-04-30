// Last reviewed: 2025-04-30 08:34:14 UTC (User: Teeksss)
import React, { createContext, useState, useContext, useEffect } from 'react';

export type ThemeType = 'light' | 'dark' | 'system';
export type FontSizeType = 'small' | 'medium' | 'large';
export type AccentColorType = 'blue' | 'green' | 'purple' | 'orange' | 'teal';

interface ThemeContextType {
  theme: ThemeType;
  fontSize: FontSizeType;
  accentColor: AccentColorType;
  highContrast: boolean;
  setTheme: (theme: ThemeType) => void;
  setFontSize: (size: FontSizeType) => void;
  setAccentColor: (color: AccentColorType) => void;
  toggleHighContrast: () => void;
  isDarkMode: boolean;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

// Provider component
export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // States
  const [theme, setThemeState] = useState<ThemeType>('system');
  const [fontSize, setFontSizeState] = useState<FontSizeType>('medium');
  const [accentColor, setAccentColorState] = useState<AccentColorType>('blue');
  const [highContrast, setHighContrast] = useState<boolean>(false);
  const [isDarkMode, setIsDarkMode] = useState<boolean>(false);
  
  // Load settings from localStorage
  useEffect(() => {
    // Theme
    const savedTheme = localStorage.getItem('rag_theme') as ThemeType;
    if (savedTheme && ['light', 'dark', 'system'].includes(savedTheme)) {
      setThemeState(savedTheme);
    }
    
    // Font size
    const savedFontSize = localStorage.getItem('rag_font_size') as FontSizeType;
    if (savedFontSize && ['small', 'medium', 'large'].includes(savedFontSize)) {
      setFontSizeState(savedFontSize);
    }
    
    // Accent color
    const savedAccentColor = localStorage.getItem('rag_accent_color') as AccentColorType;
    if (savedAccentColor && ['blue', 'green', 'purple', 'orange', 'teal'].includes(savedAccentColor)) {
      setAccentColorState(savedAccentColor);
    }
    
    // High contrast
    const savedHighContrast = localStorage.getItem('rag_high_contrast');
    if (savedHighContrast) {
      setHighContrast(savedHighContrast === 'true');
    }
  }, []);
  
  // Apply theme
  useEffect(() => {
    // Determine if we should use dark mode
    let shouldUseDarkMode = false;
    
    if (theme === 'dark') {
      shouldUseDarkMode = true;
    } else if (theme === 'system') {
      shouldUseDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    
    // Update state
    setIsDarkMode(shouldUseDarkMode);
    
    // Apply to document
    document.body.classList.toggle('dark-theme', shouldUseDarkMode);
    
    // Update CSS variables
    document.documentElement.setAttribute('data-bs-theme', shouldUseDarkMode ? 'dark' : 'light');
    
    // Save to localStorage
    localStorage.setItem('rag_theme', theme);
    
    // Listen for system theme changes if using system theme
    if (theme === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const handler = (e: MediaQueryListEvent) => {
        setIsDarkMode(e.matches);
        document.body.classList.toggle('dark-theme', e.matches);
        document.documentElement.setAttribute('data-bs-theme', e.matches ? 'dark' : 'light');
      };
      
      mediaQuery.addEventListener('change', handler);
      return () => mediaQuery.removeEventListener('change', handler);
    }
  }, [theme]);
  
  // Apply font size
  useEffect(() => {
    // Remove all font size classes
    document.documentElement.classList.remove('font-size-small', 'font-size-medium', 'font-size-large');
    
    // Add the current font size class
    document.documentElement.classList.add(`font-size-${fontSize}`);
    
    // Save to localStorage
    localStorage.setItem('rag_font_size', fontSize);
  }, [fontSize]);
  
  // Apply accent color
  useEffect(() => {
    // Remove all accent color classes
    document.documentElement.classList.remove(
      'accent-blue', 
      'accent-green', 
      'accent-purple', 
      'accent-orange', 
      'accent-teal'
    );
    
    // Add the current accent color class
    document.documentElement.classList.add(`accent-${accentColor}`);
    
    // Set CSS variables
    let primaryColor = '';
    switch (accentColor) {
      case 'blue': primaryColor = '#0d6efd'; break;
      case 'green': primaryColor = '#198754'; break;
      case 'purple': primaryColor = '#6f42c1'; break;
      case 'orange': primaryColor = '#fd7e14'; break;
      case 'teal': primaryColor = '#20c997'; break;
      default: primaryColor = '#0d6efd';
    }
    
    document.documentElement.style.setProperty('--bs-primary', primaryColor);
    
    // Save to localStorage
    localStorage.setItem('rag_accent_color', accentColor);
  }, [accentColor]);
  
  // Apply high contrast
  useEffect(() => {
    document.documentElement.classList.toggle('high-contrast', highContrast);
    
    // Save to localStorage
    localStorage.setItem('rag_high_contrast', String(highContrast));
  }, [highContrast]);
  
  // Wrapper functions
  const setTheme = (newTheme: ThemeType) => {
    setThemeState(newTheme);
  };
  
  const setFontSize = (newSize: FontSizeType) => {
    setFontSizeState(newSize);
  };
  
  const setAccentColor = (newColor: AccentColorType) => {
    setAccentColorState(newColor);
  };
  
  const toggleHighContrast = () => {
    setHighContrast(prev => !prev);
  };
  
  // Context value
  const contextValue: ThemeContextType = {
    theme,
    fontSize,
    accentColor,
    highContrast,
    setTheme,
    setFontSize,
    setAccentColor,
    toggleHighContrast,
    isDarkMode
  };
  
  return (
    <ThemeContext.Provider value={contextValue}>
      {children}
    </ThemeContext.Provider>
  );
};

// Custom hook
export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext);
  
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  
  return context;
};