"""Read-only tools for resume inspection.

These tools are available to the Resume Agent (router) and all section agents.
They return deep copies — safe to inspect, impossible to mutate state through.
"""

from typing import Any

from unibot.core.resume_store import store
from unibot.core.results import fail
from unibot.core.schema_guard import VALID_SECTIONS


def get_resume() -> dict[str, Any]:
    """Return the full resume document for inspection.

    Use this to see the overall resume structure, all sections, and all
    entry IDs. Useful for disambiguating user references before routing.

    Returns:
        The complete resume as a dict with keys: basics, summary,
        experiences, educations, skills, projects.
    """
    return store.get_resume()


def get_section(section_name: str) -> dict[str, Any]:
    """Return a single section of the resume for inspection.

    Use this to inspect one section before editing. For list sections
    (experiences, educations, skills, projects), each entry has a
    stable 'id' field. Ordinals are 1-indexed: "first" = index 0 = the
    first item in the list.

    Args:
        section_name: One of "summary", "experiences", "educations",
                      "skills", "projects".

    Returns:
        On success: {"ok": true, "section": <section_name>, "data": <section_data>}
        On failure: Standard error envelope with INVALID_SECTION code.
    """
    if section_name not in VALID_SECTIONS:
        return fail(
            "INVALID_SECTION",
            f"Invalid section: '{section_name}'.",
            f"Valid sections: {sorted(VALID_SECTIONS)}",
        )

    data = store.get_section(section_name)
    return {
        "ok": True,
        "section": section_name,
        "data": data,
    }
