"""
curate_concepts.py
==================
One-time manual curation of the concepts list in canonical_entities.json.

Replaces the 265 noisy auto-extracted concepts with ~22 genuine theoretical
frameworks, cognitive science concepts, and AI/knowledge engineering paradigms
that are useful as graph nodes.

Run once, review the result, then proceed to populate_neo4j_graph.py.
"""

import json
from pathlib import Path

CANONICAL = Path(__file__).resolve().parent / "canonical_entities.json"

# ── Curated concept list ──────────────────────────────────────────────────────
# Criteria for inclusion:
#   - Genuine theoretical framework, cognitive science concept, or AI paradigm
#   - Appears meaningfully in Barbara's KB (not a biographical fact or quote)
#   - Useful as a graph node that sections can MENTION and projects can APPLY_IN
#
# Excluded (with reasons):
#   - Dissertation vision-science specifics (Saccade Latency, Foveal resolution, etc.)
#     → too narrow; not useful for retrieval about Barbara's current work
#   - Biographical facts (double major in EE/Biology) → not a concept
#   - Personal values / quotes (be here now, No Apologizing Ethos) → not a framework
#   - Skills/Technologies misclassified as concepts (NLP, Machine Learning, Neo4j)
#     → already exist in their own node type pools
#   - Bad Phase 3 merges (Google Cloud + Digital Transformation) → excluded entirely

CURATED_CONCEPTS = [
    {
        "name": "Sensemaking",
        "source": "kb_intellectual_foundations",
        "description": "How humans construct meaning from ambiguous, complex information; core lens for Barbara's work.",
        "alt_labels": ["Contextual sensemaking", "Collaborative sensemaking", "Organizational sensemaking"],
    },
    {
        "name": "Bayesian reasoning",
        "source": "kb_intellectual_foundations",
        "description": "Probabilistic updating of beliefs given new evidence; shapes how Barbara approaches uncertainty.",
        "alt_labels": ["Bayesian thinking", "Bayesian updating under uncertainty", "Belief updating", "Base rates", "Priors"],
    },
    {
        "name": "David Marr's levels of analysis",
        "source": "kb_intellectual_foundations",
        "description": "Computational / algorithmic / implementation distinction; Barbara's framework for system design.",
        "alt_labels": ["Marr's levels of analysis", "Computational level", "Algorithmic level",
                       "Implementation level", "Levels of analysis", "Information-processing systems"],
    },
    {
        "name": "Mental Models",
        "source": "kb_intellectual_foundations",
        "description": "Internal representations users and experts build of systems; central to human-centered design.",
        "alt_labels": ["Internal models", "mental model alignment"],
    },
    {
        "name": "Human-centered design",
        "source": "kb_philosophy-and-approach",
        "description": "Prioritizing user needs, comprehension, and adoption over technical elegance.",
        "alt_labels": [],
    },
    {
        "name": "Systems thinking",
        "source": "kb_intellectual_foundations",
        "description": "Understanding complex interdependencies rather than isolated components.",
        "alt_labels": ["systems-level thinking", "Systems-level mindset"],
    },
    {
        "name": "Meaning-making",
        "source": "kb_philosophy-and-approach",
        "description": "Transforming messy, raw data into usable insight — Barbara's core value proposition.",
        "alt_labels": ["Making Meaning from Messy Data", "Meaning from messy data",
                       "Data and meaning", "Data legibility", "knowledge usability"],
    },
    {
        "name": "Explainability",
        "source": "kb_philosophy-and-approach",
        "description": "Making AI/ML decisions transparent, inspectable, and trustable.",
        "alt_labels": ["Explainable AI", "Interpretability", "AI system trustability", "Inspectable AI Systems"],
    },
    {
        "name": "Representations and Constraints Framework",
        "source": "kb_dissertation_overview",
        "description": "Barbara's dissertation framework: perception shaped by representational constraints on internal models.",
        "alt_labels": ["Representational Constraints", "Representational framing", "Prior Knowledge in Perception"],
    },
    {
        "name": "Translational Research",
        "source": "kb_professional_positioning",
        "description": "Bridging academic research methods and real-world operational practice.",
        "alt_labels": ["Cognitive science applied to AI", "cognitive science applied to AI systems"],
    },
    {
        "name": "Grounded AI Systems",
        "source": "kb_philosophy-and-approach",
        "description": "AI that is operationally ready, verifiable, and trustworthy — not just technically functional.",
        "alt_labels": ["Grounded generation", "Data Trustability", "Operational readiness",
                       "Readiness for real operation", "Real-world usability"],
    },
    {
        "name": "Evaluation as a design problem",
        "source": "kb_philosophy-and-approach",
        "description": "Treating evaluation as a first-class design concern, not an afterthought.",
        "alt_labels": ["Evaluation mindset", "Evaluation framework", "Ground-truth evaluation",
                       "Evaluation Habit", "Evaluation as shared understanding"],
    },
    {
        "name": "Pragmatic design",
        "source": "kb_philosophy-and-approach",
        "description": "The gap between technically correct and actually useful; design for adoption, not demonstration.",
        "alt_labels": ["Design philosophy", "Gap between technically correct and actually useful",
                       "Build things people actually use", "Build-adopt gap", "Durable value creation", "Durable value"],
    },
    {
        "name": "Knowledge representation",
        "source": "kb_intellectual_foundations",
        "description": "How knowledge is structured, organized, and made navigable for humans and machines.",
        "alt_labels": ["Knowledge legibility", "information navigability", "knowledge organization",
                       "Entity-relationship modeling", "Semantic Rigor"],
    },
    {
        "name": "Transfer of domain knowledge",
        "source": "kb_intellectual_foundations",
        "description": "Applying cognitive science and academic research frameworks to practical AI/data problems.",
        "alt_labels": ["Transfer of Cognitive Habits", "Cognitive Journey",
                       "Cognitive Science in Engineering"],
    },
    {
        "name": "Ontology",
        "source": "kb_intellectual_foundations",
        "description": "Formal classification and organization of concepts within a domain.",
        "alt_labels": ["Ontology extraction"],
    },
    {
        "name": "Semantic Web",
        "source": "kb_intellectual_foundations",
        "description": "Linked data paradigm for making knowledge machine-readable and interoperable.",
        "alt_labels": ["Linked Open Data", "JSON-LD"],
    },
    {
        "name": "Contextual guidance",
        "source": "kb_dissertation_overview",
        "description": "Scene context and prior knowledge guide where attention goes; from Barbara's dissertation research.",
        "alt_labels": ["Scene context", "contextual priors", "Context-Driven Attention",
                       "Context-guided attention", "Prior knowledge"],
    },
    {
        "name": "Attention as a limited resource",
        "source": "kb_dissertation_overview",
        "description": "Cognitive resource allocation under constraints; influences how Barbara thinks about information overload.",
        "alt_labels": ["Attention allocation", "Resource allocation under constraints",
                       "Attention Allocation Under Uncertainty", "Exploration vs Exploitation"],
    },
    {
        "name": "Design for the downstream mental model",
        "source": "kb_philosophy-and-approach",
        "description": "Shape what users will build in their heads, not just what the system outputs.",
        "alt_labels": ["Downstream decision-making", "decision grounding", "Problem representation"],
    },
    {
        "name": "Durable knowledge systems",
        "source": "kb_philosophy-and-approach",
        "description": "Systems that hold up over time, remain inspectable, and accumulate value rather than decay.",
        "alt_labels": ["durable value", "Timestamp-grounded traceability", "data generation tracing"],
    },
    {
        "name": "Hypothesis-driven design",
        "source": "kb_philosophy-and-approach",
        "description": "Starting from a testable claim about the world before building; experimental rigor applied to product.",
        "alt_labels": ["hypothesis-driven design", "Experimental rigor", "Hypothesis revision"],
    },
]


def main():
    data = json.loads(CANONICAL.read_text())
    old_count = len(data.get("concepts", []))
    data["concepts"] = CURATED_CONCEPTS
    CANONICAL.write_text(json.dumps(data, indent=2))
    print(f"✓ Replaced {old_count} auto-extracted concepts → {len(CURATED_CONCEPTS)} curated concepts")
    print(f"  Saved to {CANONICAL.name}")
    print()
    print("Curated concepts:")
    for c in CURATED_CONCEPTS:
        alts = f"  [{', '.join(c['alt_labels'])}]" if c["alt_labels"] else ""
        print(f"  • {c['name']}{alts}")


if __name__ == "__main__":
    main()
