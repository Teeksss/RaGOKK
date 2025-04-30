// Form validation utility with security considerations
import { safeRegexMatch } from './security';

// Email validation with proper regex
export const isValidEmail = (email: string): boolean => {
  // RFC 5322 compliant regex for email validation
  const emailRegex = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*$/;
  return safeRegexMatch(email, emailRegex.source);
};

// Password strength validation
export const validatePasswordStrength = (password: string): {
  isValid: boolean;
  errors: string[];
} => {
  const errors: string[] = [];
  
  if (password.length < 8) {
    errors.push('Password must be at least 8 characters long');
  }
  
  if (!safeRegexMatch(password, /[a-z]/)) {
    errors.push('Password must contain at least one lowercase letter');
  }
  
  if (!safeRegexMatch(password, /[A-Z]/)) {
    errors.push('Password must contain at least one uppercase letter');
  }
  
  if (!safeRegexMatch(password, /[0-9]/)) {
    errors.push('Password must contain at least one number');
  }
  
  if (!safeRegexMatch(password, /[^a-zA-Z0-9]/)) {
    errors.push('Password must contain at least one special character');
  }
  
  return {
    isValid: errors.length === 0,
    errors
  };
};

// URL validation
export const isValidUrl = (url: string): boolean => {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
};

// Safe text validation (prevent code injection)
export const isSafeText = (text: string): boolean => {
  // Check for potential JavaScript or HTML injection
  const unsafePatterns = [
    /<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/i,
    /<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/i,
    /javascript:/i,
    /data:/i,
    /vbscript:/i,
    /on\w+=/i  // onerror, onload etc.
  ];
  
  return !unsafePatterns.some(pattern => pattern.test(text));
};

// Input sanitization for form fields
export const sanitizeFormInput = (input: string): string => {
  return input
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
};

// Form error message generator
export const getFormErrorMessage = (fieldName: string, error: string): string => {
  return `${fieldName}: ${sanitizeFormInput(error)}`;
};