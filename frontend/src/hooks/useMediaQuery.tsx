// Last reviewed: 2025-04-29 13:36:58 UTC (User: TeeksssMobil)
import { useState, useEffect } from 'react';

/**
 * Media query hook - ekran boyutu değişikliklerini izler
 *
 * @param query CSS media query
 * @returns Boolean - query eşleşip eşleşmediği
 * 
 * @example
 * // Mobil cihaz kontrolü
 * const isMobile = useMediaQuery('(max-width: 768px)');
 * 
 * // Karanlık mod tercihini kontrol etme
 * const prefersDarkMode = useMediaQuery('(prefers-color-scheme: dark)');
 */
export function useMediaQuery(query: string): boolean {
  // Tarayıcı media query API'sini desteklemiyor olabilir (SSR için)
  const getMatches = (): boolean => {
    if (typeof window !== 'undefined') {
      return window.matchMedia(query).matches;
    }
    return false;
  };

  const [matches, setMatches] = useState<boolean>(getMatches());

  useEffect(() => {
    // Medya sorgusu değişikliklerini takip etmek için event listener
    const mediaQuery = window.matchMedia(query);
    
    // İlk değeri ayarla
    setMatches(mediaQuery.matches);

    // Event listener fonksiyonu
    const handleChange = (event: MediaQueryListEvent) => {
      setMatches(event.matches);
    };

    // Event listener'ı ekle
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleChange);
    } else {
      // Eski tarayıcılar için destek
      mediaQuery.addListener(handleChange);
    }

    // Cleanup
    return () => {
      if (mediaQuery.removeEventListener) {
        mediaQuery.removeEventListener('change', handleChange);
      } else {
        // Eski tarayıcılar için destek
        mediaQuery.removeListener(handleChange);
      }
    };
  }, [query]);

  return matches;
}

export default useMediaQuery;