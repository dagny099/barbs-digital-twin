---
title: What the Twin Knows
tags:
  - user-guide
  - knowledge-base
---

# What the Twin Knows

The twin's responses are grounded entirely in Barbara's curated knowledge base. Nothing is invented; nothing is pulled from general internet knowledge. Here's exactly what's in there — and what isn't.

---

## Knowledge Base Sources

The knowledge base is built from nine source types, each embedded separately so provenance is tracked at the chunk level:

| Source | Content | Priority |
|---|---|---|
| **KB: Biosketch** ⭐ | Identity, background, values, personality | Highest — wins all conflicts |
| **KB: Philosophy & Approach** | How Barbara thinks about data, meaning-making, what good work looks like | High |
| **KB: Professional Positioning** | What sets Barbara apart, the cognitive science angle, four problems she solves | High |
| **KB: Project Portfolio** | Registry of all major projects with tech stack, deployment status, cross-project connections | Medium-high |
| **KB: Career Narrative** | Career arc told as a story — five chapters from MIT through independent GenAI work | Medium |
| **KB: Publications** | Academic papers, conference posters, and dissertation with PDF links | Medium |
| **Project Summaries** | One-page PDFs for 20+ projects: What it is / Who it's for / What it does / How it works | Medium |
| **Jekyll Website** | Pages from [barbhs.com](https://barbhs.com) — fetched via sitemap | Medium |
| **Project Walkthroughs** | Deep-dive content for featured projects; linked to Project nodes in Neo4j | Medium |

---

## What the Twin Knows Well

- :white_check_mark: Barbara's professional background and career trajectory
- :white_check_mark: Detailed technical architecture for 20+ projects
- :white_check_mark: Design decisions and engineering tradeoffs
- :white_check_mark: Published research and academic work (430+ citations)
- :white_check_mark: Working philosophy and what "good work" means to her
- :white_check_mark: Skills, tools, and technologies (RAG, Neo4j, Python, Gradio, etc.)
- :white_check_mark: The connection between cognitive science and her current AI work
- :white_check_mark: Featured projects with rich walkthrough context

---

## Featured Projects

These four projects get proactive surfacing — the twin brings them up when they're relevant proof points:

| Project | What it demonstrates |
|---|---|
| **Resume Explorer** | Knowledge graph design, SKOS/ESCO ontologies, structured career data, explainable graph |
| **Concept Cartographer** | Stateful LLM systems, structured outputs, real-time graph building during conversation |
| **Beehive Photo Tracker** | Computer vision, domain-specific datasets, applying AI to real lived problems |
| **Digital Twin (this system)** | RAG design, GraphRAG retrieval, knowledge engineering as portfolio methodology |
| **ChronoScope** | Temporal event extraction, document processing, career visualization |

Non-featured projects (including the Fitness Pipeline, ConvoScope, and others) are equally real — the twin will discuss them fully when asked.

---

## What the Twin Doesn't Know

- :x: Real-time availability, scheduling, or calendar
- :x: Unpublished or proprietary work details
- :x: Information with a cutoff date beyond the knowledge base
- :x: Private personal information not explicitly included in the KB
- :x: Opinions on current events or trending topics
- :x: Anything outside Barbara's documented professional and personal background

When the twin encounters a gap, it says so clearly and can optionally send a notification to Barbara flagging the gap.

---

## Source Priority Order

When two sources say different things, the twin resolves conflicts using this hierarchy:

1. Biosketch / personal background context
2. Philosophy and positioning context
3. Intellectual foundations (frameworks, influences)
4. Dissertation and research context
5. Projects overview document
6. Individual project briefs and documentation
7. Career narrative context
8. Easter eggs / personal recognition context

The biosketch is the authoritative source of truth — it always wins.
