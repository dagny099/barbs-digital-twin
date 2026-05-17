"""
export_concepts_for_review.py
==============================
Option B: Export raw extracted concepts to a flat file for external review
(e.g., paste into Claude Web for manual curation).

Reads the pre-canonicalization data from extracted_entities.json and writes:
    scripts/concepts_raw_for_review.txt   — one concept per line, with source section
    scripts/concepts_canonical_for_review.txt — post-canonicalization list (current state)

Paste either file into Claude Web with this prompt:
    "Here are concept names extracted from a knowledge base about a data scientist.
     Keep only genuine theoretical frameworks, cognitive science concepts, and
     AI/knowledge engineering paradigms. Drop biographical facts, personal values,
     dissertation-specific vision science terms, and anything better classified as
     a Skill or Technology. Output a JSON array of objects with keys: name, description,
     alt_labels (list of synonyms to merge under this name)."
"""

import json
from pathlib import Path
from collections import defaultdict

SCRIPTS_DIR = Path(__file__).resolve().parent
EXTRACTED   = SCRIPTS_DIR / "extracted_entities.json"
CANONICAL   = SCRIPTS_DIR / "canonical_entities.json"
RAW_OUT     = SCRIPTS_DIR / "concepts_raw_for_review.txt"
CANON_OUT   = SCRIPTS_DIR / "concepts_canonical_for_review.txt"


def main():
    # ── Raw concepts (pre-canonicalization, with source section) ──────────────
    if EXTRACTED.exists():
        data = json.loads(EXTRACTED.read_text())
        by_concept: dict[str, list[str]] = defaultdict(list)

        for sec_id, mentions in data.get("section_mentions", {}).items():
            for concept in mentions.get("concepts", []):
                name = (concept.get("name", "") if isinstance(concept, dict) else concept).strip()
                if name:
                    by_concept[name].append(sec_id)

        lines = [
            "RAW EXTRACTED CONCEPTS (pre-canonicalization)",
            f"Total: {len(by_concept)} unique names",
            "Format: concept name  |  source section(s)",
            "=" * 70,
            "",
        ]
        for name in sorted(by_concept.keys(), key=str.lower):
            sources = "; ".join(sorted(set(s.split(":")[0] for s in by_concept[name])))
            lines.append(f"{name}  |  {sources}")

        RAW_OUT.write_text("\n".join(lines))
        print(f"✓ {RAW_OUT.name}  ({len(by_concept)} raw concept names)")
    else:
        print(f"⚠️  {EXTRACTED.name} not found — skipping raw export")

    # ── Canonical concepts (post-canonicalization, current state) ─────────────
    if CANONICAL.exists():
        data = json.loads(CANONICAL.read_text())
        concepts = data.get("concepts", [])

        lines = [
            "CANONICAL CONCEPTS (post-canonicalization)",
            f"Total: {len(concepts)} canonical nodes",
            "Format: canonical name  →  alt_labels (merged synonyms)",
            "=" * 70,
            "",
        ]
        for c in sorted(concepts, key=lambda x: x["name"].lower()):
            alts = f"  →  {c['alt_labels']}" if c.get("alt_labels") else ""
            lines.append(f"{c['name']}{alts}")

        CANON_OUT.write_text("\n".join(lines))
        print(f"✓ {CANON_OUT.name}  ({len(concepts)} canonical concepts)")
    else:
        print(f"⚠️  {CANONICAL.name} not found")

    print()
    print("Paste either file into Claude Web with:")
    print('  "Here are concept names extracted from a data scientist\'s knowledge base.')
    print("   Keep only genuine theoretical frameworks, cognitive science concepts, and")
    print("   AI/knowledge engineering paradigms. Drop biographical facts, personal values,")
    print("   dissertation-specific vision science terms, and anything better classified as")
    print("   a Skill or Technology. Output a JSON array of objects with keys: name,")
    print('   description, alt_labels (list of synonyms to merge under this name)."')


if __name__ == "__main__":
    main()
