"""
canonicalize_entities.py
========================
Phase 2 Step 2: Three-phase entity name normalization.

Phase 1 — Deterministic: lowercase grouping, prefer longest form
Phase 2 — Tag-anchored:  anchor to featured_projects.py tag readable forms
Phase 3 — LLM batch:     one Claude call per entity type for remaining ambiguities

Inputs:
    scripts/extracted_entities.json  (from extract_entities.py)

Outputs:
    scripts/canonical_entities.json          — for populate_neo4j_graph.py
    scripts/entity_normalization_report.json — audit trail; review before loading

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  WARNING: Re-running this script overwrites canonical_entities.json entirely,
    including the "concepts" list which was manually curated on 2026-05-16.

    If you need to re-run (e.g., after updating extracted_entities.json or
    changing normalization logic), run this immediately afterward to restore
    the curated concepts:

        python scripts/curate_concepts.py

    The right long-term fix — not yet implemented — is to save the curated
    concept list to scripts/concepts_curated.json and have this script read
    and preserve it rather than regenerating concepts from scratch each time.
    See Architectural Decision 4 in docs/NEO4J_MIGRATION_PLAN_2026-05-14.md.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from pathlib import Path
from dotenv import load_dotenv
import anthropic
from featured_projects import FEATURED_PROJECTS

load_dotenv(override=True)

SCRIPTS_DIR = Path(__file__).resolve().parent
INPUT_FILE  = SCRIPTS_DIR / "extracted_entities.json"
OUTPUT_FILE = SCRIPTS_DIR / "canonical_entities.json"
REPORT_FILE = SCRIPTS_DIR / "entity_normalization_report.json"
MODEL       = "claude-sonnet-4-6"


def get_all_tags() -> set[str]:
    tags = set()
    for p in FEATURED_PROJECTS:
        for tag in p.get("tags", []):
            tags.add(tag)
    return tags


def tag_to_readable(tag: str) -> str:
    return " ".join(w.capitalize() for w in tag.replace("-", " ").split())


def _strip_fences(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:])
        if raw.endswith("```"):
            raw = raw[:-3]
    return raw.strip()


def phase1_deterministic(entities: list[str]) -> dict[str, str]:
    """
    Group exact case-insensitive duplicates.
    Canonical: prefer the longest form (usually most descriptive).
    Returns {variant: canonical}.
    """
    groups: dict[str, list[str]] = {}
    for e in entities:
        groups.setdefault(e.lower().strip(), []).append(e)

    mapping = {}
    for variants in groups.values():
        canonical = max(variants, key=len)
        for v in variants:
            mapping[v] = canonical
    return mapping


def phase2_tag_anchored(mapping: dict[str, str], all_tags: set[str]) -> tuple[dict[str, str], list[dict]]:
    """
    If a canonical form case-insensitively matches a readable tag form,
    replace it with the tag's readable form.
    Returns (updated_mapping, decisions).
    """
    tag_lookup: dict[str, str] = {}
    for tag in all_tags:
        readable = tag_to_readable(tag)
        tag_lookup[readable.lower()] = readable

    decisions = []
    for variant, canonical in list(mapping.items()):
        canon_lower = canonical.lower()
        if canon_lower in tag_lookup:
            tag_form = tag_lookup[canon_lower]
            if canonical != tag_form:
                decisions.append({
                    "phase": 2,
                    "variant": variant,
                    "old_canonical": canonical,
                    "new_canonical": tag_form,
                    "reason": "matched featured_projects tag",
                })
                mapping[variant] = tag_form
    return mapping, decisions


def phase3_llm_batch(entity_type: str, entity_names: list[str],
                     client: anthropic.Anthropic, all_tags: set[str]) -> tuple[dict[str, str], list[dict]]:
    """
    LLM normalization for remaining ambiguities after phases 1 and 2.
    Conservative bias: only merge when highly confident.
    Returns (merge_map {variant: canonical}, decisions).
    """
    if len(entity_names) <= 1:
        return {}, []

    tag_readable = sorted({tag_to_readable(t) for t in all_tags})

    prompt = f"""You are normalizing a list of {entity_type} entity names extracted from a data scientist's project knowledge base.

Task: identify which names refer to the SAME concept and should be merged under one canonical label.

AUTHORITATIVE labels (from project tags — prefer these as canonical when merging):
{json.dumps(tag_readable, indent=2)}

EXTRACTED labels (free text from project descriptions):
{json.dumps(entity_names, indent=2)}

Rules:
1. Only group things you are HIGHLY CONFIDENT refer to the exact same concept.
2. Prefer authoritative labels as canonical names when merging.
3. Conservative bias — when in doubt, keep them separate.
4. "Neo4j" and "Neo4J" → merge (capitalization only). "Data Science" and "Machine Learning" → do NOT merge (related but distinct).

Return ONLY valid JSON with no markdown fences:
{{
  "groups": [
    {{
      "canonical": "chosen canonical name",
      "variants": ["other name 1", "other name 2"],
      "reasoning": "one-line explanation"
    }}
  ]
}}

Only include entities being merged in "groups". Entities not mentioned are kept as-is."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = _strip_fences(response.content[0].text)
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  ⚠️  JSON parse error in phase 3 (returning no merges): {e}")
        print(f"     Raw (first 300 chars): {raw[:300]}")
        return {}, []

    merge_map = {}
    decisions = []
    for group in result.get("groups", []):
        canonical = group["canonical"]
        for variant in group.get("variants", []):
            if variant != canonical:
                merge_map[variant] = canonical
                decisions.append({
                    "phase": 3,
                    "entity_type": entity_type,
                    "variant": variant,
                    "canonical": canonical,
                    "reasoning": group.get("reasoning", ""),
                })
    return merge_map, decisions


def collect_raw_entities(data: dict) -> dict[str, list[dict]]:
    """
    Gather extracted entities by type, deduplicated by name (case-insensitive).

    Source rules — intentional, not an oversight:
      Skills / Methods / Technologies → project_entities ONLY.
          Section mentions are relationship data (MENTIONS edges), not node definitions.
          Pulling skills from every KB section mention bloats the pool to 400+ names
          and defeats the purpose of structured project-level extraction.
      Concepts → section_mentions ONLY.
          Concepts (theoretical frameworks) appear in KB text, not in project walkthroughs.
    """
    result: dict[str, list[dict]] = {"skills": [], "methods": [], "technologies": [], "concepts": []}
    seen: dict[str, set[str]] = {t: set() for t in result}

    # Skills / Methods / Technologies: structured extraction from project walkthroughs only
    for entities in data.get("project_entities", {}).values():
        for skill in entities.get("skills", []):
            n = skill.get("name", "").strip()
            if n and n.lower() not in seen["skills"]:
                seen["skills"].add(n.lower())
                result["skills"].append(skill)
        for method in entities.get("methods", []):
            n = method.get("name", "").strip()
            if n and n.lower() not in seen["methods"]:
                seen["methods"].add(n.lower())
                result["methods"].append(method)
        for tech in entities.get("technologies", []):
            n = tech.get("name", "").strip()
            if n and n.lower() not in seen["technologies"]:
                seen["technologies"].add(n.lower())
                result["technologies"].append(tech)

    # Concepts: KB sections are their primary source (not project walkthroughs)
    for mentions in data.get("section_mentions", {}).values():
        for concept in mentions.get("concepts", []):
            n = (concept.get("name", "") if isinstance(concept, dict) else concept).strip()
            if n and n.lower() not in seen["concepts"]:
                seen["concepts"].add(n.lower())
                result["concepts"].append({"name": n, "source": "kb_sections", "description": ""})

    return result


def main():
    if not INPUT_FILE.exists():
        print(f"❌ {INPUT_FILE} not found — run extract_entities.py first")
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        sys.exit(1)

    data     = json.loads(INPUT_FILE.read_text())
    client   = anthropic.Anthropic(api_key=api_key)
    all_tags = get_all_tags()

    raw_by_type  = collect_raw_entities(data)
    all_decisions: list[dict] = []
    canonical_output: dict    = {}

    for entity_type, entities_list in raw_by_type.items():
        if not entities_list:
            canonical_output[entity_type] = []
            continue

        names = [e["name"] for e in entities_list]
        print(f"\n=== {entity_type.upper()} ({len(names)} raw names) ===")

        # Phase 1
        p1_map = phase1_deterministic(names)
        p1_decisions = [
            {"phase": 1, "variant": v, "canonical": c, "entity_type": entity_type}
            for v, c in p1_map.items() if v != c
        ]
        if p1_decisions:
            print(f"  Phase 1: {len(p1_decisions)} case/duplicate merges")
        all_decisions.extend(p1_decisions)

        # Phase 2
        p1_map, p2_decisions = phase2_tag_anchored(p1_map, all_tags)
        if p2_decisions:
            print(f"  Phase 2: {len(p2_decisions)} tag-anchored corrections")
        all_decisions.extend(p2_decisions)

        # Phase 3
        unique_canonicals = list(set(p1_map.values()))
        p3_map: dict[str, str] = {}
        p3_decisions: list[dict] = []
        if len(unique_canonicals) > 1:
            print(f"  Phase 3: LLM reviewing {len(unique_canonicals)} canonical names...")
            p3_map, p3_decisions = phase3_llm_batch(entity_type, unique_canonicals, client, all_tags)
            if p3_decisions:
                print(f"  Phase 3: {len(p3_decisions)} LLM merges")
            all_decisions.extend(p3_decisions)
        else:
            print(f"  Phase 3: skipped (only {len(unique_canonicals)} canonical name)")

        # Build final entities with alt_labels
        alt_labels_map: dict[str, set[str]] = {}
        final_name_for: dict[str, str] = {}
        for name in names:
            c1    = p1_map.get(name, name)
            final = p3_map.get(c1, c1)
            final_name_for[name] = final
            if name != final:
                alt_labels_map.setdefault(final, set()).add(name)

        canonical_details: dict[str, dict] = {}
        for e in entities_list:
            name  = e["name"]
            final = final_name_for.get(name, name)
            if final not in canonical_details:
                canonical_details[final] = {**e, "name": final}

        final_entities = []
        for canonical, details in canonical_details.items():
            alts = sorted(alt_labels_map.get(canonical, set()) - {canonical})
            final_entities.append({**details, "name": canonical, "alt_labels": alts})

        canonical_output[entity_type] = final_entities
        print(f"  → {len(names)} raw  →  {len(final_entities)} canonical")

    # Carry through the source data needed by populate_neo4j_graph.py
    canonical_output["_source_project_entities"] = data.get("project_entities", {})
    canonical_output["_source_section_mentions"] = data.get("section_mentions", {})

    OUTPUT_FILE.write_text(json.dumps(canonical_output, indent=2))
    REPORT_FILE.write_text(json.dumps({
        "decisions": all_decisions,
        "totals": {t: len(canonical_output.get(t, [])) for t in ["skills", "methods", "technologies", "concepts"]},
    }, indent=2))

    print(f"\n✓ {OUTPUT_FILE.name}")
    print(f"✓ {REPORT_FILE.name}")
    print(f"\n⚠️  Review {REPORT_FILE.name} before running populate_neo4j_graph.py")
    print(f"   Zero merges is a valid outcome — it means labels were already consistent.")


if __name__ == "__main__":
    main()
