// Last reviewed: 2025-04-30 11:44:29 UTC (User: Teeksssdevam)
import React, { useState, useEffect, Suspense } from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import { Container, Spinner } from 'react-bootstrap';

// Contexts
import { AuthProvider } from './contexts/AuthContext';
import { ToastProvider } from './contexts/ToastContext';
import { ThemeProvider } from './contexts/ThemeContext';
import { QueryProvider } from './contexts/QueryContext';
import { NotificationProvider } from './components/common/NotificationSystem';
import { GlobalStateProvider } from './contexts/GlobalStateContext';

// Layout Components
import AppNavbar from './components/layout/AppNavbar';
import Footer from './components/layout/Footer';
import Sidebar from './components/layout/Sidebar';

// Common Components
import AccessibilityTools from './components/common/AccessibilityTools';
import OnboardingTour from './components/onboarding/OnboardingTour';
import UserOnboarding from './components/onboarding/UserOnboarding';
import ContentLoader, { LoaderType } from './components/common/ContentLoader';
import OfflineAlert from './components/common/OfflineAlert';
import PageTransition, { TransitionType } from './components/transitions/PageTransition';
import { GlobalErrorBoundary, PageErrorBoundary } from './components/error/GlobalErrorBoundary';
import { PerformanceWarningBanner } from './services/performanceService';

// PWA Components
import UpdateNotification from './components/pwa/UpdateNotification';
import InstallPrompt from './components/pwa/InstallPrompt';

// Services
import { setupCacheCleanup } from './services/cacheService';
import { analyticsService, EventCategory, EventAction } from './services/analyticsService';
import { performanceService } from './services/performanceService';
import { errorHandlingService } from './services/errorHandlingService';

// Lazy load pages for better performance
const Dashboard = React.lazy(() => import('./pages/Dashboard'));
const Documents = React.lazy(() => import('./pages/Documents'));
const Query = React.lazy(() => import('./pages/Query'));
const MultimodalQuery = React.lazy(() => import('./pages/MultimodalQuery'));
const QueryHistory = React.lazy(() => import('./pages/QueryHistory'));
const DocumentDetail = React.lazy(() => import('./pages/DocumentDetail'));
const Profile = React.lazy(() => import('./pages/Profile'));
const Settings = React.lazy(() => import('./pages/Settings'));

// Auth pages
const Login = React.lazy(() => import('./pages/auth/Login'));
const Register = React.lazy(() => import('./pages/auth/Register'));
const ForgotPassword = React.lazy(() => import('./pages/auth/ForgotPassword'));
const ResetPassword = React.lazy(() => import('./pages/auth/ResetPassword'));
const TwoFactorAuth = React.lazy(() => import('./pages/auth/TwoFactorAuth'));
const TwoFactorSetup = React.lazy(() => import('./pages/auth/TwoFactorSetup'));

// Admin Pages
const AdminDashboard = React.lazy(() => import('./pages/admin/AdminDashboard'));
const UserManagement = React.lazy(() => import('./pages/admin/UserManagement'));
const OrganizationManagement = React.lazy(() => import('./pages/admin/OrganizationManagement'));
const SystemSettings = React.lazy(() => import('./pages/admin/SystemSettings'));
const SystemMonitoring = React.lazy(() => import('./pages/admin/SystemMonitoring'));

// Protected Route Component
import ProtectedRoute from './components/auth/ProtectedRoute';
import RoleProtectedRoute from './components/auth/RoleProtectedRoute';
import PermissionProtectedRoute from './components/auth/PermissionProtectedRoute';

// Other Components
const NotFound = React.lazy(() => import('./components/common/NotFound'));
const UnauthorizedPage = React.lazy(() => import('./components/common/UnauthorizedPage'));
const MaintenancePage = React.lazy(() => import('./components/common/MaintenancePage'));
const HelpCenter = React.lazy(() => import('./pages/HelpCenter'));
const Documentation = React.lazy(() => import('./pages/Documentation'));

// Analytics and Monitoring
import { useAnalytics } from './services/analyticsService';
import { useDeepMemo } from './utils/memoization';

// Fallback loading component for lazy loading
const PageLoadingFallback = () => (
  <div className="d-flex justify-content-center align-items-center" style={{ height: '80vh' }}>
    <Spinner animation="border" role="status" variant="primary">
      <span className="visually-hidden">Loading...</span>
    </Spinner>
  </div>
);

const App: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(false);
  const [isMaintenanceMode, setIsMaintenanceMode] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [showOnboarding, setShowOnboarding] = useState<boolean>(false);
  const [transitionType, setTransitionType] = useState<TransitionType>(TransitionType.FADE);
  
  // Cache temizleme zamanlaması
  useEffect(() => {
    setupCacheCleanup();
  }, []);
  
  // Performans izleme
  useEffect(() => {
    performanceService.addCustomMetric('AppInitialization', performance.now());
    
    // Kritik bileşen yükleme zamanlamaları
    const componentLoadTimer = performanceService.startTimer('ComponentLoadingTime');
    
    // Timer'ı uygulama tamamen yüklendiğinde durdur
    return () => {
      componentLoadTimer();
    };
  }, []);
  
  // Bakım modu kontrolü
  useEffect(() => {
    const checkMaintenanceMode = async () => {
      try {
        setIsLoading(true);
        
        const startTime = performance.now();
        
        const response = await fetch('/api/v1/system/status');
        const data = await response.json();
        
        // API yanıt süresini ölç
        performanceService.addCustomMetric('MaintenanceModeAPIResponseTime', performance.now() - startTime);
        
        setIsMaintenanceMode(data.maintenance_mode || false);
        setError(null);
        
        // Bakım modu değişikliğini izle
        if (data.maintenance_mode) {
          analyticsService.trackEvent({
            category: EventCategory.NAVIGATION,
            action: 'MaintenanceMode',
            label: 'Active'
          });
        }
      } catch (error) {
        console.error('Error checking maintenance mode:', error);
        
        // Hatayı bildir
        errorHandlingService.handleError({
          message: 'Unable to connect to server. Please try again later.',
          details: error
        });
        
        setError('Unable to connect to server. Please try again later.');
        
        // Hata analitiği
        analyticsService.trackEvent({
          category: EventCategory.ERROR,
          action: 'ConnectionError',
          label: 'MaintenanceCheck'
        });
      } finally {
        setIsLoading(false);
      }
    };
    
    checkMaintenanceMode();
    
    // 5 dakikada bir kontrol et
    const interval = setInterval(checkMaintenanceMode, 5 * 60 * 1000);
    
    return () => clearInterval(interval);
  }, []);
  
  // Onboarding kontrolü
  useEffect(() => {
    const hasCompletedOnboarding = localStorage.getItem('has_completed_onboarding') === 'true';
    const isNewUser = !localStorage.getItem('user_created_at');
    
    // Yeni kullanıcı ve onboarding tamamlanmadıysa göster
    if (!hasCompletedOnboarding && isNewUser) {
      setShowOnboarding(true);
      
      // Analitik izleme
      analyticsService.trackEvent({
        category: EventCategory.USER,
        action: 'OnboardingStarted',
        label: 'NewUser'
      });
    }
  }, []);
  
  // Sidebar aç/kapa
  const toggleSidebar = () => {
    setSidebarOpen(prevState => !prevState);
    
    // Analitik
    analyticsService.trackEvent({
      category: EventCategory.INTERACTION,
      action: sidebarOpen ? 'CloseSidebar' : 'OpenSidebar'
    });
  };
  
  // Onboarding tamamlandı
  const handleOnboardingComplete = () => {
    localStorage.setItem('has_completed_onboarding', 'true');
    setShowOnboarding(false);
    
    // Analitik
    analyticsService.trackEvent({
      category: EventCategory.USER,
      action: 'OnboardingCompleted',
      label: 'Success'
    });
  };
  
  // Onboarding atla
  const handleOnboardingSkip = () => {
    setShowOnboarding(false);
    
    // Analitik
    analyticsService.trackEvent({
      category: EventCategory.USER,
      action: 'OnboardingSkipped'
    });
  };
  
  // Geçiş animasyonu değiştirme
  const handleTransitionChange = (type: TransitionType) => {
    setTransitionType(type);
    
    // Kullanıcı tercihlerini kaydet
    try {
      localStorage.setItem('preferred_transition', type);
    } catch (error) {
      console.warn('Could not save transition preference:', error);
    }
  };
  
  // Tercih edilen geçişi yükle
  useEffect(() => {
    try {
      const savedTransition = localStorage.getItem('preferred_transition');
      if (savedTransition && Object.values(TransitionType).includes(savedTransition as TransitionType)) {
        setTransitionType(savedTransition as TransitionType);
      }
    } catch (error) {
      console.warn('Could not load transition preference:', error);
    }
  }, []);
  
  // App state optimizasyonu - Gereksiz renderları önlemek için memoize et
  const appState = useDeepMemo(() => ({
    sidebarOpen,
    isMaintenanceMode,
    error,
    showOnboarding,
    transitionType,
  }), [sidebarOpen, isMaintenanceMode, error, showOnboarding, transitionType]);
  
  // Hata varsa hata ekranı göster
  if (error) {
    return (
      <div className="d-flex justify-content-center align-items-center flex-column" style={{ height: '100vh', padding: '20px' }}>
        <div className="alert alert-danger text-center">
          <h4 className="alert-heading">Connection Error</h4>
          <p>{error}</p>
          <hr />
          <button 
            className="btn btn-outline-danger" 
            onClick={() => window.location.reload()}
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }
  
  // Yükleniyor ekranı
  if (isLoading) {
    return (
      <div className="d-flex justify-content-center align-items-center" style={{ height: '100vh' }}>
        <ContentLoader 
          isLoading={true}
          type={LoaderType.SPINNER}
          message="Connecting to server..."
        />
      </div>
    );
  }
  
  // Bakım modundaysa bakım ekranı göster (admin harici tüm rotalar için)
  if (isMaintenanceMode) {
    return (
      <ThemeProvider>
        <ToastProvider>
          <AuthProvider>
            <Router>
              <GlobalErrorBoundary>
                <Routes>
                  {/* Sadece admin bakım modunu bypass edebilir */}
                  <Route path="/admin/*" element={
                    <RoleProtectedRoute roles={['admin']}>
                      <App />
                    </RoleProtectedRoute>
                  } />
                  
                  {/* Diğer tüm rotalar bakım ekranını gösterir */}
                  <Route path="*" element={
                    <Suspense fallback={<PageLoadingFallback />}>
                      <MaintenancePage />
                    </Suspense>
                  } />
                </Routes>
              </GlobalErrorBoundary>
            </Router>
          </AuthProvider>
        </ToastProvider>
      </ThemeProvider>
    );
  }
  
  return (
    <GlobalErrorBoundary>
      <ThemeProvider>
        <ToastProvider>
          <AuthProvider>
            <NotificationProvider>
              <GlobalStateProvider>
                <QueryProvider>
                  <Router>
                    {/* PWA Updates */}
                    <UpdateNotification />
                    <InstallPrompt />
                    
                    {/* Onboarding */}
                    <UserOnboarding 
                      onComplete={handleOnboardingComplete}
                      forcedStart={showOnboarding}
                      onSkip={handleOnboardingSkip}
                    />
                    
                    <div className="app-container">
                      <AppNavbar toggleSidebar={toggleSidebar} />
                      
                      {/* Çevrimdışı uyarısı */}
                      <OfflineAlert className="sticky-top" />
                      
                      {/* Performans uyarısı */}
                      <PerformanceWarningBanner />
                      
                      <div className="content-container">
                        <Sidebar isOpen={sidebarOpen} toggleSidebar={toggleSidebar} />
                        
                        <main className={`main-content ${sidebarOpen ? 'sidebar-open' : ''}`}>
                          <Container fluid className="py-3">
                            <Suspense fallback={<PageLoadingFallback />}>
                              <Routes>
                                {/* Public Routes */}
                                <Route path="/login" element={
                                  <PageErrorBoundary>
                                    <PageTransition type={transitionType}>
                                      <Login />
                                    </PageTransition>
                                  </PageErrorBoundary>
                                } />
                                <Route path="/register" element={
                                  <PageErrorBoundary>
                                    <PageTransition type={transitionType}>
                                      <Register />
                                    </PageTransition>
                                  </PageErrorBoundary>
                                } />
                                <Route path="/forgot-password" element={
                                  <PageErrorBoundary>
                                    <PageTransition type={transitionType}>
                                      <ForgotPassword />
                                    </PageTransition>
                                  </PageErrorBoundary>
                                } />
                                <Route path="/reset-password/:token" element={
                                  <PageErrorBoundary>
                                    <PageTransition type={transitionType}>
                                      <ResetPassword />
                                    </PageTransition>
                                  </PageErrorBoundary>
                                } />
                                <Route path="/2fa-verify" element={
                                  <PageErrorBoundary>
                                    <PageTransition type={transitionType}>
                                      <TwoFactorAuth />
                                    </PageTransition>
                                  </PageErrorBoundary>
                                } />
                                <Route path="/unauthorized" element={
                                  <PageErrorBoundary>
                                    <PageTransition type={transitionType}>
                                      <UnauthorizedPage />
                                    </PageTransition>
                                  </PageErrorBoundary>
                                } />
                                <Route path="/help" element={
                                  <PageErrorBoundary>
                                    <PageTransition type={transitionType}>
                                      <HelpCenter />
                                    </PageTransition>
                                  </PageErrorBoundary>
                                } />
                                <Route path="/docs" element={
                                  <PageErrorBoundary>
                                    <PageTransition type={transitionType}>
                                      <Documentation />
                                    </PageTransition>
                                  </PageErrorBoundary>
                                } />
                                
                                {/* Protected Routes */}
                                <Route path="/" element={
                                  <ProtectedRoute>
                                    <PageErrorBoundary>
                                      <PageTransition type={transitionType}>
                                        <Dashboard />
                                      </PageTransition>
                                    </PageErrorBoundary>
                                  </ProtectedRoute>
                                } />
                                <Route path="/dashboard" element={
                                  <ProtectedRoute>
                                    <PageErrorBoundary>
                                      <PageTransition type={transitionType}>
                                        <Dashboard />
                                      </PageTransition>
                                    </PageErrorBoundary>
                                  </ProtectedRoute>
                                } />
                                <Route path="/documents" element={
                                  <ProtectedRoute>
                                    <PageErrorBoundary>
                                      <PageTransition type={transitionType}>
                                        <Documents />
                                      </PageTransition>
                                    </PageErrorBoundary>
                                  </ProtectedRoute>
                                } />
                                <Route path="/documents/:id" element={
                                  <ProtectedRoute>
                                    <PageErrorBoundary>
                                      <PageTransition type={transitionType}>
                                        <DocumentDetail />
                                      </PageTransition>
                                    </PageErrorBoundary>
                                  </ProtectedRoute>
                                } />
                                <Route path="/query" element={
                                  <ProtectedRoute>
                                    <PageErrorBoundary>
                                      <PageTransition type={transitionType}>
                                        <Query />
                                      </PageTransition>
                                    </PageErrorBoundary>
                                  </ProtectedRoute>
                                } />
                                <Route path="/multimodal" element={
                                  <ProtectedRoute>
                                    <PageErrorBoundary>
                                      <PageTransition type={transitionType}>
                                        <MultimodalQuery />
                                      </PageTransition>
                                    </PageErrorBoundary>
                                  </ProtectedRoute>
                                } />
                                <Route path="/query-history" element={
                                  <ProtectedRoute>
                                    <PageErrorBoundary>
                                      <PageTransition type={transitionType}>
                                        <QueryHistory />
                                      </PageTransition>
                                    </PageErrorBoundary>
                                  </ProtectedRoute>
                                } />
                                <Route path="/profile" element={
                                  <ProtectedRoute>
                                    <PageErrorBoundary>
                                      <PageTransition type={transitionType}>
                                        <Profile />
                                      </PageTransition>
                                    </PageErrorBoundary>
                                  </ProtectedRoute>
                                } />
                                <Route path="/settings" element={
                                  <ProtectedRoute>
                                    <PageErrorBoundary>
                                      <PageTransition type={transitionType}>
                                        <Settings transitionChange={handleTransitionChange} />
                                      </PageTransition>
                                    </PageErrorBoundary>
                                  </ProtectedRoute>
                                } />
                                <Route path="/2fa-setup" element={
                                  <ProtectedRoute>
                                    <PageErrorBoundary>
                                      <PageTransition type={transitionType}>
                                        <TwoFactorSetup />
                                      </PageTransition>
                                    </PageErrorBoundary>
                                  </ProtectedRoute>
                                } />
                                
                                {/* Role-Based Protected Routes */}
                                <Route path="/admin" element={
                                  <RoleProtectedRoute roles={['admin', 'org_admin']}>
                                    <PageErrorBoundary>
                                      <PageTransition type={transitionType}>
                                        <AdminDashboard />
                                      </PageTransition>
                                    </PageErrorBoundary>
                                  </RoleProtectedRoute>
                                } />
                                <Route path="/admin/users" element={
                                  <PermissionProtectedRoute permission="view:users">
                                    <PageErrorBoundary>
                                      <PageTransition type={transitionType}>
                                        <UserManagement />
                                      </PageTransition>
                                    </PageErrorBoundary>
                                  </PermissionProtectedRoute>
                                } />
                                <Route path="/admin/organizations" element={
                                  <PermissionProtectedRoute permission="view:organization">
                                    <PageErrorBoundary>
                                      <PageTransition type={transitionType}>
                                        <OrganizationManagement />
                                      </PageTransition>
                                    </PageErrorBoundary>
                                  </PermissionProtectedRoute>
                                } />
                                <Route path="/admin/system" element={
                                  <RoleProtectedRoute roles={['admin']}>
                                    <PageErrorBoundary>
                                      <PageTransition type={transitionType}>
                                        <SystemSettings />
                                      </PageTransition>
                                    </PageErrorBoundary>
                                  </RoleProtectedRoute>
                                } />
                                <Route path="/admin/system-monitoring" element={
                                  <RoleProtectedRoute roles={['admin', 'org_admin']}>
                                    <PageErrorBoundary>
                                      <PageTransition type={transitionType}>
                                        <SystemMonitoring />
                                      </PageTransition>
                                    </PageErrorBoundary>
                                  </RoleProtectedRoute>
                                } />
                                
                                {/* 404 Page */}
                                <Route path="*" element={
                                  <PageTransition type={transitionType}>
                                    <NotFound />
                                  </PageTransition>
                                } />
                              </Routes>
                            </Suspense>
                          </Container>
                        </main>
                      </div>
                      
                      <Footer />
                      
                      {/* Accessibility Tools */}
                      <AccessibilityTools />
                      
                      {/* Onboarding Tour */}
                      <OnboardingTour />
                    </div>
                  </Router>
                </QueryProvider>
              </GlobalStateProvider>
            </NotificationProvider>
          </AuthProvider>
        </ToastProvider>
      </ThemeProvider>
    </GlobalErrorBoundary>
  );
};

// Analytics ile izleme için HOC (Higher Order Component)
const AppWithAnalytics: React.FC = () => {
  const { trackEvent } = useAnalytics();
  
  // Uygulama başlatıldığında analitik izleme
  useEffect(() => {
    // Sayfa yükleme zamanını izle
    const loadTime = performance.now();
    
    trackEvent({
      category: EventCategory.PERFORMANCE,
      action: EventAction.PAGE_LOAD,
      label: 'AppInitialization',
      value: Math.round(loadTime)
    });
    
    // Tarayıcı ve cihaz bilgilerini izle
    trackEvent({
      category: EventCategory.USER,
      action: 'SessionStart',
      dimensions: {
        browser: navigator.userAgent,
        screenSize: `${window.innerWidth}x${window.innerHeight}`,
        language: navigator.language
      }
    });
    
    // Uygulama kapatıldığında izleme
    const handleBeforeUnload = () => {
      trackEvent({
        category: EventCategory.USER,
        action: 'SessionEnd',
        nonInteraction: true
      });
    };
    
    window.addEventListener('beforeunload', handleBeforeUnload);
    
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [trackEvent]);
  
  return <App />;
};

export default AppWithAnalytics;