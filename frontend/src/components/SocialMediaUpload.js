// Last reviewed: 2025-04-29 07:07:30 UTC (User: Teeksss)
import React, { useState } from 'react';

// Artık apiRequest prop'unu alıyor
const SocialMediaUpload = ({ onUploadSuccess, onUploadError, sourceName, apiRequest }) => {
    const [platform, setPlatform] = useState('twitter'); // Seçim için state
    // Twitter state'leri
    const [twitterQuery, setTwitterQuery] = useState('');
    const [twitterMaxResults, setTwitterMaxResults] = useState(10);
    // Facebook state'leri (placeholder)
    const [facebookPageId, setFacebookPageId] = useState('');
    // LinkedIn state'leri (placeholder)
    const [linkedinCompanyId, setLinkedinCompanyId] = useState('');

    const [isLoadingLocal, setIsLoadingLocal] = useState(false);
    const [error, setError] = useState('');

    const handleUpload = async () => {
        if (typeof apiRequest !== 'function') { setError('API istek fonksiyonu eksik.'); return; }
        setIsLoadingLocal(true); setError('');

        let endpoint = '';
        let payload = {};
        let currentSourceName = sourceName;

        try {
            if (platform === 'twitter') {
                if (!twitterQuery) throw new Error('Lütfen bir Twitter arama sorgusu girin.');
                endpoint = '/data_source/add_twitter';
                payload = { query: twitterQuery, max_results: parseInt(twitterMaxResults) || 10 };
                currentSourceName = 'Twitter';
            } else if (platform === 'facebook') {
                // Adım 15: Facebook Placeholder
                 if (!facebookPageId) throw new Error('Lütfen Facebook Sayfa ID\'sini girin.');
                 endpoint = '/data_source/add_facebook'; // Henüz implemente edilmedi
                 payload = { page_id: facebookPageId, max_results: 10 }; // Token eksik
                 currentSourceName = 'Facebook';
                 // throw new Error("Facebook entegrasyonu henüz tamamlanmadı."); // Veya API'nin 501 dönmesini bekle
            } else if (platform === 'linkedin') {
                // Adım 15: LinkedIn Placeholder
                 if (!linkedinCompanyId) throw new Error('Lütfen LinkedIn Şirket ID/URN\'sini girin.');
                 endpoint = '/data_source/add_linkedin'; // Henüz implemente edilmedi
                 payload = { company_urn_or_id: linkedinCompanyId, max_results: 10 }; // Token eksik
                 currentSourceName = 'LinkedIn';
                 // throw new Error("LinkedIn entegrasyonu henüz tamamlanmadı."); // Veya API'nin 501 dönmesini bekle
            } else {
                throw new Error("Geçersiz platform seçildi.");
            }

            // apiRequest kullanılıyor
            await apiRequest(endpoint, {
                method: 'POST',
                body: JSON.stringify(payload)
            });

            // Başarıda ilgili state'leri temizle
            if (platform === 'twitter') setTwitterQuery('');
            if (platform === 'facebook') setFacebookPageId('');
            if (platform === 'linkedin') setLinkedinCompanyId('');

            if (onUploadSuccess) onUploadSuccess(currentSourceName);
        } catch (err) {
            const errorMsg = err.message || 'Sosyal medya işlenirken hata oluştu.';
            setError(errorMsg);
            if (onUploadError) onUploadError(currentSourceName || 'Sosyal Medya', errorMsg);
        } finally { setIsLoadingLocal(false); }
    };

    return (
        <div>
            <h4>Sosyal Medya İçeriği Ekle</h4>
             <select value={platform} onChange={e => setPlatform(e.target.value)} disabled={isLoadingLocal} style={{marginBottom: '10px'}}>
                 <option value="twitter">Twitter</option>
                 <option value="facebook" disabled>Facebook (Yakında)</option>
                 <option value="linkedin" disabled>LinkedIn (Yakında)</option>
             </select>

             {platform === 'twitter' && (
                 <>
                     <p><small>Global Twitter Bearer Token yapılandırılmış olmalı.</small></p>
                     <input type="text" placeholder="Twitter Arama Sorgusu" value={twitterQuery} onChange={e => setTwitterQuery(e.target.value)} disabled={isLoadingLocal} required />
                     <input type="number" placeholder="Maksimum Tweet (10-100)" value={twitterMaxResults} onChange={e => setTwitterMaxResults(e.target.value)} disabled={isLoadingLocal} min="10" max="100" required/>
                 </>
             )}
             {platform === 'facebook' && (
                 <>
                    <p><small>Facebook entegrasyonu henüz tamamlanmadı.</small></p>
                    <input type="text" placeholder="Facebook Sayfa ID" value={facebookPageId} onChange={e => setFacebookPageId(e.target.value)} disabled={isLoadingLocal} required />
                 </>
             )}
              {platform === 'linkedin' && (
                 <>
                    <p><small>LinkedIn entegrasyonu henüz tamamlanmadı.</small></p>
                    <input type="text" placeholder="LinkedIn Şirket ID veya URN" value={linkedinCompanyId} onChange={e => setLinkedinCompanyId(e.target.value)} disabled={isLoadingLocal} required />
                 </>
             )}

            {error && <p className="error-message">{error}</p>}
            <button
                onClick={handleUpload}
                disabled={isLoadingLocal || (platform === 'twitter' && !twitterQuery) || (platform === 'facebook' && !facebookPageId) || (platform === 'linkedin' && !linkedinCompanyId) || platform === 'facebook' || platform === 'linkedin'} // FB/LI butonları devre dışı
            >
                {isLoadingLocal ? 'Ekleniyor...' : `${platform.charAt(0).toUpperCase() + platform.slice(1)} Ekle`}
            </button>
        </div>
    );
};

export default SocialMediaUpload;