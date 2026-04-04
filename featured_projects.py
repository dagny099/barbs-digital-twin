"""
featured_projects.py
====================
Lightweight data + selection logic for project walkthrough responses
and diagram serving.

Architecture (v2 — decoupled diagrams from walkthroughs):

  1. Walkthrough detection  — regex on "walk me through", "show me a project", etc.
     Triggers full walkthrough enrichment (context injected into user message).

  2. Project mention detection — keyword match on project titles, tags, key terms.
     Triggers diagram serving. Much broader than walkthrough detection.

  3. Diagram serving is its own capability — fires on ANY project mention,
     not just walkthrough requests.

  4. Walkthrough mode is hybrid — walkthrough context is injected as a
     separate block (not appended to user message), so RAG retrieval
     stays grounded in the user's actual question.

To add a new project:
    1. Add a diagram image to assets/project_diagrams/
    2. Append a new dict to FEATURED_PROJECTS below
    3. That's it — the selection logic picks it up automatically

Fields per project:
    - id (str):                  URL-safe identifier
    - title (str):               Display name
    - summary (str):             2-3 sentence overview (used for casual mentions too)
    - design_insight (str):      1-2 sentences on what makes this project distinctive —
                                 gives the LLM a narrative lead for "stories before specs"
    - walkthrough_context (str): Full pipeline/architecture walkthrough for deep dives
    - diagram_filename (str):    Filename in assets/project_diagrams/
    - diagram_caption (str):     Alt-text / caption for diagram
    - tags (list[str]):          Searchable topic tags
    - mention_keywords (list):   Phrase-level triggers for project detection
    - links (dict):              Operational URLs — live demo, github, docs
    - blog_posts (list[dict]):   Blog posts / writeups about the project
                                 Each entry: {"title": str, "url": str}
                                 Rendered separately from links in context block
"""

import os
import re

# ═══════════════════════════════════════════════════════════════════
# PROJECT DATA
# ═══════════════════════════════════════════════════════════════════

_DIAGRAM_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "assets", "project_diagrams")

FEATURED_PROJECTS = [

    # ── Resume Graph Explorer ────────────────────────────────────
    {
        "id": "resume-graph-explorer",
        "title": "Resume Graph Explorer",
        "summary": (
            "Transforms a flat resume into an interactive, navigable knowledge graph "
            "built on established semantic standards (SKOS, ESCO, schema.org). Skills "
            "form hierarchies using SKOS broader/narrower relations, so the graph "
            "captures not just what someone knows but how those skills relate."
        ),
        "design_insight": (
            "The distinctive choice here is grounding applied AI work in existing "
            "standards rather than inventing a bespoke schema. The graph uses six "
            "entity types validated with SHACL constraints and mapped to the ESCO "
            "European skills taxonomy — making the output interoperable, not just pretty."
        ),
        "walkthrough_context": (
            "Resume Graph Explorer turns a flat resume into a living knowledge graph. "
            "The pipeline works in three stages: "
            "(1) Extract — An LLM (Claude, OpenAI, or Ollama) reads the resume and "
            "pulls out structured entities: skills, roles, organizations, industries. "
            "Six entity types total: Person, Job, Skill, Education, Certification, "
            "Organization, connected by typed relationships. "
            "(2) Normalize — A three-phase pipeline maps those entities to the ESCO "
            "European skills taxonomy, resolving synonyms and aligning to a hybrid "
            "SKOS vocabulary (SKOS Core + ESCO + schema.org + a custom resume namespace). "
            "SHACL constraints validate every triple before it enters the graph. "
            "(3) Visualize — The result is an interactive graph (Vis.js) you can "
            "explore in the browser, query with SPARQL, or export as Turtle/RDF/JSON-LD. "
            "It also generates two narrative career stories from the graph structure — "
            "one conservative (what the evidence clearly supports) and one exploratory "
            "(what the patterns suggest). "
            "Stack: Python, Flask, React 18, rdflib, NetworkX, Vis.js."
        ),
        "diagram_filename": "resume_graph_explorer_diagram.png",
        "diagram_caption": "Resume Graph Explorer — extraction → normalization → interactive graph",
        "tags": ["knowledge-graph", "ontology", "skos", "resume", "rdf", "nlp", "semantic-web"],
        "mention_keywords": ["resume explorer", "resume graph", "skos", "esco"],
        "links": {
            "live demo": "https://resume-graph-explorer.vercel.app/",
            "github": "https://github.com/dagny099/resume-graph-explorer",
        },
    },

    # ── Digital Twin ─────────────────────────────────────────────
    {
        "id": "digital-twin",
        "title": "Digital Twin",
        "summary": (
            "A RAG-powered chatbot that represents Barbara conversationally, grounded "
            "in her actual writing and work history. The twin itself is a portfolio piece "
            "— not just a wrapper around an LLM — demonstrating how knowledge base design "
            "directly shapes retrieval quality."
        ),
        "design_insight": (
            "The key insight: retrieval quality depends more on how you write your "
            "knowledge base documents than on the embedding model. Three documents were "
            "written specifically to improve retrieval — a philosophy doc, a positioning "
            "doc, and a career narrative — each designed for how chunks will be retrieved, "
            "not just how they read as prose."
        ),
        "walkthrough_context": (
            "Digital Twin is the chatbot you may be talking to right now. "
            "It's a retrieval-augmented generation (RAG) system grounded in Barbara's "
            "actual writing and work history. "
            "(1) Knowledge Base — Multiple document types (biosketch, project briefs, "
            "website pages, resume, publications) are chunked with section-aware "
            "splitting and embedded using OpenAI's text-embedding-3-small into ChromaDB. "
            "The KB was designed for retrieval quality, not just storage: source priority "
            "ordering, synthetic overview chunks, and a multi-document architecture ensure "
            "the right context surfaces for different question types. "
            "(2) Retrieval — When you ask a question, the system embeds your query, "
            "retrieves the most relevant chunks, and injects them as context. "
            "(3) Generation — A carefully designed system prompt controls voice, "
            "framing, and source priority so the chatbot sounds like Barbara, not a "
            "generic assistant. The prompt encodes narrative priorities ('stories before "
            "specs', 'problems before skills') and explicit failure modes observed "
            "during testing. "
            "Stack: Python, Gradio, ChromaDB, OpenAI API, AWS EC2."
        ),
        "diagram_filename": "architecture-overview_barb_twin.png",
        "diagram_caption": "Digital Twin — document ingestion → embedding → retrieval → response",
        "tags": ["rag", "chatbot", "embeddings", "chromadb", "gradio", "nlp"],
        "mention_keywords": ["digital twin", "this chatbot", "this twin", "how were you built",
                             "how was this built", "how does this work", "digital twin chatbot", "your chatbot", "this bot"],
        "links": {
            "live demo": "https://twin.barbhs.com",
            "github": "https://github.com/dagny099/barbs-digital-twin",
        },
    },

    # ── Weaving Memories into Graphs ─────────────────────────────
    {
        "id": "weaving-memories",
        "title": "Weaving Memories Into Graphs",
        "summary": (
            "A memorial knowledge graph preserving the professional legacy of Barbara's "
            "late father, Domingo Hidalgo Lopez — a software developer and naval architect "
            "whose systems still run in semiconductor fabs worldwide. It proves you can "
            "apply rigorous knowledge engineering to something deeply personal."
        ),
        "design_insight": (
            "This project bridges rigorous knowledge engineering methodology with deeply "
            "personal subject matter. Every fact has provenance tracking (source + confidence), "
            "and a semi-automated Wikidata enrichment pipeline adds external context — "
            "showing that KG best practices aren't just for enterprise data."
        ),
        "walkthrough_context": (
            "Weaving Memories Into Graphs is a memorial project for Barbara's late "
            "father, Domingo Hidalgo Lopez — a software developer and naval architect "
            "whose systems still run in semiconductor fabs worldwide. "
            "The system works like this: "
            "(1) Schema Design — A 14-entity Neo4j schema (Person, Organization, "
            "Position, Education, Location, Project, Technology, Skill, Patent, Product, "
            "Event, Artifact, Publication, Industry) with temporal relationship patterns. "
            "(2) Extraction — Claude extracts structured YAML from biographical text, "
            "validated against Pydantic dataclasses. "
            "(3) Enrichment — A semi-automated tool queries Wikidata for external "
            "context, with provenance tracking so every fact has a source. "
            "(4) Frontend — A React + Vite app with timeline, legacy, and network "
            "views served by a Flask REST API. "
            "Stack: Python, Neo4j Aura, Claude, Flask, React + Vite, Wikidata API."
        ),
        "diagram_filename": "weaving_memories_diagram.png",
        "diagram_caption": "Weaving Memories — biographical text → LLM extraction → Neo4j graph → interactive views",
        "tags": ["knowledge-graph", "neo4j", "memorial", "family", "wikidata", "llm-extraction"],
        "mention_keywords": ["weaving memories", "memorial", "father", "domingo", "family graph"],
        "links": {
            "live demo": "https://domingo-hidalgo.com",
            "github": "https://github.com/dagny099/weaving-memories-into-graphs",
        },
    },

    # ── Academic Citation Platform ────────────────────────────────
    {
        "id": "academic-citation-platform",
        "title": "Academic Citation Platform",
        "summary": (
            "ML-powered research discovery using TransE knowledge graph embeddings "
            "trained on 12K+ academic papers. Predicts which papers are likely to cite "
            "each other by learning citation relationships as vector translations in "
            "embedding space."
        ),
        "design_insight": (
            "The TransE model was implemented from scratch rather than using a library — "
            "a deliberate choice to understand the embedding geometry deeply. A 4-notebook "
            "research pipeline tells the complete data science story from exploration to "
            "presentation, mirroring how Barbara approaches analytical projects."
        ),
        "walkthrough_context": (
            "Academic Citation Platform predicts which papers are likely to cite "
            "each other using knowledge graph embeddings. "
            "The pipeline works in four stages: "
            "(1) Import — Papers are ingested from the Semantic Scholar API with "
            "streaming batch processing (25x faster), quality filtering by citation "
            "count and year range, and file upload for custom collections. "
            "(2) Train — A TransE model (implemented from scratch) learns citation "
            "relationships as vector translations in embedding space, with early "
            "stopping and training visualizations. "
            "(3) Predict — The trained model generates 1000+ novel citation "
            "predictions with confidence scores, evaluated via MRR, Hits@K, and AUC. "
            "(4) Explore — An interactive Streamlit dashboard with clickable network "
            "graphs, community detection (multiple algorithms), temporal trend "
            "analysis, and export to LaTeX tables and high-res graphics. "
            "A 4-notebook research pipeline tells the complete data science story "
            "from exploration to presentation. "
            "Stack: Python, Neo4j, Streamlit, TransE, Semantic Scholar API, NetworkX."
        ),
        "diagram_filename": "academic_citation_platform_diagram.png",
        "diagram_caption": "Academic Citation Platform — papers → TransE training → citation prediction → interactive analysis",
        "tags": ["knowledge-graph", "neo4j", "machine-learning", "TransE", "citation-prediction", "streamlit"],
        "mention_keywords": ["citation", "transe", "academic", "papers", "citation platform", "citation compass", "paper prediction"],
        "links": {
            "github": "https://github.com/dagny099/academic-citation-platform",
        },
    },

    # ── Poolula Platform ─────────────────────────────────────────
    {
        "id": "poolula-platform",
        "title": "Poolula Platform",
        "summary": (
            "An AI-powered LLC management platform combining structured data, document "
            "management, and a RAG chatbot with a built-in evaluation harness. Designed "
            "as a personal 'LLC Operating System' — a turnkey, always-ready structure for "
            "small property-holding businesses."
        ),
        "design_insight": (
            "What makes this project distinctive is the evaluation harness: two specialized "
            "evaluators (general business + Airbnb income with CSV ground truth) score tool "
            "choice, content relevance, and numerical accuracy with a 90%+ target. It's a "
            "demonstration that RAG systems need built-in quality measurement, not just "
            "retrieval."
        ),
        "walkthrough_context": (
            "Poolula Platform is a unified management system for a property-holding "
            "LLC, combining structured data, document management, and an AI chatbot. "
            "The system has four layers: "
            "(1) Structured Data — A SQLModel schema with 5 core tables (Properties, "
            "Transactions, Documents, Obligations, Audit Log) backed by SQLite, "
            "with full provenance tracking and Alembic migrations. "
            "(2) Document Management — PDFs are uploaded, normalized, classified by "
            "type (Agreement, Filing, Insurance, Lease), and indexed in ChromaDB "
            "for semantic search with SHA-256 duplicate detection. "
            "(3) RAG Chatbot — A provider-agnostic chatbot (Claude, OpenAI, Ollama) "
            "with three tool functions: query_database (SELECT-only SQL against "
            "structured data), search_document_content (semantic search via ChromaDB), "
            "and list_business_documents. Includes conversation history, session "
            "management, and audit logging. "
            "(4) Evaluation Harness — Two specialized evaluators (5 general business "
            "questions + 15 Airbnb income questions with CSV ground truth) score "
            "tool choice (40%), content relevance (40%), numerical accuracy (50% for "
            "income questions), and completeness with a 90%+ target. Supports "
            "multi-provider comparison (Anthropic vs OpenAI vs Ollama). "
            "Stack: Python, FastAPI, SQLModel, ChromaDB, Anthropic/OpenAI/Ollama, "
            "Alembic, DSPy."
        ),
        "diagram_filename": "poolula-platform-diagarm.png",
        "diagram_caption": "Poolula Platform — business question → RAG retrieval → LLM answer → evaluation harness verification",
        "tags": ["rag", "fastapi", "llc-management", "evaluation", "chromadb", "multi-provider", "sqlmodel"],
        "mention_keywords": ["poolula", "llc", "property management", "evaluation harness"],
        "links": {
            "github": "https://github.com/dagny099/poolula-platform",
        },
    },

    # ── Beehive Monitor ──────────────────────────────────────────
    {
        "id": "beehive-monitor",
        "title": "Beehive Monitor",
        "summary": (
            "Computer vision + weather correlation for backyard beekeeping, built from "
            "4+ years of Barbara's own hive inspection data. Turns unstructured inspection "
            "photos into a structured, searchable knowledge base — a real AI project for a "
            "problem she genuinely lives with, not a benchmark dataset."
        ),
        "design_insight": (
            "This is a good example of building tools for problems you actually have. "
            "The project combines image analysis, automated metadata extraction, color "
            "palette analysis for honeycomb health indicators, and historical weather "
            "correlation — all on a personal dataset she's been collecting for years. "
            "It's domain-specific AI applied to a domain she knows firsthand."
        ),
        "walkthrough_context": (
            "Beehive Monitor is a data collection and analysis tool for Barbara's "
            "backyard beekeeping practice, built on 4+ years of self-tracked hive data. "
            "The pipeline works in four stages: "
            "(1) Capture — A calendar-based session scheduler lets you log hive "
            "inspections with multi-photo uploads through a Streamlit multi-page app, "
            "each session date-stamped for longitudinal tracking. "
            "(2) Analyze — Google Cloud Vision API performs image label detection "
            "and object/activity recognition on hive photos. A multi-library EXIF "
            "extraction pipeline (with fallback mechanisms for diverse camera formats) "
            "pulls metadata automatically. A color palette analysis pipeline extracts "
            "and clusters bee-domain-specific colors for honeycomb health indicators. "
            "Open-Meteo pulls temperature, humidity, and wind data for the session date "
            "via a GPS validation pipeline that verifies coordinates before the weather "
            "API call. "
            "(3) Dashboard — A Streamlit interface with Plotly visualizations displays "
            "session history, vision analysis results, weather overlays, and an "
            "annotation system for beekeeper observations and hive state tracking. "
            "(4) Export + Deploy — Data exports to JSON/CSV for offline analysis. "
            "The app is containerized with Docker and deployed to Google Cloud Run, "
            "with a pluggable storage abstraction layer (local → S3 → GCS ready). "
            "Stack: Python, Streamlit, Google Cloud Vision, Open-Meteo API, "
            "Plotly, Docker, Cloud Run."
        ),
        "diagram_filename": "beehive_metadata_tracker_diagram.png",
        "diagram_caption": "Beehive Monitor — photo capture → Cloud Vision + weather analysis → dashboard → containerized deployment",
        "tags": ["computer-vision", "streamlit", "google-cloud", "beekeeping", "docker", "weather-api"],
        "mention_keywords": ["beehive", "bees", "beekeeping", "hive", "apiary", "beehive tracker", "bee tracker", "bee monitor"],
        "links": {
            "live demo": "https://beestory.barbhs.com/",
            "github": "https://github.com/dagny099/beehive-tracker",
        },
        "blog_posts": [
            {
                "title": "Hive Photo Metadata Tracker — Data Story",
                "url": "https://www.barbhs.com/data-stories/hive-photo-metadata-tracker/",
            },
        ],
    },

    # ── ConvoScope ───────────────────────────────────────────────
    {
        "id": "convoscope",
        "title": "ConvoScope",
        "summary": (
            "A conversation intelligence platform for exploring how different AI models "
            "think about the same questions. Parses conversation structure at the turn "
            "level and runs analysis across multiple LLM providers to compare "
            "interpretation patterns."
        ),
        "design_insight": (
            "Born from genuine curiosity about how context shifts across AI providers. "
            "The same question yields different insights depending on the model — "
            "ConvoScope makes those differences visible and comparable rather than "
            "anecdotal."
        ),
        "walkthrough_context": (
            "ConvoScope is a conversation intelligence platform for exploring how "
            "different AI models think about the same questions. "
            "The pipeline works in four stages: "
            "(1) Input — Paste or upload conversation text through a Streamlit "
            "interface with interactive configuration for provider selection "
            "and prompt customization. "
            "(2) Analyze — A core services engine parses conversation structure "
            "at the turn level, extracting themes, topics, and interaction "
            "patterns from the dialogue. "
            "(3) LLM Comparison — The analysis runs across multiple model "
            "providers (OpenAI active, Anthropic and Llama planned) to compare "
            "how different models interpret the same conversation. "
            "(4) Report — Rich HTML reports with side-by-side model comparisons "
            "are generated and downloadable for offline review. "
            "Stack: Python, Streamlit, OpenAI API, Anthropic (planned), HTML reports."
        ),
        "diagram_filename": "convoscope_chatbot_diagram.png",
        "diagram_caption": "ConvoScope — conversation input → analysis engine → multi-LLM comparison → HTML reports",
        "tags": ["multi-llm", "streamlit", "conversation-analysis", "openai", "anthropic", "nlp"],
        "mention_keywords": ["convoscope", "conversation analysis", "multi-llm comparison"],
        "links": {
            "github": "https://github.com/dagny099/convoscope",
        },
    },

    # ── Fitness Tracker ──────────────────────────────────────────
    {
        "id": "fitness-tracker",
        "title": "Fitness Tracker",
        "summary": (
            "A personal analytics dashboard built on 14+ years and 2,800+ sessions of "
            "self-tracked workout data. Reveals behavioral patterns like the 4.5x "
            "consistency increase that coincided with adopting a rescue dog — the kind "
            "of insight that only emerges from long-horizon personal datasets."
        ),
        "design_insight": (
            "This project demonstrates what happens when you apply data science "
            "methods to your own life over a long enough time horizon. Fourteen years "
            "of data makes patterns visible that shorter datasets can't reveal — "
            "seasonal shifts, life-event correlations, and the compounding effects of "
            "consistency."
        ),
        "walkthrough_context": (
            "Fitness Tracker is a personal analytics platform built on 14+ years "
            "and 2,800+ sessions of self-tracked workout data. "
            "The pipeline works in four stages: "
            "(1) Data Ingestion — Raw workout logs and metrics are cleaned, "
            "normalized, and enriched from historical fitness data spanning "
            "over a decade of gym sessions, runs, and activities. "
            "(2) AI + Analytics — Pattern detection algorithms and trend analysis "
            "reveal behavioral insights: volume progression, frequency shifts, "
            "seasonal patterns, and the dramatic 4.5x consistency increase that "
            "coincided with adopting a rescue dog in June 2018. "
            "(3) Dashboard — An interactive Streamlit UI with Plotly charts "
            "including time series, distributions, heatmaps, and filterable "
            "views by date range and muscle group. "
            "(4) Live Deployment — Publicly accessible at workouts.barbhs.com "
            "as a custom-domain Streamlit deployment. "
            "Stack: Python, Streamlit, Pandas, Plotly, NumPy."
        ),
        "diagram_filename": "fitness_tracker_diagram.png",
        "diagram_caption": "Fitness Tracker — 14+ years of data → AI pattern detection → interactive Plotly dashboard → live at workouts.barbhs.com",
        "tags": ["data-engineering", "streamlit", "plotly", "fitness", "analytics", "personal-data"],
        "mention_keywords": ["fitness", "workout", "exercise", "running data", "fitness dashboard", "workout dashboard", "workout tracker"],
        "links": {
            "live demo": "https://workouts.barbhs.com/",
            "github": "https://github.com/dagny099/fitness-dashboard",
        },
        "blog_posts": [
            {
                "title": "Exercise Dashboard — Data Story",
                "url": "https://www.barbhs.com/data-stories/exercise-dashboard/",
            },
        ],
    },

    # ── Concept Cartographer ─────────────────────────────────────
    {
        "id": "concept-cartographer",
        "title": "Concept Cartographer",
        "summary": (
            "A Gradio app that makes implicit knowledge structure explicit: as you chat, "
            "it extracts concepts and relationships from each turn and builds a persistent, "
            "growing knowledge graph you can explore and export. A compact demonstration "
            "of stateful LLM tooling that externalizes reasoning structure rather than "
            "just generating text."
        ),
        "design_insight": (
            "The architectural decision worth noting is the single-call design — one "
            "LLM call per turn returns both a conversational response and structured "
            "JSON simultaneously, rather than a separate extraction step. This is ~50% "
            "faster and cheaper than a two-call approach. Above 30 nodes, a connectivity "
            "filter keeps the graph coherent by only admitting concepts that connect to "
            "existing ones."
        ),
        "walkthrough_context": (
            "Concept Cartographer is a Gradio app that turns a conversation into a "
            "growing knowledge graph. As you chat, it extracts concepts and relationships "
            "and renders them as a color-coded, persistent map you can export. "
            "The key architectural decision is the single-call design: "
            "(1) Ask — Pick a domain lens (AI/ML, Cognitive Science, Philosophy, Biology, "
            "or more) and ask a question through the Gradio interface. Domain selection "
            "nudges extraction toward domain-relevant concepts and relation types. "
            "(2) Extract — A single LLM call (GPT-4o-mini) returns both a conversational "
            "narrative and a structured JSON ontology (concepts with categories like "
            "Entity, Process, Theory, Method, Property, plus relationship triples with "
            "typed edges like causes, requires, enables). This is ~50% faster and cheaper "
            "than a two-call approach that separates chat from extraction. "
            "(3) Build — The graph accumulates across conversation turns with a color-coded "
            "legend by concept category. Above 30 nodes, a connectivity filter ensures only "
            "concepts that connect to existing nodes are admitted — preventing disconnected "
            "islands and keeping the map coherent. A 'Latest Connections' panel below the "
            "chat shows a plain-language summary of what was just extracted. "
            "(4) Export — The current graph state exports as JSON (for downstream tools "
            "like Neo4j, Obsidian, or presentations) or PNG (for sharing). "
            "Stack: Python, Gradio, OpenAI API (GPT-4o-mini), NetworkX, Matplotlib."
        ),
        "diagram_filename": "architecture-diagram_concept_cartography.png",
        "diagram_caption": "Concept Cartographer — question → single LLM call → growing knowledge graph → export",
        "tags": ["knowledge-graph", "gradio", "llm", "ontology", "concept-extraction", "structured-output", "nlp"],
        "mention_keywords": [
            "concept cartographer", "concept cartography",
            "concept map", "concept graph",
            "concept extraction", "knowledge mapping"
        ],
        "links": {
            "live demo": "https://concept-cartographer.com/",
            "github": "https://github.com/dagny099/concept-cartography-gradio",
        },
    },

    # ── ChronoScope ──────────────────────────────────────────────
    {
        "id": "chronoscope",
        "title": "ChronoScope",
        "summary": (
            "Transforms documents into interactive timelines using AI event extraction. "
            "The same career data that Resume Explorer models as a knowledge graph, "
            "ChronoScope unfolds along a temporal axis — showing Barbara can approach "
            "the same domain from fundamentally different structural perspectives."
        ),
        "design_insight": (
            "ChronoScope treats time as the primary organizing principle. Where Resume "
            "Explorer asks 'how do these skills and roles relate?', ChronoScope asks "
            "'when did these things happen and what patterns emerge over time?' Together "
            "they demonstrate that the same source material yields different insights "
            "depending on which structural lens you apply — a core cognitive science idea."
        ),
        "walkthrough_context": (
            "ChronoScope automatically extracts life events from resumes, cover letters, "
            "and personal documents to create rich, interactive timelines. "
            "The pipeline works in five stages: "
            "(1) Upload — Drop in a resume (95%+ extraction accuracy) or try cover "
            "letters and personal statements (70-80% accuracy, experimental). PDF "
            "extraction uses a dual-library fallback (PyMuPDF + pdfplumber). "
            "(2) Extract — OpenAI GPT identifies events, dates, locations, and people "
            "from the document text. A date parsing pipeline handles vague dates "
            "('Fall 2010' → '2010-08-15') using dateutil. Multi-document processing "
            "includes hash-based deduplication. "
            "(3) Validate — A quality validation system checks for missing data, "
            "assigns confidence scores, and supports gold standard comparison. An "
            "editable data table lets users verify, rate, tag, and annotate events. "
            "(4) Visualize — An interactive Plotly-based Gantt chart with zoom, pan, "
            "filter, and tooltips displays the timeline. A beta knowledge graph view "
            "(NetworkX, optional Neo4j) shows entity relationships. "
            "(5) Export — TimelineJS export with 6 color schemes and 10 font "
            "combinations produces professional web timelines. Also exports to "
            "Excel/JSON for downstream use. "
            "Architecture: monolithic Streamlit (Python-only, rapid iteration) — "
            "a deliberate contrast to Resume Explorer's decoupled Flask/React stack. "
            "Stack: Python, Streamlit, OpenAI GPT, Plotly, PyMuPDF, pdfplumber, "
            "TimelineJS, NetworkX, MkDocs."
        ),
        "diagram_filename": "chronoscope_diagram.png",
        "diagram_caption": "ChronoScope — document upload → AI event extraction → validation → interactive timeline → export",
        "tags": ["timeline", "streamlit", "openai", "nlp", "document-processing", "plotly", "visualization"],
        "mention_keywords": [
            "chronoscope", "chrono scope", "timeline",
            "timeline extraction", "event extraction",
            "document timeline", "career timeline"
        ],
        "links": {
            "live demo": "https://chronoscope.barbhs.app",
            "github": "https://github.com/dagny099/chronoscope",
            "docs": "https://docs.barbhs.com/chronoscope",
        },
        "blog_posts": [
            {
                "title": "Comparing architectures: ChronoScope vs Resume Graph Explorer",
                "url": "https://www.barbhs.com/blog/comparing-architectures-chronoscope-resume-explorer/",
            },
        ],
    },
]


# ═══════════════════════════════════════════════════════════════════
# HELPERS — WALKTHROUGH DETECTION (narrow, intent-based)
# ═══════════════════════════════════════════════════════════════════

def load_featured_projects() -> list[dict]:
    """Return the list of featured projects."""
    return FEATURED_PROJECTS


# ── Names used in regex patterns ────────────────────────────────
# Keep this in sync with FEATURED_PROJECTS titles/aliases.
# Lowercase, no regex special chars. Used for intent detection only.
_PROJECT_NAMES = (
    "cartograph|explorer|digital\\s*twin|beehive|fitness|"
    "citation|poolula|convoscope|memories|weaving|chronoscope"
)

def _is_walkthrough_request(message: str) -> bool:
    """
    Return True if the user message is asking for a project walkthrough.
 
    Two detection strategies:
      1. VERB-BASED — "walk me through", "show me", "describe" + project/generic
      2. NAME-BASED — "tell me about [project name]", "how does [project name] work"
 
    Kept deliberately broad: false positives are cheap (we just inject
    extra context + show a diagram), false negatives mean the visitor
    gets a worse answer.
    """
    patterns = [
        # ── Verb-based: walkthrough intent verbs ─────────────────
        # "walk me through X" — matches regardless of what X is
        r"walk\s*(me\s+)?through",
        # "show me a project"
        r"show\s+me\s+a\s+project",
        # "portfolio project", "featured project"
        r"(portfolio|featured)\s+project",
        # "project you're proud of / built / worked on"
        r"project\s+you.*(proud|excited|built|worked)",
        r"(proud|excited)\s+.*(project|built)",
 
        # ── Name-based: project name in an explanatory request ───
        # "tell me about [project]" / "talk about [project]"
        rf"(tell|talk)\s+(me\s+)?about\s+.*({_PROJECT_NAMES}|project)",
        # "explain [project]" / "describe [project]"
        rf"(explain|describe)\s+.*?({_PROJECT_NAMES}|project)",
        # "how does [project] work/handle/do"
        rf"how\s+(does|did|do|is)\s+.*({_PROJECT_NAMES})",
    ]
    lower = message.lower()
    return any(re.search(p, lower) for p in patterns)


# ═══════════════════════════════════════════════════════════════════
# HELPERS — PROJECT MENTION DETECTION (broad, keyword-based)
# ═══════════════════════════════════════════════════════════════════

def _score_project_mention(message: str, project: dict) -> int:
    """
    Score how strongly a message mentions a specific project.

    Checks (in priority order):
      1. Explicit mention_keywords (phrase match, high signal)
      2. Title substring match
      3. Tag overlap with message words
    
    Returns an integer score. 0 = no mention detected.
    """
    lower = message.lower()
    score = 0

    # Phrase-level keyword matches (highest signal)
    for kw in project.get("mention_keywords", []):
        if kw.lower() in lower:
            score += 10

    # Title match
    title_lower = project["title"].lower()
    if title_lower in lower:
        score += 8
    else:
        # Partial title words (less confident)
        title_words = set(re.findall(r'\w{4,}', title_lower))  # 4+ char words only
        msg_words = set(re.findall(r'\w+', lower))
        overlap = title_words & msg_words
        score += len(overlap) * 2

    # Tag overlap
    tags = set(project.get("tags", []))
    msg_words = set(re.findall(r'\w+', lower))
    score += len(tags & msg_words)

    return score


def find_mentioned_project(message: str) -> dict | None:
    """
    Find the project most strongly referenced by the message.
    
    Unlike select_project_for_walkthrough(), this does NOT require
    walkthrough intent — it fires on any project mention. Used for
    diagram serving.
    
    Returns None if no project scores above the minimum threshold.
    """
    min_threshold = 5  # Avoids false positives on vague messages
    
    best, best_score = None, 0
    for project in FEATURED_PROJECTS:
        score = _score_project_mention(message, project)
        if score > best_score:
            best, best_score = project, score

    if best_score >= min_threshold:
        return best
    return None


# ═══════════════════════════════════════════════════════════════════
# HELPERS — WALKTHROUGH SELECTION (narrow intent + keyword match)
# ═══════════════════════════════════════════════════════════════════

def select_project_for_walkthrough(user_message: str) -> dict | None:
    """
    Select a featured project for a full walkthrough response.

    Returns None if the message doesn't look like a walkthrough request.
    When it is a walkthrough request, tries keyword matching against
    title/summary/tags, falling back to the first project.
    """
    if not _is_walkthrough_request(user_message):
        return None

    projects = load_featured_projects()
    if not projects:
        return None

    # Try mention-based matching first (more precise)
    mentioned = find_mentioned_project(user_message)
    if mentioned:
        return mentioned

    # Fallback: word overlap scoring (original logic)
    words = set(re.findall(r'\w+', user_message.lower()))
    best, best_score = projects[0], 0
    for project in projects:
        searchable = " ".join([
            project["title"].lower(),
            project["summary"].lower(),
            " ".join(project.get("tags", [])),
        ])
        score = len(words & set(re.findall(r'\w+', searchable)))
        if score > best_score:
            best, best_score = project, score

    return best


# ═══════════════════════════════════════════════════════════════════
# HELPERS — DIAGRAM SERVING (decoupled from walkthrough)
# ═══════════════════════════════════════════════════════════════════

def get_diagram_path(project: dict) -> str | None:
    """
    Return the absolute path to the project's diagram if it exists on disk.
    Returns None if the file is missing, so callers can gracefully omit the image.
    """
    filename = project.get("diagram_filename")
    if not filename:
        return None
    diagram_path = os.path.join(_DIAGRAM_DIR, filename)
    if os.path.isfile(diagram_path):
        return diagram_path
    return None


# ═══════════════════════════════════════════════════════════════════
# HELPERS — CONTEXT ENRICHMENT
# ═══════════════════════════════════════════════════════════════════

def build_walkthrough_context_block(project: dict) -> str:
    """
    Build a context block for walkthrough injection.

    This is injected as a SEPARATE context section (not appended to
    the user message), so RAG retrieval stays grounded in the user's
    actual question while the LLM still has the full walkthrough notes.

    Structure:
      - Title + summary (what it is)
      - Design insight (why it's distinctive — gives the LLM a narrative lead)
      - Walkthrough notes (how it works)
      - Project links (operational: demo, github, docs)
      - Related writing (blog posts / writeups — deeper context)
    """
    parts = [
        f"[WALKTHROUGH PROJECT: {project['title']}]",
        f"Summary: {project['summary']}",
    ]

    # Design insight gives the LLM "stories before specs" material
    if project.get("design_insight"):
        parts.append(f"What makes it distinctive: {project['design_insight']}")

    parts.append(f"Walkthrough notes: {project['walkthrough_context']}")

    # Operational links (demo, github, docs)
    links = {k: v for k, v in project.get("links", {}).items() if v}
    if links:
        lines = "\n".join(f"  - {label}: {url}" for label, url in links.items())
        parts.append(
            f"Project links (use these exact URLs only, do not modify or invent others):\n{lines}"
        )

    # Blog posts / writeups (separate from operational links)
    blog_posts = project.get("blog_posts", [])
    if blog_posts:
        lines = "\n".join(
            f'  - "{post["title"]}": {post["url"]}' for post in blog_posts
        )
        parts.append(
            f"Related writing (link when visitors want the story behind the project):\n{lines}"
        )

    return "\n".join(parts)


def enrich_message_for_walkthrough(message: str, project: dict) -> str:
    """
    DEPRECATED — kept for backward compatibility.
    Prefer build_walkthrough_context_block() + separate injection.

    Append project context to the user message so the LLM can generate
    a natural walkthrough grounded in the project's details.
    """
    links = {k: v for k, v in project.get("links", {}).items() if v}
    if links:
        lines = "\n".join(f"  - {label}: {url}" for label, url in links.items())
        links_block = f"\nProject links (use these exact URLs only, do not modify or invent others):\n{lines}"
    else:
        links_block = ""
    return (
        f"{message}\n\n"
        f"[Selected project for walkthrough: {project['title']}]\n"
        f"Summary: {project['summary']}\n"
        f"Walkthrough notes: {project['walkthrough_context']}"
        f"{links_block}"
    )
