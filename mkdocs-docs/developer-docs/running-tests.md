---
title: Running Tests
tags:
  - developer
  - testing
  - qa
---

# Running Tests

The project uses a three-tier QA strategy designed for a solo project where engineering time is scarce but the app is publicly accessible and used in hiring contexts.

---

## Quick Start

```bash
.venv/bin/pytest tests/ -v
```

47 pure-logic unit tests. No API keys or network required. Completes in under a second. Run before any push to `main`.

---

## The Three Tiers

| Tier | What it covers | Tool | When to run |
|---|---|---|---|
| **1 — Pure Logic** | Deterministic functions, no external deps | `pytest tests/` | Every commit, automated in CI |
| **2 — Integration Health** | External service plumbing (API keys, DB, routing) | `scripts/healthcheck.py` | Manually before deploy |
| **3 — Behavioral Quality** | LLM accuracy, tone, retrieval quality | `evals/run_evals.py` | Deliberately after KB/prompt/model changes |

---

## Tier 1: Unit Tests

### What's covered

| Test class | Functions tested |
|---|---|
| `TestDiceRoll` | `dice_roll()` — range and type |
| `TestDetectAudienceTier` | `detect_audience_tier()` — tier logic, case-insensitivity, history scanning |
| `TestBuildSensitivityFilter` | `build_sensitivity_filter()` — ChromaDB filter shape per tier |
| `TestModelSupportsTools` | `model_supports_tools()` — blocklist behavior |
| `TestComputeSimilarityStats` | `_compute_similarity_stats()` — L2→cosine math, clamping, empty input |
| `TestRedactLogText` | `_redact_log_text()` — email and phone redaction |
| `TestBuildResponsePreview` | `_build_response_preview()` — truncation, newline collapsing |
| `TestHandleToolCall` | `handle_tool_call()` — dispatch, ID threading, unknown function |

### How import isolation works

`app.py` has module-level side effects: API key check, OpenAI client creation, `SYSTEM_PROMPT.md` read. `tests/conftest.py` handles all of these before the import:

- Sets a dummy `OPENAI_API_KEY`
- Patches the OpenAI constructor with a mock
- Sets the working directory to the project root

No `.env` file or real credentials are needed to run the test suite.

### CI gate

Every push to `main` runs `pytest tests/ -v` automatically before deploying to EC2. If any test fails, the deploy is blocked. The EC2 instance is not touched.

```
push to main
    │
    ▼
┌────────┐  fails  ┌──────────────────────┐
│  test  │────────▶│  deploy blocked       │
│  job   │         └──────────────────────┘
└───┬────┘
    │ passes
    ▼
┌────────────────────────────────┐
│  deploy job                    │
│  git pull → pip install        │
│  → systemctl restart           │
│  → smoke test (HTTP 200)       │
└────────────────────────────────┘
```

---

## Tier 2: Integration Healthcheck

```bash
# Validate all external services (no notification sent)
python scripts/healthcheck.py

# Run specific checks only
python scripts/healthcheck.py --checks env chroma

# Full end-to-end: also sends a Pushover test notification
python scripts/healthcheck.py --notify
```

**Checks covered:**

| Check | Pass condition |
|---|---|
| Environment variables | All required vars are set |
| OpenAI LLM | Gets any completion with `max_tokens=1`, no auth error |
| OpenAI embeddings | Returns a valid embedding vector |
| ChromaDB | `collection.count() > 0` with the expected collection name |
| Pushover credentials | Accepted by API (credential validation only by default) |

All checks pass in ~3 seconds. Exit code 1 if anything fails.

!!! warning "Do not run in CI automatically"
    Tier 2 healthcheck involves live LLM calls (cost) and Pushover notifications. Run it manually before any deploy touching credentials, environment config, or ChromaDB.

---

## Tier 3: Behavioral Evaluation

Run after: editing `SYSTEM_PROMPT.md`, changing KB content, changing model/temperature/top-k, or before deployment.

```bash
cd evals/
python run_evals.py
python analyze_evals.py --export
```

The eval harness runs 58 questions across 7 categories through the full RAG pipeline. Each row in `evals/eval_questions.csv` carries a category and an intent type so reports can segment by both axes:

| Category | Count | What it probes |
|---|---|---|
| `bio` | 11 | Biographical and identity Q&A |
| `personality` | 10 | Voice, values, "what drives you" |
| `projects` | 15 | Project walkthroughs and tradeoffs |
| `technical` | 10 | Architecture, retrieval, scoring |
| `tool` | 5 | Function-call paths (`send_notification`, `dice_roll`) |
| `front-example` | 4 | Curated landing-page example prompts |
| `user-submitted` | 3 | Real visitor questions promoted into the suite |

Intent distribution: 46 `bounded_open`, 11 `closed_fact`, 1 `open_persona`.

Cost: ~$0.21 per full run.

### When to run evals

| Change type | Run evals? |
|---|---|
| `SYSTEM_PROMPT.md` edit | Yes — always |
| KB document added/updated | Yes |
| Retrieval parameter change | Yes |
| LLM model upgrade | Yes — compare old vs. new model |
| UI or logging code change | No |
| Dependency version bump | No (unless it touches LiteLLM/ChromaDB) |

See [`evals/EVALUATION_GUIDE.md`](https://github.com/dagny099/barbs-digital-twin/blob/main/evals/EVALUATION_GUIDE.md) for the full evaluation design rationale.

### Comparing two runs

After running evals more than once, launch the side-by-side viewer to diff any two runs question-by-question:

```bash
python evals/compare_runs.py     # http://localhost:7863
```

It pre-selects the two most recent `eval_results/eval_results_*.json` files and flags chunks that appear in only one of the runs. Use it whenever a prompt edit, scoring-weight change, or model upgrade is in flight — it makes regressions obvious before they ship. See [Debug Tools](debug-tools.md#evalscompare_runspy-ab-eval-run-viewer) for the full reference.
