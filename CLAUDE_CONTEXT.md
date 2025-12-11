# Marei Mekomos Backend - Context for Claude

## Project Overview
**Marei Mekomos** (מראה מקומות) - "Torah Source Finder"  
Converts transliteration queries → Hebrew → Organized Torah sources

**Example Flow:**
```
"chezkas haguf" → חזקת הגוף → [Gemara sources] → [Rishonim] → [Acharonim]
```

## Architecture: 3-Step Pipeline

### STEP 1: DECIPHER (Transliteration → Hebrew)
**File:** `step_one_decipher.py`

**Purpose:** Convert English transliteration to Hebrew WITHOUT using Claude or vector search

**Process:**
1. Check word dictionary (cache) - instant hit if previously learned
2. Normalize input (`lolam` → `leolam`) - typo tolerance
3. Detect prefixes (`shenagach` → `ש+נגח`)
4. Generate Hebrew variants in preference order (כתיב מלא first)
5. Validate against Sefaria corpus - **"first valid wins"** (not highest hits)
6. Store successful match in dictionary for future

**Key Features:**
- FREE (no API calls for cached words)
- Prefix-aware (handles ש, ב, ל, etc.)
- Self-learning dictionary
- Confidence scoring

### STEP 2: UNDERSTAND (Hebrew → Intent + Strategy)
**File:** `step_two_understand.py`

**Purpose:** Analyze what the user wants & create search strategy

**Process:**
1. **GATHER:** Query Sefaria to see where term appears
2. **ANALYZE:** Claude determines query type (concept/term/reference/person/etc.)
3. **DECIDE:** Build SearchStrategy with:
   - Query type classification
   - Fetch strategy (sugyot/term-based/reference/etc.)
   - Primary sources to search
   - Related sugyot if applicable

**Query Types:** 
- `SUGYA_CONCEPT` - concept in specific sugya (חזקת הגוף)
- `HALACHA_TERM` - halachic term (מיגו)
- `DAF_REFERENCE` - direct daf (כתובות ט)
- `MASECHTA` - just masechta name
- `PERSON` - tanna/amora
- `PASUK` - Torah verse
- `KLAL` - principle (אין אדם מקנה)
- `AMBIGUOUS/UNKNOWN` - needs clarification

**Philosophy:** "Think first, ask later" - make intelligent guess, user refines if wrong

### STEP 3: SEARCH (Strategy → Organized Sources)
**File:** `step_three_search.py`

**Purpose:** Fetch & organize sources in "trickle-up" order

**Trickle-Up Hierarchy:**
1. פסוק (Chumash)
2. משנה
3. גמרא
4. רש"י / תוספות
5. ראשונים (רמב"ם, רשב"א, ריטב"א, ר"ן)
6. טור / שולחן ערוך
7. נושאי כלים (ש"ך, ט"ז)
8. אחרונים (קצות, פני יהושע)

**Process:**
1. Fetch from Sefaria based on strategy
2. Classify each source by level
3. Sort within levels
4. Return organized results

## Core Files

### `api_server_v7.py` (FastAPI Entry Point)
**Endpoints:**
- `POST /search` - Full pipeline (Steps 1→2→3)
- `POST /decipher` - Step 1 only (validation UI)
- `POST /decipher/confirm` - User confirms transliteration
- `POST /decipher/reject` - User rejects transliteration
- `GET /health` - Health check

### `main_pipeline.py` (Orchestrator)
Main `search_sources(query)` function that chains Steps 1→2→3

### `models.py` (Type Definitions)
Pydantic models for type-safe data flow:
- `DecipherResult` - Step 1 output
- `SearchStrategy` - Step 2 output
- `MareiMekomosResult` - Final output
- `Source` - Individual Torah source
- Enums: `QueryType`, `ConfidenceLevel`, `SourceLevel`, `FetchStrategy`

### `config.py` (Settings)
Centralized configuration using Pydantic:
- API keys (Anthropic)
- Server settings
- File paths
- Claude model configuration
- Logging settings

### `logging_config.py` (Logging System)
Centralized logging configuration with:
- Rotating file handlers (10MB per file, 5 backups)
- Dual output (detailed file logs + simple console)
- UTF-8 encoding for Hebrew text
- Daily log files: `logs/marei_mekomos_YYYYMMDD.log`
- `setup_logging()` - Initialize logging system
- `get_logger(name)` - Get module-specific logger

### `user_validation.py` (User Interaction)
Handles ambiguous cases with user prompts:
- `CLARIFY` - Multiple valid interpretations
- `CHOOSE` - Select from options
- `UNKNOWN` - No match found

### Console Testing Tools

#### `console_step_one.py` (Step 1 Tester)
Interactive console for testing transliteration (Step 1):
- Live transliteration testing with variants
- Debug mode for pattern detection
- Prefix detection testing
- Rule analysis (which transliteration rules fired)
- **Commands:**
  - `<transliteration>` - Generate Hebrew variants
  - `debug <word>` - Detailed pattern detection
  - `prefix <word>` - Test prefix detection
  - `rules <word>` - See which rules fired
  - `q/quit` - Exit

#### `console_step_two.py` (Step 2 Tester)
Interactive console for testing query analysis (Step 2):
- Full analysis (Sefaria + Claude)
- Sefaria-only data gathering
- Mock mode (no Claude API calls)
- **Commands:**
  - `<hebrew>` - Full analysis (Sefaria + Claude)
  - `sefaria <hebrew>` - Just Sefaria data
  - `mock <hebrew>` - Test with mock strategy
  - `q/quit` - Exit
- **Features:**
  - Comprehensive logging of all operations
  - Pretty-printed results (strategy, Sefaria stats)
  - Error handling with stack traces

## Tools Directory

### `word_dictionary.py`
Self-learning cache that stores successful transliteration→Hebrew mappings.
Reduces API costs by caching known terms.

### `transliteration_map.py`
Core transliteration engine:
- Input normalization (typo handling)
- Prefix detection (ש, ב, ל, מ, ה, כ, ו)
- Variant generation (preference-ordered)
- Confidence scoring

### `sefaria_validator.py`
Validates Hebrew against Sefaria corpus:
- "First valid wins" logic
- Caches API responses
- Returns validation confidence

### `sefaria_client.py`
Wrapper for Sefaria API with caching and rate limiting

## Tech Stack
- **Backend:** Python 3.9+, FastAPI, Pydantic
- **AI:** Anthropic Claude (Sonnet 3.5)
- **Data:** Sefaria API (Jewish texts corpus)
- **Frontend:** React + Vite (minimal - just UI for backend)

## Key Design Principles

1. **Cost Efficiency:** 
   - Step 1 uses NO Claude (dictionary/validation only)
   - Aggressive caching throughout

2. **User Experience:**
   - No upfront interrogation - smart guesses first
   - Validation only when truly ambiguous
   - Results organized bottom-up (Gemara → Acharonim)

3. **Type Safety:**
   - Pydantic models everywhere
   - Runtime validation
   - Clear data contracts between steps

4. **Modularity:**
   - Each step is independent
   - Tools are reusable
   - Easy to test/modify individual components

## Current State
- ✅ 3-step pipeline working
- ✅ Dictionary learning functional
- ✅ Transliteration with prefix detection
- ✅ Sefaria integration with caching
- ✅ User validation flows
- ✅ FastAPI server with all endpoints
- ✅ Frontend UI (React)
- ✅ Comprehensive logging system (rotating file handlers, dual output)
- ✅ Console testing tools (Step 1 & Step 2)
- ✅ Cache system (Sefaria responses in `cache/sefaria_v2/`)

## Testing & Development Tools

### Interactive Console Testers
1. **Step 1 Tester** (`console_step_one.py`):
   - Test transliteration engine
   - Debug pattern detection
   - Analyze rule application
   - No API calls needed

2. **Step 2 Tester** (`console_step_two.py`):
   - Test query understanding
   - View Sefaria data
   - Mock Claude responses
   - Full logging integration

### Test Suite
Located in `backend/tests/`:
- `test_confirm_selection.py` - User selection validation
- `test_phrase_issue.py` - Multi-word phrase handling
- `test_step_one_focused.py` - Focused Step 1 tests
- `test_step_two.py` - Step 2 analysis tests

### Logging System
All logs written to `backend/logs/marei_mekomos_YYYYMMDD.log`:
- **DEBUG**: Detailed internals, data flow
- **INFO**: Key operations, successful completions
- **WARNING**: Non-critical issues
- **ERROR**: Function failures with stack traces
- **CRITICAL**: System-level failures

Console output shows INFO+ with simple formatting for readability.

## Development Notes
- Python 3.9+ required
- Uses `pydantic_settings` for config
- Async/await throughout
- Comprehensive logging with rotating file handlers
- Test suite in `backend/tests/`
- Interactive console testers for manual testing
- Cache directory structure:
  - `cache/sefaria_v2/` - Sefaria API response cache (JSON files)
  - `cache/claude/` - Claude API response cache
  - `data/word_dictionary.json` - Self-learning transliteration cache
- Embeddings stored in `backend/embeddings/` (numpy arrays)

## File Organization

```
backend/
├── Core Pipeline:
│   ├── api_server_v7.py          # FastAPI entry point
│   ├── main_pipeline.py          # Orchestrator (Steps 1→2→3)
│   ├── step_one_decipher.py      # Transliteration → Hebrew
│   ├── step_two_understand.py    # Hebrew → Intent + Strategy
│   └── step_three_search.py      # Strategy → Sources
│
├── Configuration:
│   ├── config.py                 # Settings (Pydantic)
│   ├── logging_config.py         # Logging setup
│   ├── models.py                 # Type definitions
│   └── user_validation.py        # User interaction handling
│
├── Testing Tools:
│   ├── console_step_one.py       # Interactive Step 1 tester
│   └── console_step_two.py       # Interactive Step 2 tester
│
├── tools/
│   ├── word_dictionary.py        # Self-learning cache
│   ├── transliteration_map.py    # Transliteration engine
│   ├── sefaria_validator.py      # Sefaria validation
│   ├── sefaria_client.py         # Sefaria API wrapper
│   └── clean_dictionary.py       # Maintenance utility
│
├── tests/                        # Automated test suite
├── data/                         # Runtime learning cache
├── cache/                        # API response caching
├── embeddings/                   # Vector embeddings
└── logs/                         # Daily rotating logs
```

---
**For discussions about:** architecture changes, new features, optimizations, debugging, or planning