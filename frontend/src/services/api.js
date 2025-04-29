// Last reviewed: 2025-04-29 07:07:30 UTC (User: Teeksss)
// Adım 14: API Servisi (Placeholder - Alternatif Yapı)
// Bu yapı, hook yerine class veya fonksiyon tabanlı bir servis kullanmak isteyenler içindir.

const BASE_URL = 'http://localhost:8000/api';
let authToken = localStorage.getItem('authToken'); // Token'ı modül içinde tut

const setAuthToken = (token) => {
    authToken = token;
    if (token) {
        localStorage.setItem('authToken', token);
    } else {
        localStorage.removeItem('authToken');
    }
};

const request = async (endpoint, options = {}) => {
    const headers = { ...options.headers };

    if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }

    if (!(options.body instanceof FormData) && !headers['Content-Type']) {
        headers['Content-Type'] = 'application/json';
    }

    try {
        const response = await fetch(`${BASE_URL}${endpoint}`, {
            ...options,
            headers,
        });

        if (!response.ok) {
             let errorDetail = `HTTP Hata Kodu: ${response.status}`;
             try { const errorData = await response.json(); errorDetail = errorData.detail || errorDetail; } catch (e) { /* ignore */ }
             if (response.status === 401) {
                 console.error("Yetkilendirme Hatası - Token Temizleniyor...");
                 setAuthToken(null); // Token'ı temizle
                 // Login sayfasına yönlendir
                 // window.location.href = '/login';
             }
             throw new Error(errorDetail);
        }

        if (response.status === 204 || response.status === 202) {
             try { return await response.json(); }
             catch (e) { return { message: response.status === 202 ? "İstek kabul edildi." : "İçerik yok." }; }
        }
        return await response.json();
    } catch (error) {
        console.error("API Request Error:", error);
        throw error;
    }
};

// Örnek API metodları
const login = async (username, password) => {
    const response = await fetch(`${BASE_URL.replace('/api','')}/token`, { // Login endpoint'i farklı olabilir
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ username, password }),
    });
     if (!response.ok) { /* ... hata yönetimi ... */ throw new Error("Login failed"); }
     const data = await response.json();
     setAuthToken(data.access_token);
     // Kullanıcı bilgisini almak için ek istek gerekebilir (/users/me)
     // const user = await getUserProfile();
     return { token: data.access_token /*, user: user */ };
};

const getUserProfile = () => request('/users/me');
const search = (queryData, params) => request(`/query?${params.toString()}`, { method: 'POST', body: JSON.stringify(queryData) });
const listDataSources = (params) => request(`/data_source/list?${params.toString()}`);
const deleteDataSource = (docId) => request(`/data_source/delete/${docId}`, { method: 'DELETE' });
// ... diğer API metodları ...

const apiService = {
    setAuthToken,
    request,
    login,
    getUserProfile,
    search,
    listDataSources,
    deleteDataSource,
    // ... diğer metodlar ...
};

export default apiService;