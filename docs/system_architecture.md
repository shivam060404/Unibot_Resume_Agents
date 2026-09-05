# System Architecture: Unibot Multi-Agent Resume Co-Pilot

> **Status:** ✅ End-to-end verified — fully operational on Groq via ADK-native `OpenAILlm`.

---

## 1. Architectural Philosophy

This system demonstrates **Enterprise-Grade GenAI Engineering** on the Google Agent Development Kit (ADK). The core design principle is:

> **Separate non-deterministic LLM reasoning from deterministic data mutation.**

LLMs are used exclusively for **semantic translation** — understanding *what* the user wants and *where* it belongs in the resume. All actual data changes are performed by **typed Python tool functions** that enforce schema contracts, execute transactionally, and return structured responses. The LLM never touches the JSON directly.

This eliminates common GenAI failure modes:
- ❌ Schema corruption from freeform LLM rewrites
- ❌ Field hallucination (e.g., invented GPA values)
- ❌ Cross-domain mutations (Skills agent editing Experiences)
- ❌ Silent state corruption

---

## 2. Model & LLM Backend

| Component | Value |
|-----------|-------|
| **Framework** | Google ADK |
| **LLM Adapter** | `google.adk.labs.openai.OpenAILlm` (ADK-native, no litellm) |
| **Backend** | [Groq](https://console.groq.com) OpenAI-compatible API |
| **Model** | `openai/gpt-oss-20b` — supports tool calling |
| **Client** | `openai.AsyncOpenAI(base_url="https://api.groq.com/openai/v1")` |

**Why no litellm?** The ADK ships with its own `OpenAILlm` adapter in `google.adk.labs.openai`. By passing a pre-configured `AsyncOpenAI` client, we route all calls through Groq without any additional dependency — keeping the dependency graph minimal and the configuration explicit.

---

## 3. The 3-Tier Agent Topology (Least-Privilege Routing)

The system enforces the **Principle of Least Privilege** through a strict 3-tier hierarchy. Each tier has a clearly bounded responsibility and is granted only the tools it absolutely needs.

```
┌──────────────────────────────────────────────────────────────────┐
│  TIER 1 — Unibot Root Agent  (unibot_root)                       │
│  Tools: NONE                                                      │
│  Role: Conversational gateway. Handles greetings, career Q&A.    │
│        Detects resume-edit intent → transfers to Tier 2.          │
└──────────────────────────────┬───────────────────────────────────┘
                               │ transfer_to_agent
┌──────────────────────────────▼───────────────────────────────────┐
│  TIER 2 — Resume Router Agent  (resume_agent)                    │
│  Tools: get_resume, get_section  (READ-ONLY)                     │
│  Role: Translates fuzzy NL requests into concrete system targets. │
│        Resolves "my first job" → exp_1. Splits multi-step edits.  │
│        Selects the correct Tier 3 agent → transfers.             │
└──┬──────────┬───────────┬───────────┬───────────────────────────┘
   │          │           │           │           │
   ▼          ▼           ▼           ▼           ▼
Summary  Experiences  Educations   Skills    Projects
 Agent     Agent        Agent       Agent     Agent
```

### Tier 1 — Conversational Gateway

- **Agent:** `unibot_root`
- **Tools:** **None** (enforced by `tools=[]`)
- **Responsibility:** First contact. Handles greetings and Unimad career questions. The moment it detects resume-edit intent ("update my summary", "add a skill"), it immediately calls `transfer_to_agent("resume_agent")`.
- **Guardrail:** Cannot read or mutate the resume under any circumstances.

### Tier 2 — Orchestrator / Router

- **Agent:** `resume_agent`
- **Tools:** `get_resume`, `get_section` (read-only inspection only)
- **Responsibility:** Semantic disambiguation. Uses read tools to inspect the live resume and resolve ambiguous references (ordinals, fuzzy job title matches, "my first experience"). Identifies the target section and transfers with a resolved, concrete intent.
- **Guardrail:** Strictly read-only. Has zero mutation tools. Cannot modify state.

### Tier 3 — Domain Experts (Section Agents)

Five isolated agents, each owning exactly one resume section:

| Agent | Section | Mutation Tools |
|-------|---------|---------------|
| `summary_agent` | `summary` | `update_summary` |
| `experiences_agent` | `experiences[]` | `update_experience`, `add_experience_bullet`, `edit_experience_bullet`, `remove_experience_bullet` |
| `educations_agent` | `educations[]` | `update_education` |
| `skills_agent` | `skills[]` | `add_skill`, `remove_skill`, `update_skill` |
| `projects_agent` | `projects[]` | `add_project`, `update_project`, `remove_project` |

> **Tool Scoping:** The `skills_agent` physically cannot see `add_experience_bullet`. Cross-domain mutations are architecturally impossible, not just prompt-instructed.

---

## 4. Transactional State Engine (ResumeStore)

All live resume state is held inside a **singleton `ResumeStore`** Python object — never as a raw dictionary accessible to the LLM.

### Fail-Fast Startup
On initialization, `ResumeStore` loads `resume_data/resume.json` and validates it against the full schema. If the file is malformed or violates the schema, the process **exits immediately**. Silent corruption at startup is impossible.

### Anti-Aliasing Read Layer
`get_resume()` and `get_section()` return `copy.deepcopy()` snapshots of the internal state. Agents receive a copy, never a reference. Accidental in-memory mutation from the LLM tool layer is impossible.

### Transactional Writes

Every mutation tool wraps its operation in a 4-step transaction:

```
1. SNAPSHOT  →  Deep copy of current state saved to rollback buffer
2. MUTATE    →  Python tool applies the change to the in-memory dict
3. VALIDATE  →  Full schema validation against field whitelists
4. COMMIT    →  If valid, changes persist
   ROLLBACK  →  If invalid, state reverts to snapshot; error returned
```

This means the LLM can **never** leave the resume in a corrupted intermediate state.

---

## 5. Self-Correcting Tool Envelopes

Every tool returns a standardized Result Envelope, making errors machine-readable to the LLM:

**Success:**
```json
{ "ok": true, "data": { ... } }
```

**Failure:**
```json
{
  "ok": false,
  "error_code": "INVALID_ID",
  "message": "No project with id 'proj_99'.",
  "hint": "Valid ids: ['proj_1', 'proj_2']. Call get_section('projects') to inspect."
}
```

The LLM reads the error in the ADK conversation history, calls `get_section('projects')` to find the correct ID, and retries — **no application crash, no user-visible failure**.

---

## 6. Prompt Architecture

All agent prompts follow a strict, standardized contract enforced as a template:

```
[ROLE]          — Who this agent is and what it owns
[SCOPE]         — Exactly which section/fields it manages
[TOOL POLICY]   — Which tools to call and when
[EDIT POLICY]   — Anti-fabrication and anti-overwrite rules
[GUARDRAILS]    — Explicit list of what the agent must NEVER do
[EXAMPLES]      — Annotated few-shot examples
```

Key constraints in every section agent:
- **Anti-Fabrication:** "Never invent metrics, percentages, or facts not provided by the user."
- **Confirmation Protocol:** "Before calling any `remove_*` tool, you MUST confirm the exact item with the user."
- **Scope Boundary:** "If the user requests a change outside your section, reply that you cannot help and suggest they rephrase to the main assistant."

---

## 7. Security & Configuration

| Concern | Mitigation |
|---------|-----------|
| API Key exposure | Keys loaded from `.env` via `python-dotenv`; `.gitignore` excludes `.env` |
| Source control secrets | `.env.example` with placeholder values committed; real keys never committed |
| Destructive operations | Mandatory confirmation protocol in prompts before any `remove_*` call |
| Schema drift | Strict Python field-whitelist validator rejects any unknown key |
| Multi-agent confusion | Tool scoping physically isolates each agent's mutation surface |

---

## 8. Data Flow (End-to-End)

```
User NL Input
     │
     ▼
unibot_root (Tier 1)
  ├─ Career question?  → Answer directly
  └─ Resume edit intent? → transfer_to_agent("resume_agent")
         │
         ▼
  resume_agent (Tier 2)
    ├─ Calls get_resume() / get_section() to inspect current state
    ├─ Resolves target: "first experience" → exp_1
    └─ transfer_to_agent("experiences_agent")
              │
              ▼
       experiences_agent (Tier 3)
         ├─ Calls edit_experience_bullet(id="exp_1", ...)
         │    └─ ResumeStore: Snapshot → Mutate → Validate → Commit
         │         └─ Returns: { "ok": true, "data": {...} }
         └─ Confirms success to user: "Done! I've updated that bullet."
```
