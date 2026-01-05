"""
Source Output Writer for Ohr Haner V4
======================================

Generates formatted output files (TXT and HTML) from search results.
V4: Supports tiered output for nuance queries with landmark display.
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict
import re
import html

# Initialize logging
try:
    from logging_config import setup_logging
    setup_logging()
except ImportError:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

try:
    from step_three_search import SearchResult, Source, SourceLevel
except ImportError:
    pass

logger = logging.getLogger(__name__)

# Output directory
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Traditional learning hierarchy order for sorting
LEVEL_ORDER = {
    "chumash": 1,
    "mishna": 2,
    "gemara": 3,
    "rashi": 4,
    "tosfos": 5,
    "rishonim": 6,
    "rambam": 7,
    "tur": 8,
    "shulchan_aruch": 9,
    "nosei_keilim": 10,
    "acharonim": 11,
    "other": 12
}

# Level display names (Hebrew)
LEVEL_NAMES = {
    "chumash": "פסוקים",
    "mishna": "משנה",
    "gemara": "גמרא בבלי",
    "rashi": "רש\"י",
    "tosfos": "תוספות",
    "rishonim": "ראשונים",
    "rambam": "רמב\"ם",
    "tur": "טור",
    "shulchan_aruch": "שולחן ערוך",
    "nosei_keilim": "נושאי כלים",
    "acharonim": "אחרונים",
    "other": "אחר"
}


def get_level_str(source) -> str:
    """Get the level string from a source."""
    if hasattr(source.level, 'value'):
        return source.level.value
    return str(source.level)


def sort_sources_by_level(sources: List["Source"]) -> List["Source"]:
    """Sort sources by traditional learning hierarchy."""
    def get_level_priority(source):
        level_str = get_level_str(source)
        return LEVEL_ORDER.get(level_str, 99)
    
    return sorted(sources, key=get_level_priority)


def group_sources_by_level(sources: List["Source"]) -> Dict[str, List["Source"]]:
    """Group sources by their level."""
    groups = {}
    for source in sources:
        level_str = get_level_str(source)
        if level_str not in groups:
            groups[level_str] = []
        groups[level_str].append(source)
    return groups


def sanitize_filename(query: str) -> str:
    """Create a safe filename from query."""
    safe = re.sub(r'[<>:"/\\|?*]', '', query)
    safe = re.sub(r'\s+', '_', safe)
    safe = safe[:50]
    return safe or "query"


def strip_html_tags(text: str) -> str:
    """Remove HTML tags from text for plain text output."""
    if not text:
        return ""
    
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p>|</div>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    
    return text


def format_source_txt(source: "Source", num: int, show_tier: bool = False) -> List[str]:
    """Format a single source as text lines."""
    lines = []
    
    # Source header with optional landmark/tier marker
    tier_marker = ""
    if show_tier:
        if getattr(source, 'is_landmark', False):
            tier_marker = " ⭐ LANDMARK"
        elif getattr(source, 'tier', '') == 'primary':
            tier_marker = " [PRIMARY]"
        elif getattr(source, 'tier', '') == 'context':
            tier_marker = " [CONTEXT]"
    
    lines.append(f"[{num}] {source.ref}{tier_marker}")
    
    # Hebrew ref if different
    if source.he_ref and source.he_ref != source.ref:
        lines.append(f"    {source.he_ref}")
    
    # Author
    author = source.author if source.author else ""
    if author:
        lines.append(f"    Author: {author}")
    
    # Focus score for nuance queries
    focus_score = getattr(source, 'focus_score', 0)
    if focus_score > 0:
        lines.append(f"    Focus Score: {focus_score:.1f}")
    
    # Character count
    total_chars = len(source.hebrew_text or "") + len(source.english_text or "")
    lines.append(f"    Characters: {total_chars}")
    lines.append("")
    
    # Hebrew text
    if source.hebrew_text:
        lines.append("    ─── Hebrew ───")
        hebrew_clean = strip_html_tags(source.hebrew_text)
        for line in hebrew_clean.split('\n'):
            lines.append(f"    {line}")
    
    # English text
    if source.english_text:
        lines.append("")
        lines.append("    ─── English ───")
        english_clean = strip_html_tags(source.english_text)
        for line in english_clean.split('\n'):
            lines.append(f"    {line}")
    
    # Source separator
    lines.append("")
    lines.append("─" * 60)
    lines.append("")
    
    return lines


def format_nuance_sources_txt(result: "SearchResult", query: str) -> str:
    """Format nuance query results with tiered display."""
    lines = []
    timestamp = datetime.now().isoformat()
    
    # Header
    lines.append("=" * 80)
    lines.append("OHR HANER - NUANCE QUERY RESULTS")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"Query: {query}")
    lines.append(f"Generated: {timestamp}")
    lines.append(f"Total Sources: {result.total_sources}")
    
    # Nuance info
    if hasattr(result, 'landmark_discovery') and result.landmark_discovery:
        discovery = result.landmark_discovery
        lines.append("")
        lines.append("─" * 40)
        lines.append("  NUANCE DETECTION")
        lines.append("─" * 40)
        lines.append(f"Discovery Method: {discovery.discovery_method}")
        lines.append(f"Confidence: {discovery.confidence}")
        if discovery.reasoning:
            lines.append(f"Reasoning: {discovery.reasoning}")
        if discovery.focus_keywords_found:
            lines.append(f"Focus Keywords: {discovery.focus_keywords_found}")
        if discovery.topic_keywords_found:
            lines.append(f"Topic Keywords: {discovery.topic_keywords_found}")
    
    lines.append("")
    lines.append("=" * 80)
    lines.append("")
    lines.append("")
    
    source_num = 1
    
    # ============================================
    # TIER 1: LANDMARK
    # ============================================
    if result.landmark_source:
        lines.append("╔" + "═" * 78 + "╗")
        lines.append("║" + "  ⭐ LANDMARK - THE SOURCE FOR THIS NUANCE".center(78) + "║")
        lines.append("╚" + "═" * 78 + "╝")
        lines.append("")
        
        lines.extend(format_source_txt(result.landmark_source, source_num, show_tier=True))
        source_num += 1
    
    # ============================================
    # TIER 2: PRIMARY SOURCES
    # ============================================
    primary_sources = [s for s in result.foundation_stones if not getattr(s, 'is_landmark', False)]
    primary_sources.extend(result.primary_sources or [])
    
    # Deduplicate
    seen = {result.landmark_source.ref} if result.landmark_source else set()
    unique_primary = []
    for s in primary_sources:
        if s.ref not in seen:
            seen.add(s.ref)
            unique_primary.append(s)
    
    if unique_primary:
        lines.append("")
        lines.append("─" * 40)
        lines.append(f"  📖 PRIMARY SOURCES ({len(unique_primary)} sources)")
        lines.append("  Sources directly discussing this nuance")
        lines.append("─" * 40)
        lines.append("")
        
        for source in unique_primary:
            lines.extend(format_source_txt(source, source_num, show_tier=True))
            source_num += 1
    
    # ============================================
    # TIER 3: COMMENTARIES ON LANDMARK
    # ============================================
    if result.commentary_sources:
        lines.append("")
        lines.append("─" * 40)
        lines.append(f"  📚 COMMENTARIES ({len(result.commentary_sources)} sources)")
        lines.append("  Discussing the landmark and primary sources")
        lines.append("─" * 40)
        lines.append("")
        
        # Sort by focus score
        sorted_commentaries = sorted(
            result.commentary_sources,
            key=lambda s: getattr(s, 'focus_score', 0),
            reverse=True
        )
        
        for source in sorted_commentaries:
            if source.ref not in seen:
                seen.add(source.ref)
                lines.extend(format_source_txt(source, source_num, show_tier=True))
                source_num += 1
    
    # ============================================
    # TIER 4: CONTEXT (CONTRAST REFS)
    # ============================================
    if result.context_sources:
        lines.append("")
        lines.append("─" * 40)
        lines.append(f"  ⚖️ CONTEXT / CONTRAST ({len(result.context_sources)} sources)")
        lines.append("  For comparison - not the main nuance")
        lines.append("─" * 40)
        lines.append("")
        
        for source in result.context_sources:
            if source.ref not in seen:
                seen.add(source.ref)
                lines.extend(format_source_txt(source, source_num, show_tier=True))
                source_num += 1
    
    # ============================================
    # TIER 5: EARLIER SOURCES
    # ============================================
    if result.earlier_sources:
        lines.append("")
        lines.append("─" * 40)
        lines.append(f"  📜 EARLIER SOURCES ({len(result.earlier_sources)} sources)")
        lines.append("  Mishna, Chumash, etc.")
        lines.append("─" * 40)
        lines.append("")
        
        for source in result.earlier_sources:
            if source.ref not in seen:
                seen.add(source.ref)
                lines.extend(format_source_txt(source, source_num, show_tier=False))
                source_num += 1
    
    # Footer
    lines.append("")
    lines.append("=" * 80)
    lines.append("END OF NUANCE QUERY RESULTS")
    lines.append("=" * 80)
    
    return "\n".join(lines)


def format_general_sources_txt(result: "SearchResult", query: str) -> str:
    """Format general query results (non-nuance) grouped by level."""
    lines = []
    timestamp = datetime.now().isoformat()
    
    # Header
    lines.append("=" * 80)
    lines.append("MAREI MEKOMOS - SOURCE OUTPUT")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"Query: {query}")
    lines.append(f"Generated: {timestamp}")
    lines.append(f"Total Sources: {result.total_sources}")
    
    # List base refs if available
    base_refs = []
    if result.foundation_stones:
        base_refs = [s.ref for s in result.foundation_stones[:5]]
    lines.append(f"Base Refs: {', '.join(base_refs) if base_refs else ''}")
    lines.append("")
    lines.append("=" * 80)
    lines.append("")
    lines.append("")
    
    # Combine all sources and group by level
    all_sources = []
    all_sources.extend(result.earlier_sources or [])
    all_sources.extend(result.foundation_stones or [])
    all_sources.extend(result.commentary_sources or [])
    
    # Sort by level
    all_sources = sort_sources_by_level(all_sources)
    
    # Group by level
    grouped = group_sources_by_level(all_sources)
    
    # Output each group
    source_num = 1
    
    for level_key in sorted(grouped.keys(), key=lambda x: LEVEL_ORDER.get(x, 99)):
        sources = grouped[level_key]
        level_name = LEVEL_NAMES.get(level_key, level_key)
        
        # Section header
        lines.append("─" * 40)
        lines.append(f"  {level_name} ({len(sources)} sources)")
        lines.append("─" * 40)
        lines.append("")
        
        for source in sources:
            lines.extend(format_source_txt(source, source_num, show_tier=False))
            source_num += 1
    
    # Footer
    lines.append("")
    lines.append("=" * 80)
    lines.append("END OF SOURCE OUTPUT")
    lines.append("=" * 80)
    
    return "\n".join(lines)


def format_sources_txt(result: "SearchResult", query: str) -> str:
    """Format search results as plain text."""
    # Check if this is a nuance query result
    is_nuance = getattr(result, 'is_nuance_result', False)
    
    if is_nuance:
        return format_nuance_sources_txt(result, query)
    else:
        return format_general_sources_txt(result, query)


def format_sources_html(result: "SearchResult", query: str) -> str:
    """Format search results as HTML with RTL support."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    is_nuance = getattr(result, 'is_nuance_result', False)
    
    html_content = f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>מראי מקומות - {html.escape(query)}</title>
    <style>
        :root {{
            --bg: #1a1a2e;
            --card-bg: #16213e;
            --text: #eee;
            --text-light: #aaa;
            --primary: #e94560;
            --accent: #0f3460;
            --border: #333;
            --landmark-bg: #2d1f3d;
            --landmark-border: #9b59b6;
            --primary-bg: #1f2d3d;
            --context-bg: #2d2d1f;
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: 'David Libre', 'Frank Ruhl Libre', 'SBL Hebrew', serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.8;
            padding: 20px;
            direction: rtl;
        }}
        
        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}
        
        header {{
            background: var(--card-bg);
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            border: 1px solid var(--border);
        }}
        
        h1 {{
            color: var(--primary);
            font-size: 2em;
            margin-bottom: 10px;
        }}
        
        .query {{
            font-size: 1.3em;
            color: var(--text);
            margin: 15px 0;
        }}
        
        .meta {{
            color: var(--text-light);
            font-size: 0.9em;
        }}
        
        .nuance-info {{
            background: var(--landmark-bg);
            border: 1px solid var(--landmark-border);
            border-radius: 8px;
            padding: 15px;
            margin: 20px 0;
        }}
        
        .nuance-info h3 {{
            color: var(--landmark-border);
            margin-bottom: 10px;
        }}
        
        .section {{
            margin-bottom: 30px;
        }}
        
        .section-title {{
            background: var(--accent);
            color: var(--text);
            padding: 15px 20px;
            border-radius: 8px;
            font-size: 1.2em;
            margin-bottom: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .section-title.landmark {{
            background: var(--landmark-bg);
            border: 2px solid var(--landmark-border);
        }}
        
        .section-title.primary {{
            background: var(--primary-bg);
        }}
        
        .section-title.context {{
            background: var(--context-bg);
        }}
        
        .count {{
            background: var(--primary);
            color: white;
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 0.85em;
        }}
        
        .source-card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
        }}
        
        .source-card.landmark {{
            background: var(--landmark-bg);
            border: 2px solid var(--landmark-border);
        }}
        
        .source-ref {{
            font-weight: bold;
            color: var(--primary);
            font-size: 1.1em;
            margin-bottom: 5px;
        }}
        
        .source-he-ref {{
            color: var(--text-light);
            font-size: 0.95em;
            margin-bottom: 10px;
        }}
        
        .source-author {{
            color: var(--text-light);
            font-size: 0.9em;
            margin-bottom: 10px;
        }}
        
        .source-score {{
            color: var(--landmark-border);
            font-size: 0.85em;
            margin-bottom: 10px;
        }}
        
        .source-text {{
            background: rgba(0,0,0,0.2);
            padding: 15px;
            border-radius: 6px;
            border-right: 3px solid var(--accent);
            font-size: 1.05em;
            max-height: 400px;
            overflow-y: auto;
        }}
        
        .landmark-badge {{
            display: inline-block;
            background: var(--landmark-border);
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            margin-left: 10px;
        }}
        
        .summary {{
            background: var(--card-bg);
            border: 2px solid var(--primary);
            border-radius: 8px;
            padding: 20px;
            margin-top: 30px;
        }}
        
        .summary h3 {{
            color: var(--primary);
            margin-bottom: 15px;
        }}
        
        .summary-stats {{
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }}
        
        .stat {{
            background: var(--bg);
            padding: 10px 15px;
            border-radius: 6px;
            text-align: center;
        }}
        
        .stat-value {{
            font-size: 1.5em;
            font-weight: bold;
            color: var(--primary);
        }}
        
        .stat-label {{
            font-size: 0.85em;
            color: var(--text-light);
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🕯️ אור הנר - מראי מקומות</h1>
            <div class="query">{html.escape(query)}</div>
            <div class="meta">נוצר: {timestamp} | סה״כ מקורות: {result.total_sources}</div>
        </header>
"""
    
    # Nuance info box
    if is_nuance and hasattr(result, 'landmark_discovery') and result.landmark_discovery:
        discovery = result.landmark_discovery
        html_content += f"""
        <div class="nuance-info">
            <h3>🎯 Nuance Query Detected</h3>
            <p><strong>Discovery Method:</strong> {html.escape(discovery.discovery_method)}</p>
            <p><strong>Confidence:</strong> {html.escape(discovery.confidence)}</p>
            {f'<p><strong>Reasoning:</strong> {html.escape(discovery.reasoning)}</p>' if discovery.reasoning else ''}
        </div>
"""
    
    # Track seen refs for deduplication
    seen_refs = set()
    
    # LANDMARK SECTION
    if is_nuance and result.landmark_source:
        html_content += """
        <div class="section">
            <div class="section-title landmark">
                ⭐ LANDMARK - המקור המרכזי
                <span class="count">1</span>
            </div>
"""
        s = result.landmark_source
        seen_refs.add(s.ref)
        source_text = s.hebrew_text[:2000] if s.hebrew_text else '<em>אין טקסט</em>'
        focus_score = getattr(s, 'focus_score', 0)
        
        html_content += f"""
            <div class="source-card landmark">
                <div class="source-ref">{html.escape(s.ref)}<span class="landmark-badge">⭐ LANDMARK</span></div>
                {f'<div class="source-he-ref">{html.escape(s.he_ref)}</div>' if s.he_ref and s.he_ref != s.ref else ''}
                {f'<div class="source-author">{html.escape(s.author)}</div>' if s.author else ''}
                {f'<div class="source-score">Focus Score: {focus_score:.1f}</div>' if focus_score > 0 else ''}
                <div class="source-text">{source_text}</div>
            </div>
"""
        html_content += "</div>"
    
    # PRIMARY SOURCES
    primary_sources = []
    if is_nuance:
        primary_sources = [s for s in result.foundation_stones if s.ref not in seen_refs]
        primary_sources.extend([s for s in (result.primary_sources or []) if s.ref not in seen_refs])
    else:
        primary_sources = result.foundation_stones or []
    
    if primary_sources:
        section_class = "primary" if is_nuance else ""
        html_content += f"""
        <div class="section">
            <div class="section-title {section_class}">
                📖 {'PRIMARY SOURCES' if is_nuance else 'יסודות - Foundation Sources'}
                <span class="count">{len(primary_sources)}</span>
            </div>
"""
        for s in primary_sources:
            if s.ref in seen_refs:
                continue
            seen_refs.add(s.ref)
            source_text = s.hebrew_text[:2000] if s.hebrew_text else '<em>אין טקסט</em>'
            focus_score = getattr(s, 'focus_score', 0)
            
            html_content += f"""
            <div class="source-card">
                <div class="source-ref">{html.escape(s.ref)}</div>
                {f'<div class="source-he-ref">{html.escape(s.he_ref)}</div>' if s.he_ref and s.he_ref != s.ref else ''}
                {f'<div class="source-author">{html.escape(s.author)}</div>' if s.author else ''}
                {f'<div class="source-score">Focus Score: {focus_score:.1f}</div>' if focus_score > 0 else ''}
                <div class="source-text">{source_text}</div>
            </div>
"""
        html_content += "</div>"
    
    # COMMENTARIES
    if result.commentary_sources:
        html_content += f"""
        <div class="section">
            <div class="section-title">
                📚 מפרשים - Commentaries
                <span class="count">{len(result.commentary_sources)}</span>
            </div>
"""
        # Sort by focus score for nuance queries
        sorted_comms = sorted(
            result.commentary_sources,
            key=lambda s: getattr(s, 'focus_score', 0),
            reverse=True
        )
        
        for s in sorted_comms:
            if s.ref in seen_refs:
                continue
            seen_refs.add(s.ref)
            source_text = s.hebrew_text[:1500] if s.hebrew_text else '<em>אין טקסט</em>'
            focus_score = getattr(s, 'focus_score', 0)
            
            html_content += f"""
            <div class="source-card">
                <div class="source-ref">{html.escape(s.ref)}</div>
                {f'<div class="source-author">{html.escape(s.author)}</div>' if s.author else ''}
                {f'<div class="source-score">Focus Score: {focus_score:.1f}</div>' if focus_score > 0 and is_nuance else ''}
                <div class="source-text">{source_text}</div>
            </div>
"""
        html_content += "</div>"
    
    # CONTEXT SOURCES (nuance queries only)
    if is_nuance and result.context_sources:
        html_content += f"""
        <div class="section">
            <div class="section-title context">
                ⚖️ CONTEXT / CONTRAST
                <span class="count">{len(result.context_sources)}</span>
            </div>
"""
        for s in result.context_sources:
            if s.ref in seen_refs:
                continue
            seen_refs.add(s.ref)
            source_text = s.hebrew_text[:1500] if s.hebrew_text else '<em>אין טקסט</em>'
            
            html_content += f"""
            <div class="source-card">
                <div class="source-ref">{html.escape(s.ref)}</div>
                {f'<div class="source-he-ref">{html.escape(s.he_ref)}</div>' if s.he_ref and s.he_ref != s.ref else ''}
                <div class="source-text">{source_text}</div>
            </div>
"""
        html_content += "</div>"
    
    # EARLIER SOURCES
    if result.earlier_sources:
        html_content += f"""
        <div class="section">
            <div class="section-title">
                📜 מקורות קדומים - Earlier Sources
                <span class="count">{len(result.earlier_sources)}</span>
            </div>
"""
        for s in result.earlier_sources:
            if s.ref in seen_refs:
                continue
            seen_refs.add(s.ref)
            source_text = s.hebrew_text[:1000] if s.hebrew_text else '<em>אין טקסט</em>'
            
            html_content += f"""
            <div class="source-card">
                <div class="source-ref">{html.escape(s.ref)}</div>
                <div class="source-text">{source_text}</div>
            </div>
"""
        html_content += "</div>"
    
    # Summary
    html_content += f"""
        <div class="summary">
            <h3>סיכום</h3>
            <div class="summary-stats">
                {'<div class="stat"><div class="stat-value">⭐</div><div class="stat-label">Landmark</div></div>' if is_nuance and result.landmark_source else ''}
                <div class="stat">
                    <div class="stat-value">{len(result.foundation_stones or [])}</div>
                    <div class="stat-label">יסודות</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{len(result.commentary_sources or [])}</div>
                    <div class="stat-label">מפרשים</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{result.total_sources}</div>
                    <div class="stat-label">סה״כ</div>
                </div>
            </div>
            <p style="margin-top: 15px; color: var(--text-light);">{html.escape(result.search_description)}</p>
        </div>
    </div>
</body>
</html>
"""
    
    return html_content


class SourceOutputWriter:
    """Writes search results to output files."""
    
    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or OUTPUT_DIR
        self.output_dir.mkdir(exist_ok=True)
    
    def write_results(
        self,
        result: "SearchResult",
        query: str,
        formats: List[str] = None
    ) -> dict:
        """
        Write results to output files.
        
        Args:
            result: SearchResult from step 3
            query: Original query string
            formats: List of formats to write ("txt", "html"). Default: both.
        
        Returns:
            Dict mapping format to output file path
        """
        if formats is None:
            formats = ["txt", "html"]
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = sanitize_filename(query)
        
        output_files = {}
        
        if "txt" in formats:
            txt_content = format_sources_txt(result, query)
            txt_path = self.output_dir / f"sources_{safe_query}_{timestamp}.txt"
            txt_path.write_text(txt_content, encoding='utf-8')
            output_files["txt"] = txt_path
            logger.info(f"Wrote TXT output: {txt_path}")
        
        if "html" in formats:
            html_content = format_sources_html(result, query)
            html_path = self.output_dir / f"sources_{safe_query}_{timestamp}.html"
            html_path.write_text(html_content, encoding='utf-8')
            output_files["html"] = html_path
            logger.info(f"Wrote HTML output: {html_path}")
        
        return output_files


# Convenience function
def write_output(result: "SearchResult", query: str, formats: List[str] = None) -> dict:
    """Write search results to output files."""
    writer = SourceOutputWriter()
    return writer.write_results(result, query, formats)