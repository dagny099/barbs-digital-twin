# Neo4j Prototype Evaluation Plan

**Date**: 2026-05-11
**Purpose**: Define metrics and test cases to evaluate if Neo4j graph-based retrieval improves on ChromaDB limitations
**Scope**: Small prototype with 2-3 KB documents before full migration

---

## Table of Contents

1. [Evaluation Goals](#evaluation-goals)
2. [Test Dataset](#test-dataset)
3. [Baseline Metrics (ChromaDB)](#baseline-metrics-chromadb)
4. [Prototype Metrics (Neo4j)](#prototype-metrics-neo4j)
5. [Test Queries](#test-queries)
6. [Success Criteria](#success-criteria)
7. [Measurement Methodology](#measurement-methodology)
8. [Decision Framework](#decision-framework)

---

## Evaluation Goals

We're testing whether Neo4j solves three specific problems identified with ChromaDB:

| **Problem** | **What to Measure** | **How to Measure** |
|------------|--------------------|--------------------|
| **1. Wrong Granularity** | Are returned contexts complete and coherent? | Context Coherence Score (1-5 scale) |
| **2. Missing Connections** | Can we traverse relationships to find related content? | Relationship Query Success Rate (% working) |
| **3. Poor Ranking** | Does the top result contain the answer? | Top-1 Precision, MRR (Mean Reciprocal Rank) |

**Additional Metrics**:
- Retrieval latency (acceptable if <500ms)
- Context completeness (does LLM have enough info to answer?)
- Backward compatibility (does existing eval suite still pass?)

---

## Test Dataset

### Prototype Scope: 3 Documents

To keep the prototype manageable, we'll use **3 knowledge base documents**:

1. **`kb_biosketch.md`** (authoritative biographical facts)
   - Sections: Professional Identity, Education, Career Highlights, etc.
   - ~4-5 sections, 2-3K chars each

2. **`kb_projects.md`** (project registry)
   - Sections organized by project or thematic grouping
   - Links to featured projects

3. **Featured Projects data** (from `featured_projects.py`)
   - 10 projects with skills, methods, technologies
   - Already structured data, perfect for entity extraction

**Why these three?**
- Cover biographical facts (bio), project details (projects), and relationships (skills/methods)
- Representative of broader KB structure
- Enable all three problem types to be tested
- Small enough to iterate quickly (<1 day to build graph)

### Entity Extraction Targets

From these 3 sources, we'll extract:
- **Projects**: 10 nodes (from `featured_projects.py`)
- **Skills**: ~30-40 unique skills (extracted from project walkthroughs)
- **Methods**: ~20-30 methods (e.g., "section-aware chunking", "TransE embeddings")
- **Technologies**: ~20 technologies (e.g., "Neo4j", "Streamlit", "ChromaDB")
- **Sections**: ~15-20 sections from KB docs
- **Documents**: 3 document nodes

**Total**: ~100-120 nodes, ~200-300 relationships

---

## Baseline Metrics (ChromaDB)

### Capture Before Building Prototype

Run these tests on the **current ChromaDB system** to establish baseline:

#### Test 1: Context Coherence (Granularity Problem)

**Test Queries** (10 queries):
```
1. "What is Barbara's educational background?"
2. "Tell me about the Resume Graph Explorer project"
3. "What is Barbara's approach to knowledge graphs?"
4. "Explain the Digital Twin architecture"
5. "What skills does Barbara demonstrate in her projects?"
6. "Describe Barbara's dissertation research"
7. "What makes the Poolula Platform distinctive?"
8. "How does Barbara approach problem-solving?"
9. "What certifications does Barbara have?"
10. "Tell me about the Beehive Monitor project"
```

**Measurement**:
For each query, manually score retrieved chunks on coherence:

| Score | Definition | Example |
|-------|-----------|---------|
| **5** | Complete, coherent section with full context | Entire "Education" section returned intact |
| **4** | Mostly complete, minor fragmentation | 90% of section, one small chunk missing |
| **3** | Multiple chunks but requires stitching | 3-4 related chunks from same section |
| **2** | Fragments from different sections | Chunks from bio + projects mixed |
| **1** | Incoherent or wrong content | Unrelated chunks returned |

**Baseline Target**: Average score ~2.5-3.0 (based on known fragmentation issues)

---

#### Test 2: Relationship Traversal (Missing Connections)

**Test Queries** (8 relationship queries):
```
1. "Which projects use knowledge graphs?"
2. "What other projects use similar methods to Resume Explorer?"
3. "Show me all projects that use Neo4j"
4. "Which projects demonstrate data visualization skills?"
5. "Find projects that use evaluation harnesses"
6. "What projects involve natural language processing?"
7. "Which projects use Streamlit?"
8. "Show me projects related to beekeeping"
```

**Measurement**:
For each query, test if ChromaDB can answer it:

- **✅ Success**: Answer contains correct projects via semantic search
- **⚠️ Partial**: Answer mentions some but misses others
- **❌ Failure**: Cannot traverse relationships, answers generically or incorrectly

**Expected Baseline**: 0-20% success rate (these are explicitly relationship queries that vector search struggles with)

---

#### Test 3: Ranking Quality (Poor Ranking Problem)

**Test Queries** (15 factual questions from eval suite):
```
Use V3-001 through V3-015 from eval_questions.csv
(Bio and project questions with clear ground truth)
```

**Measurement**:
- **Top-1 Precision**: Does the #1 retrieved chunk contain the answer? (% yes)
- **Top-3 Precision**: Do any of top-3 chunks contain the answer? (% yes)
- **MRR (Mean Reciprocal Rank)**: Average of 1/rank where answer first appears

**Formula**:
```
MRR = (1/N) * Σ(1/rank_i)

where rank_i is the position (1-10) where correct answer first appears
```

**Expected Baseline**:
- Top-1: ~60%
- Top-3: ~85%
- MRR: ~0.75

---

#### Test 4: Retrieval Latency

**Measurement**:
Run 20 random queries, measure time from query → retrieved chunks

**Metric**: p50, p95, p99 latency

**Expected Baseline**:
- p50: ~150ms (local ChromaDB)
- p95: ~300ms
- p99: ~500ms

---

#### Test 5: Existing Eval Suite Baseline

**Measurement**:
Run the full eval suite (50 questions):
```bash
cd evals
python run_evals.py
python analyze_evals.py
```

**Metrics**:
- Overall pass rate
- Category-wise pass rates (bio, projects, technical, personality)
- Flagged failures

**Expected Baseline**: ~85-90% pass rate (based on existing system quality)

---

## Prototype Metrics (Neo4j)

After building the Neo4j prototype with 3 documents, run the **same 5 test batteries**.

### Expected Improvements

| **Test** | **ChromaDB Baseline** | **Neo4j Target** | **Improvement** |
|----------|----------------------|-----------------|----------------|
| **Context Coherence** | 2.5-3.0 (fragmented) | 4.0-4.5 (full sections) | **+40-60% improvement** |
| **Relationship Queries** | 0-20% success | 75-100% success | **New capability unlocked** |
| **Top-1 Precision** | 60% | 75-80% | **+15-20 percentage points** |
| **MRR** | 0.75 | 0.85-0.90 | **+13-20% relative** |
| **Latency (p95)** | 300ms | 350-450ms | **Slight increase, acceptable** |
| **Eval Suite Pass Rate** | 85-90% | ≥85% (no regression) | **Maintained** |

---

## Test Queries

### Category 1: Granularity Tests (10 queries)

These test whether Neo4j returns complete sections vs. fragmented chunks.

```python
GRANULARITY_TESTS = [
    {
        "query": "What is Barbara's educational background?",
        "expected_section": "Education",
        "expected_source": "kb_biosketch",
        "must_contain": ["UT Austin", "MIT", "Electrical Engineering", "Biology", "cognitive science"],
        "coherence_target": 4.5
    },
    {
        "query": "Tell me about the Resume Graph Explorer project",
        "expected_section": "Resume Graph Explorer",
        "expected_source": "featured_projects",
        "must_contain": ["SKOS", "ESCO", "knowledge graph", "semantic standards"],
        "coherence_target": 4.5
    },
    {
        "query": "Describe Barbara's dissertation research",
        "expected_section": "Dissertation",
        "expected_source": "kb_biosketch",
        "must_contain": ["MIT", "visual attention", "eye movements", "computational models"],
        "coherence_target": 4.5
    },
    # Add 7 more...
]
```

**Measurement**:
1. Run query through both systems (ChromaDB and Neo4j)
2. For each result, score coherence (1-5)
3. Check if `must_contain` keywords are present
4. Calculate average coherence score

**Success**: Neo4j avg coherence ≥4.0 (vs ChromaDB ~2.5-3.0)

---

### Category 2: Relationship Traversal Tests (8 queries)

These test whether Neo4j can answer graph-based queries.

```python
RELATIONSHIP_TESTS = [
    {
        "query": "Which projects use knowledge graphs?",
        "expected_projects": ["Resume Graph Explorer", "Weaving Memories Into Graphs",
                              "Academic Citation Platform", "Concept Cartographer"],
        "query_type": "skill_to_projects",
        "cypher_pattern": "(skill:Skill {name: 'Knowledge Graphs'})<-[:DEMONSTRATES]-(project:Project)"
    },
    {
        "query": "What projects use Neo4j?",
        "expected_projects": ["Weaving Memories Into Graphs", "Academic Citation Platform"],
        "query_type": "technology_to_projects",
        "cypher_pattern": "(tech:Technology {name: 'Neo4j'})<-[:USES_TECHNOLOGY]-(project:Project)"
    },
    {
        "query": "Which projects are similar to Resume Explorer?",
        "expected_projects": ["Concept Cartographer", "ChronoScope", "Weaving Memories Into Graphs"],
        "query_type": "project_similarity",
        "cypher_pattern": "(p1:Project {id: 'resume-graph-explorer'})-[:USES_METHOD]->(m:Method)<-[:USES_METHOD]-(p2:Project)"
    },
    # Add 5 more...
]
```

**Measurement**:
1. Run query through both systems
2. ChromaDB: Check if answer mentions expected projects (likely fails or is incomplete)
3. Neo4j: Run corresponding Cypher query, check if results match expected
4. Score: ✅ Success, ⚠️ Partial, ❌ Failure

**Success**: Neo4j ≥75% success rate (ChromaDB expected ~0-20%)

---

### Category 3: Ranking Quality Tests (15 queries)

Use existing eval questions (V3-001 through V3-015) to test if ranking improves.

```python
RANKING_TESTS = [
    # From eval_questions.csv
    "What undergraduate degrees did you earn?",
    "What honors program were you part of at UT Austin?",
    "Where did you do your PhD?",
    "What was your dissertation about?",
    "What certifications do you have?",
    "Walk me through a project",
    "How was this digital twin built?",
    "What problems does Barbara solve?",
    "Tell me about your knowledge graph work",
    # ... 6 more
]
```

**Measurement**:
1. For each query, retrieve top-10 results from both systems
2. Manually identify which rank (1-10) contains the answer
3. Calculate Top-1, Top-3, MRR for each system

**Success**: Neo4j Top-1 ≥75% (vs ChromaDB ~60%), MRR ≥0.85 (vs ~0.75)

---

### Category 4: Hybrid Tests (Combining Multiple Signals)

These test the composite ranking (vector + graph signals).

```python
HYBRID_TESTS = [
    {
        "query": "What makes Barbara's RAG projects distinctive?",
        "expected_signals": {
            "vector_match": ["RAG", "retrieval", "embeddings"],
            "project_boost": ["Digital Twin", "Poolula Platform"],
            "entity_richness": True  # Should mention multiple projects/methods
        }
    },
    {
        "query": "Tell me about Barbara's evaluation approach",
        "expected_signals": {
            "vector_match": ["evaluation", "metrics", "testing"],
            "method_boost": ["Evaluation harness", "Offline eval"],
            "cross_project": True  # Should cite multiple projects with evals
        }
    },
    # Add 3 more...
]
```

**Measurement**:
1. Check if top results demonstrate multi-signal ranking
2. Verify that sections describing projects rank higher than mentions
3. Verify entity-rich sections get boosted

**Success**: Qualitative assessment that Neo4j uses graph structure effectively

---

## Success Criteria

### Must-Have (Go/No-Go for Full Migration)

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| **Context Coherence** | Avg ≥4.0/5.0 | Manual scoring on 10 granularity tests |
| **Relationship Queries** | ≥75% success | 8 relationship tests, % that return correct projects |
| **No Critical Regression** | 0 failures | All questions that worked in ChromaDB still work |
| **Eval Suite Pass Rate** | ≥85% | Run full eval suite on prototype dataset |

**Decision**: If all 4 criteria met → **Proceed with full migration**

---

### Should-Have (Validates Approach Quality)

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| **Top-1 Precision** | ≥75% | 15 ranking tests, % where answer is in top result |
| **MRR** | ≥0.85 | Mean reciprocal rank across ranking tests |
| **Latency p95** | <500ms | 20 queries, 95th percentile response time |

**Decision**: If 2+ criteria met → **Strong confidence in approach**

---

### Nice-to-Have (Extra Validation)

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| **Graph Connectivity** | ≥80% nodes connected | % of nodes with ≥1 relationship |
| **Entity Extraction Accuracy** | ≥90% | Manual review of extracted skills/methods |
| **Query Explainability** | Qualitative | Can we explain why results rank the way they do? |

---

## Measurement Methodology

### Phase 1: Capture ChromaDB Baseline

**Time**: 2-3 hours

1. **Granularity Tests** (30 min):
   - Run 10 granularity queries through current system
   - For each, retrieve top-5 chunks
   - Score coherence (1-5) and note fragmentation
   - Save results to `baseline_granularity.json`

2. **Relationship Tests** (30 min):
   - Run 8 relationship queries
   - Manually check if answers contain expected projects
   - Score: ✅ Success, ⚠️ Partial, ❌ Failure
   - Save results to `baseline_relationships.json`

3. **Ranking Tests** (45 min):
   - Run 15 factual questions
   - For each, examine top-10 chunks
   - Mark rank where answer first appears (1-10 or "not found")
   - Calculate Top-1, Top-3, MRR
   - Save results to `baseline_ranking.json`

4. **Latency Benchmark** (15 min):
   - Run 20 random queries, measure retrieval time
   - Calculate p50, p95, p99
   - Save results to `baseline_latency.json`

5. **Eval Suite Baseline** (30 min):
   ```bash
   cd evals
   python run_evals.py --category bio --category projects
   python analyze_evals.py --export
   mv eval_results/latest.json eval_results/baseline_chromadb.json
   ```

**Deliverables**:
- `baseline_granularity.json`
- `baseline_relationships.json`
- `baseline_ranking.json`
- `baseline_latency.json`
- `baseline_chromadb.json` (full eval run)

---

### Phase 2: Build Neo4j Prototype

**Time**: 4-6 hours (see implementation section below)

1. Set up Neo4j (Docker or Aura)
2. Extract entities from 3 documents
3. Populate graph with nodes and relationships
4. Create vector index on section embeddings
5. Implement query function with hybrid ranking

**Deliverables**:
- Running Neo4j database with ~100 nodes
- `neo4j_prototype_query.py` script
- Sample Cypher queries documented

---

### Phase 3: Measure Neo4j Prototype

**Time**: 2-3 hours

Run the **exact same tests** as Phase 1, using Neo4j instead of ChromaDB:

1. **Granularity Tests** → `neo4j_granularity.json`
2. **Relationship Tests** → `neo4j_relationships.json`
3. **Ranking Tests** → `neo4j_ranking.json`
4. **Latency Benchmark** → `neo4j_latency.json`
5. **Eval Suite** → `neo4j_eval.json`

---

### Phase 4: Comparative Analysis

**Time**: 1 hour

Create comparison report:

```python
# scripts/compare_chromadb_vs_neo4j.py

import json
import pandas as pd

def load_results(system_name):
    return {
        'granularity': json.load(open(f'{system_name}_granularity.json')),
        'relationships': json.load(open(f'{system_name}_relationships.json')),
        'ranking': json.load(open(f'{system_name}_ranking.json')),
        'latency': json.load(open(f'{system_name}_latency.json')),
    }

chromadb = load_results('baseline')
neo4j = load_results('neo4j')

comparison = pd.DataFrame({
    'Metric': ['Coherence Score', 'Relationship Success %', 'Top-1 Precision', 'MRR', 'p95 Latency (ms)'],
    'ChromaDB': [
        chromadb['granularity']['avg_coherence'],
        chromadb['relationships']['success_rate'],
        chromadb['ranking']['top1_precision'],
        chromadb['ranking']['mrr'],
        chromadb['latency']['p95']
    ],
    'Neo4j': [
        neo4j['granularity']['avg_coherence'],
        neo4j['relationships']['success_rate'],
        neo4j['ranking']['top1_precision'],
        neo4j['ranking']['mrr'],
        neo4j['latency']['p95']
    ],
    'Target': [4.0, 75.0, 75.0, 0.85, 500.0],
})

comparison['Improvement'] = comparison['Neo4j'] - comparison['ChromaDB']
comparison['Target Met'] = comparison['Neo4j'] >= comparison['Target']

print(comparison.to_markdown(index=False))
comparison.to_csv('neo4j_vs_chromadb_comparison.csv')
```

**Deliverables**:
- `neo4j_vs_chromadb_comparison.csv`
- `PROTOTYPE_EVALUATION_REPORT.md` (narrative summary)

---

## Decision Framework

After Phase 4 analysis, use this decision tree:

```
┌─────────────────────────────────────────────────┐
│ All 4 Must-Have Criteria Met?                  │
│ - Coherence ≥4.0                                │
│ - Relationship success ≥75%                     │
│ - No critical regressions                       │
│ - Eval pass rate ≥85%                           │
└────────────┬────────────────────────────────────┘
             │
             ├─ YES ──→ ✅ Proceed with Full Migration
             │           - Move to Phase 2-6 of main roadmap
             │           - Extract all 16 KB sources
             │           - Production deployment
             │
             └─ NO ──→ Investigate Failure Mode
                       │
                       ├─ Coherence Failed (<4.0)
                       │  → Section splitting logic needs work
                       │  → Review embedding strategy
                       │
                       ├─ Relationships Failed (<75%)
                       │  → Entity extraction quality issue
                       │  → Review Cypher query patterns
                       │
                       ├─ Critical Regression
                       │  → Identify which queries broke
                       │  → Determine if fixable or fundamental
                       │
                       └─ Eval Suite Regression (<85%)
                          → Compare specific failures
                          → Determine if prompt changes needed
```

### If Prototype Fails

**Do NOT abandon** — iterate:

1. **Analyze which criterion failed**
2. **Identify root cause**:
   - Entity extraction errors?
   - Cypher query bugs?
   - Ranking weight tuning needed?
   - Section boundary issues?
3. **Make targeted fix**
4. **Re-run evaluation** (Phases 2-4)
5. **Re-assess with decision framework**

**Iteration budget**: 2-3 cycles before reconsidering approach

---

## Appendix: Test Scripts

### Script 1: Granularity Test Runner

```python
# evals/test_granularity.py

import json
from typing import List, Dict

GRANULARITY_QUERIES = [
    {
        "query": "What is Barbara's educational background?",
        "expected_section": "Education",
        "must_contain": ["UT Austin", "MIT", "Electrical Engineering", "Biology"],
    },
    # ... 9 more
]

def score_coherence(retrieved_chunks: List[str]) -> float:
    """
    Score 1-5 based on coherence.

    5 = Complete section, no fragmentation
    4 = Mostly complete, minor gaps
    3 = Multiple related chunks, requires stitching
    2 = Fragmented across different sections
    1 = Incoherent or wrong content
    """
    # TODO: Implement scoring logic
    # For prototype, manual scoring is fine
    return float(input(f"Score coherence (1-5): "))

def test_granularity_chromadb():
    """Run granularity tests on ChromaDB baseline."""
    results = []

    for test in GRANULARITY_QUERIES:
        # Query ChromaDB
        retrieved = query_chromadb(test['query'], k=5)

        # Score coherence
        score = score_coherence(retrieved)

        # Check must_contain
        text = " ".join(retrieved)
        coverage = sum(1 for kw in test['must_contain'] if kw.lower() in text.lower())

        results.append({
            "query": test['query'],
            "coherence_score": score,
            "keyword_coverage": coverage / len(test['must_contain']),
            "retrieved_chunks": retrieved
        })

    avg_coherence = sum(r['coherence_score'] for r in results) / len(results)

    output = {
        "avg_coherence": avg_coherence,
        "results": results
    }

    with open('baseline_granularity.json', 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Average Coherence: {avg_coherence:.2f}")
```

### Script 2: Relationship Test Runner

```python
# evals/test_relationships.py

RELATIONSHIP_QUERIES = [
    {
        "query": "Which projects use knowledge graphs?",
        "expected_projects": ["Resume Graph Explorer", "Weaving Memories",
                              "Academic Citation Platform", "Concept Cartographer"],
    },
    # ... 7 more
]

def test_relationships_neo4j():
    """Run relationship traversal tests on Neo4j."""
    results = []

    for test in RELATIONSHIP_QUERIES:
        # Query Neo4j with Cypher
        found_projects = query_neo4j_relationships(test['query'])

        # Check if found projects match expected
        expected_set = set(test['expected_projects'])
        found_set = set(found_projects)

        precision = len(expected_set & found_set) / len(found_set) if found_set else 0
        recall = len(expected_set & found_set) / len(expected_set)

        if precision >= 0.9 and recall >= 0.9:
            status = "✅ Success"
        elif precision >= 0.5 and recall >= 0.5:
            status = "⚠️ Partial"
        else:
            status = "❌ Failure"

        results.append({
            "query": test['query'],
            "expected": list(expected_set),
            "found": list(found_set),
            "precision": precision,
            "recall": recall,
            "status": status
        })

    success_rate = sum(1 for r in results if r['status'] == "✅ Success") / len(results) * 100

    output = {
        "success_rate": success_rate,
        "results": results
    }

    with open('neo4j_relationships.json', 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Relationship Query Success Rate: {success_rate:.1f}%")
```

---

**End of Evaluation Plan**

Next Step: Run Phase 1 (Capture ChromaDB Baseline) before building the prototype.
