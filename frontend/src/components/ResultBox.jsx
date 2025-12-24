import React from 'react';

/**
 * ResultBox Component
 * Displays the confirmed Hebrew result and additional options.
 * 
 * Props:
 * - originalQuery: The original query entered by the user.
 * - confirmedHebrew: The confirmed Hebrew translation.
 * - decipherResult: Raw Step 1 response for extra details.
 * - handleNotWhatIMeant: Function to handle feedback submission.
 */
const ResultBox = ({ originalQuery, confirmedHebrew, decipherResult, handleNotWhatIMeant }) => {
  if (!confirmedHebrew) return null;

  const displayOriginal = originalQuery || decipherResult?.original_query || '';
  const sampleRefs = decipherResult?.sample_refs || [];
  const alternatives = decipherResult?.alternatives || [];
  const hebrewTerms = decipherResult?.hebrew_terms?.length
    ? decipherResult.hebrew_terms
    : [confirmedHebrew];
  const isMixedQuery = Boolean(decipherResult?.is_mixed_query);
  const extractionConfident = decipherResult?.extraction_confident !== false;

  return (
    <div className="result-box success">
      <div className="result-header">
        <h3>Result</h3>
      </div>

      <div className="translation-display">
        <span className="original-term">"{displayOriginal}"</span>
        <span className="arrow">-&gt;</span>
        <span className="hebrew-term" dir="rtl">{confirmedHebrew}</span>
      </div>

      {isMixedQuery && (
        <div className={`mixed-query ${extractionConfident ? 'confident' : 'uncertain'}`}>
          <strong>Mixed query detected.</strong>{' '}
          {extractionConfident
            ? 'Extracted multiple Hebrew terms for analysis.'
            : 'Extraction may be incomplete. Consider rephrasing.'}
        </div>
      )}

      {hebrewTerms.length > 1 && (
        <div className="term-list">
          <h4>Extracted Terms</h4>
          <div className="tag-list">
            {hebrewTerms.map((term, idx) => (
              <span key={`${term}-${idx}`} className="tag" dir="rtl">
                {term}
              </span>
            ))}
          </div>
        </div>
      )}

      {sampleRefs.length > 0 && (
        <div className="sample-refs">
          <strong>Sample refs:</strong> {sampleRefs.join(', ')}
        </div>
      )}

      {alternatives.length > 0 && (
        <div className="term-list">
          <h4>Other possibilities</h4>
          <div className="tag-list">
            {alternatives.map((alt, idx) => (
              <span key={`${alt}-${idx}`} className="tag" dir="rtl">
                {alt}
              </span>
            ))}
          </div>
        </div>
      )}
      
      <button 
        className="feedback-btn"
        onClick={handleNotWhatIMeant}
      >
        Submit a correction
      </button>
    </div>
  );
};

export default ResultBox;
