# Marei Mekomos V5.0 - "Sugya Archaeology"
## Torah Source Finder with VGR Protocol

**A sophisticated Torah source discovery system that uses Acharonim as "semantic indices" to uncover foundational sources through citation network analysis.**

---

## Core Methodology: Sugya Archaeology

This is NOT a keyword search engine. It's a **Citation Graph Traversal System**.

The insight: When later authorities (Acharonim) like Ketzos HaChoshen, Pnei Yehoshua, or Reb Akiva Eiger discuss a topic, they systematically cite:
- **Origin**: Talmudic sugya
- **Interpretation**: Rishonim (Rashi, Tosfos, Rambam, Rashba, etc.)
- **Ruling**: Shulchan Aruch and its commentaries

By analyzing *what* these later authorities cite, we discover the foundational sources that a keyword search would never find. This approach is robust against terminology drift because the linkage is **conceptual, not lexical**.

---

## Key Features

### 1. VGR Protocol (Validated Generative Retrieval)

A strict 3-phase anti-hallucination system:

1. **Generation Phase**: Claude interprets query and suggests potential sources
2. **Extraction Phase**: Parse citations from Claude's response
3. **Verification Phase**: Every ref is validated against Sefaria API
   - `200 OK` + Text → Source is **real**, passed to frontend
   - `400/404` → **HALLUCINATION**, silently discarded

This "gatekeeper" logic ensures AI can be creative in associations while being strict about presenting facts.

### 2. Contextual Vectorization

Detects query intent to prioritize appropriate commentators:

| Intent | Keywords | Prioritized Sources |
|--------|----------|---------------------|
| **Lomdus** (Analytical) | "why", "svara", "contradiction", "machlokes" | Ketzos, Nesivos, Pnei Yehoshua, Reb Akiva Eiger |
| **Psak** (Practical) | "can I", "is it mutar", "how do I" | Mishnah Berurah, Aruch HaShulchan, Shakh, Taz |
| **Makor** (Source-finding) | "where does it say", "source for" | Primary Gemara sugyos |

### 3. Masechta-Specific Acharon Prioritization

Based on the Reference Guide to the Talmud Bavli, each masechta has its own set of essential Acharonim:

```
Kesubos: Pnei Yehoshua, Avnei Milluim, Beis Shmuel, Chelkas Mechokek
Bava Kamma: Ketzos HaChoshen, Nesivos HaMishpat, Chazon Ish
Pesachim: Pnei Yehoshua, Reb Akiva Eiger, Chiddushei HaTzlach
Niddah: Chazon Ish, Aruch LaNer, Sidrei Taharah
```

### 4. High-Entropy Query Detection (Chavrusa-style Disambiguation)

Single-word ambiguous queries trigger clarifying questions:

```
"niddah" → "Are you asking about hilchos niddah? Or tumas niddah? Or masechta Niddah?"
"shabbos" → "A specific melacha? Hilchos Shabbos in general? Eruvin/techumin?"
```

### 5. Slug Translation Dictionary

Comprehensive mapping from common variations to Sefaria-compatible slugs:

```
"kesubos" / "kesuvos" / "ketubos" → "Ketubot"
"tosfos" / "tosefos" / "תוספות" → "Tosafot"
"ketzos" / "קצות החושן" → "Ketzot HaChoshen"
```

### 6. Hebrew Citation Pattern Extraction

Recognizes citation markers in Hebrew text:
- `ע״ש`, `עיין` - "See there"
- `כמ״ש`, `כדאיתא` - "As written in"
- `ד״ה` - Dibbur hamaschil (Rashi/Tosfos heading)
- `מבואר מדבריו` - "Explained in his words"

---

## API Endpoints

### `POST /search`
Main search endpoint using Sugya Archaeology + VGR Protocol.

**Request:**
```json
{
  "topic": "chuppas niddah",
  "clarification": "optional user clarification"
}
```

**Response:**
```json
{
  "topic": "chuppas niddah",
  "interpreted_query": "Laws of marriage ceremony when kallah is niddah",
  "query_intent": "lomdus",
  "primary_masechta": "Ketubot",
  "sources": [...],
  "summary": "...",
  "methodology_notes": "..."
}
```

### `GET /test/intent/{query}`
Test query intent detection.

### `GET /test/slug/{ref}`
Test slug translation.

### `GET /test/related/{ref}`
Test Sefaria Related API.

---

## Pipeline Stages

```
┌──────────────────────────────────────────────────────────────────┐
│ STAGE 1: QUERY INTERPRETATION (VGR Generation Phase)            │
├──────────────────────────────────────────────────────────────────┤
│ • Check high-entropy queries (disambiguation)                    │
│ • Detect query intent (lomdus/psak/makor)                       │
│ • Normalize spelling/transliteration                             │
│ • Identify primary Gemara sugyos                                │
└───────────────────────────┬──────────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────┐
│ STAGE 2: DISCOVER COMMENTARIES                                   │
├──────────────────────────────────────────────────────────────────┤
│ • Use Sefaria Related API on primary sugyos                      │
│ • Prioritize by: Intent → Masechta-specific Acharonim → Default │
│ • Fetch commentary texts                                         │
└───────────────────────────┬──────────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────┐
│ STAGE 3: CITATION ANALYSIS (VGR Extraction Phase)               │
├──────────────────────────────────────────────────────────────────┤
│ • Claude analyzes commentary texts                               │
│ • Extract earlier source citations                               │
│ • Identify key machlokesim                                       │
│ • Filter for query relevance                                     │
└───────────────────────────┬──────────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────┐
│ STAGE 4: VALIDATION (VGR Verification Phase)                    │
├──────────────────────────────────────────────────────────────────┤
│ • Validate every ref against Sefaria API                        │
│ • 200 OK → Real source, include                                 │
│ • 404/400 → HALLUCINATION, discard                              │
│ • Optional: Content match verification                           │
└──────────────────────────────────────────────────────────────────┘
```

---

## Two-Tier Caching Strategy

### Tier 1: Immutable Acharon Layer
- **TTL**: 1 week (or permanent)
- **Contents**: Sefaria text fetches, Related API results
- **Rationale**: Ketzos HaChoshen from 1788 won't change

### Tier 2: User Session Layer
- **TTL**: 24 hours
- **Contents**: Claude interpretation results, citation analysis
- **Rationale**: LLM capabilities improve, allow cache refresh

---

## Environment Variables

```bash
ANTHROPIC_API_KEY=sk-...          # Required
COST_SAVING_MODE=true             # Optimize for minimal API costs
STRICT_VALIDATION=true            # Enhanced anti-hallucination
MAX_COMMENTARIES=12               # Per base text
MAX_SOURCES=30                    # Final results limit
```

---

## Yeshivish Conventions

Throughout the codebase, we use proper yeshivish transliteration:
- **Sav not tav**: Shabbos, Kesubos, Pesachim
- **Standard terminology**: Tosfos, Meseches, Sugya
- **Hebrew citation markers**: ע״ש, ד״ה, כמ״ש

---

## Resources Incorporated

This implementation draws from:

1. **"Computational Hermeneutics and the Digital Beit Midrash"** (Gemini Paper)
   - VGR Protocol
   - Contextual Vectorization
   - Two-tier caching strategy
   - Slug translation middleware

2. **Reference Guide to the Talmud Bavli**
   - Masechta-specific Acharon prioritization
   - Universal Rishonim priority list
   - Commentary layout conventions

3. **Learning Notes (Kesubos, Pesachim)**
   - Real citation patterns and methodology
   - Machlokes Rishonim tracing
   - Cross-reference patterns

---

## Running the Application

### Backend
```bash
cd backend
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-...
python main.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## TODO: Additional Enhancements

```python
#TODO: The user has learning notes available that show real citation patterns.
# File path: [USER TO FILL IN - e.g., /path/to/kesubos_notes.md]
# These could be loaded at runtime for improved citation pattern recognition.

#TODO: Implement citation graph database for building proprietary linkage data
# over time - each successful search adds to the knowledge graph.

#TODO: Add "shiur mode" vs "shayla mode" selector in frontend for explicit
# intent specification.
```

---

## License

For internal use. Built for the Torah learning community.

---

*"ואמר רבי חייא בר אבא אמר רבי יוחנן: כל המלמד את בן חבירו תורה מעלה עליו הכתוב כאילו עשאו"*
*(Sanhedrin 19b)*
