import { useState } from 'react'
import './App.css'

function App() {
  const [topic, setTopic] = useState('')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState(null)
  const [clarification, setClarification] = useState(null)
  const [userClarification, setUserClarification] = useState('')
  const [error, setError] = useState('')
  const [resolvedTerms, setResolvedTerms] = useState([])  // NEW: Track resolved Hebrew terms

  const handleSearch = async (e, withClarification = '') => {
    e.preventDefault()
    if (!topic.trim()) return

    setLoading(true)
    setError('')
    setResults(null)
    setClarification(null)
    setResolvedTerms([])  // Clear previous resolutions

    try {
      const body = { topic }
      if (withClarification) {
        body.clarification = withClarification
      }

      const response = await fetch('http://localhost:8000/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      })

      if (!response.ok) {
        throw new Error('Failed to fetch sources')
      }

      const data = await response.json()
      
      // NEW: Extract resolved terms if present
      if (data.resolved_terms && data.resolved_terms.length > 0) {
        setResolvedTerms(data.resolved_terms)
      }
      
      // Check if we need clarification
      if (data.needs_clarification && data.clarifying_questions && data.clarifying_questions.length > 0) {
        setClarification({
          interpreted_as: data.interpreted_query,
          questions: data.clarifying_questions
        })
        setUserClarification('')
      } else {
        // We have results
        setResults(data)
      }
    } catch (err) {
      setError('Error connecting to server. Make sure the backend is running.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleClarificationSubmit = (e) => {
    e.preventDefault()
    if (!userClarification.trim()) return
    handleSearch(e, userClarification)
  }

  // Group sources by category
  const groupedSources = results?.sources?.reduce((acc, source) => {
    const category = source.category || 'Other'
    if (!acc[category]) {
      acc[category] = []
    }
    acc[category].push(source)
    return acc
  }, {})

  // Define category order
  const categoryOrder = [
    'Chumash', 'Nach', 'Mishna', 'Gemara', 'Rishonim', 
    'Shulchan Aruch', 'Acharonim', 'Other'
  ]

  // NEW: Helper to get confidence badge color
  const getConfidenceColor = (confidence) => {
    switch (confidence) {
      case 'high': return 'confidence-high'
      case 'medium': return 'confidence-medium'
      case 'low': return 'confidence-low'
      default: return 'confidence-unknown'
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>אור הנר</h1>
        <h2>Marei Mekomos Finder</h2>
        <p>Enter any topic to find relevant מקומות</p>
        <p className="version">V5.0 - Now with smart transliteration! 🎯</p>
      </header>

      <form onSubmit={handleSearch} className="search-form">
        <div className="input-group">
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="Enter a topic (e.g, bedikas chometz, ביטול חמץ, chezkas rav huna)"
            className="topic-input"
            dir="auto"
            disabled={loading}
          />
        </div>

        <button type="submit" disabled={loading || !topic.trim()}>
          {loading ? 'Searching...' : 'בודק'}
        </button>
      </form>

      {/* NEW: Display resolved Hebrew terms */}
      {resolvedTerms.length > 0 && (
        <div className="resolved-terms-box">
          <h3>🎯 Found Hebrew Term{resolvedTerms.length > 1 ? 's' : ''}!</h3>
          {resolvedTerms.map((term, idx) => (
            <div key={idx} className="resolved-term">
              <div className="term-header">
                <span className="original-term">"{term.original}"</span>
                <span className="arrow">→</span>
                <span className="hebrew-term" dir="rtl">{term.hebrew}</span>
                <span className={`confidence-badge ${getConfidenceColor(term.confidence)}`}>
                  {term.confidence}
                </span>
              </div>
              <div className="term-details">
                <p className="source-ref">
                  <strong>Source:</strong> {term.source_ref}
                </p>
                <p className="explanation">
                  <strong>Why this match:</strong> {term.explanation}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      {error && <div className="error">{error}</div>}

      {clarification && (
        <div className="clarification-box">
          <h3>📋 I need a bit more info...</h3>
          <p className="interpreted-as">
            I understood you're asking about: <em>{clarification.interpreted_as}</em>
          </p>
          <div className="questions">
            {clarification.questions.map((q, idx) => (
              <p key={idx} className="question">
                <strong>{idx + 1}.</strong> {q}
              </p>
            ))}
          </div>
          <form onSubmit={handleClarificationSubmit} className="clarification-form">
            <textarea
              value={userClarification}
              onChange={(e) => setUserClarification(e.target.value)}
              placeholder="Your answer... (e.g., 'I'm looking for the foundational sugya about chuppah being koneh')"
              className="clarification-input"
              rows="3"
            />
            <div className="clarification-buttons">
              <button type="submit" disabled={!userClarification.trim()}>
                Continue Search
              </button>
              <button 
                type="button" 
                onClick={(e) => handleSearch(e, "Search for all related sources")}
                className="secondary-button"
              >
                Just show me everything related
              </button>
            </div>
          </form>
        </div>
      )}

      {results && (
        <div className="results">
          <h3>Sources for: {results.topic}</h3>
          
          {results.interpreted_query && (
            <p className="interpreted-query">
              <strong>Interpreted as:</strong> {results.interpreted_query}
            </p>
          )}
          
          {results.summary && (
            <p className="summary">{results.summary}</p>
          )}

          {results.sources.length === 0 ? (
            <p>No sources found. Try a different topic or spelling.</p>
          ) : (
            <div className="sources-container">
              {categoryOrder.map(category => {
                const sources = groupedSources?.[category]
                if (!sources || sources.length === 0) return null

                return (
                  <div key={category} className="category-section">
                    <h4 className="category-title">{category}</h4>
                    
                    {sources.map((source, idx) => (
                      <div key={idx} className="source-card">
                        <div className="source-header">
                          <a 
                            href={source.sefaria_url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="source-ref"
                          >
                            {source.he_ref || source.ref}
                          </a>
                          <span className="source-ref-en">({source.ref})</span>
                        </div>
                        
                        {source.he_text && (
                          <div className="source-text he" dir="rtl">
                            {source.he_text}
                          </div>
                        )}
                        
                        {source.en_text && (
                          <div className="source-text en">
                            {source.en_text}
                          </div>
                        )}

                        {source.relevance && (
                          <div className="source-relevance">
                            <strong>Why relevant:</strong> {source.relevance}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )
              })}
            </div>
          )}

          <p className="source-count">
            Found {results.sources.length} sources
          </p>
        </div>
      )}
    </div>
  )
}

export default App