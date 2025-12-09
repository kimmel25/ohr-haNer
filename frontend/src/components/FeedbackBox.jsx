import React from 'react';

/**
 * FeedbackBox Component
 * Displays a feedback form when the user indicates the result is incorrect.
 * 
 * Props:
 * - decipherResult: The result object from the decipher API.
 * - feedbackText: The current feedback text entered by the user.
 * - setFeedbackText: Function to update the feedback text state.
 * - handleFeedbackSubmit: Function to handle feedback form submission.
 * - handleTryDifferentSpelling: Function to handle "Try a different spelling" action.
 * - loading: Boolean indicating if the app is loading.
 */
const FeedbackBox = ({ decipherResult, feedbackText, setFeedbackText, handleFeedbackSubmit, handleTryDifferentSpelling, loading }) => {
  return (
    <div className="feedback-box">
      <h3>Help us improve</h3>
      <p>
        You searched for <strong>"{decipherResult?.original_query}"</strong> 
        {decipherResult?.hebrew_term && (
          <> and we suggested <strong dir="rtl">{decipherResult.hebrew_term}</strong></>
        )}
      </p>
      
      <form onSubmit={handleFeedbackSubmit} className="feedback-form">
        <label>
          What were you looking for? (optional)
          <textarea
            value={feedbackText}
            onChange={(e) => setFeedbackText(e.target.value)}
            placeholder="e.g., 'I meant the concept from Kesubos, not Gittin' or 'The spelling should be...' or just leave blank"
            rows="3"
          />
        </label>
        
        <div className="feedback-buttons">
          <button type="submit" className="submit-feedback-btn" disabled={loading}>
            {loading ? 'Searching...' : 'Show me other options'}
          </button>
          <button 
            type="button" 
            className="try-again-btn"
            onClick={handleTryDifferentSpelling}
          >
            Try a different spelling
          </button>
        </div>
      </form>
    </div>
  );
};

export default FeedbackBox;