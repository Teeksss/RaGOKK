// Last reviewed: 2025-04-29 07:31:24 UTC (User: TeeksssLogin)
import React from 'react';
import PropTypes from 'prop-types';
import './Spinner.css';

const Spinner = ({ size, color, text }) => {
  const sizeClass = size === 'small' ? 'spinner-small' : size === 'large' ? 'spinner-large' : '';
  const colorClass = color === 'light' ? 'spinner-light' : '';
  
  return (
    <div className="spinner-container">
      <div className={`spinner ${sizeClass} ${colorClass}`}></div>
      {text && <span className="spinner-text">{text}</span>}
    </div>
  );
};

Spinner.propTypes = {
  size: PropTypes.oneOf(['small', 'medium', 'large']),
  color: PropTypes.oneOf(['default', 'light']),
  text: PropTypes.string
};

Spinner.defaultProps = {
  size: 'medium',
  color: 'default',
  text: null
};

export default Spinner;