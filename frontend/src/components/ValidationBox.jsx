import React from 'react';

/**
 * ValidationBox Component
 * Displays validation options when the confidence is low or medium.
 * 
 * Props:
 * - decipherResult: The result object from the decipher API.
 * - handleOptionSelect: Function to handle option selection.
 * - handleNoneOfThese: Function to handle "None of these" selection.
 * - loading: Boolean indicating if the app is loading.
 */
const ValidationBox = ({ decipherResult, handleOptionSelect, handleNoneOfThese, loading }) => {
  if (!decipherResult || !decipherResult.needs_validation) return null;

  const validationType = String(decipherResult.validation_type || '').toUpperCase();
  const chooseOptions = decipherResult.choose_options?.length
    ? decipherResult.choose_options
    : decipherResult.alternatives || [];
  const clarifyOptions = decipherResult.clarify_options?.length
    ? decipherResult.clarify_options
    : validationType === 'CLARIFY'
    ? chooseOptions.map((opt) => ({ hebrew: opt, description: '' }))
    : [];
  const wordValidations = decipherResult.word_validations || [];

  return (
    <div className="validation-box">
      <h3>
        {validationType === 'CLARIFY' 
          ? 'Did you mean...'
          : validationType === 'UNKNOWN'
          ? "I'm not sure about this term"
          : 'Please select the correct option'}
      </h3>
      
      {decipherResult.message && (
        <p className="validation-message">{decipherResult.message}</p>
      )}
      
      <div className="validation-query">
        <span className="query-label">Your input:</span>
        <span className="query-text">"{decipherResult.original_query}"</span>
      </div>
      
      {/* CLARIFY type - "Did you mean X or Y?" buttons */}
      {validationType === 'CLARIFY' && clarifyOptions.length > 0 && (
        <div className="clarify-options">
          {clarifyOptions.map((opt, idx) => (
            <button 
              key={idx}
              className="clarify-btn"
              onClick={() => handleOptionSelect(idx + 1)}
              disabled={loading}
            >
              <span className="hebrew-option" dir="rtl">{opt.hebrew}</span>
              {opt.description && <span className="option-desc">{opt.description}</span>}
            </button>
          ))}
        </div>
      )}
      
      {/* CHOOSE type - numbered list */}
      {(validationType === 'CHOOSE' || validationType === 'UNKNOWN') && 
       chooseOptions.length > 0 && (
        <div className="choose-options">
          {chooseOptions.map((opt, idx) => (
            <button 
              key={idx}
              className="choose-btn"
              onClick={() => handleOptionSelect(idx + 1)}
              disabled={loading}
            >
              <span className="option-number">{idx + 1}.</span>
              <span className="hebrew-option" dir="rtl">{opt}</span>
            </button>
          ))}
        </div>
      )}

      {wordValidations.length > 0 && (
        <div className="word-validation-breakdown">
          <h4>Word confidence</h4>
          {wordValidations.map((word, idx) => (
            <div
              key={`${word.original}-${idx}`}
              className={`word-validation-item ${word.needs_validation ? 'uncertain' : 'confident'}`}
            >
              <span className="word-indicator">{word.needs_validation ? '!' : 'OK'}</span>
              <span className="word-original">{word.original}</span>
              <span className="word-arrow">-&gt;</span>
              <span className="word-hebrew" dir="rtl">{word.best_match}</span>
              {word.alternatives?.length > 0 && (
                <span className="word-alternatives">
                  {word.alternatives.slice(0, 3).join(', ')}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
      
      <button 
        className="none-btn"
        onClick={handleNoneOfThese}
        disabled={loading}
      >
        None of these / I'm not sure
      </button>
    </div>
  );
};

export default ValidationBox;
