# Architecture Flow Diagrams (Digital Twin Project)

## Flow 1: End-to-End Ingestion Orchestration (`scripts/ingest.py`)
Shows how curated knowledge sources are discovered, chunked, embedded, and persisted to ChromaDB.

```mermaid
---
id: 1a2d0d20-37b2-4c35-9d53-2a5e59f49c11
title: "Flow 1: End-to-End Ingestion Orchestration"
---
graph TD
    Start([Maintainer: Run ingestion]) --> IngestCLI[scripts/ingest.py<br/>interactive menu or --source/--all flags]

    IngestCLI --> Status[verify current chunk counts<br/>before writing]
    Status --> SourceSelect{Source selected?}

    SourceSelect --> SourceTypes[inputs/*.md, project PDFs,<br/>Jekyll sitemap, walkthrough content]
    SourceTypes --> EmbedEntry[scripts/embed_kb_doc.py /<br/>scripts/embed_project_summaries.py /<br/>scripts/embed_jekyll.py /<br/>scripts/embed_walkthroughs.py]

    EmbedEntry --> Parse[section-aware parsing<br/>header boundaries + provenance]
    Parse --> Chunk[paragraph-aware chunking<br/>size + overlap controls]
    Chunk --> Embed[embedding generation<br/>query/document vectors]
    Embed --> Persist[(ChromaDB collection<br/>.chroma_db_DT)]

    Persist --> Verify[scripts/verify_collection.py<br/>stats + sample chunks]
    Verify --> End([Knowledge base updated])

    IngestCLI -.-> DryRun[dry-run path<br/>preview only, no writes]
    IngestCLI -.-> Force[force re-embed path<br/>overwrite/update source vectors]

    style IngestCLI fill:#e1f5ff
    style Embed fill:#fff4e1
    style Persist fill:#d4e8ff
    style SourceSelect fill:#f0f0f0
```

## Flow 2: Public Conversation Runtime (`app.py`)
Shows the request lifecycle from visitor message to grounded answer.

```mermaid
---
id: b3f1be5c-cf49-4b89-bf11-86417d0e8bbd
title: "Flow 2: Public Conversation Runtime"
---
graph TD
    Start([Visitor sends message]) --> UI[Gradio ChatInterface<br/>app.py]
    UI --> PromptLoad[SYSTEM_PROMPT.md loaded<br/>persona + guardrails]

    PromptLoad --> QueryEmbed[embed user query]
    QueryEmbed --> Retrieve[ChromaDB semantic search<br/>top-K chunks + similarity]
    Retrieve --> ContextBuild[assemble prompt context<br/>system + retrieval + chat history]

    ContextBuild --> LLMCall[LiteLLM completion call<br/>provider/model via env]
    LLMCall --> ToolGate{Tool call requested?}

    ToolGate -->|Yes| ToolExec[handle_tool_call()<br/>notifications / dice roll]
    ToolExec --> LLMCall

    ToolGate -->|No| Answer[final response in Barbara's voice]
    Answer --> LogWrite[scripts/conversation_logger.py<br/>request/latency/cost metadata]
    LogWrite --> End([Response returned to visitor])

    Retrieve -.-> ProjectAssist[featured_projects.py<br/>project walkthrough helpers]

    style UI fill:#e1f5ff
    style Retrieve fill:#fff4e1
    style LLMCall fill:#ffe8f5
    style LogWrite fill:#e8f5e8
```

## Flow 3: Admin Debug + Retrieval Inspection (`app_admin.py`)
Shows the local-only diagnostics path for model comparison and retrieval forensics.

```mermaid
---
id: 33a10f79-1ec7-45d8-b2f9-29192a9f729d
title: "Flow 3: Admin Debug + Retrieval Inspection"
---
graph TD
    Start([Developer opens admin app]) --> AdminUI[app_admin.py<br/>local debug interface]

    AdminUI --> ProbeInput[enter test query / choose model params]
    ProbeInput --> ProbeRetrieve[run same retrieval path<br/>as production app]
    ProbeRetrieve --> ChunkInspect[chunk_inspector.py-style view<br/>source + section + similarity]

    ChunkInspect --> Compare{Compare variants?}
    Compare -->|Yes| MultiRun[run multiple model/prompt configs]
    MultiRun --> EvalNotes[save observations + failure patterns]

    Compare -->|No| SingleRun[single config trace]
    SingleRun --> EvalNotes

    EvalNotes --> AdminLogs[admin logging artifacts<br/>for offline analysis]
    AdminLogs --> End([Debug cycle completed])

    style AdminUI fill:#e1f5ff
    style ProbeRetrieve fill:#fff4e1
    style ChunkInspect fill:#ffe1e1
    style AdminLogs fill:#e8f5e8
```

## Layered Architecture (Current Digital Twin)
Shows the dependency structure from interfaces to shared infrastructure.

```mermaid
---
id: 9cd7f7db-6c6d-4ea5-bf1d-3f48aa9b4b4f
title: "Layered Architecture Diagram (Digital Twin)"
---
graph TB
    subgraph Interface["INTERFACE LAYER"]
        I1[app.py<br/>public chat]
        I2[app_admin.py<br/>admin debug]
        I3[scripts/ingest.py<br/>ingestion orchestrator]
    end

    subgraph Orchestration["ORCHESTRATION LAYER"]
        O1[featured_projects.py<br/>walkthrough routing]
        O2[scripts/embed_*.py<br/>source-specific pipelines]
        O3[scripts/verify_collection.py<br/>db verification]
        O4[chunk_inspector.py<br/>retrieval audit]
    end

    subgraph Data["DATA & RETRIEVAL LAYER"]
        D1[ChromaDB collection<br/>vectors + metadata]
        D2[inputs/*.md and PDFs<br/>source corpus]
        D3[Jekyll content ingest path]
    end

    subgraph Shared["SHARED SERVICES LAYER"]
        S1[SYSTEM_PROMPT.md<br/>response policy]
        S2[utils.py<br/>text helpers]
        S3[analytics/*<br/>session + metrics processing]
        S4[scripts/conversation_logger.py<br/>observability]
        S5[db_sync.py<br/>remote snapshot sync]
    end

    I1 --> O1
    I1 --> D1
    I1 --> S1
    I1 --> S2
    I2 --> O4
    I2 --> D1
    I3 --> O2
    I3 --> O3

    O2 --> D2
    O2 --> D3
    O2 --> D1
    O4 --> D1

    I1 --> S4
    I2 --> S4
    S4 --> S3
    D1 --> S5

    style Interface fill:#e1f5ff
    style Orchestration fill:#e8f5e8
    style Data fill:#fff4e1
    style Shared fill:#f0f0f0
```

## Module Interaction Matrix (Current State)
Highlights core modules and their primary interactions before a GraphRAG evolution.

```mermaid
---
id: d469bc8d-0fd6-42d2-9a47-82054fb5b2cf
title: "Module Interaction Matrix (Digital Twin)"
---
graph LR
    subgraph Apps["Apps"]
        A1[app.py]
        A2[app_admin.py]
    end

    subgraph Ingestion["Ingestion"]
        I1[scripts/ingest.py]
        I2[scripts/embed_kb_doc.py]
        I3[scripts/embed_project_summaries.py]
        I4[scripts/embed_jekyll.py]
        I5[scripts/embed_walkthroughs.py]
    end

    subgraph Retrieval["Retrieval & Inspection"]
        R1[ChromaDB collection]
        R2[chunk_inspector.py]
        R3[scripts/verify_collection.py]
    end

    subgraph Support["Support & Analytics"]
        S1[featured_projects.py]
        S2[utils.py]
        S3[scripts/conversation_logger.py]
        S4[analytics/log_loader.py + metrics.py + sessionize.py]
        S5[evals/run_evals.py + analyze_evals.py]
    end

    A1 --> R1
    A1 --> S1
    A1 --> S2
    A1 --> S3

    A2 --> R1
    A2 --> R2
    A2 --> S3

    I1 --> I2
    I1 --> I3
    I1 --> I4
    I1 --> I5
    I2 --> R1
    I3 --> R1
    I4 --> R1
    I5 --> R1

    R3 --> R1
    R2 --> R1

    S3 --> S4
    S5 --> A1
    S5 --> R1

    style Apps fill:#e1f5ff
    style Ingestion fill:#e8f5e8
    style Retrieval fill:#fff4e1
    style Support fill:#f0f0f0
```

## Forward-Looking Notes for "GraphRAG Makeover"
- The current flows are retrieval-first with vector similarity and metadata provenance.
- A GraphRAG transition can add an entity/concept graph expansion stage between retrieval and answer synthesis.
- Keep this file as the "baseline architecture" snapshot to compare pre/post GraphRAG behavior.
