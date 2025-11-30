import { useState } from 'react'
import './App.css'

function App() {
  const [topic, setTopic] = useState('')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState(null)
  const [clarification, setClarification] = useState(null)
  const [userClarification, setUserClarification] = useState('')
  const [error, setError] = useState('')
  const [searchScope, setSearchScope] = useState('standard')
  const [showMethodology, setShowMethodology] = useState(false)

  const handleSearch = async (e, withClarification = '') => {
    e.preventDefault()
    if (!topic.trim()) return

    setLoading(true)
    setError('')
    setResults(null)
    setClarification(null)

    try {
      const body = { 
        topic,
        scope: searchScope
      }
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
      
      if (data.needs_clarification && data.clarifying_questions?.length > 0) {
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

  const handleFeedback = async (isGood) => {
    if (!results) return
    
    try {
      await fetch('http://localhost:8000/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: results.topic,
          good_sources: isGood ? results.sources.map(s => s.ref) : [],
          bad_sources: !isGood ? results.sources.map(s => s.ref) : [],
          notes: ""
        })
      })
      alert(isGood ? 'Thanks! These sources will help future searches.' : 'Thanks for the feedback!')
    } catch (err) {
      console.error('Feedback error:', err)
    }
  }

  // Group sources by layer
  const sourcesByLayer = results?.sources?.reduce((acc, source) => {
    const layer = source.layer || source.category || 'Other'
    if (!acc[layer]) {
      acc[layer] = []
    }
    acc[layer].push(source)
    return acc
  }, {})

  // Define layer order (Chumash to Acharonim)
  const layerOrder = [
    'Chumash', 'Nach', 'Mishna', 'Gemara', 
    'Rishonim', 'Shulchan Aruch', 'Acharonim', 'Other'
  ]

  // Layer colors
  const layerColors = {
    'Chumash': '#8B4513',
    'Nach': '#6B8E23',
    'Mishna': '#4169E1',
    'Gemara': '#DC143C',
    'Rishonim': '#9932CC',
    'Shulchan Aruch': '#008B8B',
    'Acharonim': '#FF8C00',
    'Other': '#696969'
  }

  return (
    <div className="app">
      <header className="header">
        <h1>אור הנר</h1>
        <h2>Marei Mekomos Finder</h2>
        <p className="subtitle">Living Knowledge - From Chumash to Acharonim</p>
      </header>

      <form onSubmit={handleSearch} className="search-form">
        <div className="input-group">
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="Enter a topic (e.g., chuppas niddah, bitul chametz, safek sotah)"
            className="topic-input"
            dir="auto"
            disabled={loading}
          />
        </div>

        {/* Scope Selection */}
        <div className="scope-selector">
          <label>Search Depth:</label>
          <div className="scope-options">
            <button
              type="button"
              className={`scope-btn ${searchScope === 'focused' ? 'active' : ''}`}
              onClick={() => setSearchScope('focused')}
            >
              Focused
              <span className="scope-desc">Gemara + Key Rishonim</span>
            </button>
            <button
              type="button"
              className={`scope-btn ${searchScope === 'standard' ? 'active' : ''}`}
              onClick={() => setSearchScope('standard')}
            >
              Standard
              <span className="scope-desc">Gemara → Shulchan Aruch</span>
            </button>
            <button
              type="button"
              className={`scope-btn ${searchScope === 'comprehensive' ? 'active' : ''}`}
              onClick={() => setSearchScope('comprehensive')}
            >
              Comprehensive
              <span className="scope-desc">Chumash → Acharonim</span>
            </button>
          </div>
        </div>

        <button type="submit" disabled={loading || !topic.trim()}>
          {loading ? 'Searching All Layers...' : 'בודק'}
        </button>
      </form>

      {/* Quick Examples */}
      <div className="examples">
        <span>Try: </span>
        <button onClick={() => setTopic('chuppas niddah')}>chuppas niddah</button>
        <button onClick={() => setTopic('bitul chametz')}>bitul chametz</button>
        <button onClick={() => setTopic('kim lei bgavei')}>kim lei bgavei</button>
        <button onClick={() => setTopic('safek sotah')}>safek sotah</button>
      </div>

      {error && <div className="error">{error}</div>}

      {clarification && (
        <div className="clarification-box">
          <h3>🤝 Chavrusa Question...</h3>
          <p className="interpreted-as">
            I think you're asking about: <em>{clarification.interpreted_as}</em>
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
              placeholder="Tell me more about what you're looking for..."
              className="clarification-input"
              rows="3"
            />
            <div className="clarification-buttons">
              <button type="submit" disabled={!userClarification.trim()}>
                Continue Search
              </button>
              <button 
                type="button" 
                onClick={(e) => handleSearch(e, "Give me everything related")}
                className="secondary-button"
              >
                Just show me everything
              </button>
            </div>
          </form>
        </div>
      )}

      {results && (
        <div className="results">
          <div className="results-header">
            <h3>Sources for: {results.topic}</h3>
            
            {/* Metadata badges */}
            <div className="metadata">
              {results.query_intent && (
                <span className={`badge intent-${results.query_intent}`}>
                  {results.query_intent}
                </span>
              )}
              {results.search_scope && (
                <span className="badge scope">
                  {results.search_scope}
                </span>
              )}
              {results.layers_searched?.length > 0 && (
                <span className="badge layers">
                  {results.layers_searched.length} layers
                </span>
              )}
            </div>
          </div>
          
          {results.summary && (
            <p className="summary">{results.summary}</p>
          )}

          {/* Methodology toggle */}
          <div className="methodology-section">
            <button 
              className="methodology-toggle"
              onClick={() => setShowMethodology(!showMethodology)}
            >
              {showMethodology ? '▼' : '▶'} How we found these sources
            </button>
            {showMethodology && results.methodology_notes && (
              <p className="methodology-notes">{results.methodology_notes}</p>
            )}
          </div>

          {results.sources.length === 0 ? (
            <p>No sources found. Try a different topic or broader search scope.</p>
          ) : (
            <div className="sources-container">
              {layerOrder.map(layer => {
                const sources = sourcesByLayer?.[layer]
                if (!sources || sources.length === 0) return null

                return (
                  <div key={layer} className="layer-section">
                    <h4 
                      className="layer-title"
                      style={{ borderLeftColor: layerColors[layer] }}
                    >
                      <span 
                        className="layer-dot"
                        style={{ backgroundColor: layerColors[layer] }}
                      />
                      {layer}
                      <span className="layer-count">({sources.length})</span>
                    </h4>
                    
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
                          <span className="validated-badge" title="Validated against Sefaria">✓</span>
                        </div>
                        
                        {source.relevance && (
                          <p className="relevance">{source.relevance}</p>
                        )}
                        
                        {source.he_text && (
                          <div className="source-text he" dir="rtl">
                            {source.he_text.length > 500 
                              ? source.he_text.substring(0, 500) + '...' 
                              : source.he_text}
                          </div>
                        )}
                        
                        {source.en_text && (
                          <div className="source-text en">
                            {source.en_text.length > 400 
                              ? source.en_text.substring(0, 400) + '...' 
                              : source.en_text}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )
              })}
            </div>
          )}

          {/* Feedback */}
          <div className="feedback-section">
            <p>Were these sources helpful?</p>
            <button onClick={() => handleFeedback(true)} className="feedback-btn good">
              👍 Yes, great sources!
            </button>
            <button onClick={() => handleFeedback(false)} className="feedback-btn bad">
              👎 Not what I needed
            </button>
          </div>

          <p className="source-count">
            Found {results.sources.length} validated sources across {results.layers_searched?.length || 0} layers
          </p>
        </div>
      )}
    </div>
  )
}

export default App
