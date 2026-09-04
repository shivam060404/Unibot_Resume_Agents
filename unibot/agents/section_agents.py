"""Five section agents — Tier 3 domain experts.

Each agent owns exactly one resume section and has exclusive access to
that section's mutation tools (Rule D1). All agents share the read tool
get_section for inspection before editing.

Agent descriptions are written as routing metadata (ADK note from §2.2):
ADK's LLM-driven transfer_to_agent selects targets from descriptions.
"""

from google.adk.agents import Agent

from unibot.prompts.section_prompts import (
    EDUCATIONS_AGENT_PROMPT,
    EXPERIENCES_AGENT_PROMPT,
    PROJECTS_AGENT_PROMPT,
    SKILLS_AGENT_PROMPT,
    SUMMARY_AGENT_PROMPT,
)
from unibot.tools.read_tools import get_section
from unibot.tools.summary_tools import update_summary
from unibot.tools.experience_tools import (
    add_experience_bullet,
    edit_experience_bullet,
    remove_experience_bullet,
    update_experience,
)
from unibot.tools.education_tools import update_education
from unibot.tools.skills_tools import add_skill, remove_skill, update_skill
from unibot.tools.projects_tools import add_project, remove_project, update_project


# Model for all agents (ADR-7)
MODEL = "gemini-1.5-flash"


# ---------------------------------------------------------------------------
#  Summary Agent — owns "summary" field
# ---------------------------------------------------------------------------

summary_agent = Agent(
    name="summary_agent",
    model=MODEL,
    instruction=SUMMARY_AGENT_PROMPT,
    description=(
        "Handles requests to read, rewrite, shorten, expand, or change the tone "
        "of the resume summary/profile/bio section. Transfers here for any "
        "summary-related edit."
    ),
    tools=[get_section, update_summary],
)


# ---------------------------------------------------------------------------
#  Experiences Agent — owns "experiences" array
# ---------------------------------------------------------------------------

experiences_agent = Agent(
    name="experiences_agent",
    model=MODEL,
    instruction=EXPERIENCES_AGENT_PROMPT,
    description=(
        "Handles requests to add, edit, or remove experience bullets, and to "
        "update job titles, organizations, locations, or dates in the experiences "
        "section. Transfers here for any work experience edit."
    ),
    tools=[
        get_section,
        update_experience,
        add_experience_bullet,
        edit_experience_bullet,
        remove_experience_bullet,
    ],
)


# ---------------------------------------------------------------------------
#  Educations Agent — owns "educations" array
# ---------------------------------------------------------------------------

educations_agent = Agent(
    name="educations_agent",
    model=MODEL,
    instruction=EDUCATIONS_AGENT_PROMPT,
    description=(
        "Handles requests to update education entries: degree, institution, "
        "field of study, dates, or details. Transfers here for any education edit."
    ),
    tools=[get_section, update_education],
)


# ---------------------------------------------------------------------------
#  Skills Agent — owns "skills" array
# ---------------------------------------------------------------------------

skills_agent = Agent(
    name="skills_agent",
    model=MODEL,
    instruction=SKILLS_AGENT_PROMPT,
    description=(
        "Handles requests to add, remove, or recategorize skills. Transfers "
        "here when the user wants to modify their skills/tech stack list."
    ),
    tools=[get_section, add_skill, remove_skill, update_skill],
)


# ---------------------------------------------------------------------------
#  Projects Agent — owns "projects" array
# ---------------------------------------------------------------------------

projects_agent = Agent(
    name="projects_agent",
    model=MODEL,
    instruction=PROJECTS_AGENT_PROMPT,
    description=(
        "Handles requests to add, edit, or remove projects from the portfolio "
        "section. Transfers here for any project-related edit."
    ),
    tools=[get_section, add_project, update_project, remove_project],
)
