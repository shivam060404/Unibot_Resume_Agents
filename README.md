# Unibot Resume Agents

A multi-agent resume editing system built with the Google Agent Development Kit (ADK). Converts natural-language requests into schema-safe, tool-executed mutations of a JSON resume document.

## Running the System

1. Install dependencies (requires Python 3.10+):
   ```bash
   pip install -r requirements.txt
   ```
2. Create a `.env` file in the root directory based on `.env.example`.
3. Add your Google AI Studio API Key to the `.env` file: `GOOGLE_API_KEY=your_key`
4. Run the ADK web server:
   ```bash
   adk web unibot
   ```
   Or run the CLI:
   ```bash
   adk run unibot
   ```

## Swapping the Resume

**To change resume, edit `resume_data/resume.json`.**

The system loads this file at startup. It serves as the single source of truth and is strictly validated against the required schema.

## Architecture & Agent Hierarchy

The system enforces the **Principle of Least Privilege** using a strict 3-tier hierarchy.

```
Unibot Root Agent (Greetings, Career Chat, Intent Detection)
│
└─── Resume Agent (Router / Orchestrator)
      ├─── Summary Agent
      ├─── Experiences Agent
      ├─── Educations Agent
      ├─── Skills Agent
      └─── Projects Agent
```

### Token Efficiency & Tool Scoping
To prevent context-window pollution and hallucination, Section Agents only have access to `get_section(their_section)` and their specific mutation tools. The Experiences Agent cannot accidentally edit Skills.

### Transactional State Engine & LLM Self-Correction
All mutations go through a `ResumeStore` transaction: Snapshot → Mutate → Validate → Commit/Rollback. Tools return standardized Error Envelopes (e.g., `INVALID_ID`) which allow the LLM to read the error and self-correct on the next turn.

## Tool Catalog

| Agent | Tools | Purpose |
|---|---|---|
| Resume Agent | `get_resume`, `get_section` | Read-only inspection and disambiguation |
| Summary Agent | `update_summary` | Replace summary text |
| Experiences Agent | `update_experience`, `add_experience_bullet`, `edit_experience_bullet`, `remove_experience_bullet` | CRUD for work experience |
| Educations Agent | `update_education` | Factual updates to education |
| Skills Agent | `add_skill`, `remove_skill`, `update_skill` | Skill management with case-insensitive dedup |
| Projects Agent | `add_project`, `update_project`, `remove_project` | Portfolio management |

## Evaluator Queries (Sample Inputs)

Try these exact queries in the UI to see the system's routing, disambiguation, and tool execution in action:

1. *"Make my summary more senior"*
2. *"Rewrite my summary for leadership roles"*
3. *"Add a leadership bullet to my first experience"*
4. *"Add Python to my skills"*
5. *"Remove my second project"* (Triggers confirmation protocol)
6. *"Improve my first job bullets for impact"*
7. *"Add a project about an AI chatbot"*
8. *"Shorten my summary"*

## Prompt Design Rationale

All prompts follow a strict, standardized contract: `ROLE` → `SCOPE` → `TOOL POLICY` → `EDIT POLICY` → `GUARDRAILS` → `EXAMPLES`.

- **Boundaries:** Every agent explicitly states what it *cannot* do.
- **Anti-Fabrication:** Mutating agents are strictly instructed never to invent metrics or facts.
- **Confirmation Protocols:** Destructive operations (`remove_*`) require the agent to ask the user for confirmation before calling the tool.
