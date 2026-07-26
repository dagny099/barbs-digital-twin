# Kickoff prompt — diagram display feature

**How to use this file:** start a fresh Claude Code session on this repo and paste
everything between the rules below as your first message. Everything it needs is
either in that prompt or in the repo docs it points at.

---

> ## Task
>
> You're picking up a feature that has been fully planned but not built. Read these
> three docs first, in this order — they are the complete context:
>
> 1. `docs/DIAGRAM_DISPLAY_DESIGN.md` — when the twin shows a project diagram. Current
>    behavior, five recorded decisions (D1–D5), four reproduced failure cases, and a
>    dependency-ordered 5-step plan. **The plan section is your spec.**
> 2. `docs/handoff/GOLDEN_SET_PROTOCOL.md` — how to build the labeled test fixture
>    *with Barbara*, not for her. Read this before writing any test code.
> 3. `docs/VISUAL_SYSTEM_ROADMAP.md` — what the diagrams look like. Mostly separate
>    work; read it so you understand why D1 matters, then set it aside unless asked.
>
> Also skim `docs/LESSONS_LEARNED.md` entries 004 and 005 — they're the two most
> recent findings and both bear on this feature.
>
> ## Branch
>
> Work on a new branch off `main`: `claude/diagram-display-impl`. Do not reuse
> `claude/diagram-display-planning-jfqcrd` — that branch holds the planning docs and
> may already be merged.
>
> ## Build order (do not reorder — each step depends on the one before)
>
> **Step 1 — Extract to one function.** Move the duplicated diagram-decision logic out
> of `app.py:1450` and `app_admin.py:1213` into a single pure function in
> `featured_projects.py`:
>
> ```python
> def decide_diagram(message, response, walkthrough_project) -> DiagramDecision
> ```
>
> Return the chosen project (or `None`) *plus a reason string* — the reason is what
> makes the golden set debuggable and what should be logged. Both apps call it. No
> behavior change in this step; it is a pure refactor, and the existing print-based
> logging (`DIAGRAM: …`) should keep emitting the same strings.
>
> **Step 2 — Golden set.** Follow `GOLDEN_SET_PROTOCOL.md` exactly. This is a
> collaboration with Barbara, not a solo task. It gates steps 3–5.
>
> **Step 3 — Normalize the mention score.** Fix the failure where a long pasted job
> description scores 5/5 on generic tag overlap alone. Preferred approach: require at
> least one high-signal match (a `mention_keywords` phrase or a full title) before tag
> overlap can contribute at all — tags should break ties, not create matches. Calibrate
> any threshold against the golden set, and say in the commit message what the number
> is and why.
>
> **Step 4 — Share the alias list.** `find_prominent_project()` currently matches the
> exact lowercased title only, while `find_mentioned_project()` matches the much richer
> `mention_keywords`. Make the prominence pass use both. Then do a data pass over
> `mention_keywords` in `featured_projects.yaml`: the highest-value additions are the
> names each project is called *in its own summary prose*, since that's the text the
> model echoes back.
>
> **Step 5 — Only if Barbara green-lights it (D5).** Add the diagram manifest to
> `SYSTEM_PROMPT.md` so the model can signal which diagram fits; validate the signal
> against the manifest; fall back to steps 3–4 when it's absent. Measure against the
> golden set before and after. **Do not start this without the golden set passing.**
>
> ## Guardrails
>
> - **D3 is a decision, not a bug.** Generic walkthrough requests return a *random*
>   project on purpose. Never "fix" the nondeterminism. Tests assert the gate and
>   named-project selection; the random fallback is asserted by set membership or under
>   a fixed seed.
> - **D2 sets the error bias.** When suppressing and showing are both defensible,
>   suppress. A wrong diagram costs more than a missing one. The
>   `_is_walkthrough_request` docstring says "false positives are cheap" — that is true
>   for context injection and explicitly *not* true for diagrams.
> - Run `.venv/bin/pytest tests/ -v` before any push.
> - `app_admin.py` is the tool used to evaluate this logic. If it drifts from `app.py`,
>   every future evaluation is misleading — that's the whole reason for step 1.
> - Don't touch retrieval scoring (`neo4j_utils.py` weights). Unrelated subsystem, and
>   `LESSONS_LEARNED.md` Entry 001 explains why it's delicate.
>
> ## What "done" looks like
>
> Steps 1–4 shipped, `pytest` green including the new golden-set test, the beekeeping
> case suppressed, the job-description case suppressed, and Barbara able to run one
> command to see every diagram decision the current code would make on real logged
> traffic.

---

## Notes for Barbara (not part of the prompt)

**What you'll need to do:** one labeling pass, roughly 30 minutes, described in
`GOLDEN_SET_PROTOCOL.md`. Everything else the agent can do alone. You are the only
one who can say what the *right* answer is for an ambiguous query — that judgment is
the actual specification, and it can't be delegated.

**The log file.** Steps 2 onward want a current `latest.json`. Pull it with
`./scripts/pull_latest_log.sh`, or upload it to the session. It is gitignored and
**must stay that way** — see the privacy note in the protocol doc.

**If you only have time for one thing**, do the labeling pass. Steps 1, 3, and 4 are
mechanical; step 2 is the one that encodes your taste into something testable.
