"""
featured_projects.py
====================
Lightweight data + selection logic for project walkthrough responses.

Each featured project includes a title, summary, walkthrough context
(briefing notes for the LLM), diagram path, and optional tags for
keyword matching.

To add a new project:
    1. Add a diagram image to assets/project_diagrams/
    2. Append a new dict to FEATURED_PROJECTS below
    3. That's it — the selection logic picks it up automatically
"""

import os
import re

# ═══════════════════════════════════════════════════════════════════
# PROJECT DATA
# ═══════════════════════════════════════════════════════════════════

_DIAGRAM_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "assets", "project_diagrams")

FEATURED_PROJECTS = [

    # Resume Graph Explorer
    {
        "id": "resume-graph-explorer",
        "title": "Resume Graph Explorer",
        "summary": "Transforms resumes into interactive SKOS-compliant knowledge graphs.",
        "walkthrough_context": (
            "Resume Graph Explorer turns a flat resume into a living knowledge graph. "
            "The pipeline works in three stages: "
            "(1) Extract — An LLM (Claude, OpenAI, or Ollama) reads the resume and "
            "pulls out structured entities: skills, roles, organizations, industries. "
            "(2) Normalize — A three-phase pipeline maps those entities to the ESCO "
            "European skills taxonomy, resolving synonyms and aligning to a hybrid "
            "SKOS vocabulary (SKOS Core + ESCO + schema.org + a custom resume namespace). "
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
        "links": {
            "live demo": "https://resume-graph-explorer.vercel.app/",
            "github": "https://github.com/dagny099/resume-graph-explorer", 
            # "writeup": "https://...",  # add blog post / article URL when available
        },
    },

    # Digital Twion
    {
        "id": "digital-twin",
        "title": "Digital Twin",
        "summary": "A RAG-powered chatbot that represents Barbara conversationally.",
        "walkthrough_context": (
            "Digital Twin is the chatbot you may be talking to right now. "
            "It's a retrieval-augmented generation (RAG) system grounded in Barbara's "
            "actual writing and work history. "
            "(1) Knowledge Base — Multiple document types (biosketch, project briefs, "
            "website pages, resume, publications) are chunked and embedded using "
            "OpenAI's text-embedding-3-small into ChromaDB. "
            "(2) Retrieval — When you ask a question, the system embeds your query, "
            "retrieves the most relevant chunks, and injects them as context. "
            "(3) Generation — A carefully designed system prompt controls voice, "
            "framing, and source priority so the chatbot sounds like Barbara, not a "
            "generic assistant. "
            "The key insight: retrieval quality depends more on how you write your "
            "knowledge base documents than on the embedding model. Three documents were "
            "written specifically to improve retrieval — a philosophy doc, a positioning "
            "doc, and a career narrative. "
            "Stack: Python, Gradio, ChromaDB, OpenAI API, HuggingFace Spaces."
        ),
        "diagram_filename": "digital_twin_diagram.png",
        "diagram_caption": "Digital Twin — document ingestion → embedding → retrieval → response",
        "tags": ["rag", "chatbot", "embeddings", "chromadb", "gradio", "nlp"],
        "links": {
            "live demo": "https://twin.barbhs.com",
            "github": "https://github.com/dagny099/barbs-digital-twin", 
            # "writeup": "https://...",  # add blog post / article URL when available
        },
    },

    # Weaving Memories into Graphs
    {
        "id": "weaving-memories",
        "title": "Weaving Memories Into Graphs",
        "summary": "A memorial knowledge graph preserving a family legacy in Neo4j.",
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
            "It proves you can apply rigorous knowledge engineering methodology to "
            "something deeply personal. "
            "Stack: Python, Neo4j Aura, Claude, Flask, React + Vite, Wikidata API."
        ),
        "diagram_filename": "weaving_memories_diagram.png",
        "diagram_caption": "Weaving Memories — biographical text → LLM extraction → Neo4j graph → interactive views",
        "tags": ["knowledge-graph", "neo4j", "memorial", "family", "wikidata", "llm-extraction"],
        "links": {
            "live demo": "https://domingo-hidalgo.com",
            "github": "https://github.com/dagny099/weaving-memories-into-graphs", 
            # "writeup": "https://...",  # add blog post / article URL when available
        },
    },

    # Academic Citation Platform
    {
        "title": "Academic Citation Platform",
        "summary": "ML-powered research discovery using TransE embeddings on 12K+ academic papers.",
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
        "diagram_filename": "citation-chatbot-v2.png",
        "diagram_caption": "Academic Citation Platform — papers → TransE training → citation prediction → interactive analysis",
        "tags": ["knowledge-graph", "neo4j", "machine-learning", "TransE", "citation-prediction", "streamlit"],
        #"links": {
            # "live demo": "",
            # "github": "https://github.com/dagny099/", 
            # "writeup": "https://...",  # add blog post / article URL when available
        #},
    },

    # Poolula Platform
    {
        "title": "Poolula Platform",
        "summary": "AI-powered LLC management platform with RAG chatbot, structured data, and evaluation harness.",
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
            "tool choice, content relevance, numerical accuracy, and completeness "
            "with a 90%+ target. Supports multi-provider comparison. "
            "Stack: Python, FastAPI, SQLModel, ChromaDB, Anthropic/OpenAI/Ollama, "
            "Alembic, DSPy."
        ),
        "diagram_filename": "poolula-chatbot-v2.png",
        "diagram_caption": "Poolula Platform — business question → RAG retrieval → LLM answer → evaluation harness verification",
        "tags": ["rag", "fastapi", "llc-management", "evaluation", "chromadb", "multi-provider", "sqlmodel"],
        #"links": {
            # "live demo": "",
            # "github": "https://github.com/dagny099/", 
            # "writeup": "https://...",  # add blog post / article URL when available
        #},
    },
    
    # Beehive Monitor
    {
        "title": "Beehive Monitor",
        "summary": "Computer vision + weather correlation for backyard beekeeping sessions.",
        "walkthrough_context": (
            "Beehive Monitor is a data collection and analysis tool for Barbara's "
            "backyard beekeeping practice. "
            "The pipeline works in four stages: "
            "(1) Capture — A calendar-based session scheduler lets you log hive "
            "inspections with multi-photo uploads through a Streamlit UI, each "
            "session date-stamped for longitudinal tracking. "
            "(2) Analyze — Google Cloud Vision API performs image label detection "
            "and object/activity recognition on hive photos, while Open-Meteo "
            "pulls temperature, humidity, and wind data for the session date "
            "to correlate weather conditions with hive behavior. "
            "(3) Dashboard — A Streamlit interface displays session history, "
            "vision analysis results, and weather overlays for pattern spotting "
            "across inspections. "
            "(4) Export + Deploy — Data exports to JSON/CSV for offline analysis. "
            "The app is containerized with Docker and deployed to Google Cloud Run. "
            "Stack: Python, Streamlit, Google Cloud Vision, Open-Meteo API, "
            "Docker, Cloud Run."
        ),
        "diagram_filename": "bees-chatbot-v2.png",
        "diagram_caption": "Beehive Monitor — photo capture → Cloud Vision + weather analysis → dashboard → containerized deployment",
        "tags": ["computer-vision", "streamlit", "google-cloud", "beekeeping", "docker", "weather-api"],
        "links": {
            "live demo": "https://beestory.barbhs.com/",
            "github": "https://github.com/dagny099/beehive-tracker", 
            "writeup": "https://www.barbhs.com/data-stories/hive-photo-metadata-tracker/",  
        },
    },

    # ConvoScope
    {
        "title": "ConvoScope",
        "summary": "Multi-LLM conversation analysis and comparison platform.",
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
            "Born from curiosity about how context shifts across AI providers "
            "and how the same question yields different insights depending on "
            "the model. "
            "Stack: Python, Streamlit, OpenAI API, Anthropic (planned), HTML reports."
        ),
        "diagram_filename": "convo-chatbot-v2.png",
        "diagram_caption": "ConvoScope — conversation input → analysis engine → multi-LLM comparison → HTML reports",
        "tags": ["multi-llm", "streamlit", "conversation-analysis", "openai", "anthropic", "nlp"],
        #"links": {
            # "live demo": "",
            # "github": "https://github.com/dagny099/", 
            # "writeup": "https://...",  # add blog post / article URL when available
        #},
    },

    # Fitness Tracker
    {
        "title": "Fitness Tracker",
        "summary": "14+ years of self-tracked workout data turned into an interactive analytics dashboard.",
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
        "diagram_filename": "fitness-chatbot-v2.png",
        "diagram_caption": "Fitness Tracker — 14+ years of data → AI pattern detection → interactive Plotly dashboard → live at workouts.barbhs.com",
        "tags": ["data-engineering", "streamlit", "plotly", "fitness", "analytics", "personal-data"],
        "links": {
            "live demo": "https://workouts.barbhs.com/",
            "github": "https://github.com/dagny099/fitness-dashboard", 
            "writeup": "https://www.barbhs.com/data-stories/exercise-dashboard/",  # Data Story
        },
    }    
]


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════

def load_featured_projects() -> list[dict]:
    """Return the list of featured projects."""
    return FEATURED_PROJECTS


def _is_walkthrough_request(message: str) -> bool:
    """Return True if the user message is asking for a project walkthrough."""
    patterns = [
        r"walk\s*(me\s+)?through\s+(a\s+)?project",
        r"show\s+me\s+a\s+project",
        r"project\s+you.*(proud|excited|built|worked)",
        r"explain\s+(one\s+of\s+)?your\s+project",
        r"tell\s+me\s+about\s+(a|one\s+of)\s+(your\s+)?project",
        r"describe\s+(a|one\s+of)\s+(your\s+)?project",
        r"portfolio\s+project",
        r"featured\s+project",
    ]
    lower = message.lower()
    return any(re.search(p, lower) for p in patterns)


def select_project_for_walkthrough(user_message: str) -> dict | None:
    """
    Select a featured project based on the user's message.

    Returns None if the message doesn't look like a walkthrough request.
    When it is a walkthrough request, tries keyword matching against
    title/summary/tags, falling back to the first project.
    """
    if not _is_walkthrough_request(user_message):
        return None

    projects = load_featured_projects()
    if not projects:
        return None

    # Score each project by keyword overlap with the user message
    words = set(re.findall(r'\w+', user_message.lower()))

    best, best_score = projects[0], 0  # default fallback
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


def get_diagram_path(project: dict) -> str | None:
    """
    Return the absolute path to the project's diagram if it exists on disk.
    Returns None if the file is missing, so callers can gracefully omit the image.
    """
    diagram_path = os.path.join(_DIAGRAM_DIR, project["diagram_filename"])
    if os.path.isfile(diagram_path):
        print("THE EXISTING DIAGRAM PATH WAS FOUND")
        return diagram_path
    return None


def enrich_message_for_walkthrough(message: str, project: dict) -> str:
    """
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
