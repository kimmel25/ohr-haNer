import React from 'react';

/**
 * ResultBox Component
 * Displays the confirmed Hebrew result and additional options.
 * 
 * Props:
 * - originalQuery: The original query entered by the user.
 * - confirmedHebrew: The confirmed Hebrew translation.
 * - handleNotWhatIMeant: Function to handle feedback submission.
 */
const ResultBox = ({ originalQuery, confirmedHebrew, handleNotWhatIMeant }) => {
  if (!confirmedHebrew) return null;

  return (
    <div className="result-box success">
      <div className="result-header">
        <h3>Result</h3>
      </div>
      
      <div className="translation-display">
        <span className="original-term">"{originalQuery}"</span>
        <span className="arrow">→</span>
        <span className="hebrew-term" dir="rtl">{confirmedHebrew}</span>
      </div>
      
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