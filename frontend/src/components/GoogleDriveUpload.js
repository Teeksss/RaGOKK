// Last reviewed: 2025-04-29 06:57:37 UTC (User: Teeksss)
import React, { useState } from 'react';

const GoogleDriveUpload = ({ onUploadSuccess, onUploadError, sourceName, fetchApi }) => {
    const [identifier, setIdentifier] = useState(''); // Dosya ID
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    const handleAuthorize = () => {
        // Yeni sekmede yetkilendirme URL'sini aç
        window.open('http://localhost:8000/auth/google/login', '_blank');
        setError('Yetkilendirme başlatıldı. Lütfen Google hesabınızla giriş yapıp izin verin ve ardından dosyayı ekleyin.');
    };

    const handleUpload = async () => {
        if (!identifier) { setError('Lütfen Google Drive Dosya ID\'sini girin.'); return; }
        if (!fetchApi) { setError('API çağrı fonksiyonu eksik.'); setIsLoading(false); return; } // fetchApi kontrolü
        setIsLoading(true); setError('');
        try {
            await fetchApi(`/data_source/add_google_drive`, {
                method: 'POST',
                body: JSON.stringify({ identifier: identifier })
            });
            setIdentifier(''); // Başarıda temizle
            if (onUploadSuccess) onUploadSuccess(sourceName || 'Google Drive');
        } catch (err) {
            const errorMsg = err.message || 'Google Drive işlenirken hata oluştu.';
             if (errorMsg.includes("401")) {
                 setError('Yetkilendirme gerekli veya geçersiz. Lütfen tekrar yetkilendirin.');
             } else {
                 setError(errorMsg);
             }
            if (onUploadError) onUploadError(sourceName || 'Google Drive', errorMsg);
        } finally { setIsLoading(false); }
    };

    return (
        <div>
            <h4>Google Drive Dosyası Ekle</h4>
            <button onClick={handleAuthorize} style={{marginBottom: '10px', backgroundColor: '#dd4b39'}}>Google ile Yetkilendir</button>
            <input type="text" placeholder="Dosya ID" value={identifier} onChange={e => setIdentifier(e.target.value)} disabled={isLoading} required />
            {error && <p className="error-message" style={{fontSize: '0.9em'}}>{error}</p>}
            <button onClick={handleUpload} disabled={isLoading || !identifier}>
                {isLoading ? 'Ekleniyor...' : 'Google Drive Ekle'}
            </button>
            <p><small>Dosyaya erişim için önce yetkilendirme yapmanız gerekir.</small></p>
        </div>
    );
};

export default GoogleDriveUpload;