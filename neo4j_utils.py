"""
neo4j_utils.py
==============
Neo4j driver factory and connection helpers for the Digital Twin graph.

Provides a module-level singleton driver so all scripts share one connection pool.
LLM configuration stays in utils.py / litellm — not duplicated here.

Usage:
    from neo4j_utils import get_driver, close_driver

    driver = get_driver()
    with driver.session() as session:
        session.run("RETURN 1")
    close_driver()
"""

import os
from neo4j import GraphDatabase, Driver
from dotenv import load_dotenv

load_dotenv()

_driver: Driver | None = None


def get_driver() -> Driver:
    """Return the module-level Neo4j driver, creating it on first call."""
    global _driver
    if _driver is None:
        uri = os.environ["NEO4J_URI"]
        user = os.environ["NEO4J_USER"]
        password = os.environ["NEO4J_PASSWORD"]
        _driver = GraphDatabase.driver(uri, auth=(user, password))
    return _driver


def close_driver() -> None:
    """Close the driver and release all connections."""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
