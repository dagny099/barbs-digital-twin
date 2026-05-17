# Digital Twin — Lessons Learned

A running log of observations from building and operating the Digital Twin.
Each entry captures a real incident, its root cause, the fix applied, and
the blog-post angle — so this can be mined directly when writing about the
design and engineering decisions behind the system.

Add an entry when you find a non-obvious failure, make a non-obvious tuning decision,
or notice something that would have saved debugging time if you'd known it earlier.

---

## How to add an entry

Copy the template below, fill it in, and append to the bottom of this file.
Use the query log (`query_log.jsonl`) and `replay_retrieval.py` to gather
the technical specifics.

```
## Entry NNN — YYYY-MM-DD — [Short title]

**Category:** [Retrieval | LLM | KB Design | Eval | Infrastructure | UX]
**Severity:** [Critical | Medium | Low]  (Critical = factually wrong answer shown to user)

### What happened
[1–2 sentences describing the observable symptom — what the user saw]

### Root cause
[The actual technical cause. Be specific — include scores, weights, file names.]

### Fix applied
[What was changed, where, and why. Include file:line references.]

### Lesson / takeaway
[The generalizable insight — what this means for RAG system design broadly]

### Blog post angle
[How to frame this for a technical audience. What's the story? What's surprising?]

### Supporting data
[Scores, query log timestamps, before/after comparisons]
```

---

## Entry 001 — 2026-05-17 — Graph-signal bonuses overrode vector similarity, causing hallucination

**Category:** Retrieval, LLM
**Severity:** Critical (factually wrong answer delivered to live user)

### What happened

The Digital Twin was asked: *"How did you get into beekeeping, and does it
influence your work?"* — a curated example question. The response stated:

> "Beekeeping started as a curiosity-turned-hobby when I moved into a house
> with enough backyard space and a bit of a 'why not?' attitude."

This is factually wrong. There was no house move. A colony of bees moved into
a bat box in the backyard of Barbara's existing home — an unexpected event that
started the whole thing. The correct origin story was in the knowledge base.

### Root cause

A two-layer failure:

**Layer 1 — Retrieval failure (the cause):**
The Neo4j hybrid retrieval uses a composite scoring formula:
```
final_score = vector_score × 0.60
            + 0.25  (if section linked to any Project node)
            + 0.10  (entity mention bonus, capped at 5 entities)
            + 0.05  (length bonus, > 2000 chars)
```
The graph-signal bonuses (max +0.40) were disproportionately large relative to
the vector weight (0.60). The answer bank chunk containing the correct origin
story had the highest raw vector similarity of any public-tier chunk (vec=0.860)
but zero project links and few entity mentions. Its composite score was ~0.516.

Richly-connected long-form sections like the Career Narrative chapter
(vec=0.679, all three graph bonuses = +0.40) scored 0.807 — and landed in the
top-5 instead. None of the top-5 retrieved chunks contained the beekeeping
origin story.

The vector signal was effectively *overruled* by graph topology for a purely
biographical question.

**Layer 2 — LLM confabulation (the amplifier):**
With no factual context about how Barbara got into beekeeping, GPT-4.1 synthesized
a plausible-sounding narrative ("moved into a house with backyard space") that
matches common beekeeping origin stories but is not Barbara's story. The system
prompt's Section 8 factual accuracy instructions were not sufficient to prevent
this when the correct context was absent.

**What made this hard to catch:**
- The chunk existed and was correctly embedded (ChromaDB ranked it #1)
- The retrieval *appeared* to be working (scores logged as avg=0.784)
- The hallucinated answer sounded confident and plausible

### Fix applied

**`neo4j_utils.py`** — rebalanced composite scoring weights:
```python
# Before (graph signals too dominant):
SCORE_W_VECTOR  = 0.60
SCORE_W_PROJECT = 0.25   # +0.25 per project link
SCORE_W_ENTITY  = 0.10   # +0.10 max entity mentions
SCORE_W_LENGTH  = 0.05   # +0.05 for long chunks

# After (vector similarity restored as primary signal):
SCORE_W_VECTOR  = 0.85
SCORE_W_PROJECT = 0.08
SCORE_W_ENTITY  = 0.05
SCORE_W_LENGTH  = 0.02
```
Graph signals still apply as tiebreakers (max +0.15) but can no longer
override a clear vector similarity lead. With the new weights, the beekeeping
answer bank chunk ranks #1 (final=0.781) rather than below 5th.

`fetch_k` was also increased from `k × 2` to `k × 4` as a secondary measure,
giving the candidate pool more runway before reranking.

**`replay_retrieval.py`** (new tool) — built a debug script that replays
any query against Neo4j, shows the exact context injected into the LLM, breaks
down the composite score into its components (+proj, +entity, +length), and
optionally compares Neo4j and ChromaDB rankings side-by-side. Usage:
```
python replay_retrieval.py --replay "beekeeping" --compare
python replay_retrieval.py --query "any question" --compare --full
```

### Lesson / takeaway

**Graph-signal bonuses in GraphRAG are topology-dependent, not semantics-dependent.**
Sections that happen to be richly connected in the graph (linked to projects,
mentioned by many entities) receive bonuses regardless of query relevance. For
biographical or Q&A-style questions, this is actively harmful: those chunks are
intentionally *not* project nodes — they're answer templates — and their value is
entirely in their semantic match, not their graph position.

The design implication: **graph signals should serve as tiebreakers, not
determiners.** The vector similarity score is earned by the chunk's actual
content. The graph signals are structural annotations. They should modulate a
semantically-ranked list, not reverse it.

A useful heuristic: if any bonus can turn a lower-similarity result into the
top result, the bonus is probably too large.

### Blog post angle

*"I built a knowledge graph to improve retrieval quality. Then the graph made
retrieval worse."*

The irony is deep: the whole point of migrating to Neo4j was to add graph signals
that would promote contextually relevant chunks. Instead, the graph topology
*demoted* the most relevant chunk (the one explicitly written to answer the exact
question) because it wasn't connected to a Project node.

This is a great example of how RAG evaluation needs to test specific factual
claims, not just "does the response sound good?" The hallucinated answer was
fluent and topically appropriate — it would have passed a vibe-check evaluation.
Only comparing it to the actual facts revealed the problem.

The debugging workflow is also worth writing about: `replay_retrieval.py`
makes the invisible visible. Before building it, a hallucination meant guessing
what went wrong. After, it's a 30-second diagnosis: run the script, see the
exact context the LLM received, understand immediately why the wrong answer
was generated.

### Supporting data

| | Before fix | After fix |
|---|---|---|
| Beekeeping chunk rank (Neo4j) | Not in top-5 | #1 (final=0.781) |
| Beekeeping chunk raw vector score | 0.860 (highest!) | 0.860 |
| Career Narrative composite score | 0.807 (was #1) | 0.727 (now #3) |
| Max graph bonus | +0.40 | +0.15 |
| Vector weight | 0.60 | 0.85 |

**Query log entry:** `ts: 2026-05-17T20:08:39.104424+00:00`
Model: `openai/gpt-4.1` | Tier: public | k=5

---

<!-- Add new entries below this line -->
