# Evaluation System — Quick Start Guide

## What You Have

An offline evaluation harness for systematically testing Digital Twin response quality:
- **92 seed questions** across 8 categories in `eval_questions.csv`
- **`run_evals.py`** — queries the RAG system and saves timestamped JSON results
- **`analyze_evals.py`** — summarizes results by category and exports for manual grading

The eval harness replicates the core RAG pipeline (embed → retrieve → prompt → complete) but
**does not** exercise tool calling (Pushover notifications, dice roll) or project walkthrough
mode. Those require manual testing in the running app.

## When to Run Evals

Run after any of these changes:
- Editing `SYSTEM_PROMPT.md`
- Adding, editing, or re-ingesting any KB source
- Changing `LLM_MODEL`, `LLM_TEMPERATURE`, or `N_CHUNKS_RETRIEVE`
- Before deploying to Hugging Face Spaces

Frequency: treat it as a pre-deploy gate. A full run costs ~$0.21 and takes ~5 minutes.

## Two Types of Questions

**Coverage questions** (6 categories) — *"Does the system know X?"*
Run these to catch regressions after KB or prompt changes.

**Visitor questions** (2 categories) — *"Would a real visitor get a satisfying response?"*
Run these to evaluate quality from the visitor's perspective.

| Category | Count | Type | What It Tests |
|----------|-------|------|---------------|
| `bio` | 19 | Coverage | Personal background, education, career history |
| `projects` | 20 | Coverage | Technical projects, accomplishments, tech stacks |
| `technical` | 10 | Coverage | Skills, tools, methodologies |
| `personality` | 10 | Coverage | Voice consistency, tone, Barbara's style |
| `tool` | 5 | Coverage | Notification and dice tool calling (note: not exercised by eval runner) |
| `publication` | 8 | Coverage | Academic research, papers, citations |
| `recruiter` | 10 | Visitor | Career narrative from a hiring manager's perspective |
| `friendly` | 10 | Visitor | Personal side and authentic personality |
| **TOTAL** | **92** | | |

## Running Evals

**Must run from the `evals/` directory** (paths are relative to this directory):

```bash
cd evals
```

### Quick test (30 seconds, ~$0.02)
```bash
python run_evals.py --limit 10
```

### Full run (~5 min, ~$0.21)
```bash
python run_evals.py
```

### Targeted runs by category
```bash
python run_evals.py --category bio
python run_evals.py --category recruiter
python run_evals.py --category publication
```

Results are saved to `evals/eval_results/eval_results_YYYY-MM-DD_HH-MM-SS.json`.

## Analyzing Results

```bash
python analyze_evals.py              # Summary of latest results
python analyze_evals.py --export     # Export to eval_review.csv for manual grading
```

Open `eval_review.csv` in a spreadsheet. Grade 10–15 responses on a 1–5 scale, prioritizing:
- `recruiter` and `friendly` categories (visitor impact)
- Any responses flagged as errors

## Interpreting Results

### Benchmark targets

| Metric | Target | What to do if low |
|--------|--------|-------------------|
| Overall success rate | 95%+ | Check for API errors in the JSON output |
| Top-10 retrieval coverage | All questions get 10 chunks | Run `python ingest.py --status` to confirm all sources are embedded |
| Manual accuracy score | 4.0+ / 5.0 | Update KB content or re-ingest the relevant source |
| Manual personality score | 4.0+ / 5.0 | Adjust system prompt in `SYSTEM_PROMPT.md` |

### What low scores by category usually mean

- **`bio` low** → biosketch needs updating, or run `python ingest.py --source kb-biosketch --force`
- **`publication` low** → check `python ingest.py --status` for the `kb-publications` source
- **`recruiter` low personality** → refine the tone/voice section of `SYSTEM_PROMPT.md`
- **`friendly` generic responses** → add more personal detail to `kb_biosketch.md` or `kb_philosophy-and-approach.md`
- **`technical` misses** → check `kb_projects.md` coverage or re-ingest `project-summaries`

### Known limitations

- **Temperature**: eval uses the same `LLM_TEMPERATURE` env var as the app (default 0.7). Keep
  this consistent so eval results reflect production behavior.
- **No tool calls**: the eval runner skips tool calling. Test notifications and dice manually.
- **No walkthrough mode**: project walkthrough responses are not evaluated. Test manually.
- **No conversation history**: each question is asked in isolation (single-turn only).

## Files

| File | Description |
|------|-------------|
| `eval_questions.csv` | Question bank — add questions here |
| `run_evals.py` | Evaluation runner |
| `analyze_evals.py` | Results analysis and CSV export |
| `eval_results/*.json` | Timestamped output from each run |
| `EVAL_WORKFLOW.md` | Full documentation and troubleshooting |

## Common Questions

**How much does this cost?**
~$0.21 per full run (92 questions at gpt-4.1-mini rates). Weekly runs ≈ $0.85/month.

**Do I need to grade all 92 responses?**
No. Grade 10–15 representative ones, prioritizing `recruiter`/`friendly` and any errors.

**Can I add my own questions?**
Yes — edit `eval_questions.csv`. Follow the existing format: `question,category,expected_info,notes`.
Valid categories: `bio`, `projects`, `technical`, `personality`, `tool`, `publication`, `recruiter`, `friendly`.
