| `showSortOptions` | `boolean` | `true` | Whether to show sort options |
| `showFilterOptions` | `boolean` | `true` | Whether to show filter options |
| `showRecentSearches` | `boolean` | `true` | Whether to show recent searches |
| `getSuggestions` | `(text: string) => Promise<Suggestion[]>` | `undefined` | Function to get search suggestions |
| `onClear` | `() => void` | `undefined` | Callback function called when search is cleared |
| `className` | `string` | `''` | Additional CSS class for the component |
| `isLoading` | `boolean` | `false` | Whether the search is loading |
| `maxRecentSearches` | `number` | `5` | Maximum number of recent searches to show |
| `debounceTime` | `number` | `300` | Debounce time in ms for search suggestions |

## Usage

```tsx
import EnhancedSearchBar, { SearchQuery, Suggestion } from '../components/search/EnhancedSearchBar';

// Define available filters
const filters = [
  { field: 'type', label: 'Type', options: ['PDF', 'DOCX', 'TXT'] },
  { field: 'owner', label: 'Owner' },
  { field: 'date', label: 'Date' }
];

// Define suggestion fetcher
const getSuggestions = async (text: string): Promise<Suggestion[]> => {
  // Fetch suggestions from API or generate locally
  return [
    { text: 'React Components', type: 'document' },
    { text: 'JavaScript', type: 'tag' }
  ];
};

// Search handler
const handleSearch = (query: SearchQuery) => {
  console.log('Search query:', query.text);
  console.log('Applied filters:', query.filters);
  console.log('Sort option:', query.sort);
  
  // Perform search with the query
};

// Render component
const MySearchComponent = () => (
  <EnhancedSearchBar
    onSearch={handleSearch}
    placeholder="Search documents..."
    availableFilters={filters}
    getSuggestions={getSuggestions}
    showSortOptions={true}
    showFilterOptions={true}
  />
);