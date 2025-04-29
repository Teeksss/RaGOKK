// Last reviewed: 2025-04-29 07:07:30 UTC (User: Teeksss)
import React, { useState } from 'react';

// Artık apiRequest prop'unu alıyor
const AddDataSource = ({ onUploadSuccess, onUploadError, sourceName, apiRequest }) => {
    const [docId, setDocId] = useState('');
    const [text, setText] = useState('');
    const [isLoadingLocal, setIsLoadingLocal] = useState(false); // Hook'un isLoading'i ile çakışmasın
    const [error, setError] = useState('');
    const [idError, setIdError] = useState('');

    // ... validateId, handleIdChange ...

    const handleAdd = async () => {
        setError('');
        if (!validateId(docId) || !text.trim()) { setError('Lütfen gerekli alanları doğru şekilde doldurun.'); return; }
        if (typeof apiRequest !== 'function') { setError('API istek fonksiyonu eksik.'); return; }
        setIsLoadingLocal(true);
        try {
            // apiRequest kullanılıyor
            await apiRequest(`/data_source/add_manual`, {
                method: 'POST',
                body: JSON.stringify({ id: docId, text: text, source: 'manual' })
            });
            setDocId(''); setText(''); setIdError('');
            if (onUploadSuccess) onUploadSuccess(sourceName || 'Manuel');
        } catch (err) {
             const errorMsg = err.message || 'Sunucuya bağlanılamadı.';
             if (errorMsg.includes("409")) { setIdError("Bu ID zaten kullanılıyor."); setError(''); }
             else { setError(errorMsg); }
             if(onUploadError) onUploadError(sourceName || 'Manuel', errorMsg);
        } finally { setIsLoadingLocal(false); }
    };

    return (
        <div>
            <h4>Manuel Metin Ekle</h4>
            {/* ... inputlar ve buton ... */}
             <input type="text" value={docId} onChange={handleIdChange} disabled={isLoadingLocal} aria-invalid={!!idError} />
             <textarea value={text} onChange={(e) => setText(e.target.value)} disabled={isLoadingLocal} />
             {error && <p className="error-message">{error}</p>}
             {idError && <p className="error-message">{idError}</p>}
             <button onClick={handleAdd} disabled={isLoadingLocal || !!idError || !text.trim()}>
                 {isLoadingLocal ? 'Ekleniyor...' : 'Manuel Ekle'}
             </button>
        </div>
    );
};

export default AddDataSource;