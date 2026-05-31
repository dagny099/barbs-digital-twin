"""
extract_entities.py
===================
Phase 2 Step 1: Extract entities (Skills, Methods, Technologies, Concepts) from
project walkthroughs and KB document sections using Claude API.

Outputs:
    scripts/extracted_entities.json  — raw extractions (review before canonicalize)

Run order:
    1. python scripts/extract_entities.py
    2. python scripts/canonicalize_entities.py
    3. python scripts/populate_neo4j_graph.py
    4. python scripts/embed_sections.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import hashlib
from pathlib import Path
from dotenv import load_dotenv
import anthropic
from featured_projects import FEATURED_PROJECTS
from utils import parse_markdown_sections, get_sensitivity

load_dotenv(override=True)

# ── Config ───────────────────────────────────────────────────────────────────
SCRIPTS_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = SCRIPTS_DIR / "extracted_entities.json"
CACHE_FILE  = SCRIPTS_DIR / ".extraction_cache.json"
INPUTS_PATH = Path(os.environ.get("INPUTS_PATH", ""))
MODEL       = "claude-sonnet-4-6"

KB_DOCS = [
    ("kb_biosketch.md",                    "kb-biosketch"),
    ("kb_career_narrative.md",             "kb-career"),
    ("kb_dissertation_modern_relevance.md","kb-dissertation-relevance"),
    ("kb_dissertation_overview.md",        "kb-dissertation-overview"),
    ("kb_dissertation_philosophy.md",      "kb-dissertation-philosophy"),
    ("kb_easter_eggs.md",                  "kb-easter-eggs"),
    ("kb_intellectual_foundations.md",     "kb-intellectual-foundations"),
    ("kb_personal_origin_stories.md",      "kb-origins"),
    ("kb_philosophy-and-approach.md",      "kb-philosophy"),
    ("kb_professional_positioning.md",     "kb-positioning"),
    ("kb_project_answer_bank.md",          "kb-answers"),
    ("kb_projects.md",                     "kb-projects"),
    ("kb_publications.md",                 "kb-publications"),
]


def _load_cache() -> dict:
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text())
    return {}


def _save_cache(cache: dict) -> None:
    CACHE_FILE.write_text(json.dumps(cache, indent=2))


def _cache_key(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def _strip_fences(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:])
        if raw.endswith("```"):
            raw = raw[:-3]
    return raw.strip()


def extract_project_entities(project: dict, client: anthropic.Anthropic, cache: dict) -> dict:
    """Extract Skills, Methods, Technologies from a project walkthrough."""
    text = project.get("walkthrough_context", "")
    key = _cache_key(f"project:{project['id']}:{text[:500]}")
    if key in cache:
        print(f"  [cached]")
        return cache[key]

    prompt = f"""Analyze this project description and extract structured entities.

Project Title: {project['title']}
Tags: {', '.join(project.get('tags', []))}

Project Walkthrough:
{text}

Extract:
1. Skills demonstrated (capabilities like "Knowledge Graphs", "RAG Systems", "Evaluation Harnesses")
2. Methods used (approaches like "Section-aware chunking", "TransE embeddings", "Hybrid retrieval")
3. Technologies used (tools like "Neo4j", "ChromaDB", "Streamlit", "Flask", "OpenAI API")

For each skill, classify the role:
- "core": Central to the project (the main capability it demonstrates)
- "secondary": Important but not the main focus
- "supporting": Enabling/infrastructure

For each method, identify the stage:
- "ingestion": Data collection/preprocessing
- "retrieval": Query/search mechanisms
- "evaluation": Testing/validation
- "generation": Output creation

Return ONLY valid JSON with no markdown fences:
{{
  "skills": [
    {{"name": "Knowledge Graphs", "role": "core", "category": "technical"}}
  ],
  "methods": [
    {{"name": "Section-aware chunking", "stage": "ingestion", "category": "data-engineering"}}
  ],
  "technologies": [
    {{"name": "Neo4j", "category": "database"}}
  ]
}}"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    result = json.loads(_strip_fences(response.content[0].text))
    cache[key] = result
    _save_cache(cache)
    return result


def extract_section_mentions(section_name: str, section_text: str,
                              client: anthropic.Anthropic, cache: dict) -> dict:
    """Extract entity mentions (projects, skills, concepts) from a KB section."""
    key = _cache_key(f"section:{section_name}:{section_text[:500]}")
    if key in cache:
        return cache[key]

    prompt = f"""Analyze this knowledge base section and identify entities mentioned.

Section: {section_name}

Text:
{section_text[:2000]}

Identify mentions of:
1. Named projects (specific project titles or clear project descriptions)
2. Skills (technical capabilities, domain expertise)
3. Concepts (theoretical frameworks, academic concepts, philosophical ideas)

Be conservative — only include clearly named entities, not generic topic words.

Return ONLY valid JSON with no markdown fences:
{{
  "projects": [{{"name": "Resume Graph Explorer", "context": "brief excerpt where mentioned"}}],
  "skills": [{{"name": "Knowledge Graphs"}}],
  "concepts": [{{"name": "Organizational sensemaking"}}]
}}"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}]
    )
    result = json.loads(_strip_fences(response.content[0].text))
    cache[key] = result
    _save_cache(cache)
    return result


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set in environment")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    cache  = _load_cache()

    output = {
        "project_entities": {},
        "section_mentions": {}
    }

    # ── Extract from project walkthroughs ────────────────────────────────────
    print("\n=== Extracting project entities ===")
    for project in FEATURED_PROJECTS:
        pid = project["id"]
        print(f"\n→ {project['title']}")
        entities = extract_project_entities(project, client, cache)
        output["project_entities"][pid] = entities
        print(f"  Skills: {len(entities.get('skills', []))}, "
              f"Methods: {len(entities.get('methods', []))}, "
              f"Technologies: {len(entities.get('technologies', []))}")

    # ── Extract from KB document sections ────────────────────────────────────
    if not INPUTS_PATH.exists():
        print(f"\n⚠️  INPUTS_PATH not found: {INPUTS_PATH} — skipping KB section extraction")
    else:
        print("\n=== Extracting KB section mentions ===")
        for filename, source_type in KB_DOCS:
            kb_path = INPUTS_PATH / filename
            if not kb_path.exists():
                print(f"  ⚠️  Skipping {filename} (not found)")
                continue

            raw = kb_path.read_text(encoding="utf-8")
            sections = parse_markdown_sections(raw, header_level=2, include_nested=True)
            sensitivity = get_sensitivity(source_type)
            print(f"\n→ {filename} ({len(sections)} sections, {sensitivity})")

            for section in sections:
                if len(section["text"].strip()) < 50:
                    continue
                sec_id = f"{filename.replace('.md', '')}:{section['section_name']}"
                print(f"  • {section['section_name'][:55]}")
                mentions = extract_section_mentions(
                    section["section_name"],
                    section["text"],
                    client,
                    cache,
                )
                output["section_mentions"][sec_id] = {
                    **mentions,
                    "source_file":  filename,
                    "source_type":  source_type,
                    "sensitivity":  sensitivity,
                    "section_name": section["section_name"],
                }

    OUTPUT_FILE.write_text(json.dumps(output, indent=2))
    print(f"\n✓ Saved → {OUTPUT_FILE.name}")
    print(f"  Projects:  {len(output['project_entities'])}")
    print(f"  Sections:  {len(output['section_mentions'])}")
    print(f"\nReview {OUTPUT_FILE.name}, then run canonicalize_entities.py")


if __name__ == "__main__":
    main()
