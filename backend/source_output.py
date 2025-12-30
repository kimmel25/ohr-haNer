"""
Source Output Writer for Ohr Haner V2
======================================

Generates formatted output files (TXT and HTML) from search results.
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import re
import html

# Initialize logging - FIXED: removed 'logging.' prefix
try:
    from logging.logging_config import setup_logging
    setup_logging()
except ImportError:
    # Fallback to basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

try:
    from step_three_search import SearchResult, Source, SourceLevel
except ImportError:
    # Will be imported at runtime
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


def sort_sources_by_level(sources: List["Source"]) -> List["Source"]:
    """Sort sources by traditional learning hierarchy."""
    def get_level_priority(source):
        level_str = source.level.value if hasattr(source.level, 'value') else str(source.level)
        return LEVEL_ORDER.get(level_str, 99)
    
    return sorted(sources, key=get_level_priority)


def sanitize_filename(query: str) -> str:
    """Create a safe filename from query."""
    # Remove/replace problematic characters
    safe = re.sub(r'[<>:"/\\|?*]', '', query)
    safe = re.sub(r'\s+', '_', safe)
    safe = safe[:50]  # Limit length
    return safe or "query"


def strip_html_tags(text: str) -> str:
    """
    Remove HTML tags from text for plain text output.
    Converts <br> to newlines, strips all other tags.
    """
    if not text:
        return ""
    
    # Convert <br> and <br/> to newlines
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    
    # Convert </p> and </div> to newlines (paragraph breaks)
    text = re.sub(r'</p>|</div>', '\n', text, flags=re.IGNORECASE)
    
    # Remove all other HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Decode HTML entities
    text = html.unescape(text)
    
    # Clean up multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Clean up whitespace
    text = text.strip()
    
    return text


def format_sources_txt(result: "SearchResult", query: str) -> str:
    """Format search results as plain text."""
    lines = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    lines.append("=" * 70)
    lines.append("                         OHR HANER - MAREI MEKOMOS")
    lines.append("=" * 70)
    lines.append(f"Query: {query}")
    lines.append(f"Generated: {timestamp}")
    lines.append(f"Confidence: {result.confidence.value if hasattr(result.confidence, 'value') else result.confidence}")
    lines.append("=" * 70)
    lines.append("")
    
    # TRADITIONAL LEARNING ORDER: Earlier → Foundation → Commentaries
    
    # 1. Earlier sources (Chumash, Mishna, etc.)
    if result.earlier_sources:
        lines.append("╔" + "═" * 68 + "╗")
        lines.append("║" + "  📜 EARLIER SOURCES (מקורות קדומים)".center(68) + "║")
        lines.append("╚" + "═" * 68 + "╝")
        lines.append("")
        
        for i, s in enumerate(result.earlier_sources, 1):
            lines.append(f"┌─ [{i}] {s.ref}")
            if s.he_ref and s.he_ref != s.ref:
                lines.append(f"│  {s.he_ref}")
            if s.hebrew_text:
                # Strip HTML tags for plain text output
                text = strip_html_tags(s.hebrew_text)
                wrapped = wrap_text(text, 65)
                for line in wrapped[:8]:
                    lines.append(f"│  {line}")
                if len(wrapped) > 8:
                    lines.append(f"│  ... ({len(wrapped) - 8} more lines)")
            lines.append("└" + "─" * 50)
            lines.append("")
    
    # 2. Foundation stones (Gemara)
    if result.foundation_stones:
        lines.append("╔" + "═" * 68 + "╗")
        lines.append("║" + "  📖 FOUNDATION SOURCES (יסודות)".center(68) + "║")
        lines.append("╚" + "═" * 68 + "╝")
        lines.append("")
        
        for i, s in enumerate(result.foundation_stones, 1):
            lines.append(f"┌─ [{i}] {s.ref}")
            if s.he_ref and s.he_ref != s.ref:
                lines.append(f"│  {s.he_ref}")
            lines.append("│")
            if s.hebrew_text:
                # Strip HTML tags for plain text output
                text = strip_html_tags(s.hebrew_text)
                wrapped = wrap_text(text, 65)
                for line in wrapped[:20]:  # Limit lines
                    lines.append(f"│  {line}")
                if len(wrapped) > 20:
                    lines.append(f"│  ... ({len(wrapped) - 20} more lines)")
            lines.append("└" + "─" * 50)
            lines.append("")
    
    # 3. Commentaries (Rashi → Tosafos → Rishonim → Acharonim)
    if result.commentary_sources:
        lines.append("╔" + "═" * 68 + "╗")
        lines.append("║" + "  📚 COMMENTARIES (מפרשים)".center(68) + "║")
        lines.append("╚" + "═" * 68 + "╝")
        lines.append("")
        
        # Sort commentaries by traditional order
        sorted_commentaries = sort_sources_by_level(result.commentary_sources)
        
        for i, s in enumerate(sorted_commentaries, 1):
            lines.append(f"┌─ [{i}] {s.ref}")
            if s.author:
                lines.append(f"│  Author: {s.author}")
            if s.hebrew_text:
                # Strip HTML tags for plain text output
                text = strip_html_tags(s.hebrew_text)
                wrapped = wrap_text(text, 65)
                for line in wrapped[:10]:
                    lines.append(f"│  {line}")
                if len(wrapped) > 10:
                    lines.append(f"│  ... ({len(wrapped) - 10} more lines)")
            lines.append("└" + "─" * 50)
            lines.append("")
    
    # Summary
    lines.append("=" * 70)
    lines.append("SUMMARY")
    lines.append("=" * 70)
    lines.append(f"Earlier sources: {len(result.earlier_sources)}")
    lines.append(f"Foundation stones: {len(result.foundation_stones)}")
    lines.append(f"Commentaries: {len(result.commentary_sources)}")
    lines.append(f"Total sources: {result.total_sources}")
    lines.append("")
    lines.append(result.search_description)
    lines.append("=" * 70)
    
    return "\n".join(lines)


def wrap_text(text: str, width: int) -> List[str]:
    """Word wrap text to specified width."""
    lines = []
    for paragraph in text.split('\n'):
        if not paragraph.strip():
            lines.append("")
            continue
        
        words = paragraph.split()
        current_line = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 <= width:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
                current_length = len(word)
        
        if current_line:
            lines.append(" ".join(current_line))
    
    return lines


def format_sources_html(result: "SearchResult", query: str) -> str:
    """Format search results as HTML."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    html_content = f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>מראי מקומות - {html.escape(query)}</title>
    <style>
        :root {{
            --primary: #1a365d;
            --secondary: #2c5282;
            --accent: #ed8936;
            --bg: #f7fafc;
            --card-bg: #ffffff;
            --text: #2d3748;
            --text-light: #718096;
            --border: #e2e8f0;
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: 'David Libre', 'Frank Ruhl Libre', 'Times New Roman', serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.8;
            padding: 20px;
        }}
        
        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}
        
        header {{
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            text-align: center;
        }}
        
        header h1 {{
            font-size: 2em;
            margin-bottom: 10px;
        }}
        
        header .query {{
            font-size: 1.3em;
            opacity: 0.9;
        }}
        
        header .meta {{
            font-size: 0.85em;
            opacity: 0.7;
            margin-top: 10px;
        }}
        
        .section {{
            margin-bottom: 30px;
        }}
        
        .section-title {{
            background: var(--secondary);
            color: white;
            padding: 12px 20px;
            border-radius: 8px 8px 0 0;
            font-size: 1.2em;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .section-title .count {{
            background: var(--accent);
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 0.8em;
        }}
        
        .source-card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-top: none;
            padding: 20px;
        }}
        
        .source-card:last-child {{
            border-radius: 0 0 8px 8px;
        }}
        
        .source-card + .source-card {{
            border-top: 1px solid var(--border);
        }}
        
        .source-ref {{
            font-weight: bold;
            color: var(--primary);
            font-size: 1.1em;
            margin-bottom: 5px;
        }}
        
        .source-author {{
            color: var(--text-light);
            font-size: 0.9em;
            margin-bottom: 10px;
        }}
        
        .source-text {{
            background: #fafafa;
            padding: 15px;
            border-radius: 6px;
            border-right: 3px solid var(--accent);
            font-size: 1.05em;
            max-height: 300px;
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
            margin-bottom: 10px;
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
        
        .empty-section {{
            color: var(--text-light);
            font-style: italic;
            padding: 20px;
            text-align: center;
        }}
        
        @media (max-width: 600px) {{
            body {{
                padding: 10px;
            }}
            
            header {{
                padding: 20px;
            }}
            
            .summary-stats {{
                flex-direction: column;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🕯️ אור הנר - מראי מקומות</h1>
            <div class="query">{html.escape(query)}</div>
            <div class="meta">נוצר: {timestamp} | רמת ביטחון: {result.confidence.value if hasattr(result.confidence, 'value') else result.confidence}</div>
        </header>
"""
    
    # TRADITIONAL LEARNING ORDER: Earlier → Foundation → Commentaries
    
    # 1. Earlier sources
    html_content += """
        <div class="section">
            <div class="section-title">
                📜 מקורות קדומים - Earlier Sources
                <span class="count">{count}</span>
            </div>
""".format(count=len(result.earlier_sources))
    
    if result.earlier_sources:
        for s in result.earlier_sources:
            # For HTML output, we keep the HTML but escape any user-injected content
            source_text = s.hebrew_text[:1000] if s.hebrew_text else '<em>No text available</em>'
            html_content += f"""
            <div class="source-card">
                <div class="source-ref">{html.escape(s.ref)}</div>
                <div class="source-text">{source_text}</div>
            </div>
"""
    else:
        html_content += '<div class="source-card empty-section">No earlier sources found</div>'
    
    html_content += "</div>"
    
    # 2. Foundation stones
    html_content += """
        <div class="section">
            <div class="section-title">
                📖 יסודות - Foundation Sources
                <span class="count">{count}</span>
            </div>
""".format(count=len(result.foundation_stones))
    
    if result.foundation_stones:
        for s in result.foundation_stones:
            source_text = s.hebrew_text[:2000] if s.hebrew_text else '<em>No text available</em>'
            html_content += f"""
            <div class="source-card">
                <div class="source-ref">{html.escape(s.ref)}</div>
                {f'<div class="source-author">{html.escape(s.he_ref)}</div>' if s.he_ref and s.he_ref != s.ref else ''}
                <div class="source-text">{source_text}</div>
            </div>
"""
    else:
        html_content += '<div class="source-card empty-section">No foundation sources found</div>'
    
    html_content += "</div>"
    
    # 3. Commentaries (sorted by level)
    html_content += """
        <div class="section">
            <div class="section-title">
                📚 מפרשים - Commentaries
                <span class="count">{count}</span>
            </div>
""".format(count=len(result.commentary_sources))
    
    if result.commentary_sources:
        sorted_commentaries = sort_sources_by_level(result.commentary_sources)
        for s in sorted_commentaries:
            source_text = s.hebrew_text[:1500] if s.hebrew_text else '<em>No text available</em>'
            html_content += f"""
            <div class="source-card">
                <div class="source-ref">{html.escape(s.ref)}</div>
                {f'<div class="source-author">{html.escape(s.author)}</div>' if s.author else ''}
                <div class="source-text">{source_text}</div>
            </div>
"""
    else:
        html_content += '<div class="source-card empty-section">No commentaries found</div>'
    
    html_content += "</div>"
    
    # Summary
    html_content += f"""
        <div class="summary">
            <h3>סיכום - Summary</h3>
            <div class="summary-stats">
                <div class="stat">
                    <div class="stat-value">{len(result.earlier_sources)}</div>
                    <div class="stat-label">Earlier</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{len(result.foundation_stones)}</div>
                    <div class="stat-label">Foundation</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{len(result.commentary_sources)}</div>
                    <div class="stat-label">Commentaries</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{result.total_sources}</div>
                    <div class="stat-label">Total</div>
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