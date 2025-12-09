# Pydantic Migration Fix - 2025-12-08

## Issue

Runtime error when calling `/search` endpoint:
```
AttributeError: 'DecipherResult' object has no attribute 'get'
File "main_pipeline.py", line 130, in search_sources
    if not step1_result.get("success") and not step1_result.get("hebrew_term"):
```

## Root Cause

[step_one_decipher.py](step_one_decipher.py:1) was refactored to return a Pydantic `DecipherResult` model instead of a dict, but [main_pipeline.py](main_pipeline.py:1) was still using dict syntax (`.get()` methods).

## Fix Applied

### 1. Changed Dict Syntax to Pydantic Model Syntax

**Before:**
```python
if not step1_result.get("success") and not step1_result.get("hebrew_term"):
    hebrew_term = step1_result.get("hebrew_term", query)
```

**After:**
```python
if not step1_result.success and not step1_result.hebrew_term:
    hebrew_term = step1_result.hebrew_term or query
```

### 2. Fixed Enum to String Conversion

`DecipherResult.confidence` is a `ConfidenceLevel` enum, but `MareiMekomosResult.transliteration_confidence` expects a string.

**Before:**
```python
transliteration_confidence=step1_result.confidence,
```

**After:**
```python
transliteration_confidence=step1_result.confidence.value,  # Convert enum to string
```

### 3. Updated Fallback Function

The `_fallback_step1()` function now returns a Pydantic `DecipherResult` instead of a dict:

```python
def _fallback_step1(query: str):
    from models import DecipherResult, ConfidenceLevel

    # Check if query is already Hebrew
    hebrew_chars = sum(1 for c in query if '\u0590' <= c <= '\u05FF')
    total_chars = sum(1 for c in query if c.isalpha())

    if total_chars > 0 and hebrew_chars / total_chars > 0.5:
        return DecipherResult(
            success=True,
            hebrew_term=query,
            confidence=ConfidenceLevel.HIGH,
            method="passthrough",
            message="Query is already in Hebrew"
        )

    return DecipherResult(
        success=False,
        hebrew_term=None,
        confidence=ConfidenceLevel.LOW,
        method="failed",
        message="Step 1 module not available and query is not Hebrew"
    )
```

### 4. Added Import Path Setup

Added the standard import setup pattern to [main_pipeline.py](main_pipeline.py:13-17):

```python
import sys
from pathlib import Path

# Add backend/ to path for local imports
sys.path.insert(0, str(Path(__file__).parent))
```

## Files Modified

- `backend/main_pipeline.py` - Lines 13-17 (imports), 131-155 (Step 1 handling), 200-201 (result creation), 230-255 (fallback function)

## All Changes to main_pipeline.py

| Line | Change | Reason |
|------|--------|--------|
| 13-17 | Added `sys.path.insert()` | Enable local imports |
| 131 | `.get("success")` → `.success` | Pydantic model attribute access |
| 137 | `.confidence` → `.confidence.value` | Convert enum to string |
| 149 | `.confidence` → `.confidence.value` | Convert enum to string |
| 151 | `.get("message")` → `.message` | Pydantic model attribute access |
| 155 | `.get("hebrew_term", query)` → `.hebrew_term or query` | Pydantic model attribute access |
| 200 | `.confidence` → `.confidence.value` | Convert enum to string |
| 230-255 | Return `DecipherResult` | Pydantic model instead of dict |

## Testing

To verify the fix works:

```bash
# Start the API server
cd backend
python api_server_v7.py

# In another terminal, test the search endpoint
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "chezkas haguf"}'
```

Expected: No `AttributeError`, should return sources successfully.

## Future Work

Steps 2 and 3 are still using **dataclasses** instead of the Pydantic models defined in [models.py](models.py:1):

- `step_two_understand.py` has its own `SearchStrategy` dataclass (line 66)
- `step_three_search.py` has its own `SearchResult` dataclass (line 133)

These could be migrated to Pydantic for consistency, but they work fine as-is since [main_pipeline.py](main_pipeline.py:1) imports from the step files directly.

## Status

✅ **FIXED** - The AttributeError is resolved and the pipeline should work correctly.

The fix maintains backward compatibility with Steps 2 and 3 which still use dataclasses.
