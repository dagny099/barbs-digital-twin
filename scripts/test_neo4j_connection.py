#!/usr/bin/env python3
"""
test_neo4j_connection.py
========================
Smoke test for the Neo4j connection and schema readiness.

Checks:
    1. Driver connects and `RETURN 1` executes
    2. Vector index `section_embeddings` is ONLINE
    3. All 4 required constraints are present

Exits 0 on pass, 1 on any failure.

Usage:
    python scripts/test_neo4j_connection.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neo4j_utils import get_driver, close_driver

REQUIRED_CONSTRAINTS = {"project_id", "skill_name", "method_name", "tech_name"}
REQUIRED_VECTOR_INDEX = "section_embeddings"


def check_connectivity(driver) -> bool:
    try:
        with driver.session() as session:
            result = session.run("RETURN 1 AS result").single()
            assert result["result"] == 1
        return True
    except Exception as exc:
        print(f"  ✗  connectivity: {exc}")
        return False


def check_vector_index(driver) -> bool:
    with driver.session() as session:
        rows = list(session.run(
            "SHOW INDEXES YIELD name, state WHERE name = $name",
            name=REQUIRED_VECTOR_INDEX,
        ))
    if not rows:
        print(f"  ✗  vector index '{REQUIRED_VECTOR_INDEX}': NOT FOUND")
        return False
    state = rows[0]["state"]
    ok = state == "ONLINE"
    mark = "✓" if ok else "✗"
    print(f"  {mark}  vector index '{REQUIRED_VECTOR_INDEX}': {state}")
    return ok


def check_constraints(driver) -> bool:
    with driver.session() as session:
        present = {
            row["name"]
            for row in session.run("SHOW CONSTRAINTS YIELD name")
        }
    all_ok = True
    for name in sorted(REQUIRED_CONSTRAINTS):
        if name in present:
            print(f"  ✓  constraint '{name}'")
        else:
            print(f"  ✗  constraint '{name}': MISSING")
            all_ok = False
    return all_ok


def main() -> int:
    uri = os.environ.get("NEO4J_URI", "(not set)")
    user = os.environ.get("NEO4J_USER", "(not set)")
    print(f"  Connecting to: {uri}  (user={user})")

    driver = get_driver()
    results = {}

    print("── Connectivity ──────────────────────────────────────────────")
    results["connectivity"] = check_connectivity(driver)
    if not results["connectivity"]:
        close_driver()
        print("\n✗  Auth failed — check NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD in .env")
        return 1
    print("  ✓  connected")

    print("── Vector index ──────────────────────────────────────────────")
    results["vector_index"] = check_vector_index(driver)

    print("── Constraints ───────────────────────────────────────────────")
    results["constraints"] = check_constraints(driver)

    close_driver()

    print("\n── Summary ───────────────────────────────────────────────────")
    all_passed = all(results.values())
    for check, passed in results.items():
        print(f"  {'✓' if passed else '✗'}  {check}")

    if all_passed:
        print("\n✓  All checks passed.")
        return 0
    else:
        print("\n✗  Some checks failed. Run scripts/setup_neo4j_schema.py first.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
