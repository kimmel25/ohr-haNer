"""
Shared level metadata and ordering.
"""

from typing import Dict

from models import SourceLevel

# Hebrew names for display (keys are SourceLevel values)
LEVEL_HEBREW_NAMES: Dict[str, str] = {
    "chumash": "חומש",
    "mishna": "משנה",
    "gemara": "גמרא",
    "rashi": 'רש"י',
    "tosfos": "תוספות",
    "rishonim": "ראשונים",
    "rambam": 'רמב"ם',
    "tur": "טור",
    "shulchan_aruch": "שולחן ערוך",
    "nosei_keilim": "נושאי כלים",
    "acharonim": "אחרונים",
    "other": "אחר",
}


def get_level_order(level: SourceLevel) -> int:
    """Return the numeric order for a SourceLevel for sorting."""
    order_map = {
        SourceLevel.CHUMASH: 1,
        SourceLevel.MISHNA: 2,
        SourceLevel.GEMARA: 3,
        SourceLevel.RASHI: 4,
        SourceLevel.TOSFOS: 5,
        SourceLevel.RISHONIM: 6,
        SourceLevel.RAMBAM: 7,
        SourceLevel.TUR: 8,
        SourceLevel.SHULCHAN_ARUCH: 9,
        SourceLevel.NOSEI_KEILIM: 10,
        SourceLevel.ACHARONIM: 11,
        SourceLevel.OTHER: 99,
    }
    return order_map.get(level, 99)

