---
title: Key Files & API
tags:
  - reference
  - architecture
---

# Key Files & API

Quick reference for the most important files in the codebase and the functions they expose.

---

## Core Application Files

| File | Purpose |
|---|---|
| [`app.py`](https://github.com/dagny099/barbs-digital-twin/blob/main/app.py) | Main Gradio app — RAG pipeline, streaming, tool calls, logging |
| [`app_admin.py`](https://github.com/dagny099/barbs-digital-twin/blob/main/app_admin.py) | Admin/debug interface — retrieval inspector, collection browser, semantic probe |
| [`neo4j_utils.py`](https://github.com/dagny099/barbs-digital-twin/blob/main/neo4j_utils.py) | Neo4j driver, `query_neo4j_rag()`, scoring weight constants |
| [`featured_projects.py`](https://github.com/dagny099/barbs-digital-twin/blob/main/featured_projects.py) | Project walkthrough logic and SVG diagram serving |
| [`utils.py`](https://github.com/dagny099/barbs-digital-twin/blob/main/utils.py) | Shared text processing — chunking, parsing, metadata, DB operations |
| [`SYSTEM_PROMPT.md`](https://github.com/dagny099/barbs-digital-twin/blob/main/SYSTEM_PROMPT.md) | LLM system prompt — persona, voice, factual accuracy guardrails, tools |
| [`db_sync.py`](https://github.com/dagny099/barbs-digital-twin/blob/main/db_sync.py) | ChromaDB push/pull to/from Hugging Face Hub |

---

## Debug & Ingestion Tools

| File | Purpose |
|---|---|
| [`replay_retrieval.py`](https://github.com/dagny099/barbs-digital-twin/blob/main/replay_retrieval.py) | Neo4j retrieval debugger — composite score breakdown, Neo4j vs ChromaDB comparison |
| [`chunk_inspector.py`](https://github.com/dagny099/barbs-digital-twin/blob/main/chunk_inspector.py) | ChromaDB chunk quality auditor and retrieval simulator |
| [`scripts/ingest.py`](https://github.com/dagny099/barbs-digital-twin/blob/main/scripts/ingest.py) | Master ingestion manager — interactive and non-interactive modes |
| [`scripts/healthcheck.py`](https://github.com/dagny099/barbs-digital-twin/blob/main/scripts/healthcheck.py) | External service validator — env vars, OpenAI, ChromaDB, Pushover |
| [`scripts/analyze_logs.py`](https://github.com/dagny099/barbs-digital-twin/blob/main/scripts/analyze_logs.py) | Query log analytics — satisfaction, cost, knowledge gaps, model comparison |
| [`scripts/verify_collection.py`](https://github.com/dagny099/barbs-digital-twin/blob/main/scripts/verify_collection.py) | ChromaDB collection stats and chunk inspection |
| [`scripts/clear_collection.py`](https://github.com/dagny099/barbs-digital-twin/blob/main/scripts/clear_collection.py) | Wipe ChromaDB (interactive confirmation required) |

---

## Key Functions

### `neo4j_utils.py`

| Function | Signature | Description |
|---|---|---|
| `query_neo4j_rag()` | `(query, k, tier, neo4j_driver)` | Main hybrid retrieval function — vector + graph scoring, tier gating |
| Weight constants | `Wt_SEMANTIC`, `BONUS_PROJECT`, `BONUS_ENTITY`, `BONUS_LENGTH` | Composite scoring weights (see [Scoring Weights](scoring-weights.md)) |

### `app.py`

| Function | Description |
|---|---|
| `detect_audience_tier()` | Scans conversation history for passphrase signals, returns current tier |
| `build_sensitivity_filter()` | Builds ChromaDB metadata filter for tier-gated retrieval |
| `handle_tool_call()` | Dispatches LLM tool calls to `dice_roll` or `send_notification` |
| `_compute_similarity_stats()` | L2→cosine conversion, clamping, stats over a list of distances |
| `_redact_log_text()` | PII redaction for email and phone numbers in log text |
| `_build_response_preview()` | Truncates response text for log preview field |

### `utils.py`

| Function | Description |
|---|---|
| `chunk_prose()` | Paragraph-aware text chunking with configurable size and overlap |
| `parse_markdown_sections()` | Parse markdown files by `##` headers into named sections |
| `build_metadata()` | Construct standardized metadata dicts (`source`, `section`, `chunk_index`) |
| `delete_chunks_by_source()` | Wipe all ChromaDB chunks for a given source prefix |
| `section_already_embedded()` | Per-section idempotency check — skip if already stored |

---

## Log Files

| File | Contents |
|---|---|
| `query_log.jsonl` | Production query log — one JSON object per turn, includes query, response preview, model, latency, cost, similarity scores, tier, votes |
| `query_log_admin.jsonl` | Admin interface log — same schema, separate file for experimentation |

---

## Configuration Files

| File | Purpose |
|---|---|
| `.env` | Runtime environment variables (see [Environment Variables](environment-variables.md)) |
| `.env.example` | Template with all available variables and descriptions |
| `requirements.txt` | Python dependencies |
| `.github/workflows/deploy-ec2.yml` | EC2 CI/CD pipeline |
| `.github/workflows/deploy-hf.yml` | HuggingFace Spaces CI/CD pipeline |
