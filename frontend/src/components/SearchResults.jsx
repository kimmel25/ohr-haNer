import React from 'react';

/**
 * SearchResults Component
 * Displays the results of the search pipeline.
 * 
 * Props:
 * - searchResult: The result object from the search API.
 */
const SearchResults = ({ searchResult }) => {
  if (!searchResult) return null;

  return (
    <div className="search-results">
      {/* Interpretation from Step 2 */}
      {searchResult.interpretation && (
        <div className="interpretation-box">
          <h3>Understanding</h3>
          <p>{searchResult.interpretation}</p>
          {searchResult.query_type && (
            <span className="query-type-badge">{searchResult.query_type}</span>
          )}
        </div>
      )}

      {/* Primary Source */}
      {searchResult.primary_source && (
        <div className="primary-source-box">
          <h3>Primary Source</h3>
          <p className="primary-ref" dir="rtl">{searchResult.primary_source_he || searchResult.primary_source}</p>
        </div>
      )}

      {/* Sources by Level */}
      {searchResult.sources_by_level && Object.keys(searchResult.sources_by_level).length > 0 && (
        <div className="sources-container">
          <h3>Sources ({searchResult.total_sources} found)</h3>
          {Object.entries(searchResult.sources_by_level).map(([level, sources]) => (
            <div key={level} className="source-level">
              <h4 className="level-header">{level}</h4>
              <div className="source-list">
                {sources.map((source, idx) => (
                  <div key={idx} className="source-item">
                    <div className="source-ref">
                      <span className="he-ref" dir="rtl">{source.he_ref || source.ref}</span>
                      {source.author && <span className="source-author">({source.author})</span>}
                    </div>
                    {source.hebrew_text && (
                      <p className="source-text" dir="rtl">{source.hebrew_text}</p>
                    )}
                    {source.english_text && (
                      <p className="source-text-en">{source.english_text}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Flat sources list (fallback) */}
      {searchResult.sources?.length > 0 && (!searchResult.sources_by_level || Object.keys(searchResult.sources_by_level).length === 0) && (
        <div className="sources-container">
          <h3>Sources ({searchResult.sources.length} found)</h3>
          <div className="source-list">
            {searchResult.sources.map((source, idx) => (
              <div key={idx} className="source-item">
                <div className="source-ref">
                  <span className="he-ref" dir="rtl">{source.he_ref || source.ref}</span>
                </div>
                {source.hebrew_text && (
                  <p className="source-text" dir="rtl">{source.hebrew_text}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Related Sugyos */}
      {searchResult.related_sugyos?.length > 0 && (
        <div className="related-sugyos">
          <h3>Related Topics</h3>
          <div className="sugya-list">
            {searchResult.related_sugyos.map((sugya, idx) => (
              <div key={idx} className="sugya-item">
                <span className="sugya-ref" dir="rtl">{sugya.he_ref || sugya.ref}</span>
                {sugya.connection && <span className="sugya-connection">({sugya.connection})</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* No results message */}
      {searchResult.total_sources === 0 && (
        <div className="no-results">
          <p>No sources found for this term.</p>
          {searchResult.message && <p className="result-message">{searchResult.message}</p>}
        </div>
      )}
    </div>
  );
};

export default SearchResults;