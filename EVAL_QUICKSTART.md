# Evaluation System — Quick Start Guide

## What You Have

A simple offline evaluation system for your Digital Twin with:
- **92 seed questions** across 8 categories
- **Automated runner** that queries your RAG system
- **Analysis tools** that flag issues
- **Manual review workflow** for human grading

## Two Types of Questions

The question bank uses two complementary perspectives:

**Coverage questions** (6 categories) — *"Does the system know X?"*
Organized by data source type. Run these to detect regressions after knowledge base changes (new embeddings, chunking tweaks, prompt edits).

**Visitor questions** (2 categories) — *"Would a real person get a satisfying response?"*
Organized by who's asking. These mirror `RECRUITER_PROMPTS` and `FRIENDLY_PROMPTS` in `app.py` — the same questions shown as UI examples. Run these to evaluate quality from the visitor's perspective.

## Question Distribution

| Category | Count | Perspective | What It Tests |
|----------|-------|-------------|---------------|
| `bio` | 19 | Coverage | Personal background, education, career history |
| `projects` | 20 | Coverage | Technical projects, work experience, accomplishments |
| `technical` | 10 | Coverage | Skills, tools, methodologies, frameworks |
| `personality` | 10 | Coverage | Voice consistency, tone, Barbara's style |
| `tool` | 5 | Coverage | Notification and dice tool calling |
| `publication` | 8 | Coverage | Academic research, papers, citations |
| `recruiter` | 10 | Visitor | Career narrative as a hiring manager would ask |
| `friendly` | 10 | Visitor | Personal side and authentic personality |
| **TOTAL** | **92** | | **Full Digital Twin capabilities** |

## Your First Evaluation (5 minutes)

### Step 1: Quick test (30 seconds)
```bash
python run_evals.py --limit 10
```

This runs the first 10 questions to make sure everything works.

### Step 2: See the results (30 seconds)
```bash
python analyze_evals.py
```

This shows you:
- Success rate by category
- How many chunks were retrieved
- Any flagged issues

### Step 3: Look at the actual responses (2 minutes)
```bash
ls -la eval_results/
```

Open the latest JSON file and browse a few responses:
- Does the response make sense?
- Were the right chunks retrieved?
- Does it sound like you?

### Step 4: Run the full eval (3 minutes)
```bash
python run_evals.py
```

All 92 questions. Takes ~4-6 minutes. Costs ~$0.21 in OpenAI API calls.

### Step 5: Grade a few responses (5-10 minutes)
```bash
python analyze_evals.py --export
```

This creates `eval_review.csv`. Open it in Excel/Google Sheets and grade 10-15 responses.

---

## Targeted Runs by Category

```bash
# Test only coverage categories
python run_evals.py --category bio
python run_evals.py --category publication

# Test only visitor experience
python run_evals.py --category recruiter
python run_evals.py --category friendly

# Quick regression check after knowledge base changes
python run_evals.py --category bio --category projects --category technical
```

---

## Weekly Workflow (15 minutes)

**Every Monday** (or after making changes):

1. Run full evaluation: `python run_evals.py`
2. Check analysis: `python analyze_evals.py`
3. Export and grade 10-15 responses: `python analyze_evals.py --export`
4. Track scores over time in a simple spreadsheet
5. Make improvements based on findings

---

## Files You'll Use

### You WILL edit these:
- `eval_questions.csv` — Add more questions as you think of them
- `eval_review.csv` — Add your 1-5 scores after running `--export`

### Connected to app.py:
- `RECRUITER_PROMPTS` in `app.py` → maps to `recruiter` category in CSV
- `FRIENDLY_PROMPTS` in `app.py` → maps to `friendly` category in CSV
- Keep these in sync when you update either

### You WON'T edit these (unless changing logic):
- `run_evals.py` — The evaluation runner
- `analyze_evals.py` — The analysis tool
- `EVAL_WORKFLOW.md` — Full documentation

### Generated automatically:
- `eval_results/*.json` — Results from each run (timestamped)

---

## Understanding Your Scores

### Good Benchmarks:

**Overall success rate**: 95%+
- Less than this? Check for errors in the analysis output

**Retrieval (3 chunks)**: 60%+
- Less than this? Your source documents may not cover these topics

**Manual grading targets**:
- Accuracy (coverage categories): 4.0+ / 5.0
- Personality (visitor categories): 4.0+ / 5.0
- Retrieval quality: 3.5+ / 5.0

### What to focus on by category:
- **`bio` low accuracy** → biosketch may need updating or re-embedding
- **`publication` low retrieval** → check that `embed_publications.py` was run
- **`recruiter` low personality** → adjust system prompt in `app.py`
- **`friendly` generic responses** → add more personal detail to biosketch

---

## Common Questions

**Q: How often should I run this?**
A: Weekly for monitoring, and immediately after any changes (new sources, prompt tweaks, model changes)

**Q: Do I need to grade all 91 responses?**
A: No! Grade 10-15 representative ones, prioritizing flagged items and the `recruiter`/`friendly` categories

**Q: Can I use Google Sheets instead of CSV?**
A: Yes! Upload `eval_questions.csv` to Google Sheets, edit there, then download as CSV before running

**Q: What if I see low scores?**
A: See "Common issues and fixes" in `EVAL_WORKFLOW.md` — usually it's missing source docs or prompt adjustments

**Q: How much does this cost?**
A: ~$0.21 per full run (91 questions). Weekly runs ≈ $0.85/month

---

## Next Steps

1. **Run your first test**: `python run_evals.py --limit 10`
2. **Read the full docs**: Open `EVAL_WORKFLOW.md`
3. **Add your own questions**: Edit `eval_questions.csv`
4. **Set a weekly reminder**: "Run Digital Twin evaluation"

---

## Need Help?

See `EVAL_WORKFLOW.md` for:
- Detailed component descriptions
- Troubleshooting guide
- Examples of good vs. bad results
- How to extend the system
