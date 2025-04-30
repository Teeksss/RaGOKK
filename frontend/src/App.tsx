// Last reviewed: 2025-04-30 13:00:37 UTC (User: TeeksssPrompt)
// ... mevcut importlar ...

// Yeni admin sayfalarını lazy yükle
const PromptTemplateManagement = React.lazy(() => import('./pages/admin/PromptTemplateManagement'));
const RetrievalStrategyManagement = React.lazy(() => import('./pages/admin/RetrievalStrategyManagement'));

// ... mevcut kodlar ...

// App bileşeni - routeları güncelle
const App: React.FC = () => {
  // ... mevcut kodlar ...
  
  return (
    // ... mevcut JSX ...
    
    <Routes>
      {/* ... mevcut rot
