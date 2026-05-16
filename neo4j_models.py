"""
neo4j_models.py
===============
Pydantic v2 validation models for all Neo4j node types in the Digital Twin graph.

These are pure data-validation models — no Neo4j driver interaction.
Each has a to_dict() method returning kwargs suitable for Cypher SET clauses.

Node types (from NEO4J_MIGRATION_PLAN_2026-05-14.md schema section):
    DocumentNode, SectionNode, ProjectNode, SkillNode, MethodNode,
    TechnologyNode, ConceptNode
"""

from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


class DocumentNode(BaseModel):
    id: str
    source_type: str
    file_path: str
    title: str
    sensitivity: str = "public"
    content_hash: str = ""
    last_updated: str = ""

    def to_dict(self) -> dict:
        return self.model_dump()


class SectionNode(BaseModel):
    id: str
    name: str
    full_text: str
    sensitivity: str = "public"
    order: int = 0
    char_count: int = 0

    @model_validator(mode="after")
    def set_char_count(self) -> "SectionNode":
        if self.char_count == 0:
            self.char_count = len(self.full_text)
        return self

    def to_dict(self) -> dict:
        return self.model_dump()


class ProjectNode(BaseModel):
    id: str
    title: str
    summary: str
    design_insight: str = ""
    walkthrough_context: str = ""
    diagram_filename: str = ""
    tags: List[str] = Field(default_factory=list)
    sensitivity: str = "public"

    def to_dict(self) -> dict:
        return self.model_dump()


class SkillNode(BaseModel):
    name: str
    category: str = ""
    alt_labels: List[str] = Field(default_factory=list)

    def to_dict(self) -> dict:
        return self.model_dump()


class MethodNode(BaseModel):
    name: str
    category: str = ""
    description: str = ""
    alt_labels: List[str] = Field(default_factory=list)

    def to_dict(self) -> dict:
        return self.model_dump()


class TechnologyNode(BaseModel):
    name: str
    category: str = ""
    alt_labels: List[str] = Field(default_factory=list)

    def to_dict(self) -> dict:
        return self.model_dump()


class ConceptNode(BaseModel):
    name: str
    source: str = ""
    description: str = ""
    alt_labels: List[str] = Field(default_factory=list)

    def to_dict(self) -> dict:
        return self.model_dump()
