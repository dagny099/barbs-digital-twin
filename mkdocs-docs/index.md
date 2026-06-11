---
title: Home
tags:
  - overview
  - graphrag
---

# Barb's Digital Twin

**An AI-powered portfolio chatbot that answers questions about Barbara Hidalgo-Sotelo — in her voice, grounded in her actual knowledge.**

<div class="grid cards" markdown>

-   :brain:{ .lg .middle } **GraphRAG Retrieval**

    ---

    Hybrid Neo4j retrieval combines vector similarity (dominant signal) with graph bonuses for project-linked and entity-rich sections. No hallucination by design.

    [:octicons-arrow-right-24: Architecture](architecture/system-overview.md)

-   :speech_balloon:{ .lg .middle } **Authentic Voice**

    ---

    The system prompt is a carefully engineered 13-section document that keeps Barbara's tone consistent, redirects out-of-scope requests, and handles uncertainty honestly.

    [:octicons-arrow-right-24: Retrieval & Scoring](architecture/retrieval-and-scoring.md)

-   :shield:{ .lg .middle } **Sensitivity Tiers**

    ---

    Content is gated by tier — `public`, `personal`, and `inner_circle`. Deeper tiers unlock via passphrase, ensuring the right depth for the right audience.

    [:octicons-arrow-right-24: Passphrase & Tiers](getting-started/tiers.md)

-   :bar_chart:{ .lg .middle } **Production-Grade Logging**

    ---

    Every query is logged with latency, cost, model, retrieval scores, and thumbs ratings. Analytics scripts surface knowledge gaps and cost trends.

    [:octicons-arrow-right-24: Developer Docs](developer-docs/local-setup.md)

-   :test_tube:{ .lg .middle } **Multi-Provider LLM**

    ---

    OpenAI, Anthropic, Google, and Ollama all supported via LiteLLM. Switch models in `.env` — no code changes needed.

    [:octicons-arrow-right-24: Environment Variables](reference/environment-variables.md)

-   :tools:{ .lg .middle } **Admin Debug Interface**

    ---

    `app_admin.py` provides a live side-by-side chat + retrieval inspector, collection browser, and semantic probe for deep diagnostics.

    [:octicons-arrow-right-24: Debug Tools](developer-docs/debug-tools.md)

</div>

---

## How It Works

This digital twin uses **GraphRAG** — retrieval-augmented generation backed by a Neo4j knowledge graph. Here's the pipeline at a glance:

1. **Curated Knowledge Base** — Biographical sketches, project summaries, publications, and website content are parsed into named sections using `##` header boundaries.
2. **Graph Construction** — Sections become nodes in a Neo4j graph with 1536-dimension OpenAI embeddings. An entity extraction pipeline links 167 canonical entity nodes (Skills, Methods, Technologies, Concepts) to sections via `MENTIONS` relationships. Projects link to their sections via `DESCRIBED_IN`.
3. **Hybrid Retrieval** — User queries are embedded and matched against Neo4j's vector index. A composite score — vector similarity (×0.85) plus graph bonuses for project links (+0.08), entity mentions (+0.05), and section length (+0.02) — reranks candidates.
4. **Tier Gating** — Sensitivity tiers (`public` / `personal` / `inner_circle`) gate which sections are eligible. Deeper tiers unlock via passphrase.
5. **Response Generation** — Top-K sections are injected as context into the system prompt. A multi-provider LLM generates responses in Barbara's voice via LiteLLM.

---

## Status & Roadmap

!!! success "Live on AWS EC2"
    Two deployments run from the same `main` branch — same codebase, different `.env` files:

    - **[twin.barbhs.com](https://twin.barbhs.com)** — ChromaDB backend (`RETRIEVAL_BACKEND=chromadb`)
    - **[graphy.twin.barbhs.com](https://graphy.twin.barbhs.com)** — Neo4j GraphRAG backend (`RETRIEVAL_BACKEND=neo4j`)

    A secondary mirror is also available on Hugging Face Spaces. Both EC2 deployments use automated GitHub Actions CI/CD.

=== "Completed"

    - [x] GraphRAG pipeline with Neo4j hybrid retrieval
    - [x] Multi-provider LLM support (OpenAI, Anthropic, Google, Ollama via LiteLLM)
    - [x] Sensitivity tier system (`public` / `personal` / `inner_circle`)
    - [x] Production-grade query logging with <16μs overhead
    - [x] 47-test unit suite gating EC2 deploys in CI
    - [x] Integration healthcheck script (`scripts/healthcheck.py`)
    - [x] Admin debug interface with retrieval inspector
    - [x] Offline eval harness across 7 question categories (58 questions)

=== "In Progress / Planned"

    - [ ] Multi-modal support — image understanding for project screenshots
    - [ ] Citation tracking — return source documents with responses
    - [ ] Session-aware project diversity — avoid walkthrough repetition
    - [ ] Conversation memory — session-based context across turns
    - [ ] Voice interface — speech-to-text / text-to-speech
    - [ ] Eval baseline comparison flag (`--compare-baseline`)

---

## Tech Stack

| Component | Technology |
|---|---|
| **LLM** | Multi-provider via LiteLLM (OpenAI, Anthropic, Google, Ollama) |
| **Embeddings** | OpenAI `text-embedding-3-small` (1536 dimensions) |
| **Knowledge Graph** | Neo4j — hybrid vector + graph retrieval (production) |
| **Vector Fallback** | ChromaDB — pure vector baseline and A/B comparison |
| **UI Framework** | Gradio |
| **Language** | Python 3.11 |
| **Deployment** | AWS EC2 (primary), Hugging Face Spaces (secondary) |
| **CI/CD** | GitHub Actions |

---

## Start Exploring

<div class="grid" markdown>

[:material-chat: **Chat with the Twin**](https://twin.barbhs.com){ .md-button .md-button--primary }
[:material-book-open: **Quick Start**](getting-started/quick-start.md){ .md-button }
[:material-github: **View Source**](https://github.com/dagny099/barbs-digital-twin){ .md-button }

</div>

---

*Built with curiosity, engineered with precision.  
"I can, I will, and I shall!" — Barbara's mantra*
