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

import React, { useState, useCallback } from 'react';
import './App.css';
import Header from './components/Header';
import SearchForm from './components/SearchForm';
import ErrorBox from './components/ErrorBox';
import ResultBox from './components/ResultBox';
import ValidationBox from './components/ValidationBox';
import FeedbackBox from './components/FeedbackBox'
import SearchResults from './components/SearchResults';

// API base URL - change for production
const API_BASE = 'http://localhost:8000';

function App() {
  // ==========================================
  //  STATE
  // ==========================================

  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Step 1 result
  const [decipherResult, setDecipherResult] = useState(null);
  
  // For when user needs to make a selection
  const [showValidation, setShowValidation] = useState(false);
  
  // For user feedback when translation is wrong
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackText, setFeedbackText] = useState('');
  
  // Final confirmed Hebrew (after validation if needed)
  const [confirmedHebrew, setConfirmedHebrew] = useState(null);
  
  // Steps 2 & 3: Search results
  const [searchResult, setSearchResult] = useState(null);
  const [searchLoading, setSearchLoading] = useState(false);

  // ==========================================
  //  API CALLS
  // ==========================================

  const callDecipher = useCallback(async (queryText, strict = false) => {
    setLoading(true);
    setError('');
    setDecipherResult(null);
    setShowValidation(false);
    setShowFeedback(false);
    setConfirmedHebrew(null);
    setSearchResult(null);

    try {
      const response = await fetch(`${API_BASE}/decipher`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: queryText, strict })
      });

      if (!response.ok) {
        throw new Error('Failed to process transliteration');
      }

      const data = await response.json();
      setDecipherResult(data);

      // If high confidence, no validation needed
      if (!data.needs_validation && data.hebrew_term) {
        // Use the hebrew_term directly - it's the complete phrase from the dictionary
        // Don't reconstruct from word_validations as that can break multi-word phrases
        const completeHebrew = data.hebrew_term;
        setConfirmedHebrew(completeHebrew);
        console.log('[callDecipher] High-confidence result:', completeHebrew);
        // Auto-trigger Steps 2 & 3
        callSearch(completeHebrew);
      } else if (data.needs_validation) {
        setShowValidation(true);
      }
      
    } catch (err) {
      setError('Error connecting to server. Make sure the backend is running.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);
  
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
        
        // Auto-trigger Steps 2 & 3
        callSearch(completeHebrew)
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
  
  // Call the full search pipeline (Steps 2 & 3)
  const callSearch = useCallback(async (hebrewTerm) => {
    setSearchLoading(true)
    setSearchResult(null)
    
    try {
      const response = await fetch(`${API_BASE}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: hebrewTerm })
      })
      
      if (!response.ok) {
        throw new Error('Failed to search sources')
      }
      
      const data = await response.json()
      setSearchResult(data)
      
    } catch (err) {
      setError('Error searching for sources. Make sure the backend is running.')
      console.error(err)
    } finally {
      setSearchLoading(false)
    }
  }, [])
  
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
  //  RENDER
  // ==========================================
  
  return (
    <div className="app">
      <Header />
      <SearchForm query={query} setQuery={setQuery} handleSubmit={handleSubmit} loading={loading} />
      <ErrorBox error={error} clearError={() => setError('')} />
      <ResultBox 
        originalQuery={decipherResult?.original_query} 
        confirmedHebrew={confirmedHebrew} 
        handleNotWhatIMeant={handleNotWhatIMeant} 
      />
      <ValidationBox 
        decipherResult={decipherResult} 
        handleOptionSelect={handleOptionSelect} 
        handleNoneOfThese={handleNoneOfThese} 
        loading={loading} 
      />
      {showFeedback && decipherResult && (
        <FeedbackBox 
          decipherResult={decipherResult} 
          feedbackText={feedbackText} 
          setFeedbackText={setFeedbackText} 
          handleFeedbackSubmit={handleFeedbackSubmit} 
          handleTryDifferentSpelling={handleTryDifferentSpelling} 
          loading={loading} 
        />
      )}
      {/* Search Results */}
      <SearchResults searchResult={searchResult} />
      {/* Search Loading Indicator */}
      {searchLoading && (
        <div className="loading-box">
          <div className="loading-spinner"></div>
          <p>Searching for sources...</p>
        </div>
      )}
    </div>
  )
}

export default App