// Last reviewed: 2025-04-29 06:57:37 UTC (User: Teeksss)
import React, { useState } from 'react';

const EmailUpload = ({ onUploadSuccess, onUploadError, sourceName, fetchApi }) => {
    const [mailbox, setMailbox] = useState('inbox');
    const [criteria, setCriteria] = useState('ALL');
    const [numLatest, setNumLatest] = useState(10);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    const handleUpload = async () => {
        if (!fetchApi) { setError('API çağrı fonksiyonu eksik.'); setIsLoading(false); return; } // fetchApi kontrolü
        setIsLoading(true); setError('');
        try {
            const payload = { mailbox, criteria, num_latest: parseInt(numLatest) || 10 }; // Default 10
            await fetchApi(`/data_source/add_email`, {
                method: 'POST',
                body: JSON.stringify(payload)
            });
            if (onUploadSuccess) onUploadSuccess(sourceName || 'Email');
        } catch (err) {
            const errorMsg = err.message || 'E-posta işlenirken hata oluştu.';
            setError(errorMsg);
            if (onUploadError) onUploadError(sourceName || 'Email', errorMsg);
        } finally { setIsLoading(false); }
    };

    return (
        <div>
            <h4>E-postaları İndeksle</h4>
             <p><small>.env dosyasında yapılandırılmış hesaptan e-postalar çekilir.</small></p>
            <input type="text" placeholder="Posta Kutusu (örn: inbox)" value={mailbox} onChange={e => setMailbox(e.target.value)} disabled={isLoading} required />
            <input type="text" placeholder="Arama Kriteri (IMAP, örn: ALL)" value={criteria} onChange={e => setCriteria(e.target.value)} disabled={isLoading} required />
            <input type="number" placeholder="En Son Kaç E-posta" value={numLatest} onChange={e => setNumLatest(e.target.value)} disabled={isLoading} min="1" max="1000" required/>
            {error && <p className="error-message">{error}</p>}
            <button onClick={handleUpload} disabled={isLoading}>
                {isLoading ? 'Ekleniyor...' : 'E-postaları Ekle'}
            </button>
        </div>
    );
};

export default EmailUpload;