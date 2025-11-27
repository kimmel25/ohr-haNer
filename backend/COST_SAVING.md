# Cost Saving Features 💰

This backend includes several features to help you save money on API calls during development.

## Features

### 1. **Smart Caching** (Automatic)
- All Claude API responses are cached for **24 hours**
- All Sefaria API responses are cached for **1 week** (they don't change)
- Same query = $0 cost on repeat requests
- Cache is file-based and survives server restarts

**Example:**
- First search for "kibbud av v'em" → Costs money
- Second search for "kibbud av v'em" (within 24h) → **FREE** (uses cache)

### 2. **Development Mode** (Manual)
Use this when you're testing frontend changes and don't care about real data.

**Enable Dev Mode:**
```bash
# Windows
set DEV_MODE=true
python main.py

# Linux/Mac
DEV_MODE=true python main.py
```

In Dev Mode:
- ❌ NO Claude API calls (uses mock data)
- ✅ Still hits Sefaria API (but with caching)
- 💰 Saves ~$0.02-0.05 per request

**Disable Dev Mode:**
```bash
# Windows
set DEV_MODE=false
# or just don't set it

# Linux/Mac
DEV_MODE=false python main.py
# or just don't set it
```

### 3. **Cache Management Endpoints**

#### Check your savings:
```bash
curl http://localhost:8000/cache/stats
```

Response shows:
- How many requests are cached
- Estimated money saved
- Cache size
- Dev mode status

#### Clear cache (get fresh results):
```bash
curl -X POST http://localhost:8000/cache/clear
```

## Cost Estimates

### Claude API (Sonnet 4):
- Input: ~$3 per 1M tokens
- Output: ~$15 per 1M tokens
- Typical request: ~$0.02-0.05

### Sefaria API:
- **FREE** (but we still cache to be respectful)

## How Caching Saves Money

**Without caching:**
```
10 test searches × $0.03 = $0.30
100 test searches × $0.03 = $3.00
```

**With caching:**
```
10 unique searches × $0.03 = $0.30
100 repeated searches × $0.00 = $0.00
```

## Development Workflow

### Testing Frontend (use Dev Mode):
```bash
DEV_MODE=true python main.py
```
- Mock responses are instant
- No API costs
- Perfect for UI/UX work

### Testing Real Data (use Cache):
```bash
# Just run normally
python main.py
```
- First request costs money
- Repeat requests are free (24h)
- Use a few test queries over and over

### Before Launching to Users:
```bash
# Clear cache to ensure fresh results
curl -X POST http://localhost:8000/cache/clear

# Run normally (no dev mode)
python main.py
```

## Cache Locations

Caches are stored in:
- `backend/cache/claude/` - Claude API responses
- `backend/cache/sefaria/` - Sefaria API responses

You can delete these folders to manually clear cache.

## Tips to Save Money

1. **Use the same test queries** during development
2. **Enable Dev Mode** when working on frontend
3. **Check cache stats** regularly: `curl localhost:8000/cache/stats`
4. **Don't clear cache** unless you need fresh data
5. **Cache survives restarts** - no need to recreate it

## Example Workflow

```bash
# Day 1: Testing
python main.py
# Search "shabbat" → costs $0.03
# Search "shabbat" again → FREE (cached)
# Search "shabbat" 50 more times → FREE

# Day 2: Frontend work
DEV_MODE=true python main.py
# All searches → FREE (mock mode)

# Day 3: Real testing
python main.py
# Search "shabbat" → FREE (still cached from Day 1)
# Search "tefillin" → costs $0.03
# Search "tefillin" again → FREE

# Check savings
curl localhost:8000/cache/stats
# Shows: Saved $1.50+ by caching 50 requests
```

## Ready for Production?

When you're ready to launch:
1. Turn off `DEV_MODE` (just don't set it)
2. Keep caching enabled (it's automatic)
3. Users will benefit from shared cache
4. Each unique topic is only expensive once per 24h
