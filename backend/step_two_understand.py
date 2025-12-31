"""
Step 2: UNDERSTAND - V3 Complete Rewrite
=========================================

PURPOSE:
    Take deciphered Hebrew terms and have Claude analyze the query to produce
    a comprehensive search plan. The output must contain everything Step 3 needs
    for PROGRAMMATIC verification (no additional Claude calls in Step 3).

V3 KEY CHANGES:
    1. Claude provides search_variants (Aramaic forms, gemara language, synonyms)
    2. Claude provides per-ref verification keywords
    3. Claude provides root_words for broad corpus searches
    4. Suggested refs are treated as HINTS with confidence levels
    5. Extensive logging for debugging
    6. SOLID principles: Single responsibility classes, dependency injection ready

ARCHITECTURE:
    - QueryAnalysis: Main output dataclass
    - RefHint: Individual ref suggestion with confidence and keywords
    - SearchVariants: All terms to search for (Hebrew, Aramaic, roots)
    - ClaudeAnalyzer: Handles Claude API interaction
    - PromptBuilder: Constructs prompts (separated for testability)

COST NOTE:
    This is the ONE Claude call in the pipeline. Step 3 should use this output
    for programmatic verification, eliminating N verification calls.
"""

import logging
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

# =============================================================================
#  LOGGING SETUP
# =============================================================================

logger = logging.getLogger(__name__)


def log_section(title: str) -> None:
    """Log a major section header."""
    border = "=" * 70
    logger.info("")
    logger.info(border)
    logger.info(f"  {title}")
    logger.info(border)


def log_subsection(title: str) -> None:
    """Log a subsection header."""
    logger.info("")
    logger.info("-" * 50)
    logger.info(f"  {title}")
    logger.info("-" * 50)


def log_dict(label: str, data: dict, indent: int = 2) -> None:
    """Log a dictionary with proper formatting."""
    prefix = " " * indent
    logger.info(f"{prefix}{label}:")
    for key, value in data.items():
        if isinstance(value, list):
            logger.info(f"{prefix}  {key}: {value}")
        elif isinstance(value, dict):
            logger.info(f"{prefix}  {key}:")
            for k2, v2 in value.items():
                logger.info(f"{prefix}    {k2}: {v2}")
        else:
            logger.info(f"{prefix}  {key}: {value}")


# =============================================================================
#  ENUMS
# =============================================================================

class QueryType(str, Enum):
    """Classification of query intent."""
    TOPIC = "topic"                    # General exploration of a concept
    QUESTION = "question"              # Specific question about a topic
    SOURCE_REQUEST = "source_request"  # Direct ref lookup ("show me X on Y")
    COMPARISON = "comparison"          # Compare multiple shittos/concepts
    SHITTAH = "shittah"               # One author's specific view
    SUGYA = "sugya"                   # Full sugya exploration
    PASUK = "pasuk"                   # Chumash verse related
    CHUMASH_SUGYA = "chumash_sugya"   # Topic rooted in Chumash
    HALACHA = "halacha"               # Practical halacha lookup
    MACHLOKES = "machlokes"           # Dispute/disagreement focus
    UNKNOWN = "unknown"


class FoundationType(str, Enum):
    """What type of source is the primary foundation?"""
    GEMARA = "gemara"
    MISHNA = "mishna"
    CHUMASH = "chumash"
    HALACHA_SA = "halacha_sa"         # Shulchan Aruch based
    HALACHA_RAMBAM = "halacha_rambam" # Rambam based
    MIDRASH = "midrash"
    UNKNOWN = "unknown"


class TrickleDirection(str, Enum):
    """Which direction to fetch related sources?"""
    UP = "up"       # Get later sources (commentaries on foundation)
    DOWN = "down"   # Get earlier sources (what foundation is based on)
    BOTH = "both"   # Both directions
    NONE = "none"   # Just the foundation itself


class Breadth(str, Enum):
    """How wide should the search be?"""
    NARROW = "narrow"         # Just main sugya (1-2 refs)
    STANDARD = "standard"     # Main sugya + key related (3-5 refs)
    WIDE = "wide"             # Multiple sugyos (5-10 refs)
    EXHAUSTIVE = "exhaustive" # Everything findable


class ConfidenceLevel(str, Enum):
    """Confidence in the analysis."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RefConfidence(str, Enum):
    """Confidence in a specific ref suggestion."""
    CERTAIN = "certain"     # Claude is very confident this ref discusses the topic
    LIKELY = "likely"       # Probably discusses it
    POSSIBLE = "possible"   # Might discuss it, needs verification
    GUESS = "guess"         # Best guess, definitely needs verification


# =============================================================================
#  DATA STRUCTURES
# =============================================================================

@dataclass
class RefHint:
    """
    A single ref suggestion from Claude with verification data.
    
    This is a HINT, not truth. Step 3 will verify using the keywords.
    """
    ref: str                              # e.g., "Ketubot 76b"
    confidence: RefConfidence             # How confident is Claude?
    
    # Keywords to search for in this ref's text to verify relevance
    verification_keywords: List[str] = field(default_factory=list)
    
    # Why Claude thinks this ref is relevant
    reasoning: str = ""
    
    # Buffer recommendation (how many dapim/simanim to check around this)
    buffer_size: int = 1
    
    def __post_init__(self):
        """Ensure confidence is RefConfidence enum."""
        if isinstance(self.confidence, str):
            try:
                self.confidence = RefConfidence(self.confidence.lower())
            except ValueError:
                self.confidence = RefConfidence.POSSIBLE


@dataclass
class SearchVariants:
    """
    All the different forms of the search terms.
    
    The gemara doesn't use modern Hebrew - it uses Aramaic and Mishnaic Hebrew.
    This structure holds all variants for comprehensive searching.
    """
    # Primary Hebrew terms (what user/Step 1 provided)
    primary_hebrew: List[str] = field(default_factory=list)
    
    # Aramaic equivalents (e.g., חזקת הגוף → חזקה דגופא)
    aramaic_forms: List[str] = field(default_factory=list)
    
    # Gemara/Mishnaic language (how the concept appears in Talmudic text)
    gemara_language: List[str] = field(default_factory=list)
    
    # Root words for broad searching (e.g., חזקה, גוף, ממון)
    root_words: List[str] = field(default_factory=list)
    
    # Related terms that might appear nearby (not synonyms, but associated)
    related_terms: List[str] = field(default_factory=list)
    
    def get_all_search_terms(self) -> List[str]:
        """Get all unique search terms for corpus searching."""
        all_terms = (
            self.primary_hebrew +
            self.aramaic_forms +
            self.gemara_language +
            self.root_words +
            self.related_terms
        )
        # Deduplicate while preserving order
        seen = set()
        result = []
        for term in all_terms:
            if term and term not in seen:
                seen.add(term)
                result.append(term)
        return result
    
    def get_high_confidence_terms(self) -> List[str]:
        """Get terms most likely to appear (primary + aramaic + gemara)."""
        return list(set(
            self.primary_hebrew +
            self.aramaic_forms +
            self.gemara_language
        ))


@dataclass
class QueryAnalysis:
    """
    Complete analysis of a Torah query - V3.
    
    This is the output of Step 2 and input to Step 3.
    Contains everything needed for programmatic verification.
    """
    # Original input
    original_query: str
    hebrew_terms_from_step1: List[str] = field(default_factory=list)
    
    # =========================================================================
    # CLASSIFICATION
    # =========================================================================
    query_type: QueryType = QueryType.UNKNOWN
    foundation_type: FoundationType = FoundationType.UNKNOWN
    breadth: Breadth = Breadth.STANDARD
    trickle_direction: TrickleDirection = TrickleDirection.UP
    
    # =========================================================================
    # SEARCH PLAN
    # =========================================================================
    
    # Ref hints from Claude (to be verified by Step 3)
    ref_hints: List[RefHint] = field(default_factory=list)
    
    # All search variants for corpus searching
    search_variants: SearchVariants = field(default_factory=SearchVariants)
    
    # Human-readable description of the topic
    inyan_description: str = ""
    
    # =========================================================================
    # TARGET SOURCES
    # =========================================================================
    
    # Which commentaries/sources to fetch after finding foundation
    target_sources: List[str] = field(default_factory=list)
    # e.g., ["gemara", "rashi", "tosafos", "ran", "ketzos"]
    
    # For halacha queries: which simanim to check
    target_simanim: List[str] = field(default_factory=list)
    
    # For halacha queries: which chelek (OC, YD, EH, CM)
    target_chelek: Optional[str] = None
    
    # =========================================================================
    # CONFIDENCE & CLARIFICATION
    # =========================================================================
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    clarification_options: List[str] = field(default_factory=list)
    
    # =========================================================================
    # DEBUGGING
    # =========================================================================
    reasoning: str = ""
    raw_claude_response: Optional[str] = None
    processing_time_ms: int = 0
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def get_suggested_refs(self) -> List[str]:
        """Get just the ref strings (for backward compatibility)."""
        return [hint.ref for hint in self.ref_hints]
    
    def get_high_confidence_refs(self) -> List[RefHint]:
        """Get refs where Claude is certain or likely."""
        return [
            h for h in self.ref_hints 
            if h.confidence in [RefConfidence.CERTAIN, RefConfidence.LIKELY]
        ]
    
    def get_all_search_terms(self) -> List[str]:
        """Get all search terms from variants."""
        return self.search_variants.get_all_search_terms()


# =============================================================================
#  CLAUDE SYSTEM PROMPT - V3
# =============================================================================

CLAUDE_SYSTEM_PROMPT_V3 = """You are an expert Torah learning assistant for Ohr Haner, a marei mekomos (source finder) system.

YOUR MISSION: Understand what the user wants and provide a COMPREHENSIVE search plan.

## CRITICAL UNDERSTANDING

The gemara and rishonim do NOT use modern Hebrew terminology. They use:
- Aramaic (e.g., "חזקה דגופא" not "חזקת הגוף")
- Mishnaic Hebrew with different conjugations
- Case descriptions rather than abstract terms

Your job is to provide ALL the linguistic variants so our search can find the actual sources.

## OUTPUT REQUIREMENTS

### 1. REF HINTS (suggested_refs)
Give specific refs like "Ketubot 76b" (not just "Ketubot").
- Include confidence level for EACH ref
- Include verification_keywords for EACH ref (words that WILL appear in that text)
- Include buffer_size (how many dapim to check around it)

If you're not 100% sure but have a good idea, still give the ref with confidence="possible".
We WILL verify programmatically - better to give hints than nothing.

### 2. SEARCH VARIANTS (search_variants)
This is CRITICAL. Provide:
- primary_hebrew: The user's Hebrew terms
- aramaic_forms: Aramaic equivalents (דגופא not הגוף, דממונא not הממון)
- gemara_language: How the concept appears in Talmud (e.g., "אוקמה אחזקתה", "העמד גברא")
- root_words: Root words for broad search (חזקה, גוף, ממון)
- related_terms: Associated terms that appear nearby

### 3. SEFARIA SPELLING
Use Sefaria's exact spellings for refs:
- Ketubot (not Kesubos)
- Shabbat (not Shabbos)  
- Berakhot (not Berachos)
- Bava Batra (not Basra)

### 4. HONESTY
If you don't know where something is discussed:
- Set needs_clarification=true
- Provide a helpful clarification_question
- Don't make up refs

## OUTPUT FORMAT

Return ONLY valid JSON (no markdown, no explanation):
{
    "query_type": "topic|question|source_request|comparison|shittah|sugya|pasuk|chumash_sugya|halacha|machlokes",
    "foundation_type": "gemara|mishna|chumash|halacha_sa|halacha_rambam|midrash",
    "breadth": "narrow|standard|wide|exhaustive",
    "trickle_direction": "up|down|both|none",
    
    "suggested_refs": [
        {
            "ref": "Ketubot 76b",
            "confidence": "certain|likely|possible|guess",
            "verification_keywords": ["חזקה דגופא", "חזקה דממונא", "רבי יהושע"],
            "reasoning": "Main sugya comparing chezkas haguf and chezkas mammon",
            "buffer_size": 1
        }
    ],
    
    "search_variants": {
        "primary_hebrew": ["חזקת הגוף", "חזקת ממון"],
        "aramaic_forms": ["חזקה דגופא", "חזקה דממונא", "דגופא", "דממונא"],
        "gemara_language": ["אוקמה אחזקתה", "העמד הגוף על חזקתו", "העמד ממון על חזקתו"],
        "root_words": ["חזקה", "גוף", "ממון"],
        "related_terms": ["המוציא מחבירו", "ספק", "ראיה"]
    },
    
    "inyan_description": "Clear explanation of the topic in 1-2 sentences",
    
    "target_sources": ["gemara", "rashi", "tosafos", "ran", "rashba", "ketzos"],
    "target_simanim": [],
    "target_chelek": null,
    
    "confidence": "high|medium|low",
    "needs_clarification": false,
    "clarification_question": null,
    "clarification_options": [],
    
    "reasoning": "Detailed explanation of your analysis and why you chose these refs"
}

## EXAMPLES

### Example 1: Chazaka Comparison
Query: "chezkas haguf vs chezkas mammon"
- query_type: "comparison"
- foundation_type: "gemara"
- Main ref: Ketubot 76b (this is where רבא explicitly discusses אזיל בתר חזקה דגופא/דממונא)
- aramaic_forms MUST include: דגופא, דממונא (this is how it appears in gemara!)
- gemara_language: העמד הגוף על חזקתו, אוקמה אחזקתה

### Example 2: Migu
Query: "migu"
- query_type: "topic"  
- foundation_type: "gemara"
- Multiple refs: Ketubot 12b, Bava Metzia 3a, Bava Kamma 46a
- aramaic_forms: מיגו (same in Aramaic)
- gemara_language: מיגו דאי בעי, מיגו דיכול

### Example 3: Halacha Query
Query: "hilchos carrying on shabbos"
- query_type: "halacha"
- foundation_type: "halacha_sa"
- target_chelek: "oc"
- target_simanim: ["301", "308", "309"]
- Then trickle down to gemara sources"""


# =============================================================================
#  PROMPT BUILDER (Separated for testability)
# =============================================================================

class PromptBuilder:
    """
    Builds prompts for Claude analysis.
    
    Separated from ClaudeAnalyzer for:
    - Unit testing prompts without API calls
    - Easy prompt iteration
    - Dependency injection
    """
    
    @staticmethod
    def build_user_prompt(query: str, hebrew_terms: List[str]) -> str:
        """Build the user prompt for Claude."""
        prompt = f"""Analyze this Torah query and provide a COMPREHENSIVE search plan.

QUERY: {query}

HEBREW TERMS DETECTED: {hebrew_terms}

Remember:
1. Give SPECIFIC refs with confidence levels and verification keywords
2. Provide ALL linguistic variants (Aramaic, gemara language, roots)
3. The gemara uses ARAMAIC - include those forms!
4. If unsure, still give your best guess with confidence="possible"
5. Return ONLY valid JSON, no markdown formatting"""
        
        return prompt
    
    @staticmethod
    def get_system_prompt() -> str:
        """Get the system prompt."""
        return CLAUDE_SYSTEM_PROMPT_V3


# =============================================================================
#  RESPONSE PARSER
# =============================================================================

class ResponseParser:
    """
    Parses Claude's JSON response into QueryAnalysis.
    
    Handles:
    - JSON extraction from potentially wrapped responses
    - Enum parsing with fallbacks
    - Missing field defaults
    - Validation
    """
    
    @staticmethod
    def extract_json(raw_text: str) -> str:
        """Extract JSON from potentially wrapped response."""
        text = raw_text.strip()
        
        # Try to extract from markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        
        # Handle case where response starts with explanation
        if not text.startswith("{"):
            # Find first {
            start = text.find("{")
            if start != -1:
                text = text[start:]
        
        # Handle case where response has trailing content
        if not text.endswith("}"):
            # Find last }
            end = text.rfind("}")
            if end != -1:
                text = text[:end + 1]
        
        return text
    
    @staticmethod
    def parse_enum(value: Any, enum_class, default):
        """Safely parse an enum value with fallback."""
        if value is None:
            return default
        try:
            if isinstance(value, enum_class):
                return value
            return enum_class(str(value).lower())
        except (ValueError, KeyError):
            logger.warning(f"Unknown {enum_class.__name__} value: {value}, using default: {default}")
            return default
    
    @staticmethod
    def parse_ref_hints(suggested_refs: List) -> List[RefHint]:
        """Parse ref hints from Claude's response."""
        hints = []
        
        for item in suggested_refs:
            if isinstance(item, str):
                # Simple string ref (backward compatibility)
                hints.append(RefHint(
                    ref=item,
                    confidence=RefConfidence.POSSIBLE,
                    verification_keywords=[],
                    reasoning="",
                    buffer_size=1
                ))
            elif isinstance(item, dict):
                # Full RefHint dict
                hints.append(RefHint(
                    ref=item.get("ref", ""),
                    confidence=item.get("confidence", "possible"),
                    verification_keywords=item.get("verification_keywords", []),
                    reasoning=item.get("reasoning", ""),
                    buffer_size=item.get("buffer_size", 1)
                ))
        
        return hints
    
    @staticmethod
    def parse_search_variants(variants_dict: Dict) -> SearchVariants:
        """Parse search variants from Claude's response."""
        if not variants_dict:
            return SearchVariants()
        
        return SearchVariants(
            primary_hebrew=variants_dict.get("primary_hebrew", []),
            aramaic_forms=variants_dict.get("aramaic_forms", []),
            gemara_language=variants_dict.get("gemara_language", []),
            root_words=variants_dict.get("root_words", []),
            related_terms=variants_dict.get("related_terms", [])
        )
    
    def parse_response(
        self,
        raw_text: str,
        query: str,
        hebrew_terms: List[str]
    ) -> QueryAnalysis:
        """Parse Claude's response into QueryAnalysis."""
        log_subsection("PARSING CLAUDE RESPONSE")
        
        # Extract JSON
        json_text = self.extract_json(raw_text)
        logger.debug(f"Extracted JSON length: {len(json_text)} chars")
        
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.error(f"Raw text: {raw_text[:500]}...")
            
            # Return error analysis
            return QueryAnalysis(
                original_query=query,
                hebrew_terms_from_step1=hebrew_terms,
                confidence=ConfidenceLevel.LOW,
                needs_clarification=True,
                clarification_question="I had trouble analyzing your query. Could you rephrase it?",
                reasoning=f"JSON parse error: {e}",
                raw_claude_response=raw_text
            )
        
        # Log parsed data
        logger.info("Parsed JSON successfully")
        logger.debug(f"Keys in response: {list(data.keys())}")
        
        # Build QueryAnalysis
        analysis = QueryAnalysis(
            original_query=query,
            hebrew_terms_from_step1=hebrew_terms,
            
            # Classification
            query_type=self.parse_enum(data.get("query_type"), QueryType, QueryType.UNKNOWN),
            foundation_type=self.parse_enum(data.get("foundation_type"), FoundationType, FoundationType.UNKNOWN),
            breadth=self.parse_enum(data.get("breadth"), Breadth, Breadth.STANDARD),
            trickle_direction=self.parse_enum(data.get("trickle_direction"), TrickleDirection, TrickleDirection.UP),
            
            # Ref hints
            ref_hints=self.parse_ref_hints(data.get("suggested_refs", [])),
            
            # Search variants
            search_variants=self.parse_search_variants(data.get("search_variants", {})),
            
            # Description
            inyan_description=data.get("inyan_description", ""),
            
            # Target sources
            target_sources=data.get("target_sources", ["gemara", "rashi", "tosafos"]),
            target_simanim=data.get("target_simanim", []),
            target_chelek=data.get("target_chelek"),
            
            # Confidence
            confidence=self.parse_enum(data.get("confidence"), ConfidenceLevel, ConfidenceLevel.MEDIUM),
            needs_clarification=data.get("needs_clarification", False),
            clarification_question=data.get("clarification_question"),
            clarification_options=data.get("clarification_options", []),
            
            # Debugging
            reasoning=data.get("reasoning", ""),
            raw_claude_response=raw_text
        )
        
        # If no search variants provided, build from hebrew_terms
        if not analysis.search_variants.primary_hebrew and hebrew_terms:
            logger.warning("No search_variants from Claude, using hebrew_terms as fallback")
            analysis.search_variants.primary_hebrew = hebrew_terms
        
        return analysis


# =============================================================================
#  CLAUDE ANALYZER
# =============================================================================

class ClaudeAnalyzer:
    """
    Handles Claude API interaction for query analysis.
    
    Responsibilities:
    - API communication
    - Caching (optional)
    - Error handling
    - Timing/metrics
    """
    
    def __init__(self, api_key: str = None, model: str = "claude-sonnet-4-5-20250929"):
        """
        Initialize the analyzer.
        
        Args:
            api_key: Anthropic API key (or from env)
            model: Model to use
        """
        self.model = model
        self.prompt_builder = PromptBuilder()
        self.response_parser = ResponseParser()
        
        # Get API key
        if api_key:
            self.api_key = api_key
        else:
            # Try to get from config or environment
            try:
                from config import get_settings
                self.api_key = get_settings().anthropic_api_key
            except ImportError:
                import os
                self.api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        
        if not self.api_key:
            logger.warning("No Anthropic API key configured!")
        
        # Initialize client lazily
        self._client = None
    
    @property
    def client(self):
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            from anthropic import Anthropic
            self._client = Anthropic(api_key=self.api_key)
        return self._client
    
    async def analyze(self, query: str, hebrew_terms: List[str]) -> QueryAnalysis:
        """
        Analyze a query using Claude.
        
        Args:
            query: Original user query
            hebrew_terms: Hebrew terms from Step 1
            
        Returns:
            QueryAnalysis with complete search plan
        """
        log_section("STEP 2: UNDERSTAND (V3)")
        
        logger.info(f"Query: {query}")
        logger.info(f"Hebrew terms: {hebrew_terms}")
        
        # Build prompts
        system_prompt = self.prompt_builder.get_system_prompt()
        user_prompt = self.prompt_builder.build_user_prompt(query, hebrew_terms)
        
        logger.debug(f"System prompt length: {len(system_prompt)} chars")
        logger.debug(f"User prompt length: {len(user_prompt)} chars")
        
        # Call Claude
        log_subsection("CALLING CLAUDE API")
        start_time = datetime.now()
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=3000,
                temperature=0,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            
            elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.info(f"Claude response received in {elapsed_ms}ms")
            
            raw_text = response.content[0].text.strip()
            logger.info(f"Response length: {len(raw_text)} chars")
            logger.debug(f"Raw response:\n{raw_text}")
            
            # Parse response
            analysis = self.response_parser.parse_response(raw_text, query, hebrew_terms)
            analysis.processing_time_ms = elapsed_ms
            
            # Log results
            self._log_analysis_results(analysis)
            
            return analysis
            
        except Exception as e:
            elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.error(f"Claude API error after {elapsed_ms}ms: {e}")
            
            return QueryAnalysis(
                original_query=query,
                hebrew_terms_from_step1=hebrew_terms,
                confidence=ConfidenceLevel.LOW,
                needs_clarification=True,
                clarification_question="I encountered an error. Could you try rephrasing?",
                reasoning=f"API error: {e}",
                processing_time_ms=elapsed_ms
            )
    
    def _log_analysis_results(self, analysis: QueryAnalysis) -> None:
        """Log the analysis results in a readable format."""
        log_subsection("ANALYSIS RESULTS")
        
        logger.info(f"Query Type: {analysis.query_type.value}")
        logger.info(f"Foundation Type: {analysis.foundation_type.value}")
        logger.info(f"Breadth: {analysis.breadth.value}")
        logger.info(f"Trickle Direction: {analysis.trickle_direction.value}")
        logger.info(f"Confidence: {analysis.confidence.value}")
        
        if analysis.needs_clarification:
            logger.warning(f"NEEDS CLARIFICATION: {analysis.clarification_question}")
        
        # Log ref hints
        logger.info("")
        logger.info(f"REF HINTS ({len(analysis.ref_hints)}):")
        for hint in analysis.ref_hints:
            logger.info(f"  • {hint.ref} [{hint.confidence.value}]")
            logger.info(f"    Keywords: {hint.verification_keywords[:5]}")
            if hint.reasoning:
                logger.info(f"    Reason: {hint.reasoning[:80]}...")
        
        # Log search variants
        logger.info("")
        logger.info("SEARCH VARIANTS:")
        sv = analysis.search_variants
        logger.info(f"  Primary Hebrew: {sv.primary_hebrew}")
        logger.info(f"  Aramaic Forms: {sv.aramaic_forms}")
        logger.info(f"  Gemara Language: {sv.gemara_language}")
        logger.info(f"  Root Words: {sv.root_words}")
        logger.info(f"  Related Terms: {sv.related_terms}")
        
        # Log target sources
        logger.info("")
        logger.info(f"Target Sources: {analysis.target_sources}")
        if analysis.target_simanim:
            logger.info(f"Target Simanim: {analysis.target_simanim}")
        if analysis.target_chelek:
            logger.info(f"Target Chelek: {analysis.target_chelek}")
        
        # Log inyan description
        if analysis.inyan_description:
            logger.info("")
            logger.info(f"Inyan: {analysis.inyan_description}")


# =============================================================================
#  MAIN ENTRY POINT
# =============================================================================

# Singleton analyzer
_analyzer: Optional[ClaudeAnalyzer] = None


def get_analyzer() -> ClaudeAnalyzer:
    """Get or create the singleton analyzer."""
    global _analyzer
    if _analyzer is None:
        _analyzer = ClaudeAnalyzer()
    return _analyzer


async def understand(
    hebrew_terms: List[str] = None,
    query: str = None,
    decipher_result: Any = None
) -> QueryAnalysis:
    """
    Main entry point for Step 2: UNDERSTAND.
    
    Args:
        hebrew_terms: List of Hebrew terms from Step 1
        query: Original query string
        decipher_result: Optional DecipherResult from Step 1
        
    Returns:
        QueryAnalysis with complete search plan for Step 3
    """
    # Handle different input formats
    if decipher_result is not None:
        if hebrew_terms is None:
            hebrew_terms = getattr(decipher_result, 'hebrew_terms', []) or []
            hebrew_term = getattr(decipher_result, 'hebrew_term', None)
            if hebrew_term and hebrew_term not in hebrew_terms:
                hebrew_terms = [hebrew_term] + list(hebrew_terms)
        
        if query is None:
            query = getattr(decipher_result, 'original_query', '')
    
    # Ensure lists
    if hebrew_terms is None:
        hebrew_terms = []
    if not isinstance(hebrew_terms, list):
        hebrew_terms = list(hebrew_terms)
    
    # Validation
    if not hebrew_terms and not query:
        logger.warning("No input provided to understand()")
        return QueryAnalysis(
            original_query="",
            confidence=ConfidenceLevel.LOW,
            needs_clarification=True,
            clarification_question="What topic would you like to explore?"
        )
    
    # Use query from hebrew_terms if not provided
    if not query:
        query = " ".join(hebrew_terms)
    
    # Run analysis
    analyzer = get_analyzer()
    analysis = await analyzer.analyze(query, hebrew_terms)
    
    # Log completion
    log_section("STEP 2 COMPLETE")
    logger.info(f"Refs found: {len(analysis.ref_hints)}")
    logger.info(f"Search terms: {len(analysis.get_all_search_terms())}")
    logger.info(f"Needs clarification: {analysis.needs_clarification}")
    
    return analysis


# Alias for backward compatibility
run_step_two = understand
analyze_with_claude = understand  # Old name


# =============================================================================
#  EXPORTS
# =============================================================================

__all__ = [
    # Main function
    'understand',
    'run_step_two',
    'analyze_with_claude',
    
    # Data structures
    'QueryAnalysis',
    'RefHint',
    'SearchVariants',
    
    # Enums
    'QueryType',
    'FoundationType',
    'TrickleDirection',
    'Breadth',
    'ConfidenceLevel',
    'RefConfidence',
    
    # Components (for testing/extension)
    'ClaudeAnalyzer',
    'PromptBuilder',
    'ResponseParser',
    'get_analyzer',
]


# =============================================================================
#  CLI TESTING
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    # Setup logging for testing
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    async def test():
        test_queries = [
            ("chezkas haguf vs chezkas mammon", ["חזקת הגוף", "חזקת ממון"]),
            ("migu", ["מיגו"]),
        ]
        
        for query, hebrew_terms in test_queries:
            print(f"\n{'='*70}")
            print(f"TESTING: {query}")
            print(f"{'='*70}")
            
            result = await understand(hebrew_terms=hebrew_terms, query=query)
            
            print(f"\n--- RESULTS ---")
            print(f"Query Type: {result.query_type}")
            print(f"Foundation: {result.foundation_type}")
            print(f"Confidence: {result.confidence}")
            print(f"Refs: {[h.ref for h in result.ref_hints]}")
            print(f"All search terms: {result.get_all_search_terms()}")
            
            if result.needs_clarification:
                print(f"CLARIFICATION NEEDED: {result.clarification_question}")
    
    asyncio.run(test())