# Architecture Flow Diagrams — Digital Twin Project

## Flow 1: Knowledge Ingestion Orchestration (`scripts/ingest.py`)
Shows how source-specific embedding scripts are orchestrated into one persistent ChromaDB collection.

```mermaid
---
id: f7f8df7a-5df4-43e2-a7f2-73732fef7f71
title: "Flow 1: Knowledge Ingestion Orchestration"
---
graph TD
    Start([Maintainer: Run ingest workflow]) --> IngestCLI["scripts/ingest.py<br/>interactive menu OR --source/--all flags"]

    IngestCLI --> SourceRegistry{"Resolve source registry<br/>SOURCES[]"}
    SourceRegistry --> KB["scripts/embed_kb_doc.py<br/>section-aware markdown parsing"]
    SourceRegistry --> PDFs["scripts/embed_project_summaries.py<br/>project summary PDFs"]
    SourceRegistry --> Jekyll["scripts/embed_jekyll.py<br/>website pages via sitemap"]
    SourceRegistry --> Walkthroughs["scripts/embed_walkthroughs.py<br/>featured project contexts"]

    KB --> Chunking["utils.py chunking helpers<br/>paragraph-aware chunks + overlap"]
    PDFs --> Chunking
    Jekyll --> Chunking
    Walkthroughs --> Chunking

    Chunking --> Embeddings["OpenAI embeddings client<br/>text-embedding-3-small"]
    Embeddings --> ChromaWrite["ChromaDB collection: barb-twin<br/>metadata: source/section/chunk_index"]
    ChromaWrite --> End([Collection updated incrementally])

    IngestCLI -. status/audit .-> Verify["scripts/verify_collection.py<br/>source counts + sample chunks"]
    IngestCLI -. cleanup .-> Clear["scripts/clear_collection.py<br/>wipe collection when needed"]

    style IngestCLI fill:#e1f5ff
    style Chunking fill:#fff4e1
    style ChromaWrite fill:#d4e8ff
    style Verify fill:#e8f5e8
```

## Flow 2: Runtime Query + RAG Generation (`app.py`)
Shows the public twin request path from user message to grounded response.

```mermaid
---
id: 1160ccb5-a7f1-4c50-aedb-c17e32d32f2f
title: "Flow 2: Runtime Query + RAG Generation"
---
graph TD
    User([Visitor asks a question]) --> UI["Gradio ChatInterface<br/>app.py"]

    UI --> Tier{"Audience tier detection<br/>detect_audience_tier()"}
    Tier --> Sensitivity["build_sensitivity_filter()<br/>public/personal/inner_circle"]

    UI --> QEmbed["OpenAI embeddings client<br/>embed user query"]
    Sensitivity --> Retrieve["ChromaDB query<br/>top-K retrieval + optional where filter"]
    QEmbed --> Retrieve

    Retrieve --> Context["Context builder<br/>SYSTEM_PROMPT + retrieved chunks + history"]
    Context --> LLM["LiteLLM completion<br/>multi-provider model routing"]

    LLM --> ToolCheck{"Tool call requested?"}
    ToolCheck -->|Yes| Tools["handle_tool_call()<br/>Pushover notify, dice_roll"]
    Tools --> LLM
    ToolCheck -->|No| Response["Assistant response as Barbara"]

    Response --> Log["JSONL query logging<br/>latency, model, retrieval stats"]
    Log --> End([Answer returned to user])

    style UI fill:#e1f5ff
    style Retrieve fill:#fff4e1
    style LLM fill:#ffe8f5
    style Tools fill:#e8f5e8
```

## Flow 3: Project Walkthrough + Diagram Injection (`featured_projects.py`)
Shows how project mentions trigger richer walkthrough context and optional diagram rendering.

```mermaid
---
id: 7f67b7ad-6118-47c7-bcc4-31bbc9d4a8b6
title: "Flow 3: Project Walkthrough + Diagram Injection"
---
graph LR
    Msg([Incoming user message]) --> MentionCheck["find_mentioned_project()<br/>keyword + tag matching"]
    Msg --> WalkthroughCheck["select_project_for_walkthrough()<br/>walkthrough intent detection"]

    MentionCheck -->|Project found| Diagram["get_diagram_path()<br/>assets/project_diagrams/*.png"]
    WalkthroughCheck -->|Walkthrough intent| ContextBlock["build_walkthrough_context_block()<br/>architecture/story context"]

    Diagram --> PromptAugment["App-level prompt assembly<br/>diagram + project summary"]
    ContextBlock --> PromptAugment

    PromptAugment --> LLMResp["LLM response generation<br/>grounded in project metadata"]
    LLMResp --> Out([User gets answer with optional visual context])

    style MentionCheck fill:#e1f5ff
    style WalkthroughCheck fill:#e1f5ff
    style Diagram fill:#fff4e1
    style ContextBlock fill:#e8f5e8
```

## Layered Architecture (Current Digital Twin)
Shows the current 4-layer dependency structure before the planned GraphRAG migration.

```mermaid
---
id: 4d1f45bd-91db-4fa0-8e5a-4ecb53405f7c
title: "Layered Architecture — Digital Twin"
---
graph TB
    subgraph UX["INTERFACE LAYER"]
        A1[app.py — public chat]
        A2[app_admin.py — local debug/admin]
        A3[dashboard/app.py — analytics dashboard]
    end

    subgraph ORCH["ORCHESTRATION LAYER"]
        O1[scripts/ingest.py]
        O2[featured_projects.py]
        O3[scripts/analyze_logs.py]
        O4[evals/run_evals.py]
    end

    subgraph DOMAIN["DOMAIN LOGIC LAYER"]
        D1[retrieval + context assembly in app.py]
        D2[sensitivity gating + policy logic]
        D3[chunking/section parsing helpers in utils.py]
        D4[analytics/sessionization + metrics]
    end

    subgraph INFRA["INFRASTRUCTURE LAYER"]
        I1[ChromaDB persistent store (.chroma_db_DT)]
        I2[Embedding API client (OpenAI)]
        I3[LLM provider abstraction (LiteLLM)]
        I4[File-based logs (JSONL)]
        I5[HF Hub sync (db_sync.py)]
    end

    A1 --> O2
    A1 --> D1
    A2 --> D1
    A3 --> D4

    O1 --> D3
    O3 --> D4
    O4 --> D1

    D1 --> I1
    D1 --> I2
    D1 --> I3
    D1 --> I4

    O1 --> I1
    O1 --> I2
    O1 --> I5

    D4 --> I4

    style UX fill:#e1f5ff
    style ORCH fill:#e8f5e8
    style DOMAIN fill:#fff4e1
    style INFRA fill:#f0f0f0
```

## Module Interaction Matrix (Current State)
Shows high-level module coupling and call directions.

```mermaid
---
id: 14c53de4-03f9-4cc0-87f8-536f66f3118c
title: "Module Interaction Matrix — Digital Twin"
---
graph LR
    subgraph Apps["Applications"]
        APP[app.py]
        ADM[app_admin.py]
        DAS[dashboard/app.py]
    end

    subgraph Ingestion["Ingestion & KB Build"]
        ING[scripts/ingest.py]
        EKB[scripts/embed_kb_doc.py]
        EPR[scripts/embed_project_summaries.py]
        EJK[scripts/embed_jekyll.py]
        EWK[scripts/embed_walkthroughs.py]
    end

    subgraph Data["Data & Utility"]
        UTL[utils.py]
        FP[featured_projects.py]
        DBS[db_sync.py]
    end

    subgraph Ops["Ops / Quality"]
        VER[scripts/verify_collection.py]
        CLR[scripts/clear_collection.py]
        EVL[evals/run_evals.py]
        ANL[scripts/analyze_logs.py]
    end

    APP --> FP
    APP --> UTL
    APP --> DBS

    ADM --> FP
    ADM --> UTL

    ING --> EKB
    ING --> EPR
    ING --> EJK
    ING --> EWK
    ING --> VER
    ING --> CLR

    EKB --> UTL
    EPR --> UTL
    EJK --> UTL
    EWK --> FP

    EVL --> APP
    ANL --> DAS

    style APP fill:#e1f5ff
    style ADM fill:#e1f5ff
    style ING fill:#e8f5e8
    style UTL fill:#fff4e1
    style FP fill:#fff4e1
```

## GraphRAG Migration Staging View (Planned Next Step)
Provides a parallel bridge from current Chroma-only RAG toward hybrid graph + vector retrieval.

```mermaid
---
id: 3805f5f3-7999-462a-9415-261dfed92e6a
title: "GraphRAG Migration Staging View"
---
graph TD
    Current["Current State<br/>Chroma-only semantic retrieval"] --> Stage1

    Stage1{"Stage 1: Canonical entity extraction"}
    Stage1 --> S1A["Extract entities/relations from KB chunks"]
    Stage1 --> S1B["Store provenance per entity mention"]

    S1A --> Stage2
    S1B --> Stage2

    Stage2{"Stage 2: Graph persistence"}
    Stage2 --> S2A["Materialize nodes/edges in graph DB"]
    Stage2 --> S2B["Add constraints + graph indexes"]

    S2A --> Stage3
    S2B --> Stage3

    Stage3{"Stage 3: Hybrid retrieval"}
    Stage3 --> S3A["Vector seeds from Chroma"]
    Stage3 --> S3B["Neighborhood expansion in graph"]
    S3A --> S3C["Merge + rerank context"]
    S3B --> S3C

    S3C --> Target["Target State<br/>GraphRAG digital twin"]

    style Current fill:#fff4e1
    style Target fill:#e1f5ff
    style Stage1 fill:#f0f0f0
    style Stage2 fill:#f0f0f0
    style Stage3 fill:#f0f0f0
```
