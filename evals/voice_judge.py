#!/usr/bin/env python3
"""
voice_judge.py — first-cut voice & judgment-fidelity evaluator for the Digital Twin.

The existing eval (run_evals.py) scores *mechanical* features: word count, whether
markdown was used, whether a follow-up regex matched. None of that measures the one
thing that matters most for this project — does an answer sound like Barbara and
*reason* like her, or like a generic hedging assistant?

This script closes that gap. It uses an LLM as a judge, anchored on a corpus of
Barbara's actual writing (voice/samples/*.md), and scores each Twin answer on:

  - voice_fidelity      does it sound like the exhibits (cadence, register, idiosyncrasy)?
  - reasoning_fidelity  does it reason like her — problems before skills, frameworks in
                        service of a concrete example, honest "I don't know"?
  - tics                which banned constructions appear (affirmation openers, the
                        "not X but Y" negation flip, "I hope that helps", restating the
                        question, over-formatting) — these come straight from SYSTEM_PROMPT.md
                        SECTION 6 and are the exact things being violated in production today.

GROUND TRUTH MATTERS. With an empty voice/samples/ folder this judge is *circular* — it
just re-scores the Twin against the system prompt's own self-description. It will say so,
loudly, and mark the run provisional. Drop 10–15 real excerpts into voice/samples/ (see
voice/README.md for the method) and the scores become real.

Usage:
    python evals/voice_judge.py                          # scores evals/voice_answers_starter.jsonl
    python evals/voice_judge.py --answers path.jsonl     # each line: {"question":..., "answer":...}
    python evals/voice_judge.py --limit 5
    python evals/voice_judge.py --model anthropic/claude-opus-4-8   # a stronger judge

The judge model defaults to VOICE_JUDGE_MODEL, else a capable general model. A judge should
be at least as strong as the model that generated the answers — you want the critic smarter
than the writer.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from statistics import mean

import litellm
from dotenv import load_dotenv

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
load_dotenv(dotenv_path=_ROOT / ".env", override=False)

VOICE_DIR = _ROOT / "voice" / "samples"
DEFAULT_ANSWERS = _HERE / "voice_answers_starter.jsonl"
SYSTEM_PROMPT_FILE = _ROOT / "SYSTEM_PROMPT.md"
DEFAULT_JUDGE_MODEL = os.getenv("VOICE_JUDGE_MODEL", "openai/gpt-4.1")

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.S)


# ---------------------------------------------------------------------------
# Loading the voice corpus and the answers to score
# ---------------------------------------------------------------------------

def load_voice_samples(voice_dir: Path) -> list[dict]:
    """Read voice/samples/*.md into [{register, source, text}]. Skips the template."""
    samples = []
    if not voice_dir.exists():
        return samples
    for path in sorted(voice_dir.glob("*.md")):
        if "TEMPLATE" in path.stem.upper():
            continue
        raw = path.read_text(encoding="utf-8")
        meta, body = {}, raw
        m = FRONTMATTER_RE.match(raw)
        if m:
            for line in m.group(1).splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    meta[key.strip()] = val.strip()
            body = m.group(2)
        body = body.strip()
        if body:
            samples.append({
                "register": meta.get("register", "unspecified"),
                "source": meta.get("source", path.name),
                "text": body,
            })
    return samples


def load_answers(path: Path, limit: int | None) -> list[dict]:
    answers = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("question") and row.get("answer"):
                answers.append(row)
            if limit and len(answers) >= limit:
                break
    return answers


def prompt_voice_fallback() -> str:
    """When no corpus exists, fall back to the prose voice sections of the system prompt.

    This is explicitly a DESCRIPTION of the voice, not an EXHIBIT of it — the judge is told
    as much, and the run is flagged provisional.
    """
    text = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
    # Grab SECTION 2 (HOW SHE SOUNDS) through the end of SECTION 3 (NARRATIVE PRIORITIES).
    start = text.find("## SECTION 2")
    end = text.find("## SECTION 3.5")
    return text[start:end].strip() if start != -1 and end != -1 else text[:2000]


# ---------------------------------------------------------------------------
# The judge
# ---------------------------------------------------------------------------

RUBRIC = """You are evaluating whether a chatbot answer sounds like, and reasons like, a
specific person — Barbara, a cognitive scientist and AI engineer. You are a careful critic
with an ear for authorial voice. You do not flatter. A generic, competent, hedging
"assistant" tone is a DEFECT here, not a neutral outcome.

Score each answer on two 1–5 axes (5 = indistinguishable from her; 1 = generic assistant):

- voice_fidelity: cadence, sentence shape, word choice, register. Does it read like the
  VOICE REFERENCE below, or like a well-formatted general-purpose assistant? Heavy bolding,
  bulleted lists where prose would do, and uniformly polished sentences push this DOWN.

- reasoning_fidelity: does it reason the way she does? Leads with the *problem* before the
  skill/tech; uses a framework only to illuminate a concrete example, never as a standalone
  lecture; is honest about uncertainty ("I don't know" is a strength, not a failure).

Also detect these specific tics (report only the ones actually present, as short slugs):
  affirmation_opener      — opens with "Absolutely", "Great question", "Of course", etc.
  negation_flip           — the "it's not X, it's Y" / "not just X" construction
  i_hope_that_helps       — closes with "I hope that helps" or similar filler
  restates_question       — begins by repeating the question back
  over_formatted          — bolding/lists/tables doing work that prose should do

Return ONLY a JSON object, no prose around it:
{
  "voice_fidelity": <int 1-5>,
  "reasoning_fidelity": <int 1-5>,
  "overall": <int 1-5>,
  "tics": [<slug>, ...],
  "weakest_sentence": "<the single least-Barbara sentence, verbatim>",
  "rewrite": "<that one sentence, rewritten in her voice>",
  "justification": "<1-2 sentences on the gap between this answer and her voice>"
}"""


def build_voice_reference(samples: list[dict], fallback: str) -> tuple[str, bool]:
    """Return (reference_block, grounded). grounded=False means we're using the prompt's
    self-description — a circular, provisional signal."""
    if samples:
        blocks = [f"[{s['register']}] (from {s['source']})\n{s['text']}" for s in samples]
        return "\n\n".join(blocks), True
    warning = (
        "NO WRITING SAMPLES WERE PROVIDED. What follows is the system prompt's own "
        "DESCRIPTION of the target voice — not examples of it. Treat every score as "
        "provisional and lean conservative; you are checking against a description, which "
        "cannot fully define a voice.\n\n" + fallback
    )
    return warning, False


def judge_answer(question: str, answer: str, voice_reference: str, model: str) -> dict:
    user = (
        f"VOICE REFERENCE (the target — how Barbara actually writes):\n{voice_reference}\n\n"
        f"=====\nNow score this Twin answer.\n\n"
        f"QUESTION: {question}\n\nANSWER:\n{answer}"
    )
    resp = litellm.completion(
        model=model,
        messages=[{"role": "system", "content": RUBRIC},
                  {"role": "user", "content": user}],
        temperature=0.0,
    )
    content = (resp.choices[0].message.content or "").strip()
    # Strip code fences if the model wrapped the JSON.
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content).strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", content, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        return {"error": "could not parse judge output", "raw": content[:400]}


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def coverage_report(samples: list[dict]) -> None:
    wanted = ["explaining", "storytelling", "reflective", "wry", "direct", "technical-peer"]
    have = {s["register"] for s in samples}
    print("Voice corpus coverage:")
    for reg in wanted:
        mark = "✓" if reg in have else "·"
        print(f"   {mark} {reg}")
    extra = have - set(wanted)
    if extra:
        print(f"   (+ other registers: {', '.join(sorted(extra))})")
    print()


def main():
    ap = argparse.ArgumentParser(description="Voice & judgment-fidelity judge for the Digital Twin")
    ap.add_argument("--answers", type=Path, default=DEFAULT_ANSWERS,
                    help="JSONL of {question, answer} objects (default: the starter set from real logs)")
    ap.add_argument("--voice-dir", type=Path, default=VOICE_DIR)
    ap.add_argument("--model", type=str, default=DEFAULT_JUDGE_MODEL)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", type=Path, default=_HERE / "eval_results" / "voice_judge_latest.json")
    args = ap.parse_args()

    samples = load_voice_samples(args.voice_dir)
    voice_reference, grounded = build_voice_reference(samples, prompt_voice_fallback())
    answers = load_answers(args.answers, args.limit)

    print("=" * 74)
    print(f"Voice judge  |  judge model: {args.model}")
    print(f"Answers: {len(answers)} from {args.answers.name}  |  voice samples: {len(samples)}")
    print("=" * 74 + "\n")

    if not grounded:
        print("⚠️  CIRCULARITY WARNING — voice/samples/ is empty.")
        print("    Scores below measure the Twin against the SYSTEM PROMPT's self-description,")
        print("    not against your actual writing. They show the mechanism works and surface")
        print("    the tic violations, but the voice_fidelity numbers are provisional until you")
        print("    add real excerpts (see voice/README.md).\n")
    else:
        coverage_report(samples)

    results, vf, rf, ov = [], [], [], []
    tic_counts: dict[str, int] = {}
    for i, a in enumerate(answers, 1):
        verdict = judge_answer(a["question"], a["answer"], voice_reference, args.model)
        verdict["question"] = a["question"]
        results.append(verdict)
        if "error" in verdict:
            print(f"[{i}/{len(answers)}] {a['question'][:55]!r:57}  PARSE ERROR")
            continue
        vf.append(verdict.get("voice_fidelity", 0))
        rf.append(verdict.get("reasoning_fidelity", 0))
        ov.append(verdict.get("overall", 0))
        for t in verdict.get("tics", []):
            tic_counts[t] = tic_counts.get(t, 0) + 1
        tics = ",".join(verdict.get("tics", [])) or "—"
        print(f"[{i}/{len(answers)}] {a['question'][:55]!r:57}  "
              f"voice={verdict.get('voice_fidelity')} reason={verdict.get('reasoning_fidelity')} "
              f"overall={verdict.get('overall')}  tics: {tics}")

    print("\n" + "=" * 74)
    if vf:
        print(f"Mean voice_fidelity:     {mean(vf):.2f} / 5")
        print(f"Mean reasoning_fidelity: {mean(rf):.2f} / 5")
        print(f"Mean overall:            {mean(ov):.2f} / 5")
    if tic_counts:
        print("\nTic frequency across answers (from SYSTEM_PROMPT.md's own banned list):")
        for tic, n in sorted(tic_counts.items(), key=lambda kv: -kv[1]):
            print(f"   {n:>2}×  {tic}")
    print("=" * 74)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "judge_model": args.model,
        "grounded": grounded,
        "n_answers": len(answers),
        "n_voice_samples": len(samples),
        "means": {"voice_fidelity": mean(vf) if vf else None,
                  "reasoning_fidelity": mean(rf) if rf else None,
                  "overall": mean(ov) if ov else None},
        "tic_counts": tic_counts,
        "results": results,
    }
    args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nFull results (with per-answer rewrites) → {args.out}")
    if not grounded:
        print("Next: add 10–15 excerpts to voice/samples/ (see voice/README.md), then re-run.")


if __name__ == "__main__":
    main()
