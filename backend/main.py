"""
Marei Mekomos Backend API - Version 6.0 "Living Knowledge"
==========================================================

PHILOSOPHY: "I don't want rigidness. The lists I gave you aren't final - 
they're starting points/resources. Ideally AI is smart and figures it out."

KEY CHANGES FROM V5:
1. LIVING RESOURCES - Claude reads from resources/ folder dynamically
2. CONTINUOUS LEARNING - Stores feedback, learns from successful patterns
3. MULTI-LAYER SEARCH - Chumash → Nach → Mishna → Gemara → Rishonim → SA → Acharonim
4. ADAPTIVE DEPTH - User can specify scope, or AI guesses from query
5. BETTER GEMARA TEXT - Smarter extraction from nested arrays

The resources/ folder is Claude's "brain" - add files and it gets smarter.
Nothing is hardcoded as FINAL - everything is a starting point.
"""

import os
import json
import httpx
import html
import re
import hashlib
import glob
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from anthropic import Anthropic
from typing import List, Optional, Dict, Set, Tuple, Any
from datetime import datetime
from enum import Enum

# Import our logging and caching
from logging_config import setup_logging, get_logger
from cache_manager import claude_cache, sefaria_cache

# Initialize logging
setup_logging()
logger = get_logger(__name__)


# =============================
# CONFIGURATION
# =============================

# Paths
BASE_DIR = Path(__file__).parent
RESOURCES_DIR = BASE_DIR / "resources"
KNOWLEDGE_DIR = RESOURCES_DIR / "knowledge"
FEEDBACK_DIR = RESOURCES_DIR / "feedback"

# Create dirs if they don't exist
KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)

# Settings
COST_SAVING_MODE = os.environ.get("COST_SAVING_MODE", "true").lower() == "true"
MAX_SOURCES_PER_LAYER = int(os.environ.get("MAX_SOURCES_PER_LAYER", "8"))
MAX_TOTAL_SOURCES = int(os.environ.get("MAX_TOTAL_SOURCES", "50"))

if COST_SAVING_MODE:
    logger.info("💰 COST_SAVING_MODE enabled")


# =============================
# SOURCE LAYERS (Comprehensive Coverage)
# =============================

class SourceLayer(str, Enum):
    """All layers of Torah sources - from Chumash to Acharonim"""
    CHUMASH = "Chumash"
    NACH = "Nach"
    MISHNA = "Mishna"
    GEMARA = "Gemara"
    RISHONIM = "Rishonim"
    SHULCHAN_ARUCH = "Shulchan Aruch"
    ACHARONIM = "Acharonim"


class QueryIntent(str, Enum):
    """Query intent affects which layers to emphasize"""
    LOMDUS = "lomdus"      # Deep analysis → emphasize Gemara + analytical Acharonim
    PSAK = "psak"          # Practical → emphasize SA + poskim
    MAKOR = "makor"        # Source-finding → find earliest source
    GENERAL = "general"    # Balanced across all layers


class SearchScope(str, Enum):
    """User-controlled search depth"""
    FOCUSED = "focused"    # Just Gemara + key Rishonim (faster)
    STANDARD = "standard"  # Gemara through SA (default)
    COMPREHENSIVE = "comprehensive"  # Everything - Chumash to Acharonim


# =============================
# LIVING KNOWLEDGE LOADER
# =============================

class KnowledgeLoader:
    """
    Loads resources from the knowledge/ folder dynamically.
    
    This is the "brain" - drop files in and Claude learns from them.
    Nothing is hardcoded as final - these are starting points.
    """
    
    def __init__(self, knowledge_dir: Path = KNOWLEDGE_DIR):
        self.knowledge_dir = knowledge_dir
        self._cache = {}
        self._last_load = None
    
    def load_all(self, force_refresh: bool = False) -> Dict[str, str]:
        """Load all knowledge files into memory"""
        # Check if we need to refresh (file changes or forced)
        current_files = set(self.knowledge_dir.rglob("*.*"))
        
        if not force_refresh and self._cache and self._last_load:
            # Simple cache - reload every 5 minutes
            if (datetime.now() - self._last_load).seconds < 300:
                return self._cache
        
        knowledge = {}
        
        for file_path in self.knowledge_dir.rglob("*.*"):
            if file_path.suffix in [".md", ".txt", ".json"]:
                try:
                    relative_path = file_path.relative_to(self.knowledge_dir)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    knowledge[str(relative_path)] = content
                    logger.debug(f"  Loaded knowledge: {relative_path}")
                except Exception as e:
                    logger.error(f"Error loading {file_path}: {e}")
        
        self._cache = knowledge
        self._last_load = datetime.now()
        logger.info(f"📚 Loaded {len(knowledge)} knowledge files from resources/")
        
        return knowledge
    
    def get_for_topic(self, topic: str, masechta: Optional[str] = None) -> str:
        """Get relevant knowledge for a specific topic/masechta"""
        all_knowledge = self.load_all()
        
        relevant = []
        topic_lower = topic.lower()
        masechta_lower = (masechta or "").lower()
        
        for path, content in all_knowledge.items():
            path_lower = path.lower()
            
            # Include if path matches topic or masechta
            if (topic_lower in path_lower or 
                masechta_lower in path_lower or
                "methodology" in path_lower):  # Always include methodology
                relevant.append(f"=== {path} ===\n{content}")
        
        return "\n\n".join(relevant) if relevant else ""
    
    def get_methodology(self) -> str:
        """Get just the methodology files"""
        all_knowledge = self.load_all()
        
        methodology = []
        for path, content in all_knowledge.items():
            if "methodology" in path.lower():
                methodology.append(content)
        
        return "\n\n".join(methodology)


# Global knowledge loader
knowledge_loader = KnowledgeLoader()


# =============================
# FEEDBACK STORAGE (Learning from Experience)
# =============================

class FeedbackStore:
    """
    Stores and retrieves search feedback for continuous learning.
    
    When a search works well or poorly, store it here.
    Claude uses this to improve future searches.
    """
    
    def __init__(self, feedback_dir: Path = FEEDBACK_DIR):
        self.feedback_dir = feedback_dir
        self.success_file = feedback_dir / "successful_searches.json"
        self.failure_file = feedback_dir / "failed_patterns.json"
    
    def _load_file(self, path: Path) -> List[dict]:
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_file(self, path: Path, data: List[dict]):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_success(self, query: str, sources: List[str], notes: str = ""):
        """Record a successful search pattern"""
        successes = self._load_file(self.success_file)
        successes.append({
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "sources": sources,
            "notes": notes
        })
        # Keep last 100
        successes = successes[-100:]
        self._save_file(self.success_file, successes)
        logger.info(f"✅ Recorded successful search: {query}")
    
    def add_failure(self, query: str, bad_sources: List[str], notes: str = ""):
        """Record what didn't work"""
        failures = self._load_file(self.failure_file)
        failures.append({
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "bad_sources": bad_sources,
            "notes": notes
        })
        failures = failures[-100:]
        self._save_file(self.failure_file, failures)
        logger.info(f"❌ Recorded failed pattern: {query}")
    
    def get_similar_successes(self, query: str, limit: int = 3) -> List[dict]:
        """Find similar past successful searches"""
        successes = self._load_file(self.success_file)
        
        # Simple keyword matching (could be improved with embeddings)
        query_words = set(query.lower().split())
        
        scored = []
        for s in successes:
            s_words = set(s["query"].lower().split())
            overlap = len(query_words & s_words)
            if overlap > 0:
                scored.append((overlap, s))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:limit]]
    
    def get_context_for_prompt(self, query: str) -> str:
        """Get feedback context to include in Claude's prompt"""
        similar = self.get_similar_successes(query)
        if not similar:
            return ""
        
        context = "PAST SUCCESSFUL SEARCHES (learn from these):\n"
        for s in similar:
            context += f"- Query: '{s['query']}' → Good sources: {', '.join(s['sources'][:5])}\n"
        
        return context


# Global feedback store
feedback_store = FeedbackStore()


# =============================
# SLUG TRANSLATION (Yeshivish → Sefaria)
# =============================

# Comprehensive masechta mapping (yeshivish transliteration)
MASECHTA_TRANSLATIONS = {
    # Seder Zeraim
    "brachos": "Berakhot", "berachos": "Berakhot", "brochos": "Berakhot",
    "berakhot": "Berakhot", "berakhos": "Berakhot", "ברכות": "Berakhot",
    
    # Seder Moed
    "shabbos": "Shabbat", "shabbat": "Shabbat", "שבת": "Shabbat",
    "eruvin": "Eruvin", "eiruvin": "Eruvin", "עירובין": "Eruvin",
    "pesachim": "Pesachim", "psachim": "Pesachim", "פסחים": "Pesachim",
    "shekalim": "Shekalim", "שקלים": "Shekalim",
    "yoma": "Yoma", "יומא": "Yoma",
    "sukkah": "Sukkah", "sukka": "Sukkah", "סוכה": "Sukkah",
    "beitzah": "Beitzah", "beitza": "Beitzah", "ביצה": "Beitzah",
    "rosh hashanah": "Rosh Hashanah", "rosh hashana": "Rosh Hashanah", 
    "ראש השנה": "Rosh Hashanah", "r\"h": "Rosh Hashanah",
    "taanis": "Taanit", "taanit": "Taanit", "תענית": "Taanit",
    "megillah": "Megillah", "מגילה": "Megillah",
    "moed katan": "Moed Katan", "mo\"k": "Moed Katan", "מועד קטן": "Moed Katan",
    "chagigah": "Chagigah", "חגיגה": "Chagigah",
    
    # Seder Nashim
    "yevamos": "Yevamot", "yevamot": "Yevamot", "יבמות": "Yevamot",
    "kesubos": "Ketubot", "kesuvos": "Ketubot", "ketubot": "Ketubot",
    "ketubos": "Ketubot", "כתובות": "Ketubot",
    "nedarim": "Nedarim", "נדרים": "Nedarim",
    "nazir": "Nazir", "נזיר": "Nazir",
    "sotah": "Sotah", "סוטה": "Sotah",
    "gittin": "Gittin", "gitin": "Gittin", "גיטין": "Gittin",
    "kiddushin": "Kiddushin", "קידושין": "Kiddushin",
    
    # Seder Nezikin
    "bava kamma": "Bava Kamma", "bava kama": "Bava Kamma", 
    "b\"k": "Bava Kamma", "בבא קמא": "Bava Kamma",
    "bava metzia": "Bava Metzia", "bava metziah": "Bava Metzia",
    "b\"m": "Bava Metzia", "בבא מציעא": "Bava Metzia",
    "bava basra": "Bava Batra", "bava batra": "Bava Batra",
    "b\"b": "Bava Batra", "בבא בתרא": "Bava Batra",
    "sanhedrin": "Sanhedrin", "סנהדרין": "Sanhedrin",
    "makkos": "Makkot", "makkot": "Makkot", "makos": "Makkot", "מכות": "Makkot",
    "shevuos": "Shevuot", "shevuot": "Shevuot", "שבועות": "Shevuot",
    "avodah zarah": "Avodah Zarah", "avoda zara": "Avodah Zarah",
    "a\"z": "Avodah Zarah", "עבודה זרה": "Avodah Zarah",
    "horayos": "Horayot", "horayot": "Horayot", "הוריות": "Horayot",
    
    # Seder Kodshim
    "zevachim": "Zevachim", "zvachim": "Zevachim", "זבחים": "Zevachim",
    "menachos": "Menachot", "menachot": "Menachot", "מנחות": "Menachot",
    "chulin": "Chullin", "chullin": "Chullin", "חולין": "Chullin",
    "bechoros": "Bekhorot", "bekhorot": "Bekhorot", "בכורות": "Bekhorot",
    "arachin": "Arakhin", "arakhin": "Arakhin", "ערכין": "Arakhin",
    "temurah": "Temurah", "תמורה": "Temurah",
    "kerisos": "Keritot", "kerisot": "Keritot", "keritot": "Keritot", "כריתות": "Keritot",
    "meilah": "Meilah", "מעילה": "Meilah",
    "tamid": "Tamid", "תמיד": "Tamid",
    "middos": "Middot", "middot": "Middot", "מדות": "Middot",
    "kinnim": "Kinnim", "קינים": "Kinnim",
    
    # Seder Taharos
    "niddah": "Niddah", "נדה": "Niddah",
}

# Rambam translations
RAMBAM_TRANSLATIONS = {
    "ishus": "Marriage", "hilchos ishus": "Marriage", "הלכות אישות": "Marriage",
    "ishut": "Marriage", "hilchot ishut": "Marriage",
    "geirushin": "Divorce", "hilchos geirushin": "Divorce",
    "yibum": "Levirate Marriage and Release",
    "chametz umatzah": "Leavened and Unleavened Bread",
    "chometz umatzah": "Leavened and Unleavened Bread",
    "hilchos chametz": "Leavened and Unleavened Bread",
    "shabbos": "Shabbat", "hilchos shabbos": "Shabbat",
    "issurei biah": "Forbidden Intercourse", "issurei bi'ah": "Forbidden Intercourse",
    "maachalos asuros": "Forbidden Foods",
    "shechitah": "Slaughter",
    "nedarim": "Vows",
    "nezirus": "Nazirite Vows",
    "arachin": "Valuations and Devoted Property",
    "kilayim": "Diverse Kinds",
    "matnos aniyim": "Gifts to the Poor",
    "shemitah": "Sabbatical Year and the Jubilee",
    "beis habechirah": "The Chosen House",
    "kiddush hachodesh": "Sanctification of the New Month",
    "taanis": "Fasts",
    "megillah": "Scroll of Esther",
    "chanukah": "Chanukah",
    "tefilah": "Prayer",
    "tefilin": "Tefillin, Mezuzah and the Torah Scroll",
    "tzitzis": "Fringes",
    "berachos": "Blessings",
    "milah": "Circumcision",
    "tumas meis": "Defilement by a Corpse",
    "parah adumah": "Red Heifer",
    "tumas tzaraas": "Defilement of Tzaraas",
    "metamei mishkav": "Those Who Defile Bedding",
    "shaar avos hatumah": "Other Sources of Defilement",
    "tumas ochlin": "Defilement of Foods",
    "keilim": "Vessels",
    "mikvaos": "Ritual Baths",
    "sanhedrin": "Sanhedrin and Penalties",
    "edus": "Testimony",
    "mamrim": "Rebels",
    "avel": "Mourning",
    "melachim": "Kings and Wars",
    "gezelah": "Robbery and Lost Property",
    "nizkei mamon": "Property Damage",
    "gneivah": "Theft",
    "chovel umazik": "One Who Injures",
    "rotzeach": "Murderer and Preservation of Life",
    "mechirah": "Sales",
    "zechiyah": "Ownerless Property",
    "shecheinim": "Neighbors",
    "shluchim": "Agents and Partners",
    "avadim": "Slaves",
    "sechirus": "Hiring",
    "sheelah ufikadon": "Borrowing and Deposit",
    "malveh": "Creditor and Debtor",
    "toen": "Plaintiff and Defendant",
    "nachalos": "Inheritances",
}

# Shulchan Aruch translations
SA_TRANSLATIONS = {
    "orach chaim": "Orach Chayim", "o\"c": "Orach Chayim", "oc": "Orach Chayim",
    "או\"ח": "Orach Chayim", "אורח חיים": "Orach Chayim",
    "yoreh deah": "Yoreh De'ah", "y\"d": "Yoreh De'ah", "yd": "Yoreh De'ah",
    "יו\"ד": "Yoreh De'ah", "יורה דעה": "Yoreh De'ah",
    "even haezer": "Even HaEzer", "e\"h": "Even HaEzer", "eh": "Even HaEzer",
    "אה\"ע": "Even HaEzer", "אבן העזר": "Even HaEzer",
    "choshen mishpat": "Choshen Mishpat", "c\"m": "Choshen Mishpat", "cm": "Choshen Mishpat",
    "חו\"מ": "Choshen Mishpat", "חושן משפט": "Choshen Mishpat",
}


def translate_to_sefaria_slug(ref: str) -> str:
    """
    Translate yeshivish/Hebrew references to Sefaria format.
    
    Examples:
        "Kesubos 4a" → "Ketubot 4a"
        "Rambam Hilchos Ishus" → "Mishneh Torah, Marriage"
        "שו\"ע או\"ח" → "Shulchan Arukh, Orach Chayim"
    """
    original = ref
    ref_lower = ref.lower()
    
    # Handle Rambam
    if "rambam" in ref_lower or "רמב\"ם" in ref or "mishneh torah" in ref_lower:
        for heb, eng in RAMBAM_TRANSLATIONS.items():
            if heb in ref_lower:
                # Extract chapter/halacha if present
                numbers = re.findall(r'(\d+[:\.\d]*)', ref)
                num_str = " " + numbers[0] if numbers else ""
                ref = f"Mishneh Torah, {eng}{num_str}"
                break
        else:
            # Clean up if no specific hilchos found
            ref = ref.replace("Rambam ", "Mishneh Torah, ").replace("rambam ", "Mishneh Torah, ")
    
    # Handle Shulchan Aruch
    if "shulchan" in ref_lower or "שו\"ע" in ref or "s\"a" in ref_lower:
        for heb, eng in SA_TRANSLATIONS.items():
            if heb in ref_lower or heb in ref:
                # Extract siman/seif
                numbers = re.findall(r'(\d+[:\.\d]*)', ref)
                num_str = " " + numbers[0] if numbers else ""
                ref = f"Shulchan Arukh, {eng}{num_str}"
                break
    
    # Handle masechtos
    for yeshivish, sefaria in MASECHTA_TRANSLATIONS.items():
        # Case-insensitive replacement for masechta names
        pattern = re.compile(re.escape(yeshivish), re.IGNORECASE)
        ref = pattern.sub(sefaria, ref)
    
    if ref != original:
        logger.debug(f"  Slug translated: '{original}' → '{ref}'")
    
    return ref


# =============================
# PYDANTIC MODELS
# =============================

class TopicRequest(BaseModel):
    """Request model for /search endpoint"""
    topic: str
    clarification: Optional[str] = None
    scope: Optional[SearchScope] = SearchScope.STANDARD  # User-controlled depth


class FeedbackRequest(BaseModel):
    """Request for storing feedback"""
    query: str
    good_sources: List[str] = []
    bad_sources: List[str] = []
    notes: str = ""


class SourceReference(BaseModel):
    """A single validated source"""
    ref: str
    category: str  # Chumash, Nach, Mishna, Gemara, Rishonim, Shulchan Aruch, Acharonim
    he_text: str = ""
    en_text: str = ""
    he_ref: str = ""
    sefaria_url: str = ""
    relevance: str = ""
    cited_by: List[str] = []
    layer: str = ""  # Which layer this came from


class MareiMekomosResponse(BaseModel):
    """Response model for /search endpoint"""
    topic: str
    sources: List[SourceReference]
    summary: str = ""
    needs_clarification: bool = False
    clarifying_questions: List[str] = []
    interpreted_query: str = ""
    query_intent: str = "general"
    search_scope: str = "standard"
    layers_searched: List[str] = []
    methodology_notes: str = ""


# =============================
# FASTAPI APP
# =============================

app = FastAPI(
    title="Marei Mekomos API v6.0",
    description="Living Knowledge - Claude learns from resources/",
    version="6.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Anthropic client
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    logger.critical("ANTHROPIC_API_KEY not found!")
    raise RuntimeError("ANTHROPIC_API_KEY environment variable is required")
client = Anthropic(api_key=api_key)
logger.info("✓ Anthropic client initialized")


# =============================
# HELPER FUNCTIONS
# =============================

def clean_html(text: str) -> str:
    """Clean HTML from Sefaria text"""
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def flatten_text(text_data, max_depth: int = 10, separator: str = " ") -> str:
    """
    Improved text flattening that handles Gemara's deeply nested arrays.
    
    Sefaria returns Gemara as nested arrays representing paragraphs.
    We need to preserve structure while extracting all text.
    """
    if max_depth <= 0:
        return str(text_data) if text_data else ""
    
    if isinstance(text_data, str):
        return text_data
    elif isinstance(text_data, list):
        parts = []
        for item in text_data:
            if item:  # Skip empty items
                flattened = flatten_text(item, max_depth - 1, separator)
                if flattened.strip():
                    parts.append(flattened)
        return separator.join(parts)
    elif text_data is None:
        return ""
    else:
        return str(text_data)


def generate_cache_key(*args) -> str:
    """Generate stable cache key"""
    combined = "|".join(str(arg) for arg in args)
    return hashlib.md5(combined.encode()).hexdigest()


# =============================
# SEFARIA API FUNCTIONS
# =============================

async def fetch_text(ref: str, timeout: float = 15.0) -> dict:
    """
    Fetch and validate text from Sefaria API.
    
    This is the VGR "gatekeeper" - if Sefaria returns 404, it's a hallucination.
    """
    ref = translate_to_sefaria_slug(ref)
    
    # Check cache
    cached = sefaria_cache.get(f"text:{ref}")
    if cached:
        return cached
    
    logger.info(f"  📥 Fetching: {ref}")
    
    encoded_ref = ref.replace(" ", "%20").replace(",", "%2C")
    url = f"https://www.sefaria.org/api/v3/texts/{encoded_ref}"
    
    async with httpx.AsyncClient(verify=False, timeout=timeout) as client:
        try:
            response = await client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                
                he_text = ""
                en_text = ""
                he_ref = data.get("heRef", "")
                
                versions = data.get("versions", [])
                for version in versions:
                    lang = version.get("language", "")
                    text = version.get("text", "")
                    
                    # Use improved flattening
                    if isinstance(text, list):
                        text = flatten_text(text)
                    
                    if lang == "he" and not he_text:
                        he_text = clean_html(text)
                    elif lang == "en" and not en_text:
                        en_text = clean_html(text)
                
                result = {
                    "found": True,
                    "he_text": he_text[:2500] if he_text else "",
                    "en_text": en_text[:1500] if en_text else "",
                    "he_ref": he_ref,
                    "sefaria_url": f"https://www.sefaria.org/{encoded_ref}",
                }
                
                sefaria_cache.set(f"text:{ref}", result)
                logger.info(f"  ✓ VALIDATED: {ref}")
                return result
                
            else:
                logger.warning(f"  ✗ NOT FOUND ({response.status_code}): {ref}")
                return {"found": False}
                
        except Exception as e:
            logger.error(f"  ✗ ERROR: {ref} - {e}")
            return {"found": False}


async def search_sefaria(query: str, filters: Dict = None) -> List[dict]:
    """
    Search Sefaria's search API for sources.
    
    This helps find sources across ALL layers, not just from Related API.
    """
    logger.info(f"  🔍 Searching Sefaria: {query}")
    
    url = "https://www.sefaria.org/api/search-wrapper"
    params = {
        "q": query,
        "size": 20,
        "type": "text",
        "field": "naive_lemmatizer",
    }
    
    # Add filters if specified
    if filters:
        params.update(filters)
    
    async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
        try:
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                hits = data.get("hits", {}).get("hits", [])
                
                results = []
                for hit in hits:
                    source = hit.get("_source", {})
                    results.append({
                        "ref": source.get("ref", ""),
                        "he_text": source.get("exact", "")[:500],
                        "en_text": "",
                        "score": hit.get("_score", 0),
                    })
                
                logger.info(f"  Found {len(results)} search results")
                return results
            else:
                logger.warning(f"  Search API returned {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"  Search error: {e}")
            return []


async def get_related_texts(ref: str) -> List[dict]:
    """Get all linked texts (commentaries, references) from Sefaria Related API"""
    ref = translate_to_sefaria_slug(ref)
    
    # Check cache
    cached = sefaria_cache.get(f"related:{ref}")
    if cached:
        return cached
    
    logger.info(f"  🔗 Getting related texts: {ref}")
    
    encoded_ref = ref.replace(" ", "%20").replace(",", "%2C")
    url = f"https://www.sefaria.org/api/related/{encoded_ref}"
    
    async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
        try:
            response = await client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                links = data.get("links", [])
                
                results = []
                for link in links:
                    results.append({
                        "ref": link.get("sourceRef", ""),
                        "type": link.get("type", ""),
                        "category": link.get("category", ""),
                    })
                
                sefaria_cache.set(f"related:{ref}", results)
                logger.info(f"  Found {len(results)} related texts")
                return results
                
            return []
            
        except Exception as e:
            logger.error(f"  Related API error: {e}")
            return []


# =============================
# CLAUDE PROMPTS (Dynamic with Knowledge)
# =============================

def build_query_prompt(topic: str, clarification: str, scope: SearchScope) -> str:
    """
    Build the query interpretation prompt with LIVING KNOWLEDGE.
    
    Claude reads from resources/ folder and learns from past successes.
    """
    # Load relevant knowledge
    methodology = knowledge_loader.get_methodology()
    topic_knowledge = knowledge_loader.get_for_topic(topic)
    feedback_context = feedback_store.get_context_for_prompt(topic)
    
    scope_instructions = {
        SearchScope.FOCUSED: "Focus on the PRIMARY Gemara sugya and key Rishonim only.",
        SearchScope.STANDARD: "Cover Gemara through Shulchan Aruch with major Acharonim.",
        SearchScope.COMPREHENSIVE: "Search ALL layers from Chumash through modern Acharonim.",
    }
    
    prompt = f"""You are a Torah scholar assistant helping find marei mekomos (source references).

{methodology}

{topic_knowledge}

{feedback_context}

SEARCH SCOPE: {scope.value}
{scope_instructions.get(scope, "")}

You will interpret the user's query and identify sources across ALL RELEVANT LAYERS:
- Chumash (Torah verses that are the basis for this halacha/concept)
- Nach (if relevant prophetic/ketuvim sources)
- Mishna (the primary mishna for this topic)
- Gemara (the IKKAR SUGYA - where is this primarily discussed in Shas?)
- Rishonim (Rashi, Tosfos, Rambam, Rashba, Ritva, Ran, Rosh on the sugya)
- Shulchan Aruch (where is this codified? Which siman?)
- Acharonim (key later authorities who analyze this)

Remember: The resources and lists I've shown you are STARTING POINTS, not final answers.
Think creatively. What sources would a talmid chacham want to see?

OUTPUT FORMAT (JSON):
{{
  "needs_clarification": false,
  "clarifying_questions": [],
  "interpreted_query": "Your understanding of what they're asking",
  "query_intent": "lomdus|psak|makor|general",
  "sources_by_layer": {{
    "Chumash": [
      {{"ref": "Vayikra 15:19", "relevance": "Source for tumas niddah"}}
    ],
    "Mishna": [
      {{"ref": "Mishna Niddah 1:1", "relevance": "Primary mishna on this topic"}}
    ],
    "Gemara": [
      {{"ref": "Kesubos 4a-4b", "relevance": "Primary sugya for chuppas niddah"}}
    ],
    "Rishonim": [
      {{"ref": "Rambam Hilchos Ishus 10:11", "relevance": "Codifies the halacha"}}
    ],
    "Shulchan Aruch": [
      {{"ref": "Even HaEzer 61", "relevance": "Primary siman"}}
    ],
    "Acharonim": [
      {{"ref": "Beis Shmuel EH 61:1", "relevance": "Key commentary"}}
    ]
  }},
  "primary_masechta": "Kesubos",
  "summary": "Brief explanation of the topic and what sources discuss it"
}}"""
    
    return prompt


# =============================
# MAIN SEARCH PIPELINE
# =============================

async def search_all_layers(
    topic: str,
    clarification: Optional[str],
    scope: SearchScope
) -> MareiMekomosResponse:
    """
    Main search pipeline - comprehensive multi-layer search.
    
    1. Claude interprets query using LIVING KNOWLEDGE
    2. Identifies sources across ALL layers
    3. Validates each source against Sefaria (VGR)
    4. Returns comprehensive marei mekomos
    """
    logger.info("=" * 80)
    logger.info(f"SEARCH: '{topic}' (scope: {scope.value})")
    logger.info("=" * 80)
    
    # Build prompt with living knowledge
    system_prompt = build_query_prompt(topic, clarification or "", scope)
    
    user_message = f"Query: \"{topic}\""
    if clarification:
        user_message += f"\nUser clarification: \"{clarification}\""
    user_message += "\n\nIdentify sources across all relevant layers."
    
    # Call Claude
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        
        result_text = response.content[0].text
        
        # Parse JSON from response
        try:
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
            
            result_text = result_text.strip()
            if not result_text.startswith("{"):
                brace_idx = result_text.find("{")
                if brace_idx != -1:
                    result_text = result_text[brace_idx:]
            
            interpretation = json.loads(result_text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.error(f"Response: {result_text[:500]}")
            interpretation = {}
        
        # Check if clarification needed
        if interpretation.get("needs_clarification") and not clarification:
            return MareiMekomosResponse(
                topic=topic,
                sources=[],
                needs_clarification=True,
                clarifying_questions=interpretation.get("clarifying_questions", []),
                interpreted_query=interpretation.get("interpreted_query", ""),
                query_intent=interpretation.get("query_intent", "general"),
                search_scope=scope.value,
            )
        
        # Extract sources from all layers
        sources_by_layer = interpretation.get("sources_by_layer", {})
        interpreted_query = interpretation.get("interpreted_query", topic)
        query_intent = interpretation.get("query_intent", "general")
        summary = interpretation.get("summary", "")
        
        logger.info(f"  Interpreted as: {interpreted_query}")
        logger.info(f"  Query intent: {query_intent}")
        
        # Validate all sources against Sefaria (VGR)
        validated_sources = []
        layers_searched = []
        hallucination_count = 0
        
        for layer, sources in sources_by_layer.items():
            if not sources:
                continue
            
            layers_searched.append(layer)
            logger.info(f"\n  📚 Layer: {layer} ({len(sources)} sources)")
            
            for source in sources[:MAX_SOURCES_PER_LAYER]:
                ref = source.get("ref", "")
                relevance = source.get("relevance", "")
                
                if not ref:
                    continue
                
                # Validate against Sefaria
                result = await fetch_text(ref)
                
                if result.get("found"):
                    validated_sources.append(SourceReference(
                        ref=ref,
                        category=layer,
                        layer=layer,
                        he_text=result.get("he_text", ""),
                        en_text=result.get("en_text", ""),
                        he_ref=result.get("he_ref", ""),
                        sefaria_url=result.get("sefaria_url", ""),
                        relevance=relevance,
                    ))
                else:
                    hallucination_count += 1
                    logger.warning(f"    ✗ HALLUCINATION: {ref}")
        
        # Sort by layer importance
        layer_order = ["Chumash", "Nach", "Mishna", "Gemara", "Rishonim", "Shulchan Aruch", "Acharonim"]
        validated_sources.sort(key=lambda x: layer_order.index(x.layer) if x.layer in layer_order else 99)
        
        # Limit total sources
        validated_sources = validated_sources[:MAX_TOTAL_SOURCES]
        
        # Build methodology notes
        methodology_notes = (
            f"Searched {len(layers_searched)} layers: {', '.join(layers_searched)}. "
            f"Validated {len(validated_sources)} sources, caught {hallucination_count} hallucinations. "
            f"Query intent: {query_intent}."
        )
        
        logger.info(f"\n{'='*80}")
        logger.info(f"COMPLETE: {len(validated_sources)} validated sources from {len(layers_searched)} layers")
        logger.info(f"{'='*80}")
        
        return MareiMekomosResponse(
            topic=topic,
            sources=validated_sources,
            summary=summary,
            interpreted_query=interpreted_query,
            query_intent=query_intent,
            search_scope=scope.value,
            layers_searched=layers_searched,
            methodology_notes=methodology_notes,
        )
        
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================
# API ENDPOINTS
# =============================

@app.get("/")
async def root():
    return {
        "message": "Marei Mekomos API v6.0 - Living Knowledge",
        "philosophy": "Resources are starting points, not final answers",
        "features": [
            "Multi-layer search (Chumash → Acharonim)",
            "Dynamic knowledge loading from resources/",
            "Feedback-based learning",
            "VGR anti-hallucination",
            "User-controlled search scope"
        ]
    }


@app.post("/search", response_model=MareiMekomosResponse)
async def search_sources(request: TopicRequest):
    """
    Main search endpoint.
    
    Searches across all layers (Chumash to Acharonim) based on scope.
    Uses living knowledge from resources/ folder.
    """
    return await search_all_layers(
        request.topic,
        request.clarification,
        request.scope or SearchScope.STANDARD
    )


@app.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """
    Submit feedback about search results.
    
    Good sources get stored for future reference.
    Bad sources help Claude learn what NOT to suggest.
    """
    if request.good_sources:
        feedback_store.add_success(request.query, request.good_sources, request.notes)
    if request.bad_sources:
        feedback_store.add_failure(request.query, request.bad_sources, request.notes)
    
    return {"status": "feedback recorded"}


@app.get("/knowledge")
async def get_knowledge():
    """View what knowledge is currently loaded"""
    knowledge = knowledge_loader.load_all(force_refresh=True)
    return {
        "files_loaded": len(knowledge),
        "file_names": list(knowledge.keys()),
        "total_chars": sum(len(v) for v in knowledge.values()),
    }


@app.get("/health")
async def health_check():
    knowledge_count = len(knowledge_loader.load_all())
    return {
        "status": "healthy",
        "version": "6.0.0",
        "knowledge_files": knowledge_count,
        "cost_saving_mode": COST_SAVING_MODE,
    }


@app.get("/cache/stats")
async def cache_stats():
    claude_stats = claude_cache.stats()
    sefaria_stats = sefaria_cache.stats()
    return {
        "claude_cache": claude_stats,
        "sefaria_cache": sefaria_stats,
    }


@app.post("/cache/clear")
async def clear_cache():
    claude_cache.clear()
    sefaria_cache.clear()
    return {"status": "cleared"}


if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting Marei Mekomos API v6.0 - Living Knowledge")
    logger.info(f"   Knowledge directory: {KNOWLEDGE_DIR}")
    logger.info(f"   Feedback directory: {FEEDBACK_DIR}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
