# Ohr HaNer (Marei Mekomos) - Comprehensive Project Context

**Version:** V7 (Local Corpus V10, Step 3 V5)  
**Type:** Torah Research Assistant with AI-Powered Query Analysis  
**Stack:** Python (FastAPI) + React (Vite) + Gemini AI (Flash) + Sefaria API  
**Purpose:** Transform natural language Torah queries (transliterated/Hebrew/English) into organized, hierarchical source compilations  
**Last Updated:** January 1, 2026

---

## 🎯 Project Mission & Philosophy

### Core Mission
Transform natural language Torah queries into comprehensive, hierarchically-organized source compilations by intelligently discovering where topics are discussed across gemara, rishonim, and acharonim. The system presents results in proper hierarchical order (base texts → commentaries).

### Guiding Philosophy
1. **User Understanding First**: "Getting into the user's head is most important"
2. **Transparency**: "We aren't scared to show our own lack of understanding"
3. **Accuracy Over Guessing**: Better to ask for clarification than provide wrong sources
4. **Trickle-Up Presentation**: Sources flow naturally: Gemara → Rishonim → Acharonim
5. **Semantic Intelligence**: Gemini AI analyzes INTENT, not just keywords

### What Makes This Different
- **No Vector Search Required**: Dictionary-first approach with rule-based transliteration
- **Smart Discovery**: Uses achronim (MB, BY) as "semantic indices" to discover relevant sugyos
- **Topic vs. Author Separation**: Understands "Ran's shittah on bittul chometz" means search for "bittul chometz", get Ran's commentary
- **Nuance Detection**: Differentiates between broad topics and specific sub-topics/shittot
- **Local Corpus Integration**: Can work offline with Sefaria JSON export

---

## 🏗️ System Architecture

### Three-Step Pipeline

```
USER INPUT → [STEP 1: DECIPHER] → [STEP 2: UNDERSTAND] → [STEP 3: SEARCH] → FORMATTED OUTPUT
   (any format)      (Hebrew terms)     (search strategy)    (organized sources)    (TXT/HTML)
```

#### STEP 1: DECIPHER (`step_one_decipher.py`)

**Goal:** Convert transliterated/mixed input → validated Hebrew terms WITHOUT using AI  
**Input:** User query (transliteration, Hebrew, English, or mixed)  
**Output:** `DecipherResult` with Hebrew terms + confidence level  
**Method:** Dictionary-first, rule-based transliteration, Sefaria validation

**The Algorithm:**

```
1. DETECT QUERY TYPE
   - Pure Hebrew? → Direct validation
   - Pure English? → Check for author names, otherwise pass through
   - Mixed? → Extract Hebrew/transliterated segments

2. DICTIONARY LOOKUP (Instant Win)
   - Check data/word_dictionary.json
   - If found: Return with HIGH confidence
   - Cache: ~500+ known terms for instant matching

3. RULE-BASED TRANSLITERATION
   - Apply transliteration_map.py rules:
     * Prefix detection (ha-, ve-, she-, mi-, be-, le-, etc.)
     * Consonant mappings (multiple variants for each letter)
     * Vowel handling (ignore or map to shva)
     * Smichut forms (haguf ↔ haguf, chezkas ↔ chezkat)
     * Sofit normalization (ם↔מ, ן↔נ, ך↔כ, ף↔פ, ץ↔צ)
     * Aramaic endings (-ta, -sa, -a)
   - Generate 10-50 Hebrew variants per term

4. SEFARIA VALIDATION (Ground Truth)
   - For each variant, query Sefaria:
     * Search API for word occurrences
     * Books API for book titles
     * Author KB for author names
   - Score each variant:
     * Exact title match: 1.0
     * High frequency in corpus: 0.7-0.9
     * Author name match: 0.8-1.0
     * Low frequency: 0.3-0.6
   - Batch validation for efficiency (max 10 concurrent)

5. CONFIDENCE DETERMINATION
   - HIGH: Dictionary hit OR Sefaria score > 0.8
   - MEDIUM: Sefaria score 0.5-0.8
   - LOW: Sefaria score 0.3-0.5
   - CLARIFY: Multiple high-scoring variants (ask user)
   - CHOOSE: Multiple medium-scoring variants (show options)
   - UNKNOWN: No variants validated

6. SPECIAL HANDLING
   - Author Names: Use torah_authors_master.py (600+ entries)
   - Mixed Queries: Segment into Hebrew/English parts
   - Multi-word phrases: Validate as phrase AND individual words
```

**Key Features:**
- **No AI Required**: Deterministic, explainable, fast
- **Mixed Query Support**: "what is the ran's shittah in bittul chometz"
- **Author Recognition**: Knows Ran, Rashi, Tosafos, Rambam, etc.
- **Smart Prefixes**: Handles ha-, ve-, be-, le-, mi-, she- automatically
- **Variant Generation**: "migu" → מיגו, "chezkas haguf" → חזקת הגוף
- **Validation Required**: Every variant must exist in Sefaria corpus
- **Batch Processing**: Validates multiple terms concurrently

**Example Flow:**
```
Input: "what is the rans shittah in bittul chometz"

1. Detect: Mixed query (English + transliteration)
2. Segment: 
   - English: ["what", "is", "the", "shittah", "in"]
   - Transliteration: ["ran", "bittul", "chometz"]
3. Author Detection: "ran" → רן (via torah_authors_master.py)
4. Transliteration:
   - "bittul" → [ביטול, ביטל, בטול, ביתול, ...]
   - "chometz" → [חמץ, חומץ, חומץ, ...]
5. Validation:
   - רן: AUTHOR_MATCH score=1.0
   - ביטול: High frequency in Pesachim, score=0.85
   - חמץ: Very high frequency in Pesachim, score=0.95
6. Output:
   - hebrew_terms: ["רן", "ביטול חמץ"]
   - confidence: HIGH
   - validation_status: PERFECT_MATCH
```

**Output Schema:**
```python
class DecipherResult:
    hebrew_term: str                    # Primary Hebrew term
    hebrew_terms: List[str]             # All Hebrew terms found
    english_remainder: str              # Non-Hebrew parts
    confidence: ConfidenceLevel         # HIGH/MEDIUM/LOW/CLARIFY/CHOOSE/UNKNOWN
    validation_status: ValidationStatus # How well validated
    requires_clarification: bool        # Need user input?
    clarification_options: List[str]    # Options if CHOOSE
    original_query: str
    word_validations: List[WordValidation]  # Per-word details
```

#### STEP 2: UNDERSTAND (`step_two_understand.py` - V5)

**Goal:** Analyze user intent and build a semantic search strategy  
**Input:** Hebrew terms from Step 1 + original query  
**Output:** `QueryAnalysis` - complete search plan with WHAT/WHERE/WHOSE/HOW  
**Method:** Gemini AI (Flash) with structured prompt engineering

**The Critical Innovation: Topic vs. Author Separation**

This is where the magic happens. Step 2 understands the difference between:
- **TOPICS** (the INYAN): What to search for → "ביטול חמץ", "חזקת הגוף"
- **AUTHORS** (WHOSE commentary): Who to fetch → Ran, Rashi, Tosafos
- **LOCATIONS** (WHERE): Which masechtos/dapim/simanim → Pesachim 4b, Bava Metzia 100a

**Example:**
```
Query: "what is the ran's shittah in bittul chometz"
❌ WRONG: Search for "רן ביטול חמץ" (will find nothing)
✅ RIGHT: 
   - search_topics: ["ביטול חמץ"] ← Search for THIS
   - target_authors: ["Ran"]        ← Fetch THIS author's commentary
   - realm: "halacha/gemara"
```

**Query Classification (V5):**

Gemini classifies queries into these types:

1. **TOPIC**: General exploration
   - "migu" → Broad search for מיגו across gemara
   - Method: Usually trickle_up (gemara → rishonim)

2. **NUANCE**: Specific sub-topic with focus
   - "bari vishema BEISSURIN" → Not just "bari vishema", specifically in context of afflictions
   - Needs: landmark source + focus terms
   - Method: trickle_up_filtered (only fetch commentaries on relevant segments)

3. **SHITTAH**: One author's view (V5 classification)
   - "ran's shittah on bittul chometz"
   - Needs: topic search + specific author fetch
   - Method: Topic-filtered with author prioritization

4. **COMPARISON**: Compare multiple views
   - "how does ran differ from rashi on bittul chometz"
   - Needs: topic search + multiple author fetch
   - Method: Topic-filtered, fetch all target authors

5. **MACHLOKES**: Dispute/disagreement
   - "machlokes rashi and tosafos on migu"
   - Similar to comparison
   - Method: Topic-filtered, highlight differences

6. **QUESTION**: Specific halachic/conceptual question
   - "can you be motzi someone with migu"
   - Method: Hybrid (search + semantic understanding)

7. **SOURCE_REQUEST**: Direct reference lookup
   - "show me rashi on pesachim 4b"
   - Method: Direct fetch (no search needed)

8. **HALACHA**: Practical halacha lookup
   - "how do you kasher a pot"
   - Realm: halacha (SA/Rambam focus)

**The System Prompt (Conceptual):**

```
You are analyzing a Torah query. Your job is to build a SEARCH STRATEGY.

KEY RULES:
1. Separate TOPICS from AUTHORS
   - Authors: Rashi, Tosafos, Ran, Rambam, etc. → target_authors
   - Topics: The INYAN (migu, bittul chometz, etc.) → search_topics

2. For SHITTAH/COMPARISON queries:
   - search_topics = the CONCEPT (what to search for)
   - target_authors = whose commentary to fetch
   - Do NOT put author names in search_topics

3. For NUANCE queries (including shittah/comparison):
   - Identify focus_terms (specific aspect)
   - Identify topic_terms (general concept)
   - Suggest a landmark source if possible

4. Provide WHERE to look:
   - target_masechtos: Which tractates
   - target_dapim: Specific dapim if known
   - target_simanim: SA/Tur simanim if halacha

Return JSON with:
- query_type: (topic/nuance/shittah/comparison/etc.)
- search_topics: WHAT to search for (the INYAN)
- target_authors: WHOSE commentary to fetch
- target_masechtos/dapim/simanim: WHERE to look
- focus_terms: For nuance queries
- suggested_landmark: Best source to start from
- confidence: How confident in this analysis
```

**Search Method Logic (V5):**

Step 2 suggests a search method, but Step 3 may override:

- **trickle_up**: Gemara → Rishonim → Acharonim
  - Use for: Simple topics, known locations
  - Example: "migu" with known dapim

- **trickle_down**: Acharonim → discover dapim → fetch rishonim
  - Use for: Comparisons, shittot, complex topics
  - Why: Achronim synthesize and cite specific sugyos
  - Example: "ran vs rashi on bittul chometz"

- **trickle_up_filtered** (V5): Like trickle_up but only fetch commentaries on relevant segments
  - Use for: Nuance queries with focus terms
  - Why: Avoid fetching entire masechta of Rashi
  - Example: "bari vishema beissurin"

- **hybrid**: Both trickle_up and trickle_down, find overlap

- **direct**: Go straight to specified reference
  - Use for: "show me rashi on X"

**V5 Improvements:**

1. **SHITTAH = NUANCE**: Queries like "ran's shittah" are now classified as NUANCE with focus
2. **Landmark Validation**: Suggested landmarks must be valid Sefaria refs (no ranges like "2a-6b")
3. **Clarification Triggers**: Vague queries trigger clarification questions
4. **Author-Aware**: Knows Ran writes on Rif, not directly on Gemara
5. **Better Ref Hints**: Provides verification keywords for each suggested ref

**Output Schema:**
```python
class QueryAnalysis:
    original_query: str
    hebrew_terms_from_step1: List[str]
    
    # WHAT type of query
    query_type: QueryType  # topic/nuance/shittah/comparison/etc.
    realm: str             # gemara/halacha/chumash/midrash
    
    # WHAT to search for (the INYAN, NOT authors)
    search_topics: List[str]         # English
    search_topics_hebrew: List[str]  # Hebrew
    
    # WHERE to look
    target_masechtos: List[str]
    target_dapim: List[str]
    target_simanim: List[str]
    target_perakim: List[str]
    
    # WHOSE commentary to fetch
    target_authors: List[str]
    primary_author: Optional[str]  # For shittah queries
    
    # For NUANCE queries (V5)
    focus_terms: List[str]           # Specific aspect
    topic_terms: List[str]           # General concept
    suggested_landmark: Optional[str] # Starting point
    landmark_confidence: str         # high/medium/guessing
    nuance_description: str          # What makes this specific
    
    # Search strategy
    trickle_direction: str  # up/down/both
    foundation_type: str    # gemara/halacha_sa/rishon
    
    # Metadata
    confidence: ConfidenceLevel
    needs_clarification: bool
    clarification_question: Optional[str]
    reasoning: str  # Gemini's explanation
```

**Example Outputs:**

**Simple Topic:**
```json
{
  "query_type": "topic",
  "search_topics": ["migu"],
  "search_topics_hebrew": ["מיגו"],
  "target_masechtos": ["Bava Kamma", "Bava Metzia", "Ketubot"],
  "target_authors": ["Rashi", "Tosafos"],
  "trickle_direction": "up",
  "confidence": "high"
}
```

**Shittah Query (V5):**
```json
{
  "query_type": "nuance",  // V5: shittah is a nuance
  "search_topics": ["ביטול חמץ"],  // The INYAN
  "target_authors": ["Ran", "Rashi", "Tosafos"],
  "primary_author": "Ran",  // Focus on this author
  "target_masechtos": ["Pesachim"],
  "focus_terms": ["דעת הרן", "רן"],
  "topic_terms": ["ביטול חמץ", "חיוב ביטול"],
  "suggested_landmark": "Pesachim 4b",
  "landmark_confidence": "medium",
  "nuance_description": "Ran's specific approach to bittul chometz",
  "trickle_direction": "both",
  "confidence": "high"
}
```

**Comparison Query:**
```json
{
  "query_type": "comparison",
  "search_topics": ["חזקת הגוף", "חזקת ממון"],
  "target_authors": ["Rashi", "Tosafos", "Rosh"],
  "target_masechtos": ["Bava Metzia", "Bava Kamma"],
  "focus_terms": ["הבדל", "חילוק"],
  "topic_terms": ["חזקת הגוף", "חזקת ממון"],
  "trickle_direction": "both",
  "confidence": "high"
}
```

#### STEP 3: SEARCH (`step_three_search.py` - V5)

**Goal:** Execute the search strategy and return organized sources  
**Input:** `QueryAnalysis` from Step 2  
**Output:** `SearchResult` with hierarchically organized sources  
**Method:** V5 algorithm with topic-filtered commentary fetching

**V5 Key Innovations:**

1. **Proper Source Mapping**: Ran writes on Rif, not directly on Gemara
2. **Topic-Filtered Commentaries**: Only fetch commentaries on relevant segments
3. **Line-Level Targeting**: Score gemara segments, expand only high-scoring lines
4. **Better Category Matching**: Fix false positives (Likutei Moharan ≠ Ran)
5. **Author-Specific Fetching**: When asking for Ran's shittah, prioritize Ran sources

**The Two Main Algorithms:**

### A. NUANCE QUERY HANDLER (V5) - For Shittah/Comparison/Focus Queries

Used when: query_type = nuance/shittah/comparison/machlokes

**PHASE 1: FIND LANDMARK**

Goal: Identify the primary source that discusses this nuance

```
PHASE 1A: VERIFY GEMINI'S SUGGESTED LANDMARK
- If Gemini suggested a landmark:
  1. Check if ref exists in Sefaria
  2. Fetch the text
  3. Verify it contains BOTH:
     - Focus terms (the specific aspect)
     - Topic terms (the general concept)
  4. If verified: Use as landmark ✓
  5. If missing terms: Reject, move to 1B

PHASE 1B: DISCOVER VIA ACHRONIM
- Build search query from focus_terms + topic_terms
- Search Shulchan Aruch, Tur, Mishnah Berurah
- Extract citations to rishonim from search results
- Score each rishon candidate:
  * Fetch the rishon text
  * Calculate: focus_score + topic_score
  * Keywords in multi-word phrases: 3.0 points
  * Keywords in Aramaic constructs (דגופא): 3.0 points
  * Generic words (חזקה, ספק): 0.5 points
  * Focus terms: 2x multiplier
- Best candidate with BOTH focus + topic terms = landmark

RESULT: Either found landmark or confidence=low
```

**PHASE 2: TOPIC-FILTERED TRICKLE UP**

Goal: Fetch commentaries ONLY on segments discussing the topic

```
For each foundation ref (landmark + primary_refs):

  STEP A: ANALYZE SEGMENTS
  - Fetch the base text (e.g., Rashi on Bava Metzia 100a)
  - Split into segments (amud typically has 10-50 segments)
  - For each segment:
    * Check if contains focus_terms
    * Check if contains topic_terms
    * Calculate score:
      focus_score * 2 + topic_score
    * is_relevant = (score >= 3.0)
  
  STEP B: GET RELEVANT SEGMENT REFS
  - Build specific refs for relevant segments
  - Example: "Bava Metzia 100a:5" (segment 5 only)
  - Log: "Found 3/45 relevant segments"
  
  STEP C: FETCH COMMENTARIES ON RELEVANT SEGMENTS
  - For each relevant segment ref:
    * Get related texts (Sefaria API)
    * Filter by target_authors
    * Use SOURCE_NAME_MAP with EXCLUSION_PATTERNS:
      - "ran" → patterns: ["Ran on Rif", "Chiddushei HaRan"]
      - Exclusions: ["Likutei Moharan", "Derashot HaRan"]
    * Score commentary by focus terms
    * Only add if score >= 2.0 OR primary author
  
  - Sort by focus_score (highest first)

RESULT: Commentaries filtered to relevant segments only
```

**PHASE 3: AUTHOR-SPECIFIC FETCHING**

For shittah queries with primary_author:

```
For author in [primary_author, ...target_authors]:
  
  1. Get author info from RISHON_SEFARIA_MAP:
     - writes_on: "gemara" or "rif" or other
     - sefaria_prefix: "Rashi on" or "Ran on Rif"
     - patterns: ["Rashi on", "Rashi's Commentary"]
     - exclusions: ["Likutei Moharan"]
  
  2. Build correct refs:
     - If writes_on="gemara": "Rashi on Pesachim 6b"
     - If writes_on="rif": Search for "Ran Pesachim {topic}"
       (Rif has different daf numbers!)
  
  3. Fetch and score:
     - Verify contains focus_terms + topic_terms
     - Mark as is_primary=True
     - Add to author_sources[author]

RESULT: Primary author's commentary prioritized
```

**Output Structure:**
```python
SearchResult:
  landmark_source: Source         # The main source (Phase 1)
  foundation_stones: List[Source] # Landmark + primary refs
  primary_sources: List[Source]   # Target author commentaries
  commentary_sources: List[Source] # Topic-filtered commentaries
  author_sources: Dict[str, List[Source]]  # By author
  segments_analyzed: int          # Total segments checked
  segments_relevant: int          # Segments with topic
  landmark_discovery: LandmarkResult  # How we found it
```

### B. GENERAL QUERY HANDLER (V5) - For Topic/Question Queries

Used when: query_type = topic/question/halacha (non-nuance)

**This is the older algorithm, simpler:**

```
PHASE 1: VERIFY REFS
- For each ref_hint from Step 2:
  * If confidence="certain": Add to verified_refs
  * Else: Fetch text, verify contains keywords
  * Build foundation_stones list

PHASE 2: UNFILTERED TRICKLE UP
- For each foundation ref:
  * Get all related texts (no filtering)
  * Fetch target_authors
  * Return all commentaries
  
RESULT: Broader search, less filtering
```

**Note:** Most queries now route through nuance handler because V5 classifies shittah queries as nuance.

---

### SOURCE LEVEL HIERARCHY

Sources are organized in this order (trickle-up):

```
1. CHUMASH        - Biblical text
2. MISHNA         - Mishnaic text
3. GEMARA         - Talmudic discussion
4. RASHI          - Rashi's commentary
5. TOSFOS         - Tosafos
6. RISHONIM       - Ran, Rashba, Ritva, Ramban, Rosh, Meiri, etc.
7. RAMBAM         - Mishneh Torah
8. TUR            - Tur (pre-Shulchan Aruch)
9. SHULCHAN_ARUCH - Shulchan Aruch
10. NOSEI_KEILIM  - SA commentaries (Taz, Shach, MB, etc.)
11. ACHARONIM     - Later commentaries (Maharsha, Pnei Yehoshua, etc.)
12. OTHER         - Miscellaneous
```

---

### RISHON-TO-SEFARIA MAPPING (V5)

Critical for correct fetching:

```python
RISHON_SEFARIA_MAP = {
    "ran": {
        "patterns": ["Ran on Rif", "Chiddushei HaRan"],
        "sefaria_prefix": "Ran on Rif",
        "writes_on": "rif",  # NOT gemara!
        "fallback_search": "ran",
    },
    "rashi": {
        "patterns": ["Rashi on"],
        "sefaria_prefix": "Rashi on",
        "writes_on": "gemara",
    },
    "tosafos": {
        "patterns": ["Tosafot on", "Tosafos on"],
        "sefaria_prefix": "Tosafot on",
        "writes_on": "gemara",
    },
    # ... more rishonim
}

EXCLUSION_PATTERNS = {
    "ran": ["Likutei Moharan", "Derashot HaRan"],
    # Prevents false matches
}
```

---

### KEYWORD MATCHING & SCORING (V5)

**Normalization:**
```python
def normalize_for_search(text):
    1. Strip HTML tags
    2. Remove nikud
    3. Remove geresh/gershayim
    4. Normalize sofits (ם→מ, ן→נ, etc.)
    5. Collapse whitespace
```

**Variant Generation:**
```python
def generate_keyword_variants(keyword):
    - Smichut: הגוף ↔ תגוף
    - Spacing: דגופא ↔ ד גופא
    - Article: הגוף ↔ גוף
```

**Scoring:**
```python
def calculate_keyword_score(keywords_found, is_focus_term):
    For each keyword:
      - Multi-word phrase: 3.0 points
      - Aramaic construct (ד+...): 3.0 points
      - Generic word (חזקה, ספק): 0.5 points
      - Other single word: 1.5 points
      - If focus_term: multiply by 2.0
    
    Return: total score
```

**Verification:**
```python
def verify_text_contains_keywords(text, keywords, require_all=False, min_score=3.0):
    1. Normalize text
    2. Generate variants for each keyword
    3. Check each variant in text
    4. Calculate score
    5. Return: (verified, keywords_found, score)
```

---

### SEGMENT-LEVEL ANALYSIS (V5)

```python
def analyze_segments(sefaria_response, focus_terms, topic_terms):
    """
    Analyze each segment of a daf to find which contain the topic.
    """
    for idx, segment in enumerate(he_content):
        # Score this segment
        focus_score = score_keywords(segment, focus_terms)
        topic_score = score_keywords(segment, topic_terms)
        total_score = focus_score * 2 + topic_score
        
        is_relevant = (total_score >= 3.0)
        
        yield {
            "segment_index": idx,
            "segment_text": segment[:200],
            "focus_score": focus_score,
            "topic_score": topic_score,
            "total_score": total_score,
            "is_relevant": is_relevant
        }
```

---

### FALLBACKS & ERROR HANDLING

**If landmark not found:**
- Try Sefaria search API with search_topics
- Return low confidence with clarification

**If no commentaries found:**
- Expand search to broader masechtos
- Try without segment filtering
- Suggest user clarify query

**If Sefaria API fails:**
- Use cached responses if available
- Retry with exponential backoff
- Log error and continue with other sources

---

### OUTPUT FORMATTING

**Generated Files:**
1. **TXT**: Plain text with hierarchy markers
2. **HTML**: Formatted with Hebrew font, collapsible sections
3. **JSON**: Machine-readable (future)

**File Naming:**
```
sources_{query_slug}_{timestamp}.txt
sources_{query_slug}_{timestamp}.html
```

**Example Output Structure:**
```
================================================================================
OHR HANER - NUANCE QUERY RESULTS
================================================================================

Query: ran's shittah in bittul chometz
Generated: 2026-01-01T08:40:26
Total Sources: 15

────────────────────────────────────────
  NUANCE DETECTION
────────────────────────────────────────
Discovery Method: gemini_verified
Landmark: Pesachim 4b
Confidence: high
Reasoning: Contains focus terms and topic terms

================================================================================

────────────────────────────────────────
  📖 PRIMARY SOURCES (5 sources)
  Ran's specific commentary
────────────────────────────────────────

[1] Ran on Rif Pesachim
    רן על הרי"ף פסחים
    Author: Ran
    Focus Score: 15.0
    
    ─── Hebrew ───
    [Hebrew text with ביטול חמץ highlighted...]
    
    ─── Relevance ───
    This is Ran's primary discussion of bittul chometz...

────────────────────────────────────────
  📚 SUPPORTING SOURCES (10 sources)
  Rishonim & Acharonim on this topic
────────────────────────────────────────

[2] Rashi on Pesachim 4b
    רש"י על פסחים ד׳ ע״ב
    
    [...]
```

---

## � Key Components & Supporting Systems

### Local Corpus (`local_corpus.py`) - V10

**Purpose:** Offline searching of Sefaria JSON export for discovery without API calls

**V10 Changes from V9:**
1. ✅ **Fixed siman extraction** - Skip non-digit keys instead of returning 0
2. ✅ **Tur nosei keilim** - Extract from Beis Yosef, Bach, Darchei Moshe
3. ✅ **Rambam nosei keilim** - Extract from Maggid Mishneh, Kesef Mishneh, Lechem Mishneh
4. ✅ **Triple citation extraction** - SA + Tur + Rambam citations
5. ✅ **Rishonim fallback** - For gemara searches, also check rishonim

**File Structure:**
```
C:/Projects/Sefaria-Export/json/
├── Halakhah/
│   ├── Mishneh Torah/
│   │   ├── Sefer Taharah/
│   │   │   ├── Mishneh Torah, Metamei Mishkav uMoshav.json
│   │   │   └── [Commentary files...]
│   │   └── [More sefarim...]
│   ├── Shulchan Arukh/
│   │   ├── Orach Chayim/
│   │   │   ├── Shulchan Arukh, Orach Chayim 1.json
│   │   │   ├── Mishnah Berurah on Shulchan Arukh, Orach Chayim 1.json
│   │   │   └── [More simanim...]
│   │   └── [Yoreh Deah, Choshen Mishpat, Even HaEzer...]
│   └── Tur/
│       ├── Orach Chayim/
│       │   ├── Tur, Orach Chayim.json
│       │   ├── Beit Yosef on Tur, Orach Chayim.json
│       │   └── [Bach, Darchei Moshe...]
│       └── [Other cheleks...]
├── Talmud/
│   └── Bavli/
│       ├── Berakhot/
│       │   ├── Berakhot.json
│       │   └── [Commentaries...]
│       └── [Other masechtos...]
└── [Tanakh, Midrash, etc...]
```

**Core Functions:**

```python
class LocalCorpus:
    def __init__(self, root_path: Path):
        """Initialize with Sefaria-Export/json path"""
        self.root_path = root_path
        self.sa_cache = {}  # Cache loaded JSON files
        self.tur_cache = {}
        self.rambam_cache = {}
    
    def search_shulchan_aruch(self, query: str, chelek: str = None) -> List[LocalSearchHit]:
        """
        Search all Shulchan Aruch simanim for query terms.
        
        Returns hits with: sefer, siman, seif, text_snippet, ref
        """
        
    def search_tur(self, query: str, chelek: str = None) -> List[LocalSearchHit]:
        """Search Tur simanim"""
        
    def search_rambam(self, query: str, sefer: str = None) -> List[LocalSearchHit]:
        """Search Rambam halachos"""
    
    def get_nosei_keilim_sa(self, chelek: str, siman: int) -> Dict[str, str]:
        """
        V10: Get all nosei keilim for an SA siman.
        
        Returns: {
            "Mishnah Berurah": "full text...",
            "Taz": "full text...",
            "Shach": "full text...",
            # etc.
        }
        """
    
    def get_nosei_keilim_tur(self, chelek: str, siman: int) -> Dict[str, str]:
        """
        V10: Get all nosei keilim for a Tur siman.
        
        Returns: {
            "Beit Yosef": "full text...",
            "Bach": "full text...",
            "Darchei Moshe": "full text...",
        }
        """
    
    def get_nosei_keilim_rambam(self, sefer: str, perek: str) -> Dict[str, str]:
        """
        V10: Get all nosei keilim for a Rambam perek.
        
        Returns: {
            "Maggid Mishneh": "full text...",
            "Kesef Mishneh": "full text...",
            "Lechem Mishneh": "full text...",
        }
        """
    
    def extract_gemara_citations(self, text: str) -> List[GemaraCitation]:
        """
        Extract all gemara citations from Hebrew text.
        
        Patterns:
        - "בבא מציעא דף ק׳"
        - "ב״מ ק׳ ע״א"
        - "פסחים דף ד׳ ע״ב"
        - Full spelled out names
        - Abbreviations
        
        Returns: List of GemaraCitation(masechta, daf, source_ref, confidence)
        """
```

**V10 Discovery Algorithm:**

```python
def discover_main_sugyos(corpus: LocalCorpus, query: str, masechta: str = None) -> List[Tuple[str, int]]:
    """
    V10: Find where a topic lives and extract gemara citations from ALL nosei keilim.
    
    Returns: List of (daf_ref, citation_count) sorted by frequency
    """
    
    # Step 1: Search SA for query
    sa_hits = corpus.search_shulchan_aruch(query)
    
    # Step 2: Search Tur for query
    tur_hits = corpus.search_tur(query)
    
    # Step 3: Search Rambam for query (V10 addition)
    rambam_hits = corpus.search_rambam(query)
    
    # Step 4: Extract citations from SA nosei keilim
    sa_citations = defaultdict(int)
    for hit in sa_hits[:20]:  # Top 20 SA simanim
        nosei_keilim = corpus.get_nosei_keilim_sa(hit.sefer, hit.siman)
        for nk_name, nk_text in nosei_keilim.items():
            citations = corpus.extract_gemara_citations(nk_text)
            for citation in citations:
                if not masechta or citation.masechta == masechta:
                    daf_ref = f"{citation.masechta} {citation.daf}"
                    sa_citations[daf_ref] += citation.confidence
    
    # Step 5: Extract citations from Tur nosei keilim (V10)
    tur_citations = defaultdict(int)
    for hit in tur_hits[:20]:
        nosei_keilim = corpus.get_nosei_keilim_tur(hit.sefer, hit.siman)
        for nk_name, nk_text in nosei_keilim.items():
            citations = corpus.extract_gemara_citations(nk_text)
            for citation in citations:
                if not masechta or citation.masechta == masechta:
                    daf_ref = f"{citation.masechta} {citation.daf}"
                    tur_citations[daf_ref] += citation.confidence
    
    # Step 6: Extract citations from Rambam nosei keilim (V10)
    rambam_citations = defaultdict(int)
    for hit in rambam_hits[:20]:
        nosei_keilim = corpus.get_nosei_keilim_rambam(hit.sefer, hit.perek)
        for nk_name, nk_text in nosei_keilim.items():
            citations = corpus.extract_gemara_citations(nk_text)
            for citation in citations:
                if not masechta or citation.masechta == masechta:
                    daf_ref = f"{citation.masechta} {citation.daf}"
                    rambam_citations[daf_ref] += citation.confidence
    
    # Step 7: Combine all citations with weighting
    combined_citations = defaultdict(float)
    for daf_ref, count in sa_citations.items():
        combined_citations[daf_ref] += count * 1.0  # SA weight
    for daf_ref, count in tur_citations.items():
        combined_citations[daf_ref] += count * 0.9  # Tur weight
    for daf_ref, count in rambam_citations.items():
        combined_citations[daf_ref] += count * 0.8  # Rambam weight
    
    # Step 8: Sort by frequency
    sorted_dapim = sorted(combined_citations.items(), key=lambda x: x[1], reverse=True)
    
    return sorted_dapim[:10]  # Top 10 dapim
```

**Masechta Mapping:**

```python
MASECHTA_MAP = {
    'ברכות': 'Berakhot',
    'שבת': 'Shabbat',
    'עירובין': 'Eruvin',
    'פסחים': 'Pesachim',
    'בבא קמא': 'Bava Kamma',
    'ב"ק': 'Bava Kamma',
    'בבא מציעא': 'Bava Metzia',
    'ב"מ': 'Bava Metzia',
    # ... 60+ masechtos with abbreviations
}

MASECHTA_MAX_DAF = {
    'Berakhot': 64,
    'Shabbat': 157,
    'Pesachim': 121,
    'Bava Kamma': 119,
    # ... validation to filter garbage citations
}
```

**V10 Fix Details:**

**Bug in V9:**
```python
# V9 - WRONG: Would return siman 0 for non-digit keys
def extract_siman(key):
    match = re.match(r'(\d+)', key)
    return int(match.group(1)) if match else 0  # ❌ Returns 0!

# V10 - FIXED: Skip non-siman entries
def extract_siman(key):
    match = re.match(r'(\d+)', key)
    return int(match.group(1)) if match else None  # ✅ Returns None

# Usage:
siman = extract_siman(key)
if siman is None:
    continue  # Skip this entry
```

This fixed SA/Tur/Rambam parsing where intro sections had keys like "Introduction" or "Contents".

---

### Torah Authors Master KB (`torah_authors_master.py`)

**Purpose:** Comprehensive knowledge base of 600+ Torah authors/commentaries

**Structure:**
```python
TORAH_AUTHORS = [
    {
        "name": "Ran",
        "hebrew": "רן",
        "full_name": "Rabbeinu Nissim",
        "hebrew_full": "רבינו נסים",
        "variations": ["רבינו ניסים", "ר״ן", "הרן"],
        "sefaria_names": ["Ran on Rif", "Chiddushei HaRan"],
        "time_period": "rishonim",
        "lived": "1320-1376",
        "primary_works": ["Commentary on Rif", "Chiddushei HaRan"],
        "writes_on": "rif",  # Critical for Step 3!
    },
    {
        "name": "Rashi",
        "hebrew": "רש״י",
        "full_name": "Rabbi Shlomo Yitzchaki",
        "variations": ["רש\"י", "רשי"],
        "sefaria_names": ["Rashi on"],
        "time_period": "rishonim",
        "writes_on": "gemara",
    },
    # ... 600+ more entries
]
```

**Categories:**
- **Tannaim**: Mishna authors
- **Amoraim**: Gemara sages
- **Geonim**: Post-Talmudic authorities
- **Rishonim**: Rashi, Tosafos, Rambam, Ramban, Rashba, Ritva, Ran, Rosh, Meiri, etc.
- **Acharonim**: Maharsha, Maharam Schiff, Pnei Yehoshua, Ketzos, Nesivos, etc.
- **Contemporary**: Chazon Ish, R' Akiva Eiger, Netziv, etc.
- **Nosei Keilim**: Taz, Shach, Mishnah Berurah, Aruch HaShulchan, etc.

**Key Functions:**
```python
def is_author(term: str) -> bool:
    """Check if term is an author name"""

def get_author_matches(term: str) -> List[Dict]:
    """Get all matching author records"""

def normalize_author_name(term: str) -> str:
    """Normalize to canonical form"""

def get_sefaria_pattern(author: str) -> str:
    """Get Sefaria search pattern for author"""
```

**Usage in Pipeline:**
- **Step 1**: Detect author names in queries
- **Step 2**: Separate authors from topics
- **Step 3**: Map to correct Sefaria refs

---

### Sefaria Client (`tools/sefaria_client.py`)

**Purpose:** Async wrapper for Sefaria API with intelligent caching

**Key Features:**
1. **JSON File Caching**: Hash-based cache prevents duplicate API calls
2. **Rate Limiting**: Respect Sefaria's API limits
3. **Retry Logic**: Exponential backoff on failures
4. **Batch Requests**: Process multiple refs concurrently

**API Methods:**
```python
class SefariaClient:
    async def get_text(self, ref: str) -> Optional[Dict]:
        """
        Fetch text for a reference.
        
        Cache key: hash(f"text_{ref}")
        Cache location: cache/sefaria_v2/{hash}.json
        """
    
    async def get_related(self, ref: str) -> Optional[Dict]:
        """Get related texts (commentaries, connections)"""
    
    async def get_links(self, ref: str) -> Optional[List]:
        """Get all links for a ref"""
    
    async def search(self, query: str, filters: Dict = None) -> Optional[Dict]:
        """
        Search Sefaria corpus.
        
        Params:
        - query: Search terms
        - filters: {"filters": ["Talmud", "Bavli"]}
        """
    
    async def validate_ref(self, ref: str) -> bool:
        """Check if ref exists"""
    
    async def batch_validate(self, refs: List[str]) -> Dict[str, bool]:
        """Validate multiple refs concurrently"""
```

**Caching Strategy:**
```python
def get_cache_path(api_type: str, params: Dict) -> Path:
    # Create deterministic hash
    cache_key = f"{api_type}_{json.dumps(params, sort_keys=True)}"
    cache_hash = hashlib.sha256(cache_key.encode()).hexdigest()[:16]
    
    return CACHE_DIR / f"{cache_hash}.json"

async def get_text(self, ref: str):
    cache_path = get_cache_path("text", {"ref": ref})
    
    # Check cache first
    if cache_path.exists():
        return json.loads(cache_path.read_text())
    
    # Fetch from API
    response = await self.session.get(f"{API_URL}/texts/{ref}")
    data = await response.json()
    
    # Save to cache
    cache_path.write_text(json.dumps(data, ensure_ascii=False))
    
    return data
```

---

### Transliteration Map (`tools/transliteration_map.py`)

**Purpose:** Rule-based Hebrew ↔ transliteration engine

**Consonant Mappings:**
```python
CONSONANT_MAP = {
    'א': ['a', 'e', 'i', 'o', 'u', ''],
    'ב': ['b', 'v'],
    'ג': ['g'],
    'ד': ['d'],
    'ה': ['h', ''],
    'ו': ['v', 'u', 'o', 'w'],
    'ז': ['z'],
    'ח': ['ch', 'kh', 'h'],
    'ט': ['t'],
    'י': ['y', 'i', ''],
    'כ': ['k', 'kh', 'ch'],
    'ך': ['kh', 'ch', 'k'],
    'ל': ['l'],
    'מ': ['m'],
    'ם': ['m'],
    'נ': ['n'],
    'ן': ['n'],
    'ס': ['s'],
    'ע': ['a', 'e', 'i', 'o', 'u', ''],
    'פ': ['p', 'f', 'ph'],
    'ף': ['f', 'ph'],
    'צ': ['tz', 'ts', 'z'],
    'ץ': ['tz', 'ts', 'z'],
    'ק': ['k', 'q'],
    'ר': ['r'],
    'ש': ['sh', 's'],
    'ת': ['t', 's', 'th'],
}
```

**Prefix Detection:**
```python
PREFIXES = {
    'ה': ['ha', 'he', 'h'],      # The
    'ו': ['ve', 'va', 'u', 'v'], # And
    'ב': ['be', 'ba', 'b'],      # In
    'כ': ['ke', 'ka', 'k'],      # Like
    'ל': ['le', 'la', 'l'],      # To
    'מ': ['me', 'mi', 'm'],      # From
    'ש': ['she', 'sha', 's'],    # That/which
}
```

**Special Rules:**
1. **Smichut Forms**: haguf → הגוף, chezkas → חזקת
2. **Sofit Normalization**: ם↔מ, ן↔נ, ך↔כ, ף↔פ, ץ↔צ
3. **Aramaic Endings**: -ta (תא-), -sa (סא-), -a (א-)
4. **Doubled Letters**: gemara → גמרא OR גממרא
5. **Vowel Stripping**: Often ignore vowels entirely

**Variant Generation:**
```python
def transliteration_to_hebrew(trans: str) -> List[str]:
    """
    Generate all possible Hebrew spellings.
    
    Example: "migu" →
    - מיגו (most common)
    - מיגוא
    - מיגיו
    - מגו
    - etc.
    
    Returns: 10-50 variants sorted by likelihood
    """
```

---

### Output Formatter (`source_output.py`)

**Purpose:** Generate TXT and HTML output files

**TXT Format:**
```
================================================================================
OHR HANER - NUANCE QUERY RESULTS
================================================================================

Query: {original_query}
Generated: {timestamp}
Total Sources: {count}

[Metadata section...]

================================================================================

────────────────────────────────────────
  📖 PRIMARY SOURCES (X sources)
────────────────────────────────────────

[1] {ref}
    {he_ref}
    Author: {author}
    Focus Score: {score}
    
    ─── Hebrew ───
    {hebrew_text}
    
    ─── English ───
    {english_text}
    
    ─── Relevance ───
    {relevance_note}

────────────────────────────────────────────────────────────

[2] ...
```

**HTML Format:**
- Bootstrap styling
- Hebrew text with proper RTL
- Collapsible sections
- Syntax highlighting
- Responsive design

---

### Configuration (`config.py`)

**Purpose:** Centralized settings via Pydantic + environment variables

```python
class Settings(BaseSettings):
    # API Keys
    gemini_api_key: str  # Required
    
    # App Settings
    app_name: str = "Marei Mekomos"
    app_version: str = "7.0.0"
    environment: str = "production"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:5173,..."
    
    # Sefaria
    sefaria_base_url: str = "https://www.sefaria.org/api"
    sefaria_timeout: int = 30
    sefaria_max_retries: int = 3
    
    # Caching
    use_cache: bool = True
    cache_dir: Path = Path(__file__).parent / "cache"
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

**Usage:**
```python
from config import get_settings

settings = get_settings()  # Singleton
api_key = settings.gemini_api_key
```

```
marei-mekomos/
├── backend/
│   ├── step_one_decipher.py      # Step 1: Transliteration → Hebrew
│   ├── step_two_understand.py    # Step 2: Gemini query analysis
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
│   │   └── gemini/              # Gemini API cache
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
├── GEMINI_CONTEXT.md           # Gemini API context
└── PROJECT_CONTEXT.md          # This file
```

---

## 🔧 Technology Stack

### Backend
- **Python 3.9+**
- **FastAPI** - REST API framework
- **Google Gemini** - Query analysis (Step 2)
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
    reasoning: str                      # Gemini's reasoning
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
GEMINI_API_KEY=your-api-key-here
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
mkdir -p cache/sefaria_v2 cache/gemini
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

### Issue: "Gemini returned wrong search method"
**Cause:** Query type not properly detected  
**Debug:**
1. Check Step 2 `query_type` classification
2. For comparisons/shittah/machlokes, should force `trickle_down` (V6+)
3. Check Gemini's `reasoning` field
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
[UNDERSTAND] Gemini raw response: {...}
[UNDERSTAND] Final QueryAnalysis:
  INYAN: ['ביטול חמץ']
  WHERE: ['Pesachim']
  WHOSE: ['Ran', 'Rashi', 'Tosafos']
  METHOD: trickle_down
```

**Step 3:**
```
[STEP 3: SEARCH] V8.1 Trickle-Down
  All topics from Gemini: ['ביטול חמץ', 'חיוב ביטול']
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

## � Getting Started & Development Workflow

### Prerequisites

1. **Python 3.9+** installed
2. **Gemini API Key** from https://aistudio.google.com/apikey
3. **Optional**: Sefaria Export for offline corpus (download from Sefaria)

### Initial Setup

```powershell
# 1. Clone repository
cd C:\Projects\marei-mekomos

# 2. Create virtual environment (recommended)
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
cd backend
pip install -r requirements.txt

# 4. Create .env file
New-Item .env -ItemType File
Add-Content .env "GEMINI_API_KEY=your-api-key-here"
Add-Content .env "ENVIRONMENT=development"
Add-Content .env "LOG_LEVEL=DEBUG"

# 5. Create necessary directories
New-Item -ItemType Directory -Force cache\sefaria_v2, cache\gemini, logs, output

# 6. Optional: Download Sefaria Export
# Download from https://github.com/Sefaria/Sefaria-Export
# Extract to C:\Projects\Sefaria-Export\
```

### Running the System

#### Option 1: Interactive Console (Recommended for Development)

```powershell
cd backend
python console_full_pipeline.py
```

**Interactive Commands:**
- Just type your query: `migu`
- `mode` - Switch between steps (1, 1+2, or 1+2+3)
- `debug` - Toggle debug logging
- `q` or `quit` - Exit

**Example Session:**
```
=== Ohr Haner Console ===
Current mode: Full Pipeline (Steps 1+2+3)

> what is the rans shittah in bittul chometz

[STEP 1: DECIPHER]
  Found: רן, ביטול חמץ
  Confidence: HIGH

[STEP 2: UNDERSTAND]
  Query Type: nuance (shittah)
  Search Topics: ['ביטול חמץ']
  Target Authors: ['Ran', 'Rashi', 'Tosafos']
  Method: topic-filtered with author focus

[STEP 3: SEARCH]
  Discovering landmark...
  Found: Pesachim 4b
  Fetching Ran's commentary...
  Found 5 primary sources, 8 supporting sources

Results saved to: output/sources_rans_shittah_in_bittul_chometz_20260101_123045.html

> q
Goodbye!
```

#### Option 2: API Server

```powershell
# Terminal 1: Start backend
cd backend
python api_server_v7.py

# Output:
# INFO: Marei Mekomos API Server Starting
# INFO: Uvicorn running on http://0.0.0.0:8000
```

**API Endpoints:**
- `POST /decipher` - Step 1 only
- `POST /decipher/confirm` - User confirms transliteration
- `POST /decipher/reject` - User rejects transliteration
- `POST /search` - Full pipeline (1+2+3)
- `GET /health` - Health check

**Example API Call:**
```powershell
# PowerShell
$body = @{
    query = "what is the rans shittah in bittul chometz"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/search" -Body $body -ContentType "application/json"
```

#### Option 3: Frontend + Backend

```powershell
# Terminal 1: Backend
cd backend
python api_server_v7.py

# Terminal 2: Frontend
cd frontend
npm install
npm run dev

# Access: http://localhost:5173
```

---

## 🐛 Debugging & Troubleshooting

### Enable Debug Logging

**Console:**
```python
# In console_full_pipeline.py
setup_console_logging(debug=True)
```

**API Server:**
```bash
# In .env
LOG_LEVEL=DEBUG
```

### Common Issues

#### Issue 1: "No Hebrew terms found"

**Symptom:** Step 1 returns UNKNOWN confidence

**Causes & Solutions:**
1. **Term not in dictionary**
   - Check: `backend/data/word_dictionary.json`
   - Fix: Add term manually or let validation add it
   
2. **Transliteration too ambiguous**
   - Example: "gg" could be anything
   - Fix: Use more standard transliteration or Hebrew directly
   
3. **Sefaria validation failing**
   - Check logs: `logs/marei_mekomos_*.log`
   - Look for "Sefaria validation returned 0 results"
   - Fix: Check internet connection, Sefaria API status

**Debug Steps:**
```python
# In step_one_decipher.py, add logging:
logger.debug(f"Generated variants: {variants}")
logger.debug(f"Validation scores: {scores}")
```

#### Issue 2: "Wrong masechta returned"

**Symptom:** Search returns sources from wrong tractate

**Causes & Solutions:**
1. **V8.1 intersection logic failing**
   - Check Step 2 `search_topics_hebrew` - too verbose (>3 words)?
   - Check logs for "INTERSECTION: 0 dapim"
   - Fix: Simplify search terms in Step 2

2. **Gemini misidentified masechta**
   - Check Step 2 `target_masechtos`
   - Fix: Add more context to query or use direct reference

3. **Local corpus missing**
   - Check if `C:/Projects/Sefaria-Export/json` exists
   - Fix: Download Sefaria export or rely on API only

**Debug Steps:**
```python
# Check what Step 2 returned
logger.info(f"Target masechtos: {analysis.target_masechtos}")
logger.info(f"Search topics: {analysis.search_topics_hebrew}")
```

### Issue: "Gemini returned wrong search method"

**Symptom:** Query uses trickle_up when should use trickle_down

**Cause:** Query type not properly detected

**Solutions:**
1. Check Step 2 `query_type` classification
2. For comparisons/shittah/machlokes, V5 should classify as NUANCE
3. Review Gemini's `reasoning` field
4. Check system prompt in `step_two_understand.py`

**Note:** Step 3 V5 often routes all queries through nuance handler anyway, so search_method is less critical now.

#### Issue 4: "No sources found"

**Symptoms:**
- SearchResult has 0 sources
- "No landmark found" message
- Empty output files

**Causes & Solutions:**
1. **Landmark verification failed**
   - Check: Does landmark exist in Sefaria?
   - Check: Does landmark contain focus_terms + topic_terms?
   - Fix: Gemini suggested bad landmark, discovery needed

2. **Topic-filtered search too restrictive**
   - Check: Are focus_terms too specific?
   - Check: Segment scoring threshold (min_score=3.0)
   - Fix: Lower threshold or broaden focus_terms

3. **Author not in RISHON_SEFARIA_MAP**
   - Check: Is target_author mapped correctly?
   - Fix: Add author to RISHON_SEFARIA_MAP in step_three_search.py

**Debug Steps:**
```python
# In step_three_search.py
logger.debug(f"Landmark result: {landmark_result}")
logger.debug(f"Segments analyzed: {segments_analyzed}")
logger.debug(f"Segments relevant: {segments_relevant}")
```

#### Issue 5: "API Timeout"

**Symptom:** "ClientTimeout" errors in logs

**Causes:**
- Sefaria API slow response
- Network issues
- Too many concurrent requests

**Solutions:**
```python
# In config.py, increase timeouts
sefaria_timeout: int = 60  # Default: 30
sefaria_max_retries: int = 5  # Default: 3
```

#### Issue 6: "Cache Corruption"

**Symptom:** Inconsistent results, errors reading cache

**Fix:**
```powershell
# Delete cache and rebuild
Remove-Item -Recurse backend\cache\sefaria_v2\*
Remove-Item -Recurse backend\cache\gemini\*
```

---

## 📊 Example Queries & Expected Flow

### Example 1: Simple Topic Query

**Input:** `migu`

**Expected Flow:**
```
STEP 1:
- Dictionary hit: מיגו
- Confidence: HIGH
- No clarification needed

STEP 2:
- query_type: topic
- search_topics: ["מיגו"]
- target_masechtos: ["Bava Kamma", "Bava Metzia", "Ketubot"]
- target_authors: ["Rashi", "Tosafos"]
- Method: general_query (not nuance)

STEP 3:
- Searches Sefaria for "מיגו"
- Returns gemara + Rashi + Tosafos
- Organized by SourceLevel

OUTPUT:
- 20-30 sources
- Gemara refs from BK, BM, Ketubot
- Rashi and Tosafos on those refs
```

### Example 2: Nuance Query (Shittah)

**Input:** `what is the rans shittah in bittul chometz`

**Expected Flow:**
```
STEP 1:
- Mixed query detection
- Author: רן
- Topic: ביטול חמץ
- Confidence: HIGH

STEP 2:
- query_type: nuance (V5: shittah → nuance)
- search_topics: ["ביטול חמץ"]  # NOT "רן"!
- target_authors: ["Ran", "Rashi", "Tosafos"]
- primary_author: "Ran"
- focus_terms: ["דעת הרן", "שיטת הרן"]
- topic_terms: ["ביטול חמץ", "חיוב ביטול"]
- suggested_landmark: "Pesachim 4b"
- Method: topic-filtered

STEP 3: (nuance_query_handler)
PHASE 1: Find Landmark
  - Verify "Pesachim 4b"
  - Check contains focus + topic terms
  - ✓ Verified

PHASE 2: Topic-Filtered Trickle Up
  - Analyze Pesachim 4b segments
  - Find segments mentioning "ביטול חמץ"
  - Fetch commentaries on those segments only
  - Filter by target_authors

PHASE 3: Author-Specific Fetch
  - Fetch Ran's commentary specifically
  - Know: Ran writes on Rif
  - Search for "Ran on Rif Pesachim" + topic
  - Mark as is_primary=True

OUTPUT:
- Landmark: Rashi on Pesachim 4b (if landmark is Rashi)
- Primary: 3-5 Ran sources with high focus_score
- Supporting: Rashi, Tosafos on same topic
- Total: 10-15 sources
```

### Example 3: Comparison Query

**Input:** `chezkas haguf vs chezkas mammon`

**Expected Flow:**
```
STEP 1:
- Two topics detected: חזקת הגוף, חזקת ממון
- Confidence: HIGH

STEP 2:
- query_type: comparison (→ nuance in V5)
- search_topics: ["חזקת הגוף", "חזקת ממון"]
- target_authors: ["Rashi", "Tosafos", "Rosh"]
- focus_terms: ["הבדל", "חילוק", "שונה"]
- topic_terms: ["חזקת הגוף", "חזקת ממון"]
- suggested_landmark: "Bava Metzia 100a"

STEP 3:
PHASE 1: Find Landmark
  - Verify BM 100a
  - Check for both topics
  - ✓ Found

PHASE 2: Topic-Filtered
  - Find segments discussing BOTH concepts
  - Fetch commentaries on those segments
  - Prioritize sources comparing them

PHASE 3: Multiple Authors
  - Fetch Rashi's view
  - Fetch Tosafos's view
  - Fetch Rosh's view
  - Group by author_sources

OUTPUT:
- Landmark: Gemara discussing both
- Primary: Rosh comparing them (15.0 score)
- Supporting: Rashi on each, Tosafos on each
- Organized to show comparison
- Total: 10-20 sources
```

### Example 4: Direct Reference

**Input:** `show me rashi on pesachim 4b`

**Expected Flow:**
```
STEP 1:
- Author: רש"י
- Masechta: פסחים
- Daf: 4b
- Confidence: HIGH

STEP 2:
- query_type: source_request
- target_refs: ["Pesachim 4b"]
- target_authors: ["Rashi"]
- Method: direct

STEP 3:
- Direct fetch: "Rashi on Pesachim 4b"
- No search needed
- Return immediately

OUTPUT:
- Single source: Rashi on Pesachim 4b
- Full text
```

---

## 📝 Recent Development History

### January 1, 2026 - Current State

**Completed Work:**
- ✅ V10 Local Corpus with Tur & Rambam nosei keilim
- ✅ V5 Step 3 with topic-filtered commentary fetching
- ✅ V5 Step 2 with shittah → nuance classification
- ✅ Proper Ran on Rif mapping
- ✅ Segment-level analysis for focused fetching
- ✅ Author-specific fetching with priority
- ✅ EXCLUSION_PATTERNS to prevent false matches
- ✅ Comprehensive PROJECT_CONTEXT.md update

**Recent Example Queries (from output/ directory):**
1. `bari vishema beissurin` - Nuance query ✓
2. `ben azzai mehalech keomed dami` - Topic query ✓
3. `chezkas haguf vs chezkas mammon` - Comparison ✓
4. `mitzvas tashbisu` - Halacha query ✓
5. `what is the rans shittah in bittul chometz` - Shittah query ✓

**Current Challenges:**
- Frontend needs more development
- No tests directory yet (needs creation)
- Vector search/embeddings not implemented
- No PDF export yet

### December 2025 - Major Developments

- V8.1 intersection logic for multi-topic queries
- V10 local corpus with triple-source citations
- Comprehensive logging infrastructure
- Async-safe logging for concurrent operations

### Earlier Versions

- V6: Introduced trickle-down for complex queries
- V5: Topic-filtered commentary, author-specific fetch
- V4: Mixed query support
- V3: Dictionary-first deciphering
- V2: Basic pipeline
- V1: Initial prototype

---

## 🔮 Roadmap & Future Work

### Short-Term (Next 2-4 Weeks)

1. **Testing Infrastructure**
   - Create `backend/tests/` directory
   - Unit tests for Steps 1, 2, 3
   - Integration tests for full pipeline
   - Pytest configuration

2. **Frontend Development**
   - Improve UI/UX
   - Add step-by-step visualization
   - Source highlighting
   - Export buttons (TXT, HTML, PDF)

3. **Error Handling**
   - Better error messages
   - Graceful degradation
   - Retry strategies
   - User-friendly error display

### Medium-Term (1-3 Months)

1. **Vector Search Integration**
   - Generate embeddings for corpus
   - Semantic similarity search
   - Hybrid keyword + vector search
   - Store in `embeddings/` directory

2. **Performance Optimization**
   - Parallel source fetching
   - Intelligent cache warming
   - Streaming results
   - Database for metadata

3. **Advanced Features**
   - PDF export with Hebrew fonts
   - Citation graph visualization
   - Save/load searches
   - User preferences

### Long-Term (3-6 Months)

1. **User Accounts & Persistence**
   - User authentication
   - Saved searches
   - Personal libraries
   - Sharing capabilities

2. **Machine Learning**
   - Learn from user feedback
   - Improve transliteration accuracy
   - Query auto-complete
   - Suggested related searches

3. **Multi-Language Support**
   - Full Hebrew UI
   - English/Hebrew toggle
   - RTL layout

---

## 🎓 Learning Resources for New Developers

### Understanding the Codebase

**Start Here:**
1. Read this PROJECT_CONTEXT.md (you're here!)
2. Run `console_full_pipeline.py` with a simple query
3. Read `step_one_decipher.py` - simplest, most self-contained
4. Read `models.py` - understand all data structures
5. Read `step_two_understand.py` - see Gemini integration
6. Read `step_three_search.py` - most complex, leave for last

**Key Concepts to Understand:**
- **Transliteration**: How English phonetics map to Hebrew letters
- **Sefaria Structure**: How refs work (e.g., "Rashi on Pesachim 4b")
- **Async Programming**: Why we use `async`/`await`
- **Caching Strategy**: Why hash-based caching matters
- **Pydantic Models**: How validation works
- **Source Levels**: The hierarchy from Gemara → Rishonim → Achronim

### Python Concepts Used

- **Async/Await**: `asyncio`, `aiohttp` for concurrent API calls
- **Type Hints**: Full typing throughout for IDE support
- **Dataclasses**: Using Pydantic for validation + serialization
- **Context Managers**: `async with`, `asynccontextmanager`
- **Enum Classes**: For structured constants (QueryType, SourceLevel, etc.)
- **Pathlib**: Modern path handling instead of os.path
- **F-strings**: Modern string formatting
- **Comprehensions**: List/dict comprehensions for data transforms

### Torah Knowledge Needed

**Basic (Required):**
- Understand Gemara structure (masechta, daf, amud)
- Know major commentaries (Rashi, Tosafos, Ran, etc.)
- Familiar with Shulchan Aruch structure (chelek, siman, seif)
- Understand Hebrew alphabet and basic transliteration

**Advanced (Helpful):**
- Know which rishonim comment on what (e.g., Ran on Rif)
- Understand Sefaria's categorization system
- Familiar with aramaic terms and constructs
- Know common Torah keywords and their significance

### Recommended Development Tools

- **IDE**: VS Code with Python extension
- **Python**: 3.9+ with virtual environment
- **Terminal**: PowerShell or Windows Terminal
- **API Testing**: Postman or curl
- **JSON Viewer**: JSONLint or VS Code JSON extension
- **Hebrew Support**: Install Hebrew keyboard, use proper fonts

---

## 📞 Support & Contact

### Getting Help

1. **Check Logs**:
   - `backend/logging/logs/marei_mekomos_YYYYMMDD.log`
   - Search for ERROR or WARNING

2. **Common Error Messages**:
   - See "Debugging & Troubleshooting" section above

3. **Documentation**:
   - This file (PROJECT_CONTEXT.md)
   - README.md for user-facing docs
   - Docstrings in code

### Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/my-feature`
3. **Make changes with tests**
4. **Submit pull request**

### Code Review Checklist

- [ ] Type hints on all functions
- [ ] Docstrings for public functions
- [ ] Error handling with logging
- [ ] Tests for new features
- [ ] Updated PROJECT_CONTEXT.md if architecture changes
- [ ] Tested with example queries

---

## 📄 License & Credits

**License:** [To be determined - likely MIT or similar]

**Credits:**
- **Sefaria**: For the amazing free Torah API and corpus
- **Google**: For Gemini AI API
- **Contributors**: [List contributors]

**Built With:**
- Python, FastAPI, Pydantic, aiohttp
- React, Vite
- Gemini (Google)
- Sefaria API

---

## 📊 Project Statistics

**Current Stats (as of Jan 1, 2026):**
- Lines of Code: ~8,000+ (backend only)
- Number of Files: ~30 Python files
- Dictionary Size: 500+ terms
- Author KB: 600+ entries
- Cache Size: Varies (auto-grows)
- Local Corpus: ~4 GB (if using Sefaria export)
- Supported Masechtos: All Bavli (37 masechtos)
- Supported SA: All 4 cheleks
- Output Files Generated: 10+ test queries

**Performance Metrics:**
- Simple Query (cached): ~2-3 seconds
- Complex Query (uncached): ~10-20 seconds
- API Calls per Query: 5-30 (depending on caching)
- Cache Hit Rate: ~70% after warmup

---

**Document Version:** 2.0  
**Last Comprehensive Update:** January 1, 2026  
**Maintained By:** [Your Name/Team]  
**Purpose:** Complete onboarding document for new LLMs/developers

**This document is THE source of truth for the Ohr HaNer project.**

---

*May this tool bring clarity to Torah learning and honor to those who seek understanding.*
