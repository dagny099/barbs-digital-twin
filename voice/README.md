# Voice reference corpus

This folder is the **ground truth for what Barbara sounds like.** The voice judge
(`evals/voice_judge.py`) reads every `.md` file in `voice/samples/` and uses them as the
target the Twin's answers are measured against. Without these, a "voice" score is circular —
it just re-scores the Twin against the adjectives already in `SYSTEM_PROMPT.md`.

The point of this corpus is to replace *description* of the voice ("warm but direct, a little
wry") with *exhibits* of it. A model can pattern-match an exhibit; it can only approximate an
adjective.

## How to pick samples — the method

You have a lot of writing. The mistake would be to dump all of it here, or to pick your most
polished pieces. Neither helps. Follow these four rules:

1. **Range over quality.** Do not pick your "best" writing. Pick writing that covers the
   *registers the Twin actually has to hit*. If every sample is a polished blog intro, the
   judge learns "Barbara = polished blog intro" and will penalize you for sounding casual when
   casual is correct. Aim to cover the registers in the table below.

2. **~10–15 samples is plenty. More is worse.** This is a voice fingerprint, not a training
   set. A dozen well-chosen excerpts anchor a judge better than fifty. If you're past 15, you're
   collecting, not curating.

3. **Short and self-contained: 100–300 words each.** One excerpt should hold a complete thought
   in your voice. Trim to the part that *sounds most like you* and cut the setup. A judge reads
   cadence, sentence shape, and word choice — it doesn't need the whole essay.

4. **Real, unedited-for-the-Twin prose.** Use what you actually wrote for a human audience —
   blog posts, dissertation passages, a talk transcript, a Slack message you were proud of, an
   email explaining something. Do **not** write new samples *for* this folder; you'll
   unconsciously write toward what you think the Twin should sound like, which defeats the
   purpose.

## Registers to cover (your coverage checklist)

Try to land at least one sample in each row. The `register` tag in each file's frontmatter is
how the judge (and you) can see what's covered and what's missing.

| register            | what it captures                                              |
|---------------------|--------------------------------------------------------------|
| `explaining`        | you teaching a technical idea to a curious non-expert         |
| `storytelling`      | you narrating a project — problem, insight, what happened     |
| `reflective`        | you on meaning, values, why the work matters (grounded)       |
| `wry`               | you being dry, lightly funny, informal                        |
| `direct`            | you being blunt / matter-of-fact / saying "I don't know"      |
| `technical-peer`    | you talking shop with someone who already gets it             |

If a register is empty, the judge can't hold the Twin to it — so a gap here is a blind spot in
what you can measure.

## File format

One excerpt per file in `voice/samples/`, named `NN-short-slug.md`. See
`samples/00-TEMPLATE.md` for the frontmatter. The judge reads the frontmatter for coverage
reporting and the body as the voice exhibit.
