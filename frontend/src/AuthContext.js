// Last reviewed: 2025-04-29 07:01:44 UTC (User: Teeksss) - YENİ DOSYA
import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [token, setToken] = useState(localStorage.getItem('authToken'));
    const [user, setUser] = useState(null); // Kullanıcı bilgileri (opsiyonel)
    const [authLoading, setAuthLoading] = useState(true); // Başlangıçta token kontrolü için

    // API çağrı fonksiyonu (token'ı otomatik ekler)
    const fetchApi = useCallback(async (url, options = {}) => {
        const headers = { ...options.headers };
        const currentToken = localStorage.getItem('authToken'); // Her zaman güncel token'ı al
        if (currentToken) {
            headers['Authorization'] = `Bearer ${currentToken}`;
        }
        if (!(options.body instanceof FormData) && !headers['Content-Type']) {
            headers['Content-Type'] = 'application/json';
        }

        const response = await fetch(`http://localhost:8000/api${url}`, { // /api prefix
            ...options,
            headers,
        });

        if (!response.ok) {
            let errorDetail = `HTTP Hata Kodu: ${response.status}`;
            try {
                const errorData = await response.json();
                errorDetail = errorData.detail || errorDetail;
            } catch (e) { /* ignore */ }
            // Yetki hatasında otomatik logout yap
            if (response.status === 401) {
                console.error("Yetki hatası (401), çıkış yapılıyor.");
                logout(); // Otomatik logout
            }
            throw new Error(errorDetail);
        }
        if (response.status === 204 || response.status === 202) {
             try { return await response.json(); } catch (e) { return { message: "İstek kabul edildi." }; }
        }
        return await response.json();
    }, []); // Bağımlılık yok (logout hariç ama onu aşağıda handle edeceğiz)

    const fetchUserInfo = useCallback(async (currentToken) => {
        if (!currentToken) { setUser(null); setAuthLoading(false); return; }
        setAuthLoading(true);
        try {
            // fetchApi'yi burada direkt kullanamayız (bağımlılık döngüsü), ayrı fetch yapalım
            const response = await fetch('http://localhost:8000/users/me', {
                headers: { 'Authorization': `Bearer ${currentToken}` }
            });
            if (response.ok) {
                const userData = await response.json();
                setUser(userData);
            } else {
                // Token geçersizse logout yap
                console.error("Kullanıcı bilgisi alınamadı, token geçersiz olabilir.");
                logout(); // Otomatik logout
            }
        } catch (error) {
            console.error("Kullanıcı bilgisi alınırken hata:", error);
            logout(); // Hata durumunda da logout yap
        } finally {
            setAuthLoading(false);
        }
    }, []); // `logout` bağımlılığı sorun yaratabilir, dikkat

    const login = useCallback((newToken) => {
        localStorage.setItem('authToken', newToken);
        setToken(newToken);
        fetchUserInfo(newToken); // Giriş yapınca kullanıcı bilgisini çek
    }, [fetchUserInfo]);

    const logout = useCallback(() => {
        localStorage.removeItem('authToken');
        setToken(null);
        setUser(null);
        // Gerekirse login sayfasına yönlendir
        // window.location.href = '/login';
    }, []);

    // Uygulama ilk yüklendiğinde token varsa kullanıcı bilgisini çek
    useEffect(() => {
        const currentToken = localStorage.getItem('authToken');
        if (currentToken) {
            fetchUserInfo(currentToken);
        } else {
            setAuthLoading(false); // Token yoksa yüklemeyi bitir
        }
    }, [fetchUserInfo]); // Sadece bir kere çalışmalı

     // fetchApi'yi logout bağımlılığı olmadan tanımla (logout içeride çağrılıyor)
     const memoizedFetchApi = useCallback(fetchApi, []);

    return (
        <AuthContext.Provider value={{ token, user, login, logout, fetchApi: memoizedFetchApi, authLoading }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};