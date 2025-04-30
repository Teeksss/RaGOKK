# RAG Base Component Documentation

This directory contains documentation for all major components used in the RAG Base frontend application. Each component documentation includes usage examples, props reference, and best practices.

## Core Components

### Layout Components
- [AppNavbar](./layout/AppNavbar.md) - Main navigation bar component
- [Sidebar](./layout/Sidebar.md) - Application sidebar navigation
- [Footer](./layout/Footer.md) - Application footer component
- [PageLayout](./layout/PageLayout.md) - Standard page layout wrapper

### Authentication Components
- [LoginForm](./auth/LoginForm.md) - User login form
- [RegisterForm](./auth/RegisterForm.md) - User registration form
- [ForgotPasswordForm](./auth/ForgotPasswordForm.md) - Password reset request form
- [ResetPasswordForm](./auth/ResetPasswordForm.md) - Password reset form
- [TwoFactorForm](./auth/TwoFactorForm.md) - Two-factor authentication form

### Common UI Components
- [Button](./common/Button.md) - Enhanced button component
- [Card](./common/Card.md) - Card container component
- [Modal](./common/Modal.md) - Modal dialog component
- [Tabs](./common/Tabs.md) - Tab navigation component
- [Dropdown](./common/Dropdown.md) - Dropdown menu component
- [Pagination](./common/Pagination.md) - Pagination control

### Form Components
- [TextField](./form/TextField.md) - Text input field
- [Select](./form/Select.md) - Select dropdown
- [Checkbox](./form/Checkbox.md) - Checkbox input
- [RadioGroup](./form/RadioGroup.md) - Radio button group
- [FileUpload](./form/FileUpload.md) - File upload component
- [DatePicker](./form/DatePicker.md) - Date selection component
- [Form](./form/Form.md) - Form container with validation

### Data Display
- [Table](./data/Table.md) - Data table component
- [VirtualList](./data/VirtualList.md) - Virtualized list for large datasets
- [Chart](./data/Chart.md) - Data visualization chart
- [Timeline](./data/Timeline.md) - Timeline visualization
- [Badge](./data/Badge.md) - Badge indicator component
- [Avatar](./data/Avatar.md) - User avatar component

### Feedback Components
- [Alert](./feedback/Alert.md) - Alert message component
- [Toast](./feedback/Toast.md) - Toast notification
- [ProgressBar](./feedback/ProgressBar.md) - Progress indicator
- [Spinner](./feedback/Spinner.md) - Loading spinner
- [Skeleton](./feedback/Skeleton.md) - Content loading skeleton
- [ErrorBoundary](./feedback/ErrorBoundary.md) - Error handling component

### Search Components
- [SearchBar](./search/SearchBar.md) - Basic search input
- [EnhancedSearchBar](./search/EnhancedSearchBar.md) - Advanced search with filters
- [SearchResults](./search/SearchResults.md) - Search results display
- [SearchFilters](./search/SearchFilters.md) - Search filtering options

### Query Components
- [QueryInput](./query/QueryInput.md) - Query input component
- [QueryResults](./query/QueryResults.md) - Query results display
- [QueryHistory](./query/QueryHistory.md) - Query history display
- [MultimodalInput](./query/MultimodalInput.md) - Text and image query input

### Document Components
- [DocumentCard](./document/DocumentCard.md) - Document summary card
- [DocumentViewer](./document/DocumentViewer.md) - Document content viewer
- [DocumentUpload](./document/DocumentUpload.md) - Document upload form
- [DocumentList](./document/DocumentList.md) - List of documents

### Accessibility Components
- [AccessibilityTools](./accessibility/AccessibilityTools.md) - Accessibility tools panel
- [ScreenReaderText](./accessibility/ScreenReaderText.md) - Screen reader only text
- [FocusTrap](./accessibility/FocusTrap.md) - Focus management component
- [SkipLink](./accessibility/SkipLink.md) - Skip to content link

### Animation Components
- [PageTransition](./animation/PageTransition.md) - Page transition wrapper
- [FadeIn](./animation/FadeIn.md) - Fade in animation
- [SlideIn](./animation/SlideIn.md) - Slide in animation
- [Collapse](./animation/Collapse.md) - Collapsible content

### PWA Components
- [UpdateNotification](./pwa/UpdateNotification.md) - PWA update notification
- [InstallPrompt](./pwa/InstallPrompt.md) - PWA installation prompt
- [OfflineIndicator](./pwa/OfflineIndicator.md) - Offline status indicator

## High-Level Feature Components

### Onboarding
- [UserOnboarding](./onboarding/UserOnboarding.md) - New user onboarding process
- [OnboardingTour](./onboarding/OnboardingTour.md) - Feature tour guide
- [OnboardingStep](./onboarding/OnboardingStep.md) - Single onboarding step

### Data Visualization
- [DocumentStatistics](./visualization/DocumentStatistics.md) - Document metrics charts
- [QueryStatistics](./visualization/QueryStatistics.md) - Query usage statistics
- [UsageMetrics](./visualization/UsageMetrics.md) - User activity metrics

### Administration
- [UserManagement](./admin/UserManagement.md) - User management interface
- [OrganizationManagement](./admin/OrganizationManagement.md) - Organization management
- [SystemSettings](./admin/SystemSettings.md) - System configuration interface

## Component Design Guidelines

### Component Structure

All components should follow this basic structure:

```tsx
import React from 'react';
import './ComponentName.scss'; // If using component-specific styles

interface ComponentNameProps {
  // Props definition
}

const ComponentName: React.FC<ComponentNameProps> = ({ prop1, prop2 }) => {
  // Component implementation
  
  return (
    <div className="component-name">
      {/* Component markup */}
    </div>
  );
};

export default ComponentName;