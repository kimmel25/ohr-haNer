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

  return (
    <div className="validation-box">
      <h3>
        {decipherResult.validation_type === 'CLARIFY' 
          ? 'Did you mean...'
          : decipherResult.validation_type === 'UNKNOWN'
          ? "I'm not sure about this term"
          : 'Please select the correct option'}
      </h3>
      
      <p className="validation-message">{decipherResult.message}</p>
      
      <div className="validation-query">
        <span className="query-label">Your input:</span>
        <span className="query-text">"{decipherResult.original_query}"</span>
      </div>
      
      {/* CLARIFY type - "Did you mean X or Y?" buttons */}
      {decipherResult.validation_type === 'CLARIFY' && decipherResult.clarify_options?.length > 0 && (
        <div className="clarify-options">
          {decipherResult.clarify_options.map((opt, idx) => (
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
      {(decipherResult.validation_type === 'CHOOSE' || decipherResult.validation_type === 'UNKNOWN') && 
       decipherResult.choose_options?.length > 0 && (
        <div className="choose-options">
          {decipherResult.choose_options.map((opt, idx) => (
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