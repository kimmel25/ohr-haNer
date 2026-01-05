import React, { useState, useCallback, useMemo } from 'react';

/**
 * SourceFeedbackPanel Component
 *
 * Collects user feedback on search results:
 * - Overall satisfaction (5 levels)
 * - Per-source thumbs up/down
 *
 * Props:
 * - queryId: Unique identifier for this search session
 * - originalQuery: The original search query
 * - hebrewTerms: Array of resolved Hebrew terms
 * - sources: Array of source objects from search results
 * - apiBase: Base URL for API calls
 * - onFeedbackSubmitted: Callback when feedback is submitted
 */
const SourceFeedbackPanel = ({
  queryId,
  originalQuery,
  hebrewTerms = [],
  sources = [],
  apiBase,
  onFeedbackSubmitted,
  sourceRatings = {},  // Shared state from parent
  onSourceRate,        // Callback to update shared state
}) => {
  // Overall satisfaction state
  const [satisfaction, setSatisfaction] = useState('neutral');

  // Optional comment
  const [comment, setComment] = useState('');

  // Submission state
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  // Satisfaction options
  const satisfactionOptions = [
    { value: 'very_satisfied', label: 'Very Happy', emoji: '😄' },
    { value: 'satisfied', label: 'Happy', emoji: '🙂' },
    { value: 'neutral', label: 'Neutral', emoji: '😐' },
    { value: 'dissatisfied', label: 'Unhappy', emoji: '🙁' },
    { value: 'very_dissatisfied', label: 'Very Unhappy', emoji: '😞' },
  ];

  // Get all unique source refs
  const sourceRefs = useMemo(() => {
    return sources.map(s => s.ref || s.he_ref).filter(Boolean);
  }, [sources]);

  // Count ratings
  const ratingCounts = useMemo(() => {
    const counts = { thumbs_up: 0, thumbs_down: 0 };
    Object.values(sourceRatings).forEach(rating => {
      if (rating === 'thumbs_up') counts.thumbs_up++;
      if (rating === 'thumbs_down') counts.thumbs_down++;
    });
    return counts;
  }, [sourceRatings]);

  // Submit feedback
  const handleSubmit = useCallback(async () => {
    if (!apiBase || !queryId) return;

    setSubmitting(true);
    setError('');

    try {
      // Build source feedbacks array
      const sourceFeedbacks = Object.entries(sourceRatings).map(([ref, rating]) => ({
        source_ref: ref,
        rating: rating,
      }));

      const response = await fetch(`${apiBase}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query_id: queryId,
          original_query: originalQuery,
          hebrew_terms: hebrewTerms,
          overall_satisfaction: satisfaction,
          source_feedbacks: sourceFeedbacks,
          comment: comment || null,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to submit feedback');
      }

      const data = await response.json();

      if (data.success) {
        setSubmitted(true);
        setResult(data);
        onFeedbackSubmitted?.(data);
      } else {
        setError(data.message || 'Failed to submit feedback');
      }
    } catch (err) {
      setError('Error submitting feedback. Please try again.');
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  }, [apiBase, queryId, originalQuery, hebrewTerms, satisfaction, sourceRatings, comment, onFeedbackSubmitted]);

  // If already submitted, show thank you message
  if (submitted) {
    return (
      <div className="feedback-panel feedback-submitted">
        <h3>Thank you for your feedback!</h3>
        {result?.should_cache && (
          <p className="feedback-cached">Your positive feedback will help improve future searches.</p>
        )}
        <p className="feedback-score">Score: {(result?.combined_score * 100).toFixed(0)}%</p>
      </div>
    );
  }

  return (
    <div className="feedback-panel">
      <h3>How were these results?</h3>

      {/* Overall satisfaction */}
      <div className="satisfaction-section">
        <p className="feedback-label">Overall satisfaction:</p>
        <div className="satisfaction-buttons">
          {satisfactionOptions.map(opt => (
            <button
              key={opt.value}
              type="button"
              className={`satisfaction-btn ${satisfaction === opt.value ? 'selected' : ''}`}
              onClick={() => setSatisfaction(opt.value)}
              title={opt.label}
            >
              <span className="satisfaction-emoji">{opt.emoji}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Per-source ratings summary */}
      {sourceRefs.length > 0 && (
        <div className="source-ratings-summary">
          <p className="feedback-label">
            Rate individual sources below
            {ratingCounts.thumbs_up > 0 || ratingCounts.thumbs_down > 0 ? (
              <span className="rating-counts">
                ({ratingCounts.thumbs_up} 👍, {ratingCounts.thumbs_down} 👎)
              </span>
            ) : null}
          </p>
          <p className="feedback-hint">Click 👍 or 👎 on sources that were helpful or not</p>
        </div>
      )}

      {/* Optional comment */}
      <div className="comment-section">
        <label className="feedback-label">
          Additional comments (optional):
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="What could be improved?"
            rows="2"
            className="feedback-comment"
          />
        </label>
      </div>

      {/* Error message */}
      {error && <p className="feedback-error">{error}</p>}

      {/* Submit button */}
      <button
        type="button"
        className="submit-feedback-btn"
        onClick={handleSubmit}
        disabled={submitting}
      >
        {submitting ? 'Submitting...' : 'Submit Feedback'}
      </button>
    </div>
  );
};

/**
 * SourceRatingButtons Component
 *
 * Inline thumbs up/down buttons for a single source.
 * Used within SearchResults to add rating to each source item.
 *
 * Props:
 * - sourceRef: The source reference string
 * - currentRating: Current rating ('thumbs_up', 'thumbs_down', or null)
 * - onRate: Callback (sourceRef, rating) => void
 */
export const SourceRatingButtons = ({ sourceRef, currentRating, onRate }) => {
  return (
    <div className="source-rating-buttons">
      <button
        type="button"
        className={`rating-btn thumbs-up ${currentRating === 'thumbs_up' ? 'selected' : ''}`}
        onClick={() => onRate(sourceRef, 'thumbs_up')}
        title="Helpful source"
      >
        👍
      </button>
      <button
        type="button"
        className={`rating-btn thumbs-down ${currentRating === 'thumbs_down' ? 'selected' : ''}`}
        onClick={() => onRate(sourceRef, 'thumbs_down')}
        title="Not helpful"
      >
        👎
      </button>
    </div>
  );
};

export default SourceFeedbackPanel;
