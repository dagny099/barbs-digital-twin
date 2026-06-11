---
title: Debug Tools
tags:
  - developer
  - debugging
  - tools
---

# Debug Tools

Three tools for diagnosing retrieval behavior before touching production code. Use these whenever a response seems wrong — they'll tell you exactly what context the LLM received and why.

---

## `replay_retrieval.py` — Neo4j Retrieval Debugger

The most important diagnostic tool. Shows exactly what context the LLM received from Neo4j for any query, with each chunk's composite score decomposed into its vector, project-link, entity-mention, and length components.

```bash
# Run any query and see scores + retrieved context
python replay_retrieval.py --query "How did you get into beekeeping?"

# Compare Neo4j vs ChromaDB rankings side-by-side
python replay_retrieval.py --query "..." --compare

# Find a past query in query_log.jsonl and replay it
python replay_retrieval.py --replay "beekeeping" --compare

# Unlock personal-tier chunks
python replay_retrieval.py --query "..." --tier personal

# Show full chunk text (not truncated)
python replay_retrieval.py --query "..." --full
```

### What the `--compare` output looks like

```
Neo4j Rank | ChromaDB Rank | Δ | Section Name           | Composite | Vec Score
-----------+---------------+---+------------------------+-----------+----------
    1      |      3        | ↑ | Beekeeping Origin KB   |  0.781    |  0.860
    2      |      1        | ↓ | Career Narrative Ch3   |  0.727    |  0.855
    3      |      5        | ↑ | Resume Explorer KB     |  0.701    |  0.743
```

Sections moving **up (↑)** in Neo4j ranking earned graph bonuses.  
Sections moving **down (↓)** had strong vector similarity but fewer graph connections.

!!! tip "Scoring weights stay in sync"
    `replay_retrieval.py` imports `Wt_SEMANTIC`, `BONUS_PROJECT`, `BONUS_ENTITY`, and `BONUS_LENGTH` directly from `neo4j_utils.py` — so the debug script and production code always use identical weights. No drift.

---

## `chunk_inspector.py` — ChromaDB Chunk Quality Auditor

Audits chunk quality in ChromaDB and simulates retrieval without running the full app. Use this to:
- Diagnose why a topic isn't being retrieved well
- Find orphaned tiny chunks after ingestion
- Confirm new content landed correctly

```bash
python chunk_inspector.py                        # Full audit report
python chunk_inspector.py --source kb-projects   # One source only
python chunk_inspector.py --query "Resume Explorer architecture"
python chunk_inspector.py --tiny                 # Show chunks < 150 chars
python chunk_inspector.py --all-chunks           # Dump every chunk
python chunk_inspector.py --query "..." --n 12   # Retrieve N chunks
```

**What the audit covers:**
1. Chunk size distribution — find orphaned tiny chunks from parsing errors
2. Per-source breakdown — chunk count and average size per source
3. Retrieval simulation — embeds a query and shows retrieved chunks exactly as the LLM would see them
4. Gap detection — sections with suspiciously few chunks

---

## `evals/compare_runs.py` — A/B Eval Run Viewer

A Gradio side-by-side viewer for any two eval runs saved under `evals/eval_results/`. Use it after running `evals/run_evals.py` more than once — for example, before/after a prompt edit, a scoring-weight change, or a model upgrade — to see exactly where the two runs diverge.

```bash
python evals/compare_runs.py                    # http://localhost:7863
python evals/compare_runs.py --port 7864        # custom port
```

The viewer auto-discovers `eval_results_*.json` files, pre-selects the two most recent runs, and lets you swap either side from a dropdown. For each question it shows:

- Both responses side-by-side
- Per-run retrieval stats (count, avg/max similarity, latency)
- The retrieved chunk cards with **"only in A" / "only in B"** badges, so you can spot ranking drift at a glance
- The rubric category and any metadata for the question
- A collapsible per-run metadata panel (model, temperature, top-k, backend)

This is the fastest way to confirm a tuning change actually moved retrieval where you expected — and to catch unintended regressions on other questions before they ship.

---

## `app_admin.py` — Admin Interface

A developer-focused debug interface that runs alongside the main app:

```bash
python app_admin.py   # http://localhost:7862 (or $ADMIN_PORT)
```

### Features

**Shared with `app.py`** (when `SHOW_SETTINGS_PANEL=true`):
- Multi-provider model switching — compare OpenAI, Anthropic, Google, and Ollama via LiteLLM
- Adjustable top-k and temperature — experiment without code changes
- Session cost tracking — running token count and USD cost

**Admin-only:**
- **Side-by-side chat + retrieval inspector** — every retrieved chunk with cosine similarity scores, visible as you chat
- **Collection browser** — browse, filter, and text-search all chunks in the knowledge base
- **Semantic probe** — embed any query and rank the entire collection to check KB coverage
- **Separate logging** — writes to `query_log_admin.jsonl` so experimentation doesn't corrupt production analytics

!!! note "Local only"
    `app_admin.py` is not included in the Hugging Face Spaces deployment. Never expose it on a public port.

### Model switching

Set provider API keys in `.env` to unlock non-OpenAI models:

| Provider | Key | Example LiteLLM Model String |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `openai/gpt-4.1` (default), `openai/gpt-5.1`, `openai/gpt-5-nano` |
| Anthropic | `ANTHROPIC_API_KEY` | `anthropic/claude-haiku-4.5`, `anthropic/claude-haiku-3.5` |
| Google | `GEMINI_API_KEY` | `gemini/gemini-2.5-flash`, `gemini/gemini-2.5-flash-lite` |
| Ollama | (local server) | `ollama/llama3.2`, `ollama/mistral` |

See `AVAILABLE_MODELS` in `app.py` for the live list. Ollama requires a local server running at the default port.

---

## Diagnostic Workflow

When a response seems wrong, work through the **[Diagnostic Playbook](diagnostic-playbook.md)** — it's a single decision tree that branches across all five tools (this page, `chunk_inspector.py`, `app_admin.py`, `compare_runs.py`, and `analyze_logs.py`) and tells you which one to reach for at each step.

Quick version:

1. **`replay_retrieval.py --query "..." --compare`** — What did Neo4j retrieve? Did ChromaDB retrieve something different? Is the correct context in the top-5?
2. If the correct context *wasn't* retrieved: **`chunk_inspector.py --query "..."`** — Is the relevant chunk in ChromaDB? Is it indexed?
3. If the correct context *was* retrieved but the answer is still wrong: The issue is in the system prompt or the LLM, not retrieval. Review `SYSTEM_PROMPT.md`.
4. If the issue is in graph signals (Neo4j demoting a high-similarity chunk): Review the composite scores in step 1 and consider whether bonuses are disproportionate relative to the vector leader.
