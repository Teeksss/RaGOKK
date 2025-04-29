// Last reviewed: 2025-04-29 07:07:30 UTC (User: Teeksss)
// Adım 14: API Hook (Placeholder)
import { useState, useCallback } from 'react';
// import { useAuth } from '../contexts/AuthContext'; // Auth context'ten token almak için

const BASE_URL = 'http://localhost:8000/api'; // API prefix dahil

const useApi = () => {
    // const { token, logout } = useAuth(); // Token ve logout fonksiyonunu al
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);

    const apiRequest = useCallback(async (endpoint, options = {}) => {
        setIsLoading(true);
        setError(null);

        const headers = { ...options.headers };
        const currentToken = localStorage.getItem('authToken'); // VEYA context'ten: token

        if (currentToken) {
            headers['Authorization'] = `Bearer ${currentToken}`;
        }

        // Content-Type ayarı (App.js'deki gibi)
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
                try {
                    const errorData = await response.json();
                    errorDetail = errorData.detail || errorDetail;
                } catch (e) { /* ignore */ }

                // 401 Unauthorized durumunda otomatik logout yapılabilir
                if (response.status === 401) {
                    console.error("Yetkilendirme Hatası - Otomatik Çıkış Yapılıyor...");
                    // logout(); // Auth context'ten gelen logout fonksiyonu
                    localStorage.removeItem('authToken'); // Manuel temizleme (eğer context yoksa)
                    window.location.reload(); // Sayfayı yenile (login'e yönlendirmek daha iyi)
                }
                throw new Error(errorDetail);
            }

            // 202/204 durumları için kontrol
            if (response.status === 204 || response.status === 202) {
                 try { return await response.json(); }
                 catch (e) { return { message: response.status === 202 ? "İstek kabul edildi." : "İçerik yok." }; }
            }

            return await response.json();

        } catch (err) {
            setError(err.message || 'Bilinmeyen bir hata oluştu.');
            throw err; // Hatanın bileşen tarafından yakalanabilmesi için tekrar fırlat
        } finally {
            setIsLoading(false);
        }
    }, [/* token, logout */]); // Token değiştiğinde bu hook'un güncellenmesi gerekebilir

    return { apiRequest, isLoading, error };
};

export default useApi;