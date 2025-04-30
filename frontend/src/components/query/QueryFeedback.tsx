// Last reviewed: 2025-04-30 06:34:07 UTC (User: Teeksss)
import React, { useState } from 'react';
import { Button, Form, ButtonGroup, Collapse, Spinner } from 'react-bootstrap';
import { FaStar, FaRegStar, FaThumbsUp, FaThumbsDown, FaComment, FaCheck } from 'react-icons/fa';
import { useTranslation } from 'react-i18next';
import API from '../../api/api';
import { useToast } from '../../contexts/ToastContext';

interface QueryFeedbackProps {
  queryId: string;
  onFeedbackSubmit?: (rating: number, feedback: string) => void;
  variant?: 'stars' | 'thumbs';
  allowComments?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

const QueryFeedback: React.FC<QueryFeedbackProps> = ({
  queryId,
  onFeedbackSubmit,
  variant = 'stars',
  allowComments = true,
  size = 'md'
}) => {
  const { t } = useTranslation();
  const { showToast } = useToast();
  
  // State
  const [rating, setRating] = useState<number>(0);
  const [hoverRating, setHoverRating] = useState<number>(0);
  const [feedback, setFeedback] = useState<string>('');
  const [showCommentForm, setShowCommentForm] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submitted, setSubmitted] = useState<boolean>(false);
  
  // Yıldız boyutu
  const starSize = size === 'sm' ? 16 : size === 'lg' ? 24 : 20;
  
  // Geri bildirim gönderme işleyicisi
  const handleSubmit = async () => {
    if (rating === 0) {
      showToast('warning', t('feedback.pleaseSelectRating'));
      return;
    }
    
    setIsSubmitting(true);
    
    try {
      // Geri bildirim verisini hazırla
      const feedbackData = {
        rating: rating,
        feedback_text: feedback,
        feedback_type: 'answer_quality',
        query_data: {}
      };
      
      // API'ye gönder
      await API.post(`/feedback/${queryId}`, feedbackData);
      
      // Başarılı mesajı
      showToast('success', t('feedback.thankYou'));
      
      // Callback'i çağır
      if (onFeedbackSubmit) {
        onFeedbackSubmit(rating, feedback);
      }
      
      // Form durumunu sıfırla
      setFeedback('');
      setShowCommentForm(false);
      setSubmitted(true);
      
    } catch (err) {
      console.error('Error submitting feedback:', err);
      showToast('error', t('feedback.submitError'));
    } finally {
      setIsSubmitting(false);
    }
  };
  
  // Yıldız derecelendirmesi bileşeni
  const StarRating = () => (
    <div className="star-rating d-flex align-items-center">
      {[1, 2, 3, 4, 5].map((star) => (
        <span 
          key={star}
          onClick={() => setRating(star)}
          onMouseEnter={() => setHoverRating(star)}
          onMouseLeave={() => setHoverRating(0)}
          style={{ cursor: 'pointer', marginRight: '2px' }}
        >
          {(hoverRating || rating) >= star ? 
            <FaStar size={starSize} color="#ffc107" /> : 
            <FaRegStar size={starSize} color="#6c757d" />
          }
        </span>
      ))}
      <span className="ms-2 text-muted small">
        {rating > 0 && t(`feedback.ratings.${rating}`)}
      </span>
    </div>
  );
  
  // Başparmak derecelendirmesi bileşeni
  const ThumbsRating = () => (
    <ButtonGroup>
      <Button 
        variant={rating === 5 ? "success" : "outline-success"}
        onClick={() => setRating(5)}
        size={size}
        disabled={submitted}
      >
        <FaThumbsUp className="me-1" /> {t('feedback.helpful')}
      </Button>
      <Button 
        variant={rating === 1 ? "danger" : "outline-danger"}
        onClick={() => setRating(1)}
        size={size}
        disabled={submitted}
      >
        <FaThumbsDown className="me-1" /> {t('feedback.notHelpful')}
      </Button>
    </ButtonGroup>
  );
  
  // Gönderildi bileşeni
  if (submitted) {
    return (
      <div className="d-flex align-items-center text-success">
        <FaCheck className="me-1" />
        <span>{t('feedback.submitted')}</span>
      </div>
    );
  }
  
  return (
    <div className="query-feedback">
      <div className="d-flex align-items-center justify-content-between mb-2">
        <div>
          {variant === 'stars' ? <StarRating /> : <ThumbsRating />}
        </div>
        
        {allowComments && rating > 0 && !showCommentForm && (
          <Button
            variant="link"
            size="sm"
            onClick={() => setShowCommentForm(true)}
            className="p-0 text-decoration-none"
          >
            <FaComment className="me-1" />
            {t('feedback.addComment')}
          </Button>
        )}
      </div>
      
      <Collapse in={showCommentForm}>
        <div>
          <Form.Group className="mb-2">
            <Form.Control
              as="textarea"
              rows={2}
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder={t('feedback.commentPlaceholder')}
              disabled={isSubmitting}
            />
          </Form.Group>
        </div>
      </Collapse>
      
      {(rating > 0 || showCommentForm) && (
        <div className="d-flex justify-content-end">
          <Button
            variant="primary"
            size={size}
            onClick={handleSubmit}
            disabled={isSubmitting || rating === 0}
          >
            {isSubmitting ? (
              <>
                <Spinner animation="border" size="sm" className="me-1" />
                {t('common.submitting')}
              </>
            ) : (
              t('common.submit')
            )}
          </Button>
        </div>
      )}
    </div>
  );
};

export default QueryFeedback;