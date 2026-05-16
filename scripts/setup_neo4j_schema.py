#!/usr/bin/env python3
"""
setup_neo4j_schema.py
=====================
Idempotent DDL script for the Digital Twin Neo4j schema.

Run order: constraints → property indexes → vector index → verification.
Safe to run multiple times — all statements use IF NOT EXISTS.

Usage:
    python scripts/setup_neo4j_schema.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neo4j_utils import get_driver, close_driver

# ── Schema statements ──────────────────────────────────────────────────────────

CONSTRAINTS = [
    (
        "project_id",
        "CREATE CONSTRAINT project_id IF NOT EXISTS "
        "FOR (p:Project) REQUIRE p.id IS UNIQUE",
    ),
    (
        "skill_name",
        "CREATE CONSTRAINT skill_name IF NOT EXISTS "
        "FOR (s:Skill) REQUIRE s.name IS UNIQUE",
    ),
    (
        "method_name",
        "CREATE CONSTRAINT method_name IF NOT EXISTS "
        "FOR (m:Method) REQUIRE m.name IS UNIQUE",
    ),
    (
        "tech_name",
        "CREATE CONSTRAINT tech_name IF NOT EXISTS "
        "FOR (t:Technology) REQUIRE t.name IS UNIQUE",
    ),
]

PROPERTY_INDEXES = [
    (
        "section_sensitivity",
        "CREATE INDEX section_sensitivity IF NOT EXISTS "
        "FOR (s:Section) ON (s.sensitivity)",
    ),
    (
        "document_source_type",
        "CREATE INDEX document_source_type IF NOT EXISTS "
        "FOR (d:Document) ON (d.source_type)",
    ),
]

VECTOR_INDEX = (
    "section_embeddings",
    """
    CREATE VECTOR INDEX section_embeddings IF NOT EXISTS
    FOR (s:Section) ON s.embedding
    OPTIONS {indexConfig: {
        `vector.dimensions`: 1536,
        `vector.similarity_function`: 'cosine'
    }}
    """,
)


def run_statements(driver, statements: list[tuple[str, str]], label: str) -> int:
    """Run a list of (name, cypher) tuples, printing ✓/✗ per statement.
    Returns count of failures.
    """
    failures = 0
    with driver.session() as session:
        for name, cypher in statements:
            try:
                session.run(cypher)
                print(f"  ✓  {name}")
            except Exception as exc:
                print(f"  ✗  {name}: {exc}")
                failures += 1
    return failures


def verify_schema(driver) -> bool:
    """Check that all 4 constraints and the vector index are ONLINE."""
    with driver.session() as session:
        constraints = {
            row["name"]
            for row in session.run("SHOW CONSTRAINTS YIELD name")
        }
        indexes = {
            row["name"]: row["state"]
            for row in session.run("SHOW INDEXES YIELD name, state")
        }

    expected_constraints = {"project_id", "skill_name", "method_name", "tech_name"}
    missing = expected_constraints - constraints
    vector_state = indexes.get("section_embeddings", "MISSING")

    print("\n── Verification ──────────────────────────────────────────────")
    for name in sorted(expected_constraints):
        status = "✓" if name in constraints else "✗  MISSING"
        print(f"  constraint {name}: {status}")
    print(f"  vector index section_embeddings: {vector_state}")

    ok = not missing and vector_state == "ONLINE"
    return ok


def main() -> int:
    driver = get_driver()
    failures = 0

    print("── Constraints ───────────────────────────────────────────────")
    failures += run_statements(driver, CONSTRAINTS, "constraint")

    print("── Property indexes ──────────────────────────────────────────")
    failures += run_statements(driver, PROPERTY_INDEXES, "index")

    print("── Vector index ──────────────────────────────────────────────")
    failures += run_statements(driver, [VECTOR_INDEX], "vector index")

    ok = verify_schema(driver)
    close_driver()

    if failures or not ok:
        print("\n✗  Schema setup completed with errors.")
        return 1
    print("\n✓  Schema setup complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
