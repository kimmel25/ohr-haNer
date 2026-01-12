"""
Token Tracking Utility for Marei Mekomos
=========================================

Tracks API token usage and calculates costs for Google Gemini API calls.

PRICING (as of January 2025):
Google Gemini 2.0 Flash:
- Input: $0.10 per 1M tokens (up to 128K context)
- Output: $0.40 per 1M tokens (up to 128K context)

USAGE:
    from utils.token_tracker import TokenTracker, track_tokens

    # Method 1: Context manager (automatic tracking)
    with track_tokens("Step 2: Understanding") as tracker:
        response = model.generate_content(prompt)
        tracker.record_from_response(response)

    # Method 2: Manual tracking
    tracker = TokenTracker()
    response = model.generate_content(prompt)
    tracker.record(response.usage_metadata.prompt_token_count,
                   response.usage_metadata.candidates_token_count)

    # Get summary
    summary = tracker.get_summary()
    print(f"Cost: ${summary['total_cost']:.4f}")
"""

import logging
import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from contextlib import contextmanager
from threading import Lock

logger = logging.getLogger(__name__)


# ==============================================================================
#  PRICING CONFIGURATION
# ==============================================================================

@dataclass
class ModelPricing:
    """Pricing information for a specific model."""
    model_name: str
    input_price_per_1m: float  # Price per 1M input tokens
    output_price_per_1m: float  # Price per 1M output tokens

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate total cost for given token counts."""
        input_cost = (input_tokens / 1_000_000) * self.input_price_per_1m
        output_cost = (output_tokens / 1_000_000) * self.output_price_per_1m
        return input_cost + output_cost


# Pricing database
MODEL_PRICING = {
    "gemini-2.0-flash": ModelPricing(
        model_name="gemini-2.0-flash",
        input_price_per_1m=0.10,
        output_price_per_1m=0.40,
    ),
    "gemini-2.0-flash-exp": ModelPricing(
        model_name="gemini-2.0-flash-exp",
        input_price_per_1m=0.00,  # Free during preview
        output_price_per_1m=0.00,
    ),
    "gemini-1.5-flash": ModelPricing(
        model_name="gemini-1.5-flash",
        input_price_per_1m=0.075,
        output_price_per_1m=0.30,
    ),
    "gemini-1.5-pro": ModelPricing(
        model_name="gemini-1.5-pro",
        input_price_per_1m=1.25,
        output_price_per_1m=5.00,
    ),
}


def get_pricing(model_name: str) -> ModelPricing:
    """Get pricing for a model, with fallback to gemini-2.0-flash."""
    # Try exact match
    if model_name in MODEL_PRICING:
        return MODEL_PRICING[model_name]

    # Try prefix match (e.g., "gemini-2.0-flash-thinking-exp" -> "gemini-2.0-flash")
    for key in MODEL_PRICING:
        if model_name.startswith(key):
            return MODEL_PRICING[key]

    # Fallback
    logger.warning(f"Unknown model '{model_name}', using gemini-2.0-flash pricing")
    return MODEL_PRICING["gemini-2.0-flash"]


# ==============================================================================
#  TOKEN USAGE RECORD
# ==============================================================================

@dataclass
class TokenUsage:
    """Record of a single API call's token usage."""
    timestamp: str
    operation: str  # e.g., "Step 2: Understanding", "Clarification"
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float

    @classmethod
    def from_response(cls, response: Any, operation: str, model: str) -> "TokenUsage":
        """Create TokenUsage from a Gemini API response object."""
        usage = response.usage_metadata
        input_tokens = usage.prompt_token_count
        output_tokens = usage.candidates_token_count
        total_tokens = usage.total_token_count

        pricing = get_pricing(model)
        cost = pricing.calculate_cost(input_tokens, output_tokens)

        return cls(
            timestamp=datetime.now().isoformat(),
            operation=operation,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost=cost,
        )


# ==============================================================================
#  TOKEN TRACKER
# ==============================================================================

class TokenTracker:
    """
    Tracks token usage across API calls and calculates costs.

    Thread-safe for use in FastAPI server.
    """

    def __init__(self, model: str = "gemini-2.0-flash"):
        """Initialize tracker with model name."""
        self.model = model
        self.usages: List[TokenUsage] = []
        self.lock = Lock()
        self._session_start = datetime.now()

    def record(self, input_tokens: int, output_tokens: int, operation: str = "API Call") -> TokenUsage:
        """
        Record token usage manually.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            operation: Description of the operation

        Returns:
            TokenUsage record
        """
        total_tokens = input_tokens + output_tokens
        pricing = get_pricing(self.model)
        cost = pricing.calculate_cost(input_tokens, output_tokens)

        usage = TokenUsage(
            timestamp=datetime.now().isoformat(),
            operation=operation,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost=cost,
        )

        with self.lock:
            self.usages.append(usage)

        logger.debug(f"[TokenTracker] {operation}: {total_tokens} tokens (${cost:.4f})")
        return usage

    def record_from_response(self, response: Any, operation: str = "API Call") -> TokenUsage:
        """
        Record token usage from a Gemini API response.

        Args:
            response: Gemini API response object with usage_metadata
            operation: Description of the operation

        Returns:
            TokenUsage record
        """
        usage = TokenUsage.from_response(response, operation, self.model)

        with self.lock:
            self.usages.append(usage)

        logger.debug(f"[TokenTracker] {operation}: {usage.total_tokens} tokens (${usage.cost:.4f})")
        return usage

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of all tracked token usage.

        Returns:
            Dictionary with aggregated statistics
        """
        with self.lock:
            if not self.usages:
                return {
                    "total_calls": 0,
                    "total_input_tokens": 0,
                    "total_output_tokens": 0,
                    "total_tokens": 0,
                    "total_cost": 0.0,
                    "model": self.model,
                    "by_operation": {},
                }

            total_input = sum(u.input_tokens for u in self.usages)
            total_output = sum(u.output_tokens for u in self.usages)
            total_tokens = sum(u.total_tokens for u in self.usages)
            total_cost = sum(u.cost for u in self.usages)

            # Group by operation
            by_operation = {}
            for usage in self.usages:
                op = usage.operation
                if op not in by_operation:
                    by_operation[op] = {
                        "calls": 0,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "total_tokens": 0,
                        "cost": 0.0,
                    }
                by_operation[op]["calls"] += 1
                by_operation[op]["input_tokens"] += usage.input_tokens
                by_operation[op]["output_tokens"] += usage.output_tokens
                by_operation[op]["total_tokens"] += usage.total_tokens
                by_operation[op]["cost"] += usage.cost

            return {
                "total_calls": len(self.usages),
                "total_input_tokens": total_input,
                "total_output_tokens": total_output,
                "total_tokens": total_tokens,
                "total_cost": total_cost,
                "model": self.model,
                "pricing": {
                    "input_per_1m": get_pricing(self.model).input_price_per_1m,
                    "output_per_1m": get_pricing(self.model).output_price_per_1m,
                },
                "by_operation": by_operation,
                "session_start": self._session_start.isoformat(),
            }

    def format_summary(self, detailed: bool = False) -> str:
        """
        Format summary as human-readable string.

        Args:
            detailed: If True, include per-operation breakdown

        Returns:
            Formatted summary string
        """
        summary = self.get_summary()

        if summary["total_calls"] == 0:
            return "No API calls tracked."

        lines = [
            "=" * 60,
            "TOKEN USAGE SUMMARY",
            "=" * 60,
            f"Model: {summary['model']}",
            f"Total API Calls: {summary['total_calls']}",
            "",
            f"Input Tokens:  {summary['total_input_tokens']:,}",
            f"Output Tokens: {summary['total_output_tokens']:,}",
            f"Total Tokens:  {summary['total_tokens']:,}",
            "",
            f"💰 Total Cost: ${summary['total_cost']:.4f}",
            "",
            f"Pricing:",
            f"  Input:  ${summary['pricing']['input_per_1m']:.2f} / 1M tokens",
            f"  Output: ${summary['pricing']['output_per_1m']:.2f} / 1M tokens",
        ]

        if detailed and summary["by_operation"]:
            lines.extend([
                "",
                "By Operation:",
                "-" * 60,
            ])
            for op, stats in summary["by_operation"].items():
                lines.append(f"\n{op}:")
                lines.append(f"  Calls: {stats['calls']}")
                lines.append(f"  Tokens: {stats['total_tokens']:,} (in: {stats['input_tokens']:,}, out: {stats['output_tokens']:,})")
                lines.append(f"  Cost: ${stats['cost']:.4f}")

        lines.append("=" * 60)
        return "\n".join(lines)

    def save_to_file(self, filepath: Path) -> None:
        """Save detailed usage log to JSON file."""
        with self.lock:
            data = {
                "summary": self.get_summary(),
                "details": [asdict(u) for u in self.usages],
            }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Token usage saved to {filepath}")

    def reset(self) -> None:
        """Clear all tracked usage."""
        with self.lock:
            self.usages.clear()
            self._session_start = datetime.now()


# ==============================================================================
#  GLOBAL TRACKER (for single-run scripts)
# ==============================================================================

_global_tracker: Optional[TokenTracker] = None
_global_lock = Lock()


def get_global_tracker(model: str = "gemini-2.0-flash") -> TokenTracker:
    """
    Get or create the global token tracker instance.

    Useful for console scripts and simple usage.
    """
    global _global_tracker

    with _global_lock:
        if _global_tracker is None:
            _global_tracker = TokenTracker(model)
        return _global_tracker


def reset_global_tracker() -> None:
    """Reset the global tracker (useful for tests)."""
    global _global_tracker

    with _global_lock:
        _global_tracker = None


# ==============================================================================
#  CONTEXT MANAGER
# ==============================================================================

@contextmanager
def track_tokens(operation: str, model: str = "gemini-2.0-flash", use_global: bool = False):
    """
    Context manager for automatic token tracking.

    Usage:
        with track_tokens("Step 2: Understanding") as tracker:
            response = model.generate_content(prompt)
            tracker.record_from_response(response)

    Args:
        operation: Description of the operation
        model: Model name for pricing
        use_global: If True, use global tracker; otherwise create new one

    Yields:
        TokenTracker instance
    """
    if use_global:
        tracker = get_global_tracker(model)
    else:
        tracker = TokenTracker(model)

    try:
        yield tracker
    finally:
        pass  # Tracker automatically records when record_from_response is called


# ==============================================================================
#  CONVENIENCE FUNCTIONS
# ==============================================================================

def print_global_summary(detailed: bool = True) -> None:
    """Print summary of global tracker."""
    tracker = get_global_tracker()
    print("\n" + tracker.format_summary(detailed=detailed))


def get_global_summary() -> Dict[str, Any]:
    """Get summary dict from global tracker."""
    tracker = get_global_tracker()
    return tracker.get_summary()


# ==============================================================================
#  USAGE EXAMPLES
# ==============================================================================

if __name__ == "__main__":
    print("Token Tracker - Demo")
    print("=" * 60)

    # Example 1: Manual tracking
    print("\n1. Manual tracking:")
    tracker = TokenTracker(model="gemini-2.0-flash")
    tracker.record(500, 200, "Test operation 1")
    tracker.record(1000, 300, "Test operation 2")
    print(tracker.format_summary(detailed=True))

    # Example 2: Cost calculation
    print("\n2. Cost calculation for typical query:")
    pricing = get_pricing("gemini-2.0-flash")
    input_tokens = 2000  # Typical prompt
    output_tokens = 1500  # Typical response
    cost = pricing.calculate_cost(input_tokens, output_tokens)
    print(f"Input: {input_tokens:,} tokens")
    print(f"Output: {output_tokens:,} tokens")
    print(f"Total: {input_tokens + output_tokens:,} tokens")
    print(f"Cost: ${cost:.4f}")

    # Example 3: Model comparison
    print("\n3. Model comparison for same query:")
    for model_name in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]:
        pricing = get_pricing(model_name)
        cost = pricing.calculate_cost(2000, 1500)
        print(f"{model_name:25s}: ${cost:.4f}")
