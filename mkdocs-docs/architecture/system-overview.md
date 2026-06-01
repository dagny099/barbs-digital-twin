---
title: System Overview
tags:
  - architecture
  - graphrag
  - neo4j
---

# System Overview

Barbara's digital twin is a GraphRAG system — retrieval-augmented generation backed by a Neo4j knowledge graph. This page covers the full retrieval pipeline, from user query to streamed response.

---

## Retrieval Pipeline

```mermaid
flowchart TD
    A(["👤 User Query"]) --> B["Gradio Interface\napp.py"]
    B --> C["Tier Detection\ndetect_audience_tier()"]
    C --> D["OpenAI Embedding\ntext-embedding-3-small\n1536 dimensions"]

    D --> E["Neo4j Hybrid Search\nvector index · graph signals\nallowed_tiers filter"]
    D -.->|"fallback / A/B eval"| L[("ChromaDB\npure vector")]

    E --> F["Composite Scoring\nWt_SEMANTIC × 0.85\n+ project link × 0.08\n+ entity mentions × 0.05\n+ section length × 0.02"]
    F --> G["Top-K Sections\n(fetch_k = k × 4 → rerank → top k)"]

    G --> H["Context Injection\nSYSTEM_PROMPT.md\n+ Retrieved Sections"]
    H --> I["LiteLLM Completion\nOpenAI · Anthropic · Google · Ollama"]
    I --> J{Tool Call\nNeeded?}
    J -->|"Yes"| K["Execute Tool\nsend_notification\ndice_roll"]
    K --> I
    J -->|"No"| M(["🗣️ Streamed Response\nas Barbara"])

    style A fill:#e8f4f8,stroke:#2196F3
    style M fill:#e8f8e8,stroke:#4CAF50
    style F fill:#fff8e1,stroke:#FFC107
    style E fill:#f3e5f5,stroke:#9C27B0
    style L fill:#f5f5f5,stroke:#9E9E9E,stroke-dasharray: 5 5
    style K fill:#e8f5e9,stroke:#4CAF50
```

---

## Data Ingestion Pipeline

```mermaid
flowchart LR
    A["Source Documents\nMD · PDF · HTML · py"] --> B["Section-Aware Parsing\n## headers → named sections"]
    B --> C["Paragraph-Aware Chunking\n≈500 chars · 50 overlap"]
    C --> D["Generate Embeddings\ntext-embedding-3-small"]

    D --> E[("ChromaDB\nfallback + A/B eval")]
    D --> F["Load Section Nodes\nNeo4j vector index"]
    F --> G[("Neo4j Graph\nDocument → Section → Entity")]

    EX["LLM Entity Extraction\nSkills · Methods · Tech · Concepts"] --> G
    A --> EX

    style D fill:#e1f5ff,stroke:#29B6F6
    style E fill:#f5f5f5,stroke:#9E9E9E
    style G fill:#f3e5f5,stroke:#9C27B0
    style EX fill:#fff8e1,stroke:#FFC107
```

---

## Key Processing Steps

1. **Parse** — `##` headers create named Section boundaries. Every chunk knows its parent section, source document, and sensitivity tier.
2. **Chunk** — Paragraph-aware splitting with configurable size (~500 chars) and overlap (50 chars). `chunk_index` resets per section, not globally.
3. **Embed** — Each section is embedded via `text-embedding-3-small` (1536 dimensions).
4. **Load** — Section nodes and embeddings are loaded into Neo4j's vector index. The same chunks are also stored in ChromaDB for fallback and A/B comparison.
5. **Entity Extraction** — An LLM extracts Skills, Methods, Technologies, and Concepts from project walkthroughs. These become 167 canonical entity nodes, connected to sections via `MENTIONS` edges. Projects link to their descriptive sections via `DESCRIBED_IN`.

---

## Neo4j Graph Schema

The graph has three primary node types:

```
(Document) -[:HAS_SECTION]-> (Section) -[:MENTIONS]-> (Entity)
(Project)  -[:DESCRIBED_IN]-> (Section)
```

- **Document** — a source file (KB doc, PDF, website page)
- **Section** — a named chunk with embedding vector and `sensitivity_tier`
- **Entity** — a canonical node (Skill, Method, Technology, Concept)
- **Project** — a named project in Barbara's portfolio

Graph connectivity is what enables the hybrid scoring: a Section linked to a Project or mentioning many Entities earns graph bonuses on top of its vector similarity score.

---

## Sensitivity Tier Gating

The `allowed_tiers` parameter is passed directly into the Cypher `WHERE` clause — no post-filter. Tier detection runs before embedding, so ineligible sections are never scored.

```python
WHERE s.sensitivity_tier IN $allowed_tiers
```

See [Passphrase & Tiers](../getting-started/tiers.md) for how tiers are detected.

---

## Deployment Architecture

```mermaid
graph TB
    subgraph "CI/CD"
        GH_MAIN["GitHub\nmain branch"]
        GHA1["GitHub Actions\ndeploy-ec2.yml"]
        GHA2["GitHub Actions\ndeploy-hf.yml"]
    end

    subgraph "Production — EC2"
        EC2["AWS EC2\nAmazon Linux 2"]
        SYS["systemd Service\ndigital-twin :7860"]
        DNS1["twin.barbhs.com"]
    end

    subgraph "Secondary — HF Spaces"
        HF["Hugging Face Space\nDocker Container"]
        DNS2["huggingface.co/spaces/..."]
    end

    GH_MAIN -->|"push to main"| GHA1
    GH_MAIN -->|"push to main"| GHA2
    GHA1 -->|"unit tests → SSH deploy"| EC2
    EC2 --> SYS
    DNS1 --> EC2
    GHA2 -->|"sync code + data"| HF
    DNS2 --> HF

    style EC2 fill:#ffd4aa,stroke:#FF9800
    style HF fill:#d4aaff,stroke:#9C27B0
```

See [EC2 Primary](../deployment/ec2-primary.md) and [HuggingFace Spaces](../deployment/huggingface-spaces.md) for setup instructions.

---

## Key Files

| File | Purpose |
|---|---|
| [`app.py`](https://github.com/dagny099/barbs-digital-twin/blob/main/app.py) | Main Gradio app — RAG pipeline, streaming, tool calls, logging |
| [`neo4j_utils.py`](https://github.com/dagny099/barbs-digital-twin/blob/main/neo4j_utils.py) | Neo4j driver, `query_neo4j_rag()`, scoring weight constants |
| [`SYSTEM_PROMPT.md`](https://github.com/dagny099/barbs-digital-twin/blob/main/SYSTEM_PROMPT.md) | Persona, voice rules, factual accuracy guardrails, tool protocols |
| [`featured_projects.py`](https://github.com/dagny099/barbs-digital-twin/blob/main/featured_projects.py) | Project walkthrough logic and diagram serving |
| [`replay_retrieval.py`](https://github.com/dagny099/barbs-digital-twin/blob/main/replay_retrieval.py) | Neo4j retrieval debugger — composite score breakdown |
| [`chunk_inspector.py`](https://github.com/dagny099/barbs-digital-twin/blob/main/chunk_inspector.py) | ChromaDB chunk quality auditor |
