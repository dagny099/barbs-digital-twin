---
title: Lessons Learned
tags:
  - lessons-learned
  - debugging
  - retrieval
---

# Lessons Learned

A running log of non-obvious failures, tuning decisions, and design insights from building and operating the Digital Twin. Each entry captures a real incident — what happened, why, what changed, and the broader design principle.

These entries are written to feed future blog posts as well as to save debugging time on the next incident. The entry format includes: category, severity, root cause, fix applied, generalizable lesson, and blog post angle.

---

## Entry Index

| # | Date | Title | Category | Severity |
|---|---|---|---|---|
| [001](entry-001.md) | 2026-05-17 | Graph-signal bonuses overrode vector similarity, causing hallucination | Retrieval, LLM | :octicons-alert-fill-24:{ .warning } Critical |
| [002](entry-002.md) | 2026-05-17 | Curated sections outcompete narrative sections on shared topics | Retrieval | :octicons-info-16: Medium |
| [003](entry-003.md) | 2026-06-02 | NEXT_SECTION neighbor expansion — latent graph value already in the schema | Retrieval | :octicons-info-16: Enhancement |

---

## How to Add an Entry

When you find a non-obvious failure, make a non-obvious tuning decision, or notice something that would have saved debugging time if you'd known it earlier:

1. Create a new file: `mkdocs-docs/lessons-learned/entry-NNN.md`
2. Add a row to the index table above
3. Use the template:

```
**Category:** [Retrieval | LLM | KB Design | Eval | Infrastructure | UX]
**Severity:** [Critical | Medium | Low]

### What happened
[Observable symptom — what the user saw]

### Root cause
[The actual technical cause. Be specific — scores, weights, file names.]

### Fix applied
[What changed, where, and why. Include file:line references.]

### Lesson / takeaway
[The generalizable insight for RAG system design]

### Blog post angle
[How to frame this for a technical audience]

### Supporting data
[Scores, query log timestamps, before/after comparisons]
```

Use `query_log.jsonl` and `replay_retrieval.py` to gather technical specifics before writing.
