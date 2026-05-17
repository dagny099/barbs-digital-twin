# Evaluation Quick Start

Use the offline harness to run regression checks against the Digital Twin.

## What this covers

The offline harness tests single-turn question answering against the current knowledge base and prompt behavior.

It is best used for:

- coverage checks after KB changes
- quality checks after prompt or model changes
- lightweight model comparisons (e.g. gpt-4.1 vs gpt-4.1-mini, or ChromaDB vs Neo4j)
- pre-deploy regression checks

It does **not** fully exercise:

- tool calling
- project walkthrough mode
- multi-turn conversational behavior

## Core files

- `eval_questions.csv` — question bank
- `run_evals.py` — evaluation runner (supports `--backend chromadb` or `--backend neo4j`)
- `analyze_evals.py` — analysis and export
- `eval_results/*.json` — saved run outputs (filename includes backend name)

## Run a quick check

```bash
python evals/run_evals.py --limit 10
python evals/analyze_evals.py
```

## Run the full suite

```bash
python evals/run_evals.py
python evals/analyze_evals.py --export --output evals/eval_results/latest_results_review.csv
```

## Run a category

```bash
python evals/run_evals.py --category bio
python evals/run_evals.py --category projects
python evals/run_evals.py --category technical
```

## Compare ChromaDB vs Neo4j retrieval

Run both backends against the full question bank, then export both to CSV and
diff the `response` column side-by-side in a spreadsheet.

```bash
# Step 1 — capture both backends
python evals/run_evals.py --backend chromadb --label chroma-baseline
python evals/run_evals.py --backend neo4j    --label neo4j-phase3

# Step 2 — export each to a review CSV
python evals/analyze_evals.py \
  --file evals/eval_results/eval_results_chromadb_<timestamp>.json \
  --export --output evals/eval_results/review_chroma.csv

python evals/analyze_evals.py \
  --file evals/eval_results/eval_results_neo4j_<timestamp>.json \
  --export --output evals/eval_results/review_neo4j.csv

# Step 3 — open both CSVs in a spreadsheet and compare the 'response' column
```

**Notes on Neo4j similarity scores:** The `chunk_similarity_avg` / `chunk_similarity_max`
columns reflect Neo4j composite scores (vector + graph bonuses), not raw cosine
distances. They are comparable within a Neo4j run but not numerically equivalent
to ChromaDB cosine similarities across runs.

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
- migrating retrieval backends (ChromaDB → Neo4j)
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
