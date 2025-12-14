"""
Serialization helpers shared across the backend.
"""

from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any, Dict, Iterable, List


def enum_value(value: Any) -> Any:
    """Return the enum's value if present, otherwise the raw object."""
    return value.value if hasattr(value, "value") else value


def enum_dict_factory(items: List[Any]) -> Dict[str, Any]:
    """Dict factory that unwraps enums when converting dataclasses."""
    result: Dict[str, Any] = {}
    for key, value in items:
        result[key] = enum_value(value)
    return result


def to_serializable(obj: Any) -> Any:
    """
    Convert dataclasses or Pydantic models to plain dictionaries for safe dumping.
    Leaves primitives untouched.
    """
    if is_dataclass(obj):
        return asdict(obj, dict_factory=enum_dict_factory)
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return obj


def serialize_word_validations(word_validations: Iterable[Any]) -> List[Dict[str, Any]]:
    """
    Convert WordValidation objects to plain dicts for API/CLI responses.
    Keeps API responses stable regardless of enum configuration.
    """
    serialized: List[Dict[str, Any]] = []
    for word in word_validations:
        serialized.append(
            {
                "original": word.original,
                "best_match": word.best_match,
                "alternatives": word.alternatives,
                "confidence": word.confidence,
                "needs_validation": word.needs_validation,
                "validation_type": word.validation_type.value
                if hasattr(word.validation_type, "value")
                else word.validation_type,
            }
        )
    return serialized

