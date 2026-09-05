"""Resume Agent — Tier 2 router and orchestrator.

The Resume Agent sits between the Root agent and the five section agents.
It has read-only tools (Rule D2) to inspect the resume for disambiguation,
then transfers to the appropriate section agent with resolved context.
"""

from google.adk.agents import Agent

from unibot.prompts.resume_router_prompt import RESUME_AGENT_PROMPT
from unibot.tools.read_tools import get_resume, get_section
from unibot.agents.section_agents import (
    educations_agent,
    experiences_agent,
    projects_agent,
    skills_agent,
    summary_agent,
)


MODEL = "gemini-3.1-pro-preview"


resume_agent = Agent(
    name="resume_agent",
    model=MODEL,
    instruction=RESUME_AGENT_PROMPT,
    description=(
        "Routes resume edit requests to the correct section agent. "
        "Resolves ambiguous references (ordinals, fuzzy names) using "
        "read-only tools before transferring. Handles multi-section "
        "requests by splitting into sequential plans."
    ),
    tools=[get_resume, get_section],
    sub_agents=[
        summary_agent,
        experiences_agent,
        educations_agent,
        skills_agent,
        projects_agent,
    ],
)
