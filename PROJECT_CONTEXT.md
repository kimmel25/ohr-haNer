# Ohr HaNer (Marei Mekomos) - Project Context

**Version:** 8.1  
**Type:** Torah Research Assistant  
**Stack:** Python (FastAPI) + React (Vite) + Claude AI + Sefaria API  
**Purpose:** Convert transliterated/Hebrew Torah queries into organized source compilations

---

## 🎯 Project Mission

Transform natural language Torah queries (transliterated Hebrew, English, or mixed) into comprehensive, hierarchically-organized source compilations. The system intelligently discovers where topics are discussed across gemara, rishonim, and acharonim, presenting results in "trickle-up" order (base texts → commentaries).

**Core Philosophy:**
- "Getting into the user's head is most important"
- Better to ask for clarification than guess wrong
- Sources should flow naturally from gemara → rishonim → acharonim

---

## 🏗️ Architecture Overview

### Three-Step Pipeline

```
USER QUERY → [STEP 1: DECIPHER] → [STEP 2: UNDERSTAND] → [STEP 3: SEARCH] → ORGANIZED SOURCES
```

#### STEP 1: DECIPHER (`step_one_decipher.py`)
**Input:** User query (any format)  
**Output:** Hebrew terms + confidence level  
**Method:** Dictionary-first, then rule-based transliteration with Sefaria validation

**Process:**
1. Extract potential Hebrew/transliterated terms
2. Check word dictionary (`data/word_dictionary.json`)
3. Generate variants using transliteration rules (`tools/transliteration_map.py`)
4. Validate against Sefaria corpus (`tools/sefaria_validator.py`)
5. Return `DecipherResult` with confidence (HIGH/MEDIUM/LOW/CLARIFY/CHOOSE/UNKNOWN)

**Key Features:**
- Mixed query handling (detects English markers)
- Author name special handling (via `torah_authors_master.py`)
- Smichut, sofit letters, Aramaic endings support
- Batch validation for efficiency

#### STEP 2: UNDERSTAND (`step_two_understand.py`)
**Input:** Hebrew terms + original query  
**Output:** `QueryAnalysis` search plan  
**Method:** Claude AI semantic analysis

**Process:**
1. Pre-split terms into TOPICS vs. AUTHORS using KB
2. Send to Claude with system prompt defining search strategy
3. Claude returns JSON with:
   - **WHAT** to search: `search_topics` (the INYAN, not author names)
   - **WHERE** to look: `target_masechtos`, `target_dapim`, `target_simanim`
   - **WHOSE** commentary: `target_authors` (Rashi, Tosafos, Ran, etc.)
   - **HOW** to search: `search_method` (trickle_up/trickle_down/hybrid/direct)

**Query Types:**
- `topic` - General conceptual inquiry
- `question` - Specific halachic/conceptual question  
- `comparison` - Compare multiple shittos
- `shittah` - One author's view on topic
- `machlokes` - Dispute/disagreement
- `sugya` - Full sugya exploration
- `pasuk` - Biblical verse request
- `halacha` - Halachic lookup

**Search Methods (V6+ Logic):**
- **trickle_down**: Search ACHRONIM first to discover relevant dapim, then fetch rishonim
  - Use for: comparisons, shittah questions, complex conceptual queries
  - Why: Achronim synthesize and act as "semantic indices" to relevant sugyos
- **trickle_up**: Start from base sources (gemara), then get commentaries
  - Use for: simple lookups, known locations, direct references
- **hybrid**: Both methods, find overlap
- **direct**: Go straight to specific reference

#### STEP 3: SEARCH (`step_three_search.py`)
**Input:** `QueryAnalysis` from Step 2  
**Output:** `SearchResult` with organized sources  
**Method:** V8.1 Smart Multi-Topic with Intersection Logic

**V8.1 Algorithm (Trickle-Down):**

```
PHASE A: LOCATE
- Search local corpus (Shulchan Aruch + Tur + Rambam) for topic
- Filter out verbose topics (>3 words) to avoid AND-logic failures
- Use only first 2 core topics for combined search

PHASE B: TRICKLE DOWN
- Extract gemara citations from nosei keilim (Mishnah Berurah, Beis Yosef, etc.)
- Count citation frequency per daf

PHASE C: CROSS-REFERENCE (V8.1 Intersection Logic)
- Try combined search with first 2 topics joined
- If no results: Search each topic individually
- Use INTERSECTION: only dapim in BOTH topic searches
- Fallback: Union with 3x bonus for dapim in both
- Identify top 10 main sugyos by citation count

PHASE D: FETCH TARGET AUTHORS
- For each main sugya, fetch:
  1. Gemara text
  2. Requested commentaries (Rashi, Tosafos, rishonim, etc.)
- Return organized by source level
```

**Why V8.1 Intersection Logic?**
- V8 joined ALL topics into one string → AND-logic required ALL words → found nothing
- Example bug: "חזקת ממון חזקת הגוף הבדל בין חזקת ממון לחזקת הגוף" (12 words)
- Fallback used UNION → Choshen Mishpat simanim dominated → wrong masechta
- V8.1: Filter verbose, use first 2 core concepts, find dapim in BOTH searches

---

## 📁 Repository Structure

```
marei-mekomos/
├── backend/
│   ├── step_one_decipher.py      # Step 1: Transliteration → Hebrew
│   ├── step_two_understand.py    # Step 2: Claude query analysis
│   ├── step_three_search.py      # Step 3: V8.1 trickle-down search
│   ├── main_pipeline.py          # Orchestrates 3-step flow
│   ├── console_full_pipeline.py  # Interactive CLI tester
│   ├── api_server_v7.py          # FastAPI REST server
│   ├── local_corpus.py           # V10 Sefaria JSON corpus handler
│   ├── config.py                 # Pydantic settings (env vars)
│   ├── models.py                 # Data models (Pydantic)
│   ├── smart_gather.py           # Intelligent source gathering
│   ├── source_output.py          # Output formatting (TXT/HTML)
│   ├── commentary_fetcher.py     # Fetch commentaries from Sefaria
│   ├── user_validation.py        # User interaction prompts
│   ├── logging_config.py         # Logging setup
│   ├── logging_async_safe.py     # Async-safe logging
│   ├── cache/                    # API response cache
│   │   ├── sefaria_v2/          # Sefaria API cache (JSON)
│   │   └── claude/              # Claude API cache
│   ├── data/
│   │   ├── word_dictionary.json # Known Hebrew terms
│   │   └── peirushim.py         # Commentary metadata
│   ├── embeddings/              # Vector embeddings (future)
│   │   ├── embeddings.npy
│   │   └── metadata.json
│   ├── logs/                    # Application logs
│   ├── tools/
│   │   ├── sefaria_client.py         # Sefaria API wrapper
│   │   ├── sefaria_validator.py      # Validate Hebrew against Sefaria
│   │   ├── torah_authors_master.py   # Author name KB (600+ entries)
│   │   ├── transliteration_map.py    # Hebrew ↔ transliteration rules
│   │   └── word_dictionary.py        # Dictionary management
│   ├── utils/
│   │   ├── fallbacks.py         # Fallback strategies
│   │   ├── levels.py            # Source level utilities
│   │   └── serialization.py     # JSON serialization helpers
│   └── tests/
│       ├── test_step_one_focused.py
│       ├── test_step_two.py
│       ├── test_phrase_issue.py
│       ├── test_master_kb_integration.py
│       └── test_confirm_selection.py
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Main React app
│   │   ├── main.jsx             # Entry point
│   │   └── components/
│   │       ├── ErrorBox.jsx     # Error display
│   │       └── ...
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── output/                      # Generated source compilations
│   ├── sources_*.html          # HTML formatted results
│   └── sources_*.txt           # Plain text results
├── README.md                    # Main documentation
├── CLAUDE_CONTEXT.md           # Claude API context
└── PROJECT_CONTEXT.md          # This file
```

---

## 🔧 Technology Stack

### Backend
- **Python 3.9+**
- **FastAPI** - REST API framework
- **Anthropic Claude** - Query analysis (Step 2)
- **Pydantic** - Data validation and settings
- **asyncio** - Async operations
- **aiohttp** - Async HTTP client

### External APIs
- **Sefaria API** - Torah text corpus
  - Text retrieval
  - Search
  - Related texts/commentaries
  - Validation

### Frontend
- **React 18**
- **Vite** - Build tool
- **JSX** - Component rendering

### Data Storage
- **JSON files** - Caching, dictionaries, corpus
- **NumPy** - Embeddings (future vector search)

---

## 🗄️ Key Data Structures

### DecipherResult (Step 1 Output)
```python
@dataclass
class DecipherResult:
    hebrew_term: str                    # Main Hebrew term
    hebrew_terms: List[str]             # All Hebrew terms found
    english_remainder: str              # Non-Hebrew parts
    confidence: ConfidenceLevel         # HIGH/MEDIUM/LOW/CLARIFY/CHOOSE/UNKNOWN
    validation_status: ValidationStatus # PERFECT_MATCH/GOOD_MATCH/etc.
    requires_clarification: bool
    clarification_options: List[str]
    original_query: str
```

### QueryAnalysis (Step 2 Output)
```python
@dataclass
class QueryAnalysis:
    original_query: str
    hebrew_terms_from_step1: List[str]
    
    query_type: QueryType               # topic/question/comparison/shittah/etc.
    realm: Realm                        # gemara/mishnah/halacha/chumash/etc.
    breadth: Breadth                    # narrow/standard/wide/exhaustive
    search_method: SearchMethod         # trickle_up/trickle_down/hybrid/direct
    
    search_topics: List[str]            # WHAT to search (English)
    search_topics_hebrew: List[str]     # WHAT to search (Hebrew)
    
    target_masechtos: List[str]         # WHERE: masechtos
    target_perakim: List[str]           # WHERE: perakim (for Mishnah/Chumash)
    target_dapim: List[str]             # WHERE: specific dapim
    target_simanim: List[str]           # WHERE: simanim (SA/Tur)
    target_sefarim: List[str]           # WHERE: other sefarim
    target_refs: List[str]              # WHERE: specific refs
    target_authors: List[str]           # WHOSE: which meforshim to fetch
    
    source_categories: SourceCategories # Which categories to include
    
    confidence: ConfidenceLevel
    needs_clarification: bool
    clarification_question: Optional[str]
    reasoning: str                      # Claude's reasoning
    search_description: str             # Human-readable description
```

### SearchResult (Step 3 Output)
```python
@dataclass
class SearchResult:
    original_query: str
    search_topics: List[str]
    
    sources: List[Source]                       # All sources
    sources_by_level: Dict[str, List[Source]]   # Grouped by level
    
    discovery: Optional[DiscoveryResult]        # Trickle-down discovery
    discovered_dapim: List[str]                 # Main sugyos found
    
    total_sources: int
    levels_found: List[str]
    search_description: str
    confidence: ConfidenceLevel
```

### Source
```python
@dataclass
class Source:
    ref: str                    # English ref (e.g., "Ketubot 2b")
    he_ref: str                 # Hebrew ref
    level: SourceLevel          # GEMARA/RASHI/TOSFOS/RISHONIM/etc.
    hebrew_text: str
    english_text: str
    author: str                 # Commentary author
    categories: List[str]       # Sefaria categories
    relevance_description: str  # Why this source is relevant
    is_primary: bool            # Primary vs. supporting source
    citation_count: int         # How many times cited (trickle-down)
```

---

## 🔑 Key Components

### Local Corpus (`local_corpus.py`) - V10

Handles Sefaria JSON export files for offline searching.

**V10 Features:**
- Fixed siman extraction (skip non-digit keys)
- Tur nosei keilim (Beis Yosef, Bach, Darchei Moshe)
- Rambam nosei keilim (Maggid Mishneh, Kesef Mishneh, etc.)
- SA + Tur + Rambam citation extraction
- Rishonim fallback for gemara searches

**Key Functions:**
- `get_local_corpus(root_path)` - Initialize corpus
- `discover_main_sugyos(corpus, query, masechta)` - Find sugyos via citations
- `search_shulchan_aruch(corpus, query)` - Search SA
- `search_tur(corpus, query)` - Search Tur
- `search_rambam(corpus, query)` - Search Rambam
- `extract_gemara_citations(text)` - Parse gemara refs from text

### Torah Authors KB (`torah_authors_master.py`)

600+ entry knowledge base of Torah authors/commentaries.

**Functions:**
- `is_author(term)` - Check if term is author name
- `get_author_matches(term)` - Get matching author records
- `normalize_author_name(term)` - Normalize variations

**Author Categories:**
- Tannaim/Amoraim
- Geonim
- Rishonim (Rashi, Tosafos, Rambam, etc.)
- Acharonim (Maharsha, Pnei Yehoshua, etc.)
- Contemporary (Chazon Ish, R' Akiva Eiger, etc.)

### Sefaria Client (`tools/sefaria_client.py`)

Async wrapper for Sefaria API with caching.

**Key Methods:**
- `get_text(ref)` - Fetch text for reference
- `get_related(ref)` - Get commentaries/connections
- `search(query, filters)` - Search Sefaria corpus
- `validate_ref(ref)` - Check if ref exists

**Features:**
- JSON file caching (hash-based)
- Rate limiting
- Retry logic
- Batch requests

### Transliteration Map (`tools/transliteration_map.py`)

Rule-based Hebrew ↔ transliteration engine.

**Features:**
- Prefix detection (ha-, ve-, she-, mi-, etc.)
- Smichut forms
- Sofit letter handling (ם/מ, ן/נ, ך/כ, ף/פ, ץ/צ)
- Aramaic endings (-ta, -sa)
- Multiple consonant mappings (kh/ch for כ/ח)
- Vowel variations

**Functions:**
- `hebrew_to_transliteration(hebrew)` - Generate variants
- `transliteration_to_hebrew(trans)` - Generate Hebrew forms
- `normalize_input(text)` - Clean input

---

## 🚀 Quick Start

### Environment Setup

1. **Create `.env` file:**
```bash
ANTHROPIC_API_KEY=sk-ant-...
SEFARIA_BASE_URL=https://www.sefaria.org/api
ENVIRONMENT=development
LOG_LEVEL=INFO
```

2. **Install dependencies:**
```bash
cd backend
pip install -r requirements.txt
```

3. **Initialize caching:**
```bash
mkdir -p cache/sefaria_v2 cache/claude
mkdir -p logs output
```

### Running the System

#### Option 1: Interactive Console
```bash
python backend/console_full_pipeline.py
```

Commands:
- Type any query to search
- `mode` - Choose which steps to run
- `q` or `quit` - Exit

#### Option 2: API Server
```bash
python backend/api_server_v7.py
```

Endpoints:
- `POST /decipher` - Step 1 only
- `POST /understand` - Step 2 only  
- `POST /search` - Step 3 only
- `POST /marei-mekomos` - Full pipeline

#### Option 3: Frontend + Backend
```bash
# Terminal 1: Backend
python backend/api_server_v7.py

# Terminal 2: Frontend
cd frontend
npm install
npm run dev
```

Access: http://localhost:5173

---

## 📊 Example Queries

### 1. Simple Topic (Trickle-Up)
```
Input: "migu"
Step 1: hebrew_term = "מיגו"
Step 2: query_type = "topic", search_method = "trickle_up"
Step 3: Search gemara for "מיגו", fetch Rashi/Tosafos
Output: Gemara → Rishonim → Acharonim
```

### 2. Comparison Query (Trickle-Down)
```
Input: "what is the rans shittah in bittul chometz and how is it different than rashis"
Step 1: hebrew_terms = ["רן", "ביטול חמץ", 'רש"י']
Step 2: 
  - query_type = "comparison"
  - search_method = "trickle_down" (V6+ forced for comparisons)
  - search_topics = ["ביטול חמץ"] (NOT "רן" - that's an author)
  - target_authors = ["Ran", "Rashi"]
  - target_masechtos = ["Pesachim"]
Step 3:
  - Search Mishnah Berurah for "ביטול חמץ"
  - Extract gemara citations → Pesachim 4b, 6b, 21a
  - Fetch Ran + Rashi on those dapim
  - Return organized sources
```

### 3. Specific Location (Direct)
```
Input: "show me rashi on pesachim 4b"
Step 1: hebrew_terms = ['רש"י', "פסחים"]
Step 2: 
  - query_type = "source_request"
  - search_method = "direct"
  - target_masechtos = ["Pesachim"]
  - target_dapim = ["4b"]
  - target_authors = ["Rashi"]
Step 3: Directly fetch Rashi on Pesachim 4b
```

### 4. Halacha Query
```
Input: "where does the mechaber discuss carrying on shabbos"
Step 1: hebrew_terms = ["מחבר", "טלטול", "שבת"]
Step 2:
  - query_type = "halacha"
  - realm = "halacha"
  - search_topics = ["carrying on shabbos", "טלטול בשבת"]
  - target_sefarim = ["Shulchan Aruch Orach Chaim"]
  - target_simanim = ["301-350"]
  - target_authors = ["Mechaber"]
Step 3: Search SA OC simanim 301-350 for "טלטול"
```

---

## 🐛 Common Issues & Debugging

### Issue: "No Hebrew terms found"
**Cause:** Step 1 couldn't decipher transliteration  
**Debug:**
1. Check if term is in `data/word_dictionary.json`
2. Check transliteration variants generated
3. Check Sefaria validation results
4. Look at logs: `logs/marei_mekomos_YYYYMMDD.log`

### Issue: "Wrong masechta returned"
**Cause:** V8.1 intersection logic failing or verbose topics  
**Debug:**
1. Check Step 2 `search_topics_hebrew` - are they too verbose (>3 words)?
2. Check if combined search returned results
3. Check intersection vs. union in Phase C
4. Look for "INTERSECTION: X dapim" in logs

### Issue: "Claude returned wrong search method"
**Cause:** Query type not properly detected  
**Debug:**
1. Check Step 2 `query_type` classification
2. For comparisons/shittah/machlokes, should force `trickle_down` (V6+)
3. Check Claude's `reasoning` field
4. Review system prompt in `step_two_understand.py`

### Issue: "No sources found"
**Cause:** Local corpus missing or search too narrow  
**Debug:**
1. Check if `C:/Projects/Sefaria-Export/json` exists
2. Check `LOCAL_CORPUS_AVAILABLE` flag
3. Check discovered_dapim in SearchResult
4. Try API fallback search
5. Check citation extraction from nosei keilim

---

## 📝 Logging Strategy

### Log Levels
- **DEBUG** - Detailed execution flow, API responses
- **INFO** - Step boundaries, major decisions, results
- **WARNING** - Fallbacks, missing data, recoverable errors
- **ERROR** - Failures requiring attention

### Log Locations
- **File:** `logs/marei_mekomos_YYYYMMDD.log` (DEBUG level)
- **Console:** INFO level only

### Key Log Patterns

**Step 1:**
```
[STEP 1: DECIPHER] Processing query: "migu"
  Found dictionary match: "מיגו"
  Confidence: HIGH
  Validation: PERFECT_MATCH
```

**Step 2:**
```
[STEP 2: UNDERSTAND] Analyzing query
  Query: what is the rans shittah in bittul chometz
  Hebrew terms: ['רן', 'ביטול חמץ']
[UNDERSTAND] Claude raw response: {...}
[UNDERSTAND] Final QueryAnalysis:
  INYAN: ['ביטול חמץ']
  WHERE: ['Pesachim']
  WHOSE: ['Ran', 'Rashi', 'Tosafos']
  METHOD: trickle_down
```

**Step 3:**
```
[STEP 3: SEARCH] V8.1 Trickle-Down
  All topics from Claude: ['ביטול חמץ', 'חיוב ביטול']
  Core topics (filtered): ['ביטול חמץ', 'חיוב ביטול']
  Combined search query: 'ביטול חמץ חיוב ביטול'
PHASE A/B/C: Discovering main sugyos
  Topic 1 dapim: 15
  Topic 2 dapim: 8
  INTERSECTION: 3 dapim
  Using INTERSECTION - dapim discussing BOTH topics:
    - Pesachim 4b
    - Pesachim 6b
    - Pesachim 21a
PHASE D: Fetching target authors
  Fetching sources for: Pesachim 4b
    Found 3 commentaries
STEP 3 COMPLETE: 12 sources found
```

---

## 🔮 Future Enhancements

### Planned Features
1. **Vector Search** - Semantic search using embeddings
2. **Multi-Language UI** - Hebrew interface
3. **Citation Graph** - Visualize source relationships
4. **User Accounts** - Save searches, build libraries
5. **Export Options** - PDF, DOCX, Markdown
6. **Advanced Filters** - By time period, author type, topic
7. **Machine Learning** - Improve transliteration with usage data

### Performance Optimizations
1. **Parallel Fetching** - Fetch multiple sources concurrently
2. **Smart Caching** - Predictive cache warming
3. **Incremental Results** - Stream sources as found
4. **Index Optimization** - Pre-index common queries

---

## 🤝 Contributing

### Code Style
- Follow PEP 8
- Use type hints
- Document complex logic
- Add tests for new features

### Testing
```bash
# Run specific test
python -m pytest backend/tests/test_step_one_focused.py

# Run all tests
python -m pytest backend/tests/

# With coverage
python -m pytest --cov=backend backend/tests/
```

### Adding New Features

**New Step in Pipeline:**
1. Create `step_X_name.py` in `backend/`
2. Define input/output dataclasses in `models.py`
3. Update `main_pipeline.py` orchestration
4. Add to `console_full_pipeline.py` for testing
5. Add API endpoint in `api_server_v7.py`

**New Commentary Source:**
1. Add to `torah_authors_master.py` KB
2. Update `source_categories` in `step_two_understand.py`
3. Add level to `SourceLevel` enum
4. Update fetching logic in `step_three_search.py`

---

## 📚 References

### External APIs
- [Sefaria API Documentation](https://developers.sefaria.org/)
- [Anthropic Claude API](https://docs.anthropic.com/)

### Torah Resources
- [Sefaria.org](https://www.sefaria.org/) - Primary text source
- [HebrewBooks.org](https://hebrewbooks.org/) - Additional texts
- [Wikisource Hebrew](https://he.wikisource.org/) - Open texts

### Technical Documentation
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Pydantic Docs](https://docs.pydantic.dev/)
- [React Docs](https://react.dev/)

---

## 📄 License

[Add your license here]

---

## 👥 Contact

[Add contact information]

---

**Last Updated:** December 25, 2025  
**Version:** 8.1  
**Maintained by:** [Your name/team]
