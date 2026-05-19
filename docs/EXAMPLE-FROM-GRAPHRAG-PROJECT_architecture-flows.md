# Architecture Flow Diagrams

## Flow 1: Episode Ingestion Pipeline (Notebook 7)
Shows the complete journey from raw transcript to Neo4j graph with concepts 

```mermaid
---
id: 921edb03-dba2-4304-a87d-786031963172
title: "Flow 1: Episode Ingestion Pipeline (Notebook 7)"
---
graph TD
    Start(["User: Ingest Episode"]) --> Pipeline["pipelines/podcast_ingestion.py<br/>PodcastIngestionPipeline.ingest_episode"]

    Pipeline --> Stage1{"Stage 1:<br/>Parse"}
    Stage1 --> Parser["parsers/transcript_parser.py<br/>TranscriptParser.parse<br/>returns List segment dicts"]

    Parser --> Stage2{"Stage 2:<br/>Embed"}
    Stage2 --> Embedder["embeddings/embedder.py<br/>embed_batch<br/>adds embeddings to segments"]

    Embedder --> Stage3{"Stage 3:<br/>Load to Neo4j"}
    Stage3 --> DataLoader["graph/data_loader.py<br/>create_segment_node<br/>create_episode_node<br/>create_concept_node<br/>create_mentions_edge<br/>MERGE to Neo4j"]

    DataLoader --> SchemaBuilder["graph/schema_builder.py<br/>create_vector_index<br/>create_constraints"]

    SchemaBuilder --> Stage4{"Stage 4:<br/>Extract Concepts"}
    Stage4 --> ConceptExtractor["extraction/concept_extractor.py<br/>extract_concepts_from_segments"]

    ConceptExtractor --> LLMProvider["providers/llm_provider.py<br/>LLMProvider.generate<br/>calls OpenAI/Anthropic"]

    LLMProvider --> Normalizer["extraction/normalizer.py<br/>normalize_concept_label<br/>cleans concept names"]

    Normalizer --> DataLoader
    DataLoader --> End(["Episode Ingested"])

    Pipeline -.-> TokenTracker["monitoring/token_tracker.py<br/>TokenTracker.track_completion<br/>accumulates costs"]
    LLMProvider -.-> TokenTracker

    style Pipeline fill:#e1f5ff
    style TokenTracker fill:#fff4e1
    style Stage1 fill:#f0f0f0
    style Stage2 fill:#f0f0f0
    style Stage3 fill:#f0f0f0
    style Stage4 fill:#f0f0f0
```

## Flow 2: Skeleton Metadata Ingestion (Notebook 8)
Shows how spreadsheet data becomes Person/Org/Episode nodes

```mermaid
---
id: 36027f25-ccd1-4306-9bf0-a15e0f4f400c
title: "Flow 2: Skeleton Metadata Ingestion (Notebook 8)"
---
graph TD
    Start([User: Load Spreadsheet]) --> MetadataParser[parsers/metadata_parser.py<br/>parse_spreadsheet_row<br/>→ EpisodeMetadata dataclass]

    MetadataParser --> Skeleton[pipelines/ingest_episode_metadata.py<br/>SkeletonGraphIngestion.ingest_batch]

    Skeleton --> Person[graph/data_loader.py<br/>create_person_node<br/>→ Person nodes]

    Skeleton --> Org[graph/data_loader.py<br/>create_organization_node<br/>→ Organization nodes]

    Skeleton --> Episode[graph/data_loader.py<br/>create_episode_node<br/>→ Episode nodes]

    Skeleton --> GuestOn[graph/data_loader.py<br/>create_guest_on_edge<br/>→ GUEST_ON relationships]

    Person --> End([Skeleton Graph Created])
    Org --> End
    Episode --> End
    GuestOn --> End

    style Skeleton fill:#e1f5ff
    style MetadataParser fill:#e8f5e8
```

## Flow 3: Query & Retrieval (Notebook 6)
Shows the 5-stage retrieval pipeline from question to answer 

```mermaid
---
id: 0d3247c8-86ad-4960-bd36-d29c29f68eac
title: "Flow 3: Query & Retrieval (Notebook 6)"
---
graph TD
    Start([User: Ask Question<br/>'What did Tim say about data mesh?']) --> GraphRAG[retrieval/graph_rag.py<br/>GraphRAGPipeline.query]

    GraphRAG --> Step1{Step 1:<br/>Get Seeds}

    Step1 --> VectorSearch[retrieval/vector_search.py<br/>Neo4jVectorSearch.search<br/>→ vector similarity<br/>→ top-K segments]

    Step1 --> EntitySearch[retrieval/entity_search.py<br/>find_guest_segments<br/>find_person_appearances<br/>→ direct Cypher queries]

    VectorSearch --> Step2{Step 2:<br/>Expand Graph}
    EntitySearch --> Step2

    Step2 --> GraphExpansion[retrieval/graph_expansion.py<br/>expand_from_segments<br/>→ MENTIONS → Concept<br/>→ BROADER/NARROWER/RELATED<br/>→ collect more segments]

    GraphExpansion --> Step3{Step 3:<br/>Rerank Optional}

    Step3 --> Reranker[retrieval/reranker.py<br/>ContextReranker.rerank<br/>→ LLM scores 0-10<br/>→ filters low scores]

    Reranker --> Step4{Step 4:<br/>Generate Answer}

    Step4 --> AnswerSynth[generation/answer_synthesizer.py<br/>synthesize_answer<br/>→ grounded answer<br/>→ timestamp citations<br/>→ what to re-listen]

    AnswerSynth --> Step5{Step 5:<br/>Follow-ups}

    Step5 --> QuestionSuggest[generation/question_suggester.py<br/>suggest_followup_questions<br/>→ 3-5 related questions]

    QuestionSuggest --> End([Answer Returned])

    Reranker -.-> LLMProvider[providers/llm_provider.py<br/>LLMProvider.generate]
    AnswerSynth -.-> LLMProvider
    QuestionSuggest -.-> LLMProvider

    LLMProvider -.-> TokenTracker[monitoring/token_tracker.py<br/>TokenTracker.track_completion]

    style GraphRAG fill:#e1f5ff
    style TokenTracker fill:#fff4e1
    style LLMProvider fill:#ffe8f5
    style Step1 fill:#f0f0f0
    style Step2 fill:#f0f0f0
    style Step3 fill:#f0f0f0
    style Step4 fill:#f0f0f0
    style Step5 fill:#f0f0f0
```

## Layered Architecture
Shows the 4-layer dependency structure (Notebook → Pipeline → Domain → Infrastructure) 

```mermaid
---
id: b11309b9-256a-4a15-8b11-f47d451be59b
title: "Layered Architecture Diagram"
---
graph TB
    subgraph Notebook["NOTEBOOK LAYER (User Interface)"]
        N1[07_podcast_ingestion_pipeline.ipynb]
        N2[08_skeleton_graph_ingestion.ipynb]
        N3[06_graphrag_qa.ipynb]
    end

    subgraph Pipeline["PIPELINE LAYER (Orchestration)"]
        P1[pipelines/podcast_ingestion.py]
        P2[pipelines/ingest_episode_metadata.py]
        P3[retrieval/graph_rag.py]
    end

    subgraph Domain["DOMAIN LOGIC LAYER (Core Operations)"]
        D1[parsers/*<br/>parse transcripts/metadata]
        D2[embeddings/*<br/>vectorize text]
        D3[extraction/*<br/>extract concepts via LLM]
        D4[retrieval/*<br/>search + expand graph]
        D5[generation/*<br/>synthesize answers]
    end

    subgraph Infra["INFRASTRUCTURE LAYER (Shared Utilities)"]
        I1[graph/*<br/>Neo4j read/write]
        I2[providers/*<br/>LLM API abstraction]
        I3[monitoring/*<br/>token tracking]
        I4[models/*<br/>shared data structures]
        I5[config.py<br/>environment setup]
    end

    N1 --> P1
    N2 --> P2
    N3 --> P3

    P1 --> D1
    P1 --> D2
    P1 --> D3

    P2 --> D1

    P3 --> D4
    P3 --> D5

    D1 --> I1
    D2 --> I1
    D3 --> I1
    D3 --> I2
    D4 --> I1
    D5 --> I2

    I2 --> I3

    D1 --> I4
    D2 --> I4
    D3 --> I4
    D4 --> I4
    D5 --> I4

    style Notebook fill:#e1f5ff
    style Pipeline fill:#e8f5e8
    style Domain fill:#fff4e1
    style Infra fill:#f0f0f0
```

## Module Interaction Matrix
Shows which modules call which other modules

```mermaid
---
id: ba442dc3-d01d-4107-b363-4d960f8b03c1
title: "App Architecture - Module Interaction"
---
graph LR
    subgraph Core["Core Orchestrators"]
        PI[podcast_ingestion.py]
        IM[ingest_episode_metadata.py]
        GR[graph_rag.py]
    end

    subgraph Parsers["Parsers"]
        TP[transcript_parser.py]
        MP[metadata_parser.py]
    end

    subgraph Processing["Processing"]
        EM[embedder.py]
        CE[concept_extractor.py]
        NO[normalizer.py]
    end

    subgraph Retrieval["Retrieval"]
        VS[vector_search.py]
        ES[entity_search.py]
        GE[graph_expansion.py]
        RR[reranker.py]
    end

    subgraph Generation["Generation"]
        AS[answer_synthesizer.py]
        QS[question_suggester.py]
    end

    subgraph Infrastructure["Infrastructure"]
        DL[data_loader.py]
        LP[llm_provider.py]
        TT[token_tracker.py]
    end

    PI --> TP
    PI --> EM
    PI --> CE

    IM --> MP

    GR --> VS
    GR --> ES
    GR --> GE
    GR --> RR
    GR --> AS
    GR --> QS

    CE --> NO

    TP --> DL
    MP --> DL
    EM --> DL
    CE --> DL

    CE --> LP
    RR --> LP
    AS --> LP
    QS --> LP

    LP --> TT

    VS --> DL
    ES --> DL
    GE --> DL

    style Core fill:#e1f5ff
    style Parsers fill:#e8f5e8
    style Processing fill:#fff4e1
    style Retrieval fill:#ffe8f5
    style Generation fill:#f5e8ff
    style Infrastructure fill:#f0f0f0
```

## Data Flow: Episode → Neo4j → Answer
Shows the end-to-end data transformation journey

```mermaid
---
id: 5b91f6b4-8027-498a-b21b-6bdd3b30b5c3
title: "Data Flow Diagram - From query to response"
---
graph LR
    subgraph Input["Input Data"]
        TR[Transcript MD/JSON]
        SS[Spreadsheet CSV]
    end

    subgraph Parse["Parsing"]
        TR --> TP[transcript_parser]
        SS --> MP[metadata_parser]

        TP --> SEG[Segment Dicts<br/>start_sec, end_sec<br/>text, speaker]
        MP --> META[EpisodeMetadata<br/>guests, orgs, dates]
    end

    subgraph Transform["Transformation"]
        SEG --> EMB[embedder]
        EMB --> EMBSEG[Segments +<br/>embeddings]

        EMBSEG --> CEXT[concept_extractor]
        CEXT --> CONC[Concepts +<br/>MENTIONS edges]
    end

    subgraph Store["Neo4j Storage"]
        META --> DL1[data_loader]
        EMBSEG --> DL1
        CONC --> DL1

        DL1 --> NEO[(Neo4j Graph<br/>Episode, Segment,<br/>Person, Org,<br/>Concept nodes)]
    end

    subgraph Query["Query Time"]
        Q[User Question] --> VS[vector_search]

        VS --> NEO
        NEO --> RSEG[Retrieved<br/>Segments]

        RSEG --> GE[graph_expansion]
        GE --> NEO
        NEO --> RCTX[Expanded<br/>Context]

        RCTX --> AS[answer_synthesizer]
        AS --> ANS[Grounded Answer<br/>+ Citations]
    end

    style Input fill:#e8f5e8
    style Parse fill:#fff4e1
    style Transform fill:#ffe8f5
    style Store fill:#e1f5ff
    style Query fill:#f5e8ff
```
