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
Wt_SEMANTIC    = 0.60
BONUS_PROJECT  = 0.25   # +0.25 per project link
BONUS_ENTITY   = 0.10   # +0.10 max entity mentions
BONUS_LENGTH   = 0.05   # +0.05 for long chunks

# After (vector similarity restored as primary signal):
Wt_SEMANTIC    = 0.85
BONUS_PROJECT  = 0.08
BONUS_ENTITY   = 0.05
BONUS_LENGTH   = 0.02
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

---

## Entry 003 — 2026-06-02 — NEXT_SECTION neighbor expansion added to Neo4j retrieval

**Category:** Retrieval
**Severity:** Enhancement (no failure; addresses structural gap in context coherence)

### What happened

Timeline-sensitive queries — "What was your role at UT Austin after MIT?", "What research did you do at MIT after your PhD?" — returned weaker answers from Neo4j than expected. Investigation showed the root cause was not scoring but context fragmentation: section boundaries often split a narrative mid-story, and the top-k retrieval returned isolated anchors without their continuations. The LLM was being asked to reconstruct a timeline from fragments.

### Root cause

The graph already contained `NEXT_SECTION` relationships (built by `populate_neo4j_graph.py`) but `_HYBRID_CYPHER` never used them. Scoring selected the right anchor sections, but the LLM lacked the continuation text needed to answer sequential or temporal questions coherently.

### Fix applied

`neo4j_utils.py` — added `OPTIONAL MATCH (section)-[:NEXT_SECTION]->(neighbor:Section)` after the `LIMIT $k` clause in `_HYBRID_CYPHER`, with `WHERE neighbor.sensitivity IN $allowed_tiers` to enforce tier filtering on neighbors. In `query_neo4j_rag()`, neighbor text is appended inline after the anchor in the context string under a `[continued: source — neighbor_name]` label. Neighbors already present in the top-k anchor set are deduplicated by section name. Logged metrics (`n_chunks_retrieved`, `sources`, `scores`) reflect only the k anchor sections — neighbor expansion is invisible to logging.

`replay_retrieval.py` — mirrored the same Cypher change in `run_neo4j()` and updated `print_neo4j_results()` to display neighbor sections with a `↓ continued:` label so the full LLM context is visible during debugging.

### Lesson / takeaway

`NEXT_SECTION` relationships were already in the graph — the infrastructure was there from day one. The value was latent, not extracted. Adding it to the retrieval query was a one-Cypher-clause change that costs one extra OPTIONAL MATCH per query (negligible) and gives the LLM coherent narrative context instead of fragments.

This is a general RAG principle: **don't only retrieve the best matching chunk — retrieve enough surrounding context that the answer can be constructed without inference**. Section-level chunking helps; neighbor expansion helps further.

### Blog post angle

*"The graph had the answer the whole time — we just weren't asking for it."*

The NEXT_SECTION relationship existed silently in the graph for weeks before it was used. This is a clean example of latent graph value: the structure is there, the query just doesn't exploit it. For a portfolio chatbot where narrative coherence matters (career timelines, project stories), this is arguably more important than scoring weight tuning.

### Supporting data

Use `replay_retrieval.py` with `--query "What was your role at UT Austin after MIT?"` before and after this change. The `↓ continued:` block should appear in the output, showing the continuation text the LLM now receives.

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

**Curated Sections outcompete narrative Sections on shared topics**  

Q034 ("What ML project did you build at Inflective?") retrieved Professional Positioning, Project Answer Bank, and Projects — none of which contained the ML classifier details. The Career Narrative section that did contain those details (Chapter 3a, "Applied ML at Inflective 2017–19") was indexed and queryable but lost the similarity race to curated content. Self-similarity test confirmed 3a's embedding was real and indexed.

Root cause: curated content uses dense, question-shaped vocabulary ("projects I'm proud of," "applied ML"). Narrative content uses chronological, engagement-shaped vocabulary. For any ML-shaped query, curated content wins on raw similarity even when narrative content is more topically specific.

Implication: retrieval is biased toward whatever content was written to be retrievable. New content (whether sub-chapters, new entity types, or future writing) must either match the curated style or be surfaced through retrieval-scoring adjustments rather than pure vector similarity.

---

## Entry 004 — 2026-07-26 — Regenerating diagrams for accuracy silently traded away the visual system

**Category:** UX
**Severity:** Medium (no wrong answers; degraded presentation + an unreproducible asset pipeline)

### What happened

The July 2026 consolidation push regenerated 7 of 9 project diagrams from re-reviewed
project summaries. The content genuinely improved — the twin's own diagram went from
claiming "ChromaDB, GPT-4.1, HuggingFace Spaces" to correctly showing the
`RETRIEVAL_BACKEND` branch, Neo4j in validation against ChromaDB in production, the HF Hub
cold-start pull, and tier detection.

Nobody noticed at the time that the regeneration also replaced a designed visual system with
default-theme Mermaid output. The previous assets were 840×480 cards: title, subtitle with
the live URL, four color-coded stages, an "Under the hood" detail row, tech-stack pills, and
a byline. The replacements are uniform lavender with no title, no branding, and no shape
discipline.

Two things surfaced it. First, a separate bug fix (`e387b9c`) corrected an `<img>` style that
was missing `height:auto`, which had been flattening every diagram into the same box — once
the true aspect ratios rendered, they were visibly wrong. Second, a planning pass on the
diagram *display* rules compared old and new assets side by side.

### Root cause

Three distinct causes that presented as one aesthetic complaint:

1. **No theme was ever specified.** The old cards were hand-designed; the regeneration used
   Mermaid defaults. Nothing in the repo recorded that a visual standard existed, so there
   was nothing to regenerate *against*.
2. **No shape constraint.** Rendered ratios now span 0.45 (twin, 1254×2764) to 6.15
   (ChronoScope, 2732×444) against the old system's uniform 1.75. In a 740px chat column the
   twin renders ~1,630px tall and ChronoScope ~120px tall — a scroll wall and an illegible
   strip respectively.
3. **The Mermaid source was never committed.** Only rendered PNGs live in the repo. So the
   diagrams cannot be re-themed or regenerated at all without reconstructing their source
   first — the aesthetic regression came bundled with a reproducibility loss, and the second
   is the more serious one.

A contributing factor: only 7 of 9 were regenerated, leaving two original cards in place. The
portfolio has been running two visual systems simultaneously ever since, which reads as
unfinished more than either style reads as bad.

### Fix applied

No code change yet — this entry documents the diagnosis. The plan is
[VISUAL_SYSTEM_ROADMAP.md](VISUAL_SYSTEM_ROADMAP.md), whose Phase 0 (commit `.mmd` sources
plus a render script) is a prerequisite for any visual change.

The reframe that unblocked the plan: the regenerated diagrams aren't *worse*, they're
**filed under the wrong job**. Their density is a virtue for a reference asset and a
liability for a chat attachment. So the roadmap keeps them as an `architecture` asset role
and reintroduces a `hero` card role for chat, rather than choosing between accuracy and
aesthetics. Nothing from the July push is discarded.

Recovery is cheap: three old cards survive on disk unreferenced
(`digital_twin_diagram.png`, `concept_cartographer_diagram.png`,
`weaving_memories_diagram.png`) and the six overwritten ones are in git history at `c03acf3`.

### Lesson / takeaway

**A regeneration pipeline inherits only the properties someone wrote down.** Accuracy was
specified — the summaries were re-reviewed, and accuracy improved exactly as intended. Layout,
palette, chrome, and aspect ratio were not specified anywhere, so they were silently replaced
with library defaults. The pipeline did precisely what it was told; the omission was in the
telling.

The generalizable rule: **when automating the production of a designed artifact, the design
itself has to become an input to the automation, or it will be quietly dropped on the first
regeneration.** A theme file in version control is the cheap form of this.

Second, narrower lesson: **committing rendered output without its source converts a
reversible change into an irreversible one.** The aesthetic regression would have been a
15-minute theme edit if the `.mmd` files had been committed alongside the PNGs.

Third: this is a rhyme with [Entry 001](#entry-001--2026-05-17--graph-signal-bonuses-overrode-vector-similarity-causing-hallucination).
There, graph bonuses were allowed to override a stronger vector signal; here, weak signals
(generic tag words) can create a match rather than break a tie. **Secondary signals should
break ties, not create matches** — a principle now applied in two unrelated subsystems of
this codebase.

### Blog post angle

*"The pipeline did exactly what I asked. That was the problem."*

A regeneration that measurably improved factual accuracy while silently deleting a visual
identity — because accuracy was specified and design was not. The strong version of the
argument: for AI-assisted content pipelines, every quality you care about must be
representable as an input, or it decays to the library default on the next run. Aesthetics
are the easiest quality to leave unwritten and the fastest to notice when lost.

Good companion piece to the diagram-display-rules post, since both trace back to the same
root: a design decision that lived in someone's head (or a code comment) rather than in a file.

### Supporting data

| | Old cards (pre-`c03acf3` style) | New Mermaid renders |
|---|---|---|
| Aspect ratio | 1.75 for all | 0.45 – 6.15 |
| Title / subtitle | Yes | No |
| Byline / branding | Yes | No |
| Color coding | Per-stage palette | Uniform lavender |
| Twin diagram accuracy | ChromaDB, GPT-4.1, HF Spaces (**stale**) | Dual-backend, Neo4j + ChromaDB, HF Hub pull (**correct**) |
| Rendered height at 740px column | ~423px | up to ~1,630px |
| Source committed | n/a (hand-designed) | **No** |
| Coverage | 2 of 9 still live | 7 of 9 |
