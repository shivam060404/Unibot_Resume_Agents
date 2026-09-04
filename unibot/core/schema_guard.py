"""Schema validation and field-whitelist enforcement.

This module is the L0 Guard Layer. It defines:
  1. Structural validation for the full resume document.
  2. Per-entity field whitelists for update tools (Rule B4).
  3. A helper to check user-supplied fields against whitelists.

The validator returns a list of human-readable error strings.
An empty list means the resume is valid.
"""

from typing import Any


# ---------------------------------------------------------------------------
#  Field definitions (source of truth for the resume schema)
# ---------------------------------------------------------------------------

REQUIRED_SECTIONS = {"basics", "summary", "experiences", "educations", "skills", "projects"}

BASICS_FIELDS = {"name", "title", "email", "phone", "location", "links"}

EXPERIENCE_ALL_FIELDS = {"id", "role", "organization", "location", "start_date", "end_date", "bullets"}
EXPERIENCE_UPDATABLE = {"role", "organization", "location", "start_date", "end_date"}

EDUCATION_ALL_FIELDS = {"id", "degree", "institution", "field_of_study", "start_date", "end_date", "details"}
EDUCATION_UPDATABLE = {"degree", "institution", "field_of_study", "start_date", "end_date", "details"}

SKILL_ALL_FIELDS = {"id", "name", "category"}
SKILL_UPDATABLE = {"name", "category"}

PROJECT_ALL_FIELDS = {"id", "name", "description", "technologies", "link"}
PROJECT_UPDATABLE = {"name", "description", "technologies", "link"}

VALID_SECTIONS = {"summary", "experiences", "educations", "skills", "projects"}


# ---------------------------------------------------------------------------
#  Structural validator
# ---------------------------------------------------------------------------

def validate(resume: dict) -> list[str]:
    """Validate the full resume dict against the expected schema.

    Returns a list of error strings. Empty list = valid.
    """
    errors: list[str] = []

    if not isinstance(resume, dict):
        return ["Resume must be a JSON object (dict)."]

    # --- Top-level sections ---
    for section in REQUIRED_SECTIONS:
        if section not in resume:
            errors.append(f"Missing required section: '{section}'")

    # --- basics ---
    if "basics" in resume:
        errors.extend(_validate_basics(resume["basics"]))

    # --- summary ---
    if "summary" in resume:
        if not isinstance(resume["summary"], str):
            errors.append("'summary' must be a string.")

    # --- experiences ---
    if "experiences" in resume:
        errors.extend(_validate_list_section(
            resume["experiences"], "experiences",
            EXPERIENCE_ALL_FIELDS, _validate_experience_entry,
        ))

    # --- educations ---
    if "educations" in resume:
        errors.extend(_validate_list_section(
            resume["educations"], "educations",
            EDUCATION_ALL_FIELDS, _validate_education_entry,
        ))

    # --- skills ---
    if "skills" in resume:
        errors.extend(_validate_list_section(
            resume["skills"], "skills",
            SKILL_ALL_FIELDS, _validate_skill_entry,
        ))

    # --- projects ---
    if "projects" in resume:
        errors.extend(_validate_list_section(
            resume["projects"], "projects",
            PROJECT_ALL_FIELDS, _validate_project_entry,
        ))

    return errors


# ---------------------------------------------------------------------------
#  Whitelist checker (used by update tools — Rule B4)
# ---------------------------------------------------------------------------

def check_whitelist(fields: dict, allowed: set[str]) -> list[str]:
    """Return error messages for any field keys not in the allowed set.

    Args:
        fields:  The dict of fields the caller wants to update.
        allowed: The set of permitted field names.

    Returns:
        List of error strings for invalid fields (empty = all ok).
    """
    invalid = set(fields.keys()) - allowed
    if not invalid:
        return []
    return [
        f"Invalid field: '{f}'. Allowed fields: {sorted(allowed)}"
        for f in sorted(invalid)
    ]


# ---------------------------------------------------------------------------
#  Internal validators
# ---------------------------------------------------------------------------

def _validate_basics(basics: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(basics, dict):
        return ["'basics' must be a dict."]
    for field in BASICS_FIELDS:
        if field not in basics:
            errors.append(f"basics: missing field '{field}'")
        elif field == "links":
            if not isinstance(basics["links"], list):
                errors.append("basics.links must be a list.")
            else:
                for i, link in enumerate(basics["links"]):
                    if not isinstance(link, str):
                        errors.append(f"basics.links[{i}] must be a string.")
        else:
            if not isinstance(basics[field], str):
                errors.append(f"basics.{field} must be a string.")
    return errors


def _validate_list_section(
    section: Any,
    section_name: str,
    required_fields: set[str],
    entry_validator,
) -> list[str]:
    """Validate a list-type section (experiences, educations, skills, projects)."""
    errors: list[str] = []
    if not isinstance(section, list):
        errors.append(f"'{section_name}' must be a list.")
        return errors
    for i, entry in enumerate(section):
        prefix = f"{section_name}[{i}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix} must be a dict.")
            continue
        # Check required fields exist
        for field in required_fields:
            if field not in entry:
                errors.append(f"{prefix}: missing field '{field}'")
        # Type-specific validation
        errors.extend(entry_validator(entry, prefix))
    return errors


def _validate_experience_entry(entry: dict, prefix: str) -> list[str]:
    errors: list[str] = []
    for field in ("id", "role", "organization", "location", "start_date", "end_date"):
        if field in entry and not isinstance(entry[field], str):
            errors.append(f"{prefix}.{field} must be a string.")
    if "bullets" in entry:
        if not isinstance(entry["bullets"], list):
            errors.append(f"{prefix}.bullets must be a list.")
        else:
            for j, bullet in enumerate(entry["bullets"]):
                if not isinstance(bullet, str):
                    errors.append(f"{prefix}.bullets[{j}] must be a string.")
    return errors


def _validate_education_entry(entry: dict, prefix: str) -> list[str]:
    errors: list[str] = []
    for field in ("id", "degree", "institution", "field_of_study", "start_date", "end_date", "details"):
        if field in entry and not isinstance(entry[field], str):
            errors.append(f"{prefix}.{field} must be a string.")
    return errors


def _validate_skill_entry(entry: dict, prefix: str) -> list[str]:
    errors: list[str] = []
    for field in ("id", "name", "category"):
        if field in entry and not isinstance(entry[field], str):
            errors.append(f"{prefix}.{field} must be a string.")
    return errors


def _validate_project_entry(entry: dict, prefix: str) -> list[str]:
    errors: list[str] = []
    for field in ("id", "name", "description", "link"):
        if field in entry and not isinstance(entry[field], str):
            errors.append(f"{prefix}.{field} must be a string.")
    if "technologies" in entry:
        if not isinstance(entry["technologies"], list):
            errors.append(f"{prefix}.technologies must be a list.")
        else:
            for j, tech in enumerate(entry["technologies"]):
                if not isinstance(tech, str):
                    errors.append(f"{prefix}.technologies[{j}] must be a string.")
    return errors
