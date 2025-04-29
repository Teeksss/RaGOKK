// Last reviewed: 2025-04-29 06:57:37 UTC (User: Teeksss)
import React, { useState } from 'react';

const MongoDbUpload = ({ onUploadSuccess, onUploadError, sourceName, fetchApi }) => {
    const [host, setHost] = useState('localhost:27017');
    const [database, setDatabase] = useState('');
    const [collectionName, setCollectionName] = useState('');
    const [user, setUser] = useState('');
    const [password, setPassword] = useState('');
    const [query, setQuery] = useState('{}');
    const [projection, setProjection] = useState('');
    const [limit, setLimit] = useState(0);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    const handleUpload = async () => {
        if (!host || !database || !collectionName) { setError('Host, Veritabanı ve Koleksiyon adları zorunludur.'); return; }
        if (!fetchApi) { setError('API çağrı fonksiyonu eksik.'); setIsLoading(false); return; } // fetchApi kontrolü

        let parsedQuery = {}; let parsedProjection = null;
        try { parsedQuery = JSON.parse(query || '{}'); } catch (e) { setError('Query geçerli bir JSON değil.'); return; }
        if (projection) { try { parsedProjection = JSON.parse(projection); } catch (e) { setError('Projection geçerli bir JSON değil.'); return; } }

        setIsLoading(true); setError('');
        try {
            const payload = {
                host, database, collection_name: collectionName,
                user: user || null, password: password || null,
                query: parsedQuery, projection: parsedProjection,
                limit: parseInt(limit) || 0
            };
            await fetchApi(`/data_source/add_mongodb`, {
                method: 'POST',
                body: JSON.stringify(payload)
            });
            // Formu temizle?
            if (onUploadSuccess) onUploadSuccess(sourceName || 'MongoDB');
        } catch (err) {
            const errorMsg = err.message || 'MongoDB işlenirken hata oluştu.';
            setError(errorMsg);
            if (onUploadError) onUploadError(sourceName || 'MongoDB', errorMsg);
        } finally { setIsLoading(false); }
    };

    return (
        <div>
            <h4>MongoDB Verisi Ekle</h4>
            <input type="text" placeholder="Host (örn: localhost:27017)" value={host} onChange={e => setHost(e.target.value)} disabled={isLoading} required />
            <input type="text" placeholder="Veritabanı Adı" value={database} onChange={e => setDatabase(e.target.value)} disabled={isLoading} required />
            <input type="text" placeholder="Koleksiyon Adı" value={collectionName} onChange={e => setCollectionName(e.target.value)} disabled={isLoading} required />
            <input type="text" placeholder="Kullanıcı Adı (opsiyonel)" value={user} onChange={e => setUser(e.target.value)} disabled={isLoading} />
            <input type="password" placeholder="Şifre (opsiyonel)" value={password} onChange={e => setPassword(e.target.value)} disabled={isLoading} />
            <textarea placeholder='Query (JSON, örn: {"alan": "değer"})' value={query} onChange={e => setQuery(e.target.value)} disabled={isLoading} rows={3} />
            <textarea placeholder='Projection (JSON, opsiyonel, örn: {"alan1": 1})' value={projection} onChange={e => setProjection(e.target.value)} disabled={isLoading} rows={2}/>
            <input type="number" placeholder="Limit (0=limitsiz)" value={limit} onChange={e => setLimit(e.target.value)} disabled={isLoading} min="0"/>
            {error && <p className="error-message">{error}</p>}
            <button onClick={handleUpload} disabled={isLoading || !host || !database || !collectionName}>
                {isLoading ? 'Ekleniyor...' : 'MongoDB Ekle'}
            </button>
        </div>
    );
};

export default MongoDbUpload;