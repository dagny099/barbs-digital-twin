# Visual System Roadmap

**Status:** Planning. Phase 0 is a hard prerequisite for everything else.
**Created:** 2026-07-26
**Scope:** What the twin's project graphics look like, how many there are per project, and
which one appears in chat.
**Companion doc:** [DIAGRAM_DISPLAY_DESIGN.md](DIAGRAM_DISPLAY_DESIGN.md) — *when* a diagram
is shown. This doc is *what* is shown.

---

## The situation

The July 2026 consolidation push regenerated 7 of 9 project diagrams. **Accuracy clearly
improved.** The twin's own diagram now shows the `RETRIEVAL_BACKEND` branch, Neo4j "in
validation" against ChromaDB "live production", the HF Hub cold-start pull, tier detection,
and the JSONL log — none of which the previous version had. The old one claimed ChromaDB
only, GPT-4.1, and HF Spaces hosting, all now wrong.

**Aesthetics regressed at the same time**, and the loss is worth naming precisely because
each part has a different fix.

### What the old cards had

The pre-consolidation assets (e.g. `digital_twin_diagram.png`, still on disk) were *posters*:

- A title and a subtitle carrying the live URL
- Four color-coded stages, each with a role and a one-line detail
- An "Under the hood" second row for depth without clutter
- Tech-stack pills
- A byline — `barbhs.com · Barbara Hidalgo-Sotelo · Making meaning from messy data`

They read as a designed object, worked standalone outside the chat, and were consistently
**840×480**.

### What replaced them

Default-theme Mermaid renders: uniform lavender fill, no title, no branding, no footer, and
**no shape discipline**.

| Asset | Dimensions | Ratio |
|---|---|---|
| `architecture-overview_barb_twin.png` | 1254×2764 | **0.45** |
| `architecture-diagram_concept_cartography.png` | 1204×1470 | 0.82 |
| `resume_graph_explorer_diagram.png` | 1702×1924 | 0.88 |
| `academic_citation_platform_diagram.png` | 1294×1318 | 0.98 |
| `beehive_metadata_tracker_diagram.png` | 840×480 | 1.75 *(old style)* |
| `poolula-platform-diagarm.png` | 840×480 | 1.75 *(old style)* |
| `convoscope_chatbot_diagram.png` | 2112×1054 | 2.00 |
| `fitness_tracker_diagram.png` | 2722×492 | **5.53** |
| `chronoscope_diagram.png` | 2732×444 | **6.15** |

Two consequences, both visible in production today:

- **The portfolio runs two visual systems at once.** Seven Mermaid renders and two surviving
  cards. Inconsistency reads as unfinished more than either style reads as ugly.
- **Extreme ratios break in a chat column.** At the 740px cap, the twin diagram renders
  ~1,630px tall — a scroll wall. ChronoScope renders ~120px tall — illegible. The recent
  `height:auto` fix (`e387b9c`) didn't cause this; it revealed it.

### Two facts that shape the plan

1. **Nothing is lost.** Three old cards survive on disk unreferenced
   (`digital_twin_diagram.png`, `concept_cartographer_diagram.png`,
   `weaving_memories_diagram.png`) and the six overwritten ones are in git history at
   `c03acf3`. Recovering the old aesthetic does not mean redrawing from scratch.
2. **The Mermaid source was never versioned.** Only rendered PNGs are in the repo — no
   `.mmd` files, no render script. **The current diagrams cannot be re-themed or regenerated
   from this repository.** This is the single blocking constraint on every aesthetic fix
   below, which is why Phase 0 exists.

---

## Phase 0 — Version the source *(prerequisite)*

Until this is done, every visual change means hand-editing binaries or reconstructing
diagrams from memory.

- `assets/diagram_src/<project>.mmd` — one Mermaid source per project, committed.
- `scripts/render_diagrams.py` — source → PNG, deterministic, one command for all projects.
- Reconstruct the 7 Mermaid sources from the rendered PNGs (they're legible; this is
  transcription, not redesign).
- Decide what happens to the 2 surviving cards: reconstruct as Mermaid, or formally keep
  them as hand-designed assets outside the pipeline. Do not leave the question open — that
  ambiguity is what produced the current split.

**Done when:** deleting every PNG and running one script reproduces the portfolio byte-for-byte
in spirit.

---

## Phase 1 — One theme, one shape

With source under version control, aesthetics become a config change rather than a redraw.

- **Theme.** A shared `%%{init}%%` block: the old cards' palette (per-stage color coding
  rather than uniform lavender), fonts, edge styling. One file, applied to all.
- **Chrome.** Restore what the cards had and Mermaid drops — title, subtitle with the live
  URL, byline. Either as Mermaid subgraph headers or as a compositing step in the render
  script.
- **Shape budget.** Constrain rendered output to a chat-safe band — roughly **1.2–2.0**
  aspect. Enforced in the render script, not by eyeballing. Diagrams that can't fit the band
  are a signal the content belongs in a *reference* asset (Phase 2), not that the band should
  stretch.

**Done when:** all 9 read as one system, and none of them breaks the chat column.

---

## Phase 2 — More than one asset per project

The expansive version, and the reason the display rule and the aesthetics are the same
problem. [D1](DIAGRAM_DISPLAY_DESIGN.md#d1--a-diagram-illustrates-it-does-not-invite)
established that a chat diagram *illustrates an answer already given*. A 2,764px-tall
architecture flowchart cannot do that. It's a fine document — it was never a chat asset.

So: give each project a small set of assets with explicit roles.

| Role | Purpose | Shape | Where it appears |
|---|---|---|---|
| `hero` | Restates the answer visually. Self-contained, branded, readable at a glance. | ~1.75, card-like | **Attached inline** in chat |
| `architecture` | The detailed, accurate flow. Depth over glanceability. | Unconstrained | **Offered** as a link, opened on request |
| `screenshot` | The thing actually running. | Native | Offered; strongest evidence for "is it real" |

This is [D4](DIAGRAM_DISPLAY_DESIGN.md#d4--attach-the-card-offer-the-deep-dive) — attach the
card, offer the deep dive — and it resolves the accuracy/aesthetics tension rather than
trading one for the other. **The new Mermaid diagrams become the `architecture` role, where
their density is a virtue. The `hero` role gets the card treatment the old assets had.**
Nothing regenerated in July is wasted; it was just filed under the wrong job.

Schema sketch for `featured_projects.yaml`:

```yaml
assets:
  hero:         fitness_tracker_card.png
  architecture: fitness_tracker_diagram.png
  screenshot:   fitness_tracker_ui.png
```

with `diagram_filename` kept as a deprecated alias so nothing breaks mid-migration.

---

## Phase 3 — Keep it from drifting again

- **Render check in CI.** Fail if a committed PNG doesn't match its `.mmd` source, so
  "regenerate the diagram" can't silently skip the theme.
- **Shape lint.** Fail if a `hero` asset falls outside the aspect band.
- **Manifest check.** Fail on a project with no `hero`, or an asset file referenced but
  missing. Would have caught the three orphaned files sitting unreferenced today.

---

## Sequencing note

Phase 0 is the only urgent item, and it's urgent for a reason unrelated to taste: **right now
the portfolio's diagrams cannot be reproduced from the repository.** That's a bus-factor
problem independent of whether the lavender ever bothers anyone.

Phases 1–3 can wait for a deliberate design session. The display-rule work in
[DIAGRAM_DISPLAY_DESIGN.md](DIAGRAM_DISPLAY_DESIGN.md) steps 1–4 does **not** depend on any
of this and can proceed in parallel — it changes *which* asset is chosen, not what the asset
looks like.

---

**Related:**
[DIAGRAM_DISPLAY_DESIGN.md](DIAGRAM_DISPLAY_DESIGN.md) ·
[MAINTAINER_GUIDE.md § Roadmap](MAINTAINER_GUIDE.md#roadmap) ·
[LESSONS_LEARNED.md Entry 004](LESSONS_LEARNED.md)
