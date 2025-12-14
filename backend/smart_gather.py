"""
Smart Sefaria Data Gathering - Phase 2 Enhanced
Intelligently handles author names vs concepts
NOW USING: Master Torah Authors Knowledge Base
"""

import logging
from typing import Dict, List, Optional
import re

# Import from MASTER knowledge base
from tools.torah_authors_master import (
    is_author,
    get_author_matches,
    disambiguate_author,
    get_sefaria_ref,
    detect_authors_in_text,
    normalize_text,
)

logger = logging.getLogger(__name__)

# ==========================================
#  MASECHTA NAME MAPPING
# ==========================================

MASECHTA_NAMES = {
    # Hebrew → English (Sefaria format)
    'פסחים': 'Pesachim',
    'שבת': 'Shabbat',
    'בבא מציעא': 'Bava Metzia',
    'בבא קמא': 'Bava Kamma',
    'בבא בתרא': 'Bava Batra',
    'כתובות': 'Ketubot',
    'קידושין': 'Kiddushin',
    'גיטין': 'Gittin',
    'סנהדרין': 'Sanhedrin',
    'ברכות': 'Berakhot',
    'עירובין': 'Eruvin',
    'נדרים': 'Nedarim',
    'נזיר': 'Nazir',
    'סוטה': 'Sotah',
    'יומא': 'Yoma',
    'מגילה': 'Megillah',
    'תענית': 'Taanit',
    'ראש השנה': 'Rosh Hashanah',
    'סוכה': 'Sukkah',
    'ביצה': 'Beitzah',
    'מועד קטן': 'Moed Katan',
    'חגיגה': 'Chagigah',
    'שבועות': 'Shevuot',
    'מכות': 'Makkot',
    'חולין': 'Chullin',
    'זבחים': 'Zevachim',
    'מנחות': 'Menachot',
}

MASECHTA_NAMES_EN = set(MASECHTA_NAMES.values())

# ==========================================
#  PRIMARY SUGYA EXTRACTION
# ==========================================

def extract_masechta_from_ref(ref: str) -> Optional[str]:
    """
    Extract masechta name from a Sefaria reference.
    
    Examples:
        "Pesachim 4b:3" → "Pesachim"
        "Bava Metzia 10a" → "Bava Metzia"
        "Rashi on Ketubot 7b:1" → "Ketubot"
    """
    # Remove commentary prefix
    ref = re.sub(r'^(Rashi|Tosafot|Ran|Rashba|Ritva|Meiri|Rambam|Rif) on ', '', ref)
    
    # Check each known masechta
    for masechta_en in MASECHTA_NAMES_EN:
        if masechta_en in ref:
            return masechta_en
    
    return None

def extract_daf_from_ref(ref: str) -> Optional[str]:
    """
    Extract daf (page) from a Sefaria reference.
    
    Examples:
        "Pesachim 4b:3" → "4b"
        "Bava Metzia 10a" → "10a"
    """
    # Pattern: number followed by 'a' or 'b'
    match = re.search(r'(\d+[ab])', ref)
    return match.group(1) if match else None

def clean_sugya_ref(ref: str) -> str:
    """
    Clean a sugya reference to just masechta + daf.
    
    Examples:
        "Pesachim 4b:3" → "Pesachim 4b"
        "Rashi on Bava Metzia 10a:5" → "Bava Metzia 10a"
    """
    # Remove commentary prefix
    ref = ref.split(' on ')[-1]
    
    # Extract masechta and daf
    masechta = extract_masechta_from_ref(ref)
    daf = extract_daf_from_ref(ref)
    
    if masechta and daf:
        return f"{masechta} {daf}"
    
    return ref  # Return as-is if can't parse

def extract_primary_sugya_from_results(
    concept: str,
    sefaria_results: Dict,
    prefer_gemara: bool = True
) -> Optional[str]:
    """
    Extract the primary sugya reference from Sefaria search results.
    
    Strategy:
    1. Look at top refs (most relevant)
    2. Prefer Gemara over commentaries (unless prefer_gemara=False)
    3. Find refs from the primary masechta
    4. Return first matching ref
    
    Args:
        concept: The concept that was searched
        sefaria_results: Results from Sefaria search
        prefer_gemara: If True, prefer Gemara refs over commentaries
    
    Returns:
        Primary sugya ref like "Pesachim 4b" or None
    """
    top_refs = sefaria_results.get('top_refs', [])
    masechtot = sefaria_results.get('masechtot', {})
    
    if not top_refs:
        logger.warning(f"[EXTRACT-SUGYA] No refs found for '{concept}'")
        return None
    
    # Determine primary masechta (most hits)
    primary_masechta = None
    if masechtot:
        primary_masechta = max(masechtot.items(), key=lambda x: x[1])[0]
        logger.info(f"[EXTRACT-SUGYA] Primary masechta for '{concept}': {primary_masechta}")
    
    # Modern works to skip
    modern_works = [
        'Peninei Halakhah',
        'Mishnat Eretz Yisrael',
        'Kovetz',
        'Sefer',
        'Responsa'
    ]
    
    # Look through top refs for Gemara from primary masechta
    gemara_refs = []
    commentary_refs = []
    
    for ref in top_refs[:20]:  # Check top 20
        # Skip modern works
        if any(modern in ref for modern in modern_works):
            continue
        
        # Check if it's a Gemara ref (no commentary prefix)
        is_gemara = not any(commentary in ref for commentary in [
            'Rashi on',
            'Tosafot on',
            'Ran on',
            'Rashba on',
            'Meiri on',
            'Ritva on'
        ])
        
        # Extract masechta from ref
        masechta = extract_masechta_from_ref(ref)
        
        if is_gemara and masechta:
            if primary_masechta and masechta == primary_masechta:
                # Perfect: Gemara from primary masechta
                gemara_refs.insert(0, ref)  # Add to front
            else:
                gemara_refs.append(ref)
        elif masechta:
            commentary_refs.append(ref)
    
    logger.debug(f"[EXTRACT-SUGYA] Found {len(gemara_refs)} Gemara refs, {len(commentary_refs)} commentary refs")
    
    # Return preference
    if prefer_gemara and gemara_refs:
        primary = gemara_refs[0]
        logger.info(f"[EXTRACT-SUGYA] Selected Gemara ref: {primary}")
        return primary
    elif commentary_refs:
        primary = commentary_refs[0]
        logger.info(f"[EXTRACT-SUGYA] Selected commentary ref: {primary}")
        return primary
    elif gemara_refs:
        primary = gemara_refs[0]
        logger.info(f"[EXTRACT-SUGYA] Selected (backup) Gemara ref: {primary}")
        return primary
    
    logger.warning(f"[EXTRACT-SUGYA] Could not extract primary sugya from {len(top_refs)} refs")
    return None

# ==========================================
#  SMART GATHERING - ENHANCED
# ==========================================

async def gather_sefaria_data_smart(
    hebrew_terms: List[str],
    original_query: str,
    sefaria_client
) -> Dict:
    """
    Intelligently gather Sefaria data, handling authors differently from concepts.
    NOW ENHANCED with Master Torah Authors Knowledge Base!
    
    Strategy:
    1. Separate authors from concepts
    2. For concepts: Search normally
    3. For authors: Don't search - construct refs based on concept results
    4. Handle acronym disambiguation
    5. Return combined data with metadata
    
    Args:
        hebrew_terms: List of Hebrew terms from Step 1
        original_query: Original English/transliterated query
        sefaria_client: Instance of SefariaClient
    
    Returns:
        Dict with data for each term, marked as 'author' or 'concept'
    """
    logger.info("=" * 70)
    logger.info("[SMART-GATHER] Starting intelligent data gathering (MASTER KB)")
    logger.info("=" * 70)
    
    # Separate authors from concepts
    authors = []
    concepts = []
    author_metadata = {}  # Store full author objects
    
    for term in hebrew_terms:
        if is_author(term):
            # Get all matching authors
            matches = get_author_matches(term)
            
            if len(matches) == 1:
                # Unambiguous
                authors.append(term)
                author_metadata[term] = matches[0]
                logger.info(f"[SMART-GATHER] Detected author (unambiguous): {term} → {matches[0]['primary_name_en']}")
            else:
                # Ambiguous - try to disambiguate
                logger.warning(f"[SMART-GATHER] Ambiguous author: {term} ({len(matches)} matches)")
                
                # Try disambiguation with context
                best_match = disambiguate_author(term, context=original_query)
                
                if best_match:
                    authors.append(term)
                    author_metadata[term] = best_match
                    logger.info(f"[SMART-GATHER] Disambiguated: {term} → {best_match['primary_name_en']} ({best_match['period']})")
                else:
                    # Could not disambiguate - mark for clarification
                    authors.append(term)
                    author_metadata[term] = {
                        'ambiguous': True,
                        'matches': matches,
                        'needs_clarification': True
                    }
                    logger.warning(f"[SMART-GATHER] Could not disambiguate {term} - needs user clarification")
        else:
            concepts.append(term)
    
    logger.info(f"[SMART-GATHER] Detected {len(authors)} authors: {authors}")
    logger.info(f"[SMART-GATHER] Detected {len(concepts)} concepts: {concepts}")
    
    sefaria_data = {}
    primary_sugya = None
    
    # ==========================================
    # PHASE 1: GATHER FOR CONCEPTS
    # ==========================================
    
    for concept in concepts:
        logger.info(f"[SMART-GATHER] Searching concept: '{concept}'")
        
        try:
            # sefaria_client.search() returns a SearchResults dataclass, NOT a dict
            result = await sefaria_client.search(concept, size=100)
            
            # FIX: Use attribute access instead of .get() - SearchResults is a dataclass
            total_hits = result.total_hits
            top_refs = [hit.ref for hit in result.hits][:20]
            
            # Extract categories and masechtot
            # NOTE: SearchResults already has hits_by_category and hits_by_masechta
            # but we'll compute masechtot ourselves for filtering
            categories = {}
            masechtot = {}
            
            # FIX: result.hits is a list of SearchHit dataclass objects
            for hit in result.hits[:100]:
                # FIX: Use attribute access - SearchHit is a dataclass
                cat = hit.category
                categories[cat] = categories.get(cat, 0) + 1
                
                # Masechtot (from ref)
                ref = hit.ref
                masechta = extract_masechta_from_ref(ref)
                if masechta:
                    masechtot[masechta] = masechtot.get(masechta, 0) + 1
            
            # Extract primary sugya
            sugya = extract_primary_sugya_from_results(
                concept,
                {'top_refs': top_refs, 'masechtot': masechtot}
            )
            
            if sugya and not primary_sugya:
                # This is our first sugya - use it for authors
                primary_sugya = clean_sugya_ref(sugya)
                logger.info(f"[SMART-GATHER] ⭐ PRIMARY SUGYA: {primary_sugya}")
            
            sefaria_data[concept] = {
                'type': 'concept',
                'total_hits': total_hits,
                'top_refs': top_refs[:10],
                'primary_sugya': sugya,
                'categories': categories,
                'masechtot': masechtot,
                'search_success': True
            }
            
            logger.info(f"[SMART-GATHER]   ✓ Found {total_hits} hits, primary sugya: {sugya}")
            
        except Exception as e:
            logger.error(f"[SMART-GATHER]   ✗ Search failed for '{concept}': {e}")
            sefaria_data[concept] = {
                'type': 'concept',
                'search_success': False,
                'error': str(e)
            }
    
    # ==========================================
    # PHASE 2: CONSTRUCT AUTHOR REFERENCES
    # ==========================================
    
    if authors and primary_sugya:
        logger.info(f"[SMART-GATHER] Constructing author refs based on sugya: {primary_sugya}")
        
        masechta = extract_masechta_from_ref(primary_sugya)
        
        for author_term in authors:
            author_data = author_metadata.get(author_term)
            
            # Check if ambiguous
            if author_data.get('ambiguous'):
                # Store disambiguation info
                sefaria_data[author_term] = {
                    'type': 'author',
                    'needs_clarification': True,
                    'matches': [
                        {
                            'name_en': m['primary_name_en'],
                            'name_he': m['primary_name_he'],
                            'period': m.get('period', 'Unknown'),
                            'region': m.get('region', 'Unknown'),
                            'disambiguation': m.get('disambiguation')
                        }
                        for m in author_data['matches']
                    ],
                    'reason': 'Multiple authors match this name/acronym'
                }
                logger.warning(f"[SMART-GATHER] {author_term} is ambiguous - stored clarification data")
                continue
            
            # Not ambiguous - construct reference
            if not author_data:
                logger.warning(f"[SMART-GATHER] No metadata for author: {author_term}")
                sefaria_data[author_term] = {
                    'type': 'author',
                    'error': 'No metadata found'
                }
                continue
            
            # Check if author covers this masechta
            coverage = author_data.get('masechta_coverage')
            primary_masechtot = author_data.get('primary_masechtot', [])
            
            covers = True
            if coverage == 'all':
                covers = True
            elif coverage == 'select':
                covers = masechta in primary_masechtot if masechta else False
            elif coverage == 'minimal':
                covers = masechta in primary_masechtot if masechta else False
            
            if not covers:
                logger.warning(f"[SMART-GATHER] {author_data['primary_name_en']} may not cover {masechta}")
            
            # Construct reference using master KB function
            constructed_ref = get_sefaria_ref(author_term, primary_sugya)
            
            if constructed_ref:
                logger.info(f"[SMART-GATHER]   ✓ {author_term} → {constructed_ref}")
                
                sefaria_data[author_term] = {
                    'type': 'author',
                    'constructed_ref': constructed_ref,
                    'based_on_sugya': primary_sugya,
                    'author_info': {
                        'name_en': author_data['primary_name_en'],
                        'name_he': author_data['primary_name_he'],
                        'period': author_data.get('period', 'Unknown'),
                        'era': author_data.get('era', 'Unknown'),
                        'category': author_data.get('category', 'Unknown'),
                    },
                    'coverage_uncertain': not covers
                }
            else:
                logger.warning(f"[SMART-GATHER]   ✗ Could not construct ref for {author_term}")
                
                sefaria_data[author_term] = {
                    'type': 'author',
                    'construction_failed': True,
                    'based_on_sugya': primary_sugya,
                    'author_info': {
                        'name_en': author_data.get('primary_name_en', 'Unknown'),
                        'name_he': author_data.get('primary_name_he', author_term),
                    }
                }
    
    elif authors and not primary_sugya:
        # We have authors but no sugya - can't construct refs
        logger.warning("[SMART-GATHER] Authors detected but no primary sugya found!")
        
        for author_term in authors:
            author_data = author_metadata.get(author_term)
            
            if author_data and not author_data.get('ambiguous'):
                sefaria_data[author_term] = {
                    'type': 'author',
                    'needs_clarification': True,
                    'author_info': {
                        'name_en': author_data.get('primary_name_en', 'Unknown'),
                        'name_he': author_data.get('primary_name_he', author_term),
                    },
                    'reason': 'No sugya found to base reference on'
                }
            elif author_data and author_data.get('ambiguous'):
                sefaria_data[author_term] = {
                    'type': 'author',
                    'needs_clarification': True,
                    'matches': [
                        {
                            'name_en': m['primary_name_en'],
                            'period': m.get('period', 'Unknown'),
                        }
                        for m in author_data['matches']
                    ],
                    'reason': 'Multiple authors match this name + no sugya context'
                }
    
    elif authors and not concepts:
        # Only authors, no topic to search
        logger.warning("[SMART-GATHER] Only authors, no concepts - need clarification!")
        
        for author_term in authors:
            author_data = author_metadata.get(author_term)
            
            if author_data and not author_data.get('ambiguous'):
                sefaria_data[author_term] = {
                    'type': 'author',
                    'needs_clarification': True,
                    'author_info': {
                        'name_en': author_data.get('primary_name_en', 'Unknown'),
                        'name_he': author_data.get('primary_name_he', author_term),
                    },
                    'reason': 'No topic specified'
                }
    
    logger.info("=" * 70)
    logger.info(f"[SMART-GATHER] Completed gathering for {len(sefaria_data)} terms")
    logger.info("=" * 70)
    
    return sefaria_data

# ==========================================
#  HELPER: Format for Claude
# ==========================================

def format_smart_gather_for_claude(sefaria_data: Dict) -> str:
    """
    Format smart gather results into a string for Claude's prompt.
    Clearly distinguishes between author entries and concept entries.
    """
    lines = []
    
    for term, data in sefaria_data.items():
        term_type = data.get('type', 'unknown')
        
        if term_type == 'concept':
            # Concept entry - show search results
            lines.append(f"--- {term} (CONCEPT) ---")
            lines.append(f"  Total hits: {data.get('total_hits', 0)}")
            
            top_refs = data.get('top_refs', [])
            if top_refs:
                lines.append(f"  Top refs: {top_refs[:5]}")
            
            primary_sugya = data.get('primary_sugya')
            if primary_sugya:
                lines.append(f"  Primary sugya: {primary_sugya}")
            
            masechtot = data.get('masechtot', {})
            if masechtot:
                top_masechta = max(masechtot.items(), key=lambda x: x[1])
                lines.append(f"  Primary masechta: {top_masechta[0]} ({top_masechta[1]} hits)")
        
        elif term_type == 'author':
            # Author entry - show constructed reference or clarification need
            author_info = data.get('author_info', {})
            name_en = author_info.get('name_en', 'Unknown')
            
            lines.append(f"--- {term} (AUTHOR: {name_en}) ---")
            
            constructed_ref = data.get('constructed_ref')
            if constructed_ref:
                lines.append(f"  Commentary reference: {constructed_ref}")
                lines.append(f"  Based on sugya: {data.get('based_on_sugya', 'N/A')}")
                
                if data.get('coverage_uncertain'):
                    lines.append(f"  Note: Coverage of this masechta may be incomplete")
            
            elif data.get('needs_clarification'):
                lines.append(f"  Status: Needs clarification")
                reason = data.get('reason', 'Unknown')
                lines.append(f"  Reason: {reason}")
                
                # If multiple matches, list them
                matches = data.get('matches')
                if matches:
                    lines.append(f"  Possible matches:")
                    for match in matches:
                        lines.append(f"    - {match['name_en']} ({match['period']})")
            
            elif data.get('construction_failed'):
                lines.append(f"  Status: Reference construction failed")
                lines.append(f"  Attempted sugya: {data.get('based_on_sugya', 'N/A')}")
            
            else:
                lines.append(f"  Status: Error - {data.get('error', 'Unknown error')}")
        
        lines.append("")  # Blank line between terms
    
    return "\n".join(lines)