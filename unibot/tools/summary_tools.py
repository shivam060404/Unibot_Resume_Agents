"""Summary section tool — update_summary.

Exclusive to the Summary Agent. Handles summary rewrites, shortening,
tone transforms, etc. via a single replacement tool.
"""

import copy
from typing import Any

from unibot.core import ToolError
from unibot.core.resume_store import store
from unibot.core.results import ok, fail


def update_summary(text: str) -> dict[str, Any]:
    """Replace the resume summary with new text.

    Use this after reading the current summary via get_section("summary").
    Pass the complete new summary text — this is a full replacement,
    not an append.

    Args:
        text: The new summary text. Must be a non-empty string.

    Returns:
        On success: {ok: true, action: "update_summary", target: "summary",
                     message: "...", after: "<new summary>"}
        On failure: Standard error envelope.
    """
    if not text or not text.strip():
        return fail("MISSING_INPUT", "Summary text cannot be empty.")

    def _update(data: dict) -> dict[str, Any]:
        data["summary"] = text.strip()
        return ok(
            action="update_summary",
            target="summary",
            message="Summary updated successfully.",
            after={"summary": data["summary"]},
        )

    return store.transact(_update)
