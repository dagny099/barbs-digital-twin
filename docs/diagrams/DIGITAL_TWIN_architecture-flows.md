# Architecture Flow Diagrams — Barbara's Digital Twin

## Flow 1: Runtime RAG Conversation (Public App)
Shows the end-to-end runtime path from user message to grounded reply in Barbara's voice.

```mermaid
---
id: 13fa7b3a-dtw-01
title: "Flow 1: Runtime RAG Conversation (app.py)"
---
graph TD
    Start([Visitor sends message]) --> Chat[app.py<br/>chatbot_response]

    Chat --> Tier[detect_audience_tier<br/>scan current + historical user turns]
    Tier --> Filter[build_sensitivity_filter<br/>public/personal/inner_circle gating]

    Chat --> QEmbed[OpenAI embeddings API<br/>embed incoming query]
    QEmbed --> Retrieve[ChromaDB collection.query<br/>top-K semantic retrieval]
    Filter --> Retrieve

    Retrieve --> Context[Build prompt context<br/>SYSTEM_PROMPT + retrieved chunks + user query]

    Context --> LLM[LiteLLM completion<br/>multi-provider model via LLM_MODEL]

    LLM --> ToolGate{Tool call requested?}
    ToolGate -->|Yes| ToolExec[handle_tool_call<br/>pushover / dice_roll / helpers]
    ToolExec --> LLM
    ToolGate -->|No| Final[Return assistant response]

    Final --> VoteLog[handle_vote + query logging<br/>quality + telemetry artifacts]

    style Chat fill:#e1f5ff
    style Retrieve fill:#fff4e1
    style LLM fill:#ffe8f5
    style ToolExec fill:#e8fbe8
    style Filter fill:#f0f0f0
```

## Flow 2: Knowledge Ingestion Orchestration
Shows how the ingestion manager routes many sources through specialized embedding scripts into ChromaDB.

```mermaid
---
id: 13fa7b3a-dtw-02
title: "Flow 2: Ingestion Orchestration (scripts/ingest.py)"
---
graph TD
    Start([Maintainer runs ingest]) --> Entry[scripts/ingest.py<br/>interactive menu or --all/--source]

    Entry --> Registry[SOURCES registry<br/>key, label, script, args, source_prefix]

    Registry --> Branch{Source family}

    Branch -->|KB markdown / project summaries| KBEmbed[scripts/embed_kb_doc.py<br/>parse ## sections + chunk prose]
    Branch -->|Project walkthrough contexts| WalkEmbed[scripts/embed_walkthroughs.py]
    Branch -->|Jekyll website| JekyllEmbed[scripts/embed_jekyll.py]
    Branch -->|Project docs set| ProjEmbed[scripts/embed_project_summaries.py]

    KBEmbed --> Embed[OpenAI text-embedding-3-small]
    WalkEmbed --> Embed
    JekyllEmbed --> Embed
    ProjEmbed --> Embed

    Embed --> Store[ChromaDB upsert<br/>metadata: source/section/chunk_index/content_hash/sensitivity]
    Store --> Status[ingest.py status table + drift checks]

    style Entry fill:#e1f5ff
    style Registry fill:#f0f0f0
    style Embed fill:#ffe8f5
    style Store fill:#fff4e1
```

## Flow 3: Section-Aware Document Embedding
Shows the internal transformation pipeline for one structured markdown source.

```mermaid
---
id: 13fa7b3a-dtw-03
title: "Flow 3: Section-Aware Embedding (scripts/embed_kb_doc.py)"
---
graph TD
    Start([Input file + source_type]) --> Load[Read file bytes + decode text]
    Load --> Hash[Compute sha256 content_hash]

    Hash --> Parse[parse_markdown_sections<br/>H2 sections with nested merge]
    Parse --> Chunk[chunk_prose + merge_tiny_chunks<br/>chunk size/overlap env-configured]

    Chunk --> Meta[build_metadata<br/>source, section, chunk_index, sensitivity, content_hash]
    Meta --> Batch[Batch chunks for embedding API]
    Batch --> Embed[OpenAI embeddings.create]
    Embed --> Upsert[collection.add / upsert to ChromaDB]

    Upsert --> End([Source embedded + retrievable])

    style Parse fill:#e8f5e8
    style Chunk fill:#fff4e1
    style Embed fill:#ffe8f5
    style Upsert fill:#e1f5ff
```

## Flow 4: Admin Debug + Retrieval Inspector
Shows the admin-only path that combines response generation with observability and diagnostics.

```mermaid
---
id: 13fa7b3a-dtw-04
title: "Flow 4: Admin Debug Flow (app_admin.py)"
---
graph TD
    Start([Admin submits prompt]) --> Auth{ADMIN_PASSWORD set?}
    Auth -->|Yes| Gate[Basic auth gate]
    Auth -->|No| Gate

    Gate --> Chat[app_admin.py chat handler]
    Chat --> Tier[detect_audience_tier + build_sensitivity_filter]
    Chat --> Search[Chroma query + retrieved chunk preview]

    Search --> Stats[_compute_similarity_stats<br/>L2 distance -> cosine-like stats]
    Search --> LLM[LiteLLM completion]

    LLM --> Tool{Tool call?}
    Tool -->|Yes| Exec[handle_tool_call]
    Exec --> LLM
    Tool -->|No| Output[Rendered answer + inspector panel]

    Output --> AdminLog[_log_admin_query<br/>latency, model, tokens, cost, similarity stats]

    style Chat fill:#e1f5ff
    style Search fill:#fff4e1
    style Stats fill:#f0f0f0
    style AdminLog fill:#ffe8f5
```

## Layered Architecture
Shows a parallel layered view of the current digital twin codebase, analogous to the GraphRAG project's layer map.

```mermaid
---
id: 13fa7b3a-dtw-05
title: "Layered Architecture Diagram (Digital Twin)"
---
graph TB
    subgraph UI["INTERFACE LAYER"]
        U1[app.py - public chat UI]
        U2[app_admin.py - debug/admin UI]
        U3[dashboard/app.py - analytics dashboard]
    end

    subgraph ORCH["ORCHESTRATION LAYER"]
        O1[scripts/ingest.py - source routing + status]
        O2[featured_projects.py - walkthrough selection]
        O3[scripts/analyze_logs.py / analytics workflows]
    end

    subgraph DOMAIN["DOMAIN LOGIC LAYER"]
        D1[utils.py - chunking, section parsing, metadata helpers]
        D2[scripts/embed_kb_doc.py - structured KB embedding]
        D3[scripts/embed_jekyll.py - website ingestion]
        D4[scripts/embed_walkthroughs.py - project context embedding]
    end

    subgraph INFRA["INFRASTRUCTURE LAYER"]
        I1[ChromaDB (.chroma_db_DT)]
        I2[OpenAI embeddings client]
        I3[LiteLLM provider abstraction]
        I4[query logs + admin logs + telemetry scripts]
        I5[db_sync.py - HF Hub backup/restore]
    end

    U1 --> O2
    U1 --> I3
    U1 --> I1
    U2 --> I3
    U2 --> I1
    U2 --> I4
    U3 --> I4

    O1 --> D2
    O1 --> D3
    O1 --> D4
    O1 --> I1
    O1 --> I2

    D2 --> I2
    D2 --> I1
    D3 --> I2
    D3 --> I1
    D4 --> I2
    D4 --> I1
    D1 --> D2
    D1 --> D3

    I1 --> I5

    style UI fill:#e1f5ff
    style ORCH fill:#e8f5e8
    style DOMAIN fill:#fff4e1
    style INFRA fill:#f0f0f0
```
