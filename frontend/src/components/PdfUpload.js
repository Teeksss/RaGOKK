// Last reviewed: 2025-04-29 06:57:37 UTC (User: Teeksss)
import React, { useState } from 'react';

const PdfUpload = ({ onUploadSuccess, onUploadError, sourceName, fetchApi }) => {
    const [file, setFile] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');
    const fileInputRef = React.useRef(); // Input'u temizlemek için ref

    const handleFileChange = (event) => {
        setFile(event.target.files[0]);
        setError('');
    };

    const handleUpload = async () => {
        if (!file) { setError('Lütfen bir PDF dosyası seçin.'); return; }
        if (!fetchApi) { setError('API çağrı fonksiyonu eksik.'); setIsLoading(false); return; } // fetchApi kontrolü
        setIsLoading(true); setError('');
        const formData = new FormData();
        formData.append('file', file);

        try {
            await fetchApi(`/data_source/add_file`, {
                method: 'POST',
                body: formData,
            });
            setFile(null);
            if(fileInputRef.current) fileInputRef.current.value = ""; // Input'u temizle
            if (onUploadSuccess) onUploadSuccess(sourceName || 'PDF');
        } catch (err) {
            const errorMsg = err.message || 'Dosya yüklenirken hata oluştu.';
            setError(errorMsg);
            if (onUploadError) onUploadError(sourceName || 'PDF', errorMsg);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div>
            <h4>PDF Dosyası Yükle</h4>
            <input
                ref={fileInputRef} // Ref eklendi
                type="file"
                accept="application/pdf"
                onChange={handleFileChange}
                disabled={isLoading}
            />
            {error && <p className="error-message">{error}</p>}
            <button onClick={handleUpload} disabled={isLoading || !file}>
                {isLoading ? 'Yükleniyor...' : 'PDF Yükle'}
            </button>
            <p><small>PDF dosyasının metin içeriği çıkarılacaktır.</small></p>
        </div>
    );
};

export default PdfUpload;