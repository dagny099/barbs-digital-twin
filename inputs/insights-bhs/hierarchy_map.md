---
analysis_type: hierarchy_map
title: "Skill Hierarchy — SKOS Taxonomy Structure"
source_file: Barbara_Hidalgo-Sotelo_Data-Scientist-Cisco.pdf
person_name: Barbara Hidalgo-Sotelo
analysis_date: 2026-03-05
tags:
  - "hierarchy"
  - "taxonomy"
  - "SKOS"
  - "skill relationships"
  - "broader"
  - "narrower"
query_hints:
  - "how do my skills relate"
  - "skill hierarchy"
  - "skill taxonomy"
  - "skill categories"
  - "what falls under what"
entity_count: 27
job_count: 4
skill_count: 22
---

# Skill Hierarchy — SKOS Taxonomy Structure

Of 22 skills in Barbara's graph, only 1 have SKOS hierarchical relationships (broader/narrower). The remaining 21 are flat, standalone skill nodes with no taxonomic context.

SKILLS WITH HIERARCHY:
  Data Science → includes: machine learning, data analysis, statistical analysis, data visualization
  Data Science → falls under: technical

STANDALONE SKILLS (no taxonomic relationships):
  • Docker (Technical, ESCO-linked)
  • Generative AI (Domain, string-only)
  • Neo4j (Technical, string-only)
  • LlamaIndex (Technical, string-only)
  • PyTorch (Technical, string-only)
  • XGBoost (Technical, string-only)
  • FAISS (Technical, string-only)
  • Python (Technical, ESCO-linked)
  • Natural Language Processing (Domain, string-only)
  • FastAPI (Technical, string-only)
  • scikit-learn (Technical, string-only)
  • Project Management (Soft, string-only)
  • Machine Learning (Domain, ESCO-linked)
  • Cross-functional Communication (Soft, string-only)
  • PostgreSQL (Technical, string-only)
  • OpenAI GPT-4 (Technical, string-only)
  • Technical Storytelling (Soft, string-only)
  • AWS (Technical, ESCO-linked)
  • Claude (Technical, string-only)
  • LangChain (Technical, string-only)
  • RAG Systems (Domain, string-only)

Richer skill hierarchies would enable queries like 'show me all my analytical skills' or 'what cloud platform experience do I have' — currently these require manual tagging because the skills aren't connected taxonomically.