import { useState } from 'react'
import './App.css'

function App() {
  const [topic, setTopic] = useState('')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState(null)
  const [clarification, setClarification] = useState(null)
  const [userClarification, setUserClarification] = useState('')
  const [error, setError] = useState('')

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

  return (
    <div className="app">
      <header className="header">
        <h1>אור הנר</h1>
        <h2>Marei Mekomos Finder</h2>
        <p>Enter any topic to find relevant מקומות</p>
      </header>

      <form onSubmit={handleSearch} className="search-form">
        <div className="input-group">
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="Enter a topic (e.g, bedikas chometz, ביטול חמץ, baal yiraeh baal yimatze derabanan)"
            className="topic-input"
            dir="auto"
            disabled={loading}
          />
        </div>

        <button type="submit" disabled={loading || !topic.trim()}>
          {loading ? 'Searching...' : 'בודק'}
        </button>
      </form>

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