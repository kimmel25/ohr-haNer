# Quick Import Fix - What You Need to Know

## The Simple Answer

**Your imports work with this pattern at the top of EVERY file:**

```python
import sys
from pathlib import Path

# This line makes imports work
sys.path.insert(0, str(Path(__file__).parent))

# Now these work:
from models import DecipherResult
from config import get_settings
```

## Visual Guide

### What __file__ Points To

```
When you run: python backend/api_server_v7.py

__file__ = "c:\Projects\marei-mekomos\backend\api_server_v7.py"
                                         ^^^^^^^^ .parent gets this

Path(__file__).parent = "c:\Projects\marei-mekomos\backend"
```

### What sys.path.insert Does

```python
sys.path.insert(0, "c:\Projects\marei-mekomos\backend")
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                     Adds this to Python's search path
```

Now when you write:
```python
from models import DecipherResult
```

Python looks in:
1. `c:\Projects\marei-mekomos\backend\models.py` ← FOUND! ✓

## Your Current Files

All these files already have the correct pattern:

✓ api_server_v7.py - Line 29: `sys.path.insert(0, str(Path(__file__).parent))`
✓ step_one_decipher.py - Line 30: `sys.path.insert(0, str(Path(__file__).parent))`
✓ main_pipeline.py - Has it
✓ All other backend files - Have it

## How to Run

```bash
# From anywhere, just run:
python backend/api_server_v7.py

# Or cd into backend first:
cd backend
python api_server_v7.py

# Both work the same!
```

## What NOT to Do

### ❌ Don't use dot imports
```python
from .models import DecipherResult  # ❌ Breaks!
```

### ❌ Don't use package imports
```python
from backend.models import DecipherResult  # ❌ Breaks!
```

### ✓ DO use simple imports
```python
from models import DecipherResult  # ✓ Works!
```

## If Imports Break

**Check these in order:**

1. **Is the sys.path line at the top of your file?**
   ```python
   sys.path.insert(0, str(Path(__file__).parent))
   ```

2. **Are you importing the right module name?**
   ```python
   from models import DecipherResult  # ✓
   from model import DecipherResult   # ✗ typo!
   ```

3. **Is the file you're importing from actually in backend/?**
   ```
   backend/
   ├── models.py        ← from models import ...
   ├── config.py        ← from config import ...
   └── tools/
       └── foo.py       ← from tools.foo import ...
   ```

## Summary

**The magic line:**
```python
sys.path.insert(0, str(Path(__file__).parent))
```

**What it does:**
- Adds `backend/` folder to Python's search path
- Makes `from models import ...` look in `backend/models.py`
- Works when you run files directly
- Simple, predictable, "just works"

**That's it!** This is the simplest import strategy that works for running files directly.
