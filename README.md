# Digital Twin: Barbara Hidalgo-Sotelo

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Demo](https://img.shields.io/badge/demo-live-brightgreen.svg)
![GraphRAG](https://img.shields.io/badge/architecture-GraphRAG-orange.svg)
![LLM](https://img.shields.io/badge/LLM-multi--provider-purple.svg)
![Neo4j](https://img.shields.io/badge/graph-Neo4j-brightgreen.svg)

A conversational AI digital twin powered by GraphRAG — retrieval-augmented generation backed by a Neo4j knowledge graph — that embodies Barbara Hidalgo-Sotelo's professional knowledge, project portfolio, and personal expertise. Built with Python, Gradio, Neo4j, and multi-provider LLM support via LiteLLM.

## Overview

This digital twin is an intelligent interface for exploring Barbara's professional background, technical projects, and expertise. It retrieves context from a structured knowledge graph — combining vector similarity with graph signals (project links, entity mentions) — and generates responses in Barbara's voice and personality.

**For Visitors**: Chat with the twin at [twin.barbhs.com](https://twin.barbhs.com)
**For Developers**: Clone this repo to explore the GraphRAG architecture, Neo4j knowledge graph, evaluation suite, and admin debugging tools

## Screenshots

| Landing page | Conversation in action |
|---|---|
| ![Landing page](assets/demo_screenshot.png) | ![Conversation](assets/demo_conversation.png) |

## Quick Start

Want to run it locally in 5 minutes?

1. Clone the repo: `git clone https://github.com/dagny099/barbs-digital-twin.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Set `OPENAI_API_KEY` in `.env` (copy from `.env.example`)
4. Run: `python app.py`
5. Open http://localhost:7860

**Need more details?** See [DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) for full installation and setup instructions.

## Features

- **Multi-Source Knowledge Base**: Structured KB docs, project PDFs, publications, and website content — parsed into named sections with provenance metadata
- **GraphRAG Retrieval**: Hybrid Neo4j retrieval combines vector similarity (dominant signal) with graph bonuses for project-linked and entity-rich sections. ChromaDB retained as fallback and A/B comparison baseline.
- **Neo4j Knowledge Graph**: Documents, Sections, Projects, and 167 canonical entity nodes (Skills, Methods, Technologies, Concepts) connected via typed relationships
- **Section-Aware Ingestion**: Provenance tracked at the section level — every retrieved chunk knows its parent section, source document, and sensitivity tier
- **Conversational Interface**: Natural conversations via Gradio ChatInterface
- **Multi-Provider LLM Support**: OpenAI, Anthropic, Google, and Ollama via LiteLLM
- **Tool Integration**: Function calling for notifications and interactive features
- **First-Person Perspective**: Responds as Barbara with consistent voice and personality
- **Production-Grade Logging**: Tracks model performance, cost, and visitor satisfaction
- **Interactive Admin Interface**: Debug tool with retrieval inspector, semantic probe, and side-by-side Neo4j vs. ChromaDB comparison

## Tech Stack

| Component | Technology |
|-----------|------------|
| **LLM** | Multi-provider support via LiteLLM (OpenAI, Anthropic, Google, Ollama)<br>Model configurable via `LLM_MODEL` env var (see `.env.example`) |
| **Embeddings** | OpenAI text-embedding-3-small (1536 dimensions) |
| **Knowledge Graph** | Neo4j — hybrid vector + graph retrieval (production) |
| **Vector Database** | ChromaDB — pure vector fallback and A/B comparison baseline |
| **UI Framework** | Gradio |
| **Language** | Python 3.11 |
| **Deployment** | AWS EC2 (primary), Hugging Face Spaces (secondary) |

## How It Works

This digital twin uses **GraphRAG** — retrieval-augmented generation backed by a Neo4j knowledge graph:

1. **Knowledge Base**: Curated content from structured KB docs, project PDFs, publications, and Barbara's website — parsed into named sections using `##` header boundaries
2. **Graph Construction**: Sections become nodes in a Neo4j graph, embedded with OpenAI's `text-embedding-3-small`. An entity extraction pipeline populates 167 canonical entity nodes (Skills, Methods, Technologies, Concepts) connected to sections via `MENTIONS` relationships. Projects link to their descriptive sections via `DESCRIBED_IN`.
3. **Hybrid Retrieval**: User query is embedded and matched against Neo4j's vector index. A composite scoring formula — vector similarity (×0.85) plus graph bonuses for project links (×0.08), entity mentions (×0.05), and section length (×0.02) — reranks candidates. Graph signals act as tiebreakers, not overrides.
4. **Tier Gating**: A sensitivity tier system (`public` / `personal` / `inner_circle`) controls which sections are eligible for retrieval. Deeper tiers unlock via passphrase.
5. **Response Generation**: Top-K sections injected as context into a carefully designed system prompt. Multi-provider LLM generates responses in Barbara's voice.
6. **Tool Integration**: Optional function calling for notifications and interactive features.

**Want the technical details?** See [DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) for architecture diagrams, data flow, and design decisions.

## Documentation

Detailed documentation is organized by role:

### 📘 [VISITOR_GUIDE.md](docs/VISITOR_GUIDE.md)
**For everyone using the twin**
- How to ask good questions
- Example questions by category (recruiter, collaborator, curious visitor)
- What the twin knows (and doesn't know)
- Understanding responses and project walkthroughs
- Tips for better conversations

### 🔧 [DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md)
**For developers building or customizing**
- Installation & setup instructions
- Architecture diagrams and data flow
- Knowledge base management (`ingest.py`, `chunk_inspector.py`)
- Prompt engineering design philosophy
- Data sources and metadata schema
- Admin interface features
- Customizing for your own digital twin

### 🚀 [MAINTAINER_GUIDE.md](docs/MAINTAINER_GUIDE.md)
**For deployment and operations**
- EC2 & Hugging Face Spaces deployment automation
- Evaluation workflow and testing harness
- Query log analytics and cost tracking
- Database operations and ChromaDB sync
- Monitoring, troubleshooting, and maintenance schedules
- Roadmap and contributing guidelines

### 🧪 Evaluation
**For prompt iteration, regression checks, and model comparison**
- [EVALUATION_GUIDE.md](evals/EVALUATION_GUIDE.md) — Canonical reference for the evaluation system design
- [EVAL_QUICKSTART.md](evals/EVAL_QUICKSTART.md) — Quick commands for running the offline harness


## Project Structure

```
digital-twin/
├── app.py                              # Main Gradio application (public-facing)
├── app_admin.py                        # Admin/debug interface (local only, default port 7862, configurable via ADMIN_PORT)
├── featured_projects.py                # Project walkthrough logic and diagram serving
├── ingest.py                           # Master ingestion manager (start here)
├── embed_kb_doc.py                     # Generic: embed any inputs/kb_*.md document
├── embed_project_summaries.py          # Embed one-page project summary PDFs
├── embed_jekyll.py                     # Embed Jekyll website via sitemap
├── db_sync.py                          # Push/pull ChromaDB to/from HF Hub
├── utils.py                            # Shared text processing utilities
├── chunk_inspector.py                  # Audit chunk quality and simulate retrieval (run `python chunk_inspector.py --query "..."` to test RAG)
├── verify_collection.py                # Inspect ChromaDB contents
├── clear_collection.py                 # Wipe ChromaDB collection
├── requirements.txt                    # Python dependencies
├── SYSTEM_PROMPT.md                    # LLM system prompt (loaded by app.py)
├── docs/                               # Documentation organized by role
│   ├── VISITOR_GUIDE.md                # Usage guide for visitors
│   ├── DEVELOPER_GUIDE.md              # Technical guide for developers
│   ├── MAINTAINER_GUIDE.md             # Operations guide for maintainers
│   ├── PROMPT_DESIGN.md                # System prompt design rationale
│   ├── LOGGING_GUIDE.md                # Production logging setup and query analytics
│   ├── ADMIN_LOGGING_GUIDE.md          # Admin-mode logging for model comparison
│   └── USAGE.md                        # Usage patterns and best practices
├── inputs/
│   ├── kb_biosketch.md                 # Biographical sketch  ⭐ authoritative
│   ├── kb_philosophy-and-approach.md   # Working philosophy and meaning-making
│   ├── kb_professional_positioning.md  # Positioning, differentiators, value prop
│   ├── kb_projects.md                  # Project portfolio registry
│   ├── kb_career_narrative.md          # Career story and trajectory
│   ├── kb_publications.md              # Research papers and academic work
│   └── project-summaries/              # One-page PDF summaries (20 projects)
├── evals/                              # Offline evaluation harness and review artifacts
│   ├── run_evals.py                    # Execute evaluation suite
│   ├── analyze_evals.py                # Analyze results and export for review
│   ├── eval_questions.csv              # Question bank
│   ├── EVALUATION_GUIDE.md             # Canonical evaluation design reference
│   └── EVAL_QUICKSTART.md              # Quick run commands├── .chroma_db_DT/                      # ChromaDB vector store (gitignored)
├── .venv/                              # Virtual environment (gitignored)
└── README.md                           # This file
```

## Contributing

This is a personal project, but suggestions and ideas are welcome! Feel free to:
- Open issues for bugs or feature requests
- Submit PRs for improvements (especially documentation)
- Fork the repo to create your own digital twin

## License

This project is open-source under the MIT License. See `LICENSE` file for details.

The biographical content and project descriptions are © Barbara Hidalgo-Sotelo. Reuse of the *code/architecture* is encouraged; reuse of the *personal content* should be adapted to your own story.

## Contact & Links

- **LinkedIn**: [barbara-hidalgo-sotelo](https://www.linkedin.com/in/barbara-hidalgo-sotelo)
- **Personal Site**: [barbhs.com](https://www.barbhs.com/)
- **GitHub**: [dagny099](https://github.com/dagny099)
- **Google Scholar**: [Barbara Hidalgo-Sotelo](https://scholar.google.com/citations?hl=en&user=nQG25vkAAAAJ)

---

**Built with curiosity, engineered with precision.**
*"I can, I will, and I shall!"* - Barbara's mantra
