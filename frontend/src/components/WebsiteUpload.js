// Last reviewed: 2025-04-29 06:57:37 UTC (User: Teeksss)
import React, { useState } from 'react';

const WebsiteUpload = ({ onUploadSuccess, onUploadError, sourceName, fetchApi }) => {
    const [url, setUrl] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');
    const [urlError, setUrlError] = useState('');

    const validateUrl = (urlString) => {
        if (!urlString.trim()) { setUrlError('URL zorunludur.'); return false; }
        try {
            const parsedUrl = new URL(urlString);
            if (parsedUrl.protocol !== "http:" && parsedUrl.protocol !== "https:") { setUrlError('"http(s)://" ile başlamalıdır.'); return false; }
            setUrlError(''); return true;
        } catch (_) { setUrlError('Geçerli URL formatı girin.'); return false; }
    }

    const handleUrlChange = (e) => { const newUrl = e.target.value; setUrl(newUrl); validateUrl(newUrl); };

    const handleUpload = async () => {
        setError('');
        if (!validateUrl(url)) { setError('Lütfen geçerli bir URL girin.'); return; }
        if (!fetchApi) { setError('API çağrı fonksiyonu eksik.'); setIsLoading(false); return; } // fetchApi kontrolü
        setIsLoading(true); setError('');
        try {
            await fetchApi(`/data_source/add_website`, {
                method: 'POST',
                body: JSON.stringify({ url: url })
            });
            setUrl(''); setUrlError('');
            if (onUploadSuccess) onUploadSuccess(sourceName || 'Website');
        } catch (err) {
            const errorMsg = err.message || 'Sunucuya bağlanılamadı.';
            setError(errorMsg);
            if(onUploadError) onUploadError(sourceName || 'Website', errorMsg);
        } finally { setIsLoading(false); }
    };

    return (
        <div>
            <h4>Web Sitesi İçeriği Ekle</h4>
            {urlError && <p className="error-message" style={{fontSize: '0.85em', padding: '4px 8px', marginTop: '-5px', marginBottom: '5px'}}>{urlError}</p>}
            <input
                type="url" placeholder="Web Sitesi URL (örn: https://example.com)" value={url}
                onChange={handleUrlChange} disabled={isLoading} aria-invalid={!!urlError}
                style={urlError ? {borderColor: '#e74c3c'} : {}} required
            />
             {error && <p className="error-message">{error}</p>}
            <button onClick={handleUpload} disabled={isLoading || !!urlError || !url.trim()}>
                 {isLoading ? 'Ekleniyor...' : 'Web Sitesi Ekle'}
            </button>
        </div>
    );
};

export default WebsiteUpload;