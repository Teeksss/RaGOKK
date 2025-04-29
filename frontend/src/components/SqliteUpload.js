// Last reviewed: 2025-04-29 06:57:37 UTC (User: Teeksss)
import React, { useState } from 'react';

const SqliteUpload = ({ onUploadSuccess, onUploadError, sourceName, fetchApi }) => {
    const [dbPath, setDbPath] = useState('');
    const [tableName, setTableName] = useState('');
    const [columns, setColumns] = useState('');
    const [limit, setLimit] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    const handleUpload = async () => {
        if (!dbPath || !tableName) { setError('Lütfen veritabanı yolu ve tablo adını girin.'); return; }
        if (!fetchApi) { setError('API çağrı fonksiyonu eksik.'); setIsLoading(false); return; } // fetchApi kontrolü
        setIsLoading(true); setError('');
        try {
            const payload = {
                db_path: dbPath, table_name: tableName,
                columns: columns ? columns.split(',').map(c => c.trim()).filter(c => c) : null,
                limit: limit ? parseInt(limit) : null
            };
            await fetchApi(`/data_source/add_sqlite`, {
                method: 'POST',
                body: JSON.stringify(payload)
            });
             // Formu temizle?
            if (onUploadSuccess) onUploadSuccess(sourceName || 'SQLite');
        } catch (err) {
            const errorMsg = err.message || 'SQLite işlenirken hata oluştu.';
            setError(errorMsg);
            if (onUploadError) onUploadError(sourceName || 'SQLite', errorMsg);
        } finally { setIsLoading(false); }
    };

    return (
        <div>
            <h4>SQLite Verisi Ekle (Admin)</h4>
             <p><small>Sunucudaki SQLite dosyasının tam yolunu girin.</small></p>
            <input type="text" placeholder="Veritabanı Dosya Yolu (Sunucuda)" value={dbPath} onChange={e => setDbPath(e.target.value)} disabled={isLoading} required />
            <input type="text" placeholder="Tablo Adı" value={tableName} onChange={e => setTableName(e.target.value)} disabled={isLoading} required />
            <input type="text" placeholder="Sütunlar (virgülle ayır, boşsa tümü)" value={columns} onChange={e => setColumns(e.target.value)} disabled={isLoading} />
            <input type="number" placeholder="Limit (opsiyonel)" value={limit} onChange={e => setLimit(e.target.value)} disabled={isLoading} min="1"/>
            {error && <p className="error-message">{error}</p>}
            <button onClick={handleUpload} disabled={isLoading || !dbPath || !tableName}>
                {isLoading ? 'Ekleniyor...' : 'SQLite Ekle'}
            </button>
        </div>
    );
};

export default SqliteUpload;