import { useState } from 'react'
import './App.css'

function App() {
  const [topic, setTopic] = useState('')
  const [level, setLevel] = useState('intermediate')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState(null)
  const [error, setError] = useState('')

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!topic.trim()) return

    setLoading(true)
    setError('')
    setResults(null)

    try {
      const response = await fetch('http://localhost:8000/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ topic, level }),
      })

      if (!response.ok) {
        throw new Error('Failed to fetch sources')
      }

      const data = await response.json()
      setResults(data)
    } catch (err) {
      setError('Error connecting to server. Make sure the backend is running.')
      console.error(err)
    } finally {
      setLoading(false)
    }
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
        <h1>מראי מקומות</h1>
        <h2>Marei Mekomos Finder</h2>
        <p>Enter any Torah topic to find relevant sources</p>
      </header>

      <form onSubmit={handleSearch} className="search-form">
        <div className="input-group">
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="Enter a topic (e.g., כיבוד אב ואם, bedikas chometz, tefilla)"
            className="topic-input"
            dir="auto"
          />
        </div>

        <div className="level-group">
          <label>Level:</label>
          <select value={level} onChange={(e) => setLevel(e.target.value)}>
            <option value="beginner">Beginner - Basic sources</option>
            <option value="intermediate">Intermediate - Main sugyos & halacha</option>
            <option value="advanced">Advanced - Comprehensive</option>
          </select>
        </div>

        <button type="submit" disabled={loading || !topic.trim()}>
          {loading ? 'Searching...' : 'Find Sources'}
        </button>
      </form>

      {error && <div className="error">{error}</div>}

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
