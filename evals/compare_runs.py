"""
compare_runs.py — Side-by-side A/B viewer for eval runs.

Discovers all evals/eval_results/eval_results_*.json files and lets you
pick any two runs to compare question-by-question: responses, retrieval
stats, retrieved chunk cards (with "only in A / only in B" badges), and
the rubric.

Run locally:
    python evals/compare_runs.py
    python evals/compare_runs.py --port 7863
"""

import argparse
import html as html_lib
import json
from pathlib import Path

import gradio as gr


HERE = Path(__file__).resolve().parent
RESULTS_DIR = HERE / "eval_results"


# ═══════════════════════════════════════════════════════════════════
# CHUNK CARD STYLING (duplicated from app_admin.py to keep that file
# untouched; eval chunks already carry cosine similarity, so no L2
# conversion needed here)
# ═══════════════════════════════════════════════════════════════════

SOURCE_COLORS = {
    "kb-biosketch":      ("#FAEEDA", "#633806"),
    "kb-philosophy":     ("#E6F4FB", "#0C4470"),
    "kb-positioning":    ("#EDF5E8", "#2A5E1A"),
    "kb-projects":       ("#EEE8FA", "#4A2B8A"),
    "kb-career":         ("#FAE8F2", "#7A1A4A"),
    "kb-publications":   ("#E8F4F8", "#1A5A6A"),
    "project-summaries": ("#E1F5EE", "#085041"),
    "jekyll":            ("#F5F0E8", "#6B5020"),
    "github-readme":     ("#EEEDFE", "#3C3489"),
    "project-summary":   ("#E1F5EE", "#085041"),
    "project-brief":     ("#E1F5EE", "#085041"),
    "mkdocs":            ("#E6F1FB", "#0C447C"),
    "biosketch":         ("#FAEEDA", "#633806"),
    "resume":            ("#EAF3DE", "#27500A"),
}
DEFAULT_SOURCE_COLOR = ("#F1EFE8", "#444441")


def _score_bar_color(sim):
    if sim is None:
        return "#999"
    if sim >= 0.75:
        return "#1D9E75"
    if sim >= 0.55:
        return "#EF9F27"
    return "#E24B4A"


def _chunk_key(chunk):
    """Stable identity for matching the same chunk across runs."""
    return (chunk.get("source", ""), chunk.get("chunk_index"))


def format_eval_chunks_html(chunks, only_in_self_keys=None):
    """Render eval-result `retrieved_chunks` (already cosine sim'd)."""
    if not chunks:
        return '<div style="padding:16px;text-align:center;color:#888;">No chunks retrieved.</div>'
    only_in_self_keys = only_in_self_keys or set()
    cards = []
    for i, chunk in enumerate(chunks):
        sim = chunk.get("similarity")
        pct = max(0, min(100, (sim or 0) * 100))
        bar_color = _score_bar_color(sim)
        raw_source = chunk.get("source") or "unknown:unknown"
        source_type, source_id = (raw_source.split(":", 1)
                                  if ":" in raw_source
                                  else (raw_source, ""))
        section = chunk.get("section") or "—"
        chunk_idx = chunk.get("chunk_index", "?")
        doc = chunk.get("text") or ""
        bg, fg = SOURCE_COLORS.get(source_type, DEFAULT_SOURCE_COLOR)
        text_display = html_lib.escape(doc[:800]) + (" …" if len(doc) > 800 else "")

        only_badge = ""
        if _chunk_key(chunk) in only_in_self_keys:
            only_badge = (
                '<span style="font-size:10px;font-weight:500;padding:1px 8px;'
                'border-radius:99px;background:#FFF4D6;color:#7A5A00;'
                'border:1px solid #E8C75A;">only in this run</span>'
            )

        sim_str = f"{sim:.3f}" if sim is not None else "—"
        cards.append(f"""
        <div style="border:1px solid var(--border-color-primary, #ddd);border-radius:8px;
                    padding:10px 12px;margin-bottom:8px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
            <div style="display:flex;align-items:center;gap:8px;">
                <span style="font-size:11px;font-weight:500;padding:2px 10px;border-radius:99px;
                            background:{bg};color:{fg};">{html_lib.escape(source_type)}</span>
                {only_badge}
            </div>
            <div style="display:flex;align-items:center;gap:8px;">
                <span style="font-size:11px;color:#888;">#{i+1}</span>
                <div style="width:80px;height:4px;border-radius:2px;
                            background:var(--border-color-primary, #e0e0e0);position:relative;">
                    <div style="height:100%;border-radius:2px;position:absolute;left:0;top:0;
                                width:{pct:.0f}%;background:{bar_color};"></div>
                </div>
                <span style="font-size:12px;font-weight:500;min-width:38px;text-align:right;">{sim_str}</span>
            </div>
        </div>
        <div style="font-size:12px;font-family:monospace;padding:8px;
                    background:var(--background-fill-secondary, #f7f7f5);
                    border-radius:6px;line-height:1.5;max-height:140px;
                    overflow-y:auto;white-space:pre-wrap;word-break:break-word;">{text_display}</div>
        <div style="display:flex;flex-wrap:wrap;gap:6px 14px;margin-top:6px;font-size:11px;
                    color:var(--body-text-color-subdued, #999);">
            <span>doc: {html_lib.escape(source_id)}</span>
            <span>section: {html_lib.escape(str(section))}</span>
            <span>chars: {len(doc)}</span>
            <span>chunk: #{chunk_idx}</span>
        </div>
        </div>""")
    header = (
        f'<div style="font-size:13px;color:var(--body-text-color-subdued, #888);'
        f'margin-bottom:8px;padding:0 4px;">{len(chunks)} chunks</div>'
    )
    return header + "\n".join(cards)


# ═══════════════════════════════════════════════════════════════════
# RUN DISCOVERY & LOADING
# ═══════════════════════════════════════════════════════════════════

def discover_runs(results_dir=RESULTS_DIR):
    """Return [(label, path)] for every eval_results_*.json, newest first."""
    if not Path(results_dir).is_dir():
        return []
    files = sorted(Path(results_dir).glob("eval_results_*.json"), reverse=True)
    items = []
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            meta = payload.get("run_metadata", {}) or {}
            label_bits = [
                meta.get("run_timestamp", "")[:19].replace("T", " "),
                meta.get("label") or meta.get("model", "?"),
                f"t={meta.get('temperature', '?')}",
                f"k={meta.get('top_k', '?')}",
            ]
            label = " · ".join(b for b in label_bits if b)
            items.append((f"{label}    [{f.name}]", str(f)))
        except Exception as e:
            items.append((f"(unreadable) {f.name}: {e}", str(f)))
    return items


def load_run(path):
    if not path:
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def results_by_qid(run):
    """Index results by question_id, falling back to question text."""
    out = {}
    if not run:
        return out
    for r in run.get("results", []):
        qid = r.get("question_id") or r.get("question", "")[:80]
        out[qid] = r
    return out


# ═══════════════════════════════════════════════════════════════════
# RENDERERS
# ═══════════════════════════════════════════════════════════════════

META_FIELDS = [
    ("model", "Model"),
    ("provider", "Provider"),
    ("temperature", "Temp"),
    ("top_k", "Top-K"),
    ("question_count", "Questions"),
    ("label", "Label"),
    ("run_timestamp", "Run time"),
]


def render_metadata_strip(run_a, run_b):
    if not run_a or not run_b:
        return '<div style="color:#888;padding:8px;">Pick two runs to compare.</div>'
    ma = run_a.get("run_metadata", {}) or {}
    mb = run_b.get("run_metadata", {}) or {}

    rows = []
    rows.append(
        '<tr><th style="text-align:left;padding:4px 10px;font-size:11px;color:#888;"></th>'
        '<th style="text-align:left;padding:4px 10px;font-size:12px;">Run A</th>'
        '<th style="text-align:left;padding:4px 10px;font-size:12px;">Run B</th></tr>'
    )
    for key, label in META_FIELDS:
        va = ma.get(key, "")
        vb = mb.get(key, "")
        differs = str(va) != str(vb)
        bg = "background:#FFF8DC;" if differs else ""
        rows.append(
            f'<tr><td style="padding:3px 10px;font-size:11px;color:#666;">{label}</td>'
            f'<td style="padding:3px 10px;font-size:12px;{bg}">{html_lib.escape(str(va))}</td>'
            f'<td style="padding:3px 10px;font-size:12px;{bg}">{html_lib.escape(str(vb))}</td></tr>'
        )
    return (
        '<table style="border-collapse:collapse;border:1px solid var(--border-color-primary, #ddd);'
        'border-radius:6px;width:100%;">'
        + "".join(rows) +
        '</table>'
    )


def _stat_chip(label, value, tinted=False):
    bg = "background:#FFF8DC;" if tinted else "background:var(--background-fill-secondary,#f7f7f5);"
    return (
        f'<span style="display:inline-block;padding:3px 8px;margin:2px 4px 2px 0;'
        f'border-radius:6px;font-size:11px;{bg}">'
        f'<span style="color:#888;">{label}:</span> <b>{html_lib.escape(str(value))}</b></span>'
    )


def render_stats_strip(result, other_result):
    if not result:
        return ""
    keys = [
        ("response_length_words", "words"),
        ("chunk_similarity_avg", "sim avg"),
        ("chunk_similarity_max", "sim max"),
        ("markdown_used", "md"),
        ("followup_present", "followup"),
        ("links_used", "links"),
        ("total_tokens", "tokens"),
        ("cost_usd", "cost $"),
    ]
    chips = []
    for k, label in keys:
        v = result.get(k)
        if v is None:
            continue
        other_v = (other_result or {}).get(k)
        tinted = (other_v is not None) and (str(other_v) != str(v))
        if isinstance(v, float):
            v_disp = f"{v:.4f}" if k == "cost_usd" else f"{v:.3f}" if k.startswith("chunk_") else v
        else:
            v_disp = v
        chips.append(_stat_chip(label, v_disp, tinted=tinted))
    n_chunks = len(result.get("retrieved_chunks") or [])
    other_n = len((other_result or {}).get("retrieved_chunks") or [])
    chips.append(_stat_chip("chunks", n_chunks, tinted=(other_result is not None and other_n != n_chunks)))
    return '<div style="margin:4px 0 8px 0;">' + "".join(chips) + '</div>'


def render_projects_html(result):
    projects = (result or {}).get("specific_projects_mentioned") or []
    if isinstance(projects, str):
        projects = [p.strip() for p in projects.split(",") if p.strip()]
    if not projects:
        return '<div style="color:#888;font-size:12px;">(none)</div>'
    chips = "".join(
        f'<span style="display:inline-block;padding:2px 8px;margin:2px;border-radius:99px;'
        f'background:#EEE8FA;color:#4A2B8A;font-size:11px;">{html_lib.escape(str(p))}</span>'
        for p in projects
    )
    return f'<div>{chips}</div>'


RUBRIC_FIELDS = [
    ("must_cover", "Must cover"),
    ("nice_to_have", "Nice to have"),
    ("should_not_do", "Should NOT do"),
    ("preferred_structure", "Preferred structure"),
    ("preferred_followup_behavior", "Preferred follow-up"),
    ("acceptable_projects_or_examples", "Acceptable projects / examples"),
    ("grounding_expectation", "Grounding expectation"),
    ("notes", "Notes"),
]


def render_rubric_html(result_a, result_b):
    """Rubric is shared per question — prefer A, fall back to B."""
    src = result_a or result_b or {}
    rows = []
    for k, label in RUBRIC_FIELDS:
        v = src.get(k, "")
        if not v:
            continue
        rows.append(
            f'<tr><td style="padding:4px 10px;font-size:11px;color:#666;vertical-align:top;'
            f'white-space:nowrap;">{label}</td>'
            f'<td style="padding:4px 10px;font-size:12px;">{html_lib.escape(str(v))}</td></tr>'
        )
    if not rows:
        return '<div style="color:#888;padding:8px;">(no rubric fields populated)</div>'
    return (
        '<table style="border-collapse:collapse;width:100%;">'
        + "".join(rows) + '</table>'
    )


def render_question_header(result_a, result_b):
    src = result_a or result_b or {}
    q = src.get("question", "")
    meta_bits = []
    for k in ("question_type", "intent", "audience_mode", "difficulty", "priority"):
        v = src.get(k)
        if v:
            meta_bits.append(f'<span style="color:#888;">{k}:</span> {html_lib.escape(str(v))}')
    return (
        f'<div style="padding:8px 4px;">'
        f'<div style="font-size:15px;font-weight:500;margin-bottom:4px;">{html_lib.escape(q)}</div>'
        f'<div style="font-size:11px;display:flex;gap:14px;flex-wrap:wrap;">'
        + " ".join(meta_bits) + '</div></div>'
    )


# ═══════════════════════════════════════════════════════════════════
# NAVIGATOR
# ═══════════════════════════════════════════════════════════════════

def build_question_choices(run_a, run_b):
    """Return choices for the question selector, with delta indicators."""
    if not run_a and not run_b:
        return []
    ra = results_by_qid(run_a)
    rb = results_by_qid(run_b)
    qids = list(dict.fromkeys(list(ra.keys()) + list(rb.keys())))

    choices = []
    for qid in qids:
        a = ra.get(qid) or {}
        b = rb.get(qid) or {}
        sim_a = a.get("chunk_similarity_avg")
        sim_b = b.get("chunk_similarity_avg")
        delta = ""
        if sim_a is not None and sim_b is not None:
            d = sim_b - sim_a
            if abs(d) >= 0.005:
                arrow = "▴" if d > 0 else "▾"
                delta = f"  Δsim {arrow}{d:+.2f}"
        len_flag = ""
        la = a.get("response_length_words")
        lb = b.get("response_length_words")
        if la and lb:
            if abs(lb - la) / max(la, lb) > 0.5:
                len_flag = "  ●len"
        qtype = (a.get("question_type") or b.get("question_type") or "")
        label = f"{qid}  {qtype}{delta}{len_flag}".strip()
        choices.append((label, qid))
    return choices


# ═══════════════════════════════════════════════════════════════════
# CALLBACKS
# ═══════════════════════════════════════════════════════════════════

def on_runs_changed(path_a, path_b):
    run_a = load_run(path_a)
    run_b = load_run(path_b)
    meta_html = render_metadata_strip(run_a, run_b)
    choices = build_question_choices(run_a, run_b)
    radio = gr.update(choices=choices, value=(choices[0][1] if choices else None))
    blank = '<div style="color:#888;padding:8px;">(no question selected)</div>'
    # meta, radio, header, resp_a, resp_b, stats_a, stats_b, chunks_a, chunks_b, proj_a, proj_b, rubric
    return (meta_html, radio,
            blank, "", "", "", "", blank, blank, blank, blank, blank)


def on_question_changed(path_a, path_b, qid):
    run_a = load_run(path_a)
    run_b = load_run(path_b)
    ra = results_by_qid(run_a).get(qid) or {}
    rb = results_by_qid(run_b).get(qid) or {}

    header = render_question_header(ra, rb)

    resp_a = ra.get("response") or (f"_(error: {ra['error']})_" if "error" in ra else "_(not in this run)_")
    resp_b = rb.get("response") or (f"_(error: {rb['error']})_" if "error" in rb else "_(not in this run)_")

    stats_a = render_stats_strip(ra, rb)
    stats_b = render_stats_strip(rb, ra)

    chunks_a = ra.get("retrieved_chunks") or []
    chunks_b = rb.get("retrieved_chunks") or []
    keys_a = {_chunk_key(c) for c in chunks_a}
    keys_b = {_chunk_key(c) for c in chunks_b}
    only_in_a = keys_a - keys_b
    only_in_b = keys_b - keys_a
    chunks_a_html = format_eval_chunks_html(chunks_a, only_in_self_keys=only_in_a)
    chunks_b_html = format_eval_chunks_html(chunks_b, only_in_self_keys=only_in_b)

    projects_a = render_projects_html(ra)
    projects_b = render_projects_html(rb)

    rubric = render_rubric_html(ra, rb)

    return (header, resp_a, resp_b, stats_a, stats_b,
            chunks_a_html, chunks_b_html, projects_a, projects_b, rubric)


# ═══════════════════════════════════════════════════════════════════
# UI
# ═══════════════════════════════════════════════════════════════════

def build_app(results_dir=RESULTS_DIR):
    runs = discover_runs(results_dir)
    if not runs:
        empty_msg = (f"No eval result files found in {results_dir}. "
                     f"Run `python evals/run_evals.py` first.")
        with gr.Blocks(title="Eval Run Comparison") as demo:
            gr.Markdown(f"### {empty_msg}")
        return demo

    default_a = runs[0][1]
    default_b = runs[1][1] if len(runs) > 1 else runs[0][1]

    with gr.Blocks(title="Eval Run Comparison", theme=gr.themes.Soft()) as demo:
        gr.Markdown("## Eval Run Comparison")

        with gr.Row():
            run_a_dd = gr.Dropdown(choices=runs, value=default_a, label="Run A", scale=1)
            run_b_dd = gr.Dropdown(choices=runs, value=default_b, label="Run B", scale=1)

        meta_strip = gr.HTML()

        with gr.Row():
            with gr.Column(scale=1, min_width=240):
                gr.Markdown("**Questions**")
                question_radio = gr.Radio(choices=[], label="", interactive=True)
            with gr.Column(scale=4):
                question_header = gr.HTML()
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### Run A")
                        stats_a_html = gr.HTML()
                        response_a_md = gr.Markdown()
                        with gr.Accordion("Retrieved chunks", open=False):
                            chunks_a_html = gr.HTML()
                        with gr.Accordion("Specific projects mentioned", open=False):
                            projects_a_html = gr.HTML()
                    with gr.Column():
                        gr.Markdown("### Run B")
                        stats_b_html = gr.HTML()
                        response_b_md = gr.Markdown()
                        with gr.Accordion("Retrieved chunks", open=False):
                            chunks_b_html = gr.HTML()
                        with gr.Accordion("Specific projects mentioned", open=False):
                            projects_b_html = gr.HTML()
                with gr.Accordion("Rubric (shared per question)", open=False):
                    rubric_html = gr.HTML()

        # When runs change: refresh metadata strip + question list, and clear panels.
        run_a_dd.change(
            on_runs_changed, [run_a_dd, run_b_dd],
            [meta_strip, question_radio,
             question_header, response_a_md, response_b_md,
             stats_a_html, stats_b_html,
             chunks_a_html, chunks_b_html,
             projects_a_html, projects_b_html, rubric_html],
        )
        run_b_dd.change(
            on_runs_changed, [run_a_dd, run_b_dd],
            [meta_strip, question_radio,
             question_header, response_a_md, response_b_md,
             stats_a_html, stats_b_html,
             chunks_a_html, chunks_b_html,
             projects_a_html, projects_b_html, rubric_html],
        )

        # When the selected question changes: refresh the main panel.
        question_radio.change(
            on_question_changed, [run_a_dd, run_b_dd, question_radio],
            [question_header, response_a_md, response_b_md,
             stats_a_html, stats_b_html,
             chunks_a_html, chunks_b_html,
             projects_a_html, projects_b_html, rubric_html],
        )

        # Initial population on load.
        demo.load(
            on_runs_changed, [run_a_dd, run_b_dd],
            [meta_strip, question_radio,
             question_header, response_a_md, response_b_md,
             stats_a_html, stats_b_html,
             chunks_a_html, chunks_b_html,
             projects_a_html, projects_b_html, rubric_html],
        )

    return demo


def main():
    parser = argparse.ArgumentParser(description="Compare two eval runs side-by-side")
    parser.add_argument("--port", type=int, default=7863, help="Port to serve on")
    parser.add_argument("--results-dir", type=str, default=str(RESULTS_DIR),
                        help="Directory containing eval_results_*.json")
    parser.add_argument("--share", action="store_true", help="Create a public Gradio share link")
    args = parser.parse_args()

    demo = build_app(Path(args.results_dir))
    demo.launch(server_port=args.port, share=args.share)


if __name__ == "__main__":
    main()
