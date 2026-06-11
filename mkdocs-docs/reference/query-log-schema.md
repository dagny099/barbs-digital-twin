---
title: Query Log Schema
tags:
  - reference
  - logging
  - analytics
---

# Query Log Schema

`query_log.jsonl` is the project's primary observability surface. Every chat turn appends one JSON row; every 👍/👎 vote appends another. Analytics scripts (`scripts/analyze_logs.py`), eval baselines, and ad-hoc debugging all read this file — so a stable, well-understood schema is load-bearing.

The schema is defined in two places in `app.py`:

- **Query rows** — `_log_query()` in `app.py`
- **Vote rows** — `handle_vote()` in `app.py`

The admin interface (`app_admin.py`) writes the same schema to a separate file (`query_log_admin.jsonl`) so experimentation never corrupts production analytics.

!!! note "Logging fails silently — by design"
    Both writers wrap their work in a try/except that swallows all exceptions. Logging must **never** affect what a visitor sees. The tradeoff: a row may be missing, but a chat will never break because of a log write.

---

## Query Row (chat turn)

One row per user turn. Written after the LLM response is fully generated.

### Identity & timing

| Field | Type | Description |
|---|---|---|
| `ts` | ISO-8601 string | UTC timestamp at log-write time (post-response) |
| `session_id` | string \| null | Gradio `session_hash` — anonymous, browser-tab scoped. Good for grouping turns within one conversation. Not stable across reloads. |
| `turn_index` | int | Current user turn within this session (1-indexed) |

### User input

| Field | Type | Description |
|---|---|---|
| `message` | string | The user's question, **PII-redacted** (`[EMAIL]`, `[PHONE]`) by `_redact_log_text()` |

### Assistant output

| Field | Type | Description |
|---|---|---|
| `assistant_response` | string | Full plain-text response **before any diagram HTML is appended**. PII-redacted. Use this — not `response_chars` — for content analytics. |
| `assistant_response_preview` | string | First 300 chars of `assistant_response`, newlines collapsed. Optimized for quick scanning. |
| `response_chars` | int | Length of the response after any HTML appendix. |

### Routing & workflow

| Field | Type | Description |
|---|---|---|
| `project` | string \| null | Featured project key if the turn matched one (e.g. `"resume-explorer"`) |
| `walkthrough` | bool | `true` if the turn entered walkthrough mode |
| `workflow` | string | `"walkthrough"` · `"diagram_only"` · `"standard"` |
| `tool_called` | bool | `true` if the LLM invoked a tool |
| `tool_name` | string \| null | `"send_notification"` · `"dice_roll"` · `null` |
| `had_error` | bool | True if the turn raised an exception |
| `empty_response` | bool | True if the LLM returned an empty string (rare, useful for flagging stream failures) |

### Audience & traffic source

| Field | Type | Description |
|---|---|---|
| `audience_tier` | string | `"public"` · `"personal"` · `"inner_circle"` — output of `detect_audience_tier()` |
| `is_owner_traffic` | bool | `true` when the visitor ticked the **"exclude my traffic"** checkbox. Used by `analyze_logs.py --exclude-owner`. Resets to `false` on every page load. |

### Model & retrieval config

| Field | Type | Description |
|---|---|---|
| `model` | string | LiteLLM model string actually used (e.g. `"openai/gpt-4.1"`) |
| `provider` | string | Resolved provider — `"openai"` · `"anthropic"` · `"gemini"` · `"ollama"` |
| `temperature` | float | Generation temperature for this turn |
| `retrieval_backend` | string | `"neo4j"` or `"chromadb"` — the value of `RETRIEVAL_BACKEND` at startup |
| `n_chunks_retrieved` | int | Number of **anchor** sections actually returned (≤ `n_chunks_config`). Does **not** include NEXT_SECTION neighbor sections appended by the Neo4j backend — those flow into the LLM context but are not counted here. When comparing per-chunk metrics across backends, segment by `retrieval_backend` first. |
| `n_chunks_config` | int | The configured top-k (`N_CHUNKS_RETRIEVE`) |
| `chunk_similarity_avg` | float | Mean cosine similarity across retrieved chunks (0–1) |
| `chunk_similarity_max` | float | Max cosine similarity (0–1) — your best evidence of whether retrieval found a strong match |

### Cost & latency

| Field | Type | Description |
|---|---|---|
| `latency_ms` | int | End-to-end response time, ms |
| `cost_usd` | float \| null | LiteLLM-computed cost for this turn |
| `prompt_tokens` | int \| null | Prompt token count (null when not reported by the provider, e.g. streaming) |
| `completion_tokens` | int \| null | Completion token count |

---

## Vote Row (thumbs up/down)

One row appended when a visitor clicks 👍 or 👎. Distinguished from query rows by the `event` field.

| Field | Type | Description |
|---|---|---|
| `event` | string | Always `"vote"` — filter on this to separate votes from query rows |
| `ts` | ISO-8601 string | UTC timestamp at click time |
| `session_id` | string \| null | Same identity as the corresponding query row |
| `liked` | bool | `true` for 👍, `false` for 👎 |
| `message_index` | int | Position of the voted-on assistant message in the chat history |
| `user_message` | string | The user turn that produced the voted response (PII-redacted, ≤300 chars) |
| `response_snippet` | string | Preview of the voted assistant response (PII-redacted, ≤300 chars) |
| `model`, `temperature`, `retrieval_backend`, `cost_usd` | — | Pulled from the most recent `SessionTracker` call so votes can be segmented by model and backend |
| `is_owner_traffic` | bool | Same semantics as query rows |

Vote rows let `analyze_logs.py --votes` compute satisfaction rates per model, per tier, per backend without joining tables.

---

## Reading the log

```bash
# Last 5 query rows, formatted
tail -5 query_log.jsonl | jq .

# Just votes
jq -c 'select(.event == "vote")' query_log.jsonl

# Negative votes only, with the question that produced them
jq -c 'select(.event == "vote" and .liked == false) | {ts, user_message, response_snippet}' query_log.jsonl

# Drop owner-flagged rows
jq -c 'select(.is_owner_traffic != true)' query_log.jsonl

# All knowledge gaps (max similarity below 0.55)
jq -c 'select(.chunk_similarity_max != null and .chunk_similarity_max < 0.55) | {ts, message, chunk_similarity_max}' query_log.jsonl
```

For the same analyses with formatted reports, summaries, and trend tables, use `scripts/analyze_logs.py` — see [EC2 Primary → Query logs](../deployment/ec2-primary.md#query-logs).

---

## Privacy & PII

The redaction layer (`_redact_log_text()` in `app.py`) replaces:

- Email addresses → `[EMAIL]`
- US phone numbers → `[PHONE]`

It does **not** attempt to redact:

- Names mentioned by the user
- Free-form personal details ("I work at X")
- Information already returned by the LLM

The log is intended to be operational, not anonymized. Treat `query_log.jsonl` like a server log: don't post it in public; rotate it like any other sensitive artifact.

---

## Schema evolution

Earlier log rows have fewer fields than current rows — `app.py` has accumulated fields over time. When writing analytics, treat missing fields as `null` rather than assuming presence:

```python
row.get("chunk_similarity_max")  # not row["chunk_similarity_max"]
```

Notable additions, oldest → newest:

- `session_id`, `turn_index` — added for session grouping
- `assistant_response`, `assistant_response_preview` — added when content analytics outgrew length-only metrics
- `audience_tier`, `is_owner_traffic` — added with tier system and the owner-traffic toggle
- `retrieval_backend` — added when the Neo4j/ChromaDB consolidation landed
- `provider`, `cost_usd`, `prompt_tokens`, `completion_tokens` — added with the LiteLLM cost-tracking pass

The schema is additive: nothing has been renamed or removed. Code that defensively defaults missing fields will keep working as more fields are added.
