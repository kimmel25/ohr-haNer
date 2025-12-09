# Refactoring Opportunities

This document outlines potential improvements to make the codebase even cleaner and more maintainable.

## 🔴 High Priority (Do Soon)

### 1. Consolidate Sefaria Validation Logic
**Current Issue:** `sefaria_validator.py` (294 lines) only uses the search API, but `sefaria_client.py` (962 lines) already has a comprehensive search wrapper.

**Files Involved:**
- `backend/tools/sefaria_validator.py` - Validation-specific logic
- `backend/tools/sefaria_client.py` - General Sefaria client

**Refactoring Options:**

**Option A (Recommended):** Merge validator into client
```python
# sefaria_client.py

class SefariaClient:
    # ... existing methods ...

    async def validate_term(self, hebrew: str, min_hits: int = 1) -> ValidResult:
        """Validate a Hebrew term against Sefaria corpus."""
        # Move logic from sefaria_validator.py here
        pass

    async def find_first_valid(self, variants: List[str], min_hits: int = 1):
        """Find first valid variant (for transliteration)."""
        # Move from sefaria_validator.py
        pass
```

**Option B:** Keep separate but use client internally
```python
# sefaria_validator.py

from .sefaria_client import get_sefaria_client

class SefariaValidator:
    def __init__(self):
        self.client = get_sefaria_client()  # Reuse client

    async def validate_term(self, hebrew: str):
        # Use self.client.search() instead of direct API calls
        return await self.client.search(hebrew)
```

**Benefits:**
- Reduces duplicate HTTP client code
- Single source of truth for Sefaria API patterns
- Easier to add caching/rate limiting in one place

**Estimated Time:** 2-3 hours

---

### 2. Simplify User Validation Overlap
**Current Issue:** `user_validation.py` (649 lines) duplicates some word analysis logic from `transliteration_map.py`.

**Files Involved:**
- `backend/user_validation.py` - Full validation + prompts
- `backend/tools/transliteration_map.py` - Core transliteration

**Problem Areas:**
1. Both files have word confidence calculation logic
2. Both generate Hebrew variants
3. Unclear which is the "source of truth"

**Refactoring Plan:**

```python
# transliteration_map.py - SINGLE SOURCE OF TRUTH
def analyze_word_confidence(word: str) -> WordConfidence:
    """
    Canonical word analysis.
    Returns: confidence score, rules applied, variants
    """
    pass

# user_validation.py - USE transliteration_map
from tools.transliteration_map import analyze_word_confidence

def analyze_word(word: str) -> WordValidation:
    """Build validation prompts using canonical analysis."""
    core_analysis = analyze_word_confidence(word)
    # Add UI-specific logic (CLARIFY/CHOOSE/UNKNOWN prompts)
    return WordValidation(...)
```

**Benefits:**
- One place to maintain word analysis logic
- user_validation.py focuses purely on UI prompts
- Less risk of inconsistencies

**Estimated Time:** 3-4 hours

---

## 🟡 Medium Priority (Nice to Have)

### 3. Centralize Caching Strategy
**Current Issue:** `sefaria_client.py` has internal dict-based caching, but it's not persistent and inconsistent with the dictionary caching pattern.

**Recommendation:**
- Either use persistent file-based cache for ALL Sefaria responses
- Or stick with in-memory only and document it clearly

**Current:**
```python
# sefaria_client.py
self._cache = {}  # In-memory only, lost on restart
```

**Option A - Persistent Cache:**
```python
import json
from pathlib import Path

class SefariaClient:
    def __init__(self):
        self.cache_file = Path("data/sefaria_cache.json")
        self._load_cache()

    def _load_cache(self):
        if self.cache_file.exists():
            with open(self.cache_file) as f:
                self._cache = json.load(f)
```

**Option B - Document In-Memory:**
```python
class SefariaClient:
    """
    Sefaria API client.

    Caching: In-memory only (cleared on restart).
    For persistent caching, use word_dictionary.py for transliterations.
    """
    def __init__(self):
        self._cache = {}  # Session cache only
```

**Estimated Time:** 1-2 hours

---

### 4. Logging Configuration Consistency
**Current Issue:** Different modules set up logging differently. Some use `logging_config.py`, others use manual setup.

**Files to Review:**
- `backend/logging_config.py` - Centralized config
- `backend/step_one_decipher.py` - Uses `logger = logging.getLogger(__name__)`
- `backend/main_pipeline.py` - Different setup
- Various tools/ files

**Refactoring:**
```python
# logging_config.py (already exists, make it canonical)
def get_logger(name: str):
    """
    Get a logger with standard formatting.
    Use this everywhere instead of logging.getLogger().
    """
    logger = logging.getLogger(name)
    # Apply standard formatting
    return logger

# Then in every file:
from logging_config import get_logger
logger = get_logger(__name__)
```

**Estimated Time:** 1 hour

---

## 🟢 Low Priority (Future Cleanup)

### 5. Test Organization
**Current State:**
- `tests/test_confirm_selection.py` - Unit tests with mocking (incomplete)
- `tests/test_phrase_issue.py` - Manual integration test
- `tests/test_step_one_focused.py` - Comprehensive test suite (40 cases)

**Recommendation:**
```
backend/tests/
├── unit/
│   ├── test_transliteration_map.py
│   ├── test_word_dictionary.py
│   └── test_sefaria_client.py
├── integration/
│   ├── test_step_one.py          (rename from test_step_one_focused)
│   ├── test_full_pipeline.py
│   └── test_api_endpoints.py
└── manual/
    └── test_phrase_issue.py       (keep for ad-hoc testing)
```

**Estimated Time:** 2 hours

---

### 6. Type Hints & Documentation
**Current:** Mixed type hint usage, some functions fully typed, others not.

**Example - Current:**
```python
def decipher(query):
    """Turn user's transliteration into Hebrew."""
    # ... 140 lines ...
```

**Example - Improved:**
```python
from typing import Dict, Optional

def decipher(query: str) -> Dict[str, Any]:
    """
    Turn user's transliteration into Hebrew.

    Args:
        query: User's input (transliteration or Hebrew)

    Returns:
        {
            "success": True/False,
            "hebrew_term": "מיגו",
            "confidence": "high/medium/low",
            "method": "dictionary/sefaria/transliteration",
            "message": "...",
            "alternatives": [...],
            "needs_clarification": False
        }

    Raises:
        ValueError: If query is empty
    """
    # ... implementation ...
```

**Recommendation:**
- Add type hints to all public functions
- Use dataclasses where appropriate (already done in user_validation.py)
- Add docstrings to all modules and functions

**Estimated Time:** 4-6 hours for full codebase

---

## 🔵 Architecture Improvements

### 7. Consider Pydantic Models for Data Flow
**Current:** Dicts passed between steps, shape not enforced

**Example - Current:**
```python
result = await decipher(query)  # Returns dict
# What keys are in result? Have to read the code.
hebrew = result.get("hebrew_term")
```

**Example - With Pydantic:**
```python
from pydantic import BaseModel

class DecipherResult(BaseModel):
    success: bool
    hebrew_term: Optional[str]
    confidence: str
    method: str
    message: str
    alternatives: List[str] = []
    needs_clarification: bool = False

# Then:
result: DecipherResult = await decipher(query)
hebrew = result.hebrew_term  # Type-safe, autocomplete works
```

**Benefits:**
- Type safety at runtime
- Auto-validation
- Better IDE autocomplete
- Self-documenting code

**Estimated Time:** 6-8 hours (affects 3 pipeline steps)

---

### 8. Environment Configuration Class
**Current:** Scattered `os.getenv()` calls throughout code

**Recommendation:**
```python
# backend/config.py (new file)
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    anthropic_api_key: str
    use_cache: bool = True
    test_mode: bool = False
    log_level: str = "INFO"
    sefaria_base_url: str = "https://www.sefaria.org/api"

    class Config:
        env_file = ".env"

# Usage everywhere:
from config import Settings
settings = Settings()
client = Anthropic(api_key=settings.anthropic_api_key)
```

**Benefits:**
- Single source of truth for config
- Type-safe
- Automatic .env loading
- Validation on startup (fails fast if key missing)

**Estimated Time:** 2-3 hours

---

## 📊 Summary Priority Matrix

| Refactoring | Impact | Effort | Priority | Timeline |
|-------------|--------|--------|----------|----------|
| Consolidate Sefaria validation | High | Medium | 🔴 High | Next sprint |
| Simplify user validation | High | Medium | 🔴 High | Next sprint |
| Centralize caching | Medium | Low | 🟡 Medium | This month |
| Logging consistency | Medium | Low | 🟡 Medium | This month |
| Test organization | Low | Medium | 🟢 Low | When needed |
| Type hints & docs | Medium | High | 🟢 Low | Ongoing |
| Pydantic models | High | High | 🔵 Future | V8 |
| Config class | Medium | Low | 🔵 Future | V8 |

---

## 🎯 Recommended Next Steps

1. **This Week:** Fix gitignore issues (DONE ✅)
2. **Next Week:** Consolidate Sefaria validation (#1)
3. **This Month:** Simplify user validation overlap (#2)
4. **Ongoing:** Add type hints to new code as you write it

---

## 📝 Notes for LLMs Reading This

When working on this codebase:

1. **File Structure is Clean:** After 2025-12-08 cleanup, all active code is in clear locations. No need to search for functionality - it's where it says it is.

2. **Pipeline is Linear:** Step 1 → Step 2 → Step 3. Each step has ONE file. No complex orchestration.

3. **Tools are Utilities:** Everything in `tools/` is imported by the step files. They don't import each other (except sefaria_validator could use sefaria_client).

4. **Tests are Separate:** All in `backend/tests/`. Don't confuse test code with production code.

5. **No Dead Code:** If it's not in the README structure diagram, it shouldn't exist.

When refactoring:
- Read the current code first (don't assume V5/V6 architecture)
- Test before committing (run pytest tests/)
- Update this document when you complete a refactoring
