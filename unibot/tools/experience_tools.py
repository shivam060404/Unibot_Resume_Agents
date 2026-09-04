"""Experience section tools — 4 tools for the Experiences Agent.

Tools:
  update_experience   – update whitelisted fields on an experience entry
  add_experience_bullet    – insert a bullet at a position (or append)
  edit_experience_bullet   – replace a bullet by index
  remove_experience_bullet – delete a bullet by index

All tools accept explicit IDs only (Rule C3). Ordinals are resolved
by the agent, not the tool.
"""

import copy
from typing import Any

from unibot.core import ToolError
from unibot.core.resume_store import store
from unibot.core.results import ok, fail
from unibot.core.schema_guard import EXPERIENCE_UPDATABLE, check_whitelist


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _find_experience(data: dict, exp_id: str) -> dict:
    """Find an experience entry by ID or raise ToolError."""
    for exp in data["experiences"]:
        if exp["id"] == exp_id:
            return exp
    valid_ids = [e["id"] for e in data["experiences"]]
    raise ToolError(
        "INVALID_ID",
        f"No experience with id '{exp_id}'.",
        f"Valid ids: {valid_ids}. Call get_section('experiences') to inspect.",
    )


def _exp_label(exp: dict) -> str:
    """Human-readable label for an experience entry."""
    return f"'{exp.get('role', '?')}' at {exp.get('organization', '?')}"


# ---------------------------------------------------------------------------
#  update_experience
# ---------------------------------------------------------------------------

def update_experience(id: str, fields: dict[str, str]) -> dict[str, Any]:
    """Update whitelisted fields on an experience entry.

    Allowed fields: role, organization, location, start_date, end_date.
    Send only the fields you want to change. Fields not in the whitelist
    will be rejected with INVALID_FIELD.

    Args:
        id:     Experience ID (e.g., "exp_1").
        fields: Dict of field names to new values. Only whitelisted
                fields are accepted.

    Returns:
        On success: {ok: true, action, target, message, after}
        On failure: Standard error envelope.
    """
    if not id:
        return fail("MISSING_INPUT", "Experience ID is required.")
    if not fields:
        return fail("MISSING_INPUT", "No fields provided to update.")

    # Whitelist check (Rule B4)
    errors = check_whitelist(fields, EXPERIENCE_UPDATABLE)
    if errors:
        return fail("INVALID_FIELD", "; ".join(errors))

    def _update(data: dict) -> dict[str, Any]:
        exp = _find_experience(data, id)
        for key, value in fields.items():
            exp[key] = value
        return ok(
            action="update_experience",
            target=id,
            message=f"Updated {list(fields.keys())} on {_exp_label(exp)}.",
            after=copy.deepcopy(exp),
        )

    return store.transact(_update)


# ---------------------------------------------------------------------------
#  add_experience_bullet
# ---------------------------------------------------------------------------

def add_experience_bullet(
    id: str,
    bullet: str,
    position: int | None = None,
) -> dict[str, Any]:
    """Add a bullet point to an experience entry.

    Args:
        id:       Experience ID (e.g., "exp_1").
        bullet:   The bullet text to add.
        position: 0-indexed insertion position. None or omitted = append
                  to the end of the bullets list.

    Returns:
        On success: {ok: true, action, target, message, after}
        On failure: Standard error envelope.
    """
    if not id:
        return fail("MISSING_INPUT", "Experience ID is required.")
    if not bullet or not bullet.strip():
        return fail("MISSING_INPUT", "Bullet text cannot be empty.")

    def _add(data: dict) -> dict[str, Any]:
        exp = _find_experience(data, id)
        cleaned = bullet.strip()

        if position is None:
            exp["bullets"].append(cleaned)
            pos_desc = "end"
        else:
            if position < 0 or position > len(exp["bullets"]):
                raise ToolError(
                    "INVALID_INDEX",
                    f"Position {position} out of range. "
                    f"Valid range: 0–{len(exp['bullets'])}.",
                )
            exp["bullets"].insert(position, cleaned)
            pos_desc = f"position {position}"

        return ok(
            action="add_experience_bullet",
            target=id,
            message=f"Added bullet at {pos_desc} of {_exp_label(exp)}.",
            after=copy.deepcopy(exp),
        )

    return store.transact(_add)


# ---------------------------------------------------------------------------
#  edit_experience_bullet
# ---------------------------------------------------------------------------

def edit_experience_bullet(
    id: str,
    bullet_index: int,
    text: str,
) -> dict[str, Any]:
    """Replace a single bullet by index in an experience entry.

    Args:
        id:           Experience ID (e.g., "exp_1").
        bullet_index: 0-indexed position of the bullet to replace.
        text:         The new bullet text.

    Returns:
        On success: {ok: true, action, target, message, after}
        On failure: Standard error envelope.
    """
    if not id:
        return fail("MISSING_INPUT", "Experience ID is required.")
    if not text or not text.strip():
        return fail("MISSING_INPUT", "Bullet text cannot be empty.")

    def _edit(data: dict) -> dict[str, Any]:
        exp = _find_experience(data, id)
        if bullet_index < 0 or bullet_index >= len(exp["bullets"]):
            raise ToolError(
                "INVALID_INDEX",
                f"Bullet index {bullet_index} out of range. "
                f"Valid range: 0–{len(exp['bullets']) - 1} "
                f"({len(exp['bullets'])} bullets exist).",
            )
        old_bullet = exp["bullets"][bullet_index]
        exp["bullets"][bullet_index] = text.strip()
        return ok(
            action="edit_experience_bullet",
            target=id,
            message=(
                f"Replaced bullet {bullet_index} of {_exp_label(exp)}. "
                f"Old: \"{old_bullet[:60]}...\"" if len(old_bullet) > 60
                else f"Replaced bullet {bullet_index} of {_exp_label(exp)}."
            ),
            after=copy.deepcopy(exp),
        )

    return store.transact(_edit)


# ---------------------------------------------------------------------------
#  remove_experience_bullet
# ---------------------------------------------------------------------------

def remove_experience_bullet(
    id: str,
    bullet_index: int,
) -> dict[str, Any]:
    """Remove a single bullet by index from an experience entry.

    The agent MUST confirm with the user before calling this tool.
    Quote the exact bullet text and ask "Remove this?" first.

    Args:
        id:           Experience ID (e.g., "exp_1").
        bullet_index: 0-indexed position of the bullet to remove.

    Returns:
        On success: {ok: true, action, target, message, after}
        On failure: Standard error envelope.
    """
    if not id:
        return fail("MISSING_INPUT", "Experience ID is required.")

    def _remove(data: dict) -> dict[str, Any]:
        exp = _find_experience(data, id)
        if bullet_index < 0 or bullet_index >= len(exp["bullets"]):
            raise ToolError(
                "INVALID_INDEX",
                f"Bullet index {bullet_index} out of range. "
                f"Valid range: 0–{len(exp['bullets']) - 1} "
                f"({len(exp['bullets'])} bullets exist).",
            )
        removed = exp["bullets"].pop(bullet_index)
        return ok(
            action="remove_experience_bullet",
            target=id,
            message=f"Removed bullet from {_exp_label(exp)}: \"{removed[:80]}\"",
            after=copy.deepcopy(exp),
        )

    return store.transact(_remove)
