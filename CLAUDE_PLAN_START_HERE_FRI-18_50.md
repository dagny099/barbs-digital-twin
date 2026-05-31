# Development Phase 1: Neo4j Migration Setup & Baseline

## Context

First development phase of the ChromaDB → Neo4j migration for the Digital Twin RAG chatbot. The migration plan (`docs/NEO4J_MIGRATION_PLAN_2026-05-11.md`) and eval plan (`evals/NEO4J_PROTOTYPE_EVAL_PLAN.md`) are complete and reviewed. All architectural decisions are locked in.

**Important discovery**: `../graph-garnish-rag-with-podcasts/` is a production-ready Neo4j GraphRAG system with directly reusable components. Phase 1 should ADAPT its patterns rather than build from scratch. This significantly reduces risk.

Phase 1 has two parallel goals:
1. **Build the Neo4j foundation** — driver, schema, Pydantic models, connection smoke test
2. **Capture ChromaDB baseline metrics** — lock in ground truth before touching the existing system

Phase 1 does NOT load data into Neo4j. That is Phase 2 (Entity Extraction).

---

## Reuse Map: Podcast Project → Digital Twin

| What we need | Reuse from podcast project | Location |
|---|---|---|
| Neo4j config/env loading | Adapt `Config` dataclass | `../graph-garnish-rag-with-podcasts/src/config.py` |
| Schema builder (idempotent DDL) | Adapt `Neo4jSchemaBuilder` | `../graph-garnish-rag-with-podcasts/src/graph/schema_builder.py` |
| LLM provider abstraction | Adapt `get_provider()` | `../graph-garnish-rag-with-podcasts/src/providers/llm_provider.py` |
| Vector search Cypher patterns | Adapt field names | `../graph-garnish-rag-with-podcasts/src/retrieval/vector_search.py` |
| Graph expansion traversal | Adapt relationship types | `../graph-garnish-rag-with-podcasts/src/retrieval/graph_expansion.py` |
| Embedding with hash caching | Adapt directly | `../graph-garnish-rag-with-podcasts/src/embeddings/embedder.py` |
| Pipeline stage architecture | Adapt pattern | `../graph-garnish-rag-with-podcasts/src/pipelines/podcast_ingestion.py` |

**What does NOT transfer from the podcast project:**
- **Normalization**: Podcast uses fuzzy matching (SequenceMatcher 0.85) because it has 720+ concepts. Digital Twin has ~40-80 entities — LLM-batch is faster, cheaper, and more accurate at this scale. Normalization stays as designed in Architectural Decision 2 (adapted from `../resume-graph-explorer/` instead).
- **Concept extraction prompts**: Domain-specific to podcast transcripts. Digital Twin needs Skills/Methods/Technologies/Concepts, not podcast topics.
- **Relationship inference**: Podcast uses SKOS BROADER/NARROWER/RELATED. Digital Twin uses DEMONSTRATES, USES_METHOD, USES_TECHNOLOGY, DESCRIBED_IN, etc.
- **Answer synthesis**: Podcast-specific citation format.

---

## Critical Files & Context

| File | Role |
|---|---|
| `docs/NEO4J_MIGRATION_PLAN_2026-05-11.md` | Full schema, Cypher, decisions — read "Architectural Decisions" section first |
| `evals/NEO4J_PROTOTYPE_EVAL_PLAN.md` | Baseline test queries + scoring rubric |
| `utils.py` | `parse_markdown_sections()`, `get_sensitivity()` — reuse directly |
| `featured_projects.py` | 10 project dicts with `tags` arrays — entity seed list |
| `scripts/embed_kb_doc.py` | Reference for section parsing pattern |
| `evals/run_evals.py` | Existing full eval suite — run for Test 5 baseline |
| `.env` | Add `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` here |
| `requirements.txt` | Add `neo4j>=5.14.0` and `anthropic>=0.21.0` |

**Inputs**: KB documents are at path in `INPUTS_PATH` env var (separate staging repo). All 13 `kb_*.md` files use consistent H2 section structure.

---

## Tasks

### Group A: Dependencies & Environment

**A1. Update `requirements.txt`**
Add:
```
neo4j>=5.14.0
anthropic>=0.21.0
```
(Podcast project uses `neo4j==5.15.0` — confirms `>=5.14.0` is correct.)

**A2. Update `.env.example`**
Add a clearly labeled Neo4j section (same vars as the podcast project: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`):
```
# ── Neo4j Graph Database ──────────────────────────────
# Local Docker: neo4j://localhost:7687
# Neo4j Aura (cloud): neo4j+s://xxx.databases.neo4j.io
NEO4J_URI=neo4j://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password-here
```

---

### Group B: Pydantic Models

**B1. Create `neo4j_models.py`** at project root

Pydantic v2 models for all node types. Each has a `to_dict()` method returning kwargs for Cypher `SET`. These are pure validation models — no Neo4j interaction.

Node types (from migration plan schema section):
- `DocumentNode` — id, source_type, file_path, title, sensitivity, content_hash, last_updated
- `SectionNode` — id, name, full_text, sensitivity, order, char_count *(embedding added at insert time, not in model)*
- `ProjectNode` — all `featured_projects.py` fields: id, title, summary, design_insight, walkthrough_context, diagram_filename, tags, sensitivity (hardcode "public")
- `SkillNode` — name, category, alt_labels (list)
- `MethodNode` — name, category, description, alt_labels (list)
- `TechnologyNode` — name, category, alt_labels (list)
- `ConceptNode` — name, source, description, alt_labels (list)

---

### Group C: Neo4j Driver & Schema

**C1. Create `neo4j_utils.py`** at project root

Adapt the `Config` dataclass and driver factory pattern from `../graph-garnish-rag-with-podcasts/src/config.py`. Key differences:
- Load from `.env` using `python-dotenv` (same pattern already in `utils.py`)
- Expose `get_driver()` returning a `GraphDatabase.driver()` singleton
- Expose `close_driver()` for clean shutdown
- Do NOT replicate LLM config here — that stays in the existing `utils.py`/litellm setup

**C2. Create `scripts/setup_neo4j_schema.py`**

Adapt `Neo4jSchemaBuilder.create_full_schema()` from `../graph-garnish-rag-with-podcasts/src/graph/schema_builder.py`. The podcast project's pattern is exactly right (idempotent DDL, prints ✓/✗ per statement). Change:
- Replace podcast node types with Digital Twin node types
- Use Digital Twin constraints (4: project_id, skill_name, method_name, tech_name)
- Same vector index config (1536 dims, cosine, `IF NOT EXISTS`) on `Section.embedding`
- Add `SHOW INDEXES` verification at end

Run order: constraints first, property indexes second, vector index third (same as podcast project).

**C3. Create `scripts/test_neo4j_connection.py`**

Smoke test (adapt from podcast project's connection test pattern):
1. `get_driver()` → run `RETURN 1 AS result`
2. `SHOW INDEXES` → assert `section_embeddings` present with status `ONLINE`
3. `SHOW CONSTRAINTS` → assert all 4 constraints present
4. Print summary table, exit 0 on pass / 1 on fail

---

### Group D: ChromaDB Baseline Capture

These scripts measure the current ChromaDB system. Run against the live system before any Neo4j work touches `app.py`.

**D1. Create `evals/capture_baseline_latency.py`**

20 representative queries (hardcode from the eval plan's granularity + relationship query lists). For each: time `collection.query(query_embeddings=[...], n_results=10)` end-to-end. Calculate p50/p95/p99 using numpy. Output `evals/results/baseline_latency.json`.

**D2. Create `evals/capture_baseline_relationships.py`**

8 relationship queries from the eval plan (hardcoded). For each: retrieve top-5 chunks, check if expected project names appear in returned text, score ✅/⚠️/❌ automatically. Output `evals/results/baseline_relationships.json`.

```python
RELATIONSHIP_QUERIES = [
    {"query": "Which projects use knowledge graphs?",
     "expected_projects": ["Resume Graph Explorer", "Weaving Memories", "Academic Citation Platform", "Concept Cartographer"]},
    {"query": "What projects use Neo4j?",
     "expected_projects": ["Weaving Memories Into Graphs", "Academic Citation Platform"]},
    {"query": "Which projects are similar to Resume Explorer?",
     "expected_projects": ["Concept Cartographer", "ChronoScope", "Weaving Memories Into Graphs"]},
    # + 5 more from eval plan Appendix
]
```

**D3. Create `evals/capture_baseline_granularity.py`**

10 granularity queries from the eval plan. For each: retrieve top-5 chunks, print them to terminal, prompt `input()` for 1-5 coherence score, check `must_contain` keywords automatically. Output `evals/results/baseline_granularity.json` including avg_coherence.

**D4. Create `evals/capture_baseline_ranking.py`**

15 factual queries (bio + project categories from `eval_questions.csv`). For each: retrieve top-10, print with rank numbers, prompt `input()` for rank where answer appears. Calculate Top-1 %, Top-3 %, MRR. Output `evals/results/baseline_ranking.json`.

**D5. Run existing eval suite (user manual step)**
```bash
cd evals && python run_evals.py
# Copy output → evals/results/baseline_chromadb.json
```

---

### Group E: Directory Structure

**E1. Create `evals/results/.gitkeep`**

Track the directory in git. Add to `.gitignore`:
```
evals/results/*.json
```

---

## Verification

Phase 1 is complete when:

1. `pip install -r requirements.txt` succeeds with neo4j driver
2. `python scripts/test_neo4j_connection.py` exits 0 — all 4 constraints + vector index confirmed ONLINE
3. `evals/results/baseline_latency.json` — has p50/p95/p99 numbers
4. `evals/results/baseline_relationships.json` — expect 0–20% success rate
5. `evals/results/baseline_granularity.json` — expect avg coherence 2.5–3.0
6. `evals/results/baseline_ranking.json` — expect Top-1 ~60%, MRR ~0.75

---

## What You (the user) Do After Claude Commits Phase 1 Code

1. **Provision Neo4j** (pick one):
   - **Aura free tier** (recommended): [console.neo4j.io](https://console.neo4j.io) → create instance → copy URI + password (50K nodes, 175K rels — sufficient for prototype)
   - **Docker local**: `docker run -p7474:7474 -p7687:7687 -e NEO4J_AUTH=neo4j/yourpassword neo4j:5`

2. **Add credentials to `.env`**:
   ```
   NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your-actual-password
   ```

3. **Run schema setup and smoke test**:
   ```bash
   python scripts/setup_neo4j_schema.py
   python scripts/test_neo4j_connection.py   # should exit 0
   ```

4. **Run baseline capture** (ChromaDB must be intact):
   ```bash
   python evals/capture_baseline_latency.py
   python evals/capture_baseline_relationships.py
   python evals/capture_baseline_granularity.py   # interactive: score 1-5 per query
   python evals/capture_baseline_ranking.py        # interactive: enter rank per query
   cd evals && python run_evals.py                 # copy output → evals/results/baseline_chromadb.json
   ```

5. **Start a new session** and say:
   > "Phase 1 is done. Neo4j is running and `test_neo4j_connection.py` passes. Baseline JSON files are in `evals/results/`. Start Phase 2: Entity Extraction. Read `docs/NEO4J_MIGRATION_PLAN_2026-05-11.md` starting from the Entity Extraction Pipeline section and the Architectural Decisions section. Also reference `../graph-garnish-rag-with-podcasts/src/embeddings/embedder.py` for the hash-caching embedding pattern."

---

## Out of Scope for Phase 1

- No data loaded into Neo4j (Phase 2)
- No entity extraction or LLM calls for extraction (Phase 2)
- No section embeddings (Phase 2)
- No `canonicalize_entities.py` (Phase 2)
- No changes to `app.py` (Phase 4)
- No ChromaDB removal (Phase 6)
