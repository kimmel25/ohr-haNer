import React, { useCallback, useEffect, useMemo, useState } from 'react';

/**
 * SearchResults Component
 * Displays the results of the search pipeline with Step 2/3 metadata.
 *
 * Props:
 * - searchResult: The result object from the search API.
 * - apiBase: Base URL for API calls (used for /sources).
 * - onSuggestionSelect: Optional handler for clarification suggestions.
 */
const SearchResults = ({ searchResult, apiBase, onSuggestionSelect }) => {
  if (!searchResult) return null;

  const baseUrl = apiBase || '';
  const [expandedSources, setExpandedSources] = useState({});
  const [sourceDetails, setSourceDetails] = useState({});
  const [sourceLoading, setSourceLoading] = useState({});
  const [sourceErrors, setSourceErrors] = useState({});
  useEffect(() => {
    setExpandedSources({});
    setSourceDetails({});
    setSourceLoading({});
    setSourceErrors({});
  }, [searchResult]);

  const normalizeEnum = useCallback((value) => {
    if (value === null || value === undefined) return '';
    if (typeof value === 'string' || typeof value === 'number') return String(value);
    if (typeof value === 'object') {
      if (value.value) return String(value.value);
      if (value.name) return String(value.name);
    }
    return String(value);
  }, []);

  const toList = useCallback((value) => {
    if (!value) return [];
    if (Array.isArray(value)) {
      return value.map((item) => normalizeEnum(item)).filter(Boolean);
    }
    const normalized = normalizeEnum(value);
    return normalized ? [normalized] : [];
  }, [normalizeEnum]);

  const getSnippet = useCallback((text, limit = 240) => {
    if (!text) return '';
    if (text.length <= limit) return text;
    return `${text.slice(0, limit).trim()}...`;
  }, []);

  const getLevelLabel = useCallback((source) => {
    const levelRaw = source.level_hebrew || source.level || source.level_name;
    const normalized = normalizeEnum(levelRaw);
    return normalized || 'Other';
  }, [normalizeEnum]);

  const groupByLevel = useCallback((sources) => {
    return sources.reduce((acc, source) => {
      const label = getLevelLabel(source);
      if (!acc[label]) acc[label] = [];
      acc[label].push(source);
      return acc;
    }, {});
  }, [getLevelLabel]);

  const hebrewTerms = useMemo(() => {
    if (searchResult.hebrew_terms?.length) return searchResult.hebrew_terms;
    if (searchResult.hebrew_term) return [searchResult.hebrew_term];
    return [];
  }, [searchResult]);

  const primarySources = useMemo(() => {
    if (searchResult.primary_sources?.length) return searchResult.primary_sources;
    if (searchResult.primary_source) return [searchResult.primary_source];
    return [];
  }, [searchResult]);

  const levelsIncluded = useMemo(() => {
    if (searchResult.levels_included?.length) return searchResult.levels_included;
    if (searchResult.levels_found?.length) return searchResult.levels_found;
    return [];
  }, [searchResult]);

  const clarificationPrompt =
    searchResult.clarification_prompt ||
    searchResult.clarification_question ||
    searchResult.clarificationPrompt ||
    '';

  const clarificationOptionsRaw =
    searchResult.clarification_options ||
    searchResult.clarificationOptions ||
    [];
  const clarificationOptions = Array.isArray(clarificationOptionsRaw)
    ? clarificationOptionsRaw
    : [];
  const hasClarification =
    Boolean(searchResult.needs_clarification) &&
    (Boolean(clarificationPrompt) || clarificationOptions.length > 0);

  const discoveredDapim =
    searchResult.discovered_dapim ||
    searchResult.discovery?.main_sugyos ||
    [];

  const searchSummary =
    searchResult.search_description ||
    searchResult.message ||
    '';

  const sourcesByTermEntries = useMemo(() => {
    const sourcesByTerm = searchResult.sources_by_term;
    if (!sourcesByTerm || typeof sourcesByTerm !== 'object' || Array.isArray(sourcesByTerm)) return [];
    return Object.entries(sourcesByTerm).filter(([, sources]) =>
      Array.isArray(sources) && sources.length > 0
    );
  }, [searchResult]);

  const flatSources = useMemo(() => {
    if (searchResult.sources?.length) return searchResult.sources;
    if (searchResult.sources_by_level) {
      return Object.values(searchResult.sources_by_level).flatMap((sources) => sources || []);
    }
    return [];
  }, [searchResult]);

  const groupedSources = useMemo(() => {
    if (!searchResult.sources?.length && searchResult.sources_by_level) {
      return searchResult.sources_by_level;
    }
    return groupByLevel(flatSources);
  }, [flatSources, groupByLevel, searchResult]);

  const totalSources = typeof searchResult.total_sources === 'number'
    ? searchResult.total_sources
    : flatSources.length;
  const totalSourcesByTerm = useMemo(
    () => sourcesByTermEntries.reduce((sum, [, sources]) => sum + sources.length, 0),
    [sourcesByTermEntries]
  );
  const hasSources = sourcesByTermEntries.length > 0 || totalSources > 0;

  const handleToggleSource = useCallback(async (source) => {
    const ref = source.ref || source.he_ref;
    if (!ref) return;

    const isExpanded = Boolean(expandedSources[ref]);
    setExpandedSources((prev) => ({ ...prev, [ref]: !isExpanded }));

    if (isExpanded || sourceDetails[ref] || sourceLoading[ref] || !baseUrl) {
      return;
    }

    setSourceLoading((prev) => ({ ...prev, [ref]: true }));
    setSourceErrors((prev) => ({ ...prev, [ref]: '' }));

    try {
      const response = await fetch(`${baseUrl}/sources/${encodeURIComponent(ref)}`);
      if (!response.ok) {
        throw new Error('Failed to load source');
      }
      const data = await response.json();
      if (data?.success) {
        setSourceDetails((prev) => ({ ...prev, [ref]: data }));
      } else {
        setSourceErrors((prev) => ({
          ...prev,
          [ref]: data?.message || 'Unable to load source',
        }));
      }
    } catch (err) {
      setSourceErrors((prev) => ({
        ...prev,
        [ref]: 'Unable to load source text.',
      }));
      console.error(err);
    } finally {
      setSourceLoading((prev) => ({ ...prev, [ref]: false }));
    }
  }, [baseUrl, expandedSources, sourceDetails, sourceLoading]);

  const renderSourceItem = (source, idx, forcedLevelLabel = '') => {
    const ref = source.ref || source.he_ref || `source-${idx}`;
    const isExpanded = Boolean(expandedSources[ref]);
    const detail = sourceDetails[ref];
    const showHebrew = isExpanded ? (detail?.hebrew_text || source.hebrew_text) : getSnippet(source.hebrew_text);
    const showEnglish = isExpanded ? (detail?.english_text || source.english_text) : getSnippet(source.english_text, 200);
    const levelLabel = getLevelLabel(source);
    const displayLevel = levelLabel === 'Other' && forcedLevelLabel
      ? forcedLevelLabel
      : levelLabel;
    const relatedTerm = source.related_term || source.relatedTerm;
    const relevanceNote = source.relevance_note || source.relevance_description;

    return (
      <div key={`${ref}-${idx}`} className="source-item">
        <div className="source-ref">
          <span className="he-ref" dir="rtl">{source.he_ref || source.ref}</span>
          {source.author && <span className="source-author">({source.author})</span>}
          {displayLevel && <span className="level-badge">{displayLevel}</span>}
        </div>
        {(relatedTerm || relevanceNote || source.citation_count) && (
          <div className="source-meta">
            {relatedTerm && <span className="meta-pill">Term: {relatedTerm}</span>}
            {relevanceNote && <span className="meta-pill">{relevanceNote}</span>}
            {source.citation_count && (
              <span className="meta-pill">Citations: {source.citation_count}</span>
            )}
          </div>
        )}
        {showHebrew && <p className="source-text" dir="rtl">{showHebrew}</p>}
        {showEnglish && <p className="source-text-en">{showEnglish}</p>}

        <div className="source-actions">
          <button
            type="button"
            className="source-action-btn"
            onClick={() => handleToggleSource(source)}
            disabled={!baseUrl || sourceLoading[ref]}
          >
            {sourceLoading[ref]
              ? 'Loading...'
              : isExpanded
              ? 'Hide full text'
              : 'Show full text'}
          </button>
        </div>

        {sourceErrors[ref] && <p className="source-error">{sourceErrors[ref]}</p>}

        {isExpanded && detail?.categories?.length > 0 && (
          <div className="source-tags">
            <span className="tag-label">Categories:</span>
            <div className="tag-list">
              {detail.categories.map((category, cIdx) => (
                <span key={`${ref}-cat-${cIdx}`} className="tag">
                  {category}
                </span>
              ))}
            </div>
          </div>
        )}

      </div>
    );
  };

  const renderGroupedSources = (sourcesMap) => (
    Object.entries(sourcesMap).map(([level, sources]) => (
      <div key={level} className="source-level">
        <h4 className="level-header">{level}</h4>
        <div className="source-list">
          {sources.map((source, idx) => renderSourceItem(source, idx, level))}
        </div>
      </div>
    ))
  );

  const searchMethod = normalizeEnum(
    searchResult.search_method || searchResult.fetch_strategy || ''
  );
  const queryType = normalizeEnum(searchResult.query_type || '');
  const realm = normalizeEnum(searchResult.realm || '');
  const depth = normalizeEnum(searchResult.depth || '');
  const confidence = normalizeEnum(searchResult.confidence || '');
  const transliterationMethod = normalizeEnum(
    searchResult.transliteration_method || searchResult.transliterationMethod || ''
  );
  const transliterationConfidence = normalizeEnum(
    searchResult.transliteration_confidence || searchResult.transliterationConfidence || ''
  );
  const isMixedQuery =
    typeof searchResult.is_mixed_query === 'boolean'
      ? searchResult.is_mixed_query
      : null;

  const searchTopics = searchResult.search_topics_hebrew?.length
    ? searchResult.search_topics_hebrew
    : searchResult.search_topics;

  const tagSections = [
    { label: 'Hebrew terms', items: hebrewTerms },
    { label: 'Search topics', items: toList(searchTopics) },
    { label: 'Target authors', items: toList(searchResult.target_authors) },
    { label: 'Target masechtos', items: toList(searchResult.target_masechtos) },
    { label: 'Target refs', items: toList(searchResult.target_refs) },
    { label: 'Levels included', items: toList(levelsIncluded) },
  ].filter((section) => section.items.length > 0);

  return (
    <div className="search-results">
      {hasClarification && (
        <div className="clarification-box">
          <h3>Clarification needed</h3>
          {clarificationPrompt && <p>{clarificationPrompt}</p>}
          {clarificationOptions.length > 0 && (
            <div className="clarification-options">
              {clarificationOptions.map((option, idx) => (
                <button
                  key={`${option}-${idx}`}
                  type="button"
                  className="clarification-option-btn"
                  onClick={() => onSuggestionSelect?.(option)}
                  disabled={!onSuggestionSelect}
                >
                  {option}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {(searchResult.interpretation || queryType || searchMethod || realm || depth || confidence || transliterationMethod || transliterationConfidence || isMixedQuery !== null) && (
        <div className="analysis-box">
          <h3>Understanding</h3>
          {searchResult.interpretation && <p>{searchResult.interpretation}</p>}
          <div className="meta-grid">
            {queryType && (
              <div className="meta-item">
                <span className="meta-label">Query type</span>
                <span className="meta-value">{queryType}</span>
              </div>
            )}
            {searchMethod && (
              <div className="meta-item">
                <span className="meta-label">Search method</span>
                <span className="meta-value">{searchMethod}</span>
              </div>
            )}
            {realm && (
              <div className="meta-item">
                <span className="meta-label">Realm</span>
                <span className="meta-value">{realm}</span>
              </div>
            )}
            {depth && (
              <div className="meta-item">
                <span className="meta-label">Depth</span>
                <span className="meta-value">{depth}</span>
              </div>
            )}
            {confidence && (
              <div className="meta-item">
                <span className="meta-label">Confidence</span>
                <span className="meta-value">{confidence}</span>
              </div>
            )}
            {transliterationMethod && (
              <div className="meta-item">
                <span className="meta-label">Transliteration</span>
                <span className="meta-value">{transliterationMethod}</span>
              </div>
            )}
            {transliterationConfidence && (
              <div className="meta-item">
                <span className="meta-label">Transliteration confidence</span>
                <span className="meta-value">{transliterationConfidence}</span>
              </div>
            )}
            {isMixedQuery !== null && (
              <div className="meta-item">
                <span className="meta-label">Mixed query</span>
                <span className="meta-value">{isMixedQuery ? 'Yes' : 'No'}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {tagSections.length > 0 && (
        <div className="tag-section">
          {tagSections.map((section) => (
            <div key={section.label} className="tag-block">
              <span className="tag-label">{section.label}</span>
              <div className="tag-list">
                {section.items.map((item, idx) => (
                  <span key={`${section.label}-${idx}`} className="tag" dir="auto">
                    {item}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {primarySources.length > 0 && (
        <div className="primary-source-box">
          <h3>Primary Source</h3>
          <div className="tag-list">
            {primarySources.map((source, idx) => (
              <span key={`${source}-${idx}`} className="tag" dir="auto">
                {source}
              </span>
            ))}
          </div>
          {searchResult.primary_source_he && (
            <p className="primary-ref" dir="rtl">{searchResult.primary_source_he}</p>
          )}
        </div>
      )}

      {(searchSummary || discoveredDapim.length > 0) && (
        <div className="search-summary">
          <h3>Search Summary</h3>
          {searchSummary && <p>{searchSummary}</p>}
          {discoveredDapim.length > 0 && (
            <div className="discovered-list">
              <span className="meta-label">Main sugyos</span>
              <div className="tag-list">
                {discoveredDapim.map((daf, idx) => (
                  <span key={`${daf}-${idx}`} className="tag" dir="auto">
                    {daf}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {sourcesByTermEntries.length > 0 ? (
        <div className="sources-container">
          <h3>Sources by Term ({totalSourcesByTerm} found)</h3>
          {sourcesByTermEntries.map(([term, sources]) => {
            const grouped = groupByLevel(sources);
            return (
              <div key={term} className="term-group">
                <h4 className="term-header" dir="auto">{term}</h4>
                {renderGroupedSources(grouped)}
              </div>
            );
          })}
        </div>
      ) : (
        totalSources > 0 && (
          <div className="sources-container">
            <h3>Sources ({totalSources} found)</h3>
            {Object.keys(groupedSources).length > 0 ? (
              renderGroupedSources(groupedSources)
            ) : (
              <div className="source-list">
                {flatSources.map((source, idx) => renderSourceItem(source, idx))}
              </div>
            )}
          </div>
        )
      )}

      {searchResult.related_sugyos?.length > 0 && (
        <div className="related-sugyos">
          <h3>Related Topics</h3>
          <div className="sugya-list">
            {searchResult.related_sugyos.map((sugya, idx) => (
              <div key={`${sugya.ref}-${idx}`} className="sugya-item">
                <div className="sugya-ref" dir="rtl">{sugya.he_ref || sugya.ref}</div>
                {sugya.connection && <span className="sugya-connection">({sugya.connection})</span>}
                {sugya.preview_text && (
                  <p className="sugya-preview">{sugya.preview_text}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {!hasSources && (
        <div className="no-results">
          <p>No sources found for this term.</p>
          {searchResult.message && <p className="result-message">{searchResult.message}</p>}
        </div>
      )}
    </div>
  );
};

export default SearchResults;
