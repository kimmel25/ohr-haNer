# Marei Mekomos V7 - Torah Source Finder

Marei Mekomos turns transliterated Hebrew (and mixed English) into organized Torah sources. The backend runs a 3-step pipeline:

1. DECIPHER: transliteration -> Hebrew (dictionary + rules + Sefaria validation)
2. UNDERSTAND: Hebrew -> query intent + search plan (Gemini)
3. SEARCH: search plan -> organized sources (local corpus + Sefaria)

The system is optimized for speed, cost control, and clear "trickle-up" presentation (Gemara -> Rishonim -> Acharonim).

## Table of Contents
- Overview
- Architecture (3-step pipeline)
- Repository Layout
- Quick Start
- Configuration
- API Reference
- Frontend Notes
- Local Corpus Setup
- Caching and Output Files
- CLI Tools
- Testing
- Troubleshooting
- Design Notes

## Overview
- Inputs: transliteration, Hebrew, or mixed English (examples: "migu", "chezkas haguf", "what is migu")
- Outputs: sources grouped by level, query analysis metadata, and optional clarification prompts
- Backend: FastAPI + Gemini + Sefaria API
- Frontend: React + Vite UI for Step 1 validation and Step 2/3 results

Example (abbreviated):
Input: "migu lehotzi mamon"
Step 1 -> hebrew_term + confidence
Step 2 -> query_type=halacha_term, search_method=hybrid
Step 3 -> sources_by_level (gemara, rishonim, acharonim)

## Architecture (3-step pipeline)

### Step 1: DECIPHER (backend/step_one_decipher.py)
- Purpose: convert transliteration to Hebrew without using Gemini or vector search.
- Mixed query handling: detects English markers, extracts likely transliterated segments, and treats author names specially.
- Dictionary-first: checks backend/data/word_dictionary.json for an instant hit.
- Rules-based transliteration: backend/tools/transliteration_map.py generates variants using prefix detection, smichut, sofit letters, and Aramaic endings.
- Validation: backend/tools/sefaria_validator.py validates variants against the Sefaria corpus with author-aware scoring and batch requests.
- Output: DecipherResult (see API reference); may request user validation (CLARIFY/CHOOSE/UNKNOWN).

### Step 2: UNDERSTAND (backend/step_two_understand.py)
- Purpose: analyze intent and construct a QueryAnalysis that drives Step 3.
- Uses Google Gemini to classify the query and build a search plan.
- Key outputs: query_type, realm, search_method, search_topics, target_masechtos, target_authors, and clarification prompts.
- Search methods:
  - trickle_up: start from base texts and pull commentaries
  - trickle_down: start from later sources to locate sugyos, then backfill
  - hybrid: combine both
  - direct: user provides a specific ref
- Fallback: if Gemini fails, returns a conservative plan with a clarification prompt.

### Step 3: SEARCH (backend/step_three_search.py)
- Purpose: discover main sugyos and fetch sources.
- Phase A: local corpus discovery (optional). Uses backend/local_corpus.py to search a local Sefaria export (Shulchan Arukh, Tur, Rambam) and extract Gemara citations.
- Phase B: Gemini validation. Asks Gemini to confirm discovered sugyos or suggest better ones.
- Phase C: fetch sources from Sefaria via backend/tools/sefaria_client.py, then group by level.
- Fallback: if no sugyos found, falls back to a Sefaria search API query.
- Output: SearchResult plus output files (txt + html) via backend/source_output.py.
- Implementation note: Step 3 currently routes all queries through trickle_down_search_v9; the search_method value is still recorded in Step 2 but not used to switch algorithms.

Source levels used internally:
pasuk/chumash, targum, mishnah, tosefta, gemara_bavli, gemara_yerushalmi, midrash,
rashi, tosfos, rishonim, rambam, tur, shulchan_aruch, nosei_keilim, acharonim.

## Repository Layout

```
marei-mekomos/
  backend/
    api_server_v7.py          # FastAPI entry point
    main_pipeline.py          # Orchestrates Steps 1-3
    step_one_decipher.py      # Transliteration -> Hebrew
    step_two_understand.py    # Intent + strategy (Gemini)
    step_three_search.py      # Discovery + source fetching
    config.py                 # Settings (Pydantic)
    models.py                 # Pydantic API models
    local_corpus.py           # Optional local Sefaria export search
    source_output.py          # Writes txt/html/json output files
    commentary_fetcher.py     # Commentary discovery/fetch helpers
    smart_gather.py           # Optional Sefaria "smart gather" helpers
    logging_async_safe.py     # Async-safe logging setup
    tools/                    # Transliteration, Sefaria client, validators, author KB
    data/                     # word_dictionary.json + supporting data
    cache/                    # Sefaria API cache (auto-created)
    logs/                     # Log files (auto-created)
    tests/                    # pytest suite
  frontend/
    src/                      # React UI
    package.json              # Vite scripts
  README.md
  GEMINI_CONTEXT.md
```

## Quick Start

### Backend

1) Create a virtual environment and install dependencies:

```bash
cd backend
python -m venv .venv
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

pip install fastapi uvicorn google-generativeai pydantic pydantic-settings httpx
# Test dependencies (optional):
pip install pytest requests
```

2) Configure your Gemini key (required by backend/config.py):

```bash
# backend/.env
GEMINI_API_KEY=your-api-key
```

3) Run the API server:

```bash
python api_server_v7.py
# or
uvicorn api_server_v7:app --reload
```

Server runs on `http://localhost:8000`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:5173`.

## Configuration

Settings live in `backend/config.py` and are loaded from environment variables or a `.env` file.
Environment variables are case-insensitive.

Required:
- GEMINI_API_KEY: Gemini API key (backend will fail to start without it)

Common server settings:
- ENVIRONMENT (default: production)
- HOST (default: 0.0.0.0)
- PORT (default: 8000)
- CORS_ORIGINS (default: http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173)

Sefaria settings:
- SEFARIA_BASE_URL (default: https://www.sefaria.org/api)
- SEFARIA_TIMEOUT (default: 30)
- SEFARIA_MAX_RETRIES (default: 3)

Caching and paths:
- USE_CACHE (default: true)
- CACHE_DIR (default: backend/cache)
- DICTIONARY_FILE (default: backend/data/word_dictionary.json)

Logging:
- LOG_LEVEL (default: INFO)
- LOG_DIR (default: backend/logs)

Pipeline tuning:
- TRANSLITERATION_MAX_VARIANTS (default: 15)
- TRANSLITERATION_MIN_HITS (default: 1)
- GEMINI_MODEL (default: gemini-1.5-flash)
- GEMINI_MAX_TOKENS (default: 4000)
- GEMINI_TEMPERATURE (default: 0.7)
- DEFAULT_SEARCH_DEPTH (default: standard)
- MAX_SOURCES_PER_LEVEL (default: 10)

Development/testing:
- TEST_MODE (default: false)
- DEBUG (default: false)
- DEV_MODE (default: false)

Notes:
- Setting ENVIRONMENT=development or DEV_MODE=true enables debug endpoints and uvicorn reload.
- If you run the backend from the repo root, ensure `.env` is still discoverable or set
  environment variables explicitly.

## API Reference

Base URL: `http://localhost:8000`

### GET /health
Returns server status, version, environment, and log directory.

### POST /decipher
Runs Step 1 only (transliteration -> Hebrew).

Request body:
```json
{
  "query": "chezkas haguf",
  "strict": false
}
```

Response fields (abridged):
- success, hebrew_term, hebrew_terms
- confidence (high|medium|low)
- method (dictionary|sefaria|mixed_extraction|...)
- needs_validation (true|false)
- validation_type (none|clarify|choose|unknown)
- alternatives, choose_options
- word_validations (per-word breakdown)

### POST /decipher/confirm
Confirms a selection and updates the dictionary.

Request body:
```json
{
  "original_query": "chezkas haguf",
  "selected_hebrew": "...",
  "word_index": 0
}
```

Response:
```json
{
  "success": true,
  "message": "Confirmed: ...",
  "hebrew_term": "..."
}
```

### POST /decipher/reject
Rejects a transliteration.

Request body:
```json
{
  "original_query": "chezkas haguf",
  "feedback": "optional text"
}
```

Response:
```json
{
  "success": true,
  "message": "Thank you for the feedback."
}
```

### POST /search
Runs the full pipeline (Steps 1-2-3).

Request body:
```json
{
  "query": "migu",
  "depth": "standard"
}
```

Note: `depth` is accepted by the request model but is not currently used in the pipeline.

Response: `MareiMekomosResult` (from `backend/models.py`)

Key fields:
- original_query
- hebrew_term, hebrew_terms
- transliteration_confidence, transliteration_method, is_mixed_query
- query_type (sugya_concept, halacha_term, daf_reference, masechta, person, pasuk, klal, ambiguous, unknown, comparison)
- primary_source, primary_sources, interpretation
- sources (list of Source)
- sources_by_level (map: level label -> list of Source)
- total_sources, levels_included
- success, confidence
- needs_clarification, clarification_prompt, clarification_options
- message

Source fields in API response:
- ref, he_ref
- level (normalized enum)
- level_hebrew (label from Step 3, often Hebrew)
- hebrew_text, english_text
- author, categories
- relevance_note
- is_primary
- related_term

### Debug endpoints (development only)
Enabled when ENVIRONMENT=development or DEV_MODE=true:
- GET /debug/pending
- GET /debug/config
- GET /debug/logs

## Frontend Notes
- Entry point: `frontend/src/App.jsx`
- API base URL is hard-coded as `http://localhost:8000` (change `API_BASE` for deployment).
- Flow: `/decipher` -> optional `/decipher/confirm` or `/decipher/reject` -> `/search`.
- The UI includes an "expand source" button that calls `/sources/{ref}`; the backend does not
  currently expose this endpoint. Add one if you want on-demand full-text expansion.

## Local Corpus Setup (optional but recommended)
Step 3 can use a local Sefaria JSON export to locate sugyos via Shulchan Arukh/Tur/Rambam citations.

- Default path: `C:/Projects/Sefaria-Export/json` (see `backend/local_corpus.py`).
- To change: edit `DEFAULT_CORPUS_ROOT` or pass a path to `trickle_down_search_v9(...)` in a custom script.
- Expected structure (relative to corpus root):
  - Halakhah/Shulchan Arukh/**/merged.json
  - Halakhah/Tur/**/merged.json
  - Halakhah/Mishneh Torah/**/merged.json
- If the corpus is missing, Step 3 falls back to Sefaria API search.

## Caching and Output Files
- `backend/data/word_dictionary.json`: self-learning transliteration cache (updated on /decipher/confirm).
- `backend/cache/sefaria_v2/`: Sefaria API response cache (file-based, 7-day TTL).
- `backend/logs/`: daily log files created by the API server.
- `output/`: Step 3 source exports (txt + html) written by `backend/source_output.py`.

## CLI Tools
- `backend/console_full_pipeline.py`: interactive runner for Step 1, Step 2, or the full pipeline.
- `backend/step_one_decipher.py`: quick tests for the decipherer (runs when executed directly).
- `backend/step_two_understand.py`: quick tests for query analysis (runs when executed directly).
- `backend/step_three_search.py`: main search logic; exports results to `output/`.
- `backend/source_output.py`: write results to txt/html/json if you want custom output formats.

## Testing
Tests live in `backend/tests/`.

Typical runs:
```bash
cd backend
pytest tests/
```

Notes:
- Some tests call a running API at `http://localhost:8000` (start the backend first).
- Integration-style tests require `GEMINI_API_KEY`.
- `test_master_kb_integration.py` references `phase2_integration_helpers.py` which is not part of this repo; see that file for details.

## Troubleshooting

Backend fails to start:
- Ensure `GEMINI_API_KEY` is set (required by config validation).
- Install dependencies in your venv.
- Check that port 8000 is free.

Gemini errors or timeouts:
- Confirm the API key is valid.
- Reduce `GEMINI_MAX_TOKENS` or set `GEMINI_TEMPERATURE` lower.
- Check network access.

No sources found:
- Call `/decipher` to verify Step 1 output.
- Check logs in `backend/logs/`.
- If using local corpus, verify the export path is correct.

Frontend cannot reach backend:
- Ensure the backend is running on `http://localhost:8000`.
- Update `CORS_ORIGINS` or `API_BASE` if you changed ports.
- Check browser console for CORS errors.

## Design Notes
- Dictionary-first: cache hits avoid API calls and speed up Step 1.
- No vector search in Step 1: transliteration is rules-based + Sefaria validation.
- Author-aware validation: proper names are prioritized over generic words.
- Clarify instead of guessing: ambiguous transliterations prompt user confirmation.
- Trickle-up presentation: sources are grouped by textual level for pedagogy.
