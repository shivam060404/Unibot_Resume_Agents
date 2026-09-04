"""Skills section tools — add, remove, update.

Exclusive to the Skills Agent. Enforces case-insensitive dedup on add
(Rule C7), whitelisted fields on update, and ID validation on all ops.
"""

import copy
from typing import Any

from unibot.core import ToolError
from unibot.core.resume_store import store
from unibot.core.results import ok, fail
from unibot.core.schema_guard import SKILL_UPDATABLE, check_whitelist


def _find_skill(data: dict, skill_id: str) -> dict:
    """Find a skill entry by ID or raise ToolError."""
    for skill in data["skills"]:
        if skill["id"] == skill_id:
            return skill
    valid_ids = [s["id"] for s in data["skills"]]
    raise ToolError(
        "INVALID_ID",
        f"No skill with id '{skill_id}'.",
        f"Valid ids: {valid_ids}. Call get_section('skills') to inspect.",
    )


def _next_skill_id(data: dict) -> str:
    """Generate the next skill ID based on existing IDs."""
    existing = [s["id"] for s in data["skills"]]
    max_num = 0
    for sid in existing:
        if sid.startswith("skill_"):
            try:
                num = int(sid.split("_")[1])
                max_num = max(max_num, num)
            except (ValueError, IndexError):
                pass
    return f"skill_{max_num + 1}"


# ---------------------------------------------------------------------------
#  add_skill
# ---------------------------------------------------------------------------

def add_skill(name: str, category: str) -> dict[str, Any]:
    """Add a new skill to the resume.

    Case-insensitive dedup is enforced: if "Python" already exists,
    adding "python" will return DUPLICATE_SKILL. Inspect existing skills
    via get_section("skills") before calling.

    Args:
        name:     Skill name (e.g., "Python", "React", "AWS").
        category: Skill category (e.g., "Programming Languages", "Frameworks").
                  Prefer existing categories from the resume for consistency.

    Returns:
        On success: {ok: true, action, target, message, after}
        On failure: DUPLICATE_SKILL or MISSING_INPUT error envelope.
    """
    if not name or not name.strip():
        return fail("MISSING_INPUT", "Skill name cannot be empty.")
    if not category or not category.strip():
        return fail("MISSING_INPUT", "Skill category cannot be empty.")

    def _add(data: dict) -> dict[str, Any]:
        cleaned_name = name.strip()
        cleaned_cat = category.strip()

        # Case-insensitive dedup check (Rule C7)
        for existing in data["skills"]:
            if existing["name"].lower() == cleaned_name.lower():
                raise ToolError(
                    "DUPLICATE_SKILL",
                    f"Skill '{cleaned_name}' already exists as "
                    f"'{existing['name']}' (id: {existing['id']}, "
                    f"category: {existing['category']}).",
                    "Use update_skill to change its category, or use a "
                    "different name.",
                )

        new_id = _next_skill_id(data)
        new_skill = {
            "id": new_id,
            "name": cleaned_name,
            "category": cleaned_cat,
        }
        data["skills"].append(new_skill)
        return ok(
            action="add_skill",
            target=new_id,
            message=f"Added '{cleaned_name}' to skills under '{cleaned_cat}'.",
            after=copy.deepcopy(new_skill),
        )

    return store.transact(_add)


# ---------------------------------------------------------------------------
#  remove_skill
# ---------------------------------------------------------------------------

def remove_skill(id: str) -> dict[str, Any]:
    """Remove a skill by ID.

    The agent MUST confirm with the user before calling this tool.
    State the skill name and ask "Remove this?" first.

    IDs are stable: removing a skill does NOT renumber other skill IDs (Rule B6).

    Args:
        id: Skill ID (e.g., "skill_3").

    Returns:
        On success: {ok: true, action, target, message}
        On failure: INVALID_ID error envelope.
    """
    if not id:
        return fail("MISSING_INPUT", "Skill ID is required.")

    def _remove(data: dict) -> dict[str, Any]:
        skill = _find_skill(data, id)  # validates ID exists
        skill_name = skill["name"]
        data["skills"] = [s for s in data["skills"] if s["id"] != id]
        return ok(
            action="remove_skill",
            target=id,
            message=f"Removed skill '{skill_name}' (id: {id}).",
        )

    return store.transact(_remove)


# ---------------------------------------------------------------------------
#  update_skill
# ---------------------------------------------------------------------------

def update_skill(id: str, fields: dict[str, str]) -> dict[str, Any]:
    """Update whitelisted fields on a skill entry.

    Allowed fields: name, category. Send only the fields to change.
    If updating the name, case-insensitive dedup is checked against
    other skills.

    Args:
        id:     Skill ID (e.g., "skill_3").
        fields: Dict of field names to new values.

    Returns:
        On success: {ok: true, action, target, message, after}
        On failure: Standard error envelope.
    """
    if not id:
        return fail("MISSING_INPUT", "Skill ID is required.")
    if not fields:
        return fail("MISSING_INPUT", "No fields provided to update.")

    # Whitelist check (Rule B4)
    errors = check_whitelist(fields, SKILL_UPDATABLE)
    if errors:
        return fail("INVALID_FIELD", "; ".join(errors))

    def _update(data: dict) -> dict[str, Any]:
        skill = _find_skill(data, id)

        # If renaming, check for duplicates against other skills
        if "name" in fields:
            new_name = fields["name"].strip()
            for other in data["skills"]:
                if other["id"] != id and other["name"].lower() == new_name.lower():
                    raise ToolError(
                        "DUPLICATE_SKILL",
                        f"Cannot rename to '{new_name}' — skill "
                        f"'{other['name']}' already exists (id: {other['id']}).",
                    )

        for key, value in fields.items():
            skill[key] = value.strip() if isinstance(value, str) else value

        return ok(
            action="update_skill",
            target=id,
            message=f"Updated {list(fields.keys())} on skill '{skill['name']}'.",
            after=copy.deepcopy(skill),
        )

    return store.transact(_update)
