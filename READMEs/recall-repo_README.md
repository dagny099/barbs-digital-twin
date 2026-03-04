# RepoRecall

> Never forget how your own code works

## The Problem
You built a project 6 months ago. Now you barely remember how it works.
Documentation is stale. READMEs don't capture the *why* behind decisions.

## The Solution
RepoRecall analyzes your GitHub repositories and generates personalized 
flashcards/quizzes using spaced repetition to help you retain knowledge 
about your own code.

## How It Works
1. **Connect:** Paste your GitHub repo URL
2. **Analyze:** AI extracts key concepts, patterns, and decisions
3. **Learn:** Daily quizzes adapt to what you're forgetting
4. **Retain:** Spaced repetition keeps knowledge fresh

## Current Status: Phase 0 — Intelligence Layer Validation

We're validating the core hypothesis: *Can Claude generate useful questions 
about a codebase?* Everything else (backend, frontend, database) is proven 
territory — this is the only real risk.

### Running the Validation Script

**Prerequisites:**
```bash
pip install anthropic requests python-dotenv
```

**Setup:**
```bash
cp .env.template .env
# Edit .env → add your ANTHROPIC_API_KEY and GITHUB_TOKEN
```

**Run against any public repo:**
```bash
# Default (citation-compass):
python validate_intelligence.py

# Any repo:
python validate_intelligence.py dagny099/citation-compass
python validate_intelligence.py owner/any-public-repo
```

**Output** (in `results/` directory):
- `{repo}_REVIEW_{timestamp}.md` — Human-readable review sheet. Rate each question ✅/⚠️/❌.
- `{repo}_validation_{timestamp}.json` — Full structured data (concepts + questions + metadata).

**Success gate:** 14+ out of 20 questions rated ✅ USEFUL → proceed to Phase 1.

### ⚠️ Known Issues
- Large repos (>30 files after filtering) are capped for cost control during validation.
- Some Claude responses may have JSON parsing issues — the parser includes fallback strategies.
- GitHub API without a token is rate-limited to 60 requests/hour. Use a token.

## Tech Stack
- Frontend: React + TailwindCSS
- Backend: FastAPI + PostgreSQL
- AI: Claude API for code analysis  
- Learning: SM-2 spaced repetition algorithm

## Project Documents
- `ARCHITECTURE.md` — Full intelligence layer design (pipeline, algorithms, data model)
- `DEV_DECISIONS.md` — Tech stack choices and rationale
- `PROJECT_PLAN.md` — 3-week MVP timeline with success metrics

## Roadmap
- [x] Concept validation & architecture design
- [x] Intelligence layer validation script (Phase 0)
- [ ] Core question generation — **YOU ARE HERE**
- [ ] FastAPI backend scaffold (Phase 1)
- [ ] SM-2 spaced repetition engine
- [ ] React quiz UI
- [ ] Deploy & share

## Out of Scope (V2)
- User accounts / authentication
- Multiple repos per user  
- Auto-sync on code changes
- Mobile app
- Team features
- Payment integration

## Why I Built This
As a developer who works across multiple projects, I kept running into the same 
problem: I'd return to a codebase after weeks or months and have to re-learn my 
own architecture decisions. Existing tools (READMEs, comments, docs) go stale. 
Spaced repetition is proven to work for knowledge retention — so why not apply 
it to code?
