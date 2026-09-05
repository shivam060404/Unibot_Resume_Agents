"""Hierarchy assembly — builds and exports the root_agent.

This module is the single assembly point for the full agent hierarchy:
  Unibot Root → Resume Agent → 5 Section Agents

The root_agent is the entry point for `adk web` / `adk run`.
"""

import os

from dotenv import load_dotenv
from openai import AsyncOpenAI
from google.adk.agents import Agent
from google.adk.labs.openai import OpenAILlm

from unibot.prompts.root_prompt import ROOT_AGENT_PROMPT
from unibot.agents.root_agent import resume_agent

load_dotenv()

# ADK-native OpenAI-compatible adapter → Groq endpoint (no litellm needed)
_client = AsyncOpenAI(
    api_key=os.environ["OPENAI_API_KEY"].strip(),
    base_url=os.environ.get("OPENAI_API_BASE", "https://api.groq.com/openai/v1"),
)
_llm = OpenAILlm(model="openai/gpt-oss-20b", client=_client)


root_agent = Agent(
    name="unibot_root",
    model=_llm,
    instruction=ROOT_AGENT_PROMPT,
    description=(
        "Unibot — Unimad's career assistant. Greets users, answers career "
        "questions, and detects resume-edit intent to route to the Resume Agent."
    ),
    tools=[],  # Root has no tools (Rule D2)
    sub_agents=[resume_agent],
)
