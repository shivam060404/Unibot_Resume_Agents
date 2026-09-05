"""Resume Agent — Tier 2 router and orchestrator.

The Resume Agent sits between the Root agent and the five section agents.
It has read-only tools (Rule D2) to inspect the resume for disambiguation,
then transfers to the appropriate section agent with resolved context.
"""

import os

from dotenv import load_dotenv
from openai import AsyncOpenAI
from google.adk.agents import Agent
from google.adk.labs.openai import OpenAILlm

from unibot.prompts.resume_router_prompt import RESUME_AGENT_PROMPT
from unibot.tools.read_tools import get_resume, get_section
from unibot.agents.section_agents import (
    educations_agent,
    experiences_agent,
    projects_agent,
    skills_agent,
    summary_agent,
)

load_dotenv()

_client = AsyncOpenAI(
    api_key=os.environ["OPENAI_API_KEY"].strip(),
    base_url=os.environ.get("OPENAI_API_BASE", "https://api.groq.com/openai/v1"),
)
_llm = OpenAILlm(model="openai/gpt-oss-20b", client=_client)


resume_agent = Agent(
    name="resume_agent",
    model=_llm,
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
