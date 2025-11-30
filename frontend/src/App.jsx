import { useState } from 'react'
import './App.css'

/**
 * Marei Mekomos Frontend v5.0
 * 
 * Features:
 * - Query intent display (lomdus/psak/makor)
 * - Primary masechta highlighting
 * - VGR validation indicator
 * - Methodology notes display
 * - Improved clarification UI (chavrusa-style)
 */

function App() {
  const [topic, setTopic] = useState('')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState(null)
  const [clarification, setClarification] = useState(null)
  const [userClarification, setUserClarification] = useState('')
  const [error, setError] = useState('')
  const [showMethodology, setShowMethodology] = useState(false)

  const handleSearch = async (e, withClarification = '') => {
    e.preventDefault()
    if (!topic.trim()) return

    setLoading(true)
    setError('')
    setResults(null)
    setClarification(null)

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
      
      if (data.needs_clarification && data.clarifying_questions && data.clarifying_questions.length > 0) {
        setClarification({
          interpreted_as: data.interpreted_query,
          questions: data.clarifying_questions
        })
        setUserClarification('')
      } else {
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

  // Category order - Gemara first (primary sources), then chronological
  const categoryOrder = [
    'Gemara', 'Chumash', 'Nach', 'Mishna', 'Rishonim', 
    'Shulchan Aruch', 'Acharonim', 'Other'
  ]

  // Intent display names
  const intentDisplayNames = {
    'lomdus': '📚 Lomdus (Analytical)',
    'psak': '⚖️ Psak (Practical Halacha)',
    'makor': '🔍 Makor (Source Finding)',
    'general': '📖 General'
  }

  return (
    <div className="app">
      <header className="header">
        <h1>אור הנר</h1>
        <h2>Marei Mekomos Finder</h2>
        <p className="subtitle">Sugya Archaeology + VGR Protocol</p>
        <p className="tagline">Enter any topic to find relevant מקומות</p>
      </header>

      <form onSubmit={handleSearch} className="search-form">
        <div className="input-group">
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g., chuppas niddah, bitul chametz, safek sotah, kinyan agav"
            className="topic-input"
            dir="auto"
            disabled={loading}
          />
        </div>

        <div className="examples-row">
          <span className="examples-label">Try:</span>
          <button type="button" className="example-btn" onClick={() => setTopic('chuppas niddah')}>
            chuppas niddah
          </button>
          <button type="button" className="example-btn" onClick={() => setTopic('bitul chametz')}>
            bitul chametz
          </button>
          <button type="button" className="example-btn" onClick={() => setTopic('safek sotah')}>
            safek sotah
          </button>
        </div>

        <button type="submit" disabled={loading || !topic.trim()} className="search-btn">
          {loading ? 'Searching...' : 'חפש מקורות'}
        </button>
      </form>

      {error && <div className="error">{error}</div>}

      {/* Chavrusa-style clarification */}
      {clarification && (
        <div className="clarification-box">
          <div className="clarification-header">
            <span className="chavrusa-icon">🤝</span>
            <h3>Let me make sure I understand...</h3>
          </div>
          
          <p className="interpreted-as">
            I'm understanding you're asking about: <em>{clarification.interpreted_as}</em>
          </p>
          
          <div className="questions">
            <p className="questions-intro">To find the best mekomos, could you clarify:</p>
            {clarification.questions.map((q, idx) => (
              <p key={idx} className="question">
                <span className="question-bullet">•</span> {q}
              </p>
            ))}
          </div>
          
          <form onSubmit={handleClarificationSubmit} className="clarification-form">
            <textarea
              value={userClarification}
              onChange={(e) => setUserClarification(e.target.value)}
              placeholder="Your answer... (e.g., 'I'm looking for the machlokes rishonim about whether chuppah is koneh when she's a niddah')"
              className="clarification-input"
              rows="3"
            />
            <div className="clarification-buttons">
              <button type="submit" disabled={!userClarification.trim()}>
                Continue with clarification
              </button>
              <button 
                type="button" 
                onClick={(e) => handleSearch(e, "Search broadly for all related sources")}
                className="secondary-button"
              >
                Just show me everything
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Results */}
      {results && (
        <div className="results">
          <div className="results-header">
            <h3>Sources for: {results.topic}</h3>
            
            {/* Query metadata */}
            <div className="query-metadata">
              {results.query_intent && (
                <span className={`intent-badge intent-${results.query_intent}`}>
                  {intentDisplayNames[results.query_intent] || results.query_intent}
                </span>
              )}
              {results.primary_masechta && (
                <span className="masechta-badge">
                  📖 {results.primary_masechta}
                </span>
              )}
            </div>
          </div>
          
          {results.interpreted_query && results.interpreted_query !== results.topic && (
            <p className="interpreted">
              Interpreted as: <em>{results.interpreted_query}</em>
            </p>
          )}
          
          {results.summary && (
            <div className="summary-box">
              <h4>Overview</h4>
              <p>{results.summary}</p>
            </div>
          )}

          {/* Methodology toggle */}
          {results.methodology_notes && (
            <div className="methodology-section">
              <button 
                className="methodology-toggle"
                onClick={() => setShowMethodology(!showMethodology)}
              >
                {showMethodology ? '▼' : '▶'} How we found these sources
              </button>
              {showMethodology && (
                <div className="methodology-notes">
                  <p>{results.methodology_notes}</p>
                </div>
              )}
            </div>
          )}

          {results.sources.length === 0 ? (
            <p className="no-results">No validated sources found. Try a different topic or spelling.</p>
          ) : (
            <div className="sources-container">
              {categoryOrder.map(category => {
                const sources = groupedSources?.[category]
                if (!sources || sources.length === 0) return null

                return (
                  <div key={category} className="category-section">
                    <h4 className="category-title">
                      {category}
                      <span className="category-count">({sources.length})</span>
                    </h4>
                    
                    {sources.map((source, idx) => (
                      <div key={idx} className={`source-card ${source.citation_count >= 99 ? 'primary-source' : ''}`}>
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
                          
                          {source.citation_count >= 99 && (
                            <span className="primary-badge">Primary Sugya</span>
                          )}
                          {source.citation_count > 1 && source.citation_count < 99 && (
                            <span className="citation-badge">
                              Cited {source.citation_count}x
                            </span>
                          )}
                          {source.validated && (
                            <span className="validated-badge" title="Verified via Sefaria API">✓</span>
                          )}
                        </div>
                        
                        {source.relevance && (
                          <p className="source-relevance">{source.relevance}</p>
                        )}
                        
                        {source.cited_by && source.cited_by.length > 0 && (
                          <p className="cited-by">
                            <strong>Cited by:</strong> {source.cited_by.slice(0, 3).join(', ')}
                            {source.cited_by.length > 3 && ` +${source.cited_by.length - 3} more`}
                          </p>
                        )}
                        
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
                      </div>
                    ))}
                  </div>
                )
              })}
            </div>
          )}

          <div className="results-footer">
            <p className="source-count">
              ✓ {results.sources.length} validated sources returned
            </p>
          </div>
        </div>
      )}
      
      <footer className="footer">
        <p>Sugya Archaeology + VGR Protocol - discovering sources through citation networks</p>
      </footer>
    </div>
  )
}

export default App
