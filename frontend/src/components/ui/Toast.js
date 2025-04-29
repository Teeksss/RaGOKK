// Last reviewed: 2025-04-29 07:31:24 UTC (User: TeeksssLogin)
import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import './Toast.css';

const Toast = ({ id, message, type, duration, onClose }) => {
  const [isVisible, setIsVisible] = useState(true);
  const [progress, setProgress] = useState(0);
  
  // Progress animation
  useEffect(() => {
    if (!duration) return;
    
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev < 100) {
          return prev + (100 / (duration / 100));
        }
        return 100;
      });
    }, 100);
    
    return () => clearInterval(interval);
  }, [duration]);
  
  // Auto close timer
  useEffect(() => {
    if (!duration) return;
    
    const timer = setTimeout(() => {
      handleClose();
    }, duration);
    
    return () => clearTimeout(timer);
  }, [duration]);
  
  const handleClose = () => {
    setIsVisible(false);
    setTimeout(() => onClose(id), 300); // Allow animation to complete
  };
  
  return (
    <div className={`toast toast-${type} ${isVisible ? 'toast-visible' : 'toast-hidden'}`}>
      <div className="toast-content">
        {type === 'success' && <i className="toast-icon success">✓</i>}
        {type === 'error' && <i className="toast-icon error">✗</i>}
        {type === 'info' && <i className="toast-icon info">i</i>}
        {type === 'warning' && <i className="toast-icon warning">!</i>}
        <span className="toast-message">{message}</span>
        <button className="toast-close" onClick={handleClose}>×</button>
      </div>
      {duration > 0 && (
        <div className="toast-progress">
          <div className="toast-progress-bar" style={{ width: `${progress}%` }}></div>
        </div>
      )}
    </div>
  );
};

Toast.propTypes = {
  id: PropTypes.string.isRequired,
  message: PropTypes.string.isRequired,
  type: PropTypes.oneOf(['success', 'error', 'info', 'warning']),
  duration: PropTypes.number, // milliseconds, 0 for no auto-close
  onClose: PropTypes.func.isRequired
};

Toast.defaultProps = {
  type: 'info',
  duration: 5000 // 5 seconds
};

export default Toast;