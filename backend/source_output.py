"""
Source Text Output
==================

Creates readable output files containing the actual text of fetched sources.
This allows review and verification of the sources returned by the pipeline.

Output formats:
1. Text file (.txt) - Simple readable format
2. JSON file (.json) - Structured data for programmatic access
3. HTML file (.html) - Formatted for browser viewing with Hebrew support

Usage:
    from source_output import SourceOutputWriter
    
    writer = SourceOutputWriter(output_dir="output")
    writer.write_results(search_result, query="bittul chometz")
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class SourceForOutput:
    """Normalized source data for output."""
    ref: str
    he_ref: str
    author: str
    level: str
    level_hebrew: str
    hebrew_text: str
    english_text: str
    char_count: int
    
    @classmethod
    def from_source(cls, source: Any) -> 'SourceForOutput':
        """Create from a Source object or dict."""
        if isinstance(source, dict):
            hebrew = source.get('hebrew_text', '') or ''
            return cls(
                ref=source.get('ref', ''),
                he_ref=source.get('he_ref', source.get('ref', '')),
                author=source.get('author', ''),
                level=source.get('level', ''),
                level_hebrew=source.get('level_hebrew', ''),
                hebrew_text=hebrew,
                english_text=source.get('english_text', '') or '',
                char_count=len(hebrew)
            )
        else:
            hebrew = getattr(source, 'hebrew_text', '') or ''
            return cls(
                ref=getattr(source, 'ref', ''),
                he_ref=getattr(source, 'he_ref', getattr(source, 'ref', '')),
                author=getattr(source, 'author', ''),
                level=getattr(source, 'level', ''),
                level_hebrew=getattr(source, 'level_hebrew', ''),
                hebrew_text=hebrew,
                english_text=getattr(source, 'english_text', '') or '',
                char_count=len(hebrew)
            )


class SourceOutputWriter:
    """Writes search results to readable output files."""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def write_results(
        self,
        search_result: Any,
        query: str = "",
        formats: List[str] = None
    ) -> Dict[str, Path]:
        """
        Write search results to output files.
        
        Args:
            search_result: SearchResult object with sources
            query: Original query string
            formats: List of formats to output ("txt", "json", "html")
                    Default: all three
        
        Returns:
            Dict mapping format to output file path
        """
        if formats is None:
            formats = ["txt", "json", "html"]
        
        # Generate timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"sources_{timestamp}"
        
        # Extract sources
        sources = self._extract_sources(search_result)
        
        # Metadata
        metadata = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "total_sources": len(sources),
            "base_refs": getattr(search_result, 'base_refs_found', []),
        }
        
        output_files = {}
        
        if "txt" in formats:
            txt_path = self.output_dir / f"{base_name}.txt"
            self._write_txt(txt_path, sources, metadata)
            output_files["txt"] = txt_path
            logger.info(f"[OUTPUT] Written: {txt_path}")
        
        if "json" in formats:
            json_path = self.output_dir / f"{base_name}.json"
            self._write_json(json_path, sources, metadata)
            output_files["json"] = json_path
            logger.info(f"[OUTPUT] Written: {json_path}")
        
        if "html" in formats:
            html_path = self.output_dir / f"{base_name}.html"
            self._write_html(html_path, sources, metadata)
            output_files["html"] = html_path
            logger.info(f"[OUTPUT] Written: {html_path}")
        
        return output_files
    
    def _extract_sources(self, search_result: Any) -> List[SourceForOutput]:
        """Extract and normalize sources from search result."""
        sources = []
        
        # Try to get sources from the result
        raw_sources = getattr(search_result, 'sources', [])
        
        for src in raw_sources:
            try:
                sources.append(SourceForOutput.from_source(src))
            except Exception as e:
                logger.warning(f"Could not process source: {e}")
        
        return sources
    
    def _write_txt(
        self,
        path: Path,
        sources: List[SourceForOutput],
        metadata: Dict
    ):
        """Write plain text output."""
        with open(path, 'w', encoding='utf-8') as f:
            # Header
            f.write("=" * 80 + "\n")
            f.write("MAREI MEKOMOS - SOURCE OUTPUT\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Query: {metadata['query']}\n")
            f.write(f"Generated: {metadata['timestamp']}\n")
            f.write(f"Total Sources: {metadata['total_sources']}\n")
            f.write(f"Base Refs: {', '.join(metadata['base_refs'])}\n")
            f.write("\n" + "=" * 80 + "\n\n")
            
            # Group by level
            by_level = {}
            for src in sources:
                level = src.level_hebrew or src.level or "Other"
                if level not in by_level:
                    by_level[level] = []
                by_level[level].append(src)
            
            # Write each level
            for level, level_sources in by_level.items():
                f.write(f"\n{'─' * 40}\n")
                f.write(f"  {level} ({len(level_sources)} sources)\n")
                f.write(f"{'─' * 40}\n\n")
                
                for i, src in enumerate(level_sources, 1):
                    f.write(f"[{i}] {src.ref}\n")
                    if src.he_ref and src.he_ref != src.ref:
                        f.write(f"    {src.he_ref}\n")
                    f.write(f"    Author: {src.author}\n")
                    f.write(f"    Characters: {src.char_count}\n")
                    f.write("\n")
                    
                    # Hebrew text
                    f.write("    ─── Hebrew ───\n")
                    # Wrap text for readability
                    hebrew_lines = self._wrap_text(src.hebrew_text, 70)
                    for line in hebrew_lines:
                        f.write(f"    {line}\n")
                    
                    # English if available
                    if src.english_text:
                        f.write("\n    ─── English ───\n")
                        english_lines = self._wrap_text(src.english_text, 70)
                        for line in english_lines:
                            f.write(f"    {line}\n")
                    
                    f.write("\n" + "─" * 60 + "\n\n")
            
            # Footer
            f.write("\n" + "=" * 80 + "\n")
            f.write("END OF SOURCE OUTPUT\n")
            f.write("=" * 80 + "\n")
    
    def _write_json(
        self,
        path: Path,
        sources: List[SourceForOutput],
        metadata: Dict
    ):
        """Write JSON output."""
        output = {
            "metadata": metadata,
            "sources": [asdict(src) for src in sources]
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
    
    def _write_html(
        self,
        path: Path,
        sources: List[SourceForOutput],
        metadata: Dict
    ):
        """Write HTML output with proper Hebrew formatting."""
        html = f'''<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Marei Mekomos - {metadata['query']}</title>
    <style>
        body {{
            font-family: 'David', 'Times New Roman', serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background: #fafafa;
            line-height: 1.8;
        }}
        .header {{
            text-align: center;
            border-bottom: 2px solid #333;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #1a1a1a;
            font-size: 2em;
        }}
        .metadata {{
            background: #f0f0f0;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 30px;
            direction: ltr;
            text-align: left;
            font-family: monospace;
        }}
        .level-section {{
            margin-bottom: 40px;
        }}
        .level-header {{
            background: #333;
            color: white;
            padding: 10px 20px;
            border-radius: 5px;
            font-size: 1.3em;
        }}
        .source {{
            background: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 20px;
            margin: 15px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .source-header {{
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
            margin-bottom: 15px;
        }}
        .source-ref {{
            font-weight: bold;
            font-size: 1.1em;
            color: #0066cc;
        }}
        .source-meta {{
            color: #666;
            font-size: 0.9em;
            direction: ltr;
        }}
        .source-text {{
            font-size: 1.2em;
            line-height: 2;
            text-align: justify;
        }}
        .hebrew-text {{
            direction: rtl;
            font-family: 'David', 'Times New Roman', serif;
        }}
        .english-text {{
            direction: ltr;
            text-align: left;
            font-family: Georgia, serif;
            color: #444;
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px dashed #ccc;
        }}
        .toggle-btn {{
            background: #eee;
            border: 1px solid #ccc;
            padding: 5px 10px;
            cursor: pointer;
            border-radius: 3px;
            font-size: 0.8em;
        }}
        .toggle-btn:hover {{
            background: #ddd;
        }}
        .hidden {{
            display: none;
        }}
    </style>
    <script>
        function toggleEnglish(id) {{
            var el = document.getElementById(id);
            el.classList.toggle('hidden');
        }}
    </script>
</head>
<body>
    <div class="header">
        <h1>מראה מקומות</h1>
        <p>Source Output</p>
    </div>
    
    <div class="metadata">
        <strong>Query:</strong> {metadata['query']}<br>
        <strong>Generated:</strong> {metadata['timestamp']}<br>
        <strong>Total Sources:</strong> {metadata['total_sources']}<br>
        <strong>Base Refs:</strong> {', '.join(metadata['base_refs'])}
    </div>
'''
        
        # Group by level
        by_level = {}
        for src in sources:
            level = src.level_hebrew or src.level or "Other"
            if level not in by_level:
                by_level[level] = []
            by_level[level].append(src)
        
        # Write each level
        for level, level_sources in by_level.items():
            html += f'''
    <div class="level-section">
        <div class="level-header">{level} ({len(level_sources)})</div>
'''
            
            for i, src in enumerate(level_sources, 1):
                eng_id = f"eng_{level}_{i}"
                html += f'''
        <div class="source">
            <div class="source-header">
                <div class="source-ref">{src.he_ref}</div>
                <div class="source-meta">{src.ref} | {src.author} | {src.char_count} chars</div>
            </div>
            <div class="source-text hebrew-text">
                {src.hebrew_text}
            </div>
'''
                if src.english_text:
                    html += f'''
            <button class="toggle-btn" onclick="toggleEnglish('{eng_id}')">Toggle English</button>
            <div id="{eng_id}" class="source-text english-text hidden">
                {src.english_text}
            </div>
'''
                html += '''
        </div>
'''
            
            html += '''
    </div>
'''
        
        html += '''
</body>
</html>
'''
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
    
    def _wrap_text(self, text: str, width: int) -> List[str]:
        """Wrap text to specified width."""
        if not text:
            return []
        
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 <= width:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def write_source_output(
    search_result: Any,
    query: str = "",
    output_dir: str = "output",
    formats: List[str] = None
) -> Dict[str, Path]:
    """
    Convenience function to write source output.
    
    Args:
        search_result: SearchResult from Step 3
        query: Original query
        output_dir: Directory for output files
        formats: List of formats ("txt", "json", "html")
    
    Returns:
        Dict of format -> file path
    """
    writer = SourceOutputWriter(output_dir)
    return writer.write_results(search_result, query, formats)


# =============================================================================
# STANDALONE SOURCE FILE WRITER (Simpler version)
# =============================================================================

def write_sources_to_file(
    sources: List[Any],
    output_path: str,
    query: str = "",
    base_refs: List[str] = None
):
    """
    Simple function to write sources to a text file.
    
    Can be called directly without a SearchResult object.
    
    Args:
        sources: List of Source objects or dicts
        output_path: Path for output file
        query: Query string for header
        base_refs: List of base refs found
    """
    base_refs = base_refs or []
    
    with open(output_path, 'w', encoding='utf-8') as f:
        # Header
        f.write("=" * 80 + "\n")
        f.write("MAREI MEKOMOS - SOURCE TEXT OUTPUT\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Query: {query}\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Total Sources: {len(sources)}\n")
        f.write(f"Base Gemara Refs: {', '.join(base_refs)}\n")
        f.write("\n" + "=" * 80 + "\n")
        
        # Group by author for easier reading
        by_author = {}
        for src in sources:
            if isinstance(src, dict):
                author = src.get('author', 'Unknown')
                ref = src.get('ref', '')
                hebrew = src.get('hebrew_text', '')
                english = src.get('english_text', '')
            else:
                author = getattr(src, 'author', 'Unknown')
                ref = getattr(src, 'ref', '')
                hebrew = getattr(src, 'hebrew_text', '')
                english = getattr(src, 'english_text', '')
            
            if author not in by_author:
                by_author[author] = []
            by_author[author].append((ref, hebrew, english))
        
        # Write each author's sources
        for author in sorted(by_author.keys()):
            author_sources = by_author[author]
            f.write(f"\n\n{'═' * 80}\n")
            f.write(f"  {author} ({len(author_sources)} sources)\n")
            f.write(f"{'═' * 80}\n")
            
            for ref, hebrew, english in author_sources:
                f.write(f"\n{'─' * 60}\n")
                f.write(f"📖 {ref}\n")
                f.write(f"{'─' * 60}\n\n")
                
                # Hebrew text
                if hebrew:
                    f.write(hebrew)
                    f.write("\n")
                else:
                    f.write("[No Hebrew text]\n")
                
                # English if available
                if english:
                    f.write(f"\n--- English ---\n")
                    f.write(english)
                    f.write("\n")
                
                f.write("\n")
        
        # Footer
        f.write("\n" + "=" * 80 + "\n")
        f.write("END OF OUTPUT\n")
        f.write("=" * 80 + "\n")
    
    logger.info(f"[OUTPUT] Written {len(sources)} sources to {output_path}")