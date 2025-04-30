// Last reviewed: 2025-04-30 11:25:03 UTC (User: Teeksssdevam)
// ... mevcut imports ...
import { TransitionType } from '../components/transitions/PageTransition';

interface SettingsProps {
  transitionChange?: (type: TransitionType) => void;
}

const Settings: React.FC<SettingsProps> = ({ transitionChange }) => {
  // ... mevcut kodlar ...
  
  // Geçiş animasyonları ayarı
  const [selectedTransition, setSelectedTransition] = useState<TransitionType>(TransitionType.FADE);
  
  // Tercih edilen geçişi yükle
  useEffect(() => {
    try {
      const savedTransition = localStorage.getItem('preferred_transition');
      if (savedTransition && Object.values(TransitionType).includes(savedTransition as TransitionType)) {
        setSelectedTransition(savedTransition as TransitionType);
      }
    } catch (error) {
      console.warn('Could not load transition preference:', error);
    }
  }, []);
  
  // Geçiş değişikliği
  const handleTransitionChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newTransition = e.target.value as TransitionType;
    setSelectedTransition(newTransition);
    
    // Üst bileşeni bilgilendir
    if (transitionChange) {
      transitionChange(newTransition);
    }
    
    // Tercihi kaydet
    try {
      localStorage.setItem('preferred_transition', newTransition);
    } catch (error) {
      console.warn('Could not save transition preference:', error);
    }
    
    // Başarı bildirimi
    notify.success('Page transition animation updated');
    
    // Analitik izleme
    analyticsService.trackEvent({
      category: 'Settings',
      action: 'UpdateTransition',
      label: newTransition
    });
  };
  
  return (
    <div className="settings-page">
      <h1 className="page-title">{t('settings.title')}</h1>
      
      {/* ... mevcut Tabs ... */}
      
      <Tab.Content>
        <Tab.Pane eventKey="appearance">
          {/* ... mevcut görünüm ayarları ... */}
          
          {/* Geçiş animasyonları ayarı */}
          <Card className="mb-4">
            <Card.Header>
              <h4>{t('settings.appearance.transitions.title')}</h4>
            </Card.Header>
            <Card.Body>
              <Form.Group>
                <Form.Label>{t('settings.appearance.transitions.type')}</Form.Label>
                <Form.Select
                  value={selectedTransition}
                  onChange={handleTransitionChange}
                >
                  <option value={TransitionType.FADE}>{t('settings.appearance.transitions.fade')}</option>
                  <option value={TransitionType.SLIDE_LEFT}>{t('settings.appearance.transitions.slideLeft')}</option>
                  <option value={TransitionType.SLIDE_RIGHT}>{t('settings.appearance.transitions.slideRight')}</option>
                  <option value={TransitionType.SLIDE_UP}>{t('settings.appearance.transitions.slideUp')}</option>
                  <option value={TransitionType.SLIDE_DOWN}>{t('settings.appearance.transitions.slideDown')}</option>
                  <option value={TransitionType.SCALE}>{t('settings.appearance.transitions.scale')}</option>
                  <option value={TransitionType.NONE}>{t('settings.appearance.transitions.none')}</option>
                </Form.Select>
                <Form.Text>{t('settings.appearance.transitions.help')}</Form.Text>
              </Form.Group>
              
              <div className="transition-preview mt-3">
                <h6>{t('settings.appearance.transitions.preview')}</h6>
                <div className="p-3 border rounded bg-light">
                  <PageTransition type={selectedTransition}>
                    <div className="p-3 bg-white border rounded">
                      {t('settings.appearance.transitions.previewContent')}
                    </div>
                  </PageTransition>
                </div>
              </div>
            </Card.Body>
          </Card>
          
          {/* ... diğer ayarlar ... */}
        </Tab.Pane>
        
        {/* ... diğer tab panelleri ... */}
      </Tab.Content>
    </div>
  );
};

export default Settings;