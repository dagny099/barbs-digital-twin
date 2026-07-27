# Golden set protocol

How to build the labeled fixture that specifies when the twin shows a project diagram.

**The point:** the rules can't be tuned without a definition of "right," and the only
person who can supply that definition is Barbara. This protocol turns ~30 minutes of
her judgment into a permanent, executable spec. The agent does everything else.

---

## Why a golden set and not just tests

A normal unit test asserts behavior the developer already decided. Here the *decision
itself* is the open question — is a beekeeping question a diagram question? — and it
varies case by case in ways no rule captures up front.

So the fixture is built backwards: collect real queries, have Barbara say what should
happen, and only then write rules that satisfy her labels. Her labels are the
specification. When a future change breaks one, the test failure is a real
disagreement with her stated intent, not a broken implementation detail.

This is also the guard against the failure mode where an agent "improves" the
heuristics until the numbers look good and the behavior quietly drifts away from what
she wanted.

---

## Step 1 — Agent: assemble the candidate pool

Source: `latest.json` (pull with `./scripts/pull_latest_log.sh`, or ask Barbara to
upload it). As of 2026-07-26 it holds 318 rows spanning 2026-04-02 → 2026-07-26.

Selection rules:

- **Query rows only.** 18 rows are `event: vote` feedback records with no `message`.
- **Exclude owner traffic** where `is_owner_traffic` is `true` (60 rows) — Barbara
  testing her own twin is not representative visitor behavior. Note the field only
  exists from 2026-04-23 onward, so ~210 rows are *unknown* rather than confirmed
  visitor. Treat unknown as usable but lower priority than the 30 confirmed rows.
- **Deduplicate by message text.** `"How was this digital twin built?"` appears many
  times; one row is enough.
- **Weight toward the ambiguous middle.** Obvious cases teach nothing. Prioritize:
  personal questions that mention project keywords, long pasted text, follow-up turns
  in a session (`turn_index > 1`), and any row where the logged `workflow` looks
  arguable.
- Target **50–60 rows**.

### Privacy screen — required, not optional

The log contains real visitor messages, including at least one real name and one
contact request with an email address. The fixture will live in a public repo.

- Drop any row containing a name, email, phone number, employer, or anything that
  identifies a person.
- Drop pasted job descriptions verbatim — keep a **synthetic** stand-in of similar
  length and vocabulary instead, since length is the property being tested.
- If a row is borderline, drop it. There are plenty.
- Flag anything you're unsure about for Barbara rather than deciding alone.

## Step 2 — Agent: propose labels

Write `tests/fixtures/diagram_golden_set.jsonl`, one row per case:

```json
{"message": "How did you get into beekeeping, and does it influence your work?",
 "expect": "none",
 "expect_project": null,
 "proposed_by": "agent",
 "rationale": "Biographical question. D1: a diagram illustrates an answer; this answer is a story.",
 "confidence": "high",
 "confirmed": false}
```

`expect` is one of:

| Value | Meaning |
|-------|---------|
| `none` | No diagram |
| `any` | A diagram, project not pinned (generic walkthrough — D3 nondeterminism) |
| `<project title>` | That specific project's diagram |

Rules for this step:

- **Label every row, including the ones you're unsure about.** A wrong proposal
  Barbara corrects is more useful than a blank she has to fill in.
- Set `confidence` honestly — `low` is a request for attention, and those are the rows
  worth her time.
- Keep `rationale` to one line, and cite the decision it follows (D1/D2/D3).
- Leave `confirmed: false` everywhere. Only Barbara flips it.

## Step 3 — Barbara: the labeling pass

The agent generates a review file — a plain table, ~50 rows, each showing the message,
the proposed label, and the one-line rationale. For each row: agree, or write the
correct label.

**Where to spend the time:** the `confidence: low` rows, and anything where the
rationale sounds like a stretch. Skim the rest.

**The two questions to ask on each row:**

1. If I asked this, would an architecture diagram help me — or would it look like the
   system misread my question?
2. If the answer is "it wouldn't help, but I'd want to know a diagram exists" — that's
   not `none`, that's the **offer** case from D2. Mark it `offer`. If several rows land
   there, that's the signal to build the offer line before the other refinements.

**Time-box it.** If a row takes more than about 20 seconds, mark it `unsure` and move
on. Genuinely ambiguous rows are bad test cases anyway — a rule that has to satisfy
them will be overfit.

Then the agent sets `confirmed: true` on every reviewed row and commits the fixture.

## Step 4 — Agent: the test

`tests/test_diagram_decisions.py` loads the fixture and asserts `decide_diagram()`
against it. Rules:

- **Only `confirmed: true` rows can fail the build.** Unconfirmed rows may run as
  warnings, never as failures. This is what stops agent-proposed labels from silently
  becoming the spec.
- Per D3, an `any` row asserts *some* project was chosen, never which one.
- On failure, print the message, the expected label, what was chosen, and the reason
  string from `decide_diagram()`. A failure should be readable without a debugger.

## Step 5 — Both: confirm it works

The fixture is doing its job when all four of these hold:

1. **It fails on the known bugs before the fix.** Run the test against current `main`
   before touching the scoring. The beekeeping row and the long-paste row should fail.
   *A golden set that passes on unfixed code is measuring nothing* — check this first.
2. **It passes after steps 3 and 4.**
3. **Barbara can run it herself** — one command, output she can read.
4. **It catches a deliberate regression.** Set `Wt_` — no: set the mention threshold to
   `1`, confirm the suite goes red, put it back. Sixty seconds, and it's the only real
   proof the harness has teeth.

---

## Keeping Barbara in the loop, concretely

The risk with agent-driven work like this is a green test suite that encodes the
agent's taste rather than hers. Three cheap habits prevent it:

- **Labels are hers; rationales are the agent's.** If the agent changes a `confirmed`
  label to make a test pass, that is a bug, full stop. Rules change to fit labels, never
  the reverse.
- **Every threshold gets a sentence.** Any magic number in the diff needs a commit-message
  line saying what it is and which fixture rows justify it. `5` had no such sentence,
  which is how it survived unexamined for months.
- **Re-label when reality moves.** After a KB change or a new featured project, re-run
  step 1 against fresh logs and add rows. The fixture is a living record of intent, not
  a one-time gate.

---

**Related:** [`DIAGRAM_FEATURE_KICKOFF.md`](DIAGRAM_FEATURE_KICKOFF.md) ·
[`../DIAGRAM_DISPLAY_DESIGN.md`](../DIAGRAM_DISPLAY_DESIGN.md) ·
[`../LESSONS_LEARNED.md`](../LESSONS_LEARNED.md)
