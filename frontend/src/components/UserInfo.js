// Last reviewed: 2025-04-29 06:57:37 UTC (User: Teeksss)
import React from 'react';
// import useAuth from '../hooks/useAuth'; // Örnek

const UserInfo = () => {
    // TODO: Gerçek kullanıcı bilgisini auth context/hook'tan al.
    // const { user, logout } = useAuth();
    const user = { username: "Teeksss" }; // Placeholder
    const isLoggedIn = user && user.username; // Basit kontrol - GERÇEK KONTROL GEREKLİ
    const loginTime = "2025-04-29 06:57:37 UTC"; // Placeholder

    const handleLogout = () => {
        alert('Çıkış yapma işlevi henüz eklenmedi.');
        // logout(); // Örnek
        // TODO: Token'ı sil ve login sayfasına yönlendir.
    };

    return (
        <div style={{ textAlign: 'right', fontSize: '0.9em', color: '#bdc3c7' }}>
            {isLoggedIn ? (
                <>
                    <span>Kullanıcı: {user.username}</span>
                    <br />
                    <span style={{fontSize: '0.8em'}}>Oturum Başlangıcı (Yaklaşık): {loginTime}</span>
                    {/* <button onClick={handleLogout} style={{ marginLeft: '15px', padding: '5px 10px', fontSize: '0.9em', backgroundColor: '#f39c12' }}>
                        Çıkış Yap
                    </button> */}
                </>
            ) : (
                 <span>Giriş Yapılmadı</span>
                 // TODO: Giriş yapma linki/butonu eklenebilir.
            )}
        </div>
    );
};

export default UserInfo;