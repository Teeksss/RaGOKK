// Last reviewed: 2025-04-29 07:31:24 UTC (User: TeeksssLogin)
import React, { useState, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import useApi from '../hooks/useApi';
import SearchBar from './SearchBar';
import Results from './Results';
import Spinner from './ui/Spinner';
import './SearchSection.css';

const SearchSection = () => {
  const [searchResults, setSearchResults] = useState(null);
  const [searchError, setSearchError] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const { isLoggedIn } = useAuth();
  const { showToast } = useToast();
  const { apiRequest } = useApi();
  
  const handleSearchStart = useCallback(() => {
    setIsSearching(true);
    setSearchError('');
    setSearchResults(null);
  }, []);
  
  const handleResults = useCallback((results) => {
    setSearchResults(results);
    setIsSearching(false);
    showToast('Arama tamamlandı', 'success');
  }, [showToast]);
  
  const handleSearchError = useCallback((errorMsg) => {
    const friendlyError = errorMsg.includes("401") ? "Yetkilendirme hatası. Lütfen giriş yapın." :
                          errorMsg.includes("Failed to fetch") ? "Sunucuya bağlanılamadı." : errorMsg;
    setSearchError(friendlyError);
    setIsSearching(false);
    showToast(`Arama başarısız: ${friendlyError}`, 'error');
  }, [showToast]);
  
  if (!isLoggedIn) {
    return (
      <section className="search-section card">
        <h2>Arama</h2>
        <div className="login-required-message">
          <p>Arama yapmak için lütfen giriş yapın.</p>
        </div>
      </section>
    );
  }
  
  return (
    <section className="search-section card">
      <h2>Arama</h2>
      <SearchBar
        onSearchStart={handleSearchStart}
        onResults={handleResults}
        onError={handleSearchError}
        isSearching={isSearching}
        apiRequest={apiRequest}
      />
      
      {isSearching && (
        <div className="search-loading">
          <Spinner text="Aranıyor..." />
        </div>
      )}
      
      {searchError && !isSearching && (
        <div className="error-message search-error">
          Arama Hatası: {searchError}
        </div>
      )}
      
      {searchResults && !isSearching && (
        <Results
          answer={searchResults.answer}
          retrievedDocs={searchResults.retrieved_documents}
        />
      )}
    </section>
  );
};

export default SearchSection;