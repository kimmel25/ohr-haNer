/**
 * Marei Mekomos V7 - Frontend
 * ===========================
 * 
 * Step 1 (DECIPHER) Integration:
 * - Shows transliteration → Hebrew conversion
 * - Handles validation scenarios (CLARIFY/CHOOSE/UNKNOWN)
 * - Allows user to confirm or reject translations
 * - Per-word breakdown for multi-word queries
 * 
 * Following Architecture.md principles:
 * - "Never yes or no questions, leave room for I'm not sure"
 * - "Better annoy with asking than getting it wrong"
 */

import { useState, useCallback } from 'react'
import './App.css'

// API base URL - change for production
const API_BASE = 'http://localhost:8000'

function App() {
  // ==========================================
  //  STATE
  // ==========================================
  
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  
  // Step 1 result
  const [decipherResult, setDecipherResult] = useState(null)
  
  // For when user needs to make a selection
  const [showValidation, setShowValidation] = useState(false)
  
  // For user feedback when translation is wrong
  const [showFeedback, setShowFeedback] = useState(false)
  const [feedbackText, setFeedbackText] = useState('')
  
  // Final confirmed Hebrew (after validation if needed)
  const [confirmedHebrew, setConfirmedHebrew] = useState(null)

  // ==========================================
  //  API CALLS
  // ==========================================
  
  const callDecipher = useCallback(async (queryText, strict = false) => {
    setLoading(true)
    setError('')
    setDecipherResult(null)
    setShowValidation(false)
    setShowFeedback(false)
    setConfirmedHebrew(null)
    
    try {
      const response = await fetch(`${API_BASE}/decipher`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: queryText, strict })
      })
      
      if (!response.ok) {
        throw new Error('Failed to process transliteration')
      }
      
      const data = await response.json()
      setDecipherResult(data)
      
      // If high confidence, no validation needed
      if (!data.needs_validation && data.hebrew_term) {
        // For multi-word queries, build complete Hebrew from word_validations
        const completeHebrew = data.word_validations?.length > 1
          ? data.word_validations.map(wv => wv.best_match).join(' ')
          : data.hebrew_term
        setConfirmedHebrew(completeHebrew)
      } else if (data.needs_validation) {
        setShowValidation(true)
      }
      
    } catch (err) {
      setError('Error connecting to server. Make sure the backend is running.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [])
  
  const confirmSelection = useCallback(async (selectionIndex, customHebrew = null) => {
    if (!decipherResult) return
    
    setLoading(true)
    
    try {
      const response = await fetch(`${API_BASE}/decipher/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          original_query: decipherResult.original_query,
          selection_index: selectionIndex,
          selected_hebrew: customHebrew
        })
      })
      
      if (!response.ok) {
        throw new Error('Failed to confirm selection')
      }
      
      const data = await response.json()
      
      if (data.success) {
        // Use the complete hebrew_term from backend (already computed there)
        const completeHebrew = data.hebrew_term
        console.log('Confirm response:', { 
          hebrew_term: data.hebrew_term, 
          word_validations: data.word_validations,
          completeHebrew 
        })
        
        setConfirmedHebrew(completeHebrew)
        
        // Update decipherResult with the new word_validations
        if (data.word_validations?.length > 0) {
          setDecipherResult(prev => ({
            ...prev,
            word_validations: data.word_validations,
            hebrew_term: completeHebrew
          }))
        }
        
        setShowValidation(false)
      } else {
        setError(data.message || 'Could not confirm selection')
      }
      
    } catch (err) {
      setError('Error confirming selection')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [decipherResult])
  
  const rejectTranslation = useCallback(async () => {
    if (!decipherResult || !decipherResult.hebrew_term) return
    
    setLoading(true)
    
    try {
      const response = await fetch(`${API_BASE}/decipher/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          original_query: decipherResult.original_query,
          incorrect_hebrew: decipherResult.hebrew_term,
          user_feedback: feedbackText || null
        })
      })
      
      if (!response.ok) {
        throw new Error('Failed to submit feedback')
      }
      
      const data = await response.json()
      
      // Update with new suggestions
      if (data.suggestions && data.suggestions.length > 0) {
        setDecipherResult(prev => ({
          ...prev,
          choose_options: data.suggestions,
          needs_validation: true,
          validation_type: 'CHOOSE',
          message: data.message
        }))
        setShowValidation(true)
        setShowFeedback(false)
        setConfirmedHebrew(null)
      } else {
        setError("Couldn't find alternatives. Try a different spelling?")
      }
      
    } catch (err) {
      setError('Error submitting feedback')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [decipherResult, feedbackText])

  // ==========================================
  //  HANDLERS
  // ==========================================
  
  const handleSubmit = (e) => {
    e.preventDefault()
    if (!query.trim()) return
    callDecipher(query)
  }
  
  const handleOptionSelect = (index) => {
    confirmSelection(index)
  }
  
  const handleNoneOfThese = () => {
    // Show feedback form instead of immediately rejecting
    setShowFeedback(true)
    setShowValidation(false)
  }
  
  const handleNotWhatIMeant = () => {
    setShowFeedback(true)
  }
  
  const handleFeedbackSubmit = (e) => {
    e.preventDefault()
    rejectTranslation()
  }
  
  const handleTryDifferentSpelling = () => {
    setShowFeedback(false)
    setDecipherResult(null)
    setConfirmedHebrew(null)
    // Focus the input
    document.querySelector('.query-input')?.focus()
  }

  // ==========================================
  //  HELPER FUNCTIONS
  // ==========================================
  
  const getConfidenceColor = (confidence) => {
    switch (confidence) {
      case 'high': return 'confidence-high'
      case 'medium': return 'confidence-medium'
      case 'low': return 'confidence-low'
      default: return 'confidence-unknown'
    }
  }
  
  const getConfidenceEmoji = (confidence) => {
    switch (confidence) {
      case 'high': return '🟢'
      case 'medium': return '🟡'
      case 'low': return '🔴'
      default: return '⚪'
    }
  }

  // ==========================================
  //  RENDER
  // ==========================================
  
  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <h1>אור הנר</h1>
        <h2>מראי מקומות</h2>
        <p className="tagline">Enter any term to find תורה sources</p>
        {/* Version removed per request */}
      </header>

      {/* Search Form */}
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

      {/* Error Display */}
      {error && (
        <div className="error-box">
          <span className="error-icon">⚠️</span>
          <p>{error}</p>
          <button onClick={() => setError('')} className="dismiss-btn">×</button>
        </div>
      )}

      {/* Step 1 Result - High Confidence (no validation needed) */}
      {confirmedHebrew && !showValidation && !showFeedback && (
        <div className="result-box success">
          <div className="result-header">
            <h3>Result</h3>
          </div>
          
          <div className="translation-display">
            <span className="original-term">"{decipherResult?.original_query}"</span>
            <span className="arrow">→</span>
            <span className="hebrew-term" dir="rtl">{confirmedHebrew}</span>
          </div>
          
          {/* Word-by-word breakdown for multi-word queries */}
          {/* Word breakdown removed per request */}
          
          {/* Sample references from Sefaria */}
          {decipherResult?.sample_refs?.length > 0 && (
            <div className="sample-refs">
              <strong>Found in:</strong> {decipherResult.sample_refs.slice(0, 3).join(', ')}
            </div>
          )}
          
          {/* Method indicator removed from UI per request */}
          
          {/* "Not what I meant" button */}
          <button 
            className="feedback-btn"
            onClick={handleNotWhatIMeant}
          >
            Submit a correction
          </button>
        </div>
      )}

      {/* Validation Options - When confidence is low/medium */}
      {showValidation && decipherResult && (
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
          
          {/* Per-word breakdown with indicators */}
          {/* Per-word analysis removed per request */}
          
          {/* "None of these" option - per Architecture.md */}
          <button 
            className="none-btn"
            onClick={handleNoneOfThese}
            disabled={loading}
          >
            None of these / I'm not sure
          </button>
        </div>
      )}

      {/* Feedback Form - When user says "not what I meant" */}
      {showFeedback && (
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
      )}

      {/* Status indicator */}
      {/* Footer removed per request */}
    </div>
  )
}

export default App