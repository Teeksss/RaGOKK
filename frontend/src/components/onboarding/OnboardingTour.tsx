// Last reviewed: 2025-04-30 08:46:51 UTC (User: Teeksss)
import React, { useState, useEffect } from 'react';
import Tour from 'reactour';
import { Button, Badge } from 'react-bootstrap';
import { FaLightbulb, FaArrowRight, FaTimes } from 'react-icons/fa';
import { useTranslation } from 'react-i18next';
import { useLocation } from 'react-router-dom';

// Define tour step interface
interface TourStep {
  selector: string;
  content: React.ReactNode;
  action?: () => void;
  position?: string;
  stepInteraction?: boolean;
}

// Define tour configuration by route
interface TourConfig {
  [path: string]: {
    steps: TourStep[];
    name: string;
  };
}

// Define props
interface OnboardingTourProps {
  onComplete?: () => void;
  onSkip?: () => void;
}

const OnboardingTour: React.FC<OnboardingTourProps> = ({
  onComplete,
  onSkip
}) => {
  const { t } = useTranslation();
  const location = useLocation();
  
  // Tour state
  const [isTourOpen, setIsTourOpen] = useState(false);
  const [currentTour, setCurrentTour] = useState<string | null>(null);
  const [completedTours, setCompletedTours] = useState<string[]>([]);
  
  // Load completed tours from localStorage
  useEffect(() => {
    const stored = localStorage.getItem('onboarding_completed_tours');
    if (stored) {
      try {
        setCompletedTours(JSON.parse(stored));
      } catch (e) {
        console.error('Error parsing completed tours:', e);
      }
    }
  }, []);
  
  // Check current path and set active tour
  useEffect(() => {
    const path = location.pathname;
    const matchingTour = Object.keys(tours).find(tourPath => {
      if (tourPath === path) return true;
      if (tourPath.endsWith('*') && path.startsWith(tourPath.slice(0, -1))) return true;
      return false;
    });
    
    if (matchingTour && !completedTours.includes(matchingTour)) {
      setCurrentTour(matchingTour);
      
      // Auto open for first time users after a delay
      const isFirstTimeUser = localStorage.getItem('user_has_logged_in_before') !== 'true';
      if (isFirstTimeUser) {
        setTimeout(() => {
          setIsTourOpen(true);
          localStorage.setItem('user_has_logged_in_before', 'true');
        }, 1500);
      }
    } else {
      setCurrentTour(null);
    }
  }, [location.pathname, completedTours]);
  
  // Mark tour as completed
  const markTourCompleted = () => {
    if (currentTour) {
      const updated = [...completedTours, currentTour];
      setCompletedTours(updated);
      localStorage.setItem('onboarding_completed_tours', JSON.stringify(updated));
      
      if (onComplete) {
        onComplete();
      }
    }
  };
  
  // Handle tour closed
  const handleTourClosed = () => {
    setIsTourOpen(false);
    markTourCompleted();
  };
  
  // Handle tour skipped
  const handleTourSkip = () => {
    setIsTourOpen(false);
    markTourCompleted();
    
    if (onSkip) {
      onSkip();
    }
  };
  
  // Define tour steps for each route
  const tours: TourConfig = {
    '/dashboard': {
      name: 'dashboard',
      steps: [
        {
          selector: '.dashboard-welcome',
          content: (
            <div className="tour-content">
              <h4>{t('onboarding.dashboard.welcome.title')}</h4>
              <p>{t('onboarding.dashboard.welcome.content')}</p>
            </div>
          )
        },
        {
          selector: '.dashboard-stats',
          content: (
            <div className="tour-content">
              <h4>{t('onboarding.dashboard.stats.title')}</h4>
              <p>{t('onboarding.dashboard.stats.content')}</p>
            </div>
          )
        },
        {
          selector: '.recent-documents',
          content: (
            <div className="tour-content">
              <h4>{t('onboarding.dashboard.documents.title')}</h4>
              <p>{t('onboarding.dashboard.documents.content')}</p>
            </div>
          )
        },
        {
          selector: '.quick-actions',
          content: (
            <div className="tour-content">
              <h4>{t('onboarding.dashboard.actions.title')}</h4>
              <p>{t('onboarding.dashboard.actions.content')}</p>
            </div>
          )
        }
      ]
    },
    
    '/documents': {
      name: 'documents',
      steps: [
        {
          selector: '.document-list',
          content: (
            <div className="tour-content">
              <h4>{t('onboarding.documents.list.title')}</h4>
              <p>{t('onboarding.documents.list.content')}</p>
            </div>
          )
        },
        {
          selector: '.upload-document-btn',
          content: (
            <div className="tour-content">
              <h4>{t('onboarding.documents.upload.title')}</h4>
              <p>{t('onboarding.documents.upload.content')}</p>
            </div>
          )
        },
        {
          selector: '.document-filters',
          content: (
            <div className="tour-content">
              <h4>{t('onboarding.documents.filters.title')}</h4>
              <p>{t('onboarding.documents.filters.content')}</p>
            </div>
          )
        }
      ]
    },
    
    '/query': {
      name: 'query',
      steps: [
        {
          selector: '.query-form',
          content: (
            <div className="tour-content">
              <h4>{t('onboarding.query.form.title')}</h4>
              <p>{t('onboarding.query.form.content')}</p>
            </div>
          )
        },
        {
          selector: '.document-filter',
          content: (
            <div className="tour-content">
              <h4>{t('onboarding.query.filter.title')}</h4>
              <p>{t('onboarding.query.filter.content')}</p>
            </div>
          )
        },
        {
          selector: '.advanced-options',
          content: (
            <div className="tour-content">
              <h4>{t('onboarding.query.advanced.title')}</h4>
              <p>{t('onboarding.query.advanced.content')}</p>
            </div>
          )
        }
      ]
    },
    
    '/multimodal': {
      name: 'multimodal',
      steps: [
        {
          selector: '.query-form',
          content: (
            <div className="tour-content">
              <h4>{t('onboarding.multimodal.form.title')}</h4>
              <p>{t('onboarding.multimodal.form.content')}</p>
            </div>
          )
        },
        {
          selector: '.image-upload',
          content: (
            <div className="tour-content">
              <h4>{t('onboarding.multimodal.upload.title')}</h4>
              <p>{t('onboarding.multimodal.upload.content')}</p>
            </div>
          )
        },
        {
          selector: '.image-previews',
          content: (
            <div className="tour-content">
              <h4>{t('onboarding.multimodal.preview.title')}</h4>
              <p>{t('onboarding.multimodal.preview.content')}</p>
            </div>
          )
        }
      ]
    }
  };
  
  // If no active tour, don't render anything
  if (!currentTour || !tours[currentTour]) {
    return null;
  }
  
  // Set up tour steps
  const activeTour = tours[currentTour];
  const steps = activeTour.steps;
  
  return (
    <div className="onboarding-tour">
      {/* Show button to start tour if not automatically opened */}
      {!isTourOpen && (
        <div className="tour-button-container">
          <Button 
            variant="primary" 
            className="tour-button pulse" 
            onClick={() => setIsTourOpen(true)}
            aria-label={t('onboarding.startTour')}
          >
            <FaLightbulb />
            <Badge bg="danger" pill className="tour-badge">
              New
            </Badge>
          </Button>
        </div>
      )}
      
      {/* Tour Component */}
      <Tour
        steps={steps}
        isOpen={isTourOpen}
        onRequestClose={handleTourClosed}
        closeWithMask={false}
        showNavigation={true}
        showButtons={true}
        showCloseButton={true}
        disableInteraction={false}
        rounded={8}
        accentColor="var(--accent-color, #0d6efd)"
        className="rag-base-tour"
        prevButton={<span>{t('onboarding.previous')}</span>}
        nextButton={
          <span>
            {t('onboarding.next')}
            <FaArrowRight className="ms-1" />
          </span>
        }
        lastStepNextButton={
          <span>{t('onboarding.finish')}</span>
        }
        customButtons={{
          skip: (
            <Button variant="link" onClick={handleTourSkip} className="tour-skip-button">
              <FaTimes className="me-1" />
              {t('onboarding.skip')}
            </Button>
          )
        }}
      />
    </div>
  );
};

export default OnboardingTour;