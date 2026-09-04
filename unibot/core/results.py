"""Standardized tool-result contract helpers.

Every tool returns one of these two shapes so agents can reason about
success and failure uniformly (Rule C2).

Success:
    {"ok": True, "action": "...", "target": "...", "message": "...", "after": {...}}

Failure:
    {"ok": False, "error_code": "...", "message": "...", "hint": "..."}

Error codes:
    INVALID_ID         – No entry with the given ID exists
    INVALID_SECTION    – Section name not in {summary, experiences, ...}
    INVALID_FIELD      – Field not in the whitelist for this entity
    INVALID_INDEX      – Bullet index out of range
    DUPLICATE_SKILL    – Skill already exists (case-insensitive)
    VALIDATION_FAILED  – Schema validation failed after mutation (rollback)
    MISSING_INPUT      – Required argument was empty or None
"""

from typing import Any


def ok(
    action: str,
    target: str,
    message: str,
    after: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a success result envelope.

    Args:
        action:  Tool function name (e.g. "add_experience_bullet").
        target:  Entity affected (e.g. "exp_1", "summary").
        message: Human-readable confirmation of what changed.
        after:   Optional snapshot of the affected entity post-mutation.

    Returns:
        Standardized success dict.
    """
    result: dict[str, Any] = {
        "ok": True,
        "action": action,
        "target": target,
        "message": message,
    }
    if after is not None:
        result["after"] = after
    return result


def fail(
    error_code: str,
    message: str,
    hint: str | None = None,
) -> dict[str, Any]:
    """Build a failure result envelope.

    Args:
        error_code: One of the documented error codes (see module docstring).
        message:    Human-readable description of the error.
        hint:       Optional remediation hint for the LLM.

    Returns:
        Standardized failure dict.
    """
    result: dict[str, Any] = {
        "ok": False,
        "error_code": error_code,
        "message": message,
    }
    if hint is not None:
        result["hint"] = hint
    return result
