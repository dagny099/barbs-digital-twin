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

| Provider | Key | LiteLLM Model Format |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `openai/gpt-4.1` |
| Anthropic | `ANTHROPIC_API_KEY` | `anthropic/claude-sonnet-4-5` |
| Google | `GEMINI_API_KEY` | `gemini/gemini-pro` |
| Ollama | (local server) | `ollama/llama3` |

Ollama requires a local server running at the default port.

---

## Diagnostic Workflow

When a response seems wrong, follow this sequence:

1. **`replay_retrieval.py --query "..." --compare`** — What did Neo4j retrieve? Did ChromaDB retrieve something different? Is the correct context in the top-5?

2. If the correct context *wasn't* retrieved: **`chunk_inspector.py --query "..."`** — Is the relevant chunk in ChromaDB? Is it indexed?

3. If the correct context *was* retrieved but the answer is still wrong: The issue is in the system prompt or the LLM, not retrieval. Review `SYSTEM_PROMPT.md`.

4. If the issue is in graph signals (Neo4j demoting a high-similarity chunk): Review the composite scores in step 1 and consider whether bonuses are disproportionate relative to the vector leader.
