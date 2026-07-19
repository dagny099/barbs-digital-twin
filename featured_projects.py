"""
featured_projects.py
====================
Selection logic for project walkthrough responses and diagram serving.

Architecture (v3 — data moved to featured_projects.yaml):

  The FEATURED_PROJECTS data now lives in `featured_projects.yaml`, generated
  by the twin-freshness pipeline (`python run.py derive` in that repo).
  Entries whose project has an approved consolidated summary carry a
  `derived_from` key: their summary / design_insight / walkthrough_context
  come from that summary file — edit the summary (then re-derive), not the
  YAML. Hand-curated fields (title, keywords, tags, diagram, links) are
  edited directly in the YAML. This module keeps ALL the selection/serving
  logic, unchanged from v2:

  1. Walkthrough detection  — regex on "walk me through", "show me a project", etc.
     Triggers full walkthrough enrichment (context injected into user message).

  2. Project mention detection — keyword match on project titles, tags, key terms.
     Triggers diagram serving. Much broader than walkthrough detection.

  3. Diagram serving is its own capability — fires on ANY project mention,
     not just walkthrough requests.

  4. Walkthrough mode is hybrid — walkthrough context is injected as a
     separate block (not appended to user message), so RAG retrieval
     stays grounded in the user's actual question.

To add a new project:
    1. Add a diagram image to assets/project_diagrams/
    2. Append a new entry to featured_projects.yaml (or, preferred, run the
       twin-freshness consolidation pass so the entry is derived)
    3. That's it — the selection logic picks it up automatically

Fields per project:
    - id (str):                  URL-safe identifier
    - title (str):               Display name
    - summary (str):             2-3 sentence overview (used for casual mentions too)
    - design_insight (str):      1-2 sentences on what makes this project distinctive —
                                 gives the LLM a narrative lead for "stories before specs"
    - walkthrough_context (str): Full pipeline/architecture walkthrough for deep dives
    - diagram_filename (str):    Filename in assets/project_diagrams/
    - diagram_caption (str):     Alt-text / caption for diagram
    - tags (list[str]):          Searchable topic tags
    - mention_keywords (list):   Phrase-level triggers for project detection
    - links (dict):              Operational URLs — live demo, github, docs
    - blog_posts (list[dict]):   Blog posts / writeups about the project
                                 Each entry: {"title": str, "url": str}
                                 Rendered separately from links in context block
    - derived_from (str):        Present on derived entries: provenance
                                 "<summary path>@<repo sha>" (informational)
"""

import os
import re
import random

import yaml

# ═══════════════════════════════════════════════════════════════════
# PROJECT DATA — loaded from the generated YAML (see module docstring)
# ═══════════════════════════════════════════════════════════════════

_DIAGRAM_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "assets", "project_diagrams")

_YAML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "featured_projects.yaml")

with open(_YAML_PATH, encoding="utf-8") as _f:
    FEATURED_PROJECTS = yaml.safe_load(_f)["projects"]


# ═══════════════════════════════════════════════════════════════════
# HELPERS — WALKTHROUGH DETECTION (narrow, intent-based)
# ═══════════════════════════════════════════════════════════════════

def load_featured_projects() -> list[dict]:
    """Return the list of featured projects."""
    return FEATURED_PROJECTS


# ── Names used in regex patterns ────────────────────────────────
# Keep this in sync with FEATURED_PROJECTS titles/aliases.
# Lowercase, no regex special chars. Used for intent detection only.
_PROJECT_NAMES = (
    "cartograph|explorer|digital\\s*twin|beehive|fitness|"
    "citation|poolula|convoscope|memories|weaving|chronoscope"
)

def _is_walkthrough_request(message: str) -> bool:
    """
    Return True if the user message is asking for a project walkthrough.

    Two detection strategies:
      1. VERB-BASED — "walk me through", "show me", "describe" + project/generic
      2. NAME-BASED — "tell me about [project name]", "how does [project name] work"

    Kept deliberately broad: false positives are cheap (we just inject
    extra context + show a diagram), false negatives mean the visitor
    gets a worse answer.
    """
    patterns = [
        # ── Verb-based: walkthrough intent verbs ─────────────────
        # "walk me through X" — matches regardless of what X is
        r"walk\s*(me\s+)?through",
        # "show me a project"
        r"show\s+me\s+a\s+project",
        # "portfolio project", "featured project"
        r"(portfolio|featured)\s+project",
        # "project you're proud of / built / worked on"
        r"project\s+you.*(proud|excited|built|worked)",
        r"(proud|excited)\s+.*(project|built)",

        # ── Name-based: project name in an explanatory request ───
        # "tell me about [project]" / "talk about [project]"
        rf"(tell|talk)\s+(me\s+)?about\s+.*({_PROJECT_NAMES}|project)",
        # "explain [project]" / "describe [project]"
        rf"(explain|describe)\s+.*?({_PROJECT_NAMES}|project)",
        # "how does [project] work/handle/do"
        rf"how\s+(does|did|do|is)\s+.*({_PROJECT_NAMES})",
    ]
    lower = message.lower()
    return any(re.search(p, lower) for p in patterns)


# ═══════════════════════════════════════════════════════════════════
# HELPERS — PROJECT MENTION DETECTION (broad, keyword-based)
# ═══════════════════════════════════════════════════════════════════

def _score_project_mention(message: str, project: dict) -> int:
    """
    Score how strongly a message mentions a specific project.

    Checks (in priority order):
      1. Explicit mention_keywords (phrase match, high signal)
      2. Title substring match
      3. Tag overlap with message words

    Returns an integer score. 0 = no mention detected.
    """
    lower = message.lower()
    score = 0

    # Phrase-level keyword matches (highest signal)
    for kw in project.get("mention_keywords", []):
        if kw.lower() in lower:
            score += 10

    # Title match
    title_lower = project["title"].lower()
    if title_lower in lower:
        score += 8
    else:
        # Partial title words (less confident)
        title_words = set(re.findall(r'\w{4,}', title_lower))  # 4+ char words only
        msg_words = set(re.findall(r'\w+', lower))
        overlap = title_words & msg_words
        score += len(overlap) * 2

    # Tag overlap
    tags = set(project.get("tags", []))
    msg_words = set(re.findall(r'\w+', lower))
    score += len(tags & msg_words)

    return score


def find_mentioned_project(message: str) -> dict | None:
    """
    Find the project most strongly referenced by the message.

    Unlike select_project_for_walkthrough(), this does NOT require
    walkthrough intent — it fires on any project mention. Used for
    diagram serving.

    Returns None if no project scores above the minimum threshold.
    """
    min_threshold = 5  # Avoids false positives on vague messages

    best, best_score = None, 0
    for project in FEATURED_PROJECTS:
        score = _score_project_mention(message, project)
        if score > best_score:
            best, best_score = project, score

    if best_score >= min_threshold:
        return best
    return None


# ═══════════════════════════════════════════════════════════════════
# HELPERS — WALKTHROUGH SELECTION (narrow intent + keyword match)
# ═══════════════════════════════════════════════════════════════════

def select_project_for_walkthrough(user_message: str) -> dict | None:
    """
    Select a featured project for a full walkthrough response.

    Returns None if the message doesn't look like a walkthrough request.
    When it is a walkthrough request, tries keyword matching against
    title/summary/tags, falling back to the first project.
    """
    if not _is_walkthrough_request(user_message):
        return None

    projects = load_featured_projects()
    if not projects:
        return None

    # Try mention-based matching first (more precise)
    mentioned = find_mentioned_project(user_message)
    if mentioned:
        return mentioned

    # Fallback: Pure random for generic queries, word overlap for specific ones
    # Extract meaningful words (filter out common stopwords and short words)
    all_words = set(re.findall(r'\w+', user_message.lower()))
    stopwords = {'the', 'through', 'project', 'walk', 'tell', 'about', 'me', 'a', 'an',
                 'show', 'describe', 'explain', 'talk', 'of', 'for', 'to', 'in', 'on'}
    meaningful_words = {w for w in all_words if len(w) > 2 and w not in stopwords}

    # If query is too generic (fewer than 2 meaningful words), randomize
    if len(meaningful_words) < 2:
        return random.choice(projects)

    # Otherwise, use word overlap scoring for relevance
    # Use meaningful_words (not all_words) to avoid matching on noise like "a", "of", "the"
    # Group projects by score to handle ties with randomization
    score_groups = {}
    for project in projects:
        searchable = " ".join([
            project["title"].lower(),
            project["summary"].lower(),
            " ".join(project.get("tags", [])),
        ])
        score = len(meaningful_words & set(re.findall(r'\w+', searchable)))
        score_groups.setdefault(score, []).append(project)

    # Return random choice from highest-scoring group
    best_score = max(score_groups.keys())
    return random.choice(score_groups[best_score])

    # TODO (Future Enhancement - Option 4): Session-aware diversity
    # Track shown_projects per session and boost scores for unseen projects (+10 bonus).
    # This ensures users explore full portfolio over multiple queries instead of seeing
    # the same project repeatedly for generic walkthrough requests.
    # See MAINTAINER_GUIDE.md Roadmap for full design details.


# ═══════════════════════════════════════════════════════════════════
# HELPERS — DIAGRAM SERVING (decoupled from walkthrough)
# ═══════════════════════════════════════════════════════════════════

def get_diagram_path(project: dict) -> str | None:
    """
    Return the absolute path to the project's diagram if it exists on disk.
    Returns None if the file is missing, so callers can gracefully omit the image.
    """
    filename = project.get("diagram_filename")
    if not filename:
        return None
    diagram_path = os.path.join(_DIAGRAM_DIR, filename)
    if os.path.isfile(diagram_path):
        return diagram_path
    return None


# ═══════════════════════════════════════════════════════════════════
# HELPERS — CONTEXT ENRICHMENT
# ═══════════════════════════════════════════════════════════════════

def build_walkthrough_context_block(project: dict) -> str:
    """
    Build a context block for walkthrough injection.

    This is injected as a SEPARATE context section (not appended to
    the user message), so RAG retrieval stays grounded in the user's
    actual question while the LLM still has the full walkthrough notes.

    Structure:
      - Title + summary (what it is)
      - Design insight (why it's distinctive — gives the LLM a narrative lead)
      - Walkthrough notes (how it works)
      - Project links (operational: demo, github, docs)
      - Related writing (blog posts / writeups — deeper context)
    """
    parts = [
        f"[WALKTHROUGH PROJECT: {project['title']}]",
        f"Summary: {project['summary']}",
    ]

    # Design insight gives the LLM "stories before specs" material
    if project.get("design_insight"):
        parts.append(f"What makes it distinctive: {project['design_insight']}")

    parts.append(f"Walkthrough notes: {project['walkthrough_context']}")

    # Operational links (demo, github, docs)
    links = {k: v for k, v in project.get("links", {}).items() if v}
    if links:
        lines = "\n".join(f"  - {label}: {url}" for label, url in links.items())
        parts.append(
            f"Project links (use these exact URLs only, do not modify or invent others):\n{lines}"
        )

    # Blog posts / writeups (separate from operational links)
    blog_posts = project.get("blog_posts") or []
    if blog_posts:
        lines = "\n".join(
            f'  - "{post["title"]}": {post["url"]}' for post in blog_posts
        )
        parts.append(
            f"Related writing (link when visitors want the story behind the project):\n{lines}"
        )

    return "\n".join(parts)


def enrich_message_for_walkthrough(message: str, project: dict) -> str:
    """
    DEPRECATED — kept for backward compatibility.
    Prefer build_walkthrough_context_block() + separate injection.

    Append project context to the user message so the LLM can generate
    a natural walkthrough grounded in the project's details.
    """
    links = {k: v for k, v in project.get("links", {}).items() if v}
    if links:
        lines = "\n".join(f"  - {label}: {url}" for label, url in links.items())
        links_block = f"\nProject links (use these exact URLs only, do not modify or invent others):\n{lines}"
    else:
        links_block = ""
    return (
        f"{message}\n\n"
        f"[Selected project for walkthrough: {project['title']}]\n"
        f"Summary: {project['summary']}\n"
        f"Walkthrough notes: {project['walkthrough_context']}"
        f"{links_block}"
    )
