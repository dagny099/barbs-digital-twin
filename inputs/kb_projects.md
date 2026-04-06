# Projects

*A portfolio registry by Barbara Hidalgo-Sotelo*
*Last updated: March 2026*

---

## How to read this document

Each project below follows the same structure: what it is, what problem it solves, how it was built, where it lives, and how it connects to the rest of my work. This consistency is deliberate — it makes my portfolio navigable for anyone asking about my work, whether they're a hiring manager looking for proof of delivery or a technical peer who wants architectural detail.

The projects are ordered roughly by how often they come up in conversation, not by date.

---

## Resume Graph Explorer

**What it is:** A full-stack application that transforms resumes into interactive SKOS-compliant knowledge graphs.

**What problem it solves:** Resumes are flat documents that hide the relationships between skills, roles, industries, and growth. A career is a graph, not a list — this tool reveals the topology.

**How it works:** I designed a hybrid SKOS-compliant vocabulary combining four namespaces (SKOS Core, ESCO, schema.org, and a custom resume namespace). The system uses provider-agnostic LLM extraction (Claude, OpenAI, or Ollama) to pull structured entities from resume text, then runs them through a three-phase normalization pipeline anchored to the ESCO European skills taxonomy. The result is a proper knowledge graph you can visualize interactively, query with SPARQL, and export as Turtle, RDF/XML, or JSON-LD. I also built a narrative synthesizer that reads the graph and produces two career stories: a conservative one (what the evidence clearly supports) and an exploratory one (what the patterns suggest might be true).

**Tech stack:** Python, Flask, Flask-SocketIO, rdflib, NetworkX (backend); React 18, Vite, Vis.js (frontend); Claude/OpenAI/Ollama (extraction); SKOS, ESCO, schema.org (ontology). 

**Live Demo:** [https://resume-graph-explorer.vercel.app/](https://resume-graph-explorer.vercel.app/)

**GitHub:** [https://github.com/dagny099/resume-graph-explorer](https://github.com/dagny099/resume-graph-explorer)

**Unique Skills used:** Ontology design, semantic web standards, full-stack deployment, LLM extraction pipelines, knowledge engineering as a first-class skill.

**Connects to:** Digital Twin (complementary lenses on a career — one structural, one conversational). Weaving Memories (both build knowledge graphs from biographical data).

---

## Digital Twin

**What it is:** A RAG-powered chatbot that represents me conversationally, grounded in my actual work and writing. You are probably talking to this project right now! 

**What problem it solves:** Static portfolios can't answer follow-up questions. A hiring manager who reads my resume can't ask "tell me more about the healthcare work" — but a chatbot built on my knowledge base can.

**How it works:** The knowledge base is built from multiple document types — a biosketch, project briefs, my personal website (via Jekyll page embedding), a resume, publications, MkDocs documentation, and other documents specifically written for retrieval quality across career stages. Documents are chunked and embedded using OpenAI's text-embedding-3-small model into ChromaDB, with idempotency guards and batching. The chatbot is built in Gradio with a carefully designed system prompt that controls voice, framing, and source priority.

**Tech stack:** Python, Gradio, Trafilatura, ChromaDB, OpenAI API (embeddings + completion), AWS EC2

**Live Demo:** This app, [https://twin.barbhs.com](https://twin.barbhs.com)

**Skills used:** RAG architecture, knowledge base design for retrieval quality (not just storage), evaluation mindset, the idea that the representation of knowledge matters as much as the knowledge itself.

**Connects to:** Resume Explorer (complementary lenses — conversational vs. structural). Poolula (evaluation harness informed the DT's approach to retrieval quality). Concept Cartographer (both extract structure from unstructured text).

---

## Weaving Memories Into Graphs

**What it is:** A memorial knowledge graph for my late father, Domingo Hidalgo Lopez (1956–2018), preserving his legacy as a software developer and naval architect whose systems are still running in semiconductor fabs worldwide and teaching me by example what it means to be a systems builder.

**What problem it solves:** Memories and legacy artifacts — diplomas, patents, photos, career records, colleagues' stories — are unstructured and fragile without intentional preservation. This project weaves them into something his family can explore and his legacy can endure in.

**How it works:** I designed a 14-entity Neo4j schema (Person, Organization, Position, Education, Location, Project, Technology, Skill, Patent, Product, Event, Artifact, Publication, Industry) with temporal relationship patterns inspired by ChronoScope and semantic web patterns from Resume Explorer. LLM-powered extraction from a biosketch produces structured YAML, which is validated against Pydantic dataclasses and loaded into Neo4j via a graph builder. External enrichment comes from Wikidata (semi-automated interactive tool with provenance tracking). The frontend is a React + Vite application with timeline, legacy, and network views served by a Flask REST API.

**Tech stack:** Python, Neo4j Aura, Claude (extraction), Flask (API), React + Vite (frontend), Wikidata API (enrichment).

**Deployment:** https://domingo-hidalgo.com

**GitHub:** [https://github.com/dagny099/weaving-memories-into-graphs](https://github.com/dagny099/weaving-memories-into-graphs)

**Unique Skills used:** Complex graph schema design (14 entities), LLM extraction with provenance tracking, Linked Open Data enrichment, full-stack deployment, and the ability to apply rigorous methodology to something deeply personal. UI/UX design

**Connects to:** Resume Explorer (both build knowledge graphs from biographical data — one for career analysis, one for legacy preservation). Digital Twin (the philosophy of "making meaning from messy data" applies to both, but this one is the most personal instance).

---

## Concept Cartographer

**What it is:** A Gradio application that extracts concepts and relationships from LLM conversations and visualizes them as interactive knowledge graphs in real time.

**What problem it solves:** Valuable conceptual relationships get lost in long conversations. This tool makes the implicit knowledge structure of a conversation visible and navigable.

**How it works:**  Ask a question or type phrase, optionally specify a "lens", and the LLM-powered app derives a structured ontology representing the concepts with categories- like Entity, Theory, Method- plus relationship triples with typed edges- like causes, requires, enables- and shows the user a visual representation of the core entities and relationships over the course of the conversation.

**Tech stack:** Python, Gradio, OpenAI API, NetworkX, AWS EC2

**Deployment:** [https://concept-cartographer.com/](https://concept-cartographer.com/)

**GitHub:** [https://github.com/dagny099/concept-cartography-gradio](https://github.com/dagny099/concept-cartography-gradio)

**Unique Skills used:** Real-time structured extraction from unstructured text, LLM APIs, interactive visualization.

**Connects to:** Digital Twin (both extract structure from unstructured text). Resume Explorer (similar concept-to-graph pattern, different input domain).

---

## Poolula Platform

**What it is:** A modular RAG system with a built-in evaluation harness, designed for rapid client-oriented experimentation.

**What problem it solves:** Most RAG systems have no systematic way to evaluate retrieval quality. Poolula treats evaluation as a first-class design concern, not an afterthought.

**How it works:** Local-first modular architecture combining a structured data layer with document retrieval (ChromaDB) and tool-style routing. The evaluation workflow scores responses against defined ground-truth expectations. The LLM backend is provider-agnostic (supports OpenAI, Anthropic) with audit-friendly logging patterns so you can trace exactly what the system retrieved and why.

**Tech stack:** Python, FastAPI, SQLModel, ChromaDB, LangChain, OpenAI/Anthropic APIs.

**Deployment:** [https://github.com/dagny099/graphgarnish](https://github.com/dagny099/graphgarnish)

**GitHub:** Privately hosted

**Unique Skills used:** Evaluation-minded engineering, provider-agnostic design, audit-friendly logging, the principle that you can't improve what you don't measure.

**Connects to:** Digital Twin (Poolula's eval harness informed the DT's approach to retrieval quality). ConvoScope (both explore multi-provider LLM patterns).

---

## ConvoScope

**What it is:** A multi-LLM conversation platform with real-time streaming, topic extraction, and built-in A/B evaluation methodology.

**What problem it solves:** No easy way to compare LLM providers on real conversational tasks with actual latency and cost measurement.

**How it works:** Supports multiple AI providers (OpenAI, Anthropic, Google) with conversation management, real-time streaming, and topic extraction. Includes an evaluation framework with A/B testing methodology that achieved a 15% quality improvement. Captures latency and token-cost metrics to guide prompt compression tradeoffs.

**Tech stack:** Python, OpenAI/Anthropic/Google APIs, LangChain, AWS (EC2, RDS, Lambda).

**Deployment:** AWS EC2 with custom domain, SSL security, and automated monitoring. URL being updated.

**GitHub:** [https://github.com/dagny099/convoscope](https://github.com/dagny099/convoscope)

**What it proves:** Production GenAI deployment on AWS, multi-provider integration, evaluation methodology, cost/latency optimization.

**Connects to:** Poolula (both explore evaluation and multi-provider patterns). Digital Twin (deployment experience carried over).

---

## HiveIQ

**What it is:** An AI-powered knowledge base that transforms 4+ years of backyard beehive inspection photos into queryable colony intelligence.

**What problem it solves:** Individual inspection photos are just moments. Integrated into a knowledge graph with timestamps, weather data, and visual analysis, they become a system for understanding colony health across seasons.

**How it works:** Google Cloud Vision API extracts visual information from inspection photos. Results are integrated with weather API data and timestamps in a Neo4j graph database. Semantic search using vector embeddings enables pattern recognition and anomaly detection across seasons.

**Tech stack:** Python, Neo4j, Google Cloud Vision API, vector embeddings, weather APIs.

**Deployment:** [https://beestory.barbhs.com](https://beestory.barbhs.com)

**GitHub:** [https://github.com/dagny099/beehive-tracker](https://github.com/dagny099/beehive-tracker)

**What it proves:** Knowledge graph construction from multimodal data (images + weather + time), computer vision API integration, semantic search, and applying professional methodology to a personal domain.

**Connects to:** Weaving Memories (both use Neo4j for knowledge graphs). The fitness pipeline (both apply data engineering to personal data over long time horizons).

---

## Fitness Analytics Dashboard

**What it is:** An end-to-end ML pipeline that classifies 14 years of personal exercise data and serves it through an interactive dashboard with explainable AI features.

**What problem it solves:** Raw fitness logs across inconsistent formats, apps, and devices are unusable without a pipeline. The dashboard reveals patterns about discipline, adaptation, and what consistency actually looks like when life keeps interrupting.

**How it works:** Automated data collection from multiple sources, feature engineering, ML classification of workout types (running, walking, strength training) using scikit-learn and XGBoost, model retraining workflow with drift detection and performance monitoring. The dashboard shows classification confidence and feature importance for explainability.

**Tech stack:** Python, scikit-learn, XGBoost, Plotly, beautifulsoup, MySQL, AWS RDS, AWS Lambda, AWS EC2

**Deployment:** [https://workouts.barbhs.com](https://workouts.barbhs.com)

**GitHub:** [https://github.com/dagny099/fitness-dashboard](https://github.com/dagny099/fitness-dashboard)

**Unique Skills used:** End-to-end ML pipeline with model lifecycle management (training, deployment, monitoring, retraining), data engineering across inconsistent sources, explainable AI.

**Connects to:** Beehive Analytics (both apply data engineering to personal data over long time horizons). The career narrative (14 years of self-tracking demonstrates the same "meaning from messy data" principle).

---

## ChronoScope

**What it is:** A Streamlit application that extracts timeline events from resumes and generates interactive visualizations.

**What problem it solves:** Career timelines buried in resume text are hard to compare visually. This tool makes temporal patterns — gaps, overlaps, transitions — immediately visible.

**How it works:** Uses LLM extraction to identify temporal events from resume text, applies validation and quality checks for consistency across runs, and generates interactive Plotly timelines plus TimelineJS-ready exports. Local-first processing supports privacy-sensitive workflows.

**Tech stack:** Python, Streamlit, OpenAI API, Plotly, TimelineJS.

**Deployment:** <currently being redeployed>

**GitHub:** Will be Public Soon

**Unique Skills used:** LLM extraction with quality validation, temporal data visualization, privacy-conscious design (local-first processing).

**Connects to:** Resume Explorer (both analyze career data — ChronoScope temporally, Resume Explorer structurally). Weaving Memories (temporal relationship patterns from ChronoScope informed the Weaving Memories schema).

---

## GraphRAG with Podcasts

**What it is:** A knowledge graph and vector retrieval system for podcast episodes, supporting question answering with citation-grounded traceability. This is a really cool project I'm working on now.  

**What problem it solves:** Podcast content is rich but unsearchable. This system makes it possible to ask questions across episodes and get answers grounded in specific timestamps and sources.

**How it works:** Multi-stage ingestion pipeline with checkpointing and idempotent re-runs. Entities and relationships modeled in Neo4j Aura to connect episodes, concepts, and sources. GraphRAG-style retrieval patterns support timestamp/citation-style grounding for traceability.

**Tech stack:** Python, Neo4j Aura, OpenAI embeddings, LangChain.

**Deployment:** https://github.com/dagny099/graphgarnish  <currently being redeployed>

**GitHub:** [https://github.com/dagny099/graphgarnish](https://github.com/dagny099/graphgarnish)

**Unique Skills used:** GraphRAG architecture (not just vector RAG), citation-grounded retrieval, idempotent pipeline design, knowledge graph construction from audio/transcript data.

**Connects to:** Digital Twin (both use RAG retrieval, but this one adds graph-based retrieval patterns). Poolula (both explore advanced RAG architectures beyond simple vector search).

---

## Citation Network Analysis (CitationCompass)

**What it is:** A platform for analyzing academic citation networks using graph neural networks and knowledge graph embeddings. I'm currently revisiting this projec tnow. 

**What problem it solves:** Understanding how academic papers relate to each other — predicting citations, identifying influence patterns, mapping intellectual lineage.

**How it works:** Integrated three separate academic citation analysis codebases into a unified platform. Developed graph neural network models for citation prediction using TransE and other embedding techniques. Applied knowledge graph representation to academic literature networks.

**Tech stack:** Python, Neo4j, NetworkX, PyTorch, TransE.

**Deployment:** <currently being redeployed>

**GitHub:** [https://github.com/dagny099/citation-compass](https://github.com/dagny099/citation-compass)

**Unique Skills used:** Graph neural networks, knowledge graph embeddings (TransE), academic data analysis, codebase integration.

**Connects to:** Resume Explorer (both use knowledge graphs for structured analysis). Weaving Memories (both model complex entity relationships in Neo4j).

---

## The pattern across these projects

Every project in this portfolio follows the same methodology: start with something messy and human-generated, find the hidden structure (an ontology, a graph, a temporal pattern), and make it queryable. The tools change — Neo4j, ChromaDB, scikit-learn, rdflib — but the pattern is constant. That's not a coincidence. It's how I think about every problem.

The projects also connect to each other in non-obvious ways. Resume Explorer and the Digital Twin are complementary lenses on a career. Weaving Memories and Resume Explorer both build knowledge graphs from biographical data. Poolula's evaluation harness shaped the Digital Twin's approach to retrieval quality. ChronoScope's temporal patterns informed the Weaving Memories schema. Understanding these connections is part of understanding how I work — I don't build isolated tools, I build a portfolio where each project teaches me something that improves the next one.
