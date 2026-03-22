# My Career Narrative

*A career story document by Barbara (Dagny) Hidalgo-Sotelo*

---

## The through-line

If you look at my career as a graph — and I literally have, because I built a tool that does this — the most interesting structural feature is that it doesn't hold together at the technology layer. My stack has changed almost completely at every major transition. What holds it together is methodology: take something messy, find the right representation, and build a system that makes it useful for the people downstream.

That's not a retroactive narrative. It's what every role has actually required of me, from analyzing eye-tracking data at MIT to building knowledge graphs as an independent consultant. The tools change. The problem structure doesn't.

## Chapter 1: The research foundation (MIT, 2004–2012)

I came to MIT to study cognitive science — specifically, how humans guide their visual attention through scenes. My dissertation, "Eye Movement Guidance in Familiar Visual Scenes," showed that people use contextual priors to decide where to look before they've even processed what's in front of them. I applied computer vision and statistical modeling to analyze human visual attention across 900+ scenarios, building computational models that predicted gaze patterns from scene context and task demands. You walk into a kitchen and your eyes go to the counter, not because you've analyzed every pixel, but because you have a model of "kitchen" that predicts where things are.

The work has been cited over 430 times. My co-authors included Aude Oliva and Antonio Torralba, and we published on human learning of contextual priors for object search in Visual Cognition (2009), among other venues. More importantly, it gave me a framework I still use: the idea that structured representations of the world are how humans (and good systems) make sense of information. Perception isn't data intake. It's model-building.

I also learned how to design rigorous experiments, handle messy behavioral data, write for peer review, and teach. I was an instructor and TA for multiple undergraduate cognitive science courses and mentored research students on experimental design and data analysis.

The technical stack was MATLAB, statistical modeling, computer vision, and eye-tracking hardware. None of that persisted into my next roles. The methodology — hypothesis-driven design, rigorous evaluation, structured representation — persisted into everything.

## Chapter 2: Research, healthcare, and building from scratch (UT Austin + BALEX + Persis, 2013–2017)

I'd come to Austin originally for undergrad — dual BS in Electrical Engineering and Biology at UT Austin, Dean's Scholars Program, NCAA Division I rowing, research in the Comparative RNA Lab with Dr. Robin Gutell and in behavioral neuroscience labs. After MIT, I came back.

At UT Austin I joined a large NIH-funded longitudinal study tracking bilingual development in 1,000+ children as a Research Engineer. I engineered ETL workflows for speech and behavioral data across distributed research sites, achieving 99.9% data integrity. I automated signal processing workflows that reduced manual validation time by 40%. I built a GUI-based tool in Python and MATLAB to extract and validate speech onset times from raw audio — it was adopted by three research sites as their standard. I mentored research staff and ensured protocol compliance across teams. This was my first experience building tools that other researchers depended on daily — the beginning of the "build things people actually use" principle.

Then I co-founded BALEX Healthcare Services with my parents — a home health agency providing skilled nursing and therapy services to underserved communities in Austin. This was a complete context switch. I designed the technology architecture — a web-based EMR system (PHP, HTML/CSS, PostgreSQL) integrating clinical documentation, scheduling, billing, and payer reporting. I managed the full delivery lifecycle from requirements through UAT to deployment. We served 50+ patients in the first 18 months and established HIPAA compliance protocols with zero violations.

BALEX taught me healthcare from the inside — not the data science version, but the version where real clinicians have to use your system at the end of a 12-hour shift and it has to work or patients don't get seen. That operational understanding is something most AI engineers never develop. It fundamentally changed how I think about building systems: I design for the person who's tired and needs to make a decision, not for the person who's reviewing a demo.

During this same period, I worked with Persis Consulting (2014–2017) documenting software requirements and supporting Agile delivery for healthcare and private-sector clients. I managed QA/QC testing and created end-user training materials to improve reliability and adoption of EMR software. This was the less glamorous side of healthcare technology — alignment between technical implementation and business needs, training materials that actually help people, testing that catches problems before users do. It reinforced the same lesson BALEX was teaching me: the gap between building something and making it work for real people is where the real engineering happens.

## Chapter 3: Consulting and transformation (Inflective + MediaScience + Accuro, 2017–2022)

At Inflective (2017–2019), I led a digital transformation project optimizing medical bill adjudication for a third-party administrator processing 4M+ bills annually. I designed a Python/scikit-learn classification model that automated medical bill categorization at 92% accuracy — matching human coder performance. I co-led Lean Six Sigma workshops to identify process inefficiencies, reducing error rates by roughly 25% and improving processing throughput by 30%. I facilitated C-level and cross-team design discussions, translating business rules into configuration specs and workflow diagrams. I delivered testing plans, implementation support, and detailed documentation for new integrations.

The key insight from this work wasn't the model accuracy. It was that I designed the classification scheme around how claims adjusters actually think about their work, because I'd been on the other side of that workflow at BALEX. The cognitive science and the healthcare operations experience converged in a way that made the model not just accurate but adoptable.

At MediaScience (2017), I managed biometric and eye-tracking research projects for major media organizations — analyzing advertising effectiveness using eye tracking, GSR (galvanic skin response), and facial expression analysis. I applied anomaly detection and statistical modeling to assess advertising impact, delivered 10+ client reports with data-driven recommendations that influenced advertising strategy, and coordinated multi-disciplinary teams. This was the one role where my MIT research methodology — hypothesis testing, multimodal biometric analysis, experimental design — persisted directly into the technical work.

At Accuro Solutions (2020–2022), I served as a technical liaison managing third-party integrations for automated document capture in a high-volume insurance claims environment. I managed API-driven integrations and defect triage, coordinating multiple vendors to ensure SLAs and system stability. I onboarded three vendor systems with zero production incidents during cutover and led cross-functional testing and calibration with hypercare monitoring. This was pure integration and coordination work — no ML, no research — but it sharpened my ability to manage complex technical dependencies across organizations and communicate risks and timelines clearly to executives.

## Chapter 4: Data governance and federal consulting (Metric5, 2021–2023)

At Metric5, I consulted for a federal regulatory agency on data governance modernization to comply with OPEN Government Data Act mandates. I built Python utilities to streamline metadata export and reporting workflows with documentation that enabled 30+ non-technical data stewards to maintain catalog metadata independently. I developed a POC reporting utility integrating ServiceNow, the enterprise data catalog (Alation), and analytics outputs that improved data access request turnaround by about 25%. I designed and documented REST/JSON-based integrations between ServiceNow, Drupal, and PowerBI to streamline access-request workflows. I also delivered a text analysis and metadata classification POC that could automatically flag content containing sensitive data in the SEC data catalog.

The important thing about this period isn't the specific deliverables — it's that I developed a genuine understanding of data governance as a discipline. Metadata management, data quality frameworks, DCAM methodology, DAMA-DMBOK principles, catalog rationalization, vocabulary alignment, compliance protocols. Most AI engineers think of governance as bureaucracy. I think of it as the unsexy foundation that determines whether your AI system is trustable. The CDMP and DCAM certifications I earned during this period reflect a deliberate investment, not a checkbox.

This role also reinforced my API integration and data engineering skills — REST APIs, JSON, SQL (PostgreSQL), PowerBI (including DAX and data modeling), cross-platform data flows — and gave me experience working in a standards-driven federal environment with strict security and compliance requirements.

## Chapter 5: The GenAI pivot (Independent + Inflective, 2024–present)

Starting in early 2024, I made a deliberate shift toward hands-on GenAI application engineering. This wasn't a random pivot — it was the natural convergence of everything before it. My cognitive science background (structured representations), my healthcare experience (domain complexity), my consulting skills (stakeholder translation), and my data governance training (evaluation and quality) all pointed toward building AI systems that actually work for the people using them.

I returned to Inflective (January 2024 – May 2025) for a consulting engagement focused on program delivery and change management for a healthcare technology client transitioning to new ERP systems. I connected Google Analytics 4 to Looker Studio for engagement dashboards, analyzed user behavior for UX recommendations, and established escalation pathways that improved cross-team communication. This was client-facing delivery work — stakeholder coordination, risk identification, executive reporting.

In parallel and continuing after Inflective, I built a portfolio of GenAI applications that represent the convergence of my full background:

**Resume Graph Explorer** — a full-stack application that transforms resumes into SKOS-compliant knowledge graphs. I designed a hybrid vocabulary with four namespaces (SKOS, ESCO, schema.org, custom), built a three-phase normalization pipeline with ESCO-anchored entity merging, and implemented a narrative synthesizer that produces conservative and exploratory career stories from graph analysis. The system supports provider-agnostic LLM extraction (Claude, OpenAI, Ollama), RDF export in three formats, and SPARQL queries. Deployed with Flask on Railway and React on Vercel.

**Digital Twin** — a RAG-powered chatbot that represents me conversationally, grounded in my actual work and writing. Built with ChromaDB, OpenAI embeddings (text-embedding-3-small), and Gradio on HuggingFace. The interesting design challenge was building the knowledge base *for* retrieval — writing documents shaped to improve how the system answers questions, not just storing everything I had. Lives at twin.barbhs.com.

**Weaving Memories Into Graphs** — a memorial knowledge graph for my late father, Domingo Hidalgo. A 14-entity Neo4j schema with LLM-powered extraction from his biosketch, Wikidata enrichment for external context, temporal relationship patterns, and a React + Vite frontend served by a Flask REST API. Deployed at domingo-hidalgo.com. The most personal project in my portfolio and the most technically complete knowledge graph implementation.

**Concept Cartographer** — a Gradio app that extracts concepts and relationships from LLM conversations and visualizes them as knowledge graphs in real time. Optimized from a two-call to single structured JSON architecture, reducing token usage and latency significantly.

**Poolula Platform** — a modular RAG system with a built-in evaluation harness. Local-first architecture combining structured data and document retrieval (ChromaDB) with tool-style routing. Provider-agnostic LLM backend (OpenAI, Anthropic), audit-friendly logging, ground-truth evaluation workflow. Built with FastAPI and SQLModel. This is where I developed my approach to RAG evaluation as a first-class design concern.

**ConvoScope** — a multi-LLM conversation platform deployed on AWS EC2 with custom domain, SSL, and monitoring. Supports OpenAI, Anthropic, and Google providers with conversation management, real-time streaming, and topic extraction. Includes an evaluation framework with A/B testing methodology that achieved a 15% quality improvement. Captures latency and token-cost metrics to guide prompt compression tradeoffs.

**GraphRAG with Podcasts** — a knowledge graph and vector retrieval system for podcast Q&A. Multi-stage ingestion pipeline with checkpointing and idempotent re-runs. Entities modeled in Neo4j Aura with GraphRAG-style retrieval supporting citation-grounded traceability.

**ChronoScope** — a Streamlit application extracting timeline events from resumes and generating interactive Plotly timelines and TimelineJS-ready exports. Local-first, privacy-sensitive design with validation checks for consistency across runs.

**Beehive Analytics** — a knowledge graph transforming 4+ years of backyard beehive inspection photos into queryable colony intelligence using Google Cloud Vision API, Neo4j, vector embeddings for semantic search, and weather API integration.

**Fitness Analytics Dashboard** — an end-to-end ML pipeline classifying 14 years of personal exercise data using scikit-learn and XGBoost, with drift detection, model retraining workflows, and an interactive dashboard with explainable AI features at workouts.barbhs.com.

My current technical stack spans Python (NumPy, pandas, scikit-learn, with exposure to PyTorch and TensorFlow), GenAI frameworks (LangChain, LlamaIndex, with familiarity with LangGraph and AutoGen), vector and graph databases (ChromaDB, Neo4j, with exposure to Pinecone, Weaviate, and FAISS), web frameworks (Flask, FastAPI, Streamlit, basic React), cloud platforms (AWS EC2/RDS/Lambda/Bedrock, Azure AI Studio, GCP BigQuery/Cloud Vision/Vertex AI), and evaluation tools (RAGAS, DeepEval, custom test sets). I'm proficient in SQL (PostgreSQL, MySQL, BigQuery), comfortable with Docker and basic Terraform, and experienced with Git workflows, CI/CD patterns (GitHub Actions, Azure DevOps), and documentation practices.

## The structural story

When I ran my own career data through Resume Explorer, the graph confirmed something I already knew intuitively: my career doesn't hold together at the technology layer. The stack changes at almost every transition — MATLAB to Python to PHP to PowerBI to LangChain to Neo4j. Only Python bridges more than one role.

But the graph also showed what does hold it together: the analytical methodology. Every role required taking messy, ambiguous, human-generated material and building a structured representation that made it useful. Eye-tracking data at MIT. Speech data at UT Austin. Clinical workflows at BALEX. EMR requirements at Persis. Medical bills at Inflective. Biometric signals at MediaScience. Vendor integrations at Accuro. Federal metadata at Metric5. Resumes, conversations, beehive photos, and a father's legacy in my independent work.

My career has moved laterally across domains rather than climbing vertically within one. That's a feature, not a bug. I've worked in research, healthcare, insurance, federal government, and independent AI engineering. Every domain transition forced me to learn new tools, new constraints, new stakeholder languages. The result is that I can walk into any domain and start asking the right questions about how to represent its complexity — because I've done it many times before in completely different contexts.

The one gap in how I present this: my cognitive science research methodology — eye tracking, biometric analysis, experimental design, signal processing — is almost invisible in my current professional positioning. It shouldn't be. That toolkit didn't disappear; it transformed. The experimental rigor became evaluation framework design. The attention modeling became retrieval system design. The perceptual science became "design for the downstream mental model." The bridge is there — it's just not always visible in how I describe my work, and I'm actively working on making it more explicit.

## What I'm looking for now

I'm looking for roles where the problem isn't just "build a model" but "figure out what to build, build it, and make sure the people who need it can actually use it." Applied AI engineering, solutions architecture, technical consulting — roles that value the combination of technical depth, stakeholder communication, and domain adaptability.

I'm strongest in zero-to-one environments: standing up first RAG systems, designing knowledge representations for new domains, bridging the gap between what data science teams build and what business teams need. I'm based in Austin, TX, open to remote work, and comfortable with up to 30% travel. I'm fluent in both English and Spanish — native in both.

My salary expectations start at $140K, with total compensation targets depending on company stage, equity, and role scope. I'm not desperate — I'm actively building and shipping, and I take my time to find the right fit. The right role is one where my specific combination of cognitive science, healthcare operations, consulting delivery, and GenAI engineering is a genuine asset, not a compromise.
