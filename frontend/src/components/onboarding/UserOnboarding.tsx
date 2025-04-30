// Last reviewed: 2025-04-30 09:17:40 UTC (User: Teeksss)
import React, { useState, useEffect, useRef } from 'react';
import { Modal, Button, ProgressBar, Card, Row, Col } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';
import { 
  FaCheckCircle, FaArrowRight, FaArrowLeft, 
  FaTimes, FaInfoCircle, FaUserCircle, FaFileUpload,
  FaSearch, FaRobot, FaImage
} from 'react-icons/fa';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import Confetti from 'react-confetti';

// Adım türü
interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  image?: string;
  video?: string;
  actionText?: string;
  actionPath?: string;
  demoComponent?: React.ReactNode;
  completionCriteria?: () => boolean;
}

// Props tipi
interface UserOnboardingProps {
  onComplete?: () => void;
  onSkip?: () => void;
  forcedStart?: boolean;
}

const UserOnboarding: React.FC<UserOnboardingProps> = ({
  onComplete,
  onSkip,
  forcedStart = false
}) => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const navigate = useNavigate();
  const confettiRef = useRef<HTMLDivElement>(null);
  
  // Durum değişkenleri
  const [showModal, setShowModal] = useState<boolean>(forcedStart);
  const [currentStepIndex, setCurrentStepIndex] = useState<number>(0);
  const [completedSteps, setCompletedSteps] = useState<string[]>([]);
  const [showConfetti, setShowConfetti] = useState<boolean>(false);
  const [isFirstTimeUser, setIsFirstTimeUser] = useState<boolean>(true);
  
  // Onboarding adımları
  const steps: OnboardingStep[] = [
    {
      id: 'welcome',
      title: t('onboarding.welcome.title'),
      description: t('onboarding.welcome.description', { name: user?.name || 'there' }),
      image: '/assets/images/onboarding/welcome.svg',
      actionText: t('onboarding.welcome.action')
    },
    {
      id: 'documents',
      title: t('onboarding.documents.title'),
      description: t('onboarding.documents.description'),
      image: '/assets/images/onboarding/documents.svg',
      actionText: t('onboarding.documents.action'),
      actionPath: '/documents',
      completionCriteria: () => {
        // Gerçek uygulamada belge yükleme kontrolü yapılabilir
        return localStorage.getItem('has_uploaded_document') === 'true';
      }
    },
    {
      id: 'textQuery',
      title: t('onboarding.textQuery.title'),
      description: t('onboarding.textQuery.description'),
      image: '/assets/images/onboarding/query.svg',
      actionText: t('onboarding.textQuery.action'),
      actionPath: '/query',
      completionCriteria: () => {
        return localStorage.getItem('has_made_query') === 'true';
      }
    },
    {
      id: 'multimodal',
      title: t('onboarding.multimodal.title'),
      description: t('onboarding.multimodal.description'),
      image: '/assets/images/onboarding/multimodal.svg',
      actionText: t('onboarding.multimodal.action'),
      actionPath: '/multimodal',
      completionCriteria: () => {
        return localStorage.getItem('has_used_multimodal') === 'true';
      }
    },
    {
      id: 'complete',
      title: t('onboarding.complete.title'),
      description: t('onboarding.complete.description'),
      image: '/assets/images/onboarding/complete.svg',
      actionText: t('onboarding.complete.action')
    }
  ];
  
  // İlk yüklemede onboarding durumunu kontrol et
  useEffect(() => {
    const hasCompletedOnboarding = localStorage.getItem('has_completed_onboarding') === 'true';
    const isNewUser = !localStorage.getItem('user_created_at');
    
    setIsFirstTimeUser(isNewUser);
    
    // Zorla başlatılmadıysa ve onboarding tamamlanmışsa veya yeni kullanıcı değilse gösterme
    if (!forcedStart && (hasCompletedOnboarding || !isNewUser)) {
      return;
    }
    
    // Tamamlanan adımları yükle
    const savedCompletedSteps = localStorage.getItem('completed_onboarding_steps');
    if (savedCompletedSteps) {
      setCompletedSteps(JSON.parse(savedCompletedSteps));
    }
    
    // En son kaldığı adımdan devam et
    const lastStep = localStorage.getItem('current_onboarding_step');
    if (lastStep) {
      const stepIndex = steps.findIndex(step => step.id === lastStep);
      if (stepIndex !== -1) {
        setCurrentStepIndex(stepIndex);
      }
    }
    
    // Modal'ı göster
    setShowModal(true);
  }, [forcedStart]);
  
  // Modal kapandığında
  const handleClose = () => {
    setShowModal(false);
    
    // Onboarding'i tamamlandı olarak işaretle
    if (currentStepIndex === steps.length - 1) {
      localStorage.setItem('has_completed_onboarding', 'true');
      if (onComplete) onComplete();
    } else {
      // Kapatılmışsa, onSkip callback'ini çağır
      if (onSkip) onSkip();
    }
  };
  
  // Adım tamamlandı
  const markStepAsCompleted = (stepId: string) => {
    setCompletedSteps(prev => {
      if (prev.includes(stepId)) {
        return prev;
      }
      
      const updated = [...prev, stepId];
      localStorage.setItem('completed_onboarding_steps', JSON.stringify(updated));
      return updated;
    });
  };
  
  // Sonraki adıma geç
  const handleNext = () => {
    // Mevcut adımı tamamla
    markStepAsCompleted(steps[currentStepIndex].id);
    
    // Son adımdaysak tamamla
    if (currentStepIndex === steps.length - 1) {
      setShowConfetti(true);
      localStorage.setItem('has_completed_onboarding', 'true');
      
      // Konfeti sonrası kapat
      setTimeout(() => {
        setShowModal(false);
        if (onComplete) onComplete();
      }, 3000);
      
      return;
    }
    
    // Sonraki adım
    setCurrentStepIndex(currentStepIndex + 1);
    localStorage.setItem('current_onboarding_step', steps[currentStepIndex + 1].id);
  };
  
  // Önceki adıma dön
  const handlePrevious = () => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex(currentStepIndex - 1);
      localStorage.setItem('current_onboarding_step', steps[currentStepIndex - 1].id);
    }
  };
  
  // Belirtilen sayfaya git ve adımı tamamla
  const handleGoToAction = () => {
    const currentStep = steps[currentStepIndex];
    
    // Adımın tamamlandığını işaretle
    markStepAsCompleted(currentStep.id);
    
    if (currentStep.actionPath) {
      // Modal'ı kapat
      setShowModal(false);
      
      // Sayfaya yönlendir
      navigate(currentStep.actionPath);
    } else {
      handleNext();
    }
  };
  
  // Geçerli adım
  const currentStep = steps[currentStepIndex];
  
  // İlerleme yüzdesi
  const progressPercentage = Math.round(((currentStepIndex + (completedSteps.includes(currentStep.id) ? 1 : 0)) / steps.length) * 100);
  
  return (
    <>
      <Modal 
        show={showModal} 
        onHide={handleClose}
        centered
        backdrop="static"
        size="lg"
        className="onboarding-modal"
      >
        <Modal.Header>
          <div className="w-100 d-flex justify-content-between align-items-center">
            <Modal.Title>
              <FaInfoCircle className="me-2" />
              {t('onboarding.title')}
            </Modal.Title>
            
            <div className="step-counter">
              {t('onboarding.step', { current: currentStepIndex + 1, total: steps.length })}
            </div>
          </div>
        </Modal.Header>
        
        <Modal.Body>
          <div className="progress-container mb-4">
            <ProgressBar now={progressPercentage} variant="primary" />
          </div>
          
          <Row>
            <Col md={6} className="onboarding-content">
              <h2 className="onboarding-step-title">{currentStep.title}</h2>
              
              <div className="onboarding-description">
                {currentStep.description}
              </div>
              
              {completedSteps.includes(currentStep.id) && (
                <div className="step-completed mt-3">
                  <FaCheckCircle className="text-success me-2" />
                  {t('onboarding.stepCompleted')}
                </div>
              )}
              
              {currentStep.demoComponent && (
                <div className="onboarding-demo mt-3">
                  {currentStep.demoComponent}
                </div>
              )}
            </Col>
            
            <Col md={6} className="onboarding-media">
              {currentStep.video ? (
                <div className="video-container">
                  <video 
                    controls 
                    autoPlay 
                    muted
                    loop
                    className="onboarding-video"
                  >
                    <source src={currentStep.video} type="video/mp4" />
                    {t('common.videoNotSupported')}
                  </video>
                </div>
              ) : currentStep.image ? (
                <img 
                  src={currentStep.image} 
                  alt={currentStep.title}
                  className="onboarding-image img-fluid"
                />
              ) : null}
            </Col>
          </Row>
          
          {/* Özel içerik gösterimler - Adıma özel */}
          {currentStep.id === 'welcome' && (
            <Card className="mt-4 onboarding-features">
              <Card.Body>
                <h5>{t('onboarding.welcome.featuresTitle')}</h5>
                <Row>
                  <Col md={6}>
                    <div className="feature-item d-flex align-items-center mb-3">
                      <div className="feature-icon me-3">
                        <FaFileUpload />
                      </div>
                      <div className="feature-text">
                        {t('onboarding.welcome.feature1')}
                      </div>
                    </div>
                    <div className="feature-item d-flex align-items-center mb-3">
                      <div className="feature-icon me-3">
                        <FaSearch />
                      </div>