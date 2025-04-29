// Last reviewed: 2025-04-29 06:57:37 UTC (User: Teeksss)
import React, { useState } from 'react';

const PostgreSqlUpload = ({ onUploadSuccess, onUploadError, sourceName, fetchApi }) => {
    const [host, setHost] = useState('localhost');
    const [port, setPort] = useState(5432);
    const [database, setDatabase] = useState('');
    const [user, setUser] = useState('');
    const [password, setPassword] = useState('');
    const [tableName, setTableName] = useState('');
    const [columns, setColumns] = useState('');
    const [limit, setLimit] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    const handleUpload = async () => {
        if (!database || !user || !password || !tableName) { setError('Lütfen tüm gerekli alanları doldurun.'); return; }
        if (!fetchApi) { setError('API çağrı fonksiyonu eksik.'); setIsLoading(false); return; } // fetchApi kontrolü
        setIsLoading(true); setError('');
        try {
            const payload = {
                host, port: parseInt(port) || 5432, database, user, password, table_name: tableName,
                columns: columns ? columns.split(',').map(c => c.trim()).filter(c => c) : null,
                limit: limit ? parseInt(limit) : null
            };
            await fetchApi(`/data_source/add_postgresql`, {
                method: 'POST',
                body: JSON.stringify(payload)
            });
            // Formu temizle?
            if (onUploadSuccess) onUploadSuccess(sourceName || 'PostgreSQL');
        } catch (err) {
            const errorMsg = err.message || 'Veritabanı işlenirken hata oluştu.';
            setError(errorMsg);
            if (onUploadError) onUploadError(sourceName || 'PostgreSQL', errorMsg);
        } finally { setIsLoading(false); }
    };

    return (
        <div>
            <h4>PostgreSQL Verisi Ekle</h4>
            <input type="text" placeholder="Host (örn: localhost)" value={host} onChange={e => setHost(e.target.value)} disabled={isLoading} required />
            <input type="number" placeholder="Port (örn: 5432)" value={port} onChange={e => setPort(e.target.value)} disabled={isLoading} required />
            <input type="text" placeholder="Veritabanı Adı" value={database} onChange={e => setDatabase(e.target.value)} disabled={isLoading} required />
            <input type="text" placeholder="Kullanıcı Adı" value={user} onChange={e => setUser(e.target.value)} disabled={isLoading} required />
            <input type="password" placeholder="Şifre" value={password} onChange={e => setPassword(e.target.value)} disabled={isLoading} required />
            <input type="text" placeholder="Tablo Adı" value={tableName} onChange={e => setTableName(e.target.value)} disabled={isLoading} required />
            <input type="text" placeholder="Sütunlar (virgülle ayır, boşsa tümü)" value={columns} onChange={e => setColumns(e.target.value)} disabled={isLoading} />
            <input type="number" placeholder="Limit (opsiyonel)" value={limit} onChange={e => setLimit(e.target.value)} disabled={isLoading} min="1"/>
            {error && <p className="error-message">{error}</p>}
            <button onClick={handleUpload} disabled={isLoading || !database || !user || !password || !tableName}>
                {isLoading ? 'Ekleniyor...' : 'PostgreSQL Ekle'}
            </button>
        </div>
    );
};

export default PostgreSqlUpload;