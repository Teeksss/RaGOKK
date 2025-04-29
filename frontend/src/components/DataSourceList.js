// Last reviewed: 2025-04-29 07:07:30 UTC (User: Teeksss)
import React, { useState, useEffect, useCallback } from 'react';

// ... ListItem bileşeni aynı ...

// Artık apiRequest prop'unu alıyor
const DataSourceList = ({ onDataSourceChange, onError, apiRequest }) => {
    const [dataSources, setDataSources] = useState([]);
    const [isLoadingLocal, setIsLoadingLocal] = useState(false); // Hook'un isLoading'i ile çakışmasın
    const [error, setError] = useState('');
    const [filter, setFilter] = useState('');
    const [deletingId, setDeletingId] = useState(null);
    const [onlyOriginals, setOnlyOriginals] = useState(true);

    const fetchDataSources = useCallback(async () => {
        if (typeof apiRequest !== 'function') { setError('API istek fonksiyonu eksik.'); return; }
        setIsLoadingLocal(true); setError('');
        try {
            const params = new URLSearchParams();
            if (filter) params.append('source', filter);
            if (onlyOriginals) params.append('only_originals', 'true');
            // apiRequest kullanılıyor
            const data = await apiRequest(`/data_source/list?${params.toString()}`);
            setDataSources(data || []);
        } catch (err) {
            const errorMsg = err.message || 'Sunucuya bağlanılamadı.';
            setError(errorMsg);
            if (onError) onError("Liste", errorMsg);
        } finally { setIsLoadingLocal(false); }
    }, [filter, onlyOriginals, apiRequest, onError]); // apiRequest bağımlılıklara eklendi

    useEffect(() => { fetchDataSources(); }, [fetchDataSources]);

    const handleDelete = useCallback(async (docId) => {
         if (typeof apiRequest !== 'function') { setError('API istek fonksiyonu eksik.'); return; }
        if (!window.confirm(`'${docId}' ID'li belgeyi (ve varsa chunk'larını) silmek istediğinizden emin misiniz?`)) return;
        setDeletingId(docId); setError('');
         try {
            // apiRequest kullanılıyor
            await apiRequest(`/data_source/delete/${docId}`, { method: 'DELETE' });
            setDataSources(prev => prev.filter(ds => ds.id !== docId));
        } catch (err) {
             const errorMsg = err.message || 'Sunucuya bağlanılamadı.';
             setError(errorMsg);
             if (onError) onError("Silme", errorMsg);
        } finally { setDeletingId(null); }
    }, [apiRequest, onError]); // apiRequest bağımlılıklara eklendi

    return (
        <div>
            {error && <p className="error-message">{error}</p>}
            {/* ... Filtreleme ve Yenileme Butonu ... */}
             <button onClick={fetchDataSources} disabled={isLoadingLocal || !!deletingId}>
                 {isLoadingLocal ? 'Yenileniyor...' : 'Yenile'}
             </button>
            {/* ... Liste veya Yükleniyor/Boş mesajı ... */}
            {isLoadingLocal ? <p>Yükleniyor...</p> : (
                 <ul>
                     {dataSources.map((ds) => (
                         <ListItem key={ds.id} ds={ds} onDelete={handleDelete} isDeleting={deletingId === ds.id}/>
                     ))}
                 </ul>
            )}
        </div>
    );
};

export default DataSourceList;