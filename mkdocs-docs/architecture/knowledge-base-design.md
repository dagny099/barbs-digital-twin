---
title: Knowledge Base Design
tags:
  - architecture
  - knowledge-base
  - ingestion
---

# Knowledge Base Design

The knowledge base is the foundation of the digital twin's accuracy. The design principle is simple: **structure content for retrieval quality, not just storage.** Every architectural choice — from section boundaries to metadata schema to source priority — was made to improve what the LLM actually sees when answering a question.

---

## Source Architecture

```mermaid
graph TB
    subgraph "Knowledge Base Sources"
        KB1["KB: Biosketch ⭐\nkb_biosketch.md"]
        KB2["KB: Philosophy / Positioning /\nIntellectual Foundations"]
        KB3["KB: Dissertation\noverview · relevance · philosophy"]
        KB4["KB: Projects · Career · Publications"]
        KB5["KB: Answer Bank\nretrieval-shaped answers"]
        KB6["KB: Origins · Easter Eggs\npersonal / inner-circle tiers"]
        PDF["Project Summaries\nPDFs + 3 featured MD"]
        WEB["Jekyll Website\nbarbhs.com"]
        WALK["Project Walkthroughs\nfeatured_projects.py"]
    end

    subgraph "Processing"
        PARSE["Section-Aware Parsing\n## headers → sections"]
        CHUNK["Paragraph-Aware Chunking\n≈500 chars · 50 overlap"]
        EMBED["Generate Embeddings\ntext-embedding-3-small"]
    end

    subgraph "Storage"
        CHROMA[("ChromaDB\nfallback + A/B eval")]
        NEO4J[("Neo4j Graph\nDocument → Section → Entity")]
    end

    KB1 & KB2 & KB3 & KB4 & KB5 & KB6 --> PARSE
    PDF --> PARSE
    WEB --> PARSE
    WALK --> EMBED
    PARSE --> CHUNK
    CHUNK --> EMBED
    EMBED --> CHROMA
    EMBED --> NEO4J

    style KB1 fill:#ffd4d4,stroke:#F44336
    style CHROMA fill:#d4e8ff,stroke:#2196F3
    style NEO4J fill:#f3e5f5,stroke:#9C27B0
    style EMBED fill:#e1f5ff,stroke:#29B6F6
```

---

## Metadata Schema

Every chunk carries three provenance fields:

```python
{
    'source': 'source-type:identifier',  # e.g., 'kb-biosketch:kb_biosketch.md'
    'section': 'Section Name' or None,   # e.g., 'Professional Experience'
    'chunk_index': 0                     # position within section (resets per section)
}
```

This schema means the LLM always knows *where* a retrieved chunk came from — not just its content, but its parent section, source document, and sensitivity tier. This is the "section-aware" part of the design.

---

## Chunking Strategy

- **Chunk size**: ~500 characters (configurable)
- **Overlap**: 50 characters (re-includes trailing paragraphs to prevent boundary gaps)
- **Atomic unit**: Paragraphs (double-newline delimited) — never split mid-sentence
- **`chunk_index`**: Resets to 0 per section, not globally — this is intentional. It preserves section-relative position without inflating global indices.

The strategy balances semantic coherence (paragraphs as natural units), retrieval granularity (chunks ≈ 1–2 paragraphs), and context continuity (overlap prevents sharp boundary losses).

---

## Source Priority Order

When sources provide conflicting information, the system resolves deterministically:

1. **Biosketch** — authoritative source of truth for identity, background, and values
2. **Philosophy & Approach** — how Barbara thinks about problems
3. **Intellectual Foundations** — frameworks and influences
4. **Dissertation & Research** — academic background
5. **Projects Overview** — project registry
6. **Individual Project Briefs** — per-project documentation
7. **Career Narrative** — career arc told as a story
8. **Easter Eggs / Personal Recognition** — inner-circle content

The biosketch always wins. If it contradicts something in a project brief, the biosketch is correct.

---

## Source Types in Detail

### KB Documents (Markdown)

Curated KB documents are parsed by `embed_kb_doc.py` using the same logic: `##` headers create named section boundaries, and `chunk_prose()` handles the rest. New KB documents register in `scripts/ingest.py`.

| Source Key | File | Content |
|---|---|---|
| `kb-biosketch` | `kb_biosketch.md` | Identity, background, values — the authoritative source |
| `kb-philosophy` | `kb_philosophy-and-approach.md` | How Barbara thinks about data and meaning-making |
| `kb-positioning` | `kb_professional_positioning.md` | Differentiators, cognitive science angle, problems she solves |
| `kb-intellectual-foundations` | `kb_intellectual_foundations.md` | Frameworks and influences that shape Barbara's thinking |
| `kb-dissertation-overview` | `kb_dissertation_overview.md` | The "what" of the MIT dissertation, written for non-academic readers |
| `kb-dissertation-relevance` | `kb_dissertation_modern_relevance.md` | How that work maps onto modern ML/AI questions |
| `kb-dissertation-philosophy` | `kb_dissertation_philosophy.md` | The deeper "why" — attention research as a lens on meaning |
| `kb-projects` | `kb_projects.md` | Project registry with tech stack and deployment status |
| `kb-career` | `kb_career_narrative.md` | Five-chapter career arc from MIT through independent GenAI work |
| `kb-publications` | `kb_publications.md` | Academic papers with PDF links |
| `kb-answers` | `kb_project_answer_bank.md` | Pre-curated answers for predictable questions — written for retrieval-shaped vocabulary |
| `kb-origins` | `kb_personal_origin_stories.md` | `personal`-tier content: family context, career transitions, motivations |
| `kb-easter-eggs` | `kb_easter_eggs.md` | `inner_circle`-tier content: shared memories, family phrases, insider signals |

File paths are relative to `INPUTS_PATH` (default `inputs/`). See [Environment Variables](../reference/environment-variables.md).

### Project Summaries

Two coexisting paths, both keyed by ingest registry entries in `scripts/ingest.py`:

| Path | Source key | Script | Format |
|---|---|---|---|
| Bulk PDFs | `project-summaries` | `embed_project_summaries.py` | One-page PDFs (~20 projects) — extracted with `pdfplumber`, section headers detected via fuzzy prefix matching |
| Featured MD | `project-digital-twin`, `project-local-rag`, `project-resume-explorer` | `embed_kb_doc.py` | Longer-form markdown variants for the three featured projects, parsed by `##` headers |

Both follow the same template: *What it is / Who it's for / What it does / How it works*. PDF entries also get a synthetic "overview" chunk combining title + *What it is* + *Who it's for* — optimized for portfolio-style queries. Metadata extras on PDF chunks: `project_name`, `tech_stack` (comma-joined detected technologies).

### Jekyll Website

Fetched live via `https://barbhs.com`'s `sitemap.xml`. `trafilatura` strips nav/footer automatically. Each page becomes one document with its page title as the section name.

### Project Walkthroughs

Deep-dive context for featured projects comes from the `walkthrough_context` field in `featured_projects.py`. Each walkthrough is stored as a single Section node in Neo4j — linked to its Project node via `Project -[:DESCRIBED_IN]-> Section`, which means it earns the +0.08 project graph bonus in composite scoring.

!!! warning "ChromaDB vs Neo4j walkthroughs"
    `scripts/embed_walkthroughs.py` still exists for ChromaDB ingestion but is no longer the active path. Neo4j walkthroughs are populated during `populate_neo4j_graph.py` and embedded by `scripts/embed_sections.py`. Do not confuse the two paths.

---

## Why This Design

The core insight: **retrieval is biased toward whatever content was written to be retrievable.** Curated content that uses dense, question-shaped vocabulary ("projects I'm proud of," "applied ML") consistently outperforms narrative content that uses chronological, engagement-shaped vocabulary — even when the narrative content is more topically specific.

This has real consequences for KB design:
- New sections must either match the curated style or be surfaced through retrieval-scoring adjustments
- The biosketch's density and structure is deliberate — it's written for retrieval, not for reading
- Section boundaries matter: a chunk that straddles two topics will be retrieved for the wrong query half the time

See [Entry 002 in Lessons Learned](../lessons-learned/entry-002.md) for a concrete example of this bias in action.
