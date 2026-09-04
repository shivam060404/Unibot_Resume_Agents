"""Projects section tools — add, update, remove.

Exclusive to the Projects Agent. Handles project CRUD with whitelisted
fields, stable IDs, and confirmation-required deletions.
"""

import copy
from typing import Any

from unibot.core import ToolError
from unibot.core.resume_store import store
from unibot.core.results import ok, fail
from unibot.core.schema_guard import PROJECT_UPDATABLE, check_whitelist


def _find_project(data: dict, proj_id: str) -> dict:
    """Find a project entry by ID or raise ToolError."""
    for proj in data["projects"]:
        if proj["id"] == proj_id:
            return proj
    valid_ids = [p["id"] for p in data["projects"]]
    raise ToolError(
        "INVALID_ID",
        f"No project with id '{proj_id}'.",
        f"Valid ids: {valid_ids}. Call get_section('projects') to inspect.",
    )


def _next_project_id(data: dict) -> str:
    """Generate the next project ID based on existing IDs."""
    existing = [p["id"] for p in data["projects"]]
    max_num = 0
    for pid in existing:
        if pid.startswith("proj_"):
            try:
                num = int(pid.split("_")[1])
                max_num = max(max_num, num)
            except (ValueError, IndexError):
                pass
    return f"proj_{max_num + 1}"


# ---------------------------------------------------------------------------
#  add_project
# ---------------------------------------------------------------------------

def add_project(
    name: str,
    description: str,
    technologies: list[str] | None = None,
    link: str | None = None,
) -> dict[str, Any]:
    """Add a new project to the resume.

    Write descriptions in 1–3 crisp sentences: what it is, your role,
    notable tech. If the user didn't provide a name, the agent should
    ask for one or propose a concise name before calling this tool.

    Args:
        name:         Project name (e.g., "AI Support Chatbot").
        description:  1–3 sentence description of the project.
        technologies: Optional list of technologies used.
        link:         Optional project URL.

    Returns:
        On success: {ok: true, action, target, message, after}
        On failure: MISSING_INPUT error envelope.
    """
    if not name or not name.strip():
        return fail("MISSING_INPUT", "Project name cannot be empty.")
    if not description or not description.strip():
        return fail("MISSING_INPUT", "Project description cannot be empty.")

    def _add(data: dict) -> dict[str, Any]:
        new_id = _next_project_id(data)
        new_project = {
            "id": new_id,
            "name": name.strip(),
            "description": description.strip(),
            "technologies": [t.strip() for t in technologies] if technologies else [],
            "link": link.strip() if link else "",
        }
        data["projects"].append(new_project)
        return ok(
            action="add_project",
            target=new_id,
            message=f"Added project '{new_project['name']}'.",
            after=copy.deepcopy(new_project),
        )

    return store.transact(_add)


# ---------------------------------------------------------------------------
#  update_project
# ---------------------------------------------------------------------------

def update_project(id: str, fields: dict[str, Any]) -> dict[str, Any]:
    """Update whitelisted fields on a project entry.

    Allowed fields: name, description, technologies, link.
    Send only the fields the user asked to change.

    Args:
        id:     Project ID (e.g., "proj_1").
        fields: Dict of field names to new values. 'technologies' should
                be a list of strings; other fields are strings.

    Returns:
        On success: {ok: true, action, target, message, after}
        On failure: Standard error envelope.
    """
    if not id:
        return fail("MISSING_INPUT", "Project ID is required.")
    if not fields:
        return fail("MISSING_INPUT", "No fields provided to update.")

    # Whitelist check (Rule B4)
    errors = check_whitelist(fields, PROJECT_UPDATABLE)
    if errors:
        return fail("INVALID_FIELD", "; ".join(errors))

    def _update(data: dict) -> dict[str, Any]:
        proj = _find_project(data, id)
        for key, value in fields.items():
            if key == "technologies" and isinstance(value, list):
                proj[key] = [t.strip() if isinstance(t, str) else t for t in value]
            elif isinstance(value, str):
                proj[key] = value.strip()
            else:
                proj[key] = value

        return ok(
            action="update_project",
            target=id,
            message=f"Updated {list(fields.keys())} on project '{proj['name']}'.",
            after=copy.deepcopy(proj),
        )

    return store.transact(_update)


# ---------------------------------------------------------------------------
#  remove_project
# ---------------------------------------------------------------------------

def remove_project(id: str) -> dict[str, Any]:
    """Remove a project by ID.

    The agent MUST confirm with the user before calling this tool.
    Quote the project name and ask "Remove this?" first.

    IDs are stable: removing a project does NOT renumber other project IDs
    (Rule B6).

    Args:
        id: Project ID (e.g., "proj_2").

    Returns:
        On success: {ok: true, action, target, message}
        On failure: INVALID_ID error envelope.
    """
    if not id:
        return fail("MISSING_INPUT", "Project ID is required.")

    def _remove(data: dict) -> dict[str, Any]:
        proj = _find_project(data, id)  # validates ID exists
        proj_name = proj["name"]
        data["projects"] = [p for p in data["projects"] if p["id"] != id]
        return ok(
            action="remove_project",
            target=id,
            message=f"Removed project '{proj_name}' (id: {id}).",
        )

    return store.transact(_remove)
