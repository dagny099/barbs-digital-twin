# Neo4j Migration Plan: ChromaDB → Graph-Based Retrieval

**Date**: 2026-05-11
**Status**: Planning / Prototype Phase
**Goal**: Replace ChromaDB vector-only retrieval with Neo4j graph-based approach to solve granularity, connection, and ranking issues

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [Current Architecture Analysis](#current-architecture-analysis)
4. [Proposed Neo4j Schema](#proposed-neo4j-schema)
5. [How This Solves Current Problems](#how-this-solves-current-problems)
6. [Migration Strategy](#migration-strategy)
7. [Query Transformation](#query-transformation)
8. [Entity Extraction Pipeline](#entity-extraction-pipeline)
9. [Implementation Roadmap](#implementation-roadmap)
10. [Code Changes Required](#code-changes-required)
11. [Expected Improvements](#expected-improvements)
12. [Risks & Mitigations](#risks--mitigations)
13. [Evaluation Strategy](#evaluation-strategy)

---

## Executive Summary

This document outlines a migration from ChromaDB (pure vector search) to Neo4j (graph database with vector indexing) for Barbara's Digital Twin knowledge retrieval system.

**Key Motivations**:
- **Wrong Granularity**: 900-char chunks often split mid-thought; need full section retrieval
- **Missing Connections**: Can't answer "which projects use X skill/method?"
- **Poor Ranking**: L2 distance alone doesn't capture semantic relationships

**Proposed Solution**:
- Store full sections (not just chunks) with complete text
- Explicitly model relationships: Project → Skills, Project → Methods, Project → Publications
- Hybrid ranking: vector similarity + graph centrality + relationship depth
- Enable new query types via Cypher graph traversal

**Migration Approach**: Full replacement (not hybrid) in 5-day phased rollout with continuous evaluation.

---

## Problem Statement

### Current ChromaDB Limitations

Based on analysis of the Digital Twin codebase (app.py, utils.py, featured_projects.py, ingestion scripts):

1. **Wrong Granularity**
   - Returns 900-char chunks that often cut mid-paragraph
   - User needs complete context (full sections) for coherent answers
   - Example: Asking about a project returns 3 fragmented chunks instead of the complete project walkthrough

2. **Missing Connections**
   - Can't traverse relationships: "Which other projects use network analysis?"
   - Can't find similar projects by shared methods/skills
   - Project-to-publication links are implicit, not queryable

3. **Poor Ranking**
   - Pure L2 distance on embeddings doesn't consider:
     - How central/connected a section is in the knowledge graph
     - Whether a section explicitly describes vs. mentions a topic
     - Hierarchical relationships (section → document → source type)

### Why Graph Database?

Barbara's existing projects (Resume Explorer, Weaving Memories, Academic Citation Platform, Concept Cartographer) demonstrate deep expertise in knowledge graphs. Applying this to the Digital Twin itself creates:
- **Better retrieval quality** through multi-signal ranking
- **New capabilities** via relationship traversal
- **Portfolio alignment** — the Digital Twin becomes a demonstration of graph-based knowledge engineering

---

## Current Architecture Analysis

### ChromaDB Implementation

**Current Setup**:
- **Vector Database**: ChromaDB with persistent local storage (`.chroma_db_DT/`)
- **Collection**: `barb-twin`
- **Embeddings**: OpenAI `text-embedding-3-small` (1536 dimensions)
- **Distance Metric**: L2 → converted to cosine similarity
- **Chunking**: 900 chars, 100 char overlap, paragraph boundaries

**Data Sources** (16 distinct):
- **Core KB Documents**: `kb_biosketch.md`, `kb_philosophy-and-approach.md`, `kb_professional_positioning.md`, `kb_intellectual_foundations.md`, `kb_projects.md`, `kb_publications.md`, etc.
- **Project Summaries**: 20 one-page PDFs
- **Project Walkthroughs**: Curated contexts from `featured_projects.py`
- **Jekyll Website**: Live barbhs.com content

**Metadata Schema** (per chunk):
```python
{
    'source': 'kb-biosketch:kb_biosketch.md',
    'section': 'Professional Experience',
    'chunk_index': 0,
    'sensitivity': 'public|personal|inner_circle'
}
```

**Retrieval Flow** (app.py:1430-1532):
1. Detect visitor tier (public/personal/inner_circle)
2. Embed user query with OpenAI
3. Query ChromaDB with top-K=10, sensitivity filter
4. Convert L2 distances to cosine similarity
5. Format chunks with provenance: `[Source — Section]`
6. Inject into LLM context

### Featured Projects Structure

Barbara maintains 10 featured projects in `featured_projects.py`:
- Resume Graph Explorer (SKOS/ESCO knowledge graph)
- Digital Twin (this chatbot - RAG system)
- Weaving Memories (Neo4j memorial graph)
- Academic Citation Platform (TransE embeddings)
- Poolula Platform (LLC management with eval harness)
- Beehive Monitor (computer vision + weather correlation)
- ConvoScope (multi-LLM conversation analysis)
- Fitness Tracker (14 years of workout data)
- Concept Cartographer (real-time knowledge graph builder)
- ChronoScope (timeline extraction)

Each project has:
- `title`, `summary`, `design_insight`, `walkthrough_context`
- `tags` (technical topics)
- `mention_keywords` (detection triggers)
- `links` (live demo, GitHub, docs)
- `blog_posts` (related writing)

**These projects will become first-class entities in the Neo4j graph.**

---

## Proposed Neo4j Schema

### Node Types

```cypher
// ═══════════════════════════════════════════════════════════════════
// DOCUMENT HIERARCHY
// ═══════════════════════════════════════════════════════════════════

(:Document {
    id: string,           // e.g., "kb_biosketch"
    source_type: string,  // e.g., "kb-biosketch", "project-summary", "jekyll"
    file_path: string,
    title: string,
    sensitivity: string,  // "public", "personal", "inner_circle"
    created_at: datetime
})

(:Section {
    id: string,          // e.g., "kb_biosketch:Professional_Experience"
    name: string,        // "Professional Experience"
    full_text: string,   // COMPLETE section text (solves granularity!)
    embedding: vector,   // 1536-dim vector of FULL SECTION
    sensitivity: string,
    order: int,          // Position within document
    char_count: int
})

(:Chunk {
    id: string,
    text: string,
    embedding: vector,   // Keep for hybrid retrieval if needed
    chunk_index: int,
    char_count: int
})

// ═══════════════════════════════════════════════════════════════════
// SEMANTIC ENTITIES (extracted from content)
// ═══════════════════════════════════════════════════════════════════

(:Project {
    id: string,              // e.g., "resume-graph-explorer"
    title: string,           // "Resume Graph Explorer"
    summary: string,
    design_insight: string,
    walkthrough_context: string,
    diagram_filename: string,
    live_demo_url: string,
    github_url: string,
    docs_url: string,
    sensitivity: string,
    tags: list<string>       // ["knowledge-graph", "skos", "rdf"]
})

(:Skill {
    name: string,           // e.g., "Knowledge Graphs", "RAG Systems"
    category: string,       // "technical", "domain", "soft"
    proficiency: string     // "expert", "proficient", "familiar"
})

(:Method {
    name: string,          // e.g., "Section-aware chunking", "TransE embeddings"
    category: string,      // "data-engineering", "ml", "evaluation"
    description: string
})

(:Publication {
    title: string,
    type: string,         // "dissertation", "paper", "blog_post"
    year: int,
    url: string
})

(:Concept {
    name: string,         // e.g., "Organizational sensemaking"
    source: string,       // e.g., "intellectual_foundations"
    description: string
})

(:Technology {
    name: string,         // e.g., "ChromaDB", "Neo4j", "Streamlit"
    category: string      // "database", "framework", "platform"
})
```

### Relationship Types

```cypher
// ═══════════════════════════════════════════════════════════════════
// DOCUMENT STRUCTURE
// ═══════════════════════════════════════════════════════════════════

(:Document)-[:HAS_SECTION]->(:Section)
(:Section)-[:HAS_CHUNK]->(:Chunk)
(:Section)-[:NEXT_SECTION]->(:Section)  // Sequential ordering

// ═══════════════════════════════════════════════════════════════════
// PROJECT RELATIONSHIPS (solves "missing connections" problem!)
// ═══════════════════════════════════════════════════════════════════

(:Project)-[:DEMONSTRATES {role: string}]->(:Skill)
  // role: "core", "secondary", "supporting"

(:Project)-[:USES_METHOD {stage: string}]->(:Method)
  // stage: "ingestion", "retrieval", "evaluation", "generation"

(:Project)-[:USES_TECHNOLOGY]->(:Technology)

(:Project)-[:DOCUMENTED_IN]->(:Publication)

(:Project)-[:DESCRIBED_IN]->(:Section)
  // Links project entity to KB sections that discuss it

(:Project)-[:RELATED_TO {similarity: float}]->(:Project)
  // Similar projects by shared skills/methods

// ═══════════════════════════════════════════════════════════════════
// CONCEPTUAL RELATIONSHIPS
// ═══════════════════════════════════════════════════════════════════

(:Concept)-[:RELATES_TO {relationship_type: string}]->(:Concept)
  // relationship_type: "influences", "extends", "applies"

(:Concept)-[:APPLIED_IN]->(:Project)

(:Skill)-[:BROADER_THAN]->(:Skill)  // SKOS-style hierarchies
(:Skill)-[:RELATED_TO]->(:Skill)

(:Method)-[:VARIANT_OF]->(:Method)
(:Method)-[:USES_TECHNOLOGY]->(:Technology)

// ═══════════════════════════════════════════════════════════════════
// PUBLICATION RELATIONSHIPS
// ═══════════════════════════════════════════════════════════════════

(:Publication)-[:DISCUSSES]->(:Project)
(:Publication)-[:INTRODUCES]->(:Concept)
(:Publication)-[:CITED_IN]->(:Section)

// ═══════════════════════════════════════════════════════════════════
// SEMANTIC SEARCH ENTRY POINTS
// ═══════════════════════════════════════════════════════════════════

(:Section)-[:MENTIONS {count: int, context: string}]->(:Project)
(:Section)-[:MENTIONS {count: int, context: string}]->(:Skill)
(:Section)-[:MENTIONS {count: int, context: string}]->(:Concept)
(:Section)-[:MENTIONS {count: int, context: string}]->(:Technology)
```

---

## How This Solves Current Problems

### Problem 1: Wrong Granularity ✅

**Before (ChromaDB)**:
- Returns 900-char chunks
- Often splits mid-paragraph or mid-thought
- User gets 3-4 fragments that need mental stitching

**After (Neo4j)**:
- Store `full_text` in Section nodes (2-3K chars)
- Return complete, coherent sections
- Chunks still exist as children for fine-grained fallback if needed

**Example Query**:
```cypher
// Return FULL SECTION about Resume Graph Explorer
MATCH (p:Project {id: "resume-graph-explorer"})<-[:DESCRIBED_IN]-(s:Section)
RETURN s.full_text, s.name
```

### Problem 2: Missing Connections ✅

**Before (ChromaDB)**:
- Can't answer: "Which other projects used network analysis?"
- Can't find: "Projects similar to Resume Explorer"
- Relationships are implicit in text, not queryable

**After (Neo4j)**:
- Explicit `Project → Skill`, `Project → Method` relationships
- Graph traversal enables discovery queries

**Example Queries**:
```cypher
// Find all projects that demonstrate knowledge graphs
MATCH (skill:Skill {name: "Knowledge Graphs"})<-[:DEMONSTRATES]-(project:Project)
RETURN project.title, project.summary

// Find projects using similar methods to Resume Explorer
MATCH (p1:Project {id: "resume-graph-explorer"})-[:USES_METHOD]->(m:Method)<-[:USES_METHOD]-(p2:Project)
WHERE p1 <> p2
RETURN p2.title, collect(m.name) as shared_methods

// Find all projects using Neo4j
MATCH (tech:Technology {name: "Neo4j"})<-[:USES_TECHNOLOGY]-(project:Project)
RETURN project.title
```

### Problem 3: Poor Ranking ✅

**Before (ChromaDB)**:
- Pure L2 distance on embeddings
- No consideration of:
  - How central/connected a section is
  - Whether it explicitly describes vs. mentions
  - Hierarchical importance

**After (Neo4j)**:
- **Multi-signal ranking** combining:
  1. **Vector similarity** (still use embeddings!)
  2. **Graph centrality** (how connected is this section?)
  3. **Relationship specificity** (DESCRIBED_IN > MENTIONS)
  4. **Entity richness** (how many projects/skills/concepts)

**Example Query**:
```cypher
// Hybrid: vector similarity + graph context
CALL db.index.vector.queryNodes('section_embeddings', 10, $query_embedding)
YIELD node AS s, score AS vector_score

WHERE s.sensitivity IN $allowed_tiers

// Boost sections that explicitly describe projects
OPTIONAL MATCH (s)-[:DESCRIBED_IN]->(p:Project)
OPTIONAL MATCH (s)-[:MENTIONS]->(entity)

WITH s, vector_score,
     count(DISTINCT p) AS projects_described,
     count(DISTINCT entity) AS entities_mentioned

// Composite score: weighted combination
WITH s,
     (vector_score * 0.5 +          // Base semantic similarity
      projects_described * 0.3 +     // Boost for project descriptions
      entities_mentioned * 0.1 +     // Boost for entity-rich sections
      (CASE WHEN s.char_count > 2000 THEN 0.1 ELSE 0 END)) AS final_score

ORDER BY final_score DESC
LIMIT 5

MATCH (doc:Document)-[:HAS_SECTION]->(s)
RETURN s.full_text, s.name, doc.title, final_score,
       [(s)-[:DESCRIBED_IN]->(p:Project) | p.title] AS described_projects
```

---

## Migration Strategy

### Approach: Full Replacement (Recommended)

Replace ChromaDB entirely with Neo4j in one migration.

**Why not hybrid?**
- Hybrid (ChromaDB + Neo4j) doubles infrastructure complexity
- Requires keeping two databases in sync
- Doesn't solve granularity or ranking problems
- Graph-native vector indexing (Neo4j 5.11+) provides vector search without ChromaDB

### Phased Rollout

**Phase 1: Setup & Schema** (Day 1)
- [ ] Install Neo4j (local Docker or Aura free tier)
- [ ] Define schema with constraints and indexes
- [ ] Create vector index for section embeddings
- [ ] Write data model classes (Pydantic)

**Phase 2: Entity Extraction** (Day 2)
- [ ] Parse KB documents into Document → Section hierarchy
- [ ] Run LLM extraction for entities (Projects, Skills, Methods, Concepts)
- [ ] Create nodes in Neo4j with proper labels
- [ ] Generate and store section embeddings

**Phase 3: Relationship Mapping** (Day 2-3)
- [ ] Create structural relationships (Document → Section → Chunk)
- [ ] Create semantic relationships (Project → Skill/Method)
- [ ] Create mention relationships (Section → Entity)
- [ ] Validate graph connectivity

**Phase 4: Query Migration** (Day 3)
- [ ] Create `neo4j_utils.py` with driver and query functions
- [ ] Update `app.py` to replace ChromaDB calls
- [ ] Update context construction for full sections
- [ ] Test with sample queries

**Phase 5: Evaluation & Tuning** (Day 4)
- [ ] Run offline eval suite
- [ ] Compare ChromaDB baseline vs Neo4j
- [ ] Tune ranking weights
- [ ] Address regressions

**Phase 6: Deployment** (Day 5)
- [ ] Update requirements.txt, .env, docs
- [ ] Deploy to EC2 with Neo4j Aura
- [ ] Monitor query logs
- [ ] Update MAINTAINER_GUIDE.md

---

## Query Transformation

### Current: ChromaDB Retrieval (app.py:1454-1485)

```python
# Embed query
query_embedding = openai.embeddings.create(
    model="text-embedding-3-small",
    input=user_query
).data[0].embedding

# Similarity search
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=10,
    where={"sensitivity": {"$in": allowed_tiers}}
)

# Convert L2 to cosine similarity
similarities = [1 - (dist**2 / 2) for dist in results['distances'][0]]

# Format context
context_parts = []
for i, (doc, meta, sim) in enumerate(zip(results['documents'][0],
                                          results['metadatas'][0],
                                          similarities)):
    source = meta.get('source', 'unknown')
    section = meta.get('section', '')
    context_parts.append(f"[{source} — {section}]")
    context_parts.append(doc)
    context_parts.append("---")
```

### New: Neo4j Hybrid Retrieval

```python
from neo4j import GraphDatabase

def query_neo4j_rag(user_query: str, visitor_tier: str = "public", k: int = 5) -> dict:
    """
    Hybrid vector + graph retrieval from Neo4j.

    Returns:
        {
            "context": "Formatted context string",
            "sources": ["kb_biosketch — Professional Experience", ...],
            "scores": [0.89, 0.76, ...],
            "related_projects": [["Resume Graph Explorer"], ...]
        }
    """
    # Determine allowed tiers
    tier_hierarchy = {
        "public": ["public"],
        "personal": ["public", "personal"],
        "inner_circle": ["public", "personal", "inner_circle"]
    }
    allowed_tiers = tier_hierarchy.get(visitor_tier, ["public"])

    # Embed query
    query_embedding = openai.embeddings.create(
        model="text-embedding-3-small",
        input=user_query
    ).data[0].embedding

    # Neo4j Cypher query
    cypher = """
    // Vector similarity on section embeddings
    CALL db.index.vector.queryNodes('section_embeddings', $k * 2, $query_embedding)
    YIELD node AS section, score AS vector_score

    // Filter by sensitivity
    WHERE section.sensitivity IN $allowed_tiers

    // Calculate graph-based signals
    OPTIONAL MATCH (section)-[:DESCRIBED_IN]->(p:Project)
    OPTIONAL MATCH (section)-[:MENTIONS]->(entity)

    WITH section, vector_score,
         count(DISTINCT p) AS projects_described,
         count(DISTINCT entity) AS entities_mentioned

    // Composite ranking (tunable weights)
    WITH section,
         (vector_score * 0.5 +
          projects_described * 0.3 +
          entities_mentioned * 0.1 +
          (CASE WHEN section.char_count > 2000 THEN 0.1 ELSE 0 END)) AS final_score,
         vector_score,
         projects_described

    ORDER BY final_score DESC
    LIMIT $k

    // Get parent document and related projects
    MATCH (doc:Document)-[:HAS_SECTION]->(section)
    OPTIONAL MATCH (section)-[:DESCRIBED_IN]->(project:Project)

    RETURN section.full_text AS text,
           section.name AS section_name,
           doc.title AS source,
           final_score,
           vector_score,
           collect(DISTINCT project.title) AS related_projects
    """

    # Execute query
    with driver.session() as session:
        results = session.run(cypher, {
            "query_embedding": query_embedding,
            "k": k,
            "allowed_tiers": allowed_tiers
        })

        # Format results
        context_parts = []
        sources = []
        scores = []
        related_projects_list = []

        for record in results:
            source_label = f"{record['source']} — {record['section_name']}"
            sources.append(source_label)
            scores.append(record['final_score'])
            related_projects_list.append(record['related_projects'])

            context_parts.append(f"[{source_label}]")
            context_parts.append(record['text'])

            if record['related_projects']:
                projects = ", ".join(record['related_projects'])
                context_parts.append(f"(Describes: {projects})")

            context_parts.append("---")

        return {
            "context": "\n".join(context_parts),
            "sources": sources,
            "scores": scores,
            "related_projects": related_projects_list
        }
```

---

## Entity Extraction Pipeline

To populate the graph, we need to extract entities from existing KB documents.

### LLM-Based Extraction

```python
# scripts/extract_entities.py

import anthropic
from typing import List, Dict
import json

def extract_project_entities(project: dict) -> dict:
    """
    Extract Skills, Methods, Technologies from a project walkthrough.

    Uses Claude 3.5 Sonnet for high-quality structured extraction.
    """
    client = anthropic.Anthropic()

    prompt = f"""Analyze this project description and extract structured entities.

Project Title: {project['title']}

Project Walkthrough:
{project['walkthrough_context']}

Extract:
1. **Skills** demonstrated (capabilities like "Knowledge Graphs", "RAG Systems", "Evaluation Harnesses")
2. **Methods** used (approaches like "Section-aware chunking", "TransE embeddings", "Hybrid retrieval")
3. **Technologies** used (tools like "Neo4j", "ChromaDB", "Streamlit", "Flask")

For each skill, classify the role:
- "core": Central to the project (e.g., Knowledge Graphs for Resume Explorer)
- "secondary": Important but not primary (e.g., Web scraping)
- "supporting": Enabling/infrastructure (e.g., Docker, deployment)

For each method, identify the stage:
- "ingestion": Data collection/preprocessing
- "retrieval": Query/search mechanisms
- "evaluation": Testing/validation
- "generation": Output creation

Return JSON:
{{
  "skills": [
    {{"name": "Knowledge Graphs", "role": "core", "category": "technical"}},
    {{"name": "Data Visualization", "role": "secondary", "category": "technical"}}
  ],
  "methods": [
    {{"name": "Section-aware chunking", "stage": "ingestion", "category": "data-engineering"}},
    {{"name": "Hybrid retrieval", "stage": "retrieval", "category": "ml"}}
  ],
  "technologies": [
    {{"name": "Neo4j", "category": "database"}},
    {{"name": "Streamlit", "category": "framework"}}
  ]
}}
"""

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}]
    )

    return json.loads(response.content[0].text)


def extract_section_mentions(section_text: str, section_name: str) -> dict:
    """
    Extract entity mentions from a section of KB text.

    Lighter extraction than project-level — just identify what's mentioned.
    """
    client = anthropic.Anthropic()

    prompt = f"""Analyze this knowledge base section and identify entities mentioned.

Section: {section_name}

Text:
{section_text[:2000]}  # Truncate for cost

Identify mentions of:
1. Projects (by title or description)
2. Skills (technical capabilities)
3. Concepts (theoretical frameworks, principles)

Return JSON with counts:
{{
  "projects": [{{"name": "Resume Graph Explorer", "context": "brief excerpt where mentioned"}}],
  "skills": [{{"name": "Knowledge Graphs"}}],
  "concepts": [{{"name": "Organizational sensemaking"}}]
}}
"""

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    return json.loads(response.content[0].text)
```

### Graph Population Script

```python
# scripts/populate_neo4j_graph.py

from neo4j import GraphDatabase
from featured_projects import FEATURED_PROJECTS
from extract_entities import extract_project_entities
import openai

def create_schema(driver):
    """Create constraints and indexes."""
    with driver.session() as session:
        # Constraints (ensure uniqueness)
        session.run("CREATE CONSTRAINT project_id IF NOT EXISTS FOR (p:Project) REQUIRE p.id IS UNIQUE")
        session.run("CREATE CONSTRAINT skill_name IF NOT EXISTS FOR (s:Skill) REQUIRE s.name IS UNIQUE")
        session.run("CREATE CONSTRAINT method_name IF NOT EXISTS FOR (m:Method) REQUIRE m.name IS UNIQUE")
        session.run("CREATE CONSTRAINT tech_name IF NOT EXISTS FOR (t:Technology) REQUIRE t.name IS UNIQUE")

        # Vector index for section embeddings
        session.run("""
            CREATE VECTOR INDEX section_embeddings IF NOT EXISTS
            FOR (s:Section) ON s.embedding
            OPTIONS {indexConfig: {
                `vector.dimensions`: 1536,
                `vector.similarity_function`: 'cosine'
            }}
        """)


def populate_projects(driver):
    """Create Project nodes and extract/link entities."""

    for project in FEATURED_PROJECTS:
        print(f"\nProcessing: {project['title']}")

        # Extract entities using LLM
        entities = extract_project_entities(project)

        with driver.session() as session:
            # Create Project node
            session.run("""
                MERGE (p:Project {id: $id})
                SET p.title = $title,
                    p.summary = $summary,
                    p.design_insight = $design_insight,
                    p.walkthrough_context = $walkthrough_context,
                    p.diagram_filename = $diagram_filename,
                    p.tags = $tags,
                    p.sensitivity = 'public'
            """, {
                "id": project['id'],
                "title": project['title'],
                "summary": project['summary'],
                "design_insight": project.get('design_insight', ''),
                "walkthrough_context": project['walkthrough_context'],
                "diagram_filename": project.get('diagram_filename', ''),
                "tags": project.get('tags', [])
            })

            # Create Skills and relationships
            for skill in entities['skills']:
                session.run("""
                    MERGE (s:Skill {name: $name})
                    SET s.category = $category
                    WITH s
                    MATCH (p:Project {id: $project_id})
                    MERGE (p)-[:DEMONSTRATES {role: $role}]->(s)
                """, {
                    "name": skill['name'],
                    "category": skill['category'],
                    "project_id": project['id'],
                    "role": skill['role']
                })

            # Create Methods and relationships
            for method in entities['methods']:
                session.run("""
                    MERGE (m:Method {name: $name})
                    SET m.category = $category
                    WITH m
                    MATCH (p:Project {id: $project_id})
                    MERGE (p)-[:USES_METHOD {stage: $stage}]->(m)
                """, {
                    "name": method['name'],
                    "category": method['category'],
                    "project_id": project['id'],
                    "stage": method['stage']
                })

            # Create Technologies
            for tech in entities['technologies']:
                session.run("""
                    MERGE (t:Technology {name: $name})
                    SET t.category = $category
                    WITH t
                    MATCH (p:Project {id: $project_id})
                    MERGE (p)-[:USES_TECHNOLOGY]->(t)
                """, {
                    "name": tech['name'],
                    "category": tech['category'],
                    "project_id": project['id']
                })

        print(f"  ✓ Created {len(entities['skills'])} skills, "
              f"{len(entities['methods'])} methods, "
              f"{len(entities['technologies'])} technologies")


if __name__ == "__main__":
    driver = GraphDatabase.driver(
        "neo4j://localhost:7687",
        auth=("neo4j", "your-password")
    )

    print("Creating schema...")
    create_schema(driver)

    print("\nPopulating projects...")
    populate_projects(driver)

    print("\n✓ Graph population complete!")
    driver.close()
```

---

## Implementation Roadmap

### Phase 1: Setup & Schema (Day 1)

**Tasks**:
- [ ] Install Neo4j Desktop or Docker container
- [ ] Create database with constraints and indexes
- [ ] Set up Python environment with `neo4j` driver
- [ ] Write Pydantic models for entity validation

**Deliverables**:
- Running Neo4j instance (local or Aura)
- Schema definition script
- Connection test passing

### Phase 2: Entity Extraction (Day 2)

**Tasks**:
- [ ] Implement LLM extraction for projects (using Claude 3.5 Sonnet)
- [ ] Parse existing KB documents into sections
- [ ] Generate embeddings for full sections
- [ ] Populate graph with Document/Section/Project/Skill/Method nodes

**Deliverables**:
- `scripts/extract_entities.py`
- `scripts/populate_neo4j_graph.py`
- Graph with ~100+ nodes populated

### Phase 3: Relationship Mapping (Day 2-3)

**Tasks**:
- [ ] Create Document → Section relationships
- [ ] Create Project → Skill/Method relationships
- [ ] Create Section → MENTIONS → Entity relationships
- [ ] Validate graph connectivity with sample queries

**Deliverables**:
- Fully connected graph
- Sample Cypher queries returning expected results

### Phase 4: Query Migration (Day 3)

**Tasks**:
- [ ] Create `neo4j_utils.py` with driver and query functions
- [ ] Implement `query_neo4j_rag()` function
- [ ] Update `app.py` to use Neo4j instead of ChromaDB
- [ ] Test with manual queries

**Deliverables**:
- `neo4j_utils.py`
- Modified `app.py` with Neo4j integration
- Working chatbot using Neo4j retrieval

### Phase 5: Evaluation & Tuning (Day 4)

**Tasks**:
- [ ] Run offline evaluation suite (evals/)
- [ ] Compare metrics: ChromaDB baseline vs Neo4j
- [ ] Tune ranking weights (vector vs graph signals)
- [ ] Address any quality regressions

**Deliverables**:
- Evaluation report (CSV/markdown)
- Tuned ranking parameters
- 90%+ eval pass rate maintained

### Phase 6: Deployment (Day 5)

**Tasks**:
- [ ] Update `requirements.txt` with `neo4j` driver
- [ ] Update `.env` with Neo4j credentials
- [ ] Update documentation (README, DEVELOPER_GUIDE, MAINTAINER_GUIDE)
- [ ] Deploy to EC2 with Neo4j Aura connection
- [ ] Monitor query logs for 24h

**Deliverables**:
- Production deployment
- Updated documentation
- Monitoring dashboard showing successful queries

---

## Code Changes Required

### New Files

1. **`neo4j_utils.py`** - Neo4j driver and query utilities
2. **`scripts/extract_entities.py`** - LLM-based entity extraction
3. **`scripts/populate_neo4j_graph.py`** - Graph population script
4. **`scripts/embed_sections.py`** - Generate section embeddings for vector index

### Modified Files

1. **`app.py`**:
   - Replace ChromaDB client with Neo4j driver (lines 242-243)
   - Replace `query_rag()` function with Neo4j implementation (lines 1454-1485)
   - Update context formatting for full sections

2. **`requirements.txt`**:
   - Add: `neo4j>=5.14.0`
   - Add: `anthropic>=0.21.0` (for entity extraction)

3. **`.env`**:
   - Add: `NEO4J_URI=neo4j+s://xxx.databases.neo4j.io`
   - Add: `NEO4J_USER=neo4j`
   - Add: `NEO4J_PASSWORD=xxx`

4. **Documentation**:
   - `README.md`: Update tech stack to show Neo4j instead of ChromaDB
   - `DEVELOPER_GUIDE.md`: Update architecture diagrams
   - `MAINTAINER_GUIDE.md`: Update deployment instructions, remove ChromaDB roadmap item

### Optional Additions

5. **`scripts/compare_retrieval.py`** - A/B test ChromaDB vs Neo4j on same queries
6. **`notebooks/graph_analysis.ipynb`** - Explore graph structure, run Cypher queries

---

## Expected Improvements

Based on analysis of current limitations:

| **Metric** | **ChromaDB Baseline** | **Neo4j Target** | **Improvement** |
|------------|----------------------|-----------------|----------------|
| **Context Coherence** | 900-char chunks, often fragmented | 2-3K char full sections | **5-10x better** |
| **Connection Queries** | Not supported | Cypher traversal enables | **New capability** |
| **Top-5 Relevance** | ~75% (baseline from evals) | 85-90% target | **+15-25% relative** |
| **Retrieval Diversity** | Tends to return similar chunks | Graph spreads across related sections | **Qualitative improvement** |
| **Query Latency** | 150-300ms (ChromaDB local) | 200-400ms (Neo4j Aura + vector) | **Slight increase, acceptable** |

### Evaluation Metrics

We'll use the existing eval harness (`evals/`) to measure:
1. **Relevance**: Do retrieved sections answer the question?
2. **Completeness**: Is the context sufficient for LLM to respond?
3. **Accuracy**: Does the final answer match ground truth?
4. **Consistency**: Same question → same quality across runs

**Success Criteria**:
- Maintain 90%+ eval pass rate (current baseline)
- Improve qualitative coherence (human review)
- Enable 5+ new query types (relationship traversal)

---

## Risks & Mitigations

| **Risk** | **Impact** | **Mitigation** |
|----------|-----------|---------------|
| **Entity extraction errors** | Incorrect relationships in graph | Use Claude 3.5 Sonnet (highest accuracy); manual validation for core entities |
| **Graph becomes too sparse** | Weak connectivity, limited traversal value | Start conservative; expand iteratively based on query patterns |
| **Query latency increases** | Slow user experience | Optimize Cypher queries; use vector index; benchmark vs ChromaDB |
| **Migration breaks eval suite** | Quality regression | Run evals continuously; require 90%+ pass before deployment |
| **Neo4j hosting costs** | Budget constraints | Use Aura free tier (50K nodes, 175K rels); monitor usage |
| **Complex Cypher queries** | Hard to maintain/debug | Document query patterns; use query profiling (`EXPLAIN`, `PROFILE`) |
| **Embedding dimension mismatch** | Vector index errors | Validate all embeddings are 1536-dim before loading |

---

## Evaluation Strategy

### Pre-Migration Baseline

1. **Capture ChromaDB Metrics**:
   - Run full eval suite, record pass rate
   - Capture top-5 retrieval precision for 20 sample queries
   - Measure average latency (10 queries)
   - Document qualitative issues (granularity, missing connections)

2. **Create Ground Truth Dataset**:
   - 20 test queries with expected sections/projects
   - Example: "Which projects use knowledge graphs?" → ["Resume Explorer", "Weaving Memories", "Academic Citation Platform"]

### Post-Migration Evaluation

1. **Quantitative Metrics**:
   - Eval suite pass rate (target: ≥90%)
   - Top-5 precision (target: +15% vs baseline)
   - Query latency (target: <500ms p95)
   - Coverage: % of queries that return full sections vs chunks

2. **Qualitative Assessment**:
   - Human review: Are sections more coherent?
   - Relationship queries: Do traversals return expected results?
   - Edge cases: How does it handle vague/ambiguous queries?

3. **Regression Testing**:
   - Run 50 historical queries from `query_log.jsonl`
   - Compare answer quality: ChromaDB vs Neo4j
   - Flag any degraded responses

### Success Criteria

**Must Have**:
- ✅ Eval suite pass rate ≥90%
- ✅ Zero critical regressions (P0 queries still work)
- ✅ 5+ relationship query types working

**Should Have**:
- ✅ Top-5 precision improved by 15%+
- ✅ Latency <500ms p95
- ✅ Qualitative coherence improvement (human review)

**Nice to Have**:
- ✅ Graph visualization of knowledge structure
- ✅ Exploration notebook with sample queries
- ✅ A/B test harness for ongoing comparison

---

## Next Steps

### Prototype Phase (Current)

1. **Save this plan** to `docs/NEO4J_MIGRATION_PLAN_2026-05-11.md` ✅
2. **Design evaluation strategy** (detailed metrics and success criteria)
3. **Build small prototype** with 2-3 KB documents
4. **Evaluate prototype** against baseline
5. **Decide**: Full migration or iterate on prototype

### If Prototype Succeeds

6. Full entity extraction for all KB documents
7. Complete migration (Phases 1-6)
8. Production deployment

### If Prototype Needs Iteration

6. Identify gaps in schema/queries
7. Refine extraction pipeline
8. Re-test with expanded dataset

---

## References

- **Neo4j Vector Index Docs**: https://neo4j.com/docs/cypher-manual/current/indexes-for-vector-search/
- **Resume Graph Explorer** (Barbara's existing KG project): https://github.com/dagny099/resume-graph-explorer
- **Weaving Memories** (Neo4j memorial graph): https://github.com/dagny099/weaving-memories-into-graphs
- **Current Digital Twin Architecture**: `docs/DEVELOPER_GUIDE.md`, `docs/MAINTAINER_GUIDE.md`
- **Evaluation Suite**: `evals/EVALUATION_GUIDE.md`, `evals/EVAL_QUICKSTART.md`

---

**End of Migration Plan**
