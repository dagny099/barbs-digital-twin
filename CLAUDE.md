# Digital Twin — Claude Code Context

Barbara's AI-powered portfolio chatbot. Visitors ask questions; the system retrieves relevant
chunks from a knowledge base and generates responses in Barbara's voice via a Gradio UI.
Lives at twin.barbhs.com (EC2 primary) and HuggingFace Spaces (secondary).

## Architecture

**Both Neo4j and ChromaDB are live.** Neo4j handles production retrieval (`query_neo4j_rag()`
in `neo4j_utils.py`). ChromaDB remains intact as a fallback and comparison baseline.
Do not assume one replaced the other.

Retrieval flow: user query → OpenAI embedding → Neo4j hybrid (vector + graph signals)
→ context injected into system prompt → LiteLLM multi-provider completion → Gradio stream.

## Key commands

```bash
python app.py                          # Run the main app (localhost:7860)
python app_admin.py                    # Debug UI with live retrieval inspector (localhost:7862)
.venv/bin/pytest tests/ -v             # Unit tests — run before any push
python scripts/healthcheck.py          # Validate all external service connections
```

## Debug tools (use these before touching retrieval code)

**`replay_retrieval.py`** — Neo4j retrieval debugger. Shows exactly what context the LLM
received for any query, with composite score breakdown (+proj/+entity/+length). Use `--compare`
to see Neo4j vs ChromaDB rankings side-by-side.
```bash
python replay_retrieval.py --query "How did you get into beekeeping?" --compare
python replay_retrieval.py --replay "some past query" --compare   # finds entry in query_log.jsonl
```

**`chunk_inspector.py`** — ChromaDB chunk quality audit and retrieval simulation.
```bash
python chunk_inspector.py --query "Resume Explorer architecture"
python chunk_inspector.py --tiny    # flag short/broken chunks
```

**`app_admin.py`** — Live side-by-side chat + retrieval inspector. The fastest way to
interactively test how a new KB change affects what the LLM actually sees.

## Scoring weights — handle with care

Composite scoring weights live as named constants in `neo4j_utils.py`:
```python
SCORE_W_VECTOR  = 0.85   # dominant signal — do not reduce below ~0.80
SCORE_W_PROJECT = 0.08   # graph bonus: linked to a Project node
SCORE_W_ENTITY  = 0.05   # graph bonus: entity mentions (capped at 5)
SCORE_W_LENGTH  = 0.02   # graph bonus: section > 2000 chars
```
These were rebalanced after a hallucination caused by graph bonuses overriding a higher
vector-similarity chunk. Before changing them, read **`docs/LESSONS_LEARNED.md` Entry 001**
for the full rationale and before/after data.

## Lessons Learned

`docs/LESSONS_LEARNED.md` is a running log of non-obvious bugs, tuning decisions, and
design insights — written to feed future blog posts. **When you discover something
surprising about retrieval behavior, a scoring quirk, or a KB design tradeoff, add an
entry using the template at the top of that file.** It takes 10 minutes and saves future
debugging sessions.

## Key files

| File | Purpose |
|------|---------|
| `neo4j_utils.py` | Neo4j driver, `query_neo4j_rag()`, scoring weight constants |
| `app.py` | Main Gradio app — RAG pipeline, streaming, tool calls, logging |
| `SYSTEM_PROMPT.md` | Persona, voice, factual accuracy rules, failure mode table |
| `replay_retrieval.py` | Neo4j retrieval debugger (new — 2026-05-17) |
| `chunk_inspector.py` | ChromaDB chunk quality auditor |
| `docs/LESSONS_LEARNED.md` | Non-obvious bugs and design decisions |
| `docs/DEVELOPER_GUIDE.md` | Full architecture, KB management, ingestion commands |
| `docs/MAINTAINER_GUIDE.md` | Deployment, eval scripts, log analytics |
| `query_log.jsonl` | Per-query JSONL log (latency, cost, tier, response preview) |

## Conventions

- Sensitivity tiers: `public` → `personal` → `inner_circle`. Controlled by passphrase
  detection in `detect_audience_tier()`. The Neo4j `allowed_tiers` list gates which
  Section nodes are eligible for retrieval.
- `fetch_k = k × 4` (wider candidate pool before graph reranking). Currently set inline
  in `query_neo4j_rag()` — not exposed as an env var.
- Temperature default: 0.6 (set via `LLM_TEMPERATURE` env var or settings panel).
- The `assistant_response` field in `query_log.jsonl` is the plain-text response before
  any diagram HTML is appended — use this for content analysis, not `response_chars`.
