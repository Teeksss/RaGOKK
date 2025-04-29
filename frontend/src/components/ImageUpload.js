// Last reviewed: 2025-04-29 06:57:37 UTC (User: Teeksss)
import React, { useState } from 'react';

const ImageUpload = ({ onUploadSuccess, onUploadError, sourceName, fetchApi }) => {
    const [file, setFile] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');
    const fileInputRef = React.useRef(); // Input'u temizlemek için ref

    const handleFileChange = (event) => {
        setFile(event.target.files[0]);
        setError('');
    };

    const handleUpload = async () => {
        if (!file) { setError('Lütfen bir resim dosyası seçin.'); return; }
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
            if (onUploadSuccess) onUploadSuccess(sourceName || 'Resim');
        } catch (err) {
            const errorMsg = err.message || 'Dosya yüklenirken hata oluştu.';
            setError(errorMsg);
            if (onUploadError) onUploadError(sourceName || 'Resim', errorMsg);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div>
            <h4>Resim Dosyası Yükle (OCR)</h4>
            <input
                ref={fileInputRef} // Ref eklendi
                type="file"
                accept="image/png, image/jpeg, image/tiff, image/bmp, image/gif"
                onChange={handleFileChange}
                disabled={isLoading}
            />
            {error && <p className="error-message">{error}</p>}
            <button onClick={handleUpload} disabled={isLoading || !file}>
                {isLoading ? 'Yükleniyor...' : 'Resim Yükle'}
            </button>
             <p><small>Desteklenen formatlar: PNG, JPG, TIFF, BMP, GIF. Metin içeriği OCR ile çıkarılacaktır.</small></p>
        </div>
    );
};

export default ImageUpload;