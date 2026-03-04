# Resume Explorer: Project Brief
*Barbara Hidalgo-Sotelo — Written for Digital Twin Knowledge Base*

---

## What This Project Is and Why I Built It

Resume Explorer grew out of a question I kept returning to as a cognitive scientist who works with data: why do we represent career histories as flat lists? A resume is really a knowledge graph — people, organizations, skills, time spans, and relationships between them — and yet we flatten all of that structure into bullet points on a page.

I wanted to build a tool that restores that structure. The core idea: upload a resume, and instead of just reading it, you *explore* it. Skills connect to jobs. Jobs connect to organizations. The whole thing becomes a navigable, queryable graph that reveals patterns a traditional resume obscures — skills you've forgotten you have, gaps in your experience, the through-line of your career.

I also wanted it to be genuinely educational. The tagline I kept coming back to was "a playful exploration of your own professional narrative." The gamification angle — click a node, discover a connection, challenge yourself to find all your AI-related skills — came directly from my background in cognitive science and how I think about engaging interfaces.

---

## The Technical Vision I Cared About Most

The most important design decision I made was to build this on **semantic web standards** from day one, not as an afterthought. That meant SKOS (W3C's Simple Knowledge Organization System), the ESCO European Skills Taxonomy, and schema.org vocabularies throughout.

This matters to me for a specific reason: a knowledge graph that only lives inside one application isn't really a knowledge graph — it's a database with a pretty visualization. By grounding every entity in standard URIs and exporting to RDF (Turtle, RDF/XML, JSON-LD), Resume Explorer produces graphs that can talk to other systems. Your skills are linked to ESCO concepts used across Europe. Your organizations could be enriched with Wikidata data. The data is *interoperable*, not trapped.

Most resume tools make the opposite choice. I made this one deliberately.

---

## Key Architectural Decisions and Why I Made Them

### Provider-Agnostic LLM Layer
I built a strategy pattern abstraction so the application works identically with Claude, OpenAI, or Ollama running locally. This wasn't engineering for its own sake — it reflects something I believe about building AI systems: you should never be architecturally dependent on one provider. The model landscape is changing too fast, costs vary, and local inference is increasingly viable. The abstraction cost was low; the flexibility payoff is high.

### Dual-Library PDF Extraction
PDF parsing is a genuinely hard problem because PDFs aren't a document format — they're a printing format. PyMuPDF is fast but struggles with complex layouts. pdfplumber handles those layouts but is slower and heavier. I built an automatic fallback chain: try PyMuPDF first, fall through to pdfplumber if extraction is empty or fails. The combined success rate is ~95%, which is substantially better than either library alone. This kind of defensive engineering — anticipating failure modes and building graceful degradation — is a pattern I bring to all my systems work.

### SKOS Edge Type Classification
One of the design decisions I'm proudest of is the custom edge classification scheme I built for the visualization layer. Every relationship in the graph gets assigned to one of six semantic buckets: OWNERSHIP (person has skill), ORGANIZATIONAL (connected to a company), USAGE (skill applied in a role), HIERARCHICAL (SKOS taxonomy relationships), TYPING (RDF type declarations), and OTHER. Each bucket maps to a distinct color and line weight in the visualization.

This is a cognitive science decision as much as a technical one. The goal is that a user should be able to look at the graph and *understand its structure at a glance* — before they've read a single label. Color and weight carry semantic meaning. The classification is done in `networkx_adapter.py` and is the layer where graph theory meets visual communication.

### DSPy Integration
I integrated DSPy for the extraction pipeline to get chain-of-thought reasoning during entity extraction. The LLM doesn't just pull out "Python" as a skill — it reasons about context, confidence, and relationships. I also built a simplified fallback pipeline for cases where DSPy isn't available, so the application degrades gracefully rather than failing hard.

### Session Management Architecture
Multi-document sessions with JSON persistence allow users to build up a graph across multiple resumes — useful for comparing career trajectories or aggregating a team's skills. Sessions persist across application restarts, which was a deliberate choice: extraction is expensive (both in time and API cost), and re-running it every time you open the app would be a poor experience.

---

## What I Built: The Full Stack

The application is a complete full-stack system I designed and built across six phases over roughly one week in December 2025:

**Backend (Python/Flask):** Provider-agnostic LLM client, DSPy extraction module with fallback, SKOS-compliant data models (Person, Job, Skill, Education, Certification, Organization), RDF graph builder using rdflib, NetworkX adapter for visualization, Flask REST API with WebSocket support for real-time streaming, session-based storage.

**Frontend (React/Vis.js):** Physics-based interactive network graph, real-time WebSocket progress updates, entity detail panel, session management UI with progressive disclosure design, RDF export controls.

**Semantic Layer:** Full SKOS/ESCO/schema.org vocabulary implementation, custom RE namespace for resume-specific properties, SPARQL-queryable graph output, three RDF serialization formats.

**~10,000 lines of code. 30+ Python files. 8 React components. 80%+ test coverage.**

---

## Technical Depth: The SKOS Implementation

The knowledge graph uses a hybrid vocabulary I designed specifically for resume data:

Skills are typed as `esco:Skill` and linked via `skos:exactMatch` to ESCO URIs — real, dereferenceable identifiers in the European skills taxonomy. This means a "Python Programming" skill in Resume Explorer isn't just a string: it's the same concept as Python programming in any other ESCO-aligned system. Skill hierarchies use `skos:broader` and `skos:narrower` relationships, so "Machine Learning" is properly broader than "Neural Networks," and you can traverse the hierarchy.

Every entity carries provenance metadata: extraction confidence (0.0–1.0), source document, and creation timestamp. This is important for explainability — you can always trace why a particular skill or relationship appeared in the graph.

The RDF export means the graph is genuinely portable. You can load a Resume Explorer export into any SPARQL endpoint and query it. Example queries I built: "find all skills used in data science roles" and "find skill gaps — skills mentioned in jobs but not in the person's claimed skill list." That second query is the kind of insight that's invisible in a traditional resume.

---

## The Roadmap: Where This Is Going

I've designed a three-milestone interoperability roadmap that reflects how I think about the long arc of this project:

**Milestone 1 — Linked Open Data Enrichment:** Entity alignment against Wikidata and DBpedia to enrich graph nodes with external context. Your "MIT" is the same MIT as in Wikidata, with industry, location, and enrollment data attached. Matching strategy: deterministic rules first (exact name + country/industry filters), fuzzy matching second, confidence-gated.

**Milestone 2 — Semantic Search:** Convert graph nodes and edges into text snippets (with enriched labels) and index in a hybrid engine combining embedding similarity with graph-structure filters. The key design principle here: hybrid retrieval balances flexibility (semantic search) with precision (graph constraints). Every search result returns supporting triples for explainability.

**Milestone 3 — Graph-Based Recommendations:** Derived relations ("skill co-usage," "role progression," "project similarity"), materialized aggregates, SPARQL/Cypher recommendation templates. The north star: interpretable recommendations that cite the specific graph paths that drove them. Not "we think you'd be good at X" — "here are the three graph paths that suggest X."

This roadmap reflects my broader philosophy: explainability isn't a feature you bolt on. It's a design constraint that shapes every architectural decision from day one.

---

## Why This Project Represents My Thinking

Resume Explorer is a good example of how I approach problems at the intersection of cognitive science and AI systems. The visualization isn't decorative — it's designed around how humans actually perceive and extract meaning from complex networks. The semantic web standards aren't academic — they're practical choices that make the data more useful over time. The provider-agnostic architecture isn't premature optimization — it reflects a hard-won belief about building systems that outlast any single vendor's pricing or availability.

The project also reflects something personal: I built it partly because I've been on a job search, and I wanted a tool that would help me see my own career differently. Sometimes the best reason to build something is that you need it yourself.

---

## Technology Stack Summary

- **Backend:** Python 3.10+, Flask, Flask-SocketIO, rdflib, NetworkX, DSPy
- **Frontend:** React 18, Vite, Vis.js
- **LLM Providers:** Claude (Anthropic), OpenAI GPT, Ollama (local)
- **Semantic Web:** SKOS, ESCO Skill Taxonomy, schema.org
- **Storage:** JSON-based session persistence (designed for S3/GCS migration)
- **Export:** Turtle (.ttl), RDF/XML (.rdf), JSON-LD (.jsonld)
- **Status:** MVP complete (v0.2.0), interoperability roadmap in progress
