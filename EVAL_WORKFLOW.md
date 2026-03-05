# Offline Evaluation Workflow for Digital Twin

This document describes the simple, transparent evaluation system for the Digital Twin RAG application.

## Overview

The evaluation system helps you systematically assess the quality of your Digital Twin's responses across five key dimensions:

1. **Biographical questions** (20 questions) - Tests accuracy on personal background, education, career
2. **Project-specific questions** (20 questions) - Tests knowledge of technical projects and work
3. **Technical deep-dive questions** (10 questions) - Tests technical skills, tools, methodologies
4. **Personality/behavior questions** (10 questions) - Tests if responses maintain Barbara's voice and style
5. **Tool-usage scenarios** (5 questions) - Tests if tools (notification, dice) are called appropriately

**Total: 65 seed questions** covering the full scope of the Digital Twin's capabilities.

---

## Components

### 1. Question Bank (`eval_questions.csv`)

**Purpose**: Store all evaluation questions with expected information

**Format**: CSV with columns:
- `category`: Question category (bio, projects, technical, personality, tool)
- `question`: The actual question text
- `expected_info`: What information should be in the response
- `notes`: Additional context or grading hints

**Editing**:
- Open in Excel, Google Sheets, or any text editor
- Add new questions as needed
- Questions are version-controlled in git

**Example row**:
```csv
bio,Where were you born?,Austin Texas in 1981,Should mention Austin and 1981
```

---

### 2. Evaluation Runner (`run_evals.py`)

**Purpose**: Run questions through the Digital Twin and save detailed results

**What it does** (step-by-step):
1. Loads questions from `eval_questions.csv`
2. For each question:
   - Embeds the question using OpenAI's `text-embedding-3-small`
   - Retrieves top 3 relevant chunks from ChromaDB
   - Builds system prompt with retrieved context
   - Calls GPT-4.1-mini for response
   - Saves question, response, retrieved chunks, and metadata
3. Saves all results to timestamped JSON file in `eval_results/`

**Usage**:
```bash
# Run all questions
python run_evals.py

# Run only biographical questions
python run_evals.py --category bio

# Run first 10 questions (for testing)
python run_evals.py --limit 10

# Use custom questions file
python run_evals.py --questions my_questions.csv
```

**Output**: `eval_results/eval_results_YYYY-MM-DD_HH-MM-SS.json`

**Output format** (per question):
```json
{
  "question": "Where were you born?",
  "category": "bio",
  "response": "I was born in Austin, Texas in 1981...",
  "retrieved_chunks": [
    {
      "text": "Born 1981, Austin, Texas...",
      "source": "biosketch:barbara-hidalgo-sotelo-biosketch.md",
      "section": "Personal Information",
      "chunk_index": 0
    }
  ],
  "expected_info": "Austin Texas in 1981",
  "notes": "Should mention Austin and 1981",
  "model_used": "gpt-4.1-mini",
  "context_found": true,
  "timestamp": "2026-03-05T10:30:45.123456"
}
```

---

### 3. Analysis Script (`analyze_evals.py`)

**Purpose**: Analyze results and flag issues for manual review

**What it analyzes**:
- Overall success rate
- Success rate by category
- Retrieval statistics (how many chunks retrieved per question)
- Flags questions with:
  - No context retrieved (retrieval failure)
  - Very short responses (<50 chars)

**Usage**:
```bash
# Analyze latest results
python analyze_evals.py

# Analyze specific results file
python analyze_evals.py --file eval_results/eval_results_2026-03-05_10-30-45.json

# Export to CSV for manual grading
python analyze_evals.py --export
```

**Sample output**:
```
======================================================================
EVALUATION RESULTS ANALYSIS
======================================================================
Results file: eval_results/eval_results_2026-03-05_10-30-45.json

OVERALL STATISTICS
----------------------------------------------------------------------
  Total questions:     65
  Successful:          63 (96.9%)
  Errors:              2

BY CATEGORY
----------------------------------------------------------------------
  bio              Total: 20  |  Success: 20  |  Errors: 0  |  Rate: 100.0%
  projects         Total: 20  |  Success: 19  |  Errors: 1  |  Rate:  95.0%
  technical        Total: 10  |  Success: 10  |  Errors: 0  |  Rate: 100.0%
  personality      Total: 10  |  Success: 10  |  Errors: 0  |  Rate: 100.0%
  tool             Total:  5  |  Success:  4  |  Errors: 1  |  Rate:  80.0%

RETRIEVAL STATISTICS
----------------------------------------------------------------------
  No context:           3 ( 4.8%)
  1 chunk retrieved:    5 ( 7.9%)
  2 chunks retrieved:  12 (19.0%)
  3 chunks retrieved:  43 (68.3%)

FLAGGED FOR MANUAL REVIEW (3 items)
----------------------------------------------------------------------
  1. [tool] I need some encouragement today
     Reason: No context retrieved
     Response: I'd be happy to send you an encouraging message...

  ...
```

---

### 4. Manual Review Sheet (`eval_review.csv`)

**Purpose**: Human grading of responses

**How to use**:
1. Run `python analyze_evals.py --export` to generate the file
2. Import `eval_review.csv` into Google Sheets or Excel
3. Grade each response on three dimensions (1-5 scale):
   - **Accuracy** (1-5): Does the response contain correct information?
   - **Personality** (1-5): Does it sound like Barbara? Right tone?
   - **Retrieval Quality** (1-5): Were the right chunks retrieved?
4. Add notes for any issues or patterns you notice

**Grading rubric**:

**Accuracy (1-5)**:
- 5: Completely accurate, all expected info present
- 4: Mostly accurate, minor details missing
- 3: Partially accurate, some key info missing
- 2: Mostly inaccurate or incomplete
- 1: Completely wrong or no answer

**Personality (1-5)**:
- 5: Perfect match for Barbara's voice (practical, collaborative, clear)
- 4: Good match, minor tone issues
- 3: Acceptable but doesn't quite sound like Barbara
- 2: Off-brand or robotic
- 1: Completely wrong personality

**Retrieval Quality (1-5)**:
- 5: Perfect chunks retrieved (exactly what's needed)
- 4: Good chunks, all relevant
- 3: Some relevant chunks, some noise
- 2: Mostly irrelevant chunks
- 1: No relevant chunks retrieved

---

## Workflow: Step-by-Step

### Initial Setup (one-time)

1. Ensure your Digital Twin is working:
   ```bash
   python app.py
   # Test a few queries in the Gradio interface
   ```

2. Verify evaluation files exist:
   - `eval_questions.csv` ✓
   - `run_evals.py` ✓
   - `analyze_evals.py` ✓

### Running an Evaluation (weekly or after changes)

**Step 1: Run the evaluation**
```bash
python run_evals.py
```

This will:
- Run all 65 questions
- Save results to `eval_results/eval_results_YYYY-MM-DD_HH-MM-SS.json`
- Take ~3-5 minutes (depends on OpenAI API speed)
- Cost ~$0.10-0.20 in API calls (embedding + completions)

**Step 2: Review automated analysis**
```bash
python analyze_evals.py
```

This will:
- Show success rates by category
- Highlight retrieval issues
- Flag short or problematic responses

**Step 3: Export for manual grading**
```bash
python analyze_evals.py --export
```

This creates `eval_review.csv`

**Step 4: Manual review in Google Sheets**
1. Upload `eval_review.csv` to Google Sheets
2. Grade 10-15 responses (prioritize flagged items)
3. Look for patterns:
   - Which categories have low scores?
   - Are certain sources not being retrieved?
   - Is personality consistent?

**Step 5: Iterate and improve**

Based on your review:
- **Low retrieval quality?** Check chunking strategy, add more source documents
- **Low accuracy?** Check if source documents contain the expected info
- **Low personality?** Adjust system prompt in `app.py`
- **Specific failures?** Add more test questions in those areas

**Step 6: Track over time**

Save your manual reviews with dates:
- `eval_review_2026-03-05.csv`
- `eval_review_2026-03-12.csv`

Compare scores week-over-week to see improvements.

---

## Understanding the Results

### What "good" looks like:

**Retrieval**:
- 60%+ of questions should retrieve 3 chunks
- <10% should retrieve 0 chunks
- If many questions get 0 chunks, your sources may not cover those topics

**Accuracy**:
- Biographical questions: Should be 90%+ accurate (authoritative source)
- Project questions: 80%+ (depends on README quality)
- Technical questions: 70%+ (may require inference)

**Personality**:
- Should maintain consistent voice across all categories
- If personality drifts in tool/technical questions, adjust system prompt

**Tools**:
- Should correctly identify when to use notification/dice tools
- 80%+ success rate expected

### Common issues and fixes:

**Issue**: "No context retrieved" for many questions
- **Diagnosis**: Questions about topics not in your source documents
- **Fix**: Add more source documents, or update questions to match what's embedded

**Issue**: Retrieved chunks are irrelevant
- **Diagnosis**: Embedding similarity not capturing semantic meaning
- **Fix**: Rephrase questions to be more specific, or improve chunking strategy

**Issue**: Responses don't sound like Barbara
- **Diagnosis**: System prompt not strong enough
- **Fix**: Strengthen personality guidelines in system prompt (app.py:245-262)

**Issue**: Correct info in chunks, but wrong response
- **Diagnosis**: LLM not following instructions or context
- **Fix**: Adjust prompt to emphasize "answer based on context provided"

---

## Extending the System

### Adding new questions:

1. Open `eval_questions.csv` in Excel/Google Sheets
2. Add rows with: `category,question,expected_info,notes`
3. Save and run `python run_evals.py`

**Tips for good questions**:
- Be specific and clear
- Cover edge cases (ambiguous queries, multi-part questions)
- Test both breadth (many topics) and depth (detailed follow-ups)

### Testing after code changes:

```bash
# Quick test (first 10 questions)
python run_evals.py --limit 10

# Full test
python run_evals.py

# Compare results
python analyze_evals.py --file eval_results/eval_results_OLD.json
python analyze_evals.py --file eval_results/eval_results_NEW.json
```

### Tracking improvements over time:

Create a simple spreadsheet:
```
| Date       | Total Accuracy | Personality | Retrieval | Notes                    |
|------------|----------------|-------------|-----------|--------------------------|
| 2026-03-05 | 4.2/5          | 4.5/5       | 3.8/5     | Baseline                 |
| 2026-03-12 | 4.5/5          | 4.6/5       | 4.2/5     | Improved chunking        |
| 2026-03-19 | 4.7/5          | 4.8/5       | 4.3/5     | Updated system prompt    |
```

---

## File Reference

| File | Purpose | Git Tracked? | Editable? |
|------|---------|--------------|-----------|
| `eval_questions.csv` | Question bank | Yes | Yes - add questions freely |
| `run_evals.py` | Evaluation runner | Yes | Only if changing logic |
| `analyze_evals.py` | Results analyzer | Yes | Only if changing analysis |
| `EVAL_WORKFLOW.md` | This document | Yes | Update as workflow evolves |
| `eval_results/*.json` | Results files | No (gitignored) | No - generated by script |
| `eval_review.csv` | Manual grading | No (gitignored) | Yes - add your scores |

---

## Cost Estimates

**Per full evaluation run (65 questions)**:
- Embeddings: 65 queries × ~10 tokens = ~$0.0001
- Retrievals: Free (local ChromaDB)
- Completions: 65 × ~500 tokens = ~$0.15
- **Total: ~$0.15 per run**

**Recommended cadence**:
- Weekly full runs: ~$0.60/month
- After major changes: Ad-hoc
- Quick tests (--limit 10): ~$0.02 each

---

## Quick Reference Commands

```bash
# Run full evaluation
python run_evals.py

# Analyze latest results
python analyze_evals.py

# Export for manual review
python analyze_evals.py --export

# Run specific category
python run_evals.py --category bio

# Quick test (10 questions)
python run_evals.py --limit 10

# Analyze specific file
python analyze_evals.py --file eval_results/eval_results_2026-03-05_10-30-45.json
```

---

## Next Steps

1. **Run your first evaluation**:
   ```bash
   python run_evals.py --limit 10
   python analyze_evals.py
   ```

2. **Review a few responses manually**:
   - Look at the JSON output in `eval_results/`
   - Check if retrieved chunks are relevant
   - Check if responses match expected info

3. **Grade 10-15 responses**:
   ```bash
   python analyze_evals.py --export
   # Open eval_review.csv and add scores
   ```

4. **Identify patterns**:
   - Which categories need improvement?
   - Are there missing sources?
   - Is personality consistent?

5. **Iterate**:
   - Add source documents
   - Adjust system prompt
   - Improve chunking
   - Re-run evaluation and compare

---

**Questions or issues?**
- Check the troubleshooting section above
- Review the analysis output for flagged items
- Examine the JSON results directly for debugging
