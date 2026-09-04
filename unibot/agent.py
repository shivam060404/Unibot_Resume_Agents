"""Hierarchy assembly — builds and exports the root_agent.

This module is the single assembly point for the full agent hierarchy:
  Unibot Root → Resume Agent → 5 Section Agents

The root_agent is the entry point for `adk web` / `adk run`.
"""

from google.adk.agents import Agent

from unibot.prompts.root_prompt import ROOT_AGENT_PROMPT
from unibot.agents.root_agent import resume_agent


MODEL = "gemini-1.5-pro"


root_agent = Agent(
    name="unibot_root",
    model=MODEL,
    instruction=ROOT_AGENT_PROMPT,
    description=(
        "Unibot — Unimad's career assistant. Greets users, answers career "
        "questions, and detects resume-edit intent to route to the Resume Agent."
    ),
    tools=[],  # Root has no tools (Rule D2)
    sub_agents=[resume_agent],
)
