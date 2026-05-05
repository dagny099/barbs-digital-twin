# Log Analysis Scripts

Reference for the two scripts that analyze `query_log.jsonl` (and `query_log_admin.jsonl`).
Both live in `scripts/` and read the same JSONL format, but serve different purposes.

**Related guides:**
- [LOGGING_GUIDE.md](LOGGING_GUIDE.md) — log schema, field descriptions, quick one-liners
- [ADMIN_LOGGING_GUIDE.md](ADMIN_LOGGING_GUIDE.md) — model comparison and cost workflows
- [MAINTAINER_GUIDE.md](MAINTAINER_GUIDE.md) — daily/weekly ops checklist that uses these scripts

---

## Quick comparison

| | `analyze_logs.py` | `analyze_twin_log.py` |
|---|---|---|
| **Style** | Class-based (`LogAnalyzer`) | Functional |
| **Output** | Terminal (rich pretty-print) | Files on disk + console summary |
| **Primary focus** | Query-level quality: gaps, latency, cost, votes | Session-level engagement: turns/session, bounce rate, daily rollup |
| **Output files** | JSON export only (opt-in via `--export`) | `summary.json`, `sessions.csv`, `daily_counts.csv`, `report.md` |
| **Owner filter default** | `session` (when `--exclude-owner` is passed) | `none` |
| **Malformed row handling** | Tracked and reported separately | Silently dropped |
| **Unique features** | Knowledge-gap detection, vote analysis, model/provider/cost comparison, config experiments | Per-session CSV, daily rollup, `--compare-owner-views` side-by-side table |

**Rule of thumb:** use `analyze_logs.py` for interactive debugging and quality review; use `analyze_twin_log.py` when you want structured file output to share or visualize.

---

## `scripts/analyze_logs.py`

Interactive terminal analyzer. Designed to be run often, during routine operations.

### Common invocations

```bash
# Full report (default)
python scripts/analyze_logs.py

# Exclude your own test traffic (drops full sessions that contain owner-marked rows)
python scripts/analyze_logs.py --exclude-owner

# Only show queries where retrieval was weak (similarity < 0.55)
python scripts/analyze_logs.py --knowledge-gaps

# Only show slow queries (> 5 s)
python scripts/analyze_logs.py --performance

# Satisfaction analysis (thumbs up/down)
python scripts/analyze_logs.py --votes

# Empty/malformed turn artifacts (tracks the empty-message bug)
python scripts/analyze_logs.py --empty-turns

# Analyze only the last N queries
python scripts/analyze_logs.py --last 100

# Focus on a time window (drops rows before local midnight on that date)
python scripts/analyze_logs.py --cutoff-date 2026-04-10

# Admin mode: model comparison, cost, provider, config experiments
python scripts/analyze_logs.py --admin

# Individual admin views
python scripts/analyze_logs.py --compare-models
python scripts/analyze_logs.py --cost-analysis
python scripts/analyze_logs.py --compare-providers
python scripts/analyze_logs.py --config-experiments

# Export summary to JSON
python scripts/analyze_logs.py --export summary.json

# Admin log instead of production log
python scripts/analyze_logs.py --log query_log_admin.jsonl --admin
```

### Filters applied in order

When you combine flags, filters apply in this order:
1. `--cutoff-date` (drops rows before the date)
2. `--exclude-owner` (drops owner traffic rows or sessions)
3. `--last N` (keeps only the last N records of what remains)

### Output sections (full report)

| Section | What it tells you |
|---------|-------------------|
| Summary statistics | Total queries, date range, latency, retrieval quality, flags |
| Vote analysis | Likes vs. dislikes, satisfaction by model |
| Empty/malformed turns | Counts and examples of the empty-message logging artifact |
| Workflow breakdown | standard / walkthrough / diagram_only mix and quality |
| Model usage | Count, latency, similarity per model |
| Tool usage | Which tools were called and how often |
| Knowledge gaps | Queries with similarity < 0.55 — your content backlog |
| Performance outliers | Queries > 5 s |
| Response size outliers | Largest responses by character count |

---

## `scripts/analyze_twin_log.py`

Session-centric file reporter. Run it when you want structured output to share, visualize,
or track engagement trends over time.

### Common invocations

```bash
# Default run (no filters)
python scripts/analyze_twin_log.py

# Exclude your own traffic (row-level only)
python scripts/analyze_twin_log.py --owner-filter row

# Exclude full sessions containing owner-marked rows
python scripts/analyze_twin_log.py --owner-filter session

# Focus on a time window
python scripts/analyze_twin_log.py --cutoff-date 2026-04-10

# Side-by-side comparison of all three owner-filter modes
python scripts/analyze_twin_log.py --compare-owner-views

# Custom output directory
python scripts/analyze_twin_log.py --out-dir output/my_analysis

# All options combined
python scripts/analyze_twin_log.py \
  --cutoff-date 2026-04-10 \
  --owner-filter session \
  --compare-owner-views \
  --out-dir output/analysis_out
```

### Output files

Written to `output/analysis_out/` (or `--out-dir`):

| File | Contents |
|------|----------|
| `summary.json` | Headline metrics, top prompts, workflow/provider/model counts, filter metadata |
| `sessions.csv` | One row per session: start/end time, turns, first/last prompt, avg latency, avg similarity, cost |
| `daily_counts.csv` | One row per local day: sessions, turns, one-turn sessions, avg turns/session, votes |
| `report.md` | Human-readable markdown covering all of the above with tables |

### What counts as a valid chat row

This script requires all four fields to be present; rows missing any of them are silently excluded:
- `session_id`
- `turn_index`
- `message`
- `ts`

This is intentional — the script is session-centric and can't group a row without a `session_id`. But it means malformed rows are invisible in the output (see Known Issues below).

---

## Known issues

These were identified in a code review on 2026-05-05. Check them off as they are addressed.

- [x] **`sys.exit()` inside `LogAnalyzer.__init__`** (`analyze_logs.py:134`)
  Replaced `sys.exit(1)` with `raise FileNotFoundError`. `main()` now catches it and
  prints the friendly message before exiting, keeping CLI behaviour identical while making
  the class safe to import.

- [x] **Silent malformed-row loss in `analyze_twin_log.py`** (`load_jsonl`, line 84)
  Added a counter; a warning is printed after loading if any rows were skipped.

- [x] **Misleading p95 fallback** (`analyze_logs.py:353`)
  When sample size < 20, `"p95"` is omitted and `"p95_note"` is emitted instead. The
  terminal report prints `n/a (sample too small …)`. Also fixed an off-by-one: guard
  changed from `> 20` to `>= 20`.

- [x] **No input validation on `--cutoff-date`** (both scripts)
  Added `_validated_date()` helper in both scripts. Uses a strptime + strftime round-trip
  to enforce strict `YYYY-MM-DD` format. Bad input exits with a clear message before
  the log is even loaded.

- [x] **Inconsistent owner-filter defaults between the two scripts**
  Both scripts now print the active owner-filter mode prominently at startup so the
  difference is never silent. The API defaults are intentionally preserved (no silent
  behaviour change).

- [x] **Dead `assistant_response` fields + unnecessary `deepcopy`**
  Removed `assistant_response` and `assistant_response_preview` from `QueryRecord`
  (both were declared but never populated). Removed all `deepcopy` calls from
  `analyze_twin_log.py` — `apply_owner_filter` only filters via list comprehensions and
  does not mutate its inputs.

---

## Choosing between the two scripts

| Situation | Use |
|-----------|-----|
| "What are users asking that I can't answer?" | `analyze_logs.py --knowledge-gaps` |
| "How satisfied are my visitors?" | `analyze_logs.py --votes` |
| "Which model gives the best ROI?" | `analyze_logs.py --compare-models --cost-analysis` |
| "How many visitors bounce after one message?" | `analyze_twin_log.py` (check `pct_one_turn_sessions`) |
| "What's the daily engagement trend?" | `analyze_twin_log.py` → `daily_counts.csv` |
| "I want a shareable markdown report" | `analyze_twin_log.py` → `report.md` |
| "I want to compare owner vs. visitor behavior" | `analyze_twin_log.py --compare-owner-views` |
| "I'm debugging an empty-message artifact" | `analyze_logs.py --empty-turns` |
