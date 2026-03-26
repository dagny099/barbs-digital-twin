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
    },
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
    },
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
    },
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
    return (
        f"{message}\n\n"
        f"[Selected project for walkthrough: {project['title']}]\n"
        f"Summary: {project['summary']}\n"
        f"Walkthrough notes: {project['walkthrough_context']}"
    )
