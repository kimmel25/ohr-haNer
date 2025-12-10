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

### `user_validation.py` (User Interaction)
Handles ambiguous cases with user prompts:
- `CLARIFY` - Multiple valid interpretations
- `CHOOSE` - Select from options
- `UNKNOWN` - No match found

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

## Development Notes
- Python 3.9+ required
- Uses `pydantic_settings` for config
- Async/await throughout
- Comprehensive logging
- Test suite in `backend/tests/`

---
**For discussions about:** architecture changes, new features, optimizations, debugging, or planning