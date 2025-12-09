# Python Imports Guide - Simple Local Strategy

## ✅ How Imports Work in This Project

All files use **local imports with sys.path** - the simplest approach that "just works".

## The Pattern

**Every Python file starts with:**

```python
import sys
from pathlib import Path

# Add backend/ directory to Python's search path
sys.path.insert(0, str(Path(__file__).parent))

# Now you can import other backend files directly
from models import DecipherResult
from config import get_settings
from tools.word_dictionary import get_dictionary
```

## Why This Works

1. `Path(__file__).parent` gets the `backend/` directory
2. `sys.path.insert(0, ...)` adds it to Python's module search path
3. Now `from models import ...` looks in `backend/models.py`

## File Structure

```
backend/
├── models.py              ← from models import ...
├── config.py              ← from config import ...
├── step_one_decipher.py   ← from step_one_decipher import ...
├── api_server_v7.py       ← from api_server_v7 import ...
└── tools/
    ├── word_dictionary.py ← from tools.word_dictionary import ...
    └── sefaria_client.py  ← from tools.sefaria_client import ...
```

## How to Run Files

Just run them directly from anywhere:

```bash
# From project root
python backend/api_server_v7.py

# From backend/ directory
cd backend
python api_server_v7.py

# Both work! ✅
```

## Common Import Errors and Fixes

### ❌ Error: "ModuleNotFoundError: No module named 'models'"

**Cause:** Missing `sys.path.insert(0, str(Path(__file__).parent))`

**Fix:** Add these lines at the top of your file:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
```

### ❌ Error: "ImportError: attempted relative import with no known parent package"

**Cause:** Using relative imports like `from .models import ...`

**Fix:** Use absolute imports instead:
```python
# ❌ Don't use relative imports
from .models import DecipherResult

# ✅ Use absolute imports with sys.path
from models import DecipherResult
```

### ❌ Error: "ModuleNotFoundError: No module named 'backend'"

**Cause:** Trying to use package-style imports like `from backend.models import ...`

**Fix:** Use simple imports:
```python
# ❌ Don't use package-style
from backend.models import DecipherResult

# ✅ Use simple imports
from models import DecipherResult
```

## When to Use Each Import Style

### ✅ Use in THIS Project (Simple Local)
```python
sys.path.insert(0, str(Path(__file__).parent))
from models import DecipherResult
```

**Pros:**
- Works when running files directly
- No need for `__init__.py` files
- No need to install as a package
- Simple and predictable

**Cons:**
- Modifies sys.path (but that's fine for applications)

### ❌ Don't Use: Relative Imports
```python
from .models import DecipherResult  # ❌ Don't do this
```

**Why not:**
- Only works when running as a package
- Breaks when running files directly
- More complex setup

### ❌ Don't Use: Package-Style Imports
```python
from backend.models import DecipherResult  # ❌ Don't do this
```

**Why not:**
- Requires `backend/` to be installed as a package
- More complex setup
- Not needed for this project

## Quick Reference

**Template for any new backend file:**

```python
"""
Your file description here.
"""

import sys
from pathlib import Path

# Standard library imports
import asyncio
import logging
from typing import Dict, List, Optional

# Add backend/ to path for local imports
sys.path.insert(0, str(Path(__file__).parent))

# Now import from other backend files
from models import YourModel
from config import get_settings

# Import from tools/
from tools.word_dictionary import get_dictionary

# Your code here...
```

## Summary

**The Rule:** Every backend file adds `backend/` to `sys.path` first, then imports normally.

**Result:** Everything "just works" when you run `python filename.py`

**No need for:**
- `__init__.py` files
- Package installation
- `setup.py` or `pyproject.toml`
- Virtual environment activation (though still recommended)
- Complex PYTHONPATH configuration

**Just run the file and it works!** ✅
