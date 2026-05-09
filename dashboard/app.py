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

log_file = Path("latest.json")

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

#st.set_page_config(page_title="Digital Twin Analytics", layout="wide")
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

last_modified = datetime.fromtimestamp(log_file.stat().st_mtime)



st.title("Internal Analytics Dashboard")
st.caption("Focused v1 view of session quality, retrieval quality, and performance.")
st.caption(f"Log file last updated locally: {last_modified}")
st.markdown("<div class='accent-sage' style='margin-top:-0.35rem; margin-bottom:0.55rem;'>Quick scan: quality, engagement, latency, and outliers.</div>", unsafe_allow_html=True)

with st.sidebar:
    st.header("Filters")

    default_log = "query_log.jsonl" if Path("query_log.jsonl").exists() else "scripts/query_log_ORIG.jsonl"
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
k1.metric("Real Sessions", f"{len(real_session_df):,}")
k2.metric("Real Chat Turns", f"{len(real_chat_df):,}")
k3.metric("Median Turns / Session", f"{overall['median_turns_per_session']:.1f}")
k4.metric("Median Session Duration", _format_duration(median_duration))
k5.metric("Avg Retrieval Similarity", f"{overall['avg_similarity']:.3f}")
k6.metric("Avg Latency", f"{overall['avg_latency_ms']:.0f} ms")

# Quick health snapshot for fast triage (30-second read)
turn_count = len(real_chat_df)
slow_count = int((real_chat_df["latency_ms"] > 5000).sum()) if "latency_ms" in real_chat_df else 0
gap_count = int((real_chat_df["chunk_similarity_avg"] < 0.55).sum()) if "chunk_similarity_avg" in real_chat_df else 0
error_count = int((real_chat_df["had_error"] == True).sum()) if "had_error" in real_chat_df else 0

# st#.markdown('<div class="section-card">', unsafe_allow_html=True)
#st.markdown('<div class="section-title">Health snapshot</div>', unsafe_allow_html=True)
with st.expander("Health snapshot", icon=":material/thumb_up:"):
    h1, h2, h3, h4 = st.columns(4)
    h1.metric("Gap rate", f"{_pct(gap_count, turn_count)}%", help="Turns with retrieval similarity < 0.55")
    h2.metric("Slow rate", f"{_pct(slow_count, turn_count)}%", help="Turns with latency > 5000ms")
    h3.metric("Error rate", f"{_pct(error_count, turn_count)}%", help="Turns where had_error is true")
    h4.metric("Bounce rate", f"{overall['bounce_rate_pct']:.1f}%", help="One-turn sessions / all real sessions")
#st.markdown('</div>', unsafe_allow_html=True)

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
    #st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title accent-teal'>Daily sessions</div>", unsafe_allow_html=True)
    if daily_sessions.empty:
        st.caption("No data")
    else:
        st.line_chart(daily_sessions.set_index("day")["sessions"], height=220)
    #st.markdown("</div>", unsafe_allow_html=True)

with c2:
    #st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title accent-sage'>Daily turns</div>", unsafe_allow_html=True)
    if daily_turns.empty:
        st.caption("No data")
    else:
        st.line_chart(daily_turns.set_index("day")["turns"], height=220)
    #st.markdown("</div>", unsafe_allow_html=True)

#st.markdown("<div class='section-card'>", unsafe_allow_html=True)
st.markdown("<div class='section-title accent-amber'>Session depth distribution</div>", unsafe_allow_html=True)
if real_session_df.empty:
    st.caption("No data")
else:
    depth = real_session_df["turns"].value_counts().sort_index().rename_axis("turns").reset_index(name="sessions")
    st.bar_chart(depth.set_index("turns")["sessions"], height=220)
#st.markdown("</div>", unsafe_allow_html=True)

st.divider()

left, right = st.columns(2)
with left:
    st.markdown("<div class='section-title'>Top prompts</div>", unsafe_allow_html=True)
    st.dataframe(prompt_frequency(real_chat_df, top_n=20), use_container_width=True, hide_index=True)

    st.markdown("<div class='section-title'>Worst retrieval prompts</div>", unsafe_allow_html=True)
    st.dataframe(
        low_similarity_queries(real_chat_df, threshold=0.55, limit=30),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("<div class='section-title'>Sessions with errors</div>", unsafe_allow_html=True)
    st.dataframe(error_sessions(real_chat_df, real_session_df), use_container_width=True, hide_index=True)

with right:
    st.markdown("<div class='section-title'>Recent questions</div>", unsafe_allow_html=True)
    recent_questions = real_chat_df.sort_values("ts", ascending=False).head(30)
    st.dataframe(
        recent_questions[[c for c in ["ts", "session_id", "turn_index", "message", "workflow"] if c in recent_questions.columns]],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("<div class='section-title'>Slowest responses</div>", unsafe_allow_html=True)
    st.dataframe(slow_responses(real_chat_df, threshold_ms=5000, limit=30), use_container_width=True, hide_index=True)

st.markdown("<div class='section-title'>Recent sessions</div>", unsafe_allow_html=True)
# Future improvement: add session drilldown (click session_id => full turn timeline).
recent_sessions = real_session_df.sort_values("session_start", ascending=False).head(50)
st.dataframe(recent_sessions, use_container_width=True, hide_index=True)



with st.expander("Load metadata"):
    # Future improvement: surface schema coverage (missing-field rates) in a dedicated QA panel.
    st.json(meta)
