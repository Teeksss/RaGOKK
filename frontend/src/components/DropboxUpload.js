// Last reviewed: 2025-04-29 06:57:37 UTC (User: Teeksss)
import React, { useState } from 'react';

const DropboxUpload = ({ onUploadSuccess, onUploadError, sourceName, fetchApi }) => {
    const [identifier, setIdentifier] = useState(''); // Dosya Yolu
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    // TODO: Dropbox için kullanıcı bazlı OAuth akışı eklenmeli.

    const handleUpload = async () => {
        if (!identifier) { setError('Lütfen Dropbox dosya yolunu girin.'); return; }
        if (!fetchApi) { setError('API çağrı fonksiyonu eksik.'); setIsLoading(false); return; } // fetchApi kontrolü
        setIsLoading(true); setError('');
        try {
            await fetchApi(`/data_source/add_dropbox`, {
                method: 'POST',
                body: JSON.stringify({ identifier: identifier })
            });
            setIdentifier('');
            if (onUploadSuccess) onUploadSuccess(sourceName || 'Dropbox');
        } catch (err) {
            const errorMsg = err.message || 'Dropbox işlenirken hata oluştu.';
            setError(errorMsg);
            if (onUploadError) onUploadError(sourceName || 'Dropbox', errorMsg);
        } finally { setIsLoading(false); }
    };

    return (
        <div>
            <h4>Dropbox Dosyası Ekle</h4>
             <p><small>Global token yapılandırılmış olmalı. Dosya yolunu girin (örn: /klasor/dosya.txt).</small></p>
            <input type="text" placeholder="Dosya Yolu" value={identifier} onChange={e => setIdentifier(e.target.value)} disabled={isLoading} required />
            {error && <p className="error-message">{error}</p>}
            <button onClick={handleUpload} disabled={isLoading || !identifier}>
                {isLoading ? 'Ekleniyor...' : 'Dropbox Ekle'}
            </button>
        </div>
    );
};

export default DropboxUpload;