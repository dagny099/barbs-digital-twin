# System Prompt Design — Digital Twin

This document explains the design decisions behind `SYSTEM_PROMPT.md` and serves as a case study in prompt engineering for portfolio chatbots.

## Problem Statement

Traditional RAG chatbots fail in three common ways:

1. **Generic voice** — Sound like every other AI assistant, lacking authentic personality
2. **Hallucination** — Fill knowledge gaps with plausible-sounding fabrications
3. **Scope creep** — Try to be a general-purpose assistant instead of staying focused

This digital twin needed to avoid all three while maintaining Barbara's authentic voice and demonstrating her knowledge engineering approach.

## Design Approach

### Persona Grounding (Sections 1-2)
**Goal**: Authentic first-person voice, not "assistant speaking about Barbara"

**Implementation**:
- Explicit persona definition with specific background details (MIT PhD, cognitive science → AI engineering)
- Tone guidelines that balance warmth and directness
- Uncertainty modeling ("I'm not sure..." is acceptable)

**Trade-off**: Refuses general-purpose coding tasks, but that sharpens the focus on portfolio/background questions

### Narrative Priorities (Section 3)
**Goal**: Lead with problems solved, not technology lists

**Implementation**:
- "Problems before skills" — Name the problem, then show the proof
- "Stories before specs" — Narrative arc for project walkthroughs
- Proactive project mentions without being spammy

**Why this matters**: Recruiters care about impact, not tool lists. This framing surfaces portfolio work in context.

### Featured Projects (Section 4)
**Goal**: Proactively surface flagship work without overwhelming visitors

**Implementation**:
- Explicit "FEATURED" designation (4 projects)
- Surfacing rules: "Mention naturally and early, not as afterthoughts"
- Invitation to ask follow-up questions

**Validation**: Eval testing showed this approach works — recruiter-category questions naturally mentioned relevant projects without prompt stuffing.

### Knowledge Boundaries (Sections 8, 9)
**Goal**: Never fabricate when context is missing

**Implementation**:
- Two-source rule: Only system prompt + retrieved KB chunks (no general knowledge)
- Explicit "I don't know" protocols with natural phrasing
- Partial context handling: "I have some context on X but not the specific Y"

**Result**: Zero hallucinated project names, dates, or companies in eval suite

### Tool Integration (Section 12)
**Goal**: Enable contact requests and knowledge gap notifications without false positives

**Implementation**:
- Separate protocols for contact vs. knowledge gap
- Explicit "ask before sending" sequence (name + email + message)
- No auto-sending without visitor confirmation

**Why it's split**: Early unified instructions led to over-eager notifications

### Failure Mode Reference (Section 13)
**Goal**: Encode production lessons in a scannable format

**Implementation**: Table of wrong vs. right responses

**How it evolved**: Each row represents a real failure observed during testing. The table format makes it easy to add new failures without restructuring the entire prompt.

## Validation Strategy

The prompt is tested against a 92-question evaluation suite (`evals/`) organized into 8 categories:

- **Coverage categories** (bio, projects, technical, personality, tool, publication): "Does the system know X?"
- **Visitor categories** (recruiter, friendly): "Would a real visitor get a satisfying response?"

Questions are asked in isolation (no conversation history) with:
- Same retrieval pipeline as production (embed → ChromaDB → top-10 chunks)
- Same model and temperature (`LLM_MODEL`, `LLM_TEMPERATURE` env vars)
- Cost: ~$0.21 per full run

Eval results inform iterative prompt refinement. When a category shows weak performance, it points to either a prompt issue or a knowledge base gap.

## Lessons Learned

### What Worked

1. **Markdown structure helps debugging**: Numbered sections make it easy to reference specific instructions ("the issue is in Section 8")
2. **Explicit failure modes beat implicit rules**: The table in Section 13 prevents repeat errors
3. **Length is not the bottleneck**: At 2,500 words, the prompt is detailed — but retrieval context is 10x that. Clarity matters more than brevity.
4. **Personality consistency requires specificity**: "Warm but direct" alone isn't enough. Examples of what NOT to say ("Great question!", "I hope that helps") were necessary.

### What Didn't Work Initially

1. **Unified tool instructions**: Early versions had one protocol for all notifications. Splitting contact requests vs. knowledge gaps reduced false positives.
2. **Implicit featured projects**: Saying "mention important projects" wasn't enough. Explicitly listing the 4 featured projects and their elevator pitches made surfacing consistent.
3. **General anti-hallucination advice**: "Don't make things up" didn't work. The two-source rule (Section 8) + explicit partial-context handling (Section 9) did.

### Iterative Changes

- **V1 → V2**: Added Section 13 (Failure Mode Reference) after production errors
- **V2 → Current**: Split tool protocols, added featured project elevator pitches, strengthened factual accuracy guardrails

## Key Metrics

While specific numbers vary across eval runs, the prompt consistently achieves:
- High factual accuracy (no fabricated projects, dates, or companies)
- Voice consistency (personality category questions match tone guidelines)
- Appropriate scope boundaries (redirects general coding requests)

## For Other Builders

If you're building your own portfolio chatbot, consider:

1. **Test systematically**: Build an eval suite early. Iterating blind is expensive.
2. **Document failure modes**: When the bot screws up, add a row to your failure table
3. **Optimize for authenticity over capability**: A chatbot that sounds like you and says "I don't know" beats one that sounds generic and hallucinates
4. **Make the prompt visible**: If it's a portfolio project, the prompt IS the portfolio

---

**Version**: 2.0
**Last Updated**: 2026-04-02
**Eval Suite**: 92 questions across 8 categories
**Primary Model**: OpenAI GPT-4.1
