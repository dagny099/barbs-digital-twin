#!/usr/bin/env python3
"""
Lightweight analysis for Digital Twin query_log.jsonl

Assumes chat-turn rows include:
- ts
- session_id
- turn_index
- message

Also uses, when present:
- workflow
- latency_ms
- chunk_similarity_avg
- response_chars
- provider
- model
- cost_usd
- audience_tier

Vote rows are expected to have:
- event == "vote"

Outputs:
- analysis_out/summary.json
- analysis_out/sessions.csv
- analysis_out/daily_counts.csv
- analysis_out/report.md
"""

import csv
import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


# ----------------------------
# Config
# ----------------------------

LOG_PATH = Path("query_log.jsonl")
OUT_DIR = Path("output/analysis_out")
OUT_DIR.mkdir(exist_ok=True)

TOP_N_PROMPTS = 10
TOP_N_SESSIONS_IN_REPORT = 10
RECENT_DAYS_IN_REPORT = 14


# ----------------------------
# Helpers
# ----------------------------

def parse_ts(ts_str: str) -> datetime:
    """Parse ISO timestamp, including trailing Z if present."""
    return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))


def load_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                # Ignore malformed rows rather than failing the whole run
                continue
    return rows


def safe_mean(values, ndigits=2):
    values = [v for v in values if isinstance(v, (int, float))]
    if not values:
        return None
    return round(sum(values) / len(values), ndigits)


def safe_median(values, ndigits=2):
    values = [v for v in values if isinstance(v, (int, float))]
    if not values:
        return None
    return round(statistics.median(values), ndigits)


def fmt_num(value, default="—"):
    if value is None:
        return default
    return str(value)


def fmt_money(value):
    if value is None:
        return "—"
    return f"${value:.4f}"


def md_table(headers, rows):
    """Return a simple markdown table string."""
    out = []
    out.append("| " + " | ".join(headers) + " |")
    out.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        out.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(out)


def truncate(text, n=100):
    text = (text or "").strip().replace("\n", " ")
    return text if len(text) <= n else text[: n - 1] + "…"


# ----------------------------
# Main analysis
# ----------------------------

def main():
    rows = load_jsonl(LOG_PATH)

    vote_rows = [r for r in rows if r.get("event") == "vote"]
    chat_rows = [
        r for r in rows
        if r.get("event") != "vote"
        and r.get("session_id")
        and r.get("turn_index") is not None
        and r.get("message") is not None
        and r.get("ts")
    ]

    # Sort chat rows by time
    chat_rows.sort(key=lambda r: parse_ts(r["ts"]))
    vote_rows.sort(key=lambda r: parse_ts(r["ts"]) if r.get("ts") else datetime.min)

    # Group rows into sessions
    sessions = defaultdict(list)
    for row in chat_rows:
        sessions[row["session_id"]].append(row)

    # Sort each session and derive session-level metrics
    session_rows = []
    first_prompt_counter = Counter()
    all_prompt_counter = Counter()
    workflow_counter = Counter()
    provider_counter = Counter()
    model_counter = Counter()
    audience_counter = Counter()

    for session_id, items in sessions.items():
        items.sort(key=lambda r: parse_ts(r["ts"]))

        # Turn order should already be present, but sorting by timestamp is safest
        turns = len(items)
        first_row = items[0]
        last_row = items[-1]

        first_prompt = (first_row.get("message") or "").strip()
        last_prompt = (last_row.get("message") or "").strip()

        first_prompt_counter[first_prompt] += 1

        for item in items:
            msg = (item.get("message") or "").strip()
            if msg:
                all_prompt_counter[msg] += 1

            workflow_counter[item.get("workflow") or "unknown"] += 1
            provider_counter[item.get("provider") or "unknown"] += 1
            model_counter[item.get("model") or "unknown"] += 1
            audience_counter[item.get("audience_tier") or "unknown"] += 1

        latencies = [i.get("latency_ms") for i in items]
        similarities = [i.get("chunk_similarity_avg") for i in items]
        response_chars = [i.get("response_chars") for i in items]
        costs = [i.get("cost_usd") for i in items]

        session_rows.append({
            "session_id": session_id,
            "start_ts": first_row["ts"],
            "end_ts": last_row["ts"],
            "turns": turns,
            "first_prompt": first_prompt,
            "last_prompt": last_prompt,
            "avg_latency_ms": safe_mean(latencies),
            "avg_similarity": safe_mean(similarities, ndigits=3),
            "total_response_chars": sum(v for v in response_chars if isinstance(v, (int, float))),
            "total_cost_usd": round(sum(v for v in costs if isinstance(v, (int, float))), 6),
            "providers": ", ".join(sorted({i.get("provider") for i in items if i.get("provider")})),
            "models": ", ".join(sorted({i.get("model") for i in items if i.get("model")})),
            "audience_tiers": ", ".join(sorted({i.get("audience_tier") for i in items if i.get("audience_tier")})),
        })

    session_rows.sort(key=lambda r: r["start_ts"])

    # Daily rollup
    # A session is counted on the day it starts.
    sessions_by_day = defaultdict(list)
    turns_by_day = Counter()
    votes_by_day = Counter()

    for s in session_rows:
        start_day = parse_ts(s["start_ts"]).date().isoformat()
        sessions_by_day[start_day].append(s)

    for row in chat_rows:
        day = parse_ts(row["ts"]).date().isoformat()
        turns_by_day[day] += 1

    for row in vote_rows:
        if row.get("ts"):
            day = parse_ts(row["ts"]).date().isoformat()
            votes_by_day[day] += 1

    all_days = sorted(set(sessions_by_day) | set(turns_by_day) | set(votes_by_day))
    daily_rows = []

    for day in all_days:
        day_sessions = sessions_by_day.get(day, [])
        session_count = len(day_sessions)
        one_turn_sessions = sum(1 for s in day_sessions if s["turns"] == 1)

        daily_rows.append({
            "date": day,
            "sessions": session_count,
            "turns": turns_by_day.get(day, 0),
            "one_turn_sessions": one_turn_sessions,
            "avg_turns_per_session": round(
                sum(s["turns"] for s in day_sessions) / session_count, 2
            ) if session_count else 0,
            "votes": votes_by_day.get(day, 0),
        })

    # Overall summary
    total_sessions = len(session_rows)
    total_turns = len(chat_rows)
    turn_counts = [s["turns"] for s in session_rows]
    one_turn_sessions = sum(1 for n in turn_counts if n == 1)

    summary = {
        "total_chat_turns": total_turns,
        "total_sessions": total_sessions,
        "avg_turns_per_session": round(sum(turn_counts) / total_sessions, 2) if total_sessions else 0,
        "median_turns_per_session": safe_median(turn_counts) or 0,
        "one_turn_sessions": one_turn_sessions,
        "pct_one_turn_sessions": round((one_turn_sessions / total_sessions) * 100, 1) if total_sessions else 0,
        "total_vote_events": len(vote_rows),
        "avg_latency_ms": safe_mean([r.get("latency_ms") for r in chat_rows]),
        "avg_chunk_similarity": safe_mean([r.get("chunk_similarity_avg") for r in chat_rows], ndigits=3),
        "avg_response_chars": safe_mean([r.get("response_chars") for r in chat_rows]),
        "total_cost_usd": round(
            sum(r.get("cost_usd", 0.0) for r in chat_rows if isinstance(r.get("cost_usd"), (int, float))),
            6
        ),
        "top_first_prompts": first_prompt_counter.most_common(TOP_N_PROMPTS),
        "top_all_prompts": all_prompt_counter.most_common(TOP_N_PROMPTS),
        "workflow_counts": workflow_counter.most_common(),
        "provider_counts": provider_counter.most_common(),
        "model_counts": model_counter.most_common(),
        "audience_tier_counts": audience_counter.most_common(),
        "analysis_assumption": "session_id and turn_index are present on chat rows",
    }

    # ----------------------------
    # Write files
    # ----------------------------

    with (OUT_DIR / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    with (OUT_DIR / "sessions.csv").open("w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "session_id", "start_ts", "end_ts", "turns",
            "first_prompt", "last_prompt",
            "avg_latency_ms", "avg_similarity",
            "total_response_chars", "total_cost_usd",
            "providers", "models", "audience_tiers"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(session_rows)

    with (OUT_DIR / "daily_counts.csv").open("w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "date", "sessions", "turns", "one_turn_sessions",
            "avg_turns_per_session", "votes"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(daily_rows)

    # ----------------------------
    # Markdown report
    # ----------------------------

    recent_daily_rows = daily_rows[-RECENT_DAYS_IN_REPORT:]

    longest_sessions = sorted(session_rows, key=lambda s: (-s["turns"], s["start_ts"]))[:TOP_N_SESSIONS_IN_REPORT]
    recent_sessions = sorted(session_rows, key=lambda s: s["start_ts"], reverse=True)[:TOP_N_SESSIONS_IN_REPORT]

    report_lines = []
    report_lines.append("# Digital Twin Log Report")
    report_lines.append("")
    report_lines.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}")
    report_lines.append(f"Source file: `{LOG_PATH}`")
    report_lines.append("")

    report_lines.append("## Headline metrics")
    report_lines.append("")
    report_lines.append(f"- Total chat turns: **{summary['total_chat_turns']}**")
    report_lines.append(f"- Total sessions: **{summary['total_sessions']}**")
    report_lines.append(f"- Avg turns per session: **{summary['avg_turns_per_session']}**")
    report_lines.append(f"- Median turns per session: **{summary['median_turns_per_session']}**")
    report_lines.append(f"- One-turn sessions: **{summary['one_turn_sessions']}** ({summary['pct_one_turn_sessions']}%)")
    report_lines.append(f"- Vote events: **{summary['total_vote_events']}**")
    report_lines.append(f"- Avg latency: **{fmt_num(summary['avg_latency_ms'])} ms**")
    report_lines.append(f"- Avg chunk similarity: **{fmt_num(summary['avg_chunk_similarity'])}**")
    report_lines.append(f"- Avg response chars: **{fmt_num(summary['avg_response_chars'])}**")
    report_lines.append(f"- Total logged cost: **{fmt_money(summary['total_cost_usd'])}**")
    report_lines.append("")

    if recent_daily_rows:
        report_lines.append(f"## Daily activity (last {min(RECENT_DAYS_IN_REPORT, len(recent_daily_rows))} days)")
        report_lines.append("")
        report_lines.append(md_table(
            ["Date", "Sessions", "Turns", "1-turn sessions", "Avg turns/session", "Votes"],
            [
                [
                    r["date"],
                    r["sessions"],
                    r["turns"],
                    r["one_turn_sessions"],
                    r["avg_turns_per_session"],
                    r["votes"],
                ]
                for r in recent_daily_rows
            ]
        ))
        report_lines.append("")

    report_lines.append("## Top first prompts")
    report_lines.append("")
    if summary["top_first_prompts"]:
        report_lines.append(md_table(
            ["Count", "Prompt"],
            [[count, truncate(prompt, 110)] for prompt, count in summary["top_first_prompts"]]
        ))
    else:
        report_lines.append("_No session starts found._")
    report_lines.append("")

    report_lines.append("## Top prompts overall")
    report_lines.append("")
    if summary["top_all_prompts"]:
        report_lines.append(md_table(
            ["Count", "Prompt"],
            [[count, truncate(prompt, 110)] for prompt, count in summary["top_all_prompts"]]
        ))
    else:
        report_lines.append("_No prompts found._")
    report_lines.append("")

    report_lines.append("## Workflow / provider / model mix")
    report_lines.append("")
    report_lines.append("### Workflows")
    if summary["workflow_counts"]:
        report_lines.append(md_table(
            ["Count", "Workflow"],
            [[count, workflow] for workflow, count in summary["workflow_counts"]]
        ))
    else:
        report_lines.append("_None_")
    report_lines.append("")

    report_lines.append("### Providers")
    if summary["provider_counts"]:
        report_lines.append(md_table(
            ["Count", "Provider"],
            [[count, provider] for provider, count in summary["provider_counts"]]
        ))
    else:
        report_lines.append("_None_")
    report_lines.append("")

    report_lines.append("### Models")
    if summary["model_counts"]:
        report_lines.append(md_table(
            ["Count", "Model"],
            [[count, model] for model, count in summary["model_counts"]]
        ))
    else:
        report_lines.append("_None_")
    report_lines.append("")

    report_lines.append("## Longest sessions")
    report_lines.append("")
    if longest_sessions:
        report_lines.append(md_table(
            ["Start", "Session", "Turns", "First prompt", "Avg latency", "Avg similarity"],
            [
                [
                    s["start_ts"][:19],
                    truncate(s["session_id"], 16),
                    s["turns"],
                    truncate(s["first_prompt"], 70),
                    fmt_num(s["avg_latency_ms"]),
                    fmt_num(s["avg_similarity"]),
                ]
                for s in longest_sessions
            ]
        ))
    else:
        report_lines.append("_No sessions found._")
    report_lines.append("")

    report_lines.append("## Most recent sessions")
    report_lines.append("")
    if recent_sessions:
        report_lines.append(md_table(
            ["Start", "Session", "Turns", "First prompt", "Last prompt"],
            [
                [
                    s["start_ts"][:19],
                    truncate(s["session_id"], 16),
                    s["turns"],
                    truncate(s["first_prompt"], 60),
                    truncate(s["last_prompt"], 60),
                ]
                for s in recent_sessions
            ]
        ))
    else:
        report_lines.append("_No sessions found._")
    report_lines.append("")

    report_lines.append("## Notes")
    report_lines.append("")
    report_lines.append("- `session_id` should be treated as an anonymous chat-session identifier, not a person identifier.")
    report_lines.append("- Refreshes or new tabs may create new session IDs.")
    report_lines.append("- This report is best for **engaged usage**, not full site traffic. Use GA for top-of-funnel traffic.")
    report_lines.append("")

    with (OUT_DIR / "report.md").open("w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    # ----------------------------
    # Console summary
    # ----------------------------

    print("\n=== Digital Twin Log Summary ===")
    print(f"Chat turns:               {summary['total_chat_turns']}")
    print(f"Sessions:                 {summary['total_sessions']}")
    print(f"Avg turns/session:        {summary['avg_turns_per_session']}")
    print(f"Median turns/session:     {summary['median_turns_per_session']}")
    print(f"One-turn sessions:        {summary['one_turn_sessions']} ({summary['pct_one_turn_sessions']}%)")
    print(f"Vote events:              {summary['total_vote_events']}")
    print(f"Avg latency (ms):         {summary['avg_latency_ms']}")
    print(f"Avg similarity:           {summary['avg_chunk_similarity']}")
    print(f"Avg response chars:       {summary['avg_response_chars']}")
    print(f"Total cost (logged):      {fmt_money(summary['total_cost_usd'])}")

    print("\nTop first prompts:")
    for prompt, count in summary["top_first_prompts"][:TOP_N_PROMPTS]:
        print(f"  {count:>3}  {truncate(prompt, 100)}")

    print("\nWrote:")
    print(f"  {OUT_DIR / 'summary.json'}")
    print(f"  {OUT_DIR / 'sessions.csv'}")
    print(f"  {OUT_DIR / 'daily_counts.csv'}")
    print(f"  {OUT_DIR / 'report.md'}")


if __name__ == "__main__":
    main()