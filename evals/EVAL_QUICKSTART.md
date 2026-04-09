# Evaluation Quick Start

Use the offline harness to run regression checks against the Digital Twin.

## What this covers

The offline harness tests single-turn question answering against the current knowledge base and prompt behavior.

It is best used for:

- coverage checks after KB changes
- quality checks after prompt or model changes
- lightweight model comparisons
- pre-deploy regression checks

It does **not** fully exercise:

- tool calling
- project walkthrough mode
- multi-turn conversational behavior

## Core files

- `eval_questions.csv` — question bank
- `run_evals.py` — evaluation runner
- `analyze_evals.py`  — analysis and export
- `eval_results/*.json` — saved run outputs

## Run a quick check

```bash
python run_evals.py --limit 10
python analyze_evals.py
```

## Run the full suite

```bash
python run_evals.py
python analyze_evals.py --export
```

## Run a category

```bash
python run_evals.py --category bio
python run_evals.py --category projects
python run_evals.py --category technical
```

## Review results

Use the exported review sheet to grade responses on the core dimensions defined in `EVALUATION_GUIDE.md`.

Focus first on:

- flagged failures
- recruiter / front-example / user-submitted questions
- questions that should be tightly grounded

## When to run evals

Run them after:

- editing `SYSTEM_PROMPT.md`
- changing or re-ingesting KB sources
- changing model, temperature, or top-k
- before deployment

## Interpreting weak results

A weak answer usually points to one of five causes:

- knowledge gap
- retrieval gap
- prompt behavior
- model tendency
- evaluation item needs revision

Use the review sheet to record the diagnosis and suggested fix.

## More detail

For the overall evaluation design, question types, governed fields, and scoring model, see `EVALUATION_GUIDE.md`.
