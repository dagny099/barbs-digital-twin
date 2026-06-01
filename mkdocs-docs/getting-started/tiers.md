---
title: Passphrase & Tiers
tags:
  - getting-started
  - tiers
  - privacy
---

# Passphrase & Sensitivity Tiers

Barbara's digital twin uses a three-tier content system to serve the right depth of information to the right audience — from a first-time recruiter to a close friend or family member.

---

## The Three Tiers

=== "public"

    **Default for all visitors.** No passphrase needed.

    Includes:
    - Professional background and career narrative
    - Detailed project information and technical architecture
    - Published research and academic work
    - Working philosophy and professional values
    - Skills, tools, and technologies
    - Featured projects with walkthrough mode

    This is the full portfolio experience — most visitors never need more.

=== "personal"

    **Unlocked for visitors with genuine familiarity.**

    Includes everything in `public`, plus:
    - Personal origin stories and motivations
    - Family context that shaped Barbara's approach
    - Career transitions and the "why" behind them
    - Personal interests and influences

    Appropriate for collaborators, colleagues, and people Barbara has referred to the twin.

=== "inner_circle"

    **Reserved for people who know Barbara personally.**

    Includes everything in `personal`, plus:
    - Family sayings and bilingual warmth
    - MIT labmate details and shared memories
    - Easter eggs and personal recognition signals
    - First-name register and expressive emoji responses 🐝🧠💛

    The twin will never guess who you are — but if you self-identify with a shared memory or insider reference, the tone shifts noticeably warmer.

---

## How Tier Detection Works

The `detect_audience_tier()` function in `app.py` scans the conversation history for known passphrases and familiarity signals. Detection is:

- **Case-insensitive** — `RECRUITER` works the same as `recruiter`
- **History-scanning** — once a passphrase appears anywhere in the conversation, it unlocks for the rest of the session
- **Non-announced** — the twin shifts tone naturally without saying "you've unlocked tier X"

!!! warning "Security posture"
    Tiers are a **content filtering mechanism**, not access control. They prevent Barbara's personal stories from surfacing in a stranger's cold-open query — not from a motivated adversary. The passphrase is a social signal, not a cryptographic secret.

---

## For Developers: How Tier Gating Works in Neo4j

When `query_neo4j_rag()` runs, it passes an `allowed_tiers` list derived from the detected tier:

```python
# public tier → only public-tagged sections
allowed_tiers = ["public"]

# personal tier → public + personal
allowed_tiers = ["public", "personal"]

# inner_circle tier → all sections
allowed_tiers = ["public", "personal", "inner_circle"]
```

This list is passed directly into the Cypher query's `WHERE` clause:

```cypher
WHERE s.sensitivity_tier IN $allowed_tiers
```

No post-filter hacks — the gating happens at the database query level. See [Retrieval & Scoring](../architecture/retrieval-and-scoring.md) for the full scoring formula context.

---

## For Visitors: What to Expect

!!! tip "You don't need a passphrase for a great conversation"
    The `public` tier covers Barbara's full professional portfolio. Most recruiters, collaborators, and curious visitors get everything they need without unlocking anything.

If you're someone Barbara has specifically directed to the twin with a passphrase, you'll notice:

- Warmer, more personal responses
- Stories about what shaped her approach
- Potentially bilingual warmth if you're family

If you're a stranger who asks personal questions, the twin will stay professional — not cold, just appropriately bounded. *"What drives you?"* gets the professional answer, not family stories.
