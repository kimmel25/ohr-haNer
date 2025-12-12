"""
Phase 2 Integration Helpers - Master KB Bridge
===============================================
Drop-in helper functions that make integration seamless.
Import this module and use its functions instead of modifying existing code extensively.

Usage in step_two_understand.py:
    from phase2_integration_helpers import should_use_smart_gather, execute_smart_gather
    
    if should_use_smart_gather(hebrew_terms):
        sefaria_data = await execute_smart_gather(hebrew_terms, query)
    else:
        # existing traditional gathering
"""

import logging
from typing import List, Dict, Optional

# Import Master KB functions
from tools.torah_authors_master import (
    is_author,
    get_author_matches,
    disambiguate_author,
    get_sefaria_ref,
    detect_authors_in_text,
    normalize_text,
)

# Import enhanced gathering
from smart_gather import (
    gather_sefaria_data_smart,
    format_smart_gather_for_claude
)

logger = logging.getLogger(__name__)

# ==========================================
#  DETECTION HELPERS
# ==========================================

def has_authors(hebrew_terms: List[str]) -> bool:
    """
    Check if ANY of the Hebrew terms are authors.
    
    Args:
        hebrew_terms: List of Hebrew terms
    
    Returns:
        True if at least one term is an author
    """
    return any(is_author(term) for term in hebrew_terms)

def separate_authors_and_concepts(hebrew_terms: List[str]) -> Dict[str, List[str]]:
    """
    Separate a list of Hebrew terms into authors and concepts.
    
    Args:
        hebrew_terms: Mixed list of Hebrew terms
    
    Returns:
        {
            'authors': [...],
            'concepts': [...]
        }
    """
    authors = []
    concepts = []
    
    for term in hebrew_terms:
        if is_author(term):
            authors.append(term)
        else:
            concepts.append(term)
    
    return {
        'authors': authors,
        'concepts': concepts
    }

def should_use_smart_gather(hebrew_terms: List[str]) -> bool:
    """
    Determine if smart gathering should be used for these terms.
    
    Smart gathering is used when:
    1. At least one term is an author
    2. We want to construct commentary references
    
    Args:
        hebrew_terms: List of Hebrew terms
    
    Returns:
        True if smart gathering should be used
    """
    has_any_authors = has_authors(hebrew_terms)
    
    if has_any_authors:
        logger.info(f"[INTEGRATION] Smart gathering recommended: detected authors in {hebrew_terms}")
    else:
        logger.info(f"[INTEGRATION] Traditional gathering recommended: no authors in {hebrew_terms}")
    
    return has_any_authors

# ==========================================
#  EXECUTION HELPERS
# ==========================================

async def execute_smart_gather(
    hebrew_terms: List[str],
    original_query: str
) -> Dict:
    """
    Execute smart gathering with Master KB integration.
    
    This is a wrapper that:
    1. Gets Sefaria client
    2. Calls gather_sefaria_data_smart
    3. Returns formatted results
    
    Args:
        hebrew_terms: List of Hebrew terms
        original_query: Original user query
    
    Returns:
        Sefaria data dict with author entries properly formatted
    """
    logger.info("[INTEGRATION] Executing smart gathering with Master KB")
    
    # Import Sefaria client
    from tools.sefaria_client import get_sefaria_client
    client = get_sefaria_client()
    
    # Execute smart gathering
    sefaria_data = await gather_sefaria_data_smart(
        hebrew_terms,
        original_query,
        client
    )
    
    logger.info(f"[INTEGRATION] Smart gathering complete: {len(sefaria_data)} terms processed")
    
    return sefaria_data

def format_for_claude(sefaria_data: Dict) -> str:
    """
    Format sefaria data for Claude's prompt.
    
    This is a wrapper around format_smart_gather_for_claude
    that ensures consistent formatting.
    
    Args:
        sefaria_data: Data from smart or traditional gathering
    
    Returns:
        Formatted string for Claude prompt
    """
    return format_smart_gather_for_claude(sefaria_data)

# ==========================================
#  CLAUDE PROMPT ENHANCEMENT
# ==========================================

def get_author_handling_instructions() -> str:
    """
    Get the author handling instructions to add to Claude's system prompt.
    
    Returns:
        String to append to system prompt
    """
    return """

CRITICAL AUTHOR HANDLING (MASTER KB):
=====================================

When you see entries marked as "(AUTHOR: [name])", these are Torah authorities from our comprehensive Master Knowledge Base.

For author entries, you will see:
  --- רן (AUTHOR: Ran) ---
    Commentary reference: Ran on Pesachim 4b
    Based on sugya: Pesachim 4b

The "Commentary reference" is the CONSTRUCTED REFERENCE that should be used as the primary source.

CORRECT usage in primary_sources:
  {
    "primary_sources": [
      "Ran on Pesachim 4b",       ← Use the constructed reference
      "Tosafot on Pesachim 4b",   ← Use the constructed reference
      "Rashi on Pesachim 4b"      ← Use the constructed reference
    ]
  }

WRONG usage (NEVER DO THIS):
  {
    "primary_sources": [
      "Machberet Menachem, Letter Resh 52:1"  ← Dictionary entry - NO!
      "Selichot Nusach Lita"                  ← Liturgy - NO!
      "Kovetz Yesodot VaChakirot"             ← Modern work - NO!
    ]
  }

When an author entry says "needs_clarification":
  - Multiple authors may match the acronym (e.g., 3 different Maharams)
  - OR no sugya context was found to base the reference on
  - In this case, set clarification_prompt to ask the user for specifics

For concept entries marked "(CONCEPT)":
  - Use top_refs normally - these are actual Sefaria search results
  - The primary_sugya is the most relevant Gemara source for the concept
  - You can use these refs as you normally would

Example handling:
  User asks: "What is the Ran's view on bittul chometz?"
  
  Sefaria data shows:
    --- רן (AUTHOR: Ran) ---
      Commentary reference: Ran on Pesachim 4b
      Based on sugya: Pesachim 4b
    
    --- ביטול חמץ (CONCEPT) ---
      Total hits: 1706
      Primary sugya: Pesachim 4b
  
  Your response should use:
    primary_sources: ["Ran on Pesachim 4b"]
  
  NOT:
    primary_sources: ["Machberet Menachem..."] ← Wrong!

This ensures users get actual Torah commentaries, not dictionaries or unrelated texts.
"""

# ==========================================
#  VALIDATION HELPERS
# ==========================================

def validate_author_ref(ref: str) -> bool:
    """
    Validate that a reference looks like a proper author commentary reference.
    
    Args:
        ref: Reference string to validate
    
    Returns:
        True if it looks like a proper commentary reference
    """
    # Common author prefixes
    valid_prefixes = [
        'Rashi on',
        'Tosafot on',
        'Ran on',
        'Rashba on',
        'Ritva on',
        'Rambam on',
        'Ramban on',
        'Meiri on',
        'Maharsha on',
        'Pnei Yehoshua on',
        'Rif ',  # Special case - no "on"
    ]
    
    return any(ref.startswith(prefix) for prefix in valid_prefixes)

def detect_invalid_refs(primary_sources: List[str]) -> List[str]:
    """
    Detect potentially invalid references in primary_sources list.
    
    Args:
        primary_sources: List of source references
    
    Returns:
        List of suspicious/invalid references
    """
    invalid = []
    
    # Common invalid patterns
    invalid_patterns = [
        'Machberet',
        'Kovetz',
        'Selichot',
        'Piyut',
        'Letter',
        'Peninei Halakhah',
        'Responsa',  # Without specific author name
    ]
    
    for ref in primary_sources:
        for pattern in invalid_patterns:
            if pattern in ref and not validate_author_ref(ref):
                invalid.append(ref)
                break
    
    return invalid

# ==========================================
#  DEBUGGING HELPERS
# ==========================================

def debug_author_detection(hebrew_terms: List[str]) -> Dict:
    """
    Debug helper to see what the Master KB detects.
    
    Args:
        hebrew_terms: List of Hebrew terms
    
    Returns:
        Debug info dict
    """
    debug_info = {
        'total_terms': len(hebrew_terms),
        'authors': [],
        'concepts': [],
        'ambiguous': [],
    }
    
    for term in hebrew_terms:
        if is_author(term):
            matches = get_author_matches(term)
            
            if len(matches) == 1:
                debug_info['authors'].append({
                    'term': term,
                    'name': matches[0]['primary_name_en'],
                    'period': matches[0].get('period', 'Unknown'),
                })
            else:
                debug_info['ambiguous'].append({
                    'term': term,
                    'matches': [
                        {
                            'name': m['primary_name_en'],
                            'period': m.get('period', 'Unknown'),
                        }
                        for m in matches
                    ]
                })
        else:
            debug_info['concepts'].append(term)
    
    return debug_info

def log_integration_status():
    """
    Log the current integration status for debugging.
    """
    try:
        from tools.torah_authors_master import TORAH_AUTHORS_KB, get_stats
        stats = get_stats()
        
        logger.info("=" * 70)
        logger.info("MASTER KB INTEGRATION STATUS")
        logger.info("=" * 70)
        logger.info(f"Total authors loaded: {stats['total_authors']}")
        logger.info(f"Rishonim: {stats['rishonim']}")
        logger.info(f"Acharonim: {stats['acharonim']}")
        logger.info(f"With Sefaria integration: {stats['with_sefaria_base']}")
        logger.info(f"Ambiguous acronyms: {stats['ambiguous_acronyms']}")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"Failed to load Master KB stats: {e}")

# ==========================================
#  USAGE EXAMPLE
# ==========================================

"""
EXAMPLE USAGE IN step_two_understand.py:

# At top of file:
from phase2_integration_helpers import (
    should_use_smart_gather,
    execute_smart_gather,
    format_for_claude,
    get_author_handling_instructions,
    log_integration_status
)

# In understand() function, replace gathering logic:

# Log integration status (optional, for debugging)
log_integration_status()

# Determine gathering strategy
if should_use_smart_gather(hebrew_terms):
    logger.info("[UNDERSTAND] Using smart gathering (Master KB)")
    sefaria_data = await execute_smart_gather(hebrew_terms, query)
else:
    logger.info("[UNDERSTAND] Using traditional gathering")
    sefaria_data = {}
    for term in hebrew_terms:
        result = await gather_sefaria_data(term)
        sefaria_data[term] = result

# Format for Claude
sefaria_context = format_for_claude(sefaria_data)

# In system prompt for Claude:
system_prompt = f'''
[existing prompt content]

{get_author_handling_instructions()}

[rest of prompt]
'''
"""