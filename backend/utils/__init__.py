"""
Shared utility helpers for the Marei Mekomos backend.

Modules:
- serialization: enum/value helpers and safe serialization
- levels: shared level metadata and ordering
- fallbacks: fallback behaviors for pipeline steps
- token_tracker: API token usage tracking and cost calculation
"""

try:
    from .token_tracker import (
        TokenTracker,
        get_global_tracker,
        reset_global_tracker,
        track_tokens,
        print_global_summary,
        get_global_summary,
        MODEL_PRICING,
        get_pricing,
    )

    __all__ = [
        "TokenTracker",
        "get_global_tracker",
        "reset_global_tracker",
        "track_tokens",
        "print_global_summary",
        "get_global_summary",
        "MODEL_PRICING",
        "get_pricing",
    ]
except ImportError:
    # Token tracking optional
    __all__ = []
