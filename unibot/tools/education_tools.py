"""Education section tool — update_education.

Exclusive to the Educations Agent. Education is factual ground truth;
tools enforce strict field whitelists and never embellish.
"""

import copy
from typing import Any

from unibot.core import ToolError
from unibot.core.resume_store import store
from unibot.core.results import ok, fail
from unibot.core.schema_guard import EDUCATION_UPDATABLE, check_whitelist


def _find_education(data: dict, edu_id: str) -> dict:
    """Find an education entry by ID or raise ToolError."""
    for edu in data["educations"]:
        if edu["id"] == edu_id:
            return edu
    valid_ids = [e["id"] for e in data["educations"]]
    raise ToolError(
        "INVALID_ID",
        f"No education with id '{edu_id}'.",
        f"Valid ids: {valid_ids}. Call get_section('educations') to inspect.",
    )


def update_education(id: str, fields: dict[str, str]) -> dict[str, Any]:
    """Update whitelisted fields on an education entry.

    Allowed fields: degree, institution, field_of_study, start_date,
    end_date, details. Send only the fields the user asked to change.
    Fields not in the whitelist will be rejected with INVALID_FIELD.

    Args:
        id:     Education ID (e.g., "edu_1").
        fields: Dict of field names to new values. Only whitelisted
                fields are accepted.

    Returns:
        On success: {ok: true, action, target, message, after}
        On failure: Standard error envelope.
    """
    if not id:
        return fail("MISSING_INPUT", "Education ID is required.")
    if not fields:
        return fail("MISSING_INPUT", "No fields provided to update.")

    # Whitelist check (Rule B4)
    errors = check_whitelist(fields, EDUCATION_UPDATABLE)
    if errors:
        return fail("INVALID_FIELD", "; ".join(errors))

    def _update(data: dict) -> dict[str, Any]:
        edu = _find_education(data, id)
        for key, value in fields.items():
            edu[key] = value
        label = f"'{edu.get('degree', '?')}' at {edu.get('institution', '?')}"
        return ok(
            action="update_education",
            target=id,
            message=f"Updated {list(fields.keys())} on {label}.",
            after=copy.deepcopy(edu),
        )

    return store.transact(_update)
