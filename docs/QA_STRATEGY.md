# QA Strategy: Barb's Digital Twin

A lightweight, tiered approach to catching regressions without the overhead of
a full test suite. Written for a solo project where engineering time is scarce
but the app is publicly accessible and used in hiring contexts.

---

## Mental Model

Three tiers, each with a different failure mode and the right tool for it:

| Tier | What it covers | Failure mode | Approach |
|------|---------------|--------------|----------|
| 1 — Pure logic | Deterministic functions with no external deps | Silent regression after refactor | Automated unit tests |
| 2 — Integration health | External service plumbing (API keys, DB, routing) | Silent breakage after config/env change | Manual healthcheck script |
| 3 — Behavioral quality | LLM response accuracy, tone, retrieval quality | Quality drift after KB or prompt changes | Offline eval framework (existing) |

The goal is not to test everything — it's to catch the right failure at the right tier before a user does.

---

## Tier 1: Pure Logic — Unit Tests

**Trigger:** Run automatically on every commit (or manually before any push).  
**Cost:** ~30 min to write once, <1 second to run.  
**Lives in:** `tests/` (to be created)

### Functions to cover

| Function | Test scenario |
|----------|--------------|
| `dice_roll()` | Returns int in [1, 6] across many calls |
| `detect_audience_tier()` | Known phrases → expected tier (e.g. passphrase → `recruiter`, unknown → `public`) |
| `model_supports_tools()` | Returns `True` for known tool-capable model, `False` for known non-tool model |
| `_redact_log_text()` | Email and phone patterns are redacted; non-PII text is unchanged |
| `build_sensitivity_filter()` | Returns correct filter dict for each tier |
| `_compute_similarity_stats()` | Correct avg/max from a known distance list; handles empty input |
| `_build_response_preview()` | Truncates at `n` chars; doesn't crash on `None` |
| `handle_tool_call()` | Dispatches `dice_roll` → calls `dice_roll()`; dispatches `send_notification` → calls `send_notification()` with correct arg |

### Status

- [x] Create `tests/test_pure_logic.py` — 51 tests, all passing, runs in 0.16s
- [x] Add pytest to `requirements.txt` (dev deps)
- [ ] Wire into CI (add step before deploy in `deploy-ec2.yml`)

---

## Tier 2: Integration Health — Healthcheck Script

**Trigger:** Run manually before any deploy. Optionally wire into CI as a pre-deploy gate.  
**Cost:** ~1–2 hours to write, ~10 seconds to run.  
**Lives in:** `scripts/healthcheck.py`

### Checks to implement

| Check | What it verifies | Pass condition |
|-------|-----------------|----------------|
| OpenAI/LiteLLM | API key valid, configured model resolves | Gets any completion with `max_tokens=1`, no auth error |
| Pushover | Credentials present and accepted by API | POST to `/versions` or send a labeled "healthcheck" notification |
| ChromaDB | Collection exists and is populated | `collection.count() > 0` with the expected collection name |
| Tool routing | `handle_tool_call()` dispatches correctly end-to-end | Fake dice roll tool call → returns int in [1,6] |
| Env vars | Required vars are set | Fails fast with named missing var, not a cryptic downstream error |

### Design notes

- Do **not** run this in CI automatically — Pushover notifications would fire on every push and LLM calls cost money.
- Run it manually: `python scripts/healthcheck.py` before a deploy or after any `.env` change.
- Print a clear PASS/FAIL per check so failures are immediately obvious.
- Consider a `--dry-run` flag that skips the Pushover send (checks credentials only).

### Status

- [ ] Write `scripts/healthcheck.py`
- [ ] Add `--dry-run` flag for credential-only mode
- [ ] Document in `MAINTAINER_GUIDE.md`

---

## Tier 3: Behavioral Quality — Eval Framework

**Trigger:** Run deliberately after: system prompt edits, KB document changes, retrieval parameter tuning, or model upgrades.  
**Cost:** Already built (`evals/run_evals.py` + `evals/analyze_evals.py`). Incremental effort only.  
**Lives in:** `evals/`

### What's already working

- Questions bank in `evals/eval_questions.csv` with rich metadata (category, intent, must_cover, etc.)
- Full RAG pipeline execution per question
- Per-response feature analysis: word count, markdown usage, follow-up presence, project mentions, retrieval similarity
- Flagging of short/empty responses for manual review
- Export to CSV for human scoring

### Missing: a baseline to compare against

Without a reference run, each eval is a snapshot with no regression signal. The fix is simple:

1. Run evals on a known-good state and designate it the **baseline run**.
2. Store it as `evals/eval_results/baseline.json`.
3. On future runs, compare key aggregate metrics to the baseline:
   - Average similarity score (flag if drops > 0.05)
   - Count of responses < 30 words (flag if increases)
   - Success rate by category (flag any category that drops > 10%)

### When to run

| Change type | Run evals? |
|------------|-----------|
| System prompt edit | Yes — always |
| KB document added/updated | Yes |
| Retrieval parameter change (`N_CHUNKS_RETRIEVE`, embed model) | Yes |
| LLM model upgrade | Yes — compare old vs. new model |
| UI / logging code change | No |
| Dependency version bump | No (unless it touches LiteLLM/ChromaDB) |

### Status

- [ ] Run evals on current state → designate as `baseline.json`
- [ ] Add a `--compare-baseline` flag to `analyze_evals.py` that prints delta from baseline
- [ ] Define numeric thresholds for "regression" vs. "acceptable variance"

---

## CI / Deployment Integration

`.github/workflows/deploy-ec2.yml` is structured as two sequential jobs:

```
push to main
    │
    ▼
┌─────────┐   fails   ┌─────────────────────────┐
│  test   │──────────▶│  deploy blocked          │
│  job    │           └─────────────────────────┘
└────┬────┘
     │ passes
     ▼
┌──────────────────────────────────┐
│  deploy job                      │
│  1. SSH → git pull               │
│  2. pip install -r requirements  │
│  3. systemctl restart            │
│  4. Smoke test (HTTP 200 check)  │
└──────────────────────────────────┘
```

The `test` job runs on `ubuntu-latest`, checks out code, installs the full `requirements.txt`, sets a dummy `OPENAI_API_KEY` (no real API calls — the client is patched in `conftest.py`), then runs `pytest tests/ -v`. The `deploy` job carries `needs: test`, so GitHub Actions will not proceed to deployment if any test fails.

Key design notes:
- **No secrets needed for tests** — `conftest.py` patches the OpenAI constructor at import time; all 51 tests run with zero external calls.
- **pip cache** — the `setup-python@v5` step caches pip downloads to keep CI fast after the first run.
- **HF Spaces workflow** (`deploy-hf.yml`) does not have a test gate — that deployment is a secondary mirror, not the production path.

### Remaining CI priorities

1. ~~**Run unit tests** as a pre-deploy step~~ — **done** (see above)
2. **Run healthcheck** (Tier 2) as a manual pre-deploy step, documented in deploy runbook
3. **Eval baseline check** (Tier 3) — not wired into CI; remains a deliberate manual activity

---

## Priority Order

What to do first, and why:

1. ~~**`tests/test_pure_logic.py`**~~ — **done.** 51 tests, 0.16s, gating deploys in CI.

2. ~~**CI integration of unit tests**~~ — **done.** `deploy-ec2.yml` now has a `test` job that blocks deploy on failure.

3. **`scripts/healthcheck.py`** — next up. The scariest breakage (silent credential/config failure) is not caught by anything right now.

4. **Eval baseline** — low effort given the framework exists. Transforms the eval tool from "interesting snapshot" to "regression detector."

---

## What This Looks Like to a Hiring Manager

The framing: *deliberate trade-offs based on failure modes, not coverage for coverage's sake.*

- **Silent failures** (key rotation, model name typo, tool routing break) → caught by automated unit tests and healthcheck script before users encounter them
- **Loud failures** (app won't start, HTTP 500) → caught by existing CI smoke test
- **Quality drift** (answers get worse after a KB or prompt change) → caught by the eval framework, run deliberately as part of any knowledge-affecting change

This is a three-tier strategy where each tier earns its place. It doesn't test everything, but it tests the right things at the right level of automation — which is exactly what a senior engineer would design for a project at this stage.
