---
source: docs/LESSONS_LEARNED.md — Entry 001 (2026-05-17)
register: explaining
date: 2026-05
---

The Neo4j hybrid retrieval uses a composite scoring formula: vector score times 0.60, plus
0.25 if the section is linked to any Project node, plus a capped entity-mention bonus, plus a
small length bonus. The graph-signal bonuses — up to +0.40 — were disproportionately large
relative to the vector weight. The chunk with the correct beekeeping origin story had the
highest raw vector similarity of any public-tier chunk, but zero project links and few entity
mentions, so its composite score was ~0.516. A richly-connected Career Narrative chapter, with
all three graph bonuses, scored 0.807 and landed in the top-5 instead. The vector signal was
effectively overruled by graph topology for a purely biographical question. What made it hard
to catch: the chunk existed, was correctly embedded, and the retrieval *appeared* to be
working — the hallucinated answer just sounded confident and plausible.
