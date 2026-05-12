"""Internal analytics dashboard (v1) for Barbs Digital Twin.

Run with:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from analytics import (
    build_session_summary,
    compute_overall_metrics,
    error_sessions,
    load_query_log,
    low_similarity_queries,
    prompt_frequency,
    slow_responses,
)

THEME_CSS = """
<style>
:root {
  --bg: #f6f3ee;
  --surface: #fffdf9;
  --surface-2: #f8f5ef;
  --text: #24332f;
  --muted: #5b6c66;
  --teal: #4f8f88;
  --sage: #8da48f;
  --amber: #b08a4a;
  --border: #e5ddd0;
}

.stApp {
  background: var(--bg);
  color: var(--text);
}

.main .block-container {
  padding-top: 1.4rem;
  padding-bottom: 2rem;
  max-width: 1200px;
}

h1, h2, h3 {
  color: var(--text);
  letter-spacing: 0.01em;
}

[data-testid="stMetric"] {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 0.85rem 1rem;
  box-shadow: 0 1px 0 rgba(36, 51, 47, 0.03);
}

[data-testid="stMetricLabel"] {
  color: var(--muted);
  font-weight: 600;
}

[data-testid="stMetricValue"] {
  color: var(--teal);
}

[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #f5f2ec 0%, #f1ede5 100%);
  border-right: 1px solid var(--border);
}

div[data-testid="stVerticalBlock"] div[data-testid="stDataFrame"] {
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
}

hr {
  border-color: var(--border);
  margin-top: 1.1rem;
  margin-bottom: 1.2rem;
}

.section-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 0.8rem 0.95rem 0.5rem 0.95rem;
}

.section-title {
  font-size: 1.02rem;
  font-weight: 650;
  margin-bottom: 0.45rem;
}

.accent-teal { color: var(--teal); }
.accent-sage { color: var(--sage); }
.accent-amber { color: var(--amber); }
</style>
"""

st.set_page_config(page_title="Digital Twin Analytics", layout="wide")
#st.markdown(THEME_CSS, unsafe_allow_html=True)
st.html(THEME_CSS)


@st.cache_data(ttl=60)
def _load_data(log_path: str, start_date: str | None, end_date: str | None, owner_filter: str):
    return load_query_log(log_path=log_path, start_date=start_date, end_date=end_date, owner_filter=owner_filter)


def _pct(n: int, d: int) -> float:
    return round((n / d) * 100, 1) if d else 0.0


def _format_duration(seconds: float | int | None) -> str:
    if seconds is None or pd.isna(seconds):
        return "—"
    seconds = int(seconds)
    mins, sec = divmod(seconds, 60)
    hrs, mins = divmod(mins, 60)
    if hrs:
        return f"{hrs}h {mins}m"
    if mins:
        return f"{mins}m {sec}s"
    return f"{sec}s"

from datetime import datetime

default_log = "latest.json" if Path("latest.json").exists() else "query_log.jsonl" #"query_log.jsonl" 
last_modified = datetime.fromtimestamp(Path(default_log).stat().st_mtime)


st.title("Internal Analytics Dashboard")
st.caption("Focused v1 view of session quality, retrieval quality, and performance.")
st.caption(f"Log file last updated locally: {last_modified}")
st.markdown("<div class='accent-sage' style='margin-top:-0.35rem; margin-bottom:0.55rem;'>Quick scan: quality, engagement, latency, and outliers.</div>", unsafe_allow_html=True)

with st.sidebar:
    st.header("Filters")  
    log_path = st.text_input("Log path", value=default_log)

    owner_choice = st.selectbox(
        "Owner traffic",
        options=["Include all", "Exclude owner rows", "Exclude owner sessions"],
        index=0,
    )
    owner_filter = {
        "Include all": "none",
        "Exclude owner rows": "row",
        "Exclude owner sessions": "session",
    }[owner_choice]

    date_range = st.date_input("Date range (UTC)", value=())
    start_date = end_date = None
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date = date_range[0].isoformat() if date_range[0] else None
        end_date = date_range[1].isoformat() if date_range[1] else None

try:
    chat_df, vote_df, meta = _load_data(log_path, start_date, end_date, owner_filter)
except FileNotFoundError:
    st.error(f"Log file not found: {log_path}")
    st.info("Tip: run from repo root or set an absolute path to query_log.jsonl.")
    st.stop()
except Exception as exc:
    st.error("Failed to load analytics data.")
    st.exception(exc)
    st.stop()

if chat_df.empty:
    st.warning("No chat rows found for the current filters.")
    st.caption("Try widening date range or including owner traffic.")
    st.stop()

# NOTE: workflow may be sparsely populated in mixed/legacy logs; keep filter optional.
workflows = sorted([w for w in chat_df["workflow"].dropna().unique().tolist() if str(w).strip()])
if workflows:
    selected_workflows = st.sidebar.multiselect("Workflow type", options=workflows, default=workflows)
    if selected_workflows:
        chat_df = chat_df[chat_df["workflow"].isin(selected_workflows)].copy()

if chat_df.empty:
    st.warning("No rows remain after workflow filtering.")
    st.caption("Select one or more workflows, or clear the filter.")
    st.stop()

session_df = build_session_summary(chat_df)

# "Real" sessions/turns exclude synthetic missing-id fallback sessions
real_session_mask = ~session_df["session_id"].astype(str).str.startswith("__missing_session__")
real_session_df = session_df[real_session_mask].copy()
real_session_ids = set(real_session_df["session_id"].astype(str))
real_chat_df = chat_df[chat_df["session_id"].astype(str).isin(real_session_ids)].copy()

overall = compute_overall_metrics(real_chat_df, real_session_df)

median_duration = real_session_df["duration_seconds"].median() if not real_session_df.empty else None

# KPI row
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Real Sessions", f"{len(real_session_df):,}", help="Total conversation sessions (excludes synthetic/missing IDs)")
k2.metric("Real Chat Turns", f"{len(real_chat_df):,}", help="Total user messages across all sessions")
k3.metric("Median Turns / Session", f"{overall['median_turns_per_session']:.1f}", help="Middle value of conversation depth (turns per session)")
k4.metric("Median Session Duration", _format_duration(median_duration), help="Middle value of time spent in conversation")
k5.metric("Avg Retrieval Similarity", f"{overall['avg_similarity']:.3f}", help="Average cosine similarity between queries and retrieved chunks (higher = better retrieval quality)")
k6.metric("Avg Latency", f"{overall['avg_latency_ms']:.0f} ms", help="Average response time from query to answer")

# Quick health snapshot for fast triage (30-second read)
turn_count = len(real_chat_df)
slow_count = int((real_chat_df["latency_ms"] > 5000).sum()) if "latency_ms" in real_chat_df else 0
gap_count = int((real_chat_df["chunk_similarity_avg"] < 0.55).sum()) if "chunk_similarity_avg" in real_chat_df else 0
error_count = int((real_chat_df["had_error"] == True).sum()) if "had_error" in real_chat_df else 0

# Generate quick insights
gap_rate = _pct(gap_count, turn_count)
slow_rate = _pct(slow_count, turn_count)
error_rate = _pct(error_count, turn_count)
bounce_rate = overall['bounce_rate_pct']

insights = []
if gap_rate > 20:
    insights.append(f"⚠️ **High knowledge gap rate ({gap_rate}%)** - Consider expanding knowledge base")
elif gap_rate > 10:
    insights.append(f"⚡ Moderate knowledge gap rate ({gap_rate}%) - Some queries lack good retrieval matches")
else:
    insights.append(f"✅ Good retrieval quality ({gap_rate}% gap rate)")

if slow_rate > 10:
    insights.append(f"⚠️ **Many slow responses ({slow_rate}%)** - Check model performance and infrastructure")
elif slow_rate > 5:
    insights.append(f"⚡ Some slow responses ({slow_rate}%)")

if error_rate > 5:
    insights.append(f"🔴 **High error rate ({error_rate}%)** - Investigate error logs immediately")
elif error_rate > 0:
    insights.append(f"⚡ Some errors detected ({error_rate}%)")

if bounce_rate > 60:
    insights.append(f"⚠️ **High bounce rate ({bounce_rate:.1}%)** - Many users leave after 1 turn")
elif bounce_rate > 40:
    insights.append(f"⚡ Moderate bounce rate ({bounce_rate:.1}%)")

if overall['median_turns_per_session'] >= 3:
    insights.append(f"✅ Good engagement (median {overall['median_turns_per_session']:.1f} turns/session)")

if insights:
    with st.expander("📊 Quick Insights", expanded=True):
        for insight in insights:
            st.markdown(insight)

with st.expander("Health snapshot", icon=":material/thumb_up:"):
    h1, h2, h3, h4 = st.columns(4)
    h1.metric("Gap rate", f"{gap_rate}%", help="Turns with retrieval similarity < 0.55 (indicates knowledge base gaps)")
    h2.metric("Slow rate", f"{slow_rate}%", help="Turns with latency > 5000ms (potential performance issues)")
    h3.metric("Error rate", f"{error_rate}%", help="Turns where had_error is true (system failures)")
    h4.metric("Bounce rate", f"{bounce_rate:.1f}%", help="One-turn sessions / all real sessions (user retention indicator)")

st.divider()

# Daily charts (real sessions/turns only)
if not real_session_df.empty:
    daily_sessions = (
        real_session_df.assign(day=real_session_df["session_start"].dt.date)
        .groupby("day", as_index=False)
        .size()
        .rename(columns={"size": "sessions"})
    )
else:
    daily_sessions = pd.DataFrame(columns=["day", "sessions"])

if not real_chat_df.empty:
    daily_turns = (
        real_chat_df.assign(day=real_chat_df["ts"].dt.date)
        .groupby("day", as_index=False)
        .size()
        .rename(columns={"size": "turns"})
    )
else:
    daily_turns = pd.DataFrame(columns=["day", "turns"])

c1, c2 = st.columns(2)
with c1:
    st.markdown("<div class='section-title accent-teal'>Daily sessions</div>", unsafe_allow_html=True)
    st.caption("Unique conversation sessions per day")
    if daily_sessions.empty:
        st.caption("No data")
    else:
        st.line_chart(daily_sessions.set_index("day")["sessions"], height=240, y_label="Sessions", x_label="Date")

with c2:
    st.markdown("<div class='section-title accent-sage'>Daily turns</div>", unsafe_allow_html=True)
    st.caption("Total chat messages (user queries) per day")
    if daily_turns.empty:
        st.caption("No data")
    else:
        st.line_chart(daily_turns.set_index("day")["turns"], height=240, y_label="Turns", x_label="Date")

st.markdown("<div class='section-title accent-amber'>Session depth distribution</div>", unsafe_allow_html=True)
st.caption("Number of sessions by conversation length (turns = back-and-forth exchanges)")
if real_session_df.empty:
    st.caption("No data")
else:
    depth = real_session_df["turns"].value_counts().sort_index().rename_axis("turns").reset_index(name="sessions")
    st.bar_chart(depth.set_index("turns")["sessions"], height=240, y_label="# Sessions", x_label="Turns per session")

st.divider()

left, right = st.columns(2)
with left:
    st.markdown("<div class='section-title'>Top prompts</div>", unsafe_allow_html=True)
    st.caption("Most frequently asked questions")
    top_prompts_df = prompt_frequency(real_chat_df, top_n=20)
    st.dataframe(
        top_prompts_df,
        width='stretch',
        hide_index=True,
        column_config={
            "message": st.column_config.TextColumn("Question", width="large"),
            "count": st.column_config.NumberColumn("Count", width="small"),
        },
    )

    st.markdown("<div class='section-title'>Worst retrieval prompts</div>", unsafe_allow_html=True)
    st.caption("Questions with low similarity scores (< 0.55) indicating knowledge gaps")
    low_sim_df = low_similarity_queries(real_chat_df, threshold=0.55, limit=30)
    if not low_sim_df.empty:
        # Reorder columns: most informative first
        col_order = ["message", "chunk_similarity_avg", "chunk_similarity_max", "workflow", "turn_index", "ts", "session_id"]
        display_cols = [c for c in col_order if c in low_sim_df.columns]
        st.dataframe(
            low_sim_df[display_cols],
            width='stretch',
            hide_index=True,
            column_config={
                "message": st.column_config.TextColumn("Question", width="large"),
                "chunk_similarity_avg": st.column_config.NumberColumn("Avg Sim", format="%.3f", width="small"),
                "chunk_similarity_max": st.column_config.NumberColumn("Max Sim", format="%.3f", width="small"),
                "workflow": st.column_config.TextColumn("Workflow", width="small"),
                "turn_index": st.column_config.NumberColumn("Turn", width="small"),
                "ts": st.column_config.DatetimeColumn("Time", format="MMM D, h:mm a", width="medium"),
                "session_id": st.column_config.TextColumn("Session", width="small"),
            },
        )
    else:
        st.caption("No low similarity queries found")

    st.markdown("<div class='section-title'>Sessions with errors</div>", unsafe_allow_html=True)
    st.caption("Sessions that encountered errors during chat")
    error_sess_df = error_sessions(real_chat_df, real_session_df)
    if not error_sess_df.empty:
        st.dataframe(
            error_sess_df,
            width='stretch',
            hide_index=True,
            column_config={
                "session_id": st.column_config.TextColumn("Session", width="small"),
                "error_turns": st.column_config.NumberColumn("Errors", width="small"),
                "turns": st.column_config.NumberColumn("Total Turns", width="small"),
                "session_start": st.column_config.DatetimeColumn("Started", format="MMM D, h:mm a", width="medium"),
                "session_end": st.column_config.DatetimeColumn("Ended", format="MMM D, h:mm a", width="medium"),
            },
        )
    else:
        st.caption("No error sessions found")

with right:
    st.markdown("<div class='section-title'>Recent questions</div>", unsafe_allow_html=True)
    st.caption("Latest 30 user queries (most recent first)")
    recent_questions = real_chat_df.sort_values("ts", ascending=False).head(30)
    if not recent_questions.empty:
        # Reorder columns: message first, then context
        col_order = ["message", "workflow", "turn_index", "ts", "session_id"]
        display_cols = [c for c in col_order if c in recent_questions.columns]
        st.dataframe(
            recent_questions[display_cols],
            width='stretch',
            hide_index=True,
            column_config={
                "message": st.column_config.TextColumn("Question", width="large"),
                "workflow": st.column_config.TextColumn("Workflow", width="small"),
                "turn_index": st.column_config.NumberColumn("Turn", width="small"),
                "ts": st.column_config.DatetimeColumn("Time", format="MMM D, h:mm a", width="medium"),
                "session_id": st.column_config.TextColumn("Session", width="small"),
            },
        )
    else:
        st.caption("No recent questions")

    st.markdown("<div class='section-title'>Slowest responses</div>", unsafe_allow_html=True)
    st.caption("Queries with response time > 5000ms")
    slow_resp_df = slow_responses(real_chat_df, threshold_ms=5000, limit=30)
    if not slow_resp_df.empty:
        # Reorder columns: message first, then latency
        col_order = ["message", "latency_ms", "model", "workflow", "turn_index", "ts", "session_id"]
        display_cols = [c for c in col_order if c in slow_resp_df.columns]
        st.dataframe(
            slow_resp_df[display_cols],
            width='stretch',
            hide_index=True,
            column_config={
                "message": st.column_config.TextColumn("Question", width="large"),
                "latency_ms": st.column_config.NumberColumn("Latency (ms)", format="%d", width="small"),
                "model": st.column_config.TextColumn("Model", width="small"),
                "workflow": st.column_config.TextColumn("Workflow", width="small"),
                "turn_index": st.column_config.NumberColumn("Turn", width="small"),
                "ts": st.column_config.DatetimeColumn("Time", format="MMM D, h:mm a", width="medium"),
                "session_id": st.column_config.TextColumn("Session", width="small"),
            },
        )
    else:
        st.caption("No slow responses found")

st.markdown("<div class='section-title'>Recent sessions</div>", unsafe_allow_html=True)
st.caption("Most recent 50 conversation sessions with key metrics")
# Future improvement: add session drilldown (click session_id => full turn timeline).
recent_sessions = real_session_df.sort_values("session_start", ascending=False).head(50)
if not recent_sessions.empty:
    # Reorder columns for better readability: ID, duration, quality metrics, timestamps
    col_order = ["session_id", "turns", "duration_seconds", "error_turns", "avg_similarity", "avg_latency_ms", "session_start", "session_end"]
    display_cols = [c for c in col_order if c in recent_sessions.columns]
    st.dataframe(
        recent_sessions[display_cols],
        width='stretch',
        hide_index=True,
        column_config={
            "session_id": st.column_config.TextColumn("Session ID", width="small"),
            "turns": st.column_config.NumberColumn("Turns", width="small"),
            "duration_seconds": st.column_config.NumberColumn("Duration (s)", format="%d", width="small"),
            "error_turns": st.column_config.NumberColumn("Errors", width="small"),
            "avg_similarity": st.column_config.NumberColumn("Avg Similarity", format="%.3f", width="small"),
            "avg_latency_ms": st.column_config.NumberColumn("Avg Latency (ms)", format="%d", width="small"),
            "session_start": st.column_config.DatetimeColumn("Started", format="MMM D, h:mm a", width="medium"),
            "session_end": st.column_config.DatetimeColumn("Ended", format="MMM D, h:mm a", width="medium"),
        },
    )
else:
    st.caption("No recent sessions")



with st.expander("Load metadata"):
    # Future improvement: surface schema coverage (missing-field rates) in a dedicated QA panel.
    st.json(meta)
