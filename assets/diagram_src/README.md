# Diagram sources

Mermaid sources for the project diagrams in `assets/project_diagrams/`.
Render with:

```bash
npm install @mermaid-js/mermaid-cli        # once, at repo root
python scripts/render_diagrams.py          # all sources
python scripts/render_diagrams.py --check  # validate only, writes nothing
```

Every `.mmd` here is the source of truth. **Never hand-edit a rendered PNG** —
that is how the July 2026 diagrams became unreproducible
(see [LESSONS_LEARNED.md](../../docs/LESSONS_LEARNED.md) Entry 004).

## Theme

`_header.mmd` holds the shared frontmatter and is prepended automatically by the
render script to any source that doesn't declare its own. Files beginning with
`_` are never rendered on their own.

### Stage palette

Recovered from the pre-July card diagrams (`digital_twin_diagram.png`). Apply
with `classDef` per source and keep the stage order left to right:

| Class | Fill | Stroke | Role |
|-------|------|--------|------|
| `s1` | `#FFF8E7` | `#E0A526` | input / ingestion |
| `s2` | `#EAF7EE` | `#34A853` | processing / retrieval |
| `s3` | `#FAEFFB` | `#B44FC4` | intelligence / generation |
| `s4` | `#EAF3FE` | `#3B82D6` | output / deployment |

Stage nodes use `rx:8,ry:8` for the rounded-card look.

## Two gotchas

**Comments must come after the graph declaration.** A `%%` comment before the
`flowchart` line fails with `Parse error on line 1: Expecting 'NEWLINE',
'SPACE', 'GRAPH', got 'NODE_STRING'`, which does not point anywhere near the
real problem. Put the `flowchart` line first, then comment freely.

**Shape comes from layout, not from the width flag.** A single left-to-right row
renders at roughly 9:1 no matter what `-w` says, which is illegible in a chat
column. Stacking rows (`flowchart TB` with `direction LR` subgraphs) is what
brings a diagram into the 1.2–2.4 aspect band the render script enforces. If a
diagram can't fit the band, that's a signal it's an `architecture` asset rather
than a `hero` one — see
[VISUAL_SYSTEM_ROADMAP.md](../../docs/VISUAL_SYSTEM_ROADMAP.md) Phase 2.

## Status

| Source | Status |
|--------|--------|
| `digital_twin_card.mmd` | Worked example — renders correctly; aspect 2.58, just outside the 1.2–2.4 band pending the title/byline chrome that will add height (Phase 1) |
| *(7 Mermaid diagrams from the July push)* | **Not yet reconstructed.** PNGs exist in `assets/project_diagrams/`; sources must be transcribed from them |
| *(2 surviving hand-made cards)* | beehive, poolula — 840×480, no source, decision pending |
