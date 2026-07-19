# Changelog

Notable changes to the Digital Twin. This is a personal, single-maintainer project, so
this log is curated by hand from the commit history rather than generated — it captures the
changes that affect how the system is run, deployed, or reasoned about.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Changed
- **Documentation accuracy pass** — corrected metric drift across README, CLAUDE.md, and
  `docs/`: test count (47, not 51), eval suite (58 questions / 7 categories, not 92 / 8),
  removed the unverifiable `~16μs` logging-overhead figure, and fixed the `app.py` default
  model (`gpt-4.1`) and temperature (`0.7`) references.
- **Backend framing corrected** — ChromaDB is documented as the *current* production backend
  at `twin.barbhs.com`; Neo4j GraphRAG is the `graphy.` preview backend, in validation. The
  roadmap's "Neo4j backend" item is marked done (shipped, selectable via `RETRIEVAL_BACKEND`).

## 2026-07-18

### Added
- `scripts/retract_sources.py` — retire chunks by exact `source` value (dry-run by default).
- Source keys for consolidated project summaries (`project-chronoscope`, `project-poolula`,
  `project-beehive`).

### Changed
- `featured_projects.py` walkthrough data extracted to a generated `featured_projects.yaml`;
  retrieval/selection logic unchanged.
- `deploy-ec2` workflow now refreshes ChromaDB from the HF Hub dataset on every deploy.

## 2026-06

### Added
- Material for MkDocs documentation site (`mkdocs.yml`, `mkdocs-docs/`), published at
  docs.barbhs.com/twin/.

### Changed
- Documentation corrected for the consolidated single-codebase backend and the NEXT_SECTION
  neighbor-expansion behavior in the Neo4j pipeline.

## 2026-06-01

### Added
- **`RETRIEVAL_BACKEND` feature flag** — consolidates the `main` and `feat/graphy-preview`
  branches into one codebase. Each deployment's `.env` selects `neo4j` or `chromadb`.

## 2026-05

### Added
- Evaluation tooling: `compare_runs` admin tool for side-by-side eval run comparison.
- `replay_retrieval.py` — Neo4j retrieval debugger with `--compare` (Neo4j vs ChromaDB).

### Changed
- Composite scoring weights rebalanced (semantic 0.85 dominant) after a graph-bonus
  hallucination — see `docs/LESSONS_LEARNED.md` Entry 001.
