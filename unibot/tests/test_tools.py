"""Unit tests for the tool layer.

Tests prove schema safety, field whitelists, transactional rollback,
and dedup logic without needing an LLM.
"""

import copy
import json
import os
from pathlib import Path

import pytest

from unibot.core.resume_store import ResumeStore
from unibot.core import ToolError

# Create a temporary resume store for testing
TEST_RESUME_DATA = {
    "basics": {
        "name": "Test User",
        "title": "Engineer",
        "email": "test@test.com",
        "phone": "123",
        "location": "NY",
        "links": []
    },
    "summary": "Test summary",
    "experiences": [
        {
            "id": "exp_1",
            "role": "Role 1",
            "organization": "Org 1",
            "location": "NY",
            "start_date": "2020",
            "end_date": "2021",
            "bullets": ["Bullet 1"]
        }
    ],
    "educations": [],
    "skills": [
        {"id": "skill_1", "name": "Python", "category": "Lang"}
    ],
    "projects": []
}

@pytest.fixture
def test_store(tmp_path):
    resume_file = tmp_path / "test_resume.json"
    with open(resume_file, "w") as f:
        json.dump(TEST_RESUME_DATA, f)
    store = ResumeStore(resume_file)
    return store


# We have to patch the global store in the tools for testing
@pytest.fixture(autouse=True)
def patch_store(test_store, monkeypatch):
    import unibot.core.resume_store
    monkeypatch.setattr(unibot.core.resume_store, "store", test_store)
    import unibot.tools.read_tools
    monkeypatch.setattr(unibot.tools.read_tools, "store", test_store)
    import unibot.tools.summary_tools
    monkeypatch.setattr(unibot.tools.summary_tools, "store", test_store)
    import unibot.tools.experience_tools
    monkeypatch.setattr(unibot.tools.experience_tools, "store", test_store)
    import unibot.tools.education_tools
    monkeypatch.setattr(unibot.tools.education_tools, "store", test_store)
    import unibot.tools.skills_tools
    monkeypatch.setattr(unibot.tools.skills_tools, "store", test_store)
    import unibot.tools.projects_tools
    monkeypatch.setattr(unibot.tools.projects_tools, "store", test_store)


def test_get_section(test_store):
    from unibot.tools.read_tools import get_section
    res = get_section("summary")
    assert res["ok"] is True
    assert res["data"] == "Test summary"

    res = get_section("invalid")
    assert res["ok"] is False
    assert res["error_code"] == "INVALID_SECTION"


def test_update_summary(test_store):
    from unibot.tools.summary_tools import update_summary
    res = update_summary("New summary")
    assert res["ok"] is True
    assert test_store.get_section("summary") == "New summary"


def test_experience_tools_whitelist(test_store):
    from unibot.tools.experience_tools import update_experience
    res = update_experience("exp_1", {"role": "New Role"})
    assert res["ok"] is True
    assert test_store.get_section("experiences")[0]["role"] == "New Role"

    # Invalid field
    res = update_experience("exp_1", {"invalid_field": "Val"})
    assert res["ok"] is False
    assert res["error_code"] == "INVALID_FIELD"


def test_experience_bullet_ops(test_store):
    from unibot.tools.experience_tools import (
        add_experience_bullet,
        edit_experience_bullet,
        remove_experience_bullet,
    )
    # Add
    res = add_experience_bullet("exp_1", "Bullet 2")
    assert res["ok"] is True
    exp = test_store.get_section("experiences")[0]
    assert exp["bullets"] == ["Bullet 1", "Bullet 2"]

    # Edit
    res = edit_experience_bullet("exp_1", 1, "Edited Bullet 2")
    assert res["ok"] is True
    exp = test_store.get_section("experiences")[0]
    assert exp["bullets"] == ["Bullet 1", "Edited Bullet 2"]

    # Remove
    res = remove_experience_bullet("exp_1", 0)
    assert res["ok"] is True
    exp = test_store.get_section("experiences")[0]
    assert exp["bullets"] == ["Edited Bullet 2"]


def test_skill_dedup(test_store):
    from unibot.tools.skills_tools import add_skill
    res = add_skill("python", "Lang")
    assert res["ok"] is False
    assert res["error_code"] == "DUPLICATE_SKILL"

    res = add_skill("Java", "Lang")
    assert res["ok"] is True


def test_transactional_rollback(test_store):
    from unibot.core.resume_store import store
    from unibot.core.results import ok
    
    original_state = copy.deepcopy(store.data)

    def bad_mutation(data):
        # Mutate in a way that breaks schema (delete a required section)
        del data["summary"]
        return ok("test", "test", "test")

    res = store.transact(bad_mutation)
    assert res["ok"] is False
    assert res["error_code"] == "VALIDATION_FAILED"
    
    # Assert state was rolled back completely
    assert store.data == original_state
