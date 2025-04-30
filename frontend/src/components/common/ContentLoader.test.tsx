import React from 'react';
import { render, screen } from '@testing-library/react';
import ContentLoader, { LoaderType } from './ContentLoader';

describe('ContentLoader', () => {
  test('renders spinner when isLoading is true', () => {
    render(<ContentLoader isLoading={true} />);
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  test('renders children when isLoading is false', () => {
    render(
      <ContentLoader isLoading={false}>
        <div data-testid="child-content">Content</div>
      </ContentLoader>
    );
    expect(screen.getByTestId('child-content')).toBeInTheDocument();
  });

  test('renders error message when error is present', () => {
    const errorMessage = 'An error occurred';
    render(<ContentLoader isLoading={false} error={errorMessage} />);
    expect(screen.getByText(errorMessage)).toBeInTheDocument();
  });

  test('renders retry button when onRetry is provided and error is present', () => {
    const errorMessage = 'An error occurred';
    const mockRetry = jest.fn();
    render(<ContentLoader isLoading={false} error={errorMessage} onRetry={mockRetry} />);
    
    const retryButton = screen.getByRole('button', { name: /try again/i });
    expect(retryButton).toBeInTheDocument();
    
    retryButton.click();
    expect(mockRetry).toHaveBeenCalledTimes(1);
  });

  test('renders skeleton loader when type is SKELETON', () => {
    render(<ContentLoader isLoading={true} type={LoaderType.SKELETON} />);
    expect(screen.getByTestId('skeleton-loader')).toBeInTheDocument();
  });
});