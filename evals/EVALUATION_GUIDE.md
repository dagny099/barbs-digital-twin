# Evaluation Guide

This document is the canonical reference for how the Digital Twin evaluation system is structured, what it is meant to measure, and how the core evaluation artifacts fit together.

It is intentionally **future-facing**. It describes the durable design of the evaluation system rather than the history of how the question bank evolved.

## Purpose

The evaluation system exists to answer three different questions:

1. **Does the twin know the right things?**
2. **Does it answer in the right way?**
3. **When an answer is weak, why?**

That means evaluation is not only a factual coverage check. It is also a way to monitor voice fidelity, specificity, presentation quality, follow-up behavior, retrieval quality, and recurring failure modes.

## Design Principles

The evaluation system is built around a few principles.

### 1. Questions are not all the same

Some questions have a single correct answer. Others allow multiple good answers. Others are mostly about tone, personality, and conversation design.

The evaluation system therefore distinguishes between:

- **Closed fact** questions: expected to be tightly grounded in source material
- **Bounded-open** questions: allow variation, but within a defined response shape
- **Open persona** questions: primarily evaluate voice, warmth, and conversational judgment

### 2. The question bank and the review sheet serve different purposes

The **question bank** defines what a good answer should accomplish.
The **review template** records what actually happened during a run and how the response was judged.

### 3. Controlled vocabularies matter

Certain fields should be governed consistently so results can be analyzed over time.
Examples include question type, audience mode, issue source, strengths tags, weakness tags, and failure-mode tags.

### 4. Evaluation should lead to action

A weak answer should not end with “bad response.” It should end with a diagnosis such as:

- knowledge gap
- retrieval gap
- prompt behavior
- model tendency
- evaluation item needs revision

That diagnosis should point toward a concrete next step.

## Core Evaluation Artifacts

The evaluation system uses four primary artifacts.

### 1. Question Bank

The question bank is the design artifact for evaluation items.

Each row defines a question and the expected **shape** of a good answer. Depending on the question type, that may include:

- must-cover content
- nice-to-have content
- things the answer should not do
- preferred structure
- preferred follow-up behavior
- acceptable example projects or proof points
- grounding expectation

The question bank should be considered the authoritative source for evaluation intent.

### 2. Review Template

The review template extends the question bank with:

- run metadata such as model, provider, temperature, and top-k
- observed response fields such as raw response, word count, markdown usage, link usage, and follow-up presence
- human review fields such as scoring dimensions, controlled tags, diagnosis, and suggested fix

In practice, the review template is the working sheet used during manual evaluation.

### 3. Data Dictionary

The data dictionary defines each field used in the evaluation system, including:

- property name
- description
- data type
- whether it is required
- whether it is manually governed or automatically populated
- notes about intended usage

The data dictionary is the best place to look when deciding whether a field belongs in the question bank, review template, or runtime output.

### 4. Controlled Vocabulary Registry

The controlled vocabulary registry is the source of truth for governed values used by the evaluation system.

It should be used for three things:

- **Consistency in spreadsheets**: reviewers should choose from the same tag sets and enums
- **Consistency in scripts**: exports, dashboards, and analyzers should assume the same values
- **Future formalization**: when the system is ready, these vocabularies can become JSON Schema enums, Python enums, or spreadsheet validation lists

Examples of governed vocabularies include:

- `question_type`
- `audience_mode`
- `priority`
- `preferred_structure`
- `preferred_followup_behavior`
- `grounding_expectation`
- `issue_source`
- `strengths_tags`
- `weakness_tags`
- `failure_mode_tags`

## Question Types

### Closed Fact

Use for questions where the answer is expected to be tightly grounded and materially correct.

Examples:

- Where did you do your PhD?
- What undergraduate degrees did you earn?
- What was your role at UT Austin after returning from MIT?

Evaluation emphasis:

- accuracy
- retrieval alignment
- concise completeness

### Bounded-Open

Use for questions where multiple answers may be acceptable, but the answer should remain within a known zone.

Examples:

- Walk me through a project
- How do you approach ML model development?
- What matters most to you in a role?

Evaluation emphasis:

- specificity
- narrative arc
- problem framing
- response shape
- grounded proof points

### Open Persona

Use for questions where the main goal is to evaluate voice, warmth, judgment, and conversational fluency.

Examples:

- How many twins are there and do you get jealous of any of them?
- I heard some digital twins make up information. What do you think about that?

Evaluation emphasis:

- voice fidelity
- tone
- playfulness or restraint
- follow-up behavior

## Recommended Scoring Dimensions

The review template should evaluate responses on a stable set of dimensions.

Recommended dimensions:

- **Accuracy**: Is the answer correct and appropriately grounded?
- **Specificity**: Is it concrete rather than generic?
- **Voice Fidelity**: Does it sound like Barbara?
- **Narrative Arc**: Does the answer have a satisfying shape?
- **Follow-up Magnetism**: Does it invite a useful next turn?
- **Presentation / Scanability**: Is it easy to read and visually organized?
- **Relevance**: Does it answer the actual question asked?
- **Retrieval Alignment**: Does it seem to reflect the right source material?
- **Overall Score**: Summary judgment

Not every dimension will matter equally for every question type, but the schema should remain stable.

## Governed vs Auto-Populated Fields

### Governed fields

These should be treated as controlled or manually maintained:

- question type
- audience mode
- priority
- must-cover guidance
- preferred structure
- preferred follow-up behavior
- diagnosis labels
- strengths / weakness / failure-mode tags

### Auto-populated or derived fields

These should come from scripts or post-processing where possible:

- run timestamp
- model / provider
- temperature / top-k
- raw response
- response word count
- markdown usage
- link usage
- follow-up presence
- retrieved docs
- similarity metrics
- latency
- token counts
- cost

## Evaluation Workflow

The evaluation workflow has four phases.

### 1. Design

Create or revise evaluation items in the question bank.

This is where you define:

- what the question is testing
- what kind of answer is acceptable
- what should count as a miss

### 2. Execution

Run the offline harness against a selected question bank.

This produces:

- raw responses
- retrieved context
- runtime metadata
- derived response features

### 3. Review

Use the review template to score responses and apply controlled tags.

This is where you distinguish between:

- weak but acceptable answers
- actual failures
- style issues
- knowledge issues
- retrieval issues

### 4. Diagnosis and Improvement

Use the diagnosis fields to decide what to change.

Examples:

- update a source doc
- re-ingest a source
- adjust prompt behavior
- revise a question
- compare model behavior

## When to Run Evals

At minimum, run evaluation after:

- changing the system prompt
- changing or re-ingesting knowledge-base sources
- changing retrieval settings such as top-k
- changing default models or temperature
- before deployment

The full suite is the regression check. Smaller benchmark subsets are useful for fast model bake-offs or focused debugging.

## Relationship to Other Docs

This guide is the **canonical conceptual reference** for the evaluation system.

Other evaluation docs should be narrower in scope:

- **EVAL_QUICKSTART.md**: how to run the harness quickly
- **[MAINTAINER_GUIDE.md](../docs/MAINTAINER_GUIDE.md)**: when and why maintainers should run evals in normal operations
- **Question bank / data dictionary / review template**: working artifacts used during evaluation

## Maintenance Guidance

When the evaluation system evolves, update artifacts in this order:

1. Controlled vocabulary registry
2. Data dictionary
3. Question bank
4. Review template
5. Runner / analyzer scripts
6. Quickstart and maintainer docs

That order helps keep the conceptual design stable even when tooling changes.

## Current Practical Recommendation

For day-to-day use:

- maintain the question bank, data dictionary, and review template in Google Sheets if that is your preferred working environment
- keep the repo versions aligned enough to remain understandable and runnable
- treat this document as the stable explanation of the system’s design decisions

If the question bank or review process changes later, this guide should still remain mostly true.
