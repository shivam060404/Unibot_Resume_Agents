"""Singleton resume state engine with transactional writes.

This is the L1 State Layer — the single source of truth for all resume data.
Loaded once from resume_data/resume.json at import time (Rule B1).

Design principles:
  - Reads return deep copies (Rule B5): no agent/tool can alias-mutate state.
  - Writes are transactional (Rule B3): snapshot → mutate → validate → commit-or-rollback.
  - Journal stores pre-edit snapshots capped at 20 entries (ADR-6).
  - Startup validates the resume and fails fast with actionable errors (Rule B7).
"""

import copy
import json
from pathlib import Path
from typing import Any, Callable

from . import ToolError
from . import schema_guard
from .results import fail


# ---------------------------------------------------------------------------
#  ResumeStore
# ---------------------------------------------------------------------------

class ResumeStore:
    """Singleton state engine for the resume document.

    Usage:
        from unibot.core.resume_store import store
        data = store.get_resume()              # deep copy — safe to inspect
        result = store.transact(my_mutation)    # transactional write
    """

    def __init__(self, path: str | Path):
        self.path = Path(path).resolve()
        self.data: dict[str, Any] = self._load_and_validate()
        self.journal: list[dict[str, Any]] = []  # pre-edit snapshots, capped at 20

    # -------------------------------------------------------------------
    #  Reads (deep-copy, no aliasing)
    # -------------------------------------------------------------------

    def get_resume(self) -> dict[str, Any]:
        """Return a deep copy of the entire resume."""
        return copy.deepcopy(self.data)

    def get_section(self, name: str) -> Any:
        """Return a deep copy of one section.

        Args:
            name: One of {summary, experiences, educations, skills, projects}.

        Returns:
            Deep copy of the section data, or None if the section name
            is invalid.
        """
        if name not in schema_guard.VALID_SECTIONS:
            return None
        return copy.deepcopy(self.data[name])

    # -------------------------------------------------------------------
    #  Transactional write (Rule B3: snapshot → mutate → validate → commit)
    # -------------------------------------------------------------------

    def transact(self, fn: Callable[[dict[str, Any]], dict[str, Any]]) -> dict[str, Any]:
        """Execute a mutation function inside a transaction.

        The function receives the live data dict, mutates it in-place,
        and returns a success result dict. If it raises ToolError for
        an expected domain error, or if post-mutation validation fails,
        the state is rolled back and a fail() result is returned.

        Args:
            fn: A callable that takes the mutable resume dict and returns
                an ok() result dict on success, or raises ToolError.

        Returns:
            Either the ok() result from fn, or a fail() result on error.
        """
        snapshot = copy.deepcopy(self.data)

        try:
            result = fn(self.data)
        except ToolError as e:
            # Expected domain error → rollback + structured failure
            self.data.clear()
            self.data.update(snapshot)
            return fail(e.error_code, e.message, e.hint)

        # Post-mutation schema validation
        errors = schema_guard.validate(self.data)
        if errors:
            self.data.clear()
            self.data.update(snapshot)
            return fail("VALIDATION_FAILED", "; ".join(errors))

        # Commit: journal the pre-edit snapshot (capped at 20)
        self.journal.append(snapshot)
        if len(self.journal) > 20:
            self.journal.pop(0)

        return result

    # -------------------------------------------------------------------
    #  Startup loader with fail-fast validation (Rule B7)
    # -------------------------------------------------------------------

    def _load_and_validate(self) -> dict[str, Any]:
        """Load resume JSON from disk and validate against schema.

        Raises:
            RuntimeError: If the file is missing, malformed, or invalid.
        """
        if not self.path.exists():
            raise RuntimeError(
                f"Resume file not found: {self.path}\n"
                f"Ensure resume_data/resume.json exists in the project root."
            )

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Invalid JSON in resume file ({self.path}):\n  {e}"
            ) from e

        errors = schema_guard.validate(data)
        if errors:
            detail = "\n".join(f"  - {err}" for err in errors)
            raise RuntimeError(
                f"Resume validation failed ({self.path}):\n{detail}\n"
                f"Fix the above issues and restart."
            )

        return data


# ---------------------------------------------------------------------------
#  Module-level singleton (loaded at import time — Rule B1, ADR-4)
# ---------------------------------------------------------------------------

_RESUME_PATH = Path(__file__).resolve().parent.parent.parent / "resume_data" / "resume.json"
store = ResumeStore(_RESUME_PATH)
