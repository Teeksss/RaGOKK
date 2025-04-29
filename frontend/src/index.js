// Last reviewed: 2025-04-29 07:07:30 UTC (User: Teeksss)
import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './webVitals';
// Adım 12: State Management (Placeholder)
// import { AuthProvider } from './contexts/AuthContext'; // Auth Context'i import et

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    {/* Adım 12: State Management (Placeholder) */}
    {/* <AuthProvider> */}
      <App />
    {/* </AuthProvider> */}
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();