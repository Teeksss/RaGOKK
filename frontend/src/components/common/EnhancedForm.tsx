// Last reviewed: 2025-04-30 08:46:51 UTC (User: Teeksss)
import React, { useState, useEffect, useCallback } from 'react';
import { Form, Button, Spinner, Alert } from 'react-bootstrap';
import { useTranslation } from 'react-i18next';

interface FormErrors {
  [key: string]: string;
}

interface EnhancedFormProps {
  onSubmit: (data: any) => Promise<void>;
  initialValues?: any;
  validationSchema?: any; // Yup schema
  validateOnChange?: boolean;
  validateOnBlur?: boolean;
  submitButtonText?: string;
  cancelButtonText?: string;
  onCancel?: () => void;
  successMessage?: string;
  errorMessage?: string;
  resetAfterSubmit?: boolean;
  className?: string;
  children: React.ReactNode | ((props: EnhancedFormChildProps) => React.ReactNode);
}

interface EnhancedFormChildProps {
  values: any;
  errors: FormErrors;
  touched: any;
  isSubmitting: boolean;
  handleChange: (e: React.ChangeEvent<any>) => void;
  handleBlur: (e: React.FocusEvent<any>) => void;
  setFieldValue: (field: string, value: any, shouldValidate?: boolean) => void;
  setFieldTouched: (field: string, isTouched?: boolean, shouldValidate?: boolean) => void;
}

const EnhancedForm: React.FC<EnhancedFormProps> = ({
  onSubmit,
  initialValues = {},
  validationSchema,
  validateOnChange = true,
  validateOnBlur = true,
  submitButtonText = 'Submit',
  cancelButtonText = 'Cancel',
  onCancel,
  successMessage,
  errorMessage,
  resetAfterSubmit = false,
  className = '',
  children
}) => {
  const { t } = useTranslation();
  
  // Form state
  const [values, setValues] = useState<any>(initialValues);
  const [errors, setErrors] = useState<FormErrors>({});
  const [touched, setTouched] = useState<any>({});
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submitSuccess, setSubmitSuccess] = useState<boolean>(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  
  // Reset form when initialValues change
  useEffect(() => {
    setValues(initialValues);
    setErrors({});
    setTouched({});
  }, [initialValues]);
  
  // Validate form values with the schema
  const validateForm = useCallback(async (formValues: any = values) => {
    if (!validationSchema) return {};
    
    try {
      await validationSchema.validate(formValues, { abortEarly: false });
      return {};
    } catch (err: any) {
      if (err.inner) {
        return err.inner.reduce((acc: any, error: any) => {
          acc[error.path] = error.message;
          return acc;
        }, {});
      }
      return {};
    }
  }, [validationSchema, values]);
  
  // Handle field change
  const handleChange = async (e: React.ChangeEvent<any>) => {
    const { name, value, type, checked } = e.target;
    const newValue = type === 'checkbox' ? checked : value;
    
    // Update values state
    setValues((prevValues: any) => ({
      ...prevValues,
      [name]: newValue
    }));
    
    // Validate field if needed
    if (validateOnChange) {
      const newValues = { ...values, [name]: newValue };
      const validationErrors = await validateForm(newValues);
      setErrors(validationErrors);
    }
  };
  
  // Handle field blur
  const handleBlur = async (e: React.FocusEvent<any>) => {
    const { name } = e.target;
    
    // Mark field as touched
    setTouched((prevTouched: any) => ({
      ...prevTouched,
      [name]: true
    }));
    
    // Validate field if needed
    if (validateOnBlur) {
      const validationErrors = await validateForm();
      setErrors(validationErrors);
    }
  };
  
  // Set field value programmatically
  const setFieldValue = async (field: string, value: any, shouldValidate: boolean = true) => {
    // Update values state
    setValues((prevValues: any) => ({
      ...prevValues,
      [field]: value
    }));
    
    // Validate if needed
    if (shouldValidate && validateOnChange) {
      const newValues = { ...values, [field]: value };
      const validationErrors = await validateForm(newValues);
      setErrors(validationErrors);
    }
  };
  
  // Set field as touched programmatically
  const setFieldTouched = async (field: string, isTouched: boolean = true, shouldValidate: boolean = true) => {
    // Update touched state
    setTouched((prevTouched: any) => ({
      ...prevTouched,
      [field]: isTouched
    }));
    
    // Validate if needed
    if (shouldValidate && validateOnBlur) {
      const validationErrors = await validateForm();
      setErrors(validationErrors);
    }
  };
  
  // Check if form is valid
  const isFormValid = () => {
    return Object.keys(errors).length === 0;
  };
  
  // Handle form submission
  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    
    // Touch all fields for validation
    const allTouched = Object.keys(values).reduce((acc, field) => {
      acc[field] = true;
      return acc;
    }, {} as any);
    
    setTouched(allTouched);
    
    // Validate the form
    const formErrors = await validateForm();
    setErrors(formErrors);
    
    // If there are errors, don't submit
    if (Object.keys(formErrors).length > 0) {
      // Focus on first field with error
      const firstErrorField = document.getElementsByName(Object.keys(formErrors)[0])[0];
      if (firstErrorField) {
        firstErrorField.focus();
      }
      return;
    }
    
    // Submit the form
    setIsSubmitting(true);
    setSubmitSuccess(false);
    setSubmitError(null);
    
    try {
      await onSubmit(values);
      setSubmitSuccess(true);
      
      // Reset form if needed
      if (resetAfterSubmit) {
        setValues(initialValues);
        setTouched({});
      }
    } catch (error: any) {
      console.error('Form submission error:', error);
      setSubmitError(error.message || errorMessage || t('common.error.submission'));
    } finally {
      setIsSubmitting(false);
    }
  };
  
  // Form context for children
  const formProps: EnhancedFormChildProps = {
    values,
    errors,
    touched,
    isSubmitting,
    handleChange,
    handleBlur,
    setFieldValue,
    setFieldTouched
  };
  
  return (
    <Form className={className} onSubmit={handleSubmit} noValidate>
      {/* Success message */}
      {submitSuccess && successMessage && (
        <Alert variant="success" className="mb-4" dismissible onClose={() => setSubmitSuccess(false)}>
          {successMessage}
        </Alert>
      )}
      
      {/* Error message */}
      {submitError && (
        <Alert variant="danger" className="mb-4" dismissible onClose={() => setSubmitError(null)}>
          {submitError}
        </Alert>
      )}
      
      {/* Form children */}
      {typeof children === 'function' ? children(formProps) : children}
      
      {/* Form buttons */}
      <div className="d-flex justify-content-end mt-4">
        {onCancel && (
          <Button
            type="button"
            variant="outline-secondary"
            onClick={onCancel}
            disabled={isSubmitting}
            className="me-2"
          >
            {cancelButtonText}
          </Button>
        )}
        
        <Button
          type="submit"
          variant="primary"
          disabled={isSubmitting}
        >
          {isSubmitting ? (
            <>
              <Spinner animation="border" size="sm" className="me-2" />
              {t('common.submitting')}
            </>
          ) : (
            submitButtonText
          )}
        </Button>
      </div>
    </Form>
  );
};

export default EnhancedForm;