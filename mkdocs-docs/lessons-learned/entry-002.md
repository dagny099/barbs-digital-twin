---
title: "Entry 002 — Curated vs. Narrative Content"
tags:
  - lessons-learned
  - retrieval
  - knowledge-base
---

# Entry 002 — Curated sections outcompete narrative sections on shared topics

**Date:** 2026-05-17  
**Category:** Retrieval  
**Severity:** :octicons-info-16: **Medium** — retrievable but suboptimal; correct answer sometimes missing

---

## What Happened

Eval question Q034: *"What ML project did you build at Inflective?"*

The retrieval pipeline returned chunks from Professional Positioning, Project Answer Bank, and Projects — none of which contained the ML classifier details. The Career Narrative section that *did* contain those details (Chapter 3a, "Applied ML at Inflective 2017–19") was indexed and queryable but lost the similarity race to curated content.

A self-similarity test confirmed Chapter 3a's embedding was real and indexed correctly.

---

## Root Cause

Curated content uses dense, question-shaped vocabulary: *"projects I'm proud of," "applied ML," "what I built."* Narrative content uses chronological, engagement-shaped vocabulary: *"during this period," "the challenge was," "working alongside the team."*

For any ML-shaped query, curated content wins on raw vector similarity — even when narrative content is more topically specific. The curated sections were written to be retrieved; the narrative sections were written to be read.

!!! note "Retrieval is biased toward whatever content was written to be retrievable."
    This is not a bug in the scoring system — it's a property of vector similarity. A chunk written in the style of an answer will score higher on answer-like queries than a chunk written as a story, even if the story chunk is factually more complete.

---

## Fix Applied

No scoring change was made. The identified mitigation paths are:

1. **Rewrite narrative sections in a more retrieval-friendly style** — add denser, question-shaped vocabulary to chapter headers and topic sentences
2. **Add curated answer chunks for high-value factual details** — create explicit Q&A-style entries for specific project details that are only in narrative form
3. **Or accept the tradeoff** — narrative content serves a different purpose (career arc, story) and rewriting it to be curated may reduce its coherence as a narrative

The current approach is option 3 for most narrative content, with targeted option 2 additions for specific details that repeatedly fail in eval.

---

## Lesson / Takeaway

!!! tip "Design principle: know what each content type is for"
    - **Curated content** (biosketch, positioning, project registry) — write for retrieval. Dense, specific, question-shaped vocabulary. These are the answer chunks.
    - **Narrative content** (career arc, origin stories, philosophy) — write for coherence. These serve visitors who want to understand Barbara's story, not just get a fact.

If a factual detail is important enough to answer correctly in isolation, create a curated chunk for it. Don't depend on narrative context to surface specific facts.

**For new KB content:** ask which category it belongs to before writing it. If it's meant to answer specific questions, write it in curated style. If it's meant to tell a story, write it in narrative style — but don't expect it to win on factual queries.

---

## Blog Post Angle

*"Your RAG system is biased toward whatever you wrote to be retrieved — not toward what's actually most relevant."*

This is a subtle but important property: vector similarity measures linguistic proximity, not factual completeness. Content that uses the same vocabulary as the kinds of questions people ask will systematically outperform content that uses different vocabulary — even when the latter is factually richer.

The practical implication for knowledge base design: distinguish between "answer chunks" and "story chunks" from the start. Build curated answer chunks for the facts you know will be queried. Let narrative chunks serve their narrative purpose.

---

## Supporting Data

- **Query:** Q034 — "What ML project did you build at Inflective?"
- **Expected top result:** Career Narrative, Chapter 3a — "Applied ML at Inflective 2017–19"
- **Actual top results:** Professional Positioning, Project Answer Bank, Projects overview
- **Chapter 3a status:** Indexed, real embedding, not in top-5 for ML-shaped queries
- **Mechanism:** Curated sections contain "applied ML" in dense, question-shaped context; Chapter 3a uses chronological narrative framing
