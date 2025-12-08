import React from 'react';

/**
 * SearchForm Component
 * Handles the search input and submission.
 * 
 * Props:
 * - query: Current query string.
 * - setQuery: Function to update the query state.
 * - handleSubmit: Function to handle form submission.
 * - loading: Boolean indicating if the app is loading.
 */
const SearchForm = ({ query, setQuery, handleSubmit, loading }) => {
  return (
    <form onSubmit={handleSubmit} className="search-form">
      <div className="input-group">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g., chezkas haguf, bari vishma, מיגו"
          className="query-input"
          dir="auto"
          disabled={loading}
        />
      </div>
      
      <button 
        type="submit" 
        disabled={loading || !query.trim()}
        className="search-btn"
      >
        {loading ? '...' : 'בדוק'}
      </button>
    </form>
  );
};

export default SearchForm;