#!/usr/bin/env python3
"""
Lightweight analysis for Digital Twin query_log.jsonl

Supports:
- configurable cutoff date in a chosen local timezone
- owner-traffic filtering as a first-class dimension
- row-level exclusion OR whole-session exclusion
- optional comparison across owner-filter views

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
- is_owner_traffic

Vote rows are expected to have:
- event == "vote"

Outputs:
- summary.json
- sessions.csv
- daily_counts.csv
- report.md
"""

import argparse
import csv
import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


# ----------------------------
# Defaults / Config
# ----------------------------

DEFAULT_LOG_PATH = Path("query_log.jsonl")
DEFAULT_OUT_DIR = Path("output/analysis_out")

TOP_N_PROMPTS = 10
TOP_N_SESSIONS_IN_REPORT = 10
RECENT_DAYS_IN_REPORT = 14

DEFAULT_CUTOFF_DATE = None          # e.g. "2026-04-10"
DEFAULT_TIMEZONE = "America/Chicago"
DEFAULT_OWNER_FILTER = "none"       # one of: none, row, session


# ----------------------------
# Helpers
# ----------------------------

def parse_ts(ts_str: str) -> datetime:
    """Parse ISO timestamp, including trailing Z if present."""
    return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))


def load_jsonl(path: Path):
    rows = []
    malformed = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                malformed += 1
    if malformed:
        print(f"⚠️  {malformed} malformed JSON line(s) skipped in {path}")
    return rows, malformed


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


def local_day_str(ts_str: str, timezone_str: str) -> str:
    tz = ZoneInfo(timezone_str)
    return parse_ts(ts_str).astimezone(tz).date().isoformat()


def apply_cutoff(rows, cutoff_date: str | None, timezone_str: str):
    """
    Keep rows whose local datetime is on/after cutoff_date at 00:00:00
    in the chosen timezone.
    """
    if not cutoff_date:
        return rows, {"cutoff_date": None, "timezone": timezone_str, "removed_rows": 0}

    tz = ZoneInfo(timezone_str)
    cutoff_dt = datetime.fromisoformat(f"{cutoff_date}T00:00:00").replace(tzinfo=tz)

    kept = []
    removed = 0
    for row in rows:
        ts = row.get("ts")
        if not ts:
            # keep rows with no ts rather than losing them silently
            kept.append(row)
            continue
        local_ts = parse_ts(ts).astimezone(tz)
        if local_ts >= cutoff_dt:
            kept.append(row)
        else:
            removed += 1

    return kept, {"cutoff_date": cutoff_date, "timezone": timezone_str, "removed_rows": removed}


def apply_owner_filter(chat_rows, vote_rows, mode: str):
    """
    Owner-traffic modes:
      - none: keep all rows
      - row: drop only rows where is_owner_traffic == True
      - session: drop any session containing at least one owner-marked row
                 and also drop owner-marked rows even if session_id is missing
    """
    if mode not in {"none", "row", "session"}:
        raise ValueError(f"Unknown owner filter mode: {mode}")

    original_chat = len(chat_rows)
    original_votes = len(vote_rows)

    if mode == "none":
        return chat_rows, vote_rows, {
            "mode": mode,
            "removed_chat_rows": 0,
            "removed_vote_rows": 0,
            "removed_sessions": 0,
        }

    if mode == "row":
        filtered_chat = [r for r in chat_rows if not r.get("is_owner_traffic", False)]
        filtered_votes = [r for r in vote_rows if not r.get("is_owner_traffic", False)]
        return filtered_chat, filtered_votes, {
            "mode": mode,
            "removed_chat_rows": original_chat - len(filtered_chat),
            "removed_vote_rows": original_votes - len(filtered_votes),
            "removed_sessions": 0,
        }

    # session mode
    owner_session_ids = set()
    for row in chat_rows:
        if row.get("is_owner_traffic", False) and row.get("session_id"):
            owner_session_ids.add(row["session_id"])
    for row in vote_rows:
        if row.get("is_owner_traffic", False) and row.get("session_id"):
            owner_session_ids.add(row["session_id"])

    filtered_chat = []
    for row in chat_rows:
        sid = row.get("session_id")
        if row.get("is_owner_traffic", False):
            continue
        if sid and sid in owner_session_ids:
            continue
        filtered_chat.append(row)

    filtered_votes = []
    for row in vote_rows:
        sid = row.get("session_id")
        if row.get("is_owner_traffic", False):
            continue
        if sid and sid in owner_session_ids:
            continue
        filtered_votes.append(row)

    return filtered_chat, filtered_votes, {
        "mode": mode,
        "removed_chat_rows": original_chat - len(filtered_chat),
        "removed_vote_rows": original_votes - len(filtered_votes),
        "removed_sessions": len(owner_session_ids),
    }


def compute_view_metrics(chat_rows, vote_rows):
    """Small summary used for owner-view comparison."""
    sessions = defaultdict(list)
    for row in chat_rows:
        sid = row.get("session_id")
        if sid:
            sessions[sid].append(row)

    turn_counts = [len(v) for v in sessions.values()]
    return {
        "chat_turns": len(chat_rows),
        "sessions": len(sessions),
        "votes": len(vote_rows),
        "avg_turns_per_session": round(sum(turn_counts) / len(turn_counts), 2) if turn_counts else 0,
        "avg_latency_ms": safe_mean([r.get("latency_ms") for r in chat_rows]),
        "avg_chunk_similarity": safe_mean([r.get("chunk_similarity_avg") for r in chat_rows], ndigits=3),
        "total_cost_usd": round(
            sum(r.get("cost_usd", 0.0) for r in chat_rows if isinstance(r.get("cost_usd"), (int, float))),
            6
        ),
    }


# ----------------------------
# Main analysis
# ----------------------------

def build_analysis(rows, out_dir: Path, cutoff_date: str | None, timezone_str: str,
                   owner_filter_mode: str, compare_owner_views: bool,
                   source_log_path: str | None = None,
                   malformed_json_lines: int = 0):
    out_dir.mkdir(parents=True, exist_ok=True)

    # Separate row types first
    vote_rows_all = [r for r in rows if r.get("event") == "vote"]
    chat_rows_all = [
        r for r in rows
        if r.get("event") != "vote"
        and r.get("session_id")
        and r.get("turn_index") is not None
        and r.get("message") is not None
        and r.get("ts")
    ]

    # Optional all-vs-excluded comparison before applying final mode
    owner_view_comparison = None
    if compare_owner_views:
        owner_view_comparison = {}
        for mode in ("none", "row", "session"):
            mode_chat, mode_votes, _ = apply_owner_filter(chat_rows_all, vote_rows_all, mode)
            mode_chat, _ = apply_cutoff(mode_chat, cutoff_date, timezone_str)
            mode_votes, _ = apply_cutoff(mode_votes, cutoff_date, timezone_str)
            owner_view_comparison[mode] = compute_view_metrics(mode_chat, mode_votes)

    # Apply owner filter
    chat_rows, vote_rows, owner_filter_summary = apply_owner_filter(
        chat_rows_all, vote_rows_all, owner_filter_mode
    )

    # Apply cutoff date
    chat_rows, cutoff_chat_summary = apply_cutoff(chat_rows, cutoff_date, timezone_str)
    vote_rows, cutoff_vote_summary = apply_cutoff(vote_rows, cutoff_date, timezone_str)

    # Sort filtered rows
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

        turns = len(items)
        first_row = items[0]
        last_row = items[-1]

        first_prompt = (first_row.get("message") or "").strip()
        last_prompt = (last_row.get("message") or "").strip()

        first_prompt_counter[first_prompt] += 1

        owner_flags = []
        for item in items:
            msg = (item.get("message") or "").strip()
            if msg:
                all_prompt_counter[msg] += 1

            workflow_counter[item.get("workflow") or "unknown"] += 1
            provider_counter[item.get("provider") or "unknown"] += 1
            model_counter[item.get("model") or "unknown"] += 1
            audience_counter[item.get("audience_tier") or "unknown"] += 1
            owner_flags.append(bool(item.get("is_owner_traffic", False)))

        latencies = [i.get("latency_ms") for i in items]
        similarities = [i.get("chunk_similarity_avg") for i in items]
        response_chars = [i.get("response_chars") for i in items]
        costs = [i.get("cost_usd") for i in items]

        session_rows.append({
            "session_id": session_id,
            "start_ts": first_row["ts"],
            "end_ts": last_row["ts"],
            "start_local_date": local_day_str(first_row["ts"], timezone_str),
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
            "contains_owner_marked_rows": any(owner_flags),
        })

    session_rows.sort(key=lambda r: r["start_ts"])

    # Daily rollup in local timezone
    sessions_by_day = defaultdict(list)
    turns_by_day = Counter()
    votes_by_day = Counter()

    for s in session_rows:
        sessions_by_day[s["start_local_date"]].append(s)

    for row in chat_rows:
        day = local_day_str(row["ts"], timezone_str)
        turns_by_day[day] += 1

    for row in vote_rows:
        if row.get("ts"):
            day = local_day_str(row["ts"], timezone_str)
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
        "empty_responses": sum(1 for r in chat_rows if r.get("empty_response", False)),
        "had_errors": sum(1 for r in chat_rows if r.get("had_error", False)),
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
        "malformed_json_lines_skipped": malformed_json_lines,
        "filtering": {
            "cutoff_date": cutoff_date,
            "timezone": timezone_str,
            "owner_filter_mode": owner_filter_mode,
            "cutoff_removed_chat_rows": cutoff_chat_summary["removed_rows"],
            "cutoff_removed_vote_rows": cutoff_vote_summary["removed_rows"],
            "owner_removed_chat_rows": owner_filter_summary["removed_chat_rows"],
            "owner_removed_vote_rows": owner_filter_summary["removed_vote_rows"],
            "owner_removed_sessions": owner_filter_summary["removed_sessions"],
        },
    }

    if owner_view_comparison:
        summary["owner_view_comparison"] = owner_view_comparison

    # ----------------------------
    # Write files
    # ----------------------------

    with (out_dir / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    with (out_dir / "sessions.csv").open("w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "session_id", "start_ts", "end_ts", "start_local_date", "turns",
            "first_prompt", "last_prompt",
            "avg_latency_ms", "avg_similarity",
            "total_response_chars", "total_cost_usd",
            "providers", "models", "audience_tiers",
            "contains_owner_marked_rows",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(session_rows)

    with (out_dir / "daily_counts.csv").open("w", newline="", encoding="utf-8") as f:
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
    report_lines.append(f"Source file: `{source_log_path or DEFAULT_LOG_PATH}`")
    report_lines.append("")
    report_lines.append("## Applied filters")
    report_lines.append("")
    report_lines.append(f"- Local timezone: **{timezone_str}**")
    report_lines.append(f"- Cutoff date: **{cutoff_date or 'None'}**")
    report_lines.append(f"- Owner filter mode: **{owner_filter_mode}**")
    report_lines.append(f"- Chat rows removed by cutoff: **{summary['filtering']['cutoff_removed_chat_rows']}**")
    report_lines.append(f"- Vote rows removed by cutoff: **{summary['filtering']['cutoff_removed_vote_rows']}**")
    report_lines.append(f"- Chat rows removed by owner filter: **{summary['filtering']['owner_removed_chat_rows']}**")
    report_lines.append(f"- Vote rows removed by owner filter: **{summary['filtering']['owner_removed_vote_rows']}**")
    if owner_filter_mode == "session":
        report_lines.append(f"- Sessions removed by owner filter: **{summary['filtering']['owner_removed_sessions']}**")
    report_lines.append("")

    if owner_view_comparison:
        report_lines.append("## Owner-traffic comparison")
        report_lines.append("")
        report_lines.append(md_table(
            ["View", "Chat turns", "Sessions", "Votes", "Avg turns/session", "Avg latency", "Avg similarity", "Total cost"],
            [
                [
                    mode,
                    metrics["chat_turns"],
                    metrics["sessions"],
                    metrics["votes"],
                    metrics["avg_turns_per_session"],
                    fmt_num(metrics["avg_latency_ms"]),
                    fmt_num(metrics["avg_chunk_similarity"]),
                    fmt_money(metrics["total_cost_usd"]),
                ]
                for mode, metrics in owner_view_comparison.items()
            ]
        ))
        report_lines.append("")

    report_lines.append("## Headline metrics")
    report_lines.append("")
    report_lines.append(f"- Total chat turns: **{summary['total_chat_turns']}**")
    report_lines.append(f"- Total sessions: **{summary['total_sessions']}**")
    report_lines.append(f"- Avg turns per session: **{summary['avg_turns_per_session']}**")
    report_lines.append(f"- Median turns per session: **{summary['median_turns_per_session']}**")
    report_lines.append(f"- One-turn sessions: **{summary['one_turn_sessions']}** ({summary['pct_one_turn_sessions']}%)")
    report_lines.append(f"- Vote events: **{summary['total_vote_events']}**")
    report_lines.append(f"- Empty responses: **{summary['empty_responses']}**")
    report_lines.append(f"- Had-error rows: **{summary['had_errors']}**")
    report_lines.append(f"- Malformed JSON lines skipped: **{summary['malformed_json_lines_skipped']}**")
    report_lines.append(f"- Avg latency: **{fmt_num(summary['avg_latency_ms'])} ms**")
    report_lines.append(f"- Avg chunk similarity: **{fmt_num(summary['avg_chunk_similarity'])}**")
    report_lines.append(f"- Avg response chars: **{fmt_num(summary['avg_response_chars'])}**")
    report_lines.append(f"- Total logged cost: **{fmt_money(summary['total_cost_usd'])}**")
    report_lines.append("")

    if recent_daily_rows:
        report_lines.append(f"## Daily activity (last {min(RECENT_DAYS_IN_REPORT, len(recent_daily_rows))} local days)")
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
    report_lines.append("- Owner-traffic filtering supports either dropping only flagged rows or dropping whole sessions containing flagged rows.")
    report_lines.append("")

    with (out_dir / "report.md").open("w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    # ----------------------------
    # Console summary
    # ----------------------------

    print("\n=== Digital Twin Log Summary ===")
    print(f"Cutoff date:               {cutoff_date or 'None'} ({timezone_str})")
    print(f"Chat turns:                {summary['total_chat_turns']}")
    print(f"Sessions:                  {summary['total_sessions']}")
    print(f"Avg turns/session:         {summary['avg_turns_per_session']}")
    print(f"Median turns/session:      {summary['median_turns_per_session']}")
    print(f"One-turn sessions:         {summary['one_turn_sessions']} ({summary['pct_one_turn_sessions']}%)")
    print(f"Vote events:               {summary['total_vote_events']}")
    print(f"Empty responses:           {summary['empty_responses']}")
    print(f"Had-error rows:            {summary['had_errors']}")
    print(f"Malformed JSON skipped:    {summary['malformed_json_lines_skipped']}")
    print(f"Avg latency (ms):          {summary['avg_latency_ms']}")
    print(f"Avg similarity:            {summary['avg_chunk_similarity']}")
    print(f"Avg response chars:        {summary['avg_response_chars']}")
    print(f"Total cost (logged):       {fmt_money(summary['total_cost_usd'])}")

    print("\nFilter removals:")
    print(f"  Cutoff removed chats:    {summary['filtering']['cutoff_removed_chat_rows']}")
    print(f"  Cutoff removed votes:    {summary['filtering']['cutoff_removed_vote_rows']}")
    print(f"  Owner removed chats:     {summary['filtering']['owner_removed_chat_rows']}")
    print(f"  Owner removed votes:     {summary['filtering']['owner_removed_vote_rows']}")
    if owner_filter_mode == "session":
        print(f"  Owner removed sessions:  {summary['filtering']['owner_removed_sessions']}")

    if owner_view_comparison:
        print("\nOwner view comparison:")
        for mode, metrics in owner_view_comparison.items():
            print(
                f"  {mode:<7} | chats={metrics['chat_turns']:<4} "
                f"sessions={metrics['sessions']:<4} votes={metrics['votes']:<4} "
                f"avg_turns/session={metrics['avg_turns_per_session']}"
            )

    print("\nTop first prompts:")
    for prompt, count in summary["top_first_prompts"][:TOP_N_PROMPTS]:
        print(f"  {count:>3}  {truncate(prompt, 100)}")

    print("\nWrote:")
    print(f"  {out_dir / 'summary.json'}")
    print(f"  {out_dir / 'sessions.csv'}")
    print(f"  {out_dir / 'daily_counts.csv'}")
    print(f"  {out_dir / 'report.md'}")


def _validated_date(date_str: str) -> str:
    """Exit with a clear message if date_str is not strictly YYYY-MM-DD."""
    try:
        parsed = datetime.strptime(date_str, "%Y-%m-%d")
        if parsed.strftime("%Y-%m-%d") != date_str:
            raise ValueError
    except ValueError:
        raise SystemExit(f"❌ Invalid --cutoff-date '{date_str}'. Expected format: YYYY-MM-DD")
    return date_str


def main():
    parser = argparse.ArgumentParser(
        description="Lightweight Digital Twin log analysis with cutoff-date and owner-traffic filtering."
    )
    parser.add_argument("--log", default=str(DEFAULT_LOG_PATH), help="Path to JSONL log file")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Output directory")
    parser.add_argument("--cutoff-date", default=DEFAULT_CUTOFF_DATE,
                        help="Exclude rows before this local date (YYYY-MM-DD)")
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE,
                        help="Local timezone for date filtering and daily rollups")
    parser.add_argument("--owner-filter", choices=["none", "row", "session"],
                        default=DEFAULT_OWNER_FILTER,
                        help="Owner-traffic handling: none, row-only, or whole-session")
    parser.add_argument("--compare-owner-views", action="store_true",
                        help="Add all vs row-excluded vs session-excluded comparison to outputs")

    args = parser.parse_args()

    if args.cutoff_date:
        _validated_date(args.cutoff_date)

    print(f"ℹ️  Owner filter mode: {args.owner_filter}")

    log_path = Path(args.log)
    if not log_path.exists():
        raise SystemExit(f"❌ Log file not found: {log_path}")

    rows, malformed_json_lines = load_jsonl(log_path)
    build_analysis(
        rows=rows,
        out_dir=Path(args.out_dir),
        cutoff_date=args.cutoff_date,
        timezone_str=args.timezone,
        owner_filter_mode=args.owner_filter,
        compare_owner_views=args.compare_owner_views,
        source_log_path=str(log_path),
        malformed_json_lines=malformed_json_lines,
    )


if __name__ == "__main__":
    main()
