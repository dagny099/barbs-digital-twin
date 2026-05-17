"""
populate_neo4j_graph.py
=======================
Phase 2 Step 3: Full graph population — Document/Section/Project/entity nodes
plus all relationships.

Starts with a full wipe (MATCH (n) DETACH DELETE n) so every run is a clean rebuild.
ChromaDB is NOT touched; `.chroma_db_DT/` remains intact as rollback.

Run order:
    1. python scripts/extract_entities.py
    2. python scripts/canonicalize_entities.py
    3. python scripts/populate_neo4j_graph.py   ← this script
    4. python scripts/embed_sections.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from neo4j_utils import get_driver, close_driver
from neo4j_models import DocumentNode, SectionNode, ProjectNode, SkillNode, MethodNode, TechnologyNode, ConceptNode
from featured_projects import FEATURED_PROJECTS
from utils import parse_markdown_sections, get_sensitivity

load_dotenv(override=True)

SCRIPTS_DIR = Path(__file__).resolve().parent
CANONICAL   = SCRIPTS_DIR / "canonical_entities.json"
INPUTS_PATH = Path(os.environ.get("INPUTS_PATH", ""))
NOW         = datetime.now(timezone.utc).isoformat()

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


def clear_graph(session) -> None:
    print("⚠️  Clearing all nodes and relationships (full rebuild)...")
    session.run("MATCH (n) DETACH DELETE n")
    print("  ✓ Graph cleared")


def create_document_sections(session) -> None:
    """Create Document and Section nodes for all KB files, plus HAS_SECTION and NEXT_SECTION."""
    total_docs = 0
    total_sections = 0

    for filename, source_type in KB_DOCS:
        kb_path = INPUTS_PATH / filename
        if not kb_path.exists():
            print(f"  ⚠️  {filename} not found — skipping")
            continue

        raw_bytes    = kb_path.read_bytes()
        raw_text     = raw_bytes.decode("utf-8")
        content_hash = hashlib.sha256(raw_bytes).hexdigest()
        sensitivity  = get_sensitivity(source_type)
        doc_id       = filename.replace(".md", "")
        title        = doc_id.replace("kb_", "").replace("-", " ").replace("_", " ").title()

        doc = DocumentNode(
            id=doc_id,
            source_type=source_type,
            file_path=str(kb_path),
            title=title,
            sensitivity=sensitivity,
            content_hash=content_hash,
            last_updated=NOW,
        )
        session.run(
            "MERGE (d:Document {id: $id}) SET d += $props",
            {"id": doc.id, "props": doc.to_dict()},
        )

        sections     = parse_markdown_sections(raw_text, header_level=2, include_nested=True)
        section_ids  = []

        for order, sec in enumerate(sections):
            if len(sec["text"].strip()) < 50:
                continue
            sec_id   = f"{doc_id}:{sec['section_name']}"
            sec_node = SectionNode(
                id=sec_id,
                name=sec["section_name"],
                full_text=sec["text"],
                sensitivity=sensitivity,
                order=order,
            )
            session.run(
                """
                MERGE (s:Section {id: $id})
                SET s += $props
                WITH s
                MATCH (d:Document {id: $doc_id})
                MERGE (d)-[:HAS_SECTION]->(s)
                """,
                {"id": sec_node.id, "props": sec_node.to_dict(), "doc_id": doc_id},
            )
            section_ids.append(sec_id)

        # Sequential NEXT_SECTION chain
        for i in range(len(section_ids) - 1):
            session.run(
                """
                MATCH (a:Section {id: $a}), (b:Section {id: $b})
                MERGE (a)-[:NEXT_SECTION]->(b)
                """,
                {"a": section_ids[i], "b": section_ids[i + 1]},
            )

        print(f"  ✓ {filename}: {len(section_ids)} sections")
        total_docs    += 1
        total_sections += len(section_ids)

    print(f"  → {total_docs} documents, {total_sections} sections total")


def create_projects(session) -> None:
    for project in FEATURED_PROJECTS:
        node = ProjectNode(
            id=project["id"],
            title=project["title"],
            summary=project["summary"],
            design_insight=project.get("design_insight", ""),
            walkthrough_context=project.get("walkthrough_context", ""),
            diagram_filename=project.get("diagram_filename", ""),
            tags=project.get("tags", []),
            sensitivity="public",
        )
        session.run(
            "MERGE (p:Project {id: $id}) SET p += $props",
            {"id": node.id, "props": node.to_dict()},
        )
    print(f"  ✓ {len(FEATURED_PROJECTS)} projects")


def create_entity_nodes(session, canonical: dict) -> None:
    for s in canonical.get("skills", []):
        node = SkillNode(name=s["name"], category=s.get("category", ""), alt_labels=s.get("alt_labels", []))
        session.run("MERGE (n:Skill {name: $name}) SET n += $props", {"name": node.name, "props": node.to_dict()})

    for m in canonical.get("methods", []):
        node = MethodNode(name=m["name"], category=m.get("category", ""),
                          description=m.get("description", ""), alt_labels=m.get("alt_labels", []))
        session.run("MERGE (n:Method {name: $name}) SET n += $props", {"name": node.name, "props": node.to_dict()})

    for t in canonical.get("technologies", []):
        node = TechnologyNode(name=t["name"], category=t.get("category", ""), alt_labels=t.get("alt_labels", []))
        session.run("MERGE (n:Technology {name: $name}) SET n += $props", {"name": node.name, "props": node.to_dict()})

    for c in canonical.get("concepts", []):
        node = ConceptNode(name=c["name"], source=c.get("source", ""),
                           description=c.get("description", ""), alt_labels=c.get("alt_labels", []))
        session.run("MERGE (n:Concept {name: $name}) SET n += $props", {"name": node.name, "props": node.to_dict()})

    print(f"  ✓ {len(canonical.get('skills', []))} skills, "
          f"{len(canonical.get('methods', []))} methods, "
          f"{len(canonical.get('technologies', []))} technologies, "
          f"{len(canonical.get('concepts', []))} concepts")


def _build_name_lookup(entities: list[dict]) -> dict[str, str]:
    """Build {lowercased_name: canonical_name} including alt_labels."""
    lookup = {}
    for e in entities:
        lookup[e["name"].lower()] = e["name"]
        for alt in e.get("alt_labels", []):
            lookup[alt.lower()] = e["name"]
    return lookup


def create_project_entity_relationships(session, canonical: dict) -> None:
    """Project → DEMONSTRATES → Skill, USES_METHOD → Method, USES_TECHNOLOGY → Technology."""
    skill_lu  = _build_name_lookup(canonical.get("skills", []))
    method_lu = _build_name_lookup(canonical.get("methods", []))
    tech_lu   = _build_name_lookup(canonical.get("technologies", []))

    total = 0
    for pid, entities in canonical.get("_source_project_entities", {}).items():
        for skill in entities.get("skills", []):
            name = skill_lu.get(skill["name"].lower(), skill["name"])
            session.run(
                """
                MATCH (p:Project {id: $pid}), (s:Skill {name: $name})
                MERGE (p)-[:DEMONSTRATES {role: $role}]->(s)
                """,
                {"pid": pid, "name": name, "role": skill.get("role", "")},
            )
            total += 1

        for method in entities.get("methods", []):
            name = method_lu.get(method["name"].lower(), method["name"])
            session.run(
                """
                MATCH (p:Project {id: $pid}), (m:Method {name: $name})
                MERGE (p)-[:USES_METHOD {stage: $stage}]->(m)
                """,
                {"pid": pid, "name": name, "stage": method.get("stage", "")},
            )
            total += 1

        for tech in entities.get("technologies", []):
            name = tech_lu.get(tech["name"].lower(), tech["name"])
            session.run(
                """
                MATCH (p:Project {id: $pid}), (t:Technology {name: $name})
                MERGE (p)-[:USES_TECHNOLOGY]->(t)
                """,
                {"pid": pid, "name": name},
            )
            total += 1

    print(f"  ✓ {total} project → entity relationships")


def create_section_mention_relationships(session, canonical: dict) -> None:
    """
    Section → MENTIONS → {Project, Skill, Concept}
    Project → DESCRIBED_IN → Section (when section prominently mentions a project)
    """
    project_by_title = {p["title"].lower(): p["id"] for p in FEATURED_PROJECTS}
    for p in FEATURED_PROJECTS:
        for kw in p.get("mention_keywords", []):
            project_by_title[kw.lower()] = p["id"]

    mention_rels = 0
    described_rels = 0

    for sec_key, mentions in canonical.get("_source_section_mentions", {}).items():
        # sec_key format: "kb_biosketch:Section Name"  (matches Section.id in Neo4j)
        sec_id = sec_key

        for proj in mentions.get("projects", []):
            name       = (proj.get("name", "") if isinstance(proj, dict) else proj).strip()
            project_id = project_by_title.get(name.lower())
            if not project_id:
                continue
            context = (proj.get("context", "") if isinstance(proj, dict) else "")[:200]
            session.run(
                """
                MATCH (s:Section {id: $sid}), (p:Project {id: $pid})
                MERGE (s)-[:MENTIONS {context: $ctx}]->(p)
                MERGE (p)-[:DESCRIBED_IN]->(s)
                """,
                {"sid": sec_id, "pid": project_id, "ctx": context},
            )
            mention_rels  += 1
            described_rels += 1

        for skill in mentions.get("skills", []):
            name = (skill.get("name", "") if isinstance(skill, dict) else skill).strip()
            if not name:
                continue
            session.run(
                """
                MATCH (s:Section {id: $sid})
                MERGE (sk:Skill {name: $name})
                MERGE (s)-[:MENTIONS]->(sk)
                """,
                {"sid": sec_id, "name": name},
            )
            mention_rels += 1

        for concept in mentions.get("concepts", []):
            name = (concept.get("name", "") if isinstance(concept, dict) else concept).strip()
            if not name:
                continue
            session.run(
                """
                MATCH (s:Section {id: $sid})
                MERGE (c:Concept {name: $name})
                MERGE (s)-[:MENTIONS]->(c)
                """,
                {"sid": sec_id, "name": name},
            )
            mention_rels += 1

    print(f"  ✓ {mention_rels} MENTIONS + {described_rels} DESCRIBED_IN relationships")


def create_project_similarity(session) -> None:
    """Infer Project → RELATED_TO → Project from shared methods/technologies (≥2 shared)."""
    # Shared methods
    session.run("""
        MATCH (p1:Project)-[:USES_METHOD]->(m:Method)<-[:USES_METHOD]-(p2:Project)
        WHERE id(p1) < id(p2)
        WITH p1, p2, count(m) AS shared
        WHERE shared >= 2
        MERGE (p1)-[r:RELATED_TO]->(p2)
        SET r.shared_methods = shared, r.basis = "methods"
    """)
    # Shared technologies
    session.run("""
        MATCH (p1:Project)-[:USES_TECHNOLOGY]->(t:Technology)<-[:USES_TECHNOLOGY]-(p2:Project)
        WHERE id(p1) < id(p2)
        WITH p1, p2, count(t) AS shared
        WHERE shared >= 2
        MERGE (p1)-[r:RELATED_TO]->(p2)
        ON MATCH SET r.shared_technologies = shared
        ON CREATE SET r.shared_technologies = shared, r.basis = "technologies"
    """)
    result = session.run("MATCH ()-[r:RELATED_TO]->() RETURN count(r) AS cnt")
    print(f"  ✓ {result.single()['cnt']} RELATED_TO relationships")


def print_summary(session) -> None:
    print()
    for label in ["Document", "Section", "Project", "Skill", "Method", "Technology", "Concept"]:
        cnt = session.run(f"MATCH (n:{label}) RETURN count(n) AS cnt").single()["cnt"]
        print(f"  {label:<15} {cnt:>4} nodes")
    total_rels = session.run("MATCH ()-[r]->() RETURN count(r) AS cnt").single()["cnt"]
    print(f"  {'Relationships':<15} {total_rels:>4} total")


def main():
    if not CANONICAL.exists():
        print(f"❌ {CANONICAL} not found — run canonicalize_entities.py first")
        sys.exit(1)

    if not INPUTS_PATH.exists():
        print(f"⚠️  INPUTS_PATH not set or missing: {INPUTS_PATH}")
        print("   Document/Section nodes will be empty. Set INPUTS_PATH in .env")

    canonical = json.loads(CANONICAL.read_text())
    driver    = get_driver()

    with driver.session() as session:
        print("\n[0] Clear graph")
        clear_graph(session)

        print("\n[1] Document + Section nodes")
        create_document_sections(session)

        print("\n[2] Project nodes")
        create_projects(session)

        print("\n[3] Entity nodes (Skill / Method / Technology / Concept)")
        create_entity_nodes(session, canonical)

        print("\n[4] Project → entity relationships")
        create_project_entity_relationships(session, canonical)

        print("\n[5] Section mention relationships")
        create_section_mention_relationships(session, canonical)

        print("\n[6] Project similarity (RELATED_TO)")
        create_project_similarity(session)

        print("\n=== Graph Summary ===")
        print_summary(session)

    close_driver()
    print("\n✓ Graph population complete!")
    print("  Next: python scripts/embed_sections.py")


if __name__ == "__main__":
    main()
