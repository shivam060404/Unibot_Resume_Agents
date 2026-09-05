# Unibot Resume Agents

> **A production-grade, multi-agent resume editing system** built with the [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/). Converts natural-language requests into schema-safe, tool-executed mutations of a structured JSON resume — with zero freeform rewriting.

---

## ✅ Verified Working

End-to-end tested and verified. Sample run:

```
$ adk run unibot "Update my summary to sound more senior and leadership-focused"

[summary_agent]: Done — your summary now highlights leadership, ownership,
                 and impact. Want it tightened further?
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Agent Framework | [Google ADK](https://google.github.io/adk-docs/) |
| LLM Backend | [Groq](https://console.groq.com) via ADK-native `OpenAILlm` |
| Model | `openai/gpt-oss-20b` (tool-calling capable) |
| State Management | Transactional `ResumeStore` singleton |
| Schema Validation | Custom Python field-whitelist validator |
| Config | `python-dotenv` |

---

## Quick Start

**Requirements:** Python 3.10+

```bash
# 1. Clone and set up the virtual environment
git clone https://github.com/shivam060404/Unibot_Resume_Agents.git
cd Unibot_Resume_Agents
python3 -m venv venv && source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure your API key
cp .env.example .env
# Edit .env and add your Groq API key:
#   OPENAI_API_KEY=gsk_your_groq_api_key_here
#   OPENAI_API_BASE=https://api.groq.com/openai/v1

# 4a. Run via interactive CLI
adk run unibot

# 4b. Or launch the web UI
adk web unibot
```

Get your free Groq API key at [console.groq.com](https://console.groq.com).

---

## Architecture — 3-Tier Agent Hierarchy

The system enforces the **Principle of Least Privilege** through strict tier separation. Each agent is granted only the context and tools it absolutely needs.

```
┌─────────────────────────────────────────────────────────────┐
│  TIER 1 — Unibot Root Agent                                 │
│  Model: openai/gpt-oss-20b  │  Tools: NONE                  │
│  Role: Greetings, career chat, resume-edit intent detection  │
└────────────────────────┬────────────────────────────────────┘
                         │ transfer_to_agent
┌────────────────────────▼────────────────────────────────────┐
│  TIER 2 — Resume Router Agent                               │
│  Model: openai/gpt-oss-20b  │  Tools: get_resume, get_section│
│  Role: Disambiguate intent, resolve IDs, route to Tier 3    │
└──┬──────────┬───────────┬──────────┬────────────────────────┘
   │          │           │          │
   ▼          ▼           ▼          ▼          ▼
Summary  Experiences  Educations  Skills    Projects
 Agent     Agent        Agent      Agent     Agent
```

**TIER 3 — Section Agents** (Model: `openai/gpt-oss-20b`)

Each agent is an isolated domain expert with access only to its own section's tools:

| Agent | Mutation Tools |
|-------|---------------|
| `summary_agent` | `update_summary` |
| `experiences_agent` | `update_experience`, `add_experience_bullet`, `edit_experience_bullet`, `remove_experience_bullet` |
| `educations_agent` | `update_education` |
| `skills_agent` | `add_skill`, `remove_skill`, `update_skill` |
| `projects_agent` | `add_project`, `update_project`, `remove_project` |

> The Skills Agent physically **cannot see** the Experience Agent's tools. Cross-domain hallucination is architecturally impossible.

---

## Swapping the Resume

Edit `resume_data/resume.json` to use your own resume. The system loads and validates this file at startup — if the schema is violated, it fails fast with a clear error.

---

## Key Engineering Features

### Transactional State Engine
All mutations follow: **Snapshot → Mutate → Validate → Commit/Rollback**.  
If the LLM passes an invalid field, the transaction rolls back and a structured error is returned.

### Self-Correcting Tool Envelopes
Every tool returns a standardized envelope. On error:
```json
{
  "ok": false,
  "error_code": "INVALID_ID",
  "message": "No project with id 'proj_99'.",
  "hint": "Valid ids: ['proj_1', 'proj_2']. Call get_section('projects') to inspect."
}
```
The LLM reads this, self-corrects, and retries — no crashes.

### Confirmation Protocols
Destructive operations (`remove_*`) are **prompt-enforced**: agents must ask *"Are you sure you want to remove X?"* before calling any deletion tool.

### Schema Guard
All mutations are validated against strict Python field whitelists. The LLM can never inject arbitrary keys into the JSON resume.

---

## Sample Queries for Evaluators

```
"Make my summary more senior"
"Rewrite my summary for leadership roles"
"Add a leadership bullet to my first experience"
"Add Python to my skills"
"Remove my second project"         ← triggers confirmation protocol
"Improve my first job bullets for impact"
"Add a project about an AI chatbot"
"Shorten my summary"
```

---

## Project Structure

```
Unibot_Resume_Agents/
├── unibot/
│   ├── agent.py                   # Entry point — assembles root_agent
│   ├── agents/
│   │   ├── root_agent.py          # Tier 2: Resume Router Agent
│   │   └── section_agents.py      # Tier 3: 5 Section Agents
│   ├── core/
│   │   ├── resume_store.py        # Transactional state singleton
│   │   └── schema_guard.py        # Field whitelist validator
│   ├── prompts/
│   │   ├── root_prompt.py
│   │   ├── resume_router_prompt.py
│   │   └── section_prompts.py
│   └── tools/
│       ├── read_tools.py
│       ├── summary_tools.py
│       ├── experience_tools.py
│       ├── education_tools.py
│       ├── skills_tools.py
│       └── projects_tools.py
├── resume_data/
│   └── resume.json                # ← Edit this to use your resume
├── docs/
│   └── system_architecture.md
├── .env.example
├── requirements.txt
└── README.md
```

---

## Prompt Design

All agent prompts follow a strict, standardized contract:

```
ROLE → SCOPE → TOOL POLICY → EDIT POLICY → GUARDRAILS → EXAMPLES
```

- **Hard Boundaries:** Every agent explicitly states what it *cannot* do.
- **Anti-Fabrication:** Mutation agents are strictly forbidden from inventing metrics or facts.
- **Confirmation Protocols:** Destructive operations require explicit user confirmation before tool execution.
