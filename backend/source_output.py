"""
Source Output Writer for Ohr Haner V2
======================================

Generates formatted output files (TXT and HTML) from search results.
Clean, simple format optimized for reading in VS Code and text editors.
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict
import re
import html

# Initialize logging
try:
    from logging.logging_config import setup_logging
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
    "pasuk": 1,
    "targum": 2,
    "mishna": 3,
    "tosefta": 4,
    "gemara": 5,
    "rashi": 6,
    "tosafos": 7,
    "rishonim": 8,
    "rambam": 9,
    "tur": 10,
    "shulchan_aruch": 11,
    "nosei_keilim": 12,
    "acharonim": 13,
    "other": 14
}

# Level display names (Hebrew)
LEVEL_NAMES = {
    "pasuk": "פסוקים",
    "targum": "תרגום",
    "mishna": "משנה",
    "tosefta": "תוספתא",
    "gemara": "גמרא בבלי",
    "rashi": "רש\"י",
    "tosafos": "תוספות",
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


def format_sources_txt(result: "SearchResult", query: str) -> str:
    """
    Format search results as plain text.
    
    Simple, clean format optimized for VS Code scrolling:
    - Section headers with source counts
    - Numbered sources with ref, Hebrew ref, author
    - Hebrew and English text sections
    """
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
    
    # Process in level order
    for level_key in sorted(grouped.keys(), key=lambda x: LEVEL_ORDER.get(x, 99)):
        sources = grouped[level_key]
        level_name = LEVEL_NAMES.get(level_key, level_key)
        
        # Section header
        lines.append("─" * 40)
        lines.append(f"  {level_name} ({len(sources)} sources)")
        lines.append("─" * 40)
        lines.append("")
        
        for source in sources:
            # Source header
            lines.append(f"[{source_num}] {source.ref}")
            
            # Hebrew ref if different
            if source.he_ref and source.he_ref != source.ref:
                lines.append(f"    {source.he_ref}")
            
            # Author
            author = source.author if source.author else ""
            lines.append(f"    Author: {author}")
            
            # Character count
            total_chars = len(source.hebrew_text or "") + len(source.english_text or "")
            lines.append(f"    Characters: {total_chars}")
            lines.append("")
            
            # Hebrew text
            if source.hebrew_text:
                lines.append("    ─── Hebrew ───")
                hebrew_clean = strip_html_tags(source.hebrew_text)
                # Indent each line
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
            
            source_num += 1
    
    # Footer
    lines.append("")
    lines.append("=" * 80)
    lines.append("END OF SOURCE OUTPUT")
    lines.append("=" * 80)
    
    return "\n".join(lines)


def format_sources_html(result: "SearchResult", query: str) -> str:
    """Format search results as HTML with RTL support."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
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
        
        .source-text {{
            background: rgba(0,0,0,0.2);
            padding: 15px;
            border-radius: 6px;
            border-right: 3px solid var(--accent);
            font-size: 1.05em;
            max-height: 400px;
            overflow-y: auto;
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
    
    # Combine and sort all sources
    all_sources = []
    all_sources.extend(result.earlier_sources or [])
    all_sources.extend(result.foundation_stones or [])
    all_sources.extend(result.commentary_sources or [])
    all_sources = sort_sources_by_level(all_sources)
    
    # Group by level
    grouped = group_sources_by_level(all_sources)
    
    # Output each group
    for level_key in sorted(grouped.keys(), key=lambda x: LEVEL_ORDER.get(x, 99)):
        sources = grouped[level_key]
        level_name = LEVEL_NAMES.get(level_key, level_key)
        
        html_content += f"""
        <div class="section">
            <div class="section-title">
                {level_name}
                <span class="count">{len(sources)}</span>
            </div>
"""
        
        for source in sources:
            source_text = source.hebrew_text[:2000] if source.hebrew_text else '<em>אין טקסט</em>'
            
            html_content += f"""
            <div class="source-card">
                <div class="source-ref">{html.escape(source.ref)}</div>
                {f'<div class="source-he-ref">{html.escape(source.he_ref)}</div>' if source.he_ref and source.he_ref != source.ref else ''}
                {f'<div class="source-author">{html.escape(source.author)}</div>' if source.author else ''}
                <div class="source-text">{source_text}</div>
            </div>
"""
        
        html_content += "</div>"
    
    # Summary
    html_content += f"""
        <div class="summary">
            <h3>סיכום</h3>
            <div class="summary-stats">
                <div class="stat">
                    <div class="stat-value">{len(result.earlier_sources or [])}</div>
                    <div class="stat-label">מקורות קדומים</div>
                </div>
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