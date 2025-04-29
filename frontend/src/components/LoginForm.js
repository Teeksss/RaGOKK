// Last reviewed: 2025-04-29 07:31:24 UTC (User: TeeksssLogin)
import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import Spinner from './ui/Spinner';
import { useToast } from '../contexts/ToastContext';

const LoginForm = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { login, isLoading } = useAuth();
  const { showToast } = useToast();
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!username.trim() || !password.trim()) {
      setError('Kullanıcı adı ve şifre gereklidir.');
      return;
    }
    
    try {
      await login(username, password);
      showToast('Başarıyla giriş yaptınız!', 'success');
    } catch (err) {
      setError(err.message || 'Giriş başarısız. Lütfen bilgilerinizi kontrol edin.');
      showToast('Giriş yapılamadı', 'error');
    }
  };
  
  return (
    <div className="login-container">
      <div className="login-form">
        <h2>RAG Base Uygulamasına Giriş</h2>
        {error && <div className="error-message login-error">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="username">Kullanıcı Adı</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={isLoading}
              required
              autoFocus
            />
          </div>
          <div className="form-group">
            <label htmlFor="password">Şifre</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading}
              required
            />
          </div>
          <button type="submit" disabled={isLoading} className="login-button">
            {isLoading ? <><Spinner size="small" /> Giriş Yapılıyor...</> : 'Giriş Yap'}
          </button>
        </form>
        <div className="login-footer">
          <p className="login-info">Deneme hesapları:</p>
          <p className="login-credentials">Admin: <b>TeeksssLogin / password123</b></p>
          <p className="login-credentials">Kullanıcı: <b>user / testpass</b></p>
        </div>
      </div>
    </div>
  );
};

export default LoginForm;