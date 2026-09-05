# System Architecture: Unibot Multi-Agent Resume Co-Pilot

## 1. Architectural Philosophy
This architecture is designed to demonstrate **Enterprise-Grade GenAI Engineering**. It prioritizes deterministic state management, strict schema enforcement, and semantic agent routing over fragile heuristic logic. It leverages the Google Agent Development Kit (ADK) to build a hierarchical, fault-tolerant system.

By physically separating non-deterministic LLM reasoning from deterministic JSON mutation tools, we eliminate common failure modes such as schema corruption, field hallucination, and destructive multi-section overwrites.

---

## 2. The 3-Tier Agent Topology (Least-Privilege Routing)

The system enforces the **Principle of Least Privilege** through a strict 3-tier hierarchy. Agents are granted only the context and tools absolutely necessary for their specific domain.

### Tier 1: The Conversational Gateway
*   **Agent:** `Unibot Root Agent`
*   **Model:** `gemini-1.5-pro` (High Reasoning)
*   **Responsibility:** Handles initial user greetings, answers general Unimad career questions, and detects when a user wants to edit their resume. 
*   **Constraints:** It has **zero tools**. It cannot read or mutate the resume. When it detects edit intent, it immediately transfers to Tier 2.

### Tier 2: The Orchestrator
*   **Agent:** `Resume Router Agent`
*   **Model:** `gemini-1.5-pro` (High Reasoning)
*   **Responsibility:** Translates fuzzy user requests ("update my first job") into concrete system targets. It disambiguates intent and splits multi-step requests.
*   **Constraints:** It is strictly **Read-Only**. It has access to `get_resume` and `get_section` tools to inspect the current state, but no mutation tools. Once the target ID is resolved, it transfers to the appropriate Tier 3 agent.

### Tier 3: Domain Experts (Section Agents)
*   **Agents:** `Summary Agent`, `Experiences Agent`, `Educations Agent`, `Skills Agent`, `Projects Agent`
*   **Model:** `gemini-1.5-flash` (Low Latency, High Tool-Calling Reliability)
*   **Responsibility:** Execute the actual edits requested by the user.
*   **Constraints:** Extreme isolation. The `Skills Agent` only has access to `add_skill`, `remove_skill`, and `update_skill`. It cannot even *see* the tools for the Experiences section, physically preventing cross-domain hallucinations.

---

## 3. The L1 State Engine (ResumeStore)

To prevent the LLM from arbitrarily hallucinating JSON structures, the live state is isolated inside a singleton `ResumeStore` Python object.

1.  **Fail-Fast Startup:** On initialization, the system loads `resume_data/resume.json`. If the file is malformed or violates the schema, the system crashes immediately. Silent corruption is impossible.
2.  **Anti-Aliasing:** Read tools (`get_resume`, `get_section`) return `copy.deepcopy()` representations of the state. Agents can never accidentally mutate the live memory dictionary.

### Transactional Writes & Rollbacks
Every mutation tool (e.g., `update_experience`) is wrapped in a transactional block:

1.  **Snapshot:** A deep copy of the current state is saved.
2.  **Mutate:** The specific Python tool applies the requested change to the dictionary.
3.  **Validate:** The entire dictionary is validated against strict field whitelists and structural schemas.
4.  **Commit/Rollback:** If validation passes, the state is committed. If the LLM passed an invalid field (e.g., trying to set `GPA` on an experience entry), the transaction rolls back, and a structured error is returned to the LLM.

---

## 4. Self-Correcting Tool Envelopes

LLMs occasionally hallucinate invalid IDs or arguments. Instead of crashing the application, this architecture uses standardized Result Envelopes to enable LLM self-correction.

If an agent attempts: `remove_project(id="proj_99")`
The deterministic tool catches the error and returns:
```json
{
  "ok": false,
  "error_code": "INVALID_ID",
  "message": "No project with id 'proj_99'.",
  "hint": "Valid ids: ['proj_1', 'proj_2']. Call get_section('projects') to inspect."
}
```
The LLM reads this JSON response in the ADK conversation history, realizes its mistake, calls `get_section('projects')` to find the correct ID, and tries again.

---

## 5. Security & Configuration

*   **API Key Management:** API keys are never hardcoded. The system relies on standard `.env` configuration (documented via `.env.example`), ensuring secrets are kept out of source control.
*   **Explicit Deletions:** Destructive operations (`remove_skill`, `remove_experience_bullet`) have a mandatory Confirmation Protocol baked into the agent prompts. The LLM must explicitly ask the user "Are you sure you want to remove X?" before calling the deletion tool.
