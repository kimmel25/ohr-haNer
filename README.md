# Marei Mekomos V7 - Torah Source Finder

**אור הנר** - Intelligent Hebrew transliteration and Torah source discovery

## 📚 What This Does

Converts your transliteration queries (like "chezkas haguf") into Hebrew and finds relevant Torah sources across Gemara, Rishonim, and Acharonim.

**Example:**
```
Input: "migu lehotzi mamon"
↓ Step 1: DECIPHER → מיגו להוצי ממון
↓ Step 2: UNDERSTAND → "Legal concept: using one claim to support another"
↓ Step 3: SEARCH → Organized sources from Gemara → Rishonim → Acharonim
```

## 🏗️ Architecture (3-Step Pipeline)

```
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: DECIPHER (Transliteration → Hebrew)                │
│  • Dictionary lookup (instant cache)                        │
│  • Transliteration map (prefix detection, variants)         │
│  • Sefaria validation ("first valid wins")                  │
│  ✓ NO Claude, NO vector search                              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: UNDERSTAND (Hebrew → Intent + Strategy)            │
│  • Claude analyzes the term's meaning                       │
│  • Determines query type (concept, reference, etc.)         │
│  • Generates search strategy                                │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 3: SEARCH (Strategy → Organized Sources)              │
│  • Fetches from Sefaria based on strategy                   │
│  • Organizes by level (Gemara → Rishonim → Acharonim)       │
│  • Returns trickle-up presentation                          │
└─────────────────────────────────────────────────────────────┘
```

## 📂 Project Structure

```
marei-mekomos/
├── backend/
│   ├── api_server_v7.py           # FastAPI server (entry point)
│   ├── main_pipeline.py           # Orchestrates Steps 1→2→3
│   │
│   ├── step_one_decipher.py       # Transliteration → Hebrew
│   ├── step_two_understand.py     # Hebrew → Intent + Strategy
│   ├── step_three_search.py       # Strategy → Sources
│   │
│   ├── user_validation.py         # CLARIFY/CHOOSE/UNKNOWN prompts
│   ├── logging_config.py          # Centralized logging
│   │
│   ├── tools/
│   │   ├── word_dictionary.py     # Self-learning cache
│   │   ├── transliteration_map.py # Core transliteration engine
│   │   ├── sefaria_validator.py   # Validates against Sefaria corpus
│   │   ├── sefaria_client.py      # Sefaria API wrapper
│   │   └── clean_dictionary.py    # Maintenance utility
│   │
│   ├── tests/
│   │   ├── test_confirm_selection.py
│   │   ├── test_phrase_issue.py
│   │   └── test_step_one_focused.py
│   │
│   ├── data/
│   │   └── word_dictionary.json   # Runtime learning cache
│   │
│   ├── requirements.txt           # Python dependencies
│   └── .env.example               # API key template
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx                # Main application
│   │   └── components/
│   │       ├── SearchForm.jsx     # User input
│   │       ├── SearchResults.jsx  # Display results
│   │       ├── ValidationBox.jsx  # User validation UI
│   │       ├── ResultBox.jsx      # Individual sources
│   │       ├── ErrorBox.jsx       # Error handling
│   │       ├── FeedbackBox.jsx    # User feedback
│   │       └── Header.jsx         # UI header
│   │
│   ├── package.json               # Node dependencies
│   └── vite.config.js             # Build configuration
│
└── README.md                      # This file
```

## 🚀 Quick Start

### Backend Setup

1. **Install Python dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Configure API key:**
   ```bash
   cp .env.example .env
   # Edit .env and add your ANTHROPIC_API_KEY
   ```

3. **Run the server:**
   ```bash
   python api_server_v7.py
   ```
   Server runs on http://localhost:8000

### Frontend Setup

1. **Install Node dependencies:**
   ```bash
   cd frontend
   npm install
   ```

2. **Run development server:**
   ```bash
   npm run dev
   ```
   Frontend runs on http://localhost:5173

## 🔧 API Endpoints

### Full Search Pipeline
```
POST /search
Body: {"query": "migu", "depth": "standard"}
→ Returns: Complete pipeline result with organized sources
```

### Step 1 Only (Transliteration)
```
POST /decipher
Body: {"query": "chezkas haguf", "strict": false}
→ Returns: Hebrew term + validation info
```

### User Validation
```
POST /decipher/confirm
Body: {"original_query": "...", "selection_index": 1}
→ Confirms user's selection, learns for future

POST /decipher/reject
Body: {"original_query": "...", "incorrect_hebrew": "..."}
→ Gets alternative suggestions
```

### Source Fetching
```
GET /sources/{ref}
→ Returns full text for a Sefaria reference

GET /related/{ref}
→ Returns commentaries and cross-references
```

## 🧪 Testing

```bash
cd backend

# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_step_one_focused.py

# Run with verbose output
pytest -v tests/
```

## 📝 Development Notes

### Key Design Decisions

1. **Dictionary-First Approach**: Step 1 checks dictionary before transliteration to maximize speed and accuracy

2. **No Vector Search**: V7 removed hybrid vector search due to complexity. Pure dictionary + transliteration + Sefaria validation is faster and more reliable.

3. **Word Validation**: `user_validation.py` provides CLARIFY/CHOOSE/UNKNOWN prompts when uncertain, following the principle "better annoy with asking than getting it wrong"

4. **Self-Learning Dictionary**: Every confirmed transliteration is added to `word_dictionary.json` for future instant lookups

5. **Trickle-Up Presentation**: Sources organized Gemara → Rishonim → Acharonim for pedagogical clarity

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-...     # Claude API key

# Optional
USE_CACHE=true               # Enable caching (default: true)
TEST_MODE=true               # Testing mode for test suite
```

## 🐛 Troubleshooting

### Backend won't start
- Check `ANTHROPIC_API_KEY` is set in `.env`
- Verify all dependencies: `pip install -r requirements.txt`
- Check port 8000 is available

### Frontend can't connect to backend
- Verify backend is running on http://localhost:8000
- Check CORS settings in `api_server_v7.py`
- Try clearing browser cache

### Transliteration not working
- Check Sefaria API is accessible
- Review logs in `backend/logs/`
- Test Step 1 directly: `POST /decipher`

### Tests failing
- Ensure `TEST_MODE=true` in environment
- Check test data in `word_dictionary.json`
- Run individual tests: `pytest tests/test_step_one_focused.py -v`

## 📊 Code Statistics

- **Backend**: ~3,500 lines (7 core files + 5 tools)
- **Frontend**: ~350 lines (9 components)
- **Tests**: 3 test files
- **Total Active Code**: ~4,000 lines

## 🔄 Recent Cleanup (2025-12-08)

Removed dead code and improved organization:
- ✅ Deleted `hybrid_resolver.py` (348 lines, unused)
- ✅ Deleted `vector_search.py` (267 lines, unused)
- ✅ Deleted `cache_manager.py` (111 lines, unused)
- ✅ Removed legacy `resources/` directory
- ✅ Organized test files into `backend/tests/`
- ✅ Updated `.gitignore` for node_modules, cache, embeddings
- ✅ Added `requirements.txt` for Python dependencies

**Saved:** ~730 lines of dead code removed

---

**Built with:** Python (FastAPI), React (Vite), Claude API, Sefaria API
