import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import EnhancedSearchBar from '../search/EnhancedSearchBar';
import { act } from 'react-dom/test-utils';

// Mock props
const mockOnSearch = jest.fn();
const mockGetSuggestions = jest.fn();
const mockOnClear = jest.fn();

// Mock data
const mockSuggestions = [
  { text: 'Document about AI', type: 'document' },
  { text: 'Machine Learning', type: 'tag' },
  { text: 'Previous search', type: 'history' }
];

// Default props
const defaultProps = {
  onSearch: mockOnSearch,
  placeholder: 'Search...',
  initialQuery: '',
  initialFilters: [],
  availableFilters: [
    { field: 'type', label: 'Document Type', options: ['PDF', 'DOCX', 'TXT'] },
    { field: 'owner', label: 'Owner' }
  ],
  showSortOptions: true,
  showFilterOptions: true,
  showRecentSearches: true,
  getSuggestions: mockGetSuggestions,
  onClear: mockOnClear
};

describe('EnhancedSearchBar Integration Tests', () => {
  beforeEach(() => {
    mockOnSearch.mockClear();
    mockGetSuggestions.mockClear();
    mockOnClear.mockClear();
    
    // Setup localStorage mock
    jest.spyOn(Storage.prototype, 'getItem').mockImplementation((key) => {
      if (key === 'recent_searches') {
        return JSON.stringify(['previous search 1', 'previous search 2']);
      }
      return null;
    });
    
    mockGetSuggestions.mockResolvedValue(mockSuggestions);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('search is triggered when pressing Enter', async () => {
    render(<EnhancedSearchBar {...defaultProps} />);
    
    const searchInput = screen.getByPlaceholderText('Search...');
    
    // Type in the search input
    fireEvent.change(searchInput, { target: { value: 'test query' } });
    
    // Press Enter
    fireEvent.keyDown(searchInput, { key: 'Enter', code: 'Enter' });
    
    // Check if onSearch was called with the correct parameters
    expect(mockOnSearch).toHaveBeenCalledWith(expect.objectContaining({
      text: 'test query',
      filters: []
    }));
  });

  test('shows suggestions when typing in search input', async () => {
    render(<EnhancedSearchBar {...defaultProps} />);
    
    const searchInput = screen.getByPlaceholderText('Search...');
    
    // Type in the search input
    await act(async () => {
      fireEvent.change(searchInput, { target: { value: 'test' } });
    });
    
    // Wait for suggestions to appear
    await waitFor(() => {
      expect(mockGetSuggestions).toHaveBeenCalledWith('test');
    });
    
    // Suggestions should be visible
    await waitFor(() => {
      expect(screen.getByText('Document about AI')).toBeInTheDocument();
      expect(screen.getByText('Machine Learning')).toBeInTheDocument();
      expect(screen.getByText('Previous search')).toBeInTheDocument();
    });
  });

  test('clicking clear button clears input and calls onClear', async () => {
    render(<EnhancedSearchBar {...defaultProps} initialQuery="initial query" />);
    
    const clearButton = screen.getByTitle(/clear/i);
    
    // Click clear button
    fireEvent.click(clearButton);
    
    // Check if input is cleared
    const searchInput = screen.getByPlaceholderText('Search...');
    expect(searchInput).toHaveValue('');
    
    // Check if onClear was called
    expect(mockOnClear).toHaveBeenCalled();
  });

  test('adding filter triggers search with filter', async () => {
    render(<EnhancedSearchBar {...defaultProps} />);
    
    // Open filter dropdown
    const filterButton = screen.getByTitle('search.filter');
    fireEvent.click(filterButton);
    
    // Select a filter option
    const filterSelect = screen.getAllByRole('combobox')[0];
    fireEvent.change(filterSelect, { target: { value: 'PDF' } });
    
    // Check if onSearch was called with the correct filter
    await waitFor(() => {
      expect(mockOnSearch).toHaveBeenCalledWith(expect.objectContaining({
        filters: [expect.objectContaining({
          field: 'type',
          value: 'PDF'
        })]
      }));
    });
  });
});