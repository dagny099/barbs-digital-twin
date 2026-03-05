# Evaluation System - Quick Start Guide

## What You Have

A simple offline evaluation system for your Digital Twin with:
- **65 seed questions** across 5 categories
- **Automated runner** that queries your RAG system
- **Analysis tools** that flag issues
- **Manual review workflow** for human grading

## Question Distribution

| Category | Count | What It Tests |
|----------|-------|---------------|
| Biographical | 20 | Personal background, education, career history |
| Projects | 20 | Technical projects, work experience, accomplishments |
| Technical | 10 | Skills, tools, methodologies, frameworks |
| Personality | 10 | Voice consistency, tone, Barbara's style |
| Tool Usage | 5 | Notification and dice tool calling |
| **TOTAL** | **65** | **Full Digital Twin capabilities** |

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

All 65 questions. Takes ~3-5 minutes. Costs ~$0.15 in OpenAI API calls.

### Step 5: Grade a few responses (5-10 minutes)
```bash
python analyze_evals.py --export
```

This creates `eval_review.csv`. Open it in Excel/Google Sheets and grade 10-15 responses.

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
- `eval_questions.csv` - Add more questions as you think of them
- `eval_review.csv` - Add your 1-5 scores after running --export

### You WON'T edit these (unless changing logic):
- `run_evals.py` - The evaluation runner
- `analyze_evals.py` - The analysis tool
- `EVAL_WORKFLOW.md` - Full documentation

### Generated automatically:
- `eval_results/*.json` - Results from each run (timestamped)

---

## Understanding Your Scores

### Good Benchmarks:

**Overall success rate**: 95%+
- Less than this? Check for errors in the analysis output

**Retrieval (3 chunks)**: 60%+
- Less than this? Your source documents may not cover these topics

**Manual grading targets**:
- Accuracy: 4.0+ / 5.0
- Personality: 4.0+ / 5.0
- Retrieval: 3.5+ / 5.0

---

## Common Questions

**Q: How often should I run this?**
A: Weekly for monitoring, and immediately after any changes (new sources, prompt tweaks, model changes)

**Q: Do I need to grade all 65 responses?**
A: No! Grade 10-15 representative ones, focusing on flagged items from the analysis

**Q: Can I use Google Sheets instead of CSV?**
A: Yes! Upload `eval_questions.csv` to Google Sheets, edit there, then download as CSV before running

**Q: What if I see low scores?**
A: See "Common issues and fixes" in EVAL_WORKFLOW.md - usually it's missing source docs or prompt adjustments

**Q: How much does this cost?**
A: ~$0.15 per full run (65 questions). Weekly runs = ~$0.60/month

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
