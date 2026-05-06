"""Log loading and normalization utilities for query_log.jsonl."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pandas as pd


CHAT_COLUMNS = [
    "ts",
    "session_id",
    "turn_index",
    "message",
    "assistant_response_preview",
    "project",
    "walkthrough",
    "audience_tier",
    "is_owner_traffic",
    "tool_called",
    "tool_name",
    "had_error",
    "empty_response",
    "model",
    "temperature",
    "n_chunks_retrieved",
    "n_chunks_config",
    "response_chars",
    "latency_ms",
    "workflow",
    "chunk_similarity_avg",
    "chunk_similarity_max",
    "provider",
    "cost_usd",
    "prompt_tokens",
    "completion_tokens",
]

BOOL_COLUMNS = [
    "walkthrough",
    "is_owner_traffic",
    "tool_called",
    "had_error",
    "empty_response",
]

NUMERIC_COLUMNS = [
    "turn_index",
    "temperature",
    "n_chunks_retrieved",
    "n_chunks_config",
    "response_chars",
    "latency_ms",
    "chunk_similarity_avg",
    "chunk_similarity_max",
    "cost_usd",
    "prompt_tokens",
    "completion_tokens",
]


def _parse_jsonl(path: Path) -> tuple[list[dict], int]:
    """Parse JSONL rows; skip malformed lines and return skipped count."""
    rows: list[dict] = []
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
    return rows, malformed


def _normalize_bool(series: pd.Series) -> pd.Series:
    """Normalize loose boolean-like values into pandas nullable boolean dtype."""
    mapping = {
        "true": True,
        "false": False,
        "1": True,
        "0": False,
        "yes": True,
        "no": False,
        "y": True,
        "n": False,
    }

    def to_bool(value):
        if pd.isna(value):
            return pd.NA
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            if value == 1:
                return True
            if value == 0:
                return False
            return pd.NA
        if isinstance(value, str):
            return mapping.get(value.strip().lower(), pd.NA)
        return pd.NA

    return series.map(to_bool).astype("boolean")


def load_query_log(
    log_path: str = "query_log.jsonl",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    owner_filter: str = "none",
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Load and normalize query log rows.

    Returns a tuple of (chat_df, vote_df, metadata).

    - Parses timestamps safely (`errors="coerce"`).
    - Keeps only modern chat schema columns (extras are ignored).
    - Handles missing values with nullable pandas dtypes.
    - Supports optional date filtering and owner-traffic filtering.

    owner_filter options:
      - "none": keep all rows
      - "row": drop rows where is_owner_traffic is true
      - "session": drop any session with owner-marked traffic
    """
    path = Path(log_path)
    if not path.exists():
        raise FileNotFoundError(path)

    rows, malformed_rows = _parse_jsonl(path)
    if not rows:
        empty_chat = pd.DataFrame(columns=CHAT_COLUMNS)
        empty_vote = pd.DataFrame(columns=["ts", "event", "session_id", "liked", "is_owner_traffic"])
        return empty_chat, empty_vote, {"malformed_rows": malformed_rows, "total_rows": 0}

    raw_df = pd.DataFrame(rows)

    vote_df = raw_df[raw_df.get("event").eq("vote")].copy() if "event" in raw_df.columns else pd.DataFrame()
    chat_df = raw_df[~raw_df.get("event").eq("vote")].copy() if "event" in raw_df.columns else raw_df.copy()

    for col in CHAT_COLUMNS:
        if col not in chat_df.columns:
            chat_df[col] = pd.NA
    chat_df = chat_df[CHAT_COLUMNS].copy()

    # Safe timestamp parsing
    chat_df["ts"] = pd.to_datetime(chat_df["ts"], errors="coerce", utc=True)
    if not vote_df.empty:
        vote_df["ts"] = pd.to_datetime(vote_df.get("ts"), errors="coerce", utc=True)

    # Normalize booleans and numerics
    for col in BOOL_COLUMNS:
        chat_df[col] = _normalize_bool(chat_df[col])
    if not vote_df.empty and "is_owner_traffic" in vote_df.columns:
        vote_df["is_owner_traffic"] = _normalize_bool(vote_df["is_owner_traffic"])

    for col in NUMERIC_COLUMNS:
        chat_df[col] = pd.to_numeric(chat_df[col], errors="coerce")

    # Basic text cleanup
    chat_df["message"] = chat_df["message"].fillna("").astype(str).str.strip()
    chat_df["session_id"] = chat_df["session_id"].fillna("").astype(str).str.strip()

    # Date filtering (inclusive), based on UTC timestamps
    if start_date:
        start_ts = pd.to_datetime(start_date, errors="coerce", utc=True)
        if pd.notna(start_ts):
            chat_df = chat_df[chat_df["ts"].isna() | (chat_df["ts"] >= start_ts)]
            if not vote_df.empty:
                vote_df = vote_df[vote_df["ts"].isna() | (vote_df["ts"] >= start_ts)]
    if end_date:
        end_ts = pd.to_datetime(end_date, errors="coerce", utc=True)
        if pd.notna(end_ts):
            end_ts = end_ts + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
            chat_df = chat_df[chat_df["ts"].isna() | (chat_df["ts"] <= end_ts)]
            if not vote_df.empty:
                vote_df = vote_df[vote_df["ts"].isna() | (vote_df["ts"] <= end_ts)]

    # Owner filtering
    if owner_filter not in {"none", "row", "session"}:
        raise ValueError("owner_filter must be one of: none, row, session")

    if owner_filter == "row":
        chat_df = chat_df[chat_df["is_owner_traffic"] != True]
        if not vote_df.empty and "is_owner_traffic" in vote_df.columns:
            vote_df = vote_df[vote_df["is_owner_traffic"] != True]

    if owner_filter == "session":
        owner_sessions = set(chat_df.loc[chat_df["is_owner_traffic"] == True, "session_id"].dropna())
        owner_sessions.discard("")

        if not vote_df.empty and "is_owner_traffic" in vote_df.columns and "session_id" in vote_df.columns:
            vote_sessions = set(vote_df.loc[vote_df["is_owner_traffic"] == True, "session_id"].dropna())
            owner_sessions.update(s for s in vote_sessions if isinstance(s, str) and s.strip())

        chat_df = chat_df[(chat_df["is_owner_traffic"] != True) & (~chat_df["session_id"].isin(owner_sessions))]
        if not vote_df.empty and "session_id" in vote_df.columns:
            if "is_owner_traffic" in vote_df.columns:
                vote_df = vote_df[(vote_df["is_owner_traffic"] != True) & (~vote_df["session_id"].isin(owner_sessions))]
            else:
                vote_df = vote_df[~vote_df["session_id"].isin(owner_sessions)]

    meta = {
        "malformed_rows": malformed_rows,
        "total_rows": len(raw_df),
        "chat_rows": len(chat_df),
        "vote_rows": len(vote_df),
        "owner_filter": owner_filter,
        "start_date": start_date,
        "end_date": end_date,
    }

    return chat_df.reset_index(drop=True), vote_df.reset_index(drop=True), meta
