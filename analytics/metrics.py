"""Reusable analytics metrics computed from normalized chat/session data."""

from __future__ import annotations

import pandas as pd


def compute_overall_metrics(chat_df: pd.DataFrame, session_df: pd.DataFrame | None = None) -> dict:
    """Compute top-level KPI dictionary for dashboard cards."""
    if session_df is None:
        from .sessionize import build_session_summary

        session_df = build_session_summary(chat_df)

    total_turns = int(len(chat_df))
    total_sessions = int(len(session_df))
    one_turn_sessions = int((session_df["turns"] == 1).sum()) if total_sessions else 0

    # Votes live in a separate dataframe and are intentionally excluded here.

    metrics = {
        "total_chat_turns": total_turns,
        "total_sessions": total_sessions,
        "avg_turns_per_session": round(total_turns / total_sessions, 2) if total_sessions else 0.0,
        "median_turns_per_session": float(session_df["turns"].median()) if total_sessions else 0.0,
        "one_turn_sessions": one_turn_sessions,
        "bounce_rate_pct": round((one_turn_sessions / total_sessions) * 100, 1) if total_sessions else 0.0,
        "had_error_turns": int((chat_df.get("had_error") == True).sum()) if "had_error" in chat_df else 0,
        "empty_response_turns": int((chat_df.get("empty_response") == True).sum()) if "empty_response" in chat_df else 0,
        "avg_latency_ms": round(float(chat_df["latency_ms"].mean()), 2) if "latency_ms" in chat_df and total_turns else 0.0,
        "p95_latency_ms": round(float(chat_df["latency_ms"].quantile(0.95)), 2) if "latency_ms" in chat_df and total_turns else 0.0,
        "avg_similarity": round(float(chat_df["chunk_similarity_avg"].mean()), 3) if "chunk_similarity_avg" in chat_df and total_turns else 0.0,
        "knowledge_gap_rate_pct": round(float((chat_df["chunk_similarity_avg"] < 0.55).mean() * 100), 1)
        if "chunk_similarity_avg" in chat_df and total_turns
        else 0.0,
        "total_cost_usd": round(float(chat_df["cost_usd"].fillna(0).sum()), 6) if "cost_usd" in chat_df else 0.0,
    }
    return metrics


def session_summaries(session_df: pd.DataFrame, limit: int = 100) -> pd.DataFrame:
    """Return recent session summary rows."""
    if session_df.empty:
        return session_df
    return session_df.sort_values("session_start", ascending=False).head(limit).reset_index(drop=True)


def prompt_frequency(chat_df: pd.DataFrame, top_n: int = 20, min_len: int = 1) -> pd.DataFrame:
    """Return most frequent normalized prompts."""
    if chat_df.empty:
        return pd.DataFrame(columns=["message", "count"])

    msg = chat_df["message"].fillna("").astype(str).str.strip().str.lower()
    msg = msg[msg.str.len() >= min_len]
    out = msg.value_counts().head(top_n).rename_axis("message").reset_index(name="count")
    return out


def low_similarity_queries(chat_df: pd.DataFrame, threshold: float = 0.55, limit: int = 100) -> pd.DataFrame:
    """Return low similarity turns sorted by weakest retrieval first."""
    if chat_df.empty or "chunk_similarity_avg" not in chat_df:
        return pd.DataFrame(columns=["ts", "session_id", "turn_index", "message", "chunk_similarity_avg"])

    cols = [c for c in ["ts", "session_id", "turn_index", "message", "workflow", "chunk_similarity_avg", "chunk_similarity_max"] if c in chat_df.columns]
    out = chat_df[chat_df["chunk_similarity_avg"] < threshold][cols].sort_values("chunk_similarity_avg", ascending=True)
    return out.head(limit).reset_index(drop=True)


def slow_responses(chat_df: pd.DataFrame, threshold_ms: int = 5000, limit: int = 100) -> pd.DataFrame:
    """Return slow response turns sorted by longest latency."""
    if chat_df.empty or "latency_ms" not in chat_df:
        return pd.DataFrame(columns=["ts", "session_id", "turn_index", "message", "latency_ms"])

    cols = [c for c in ["ts", "session_id", "turn_index", "message", "workflow", "model", "latency_ms"] if c in chat_df.columns]
    out = chat_df[chat_df["latency_ms"] > threshold_ms][cols].sort_values("latency_ms", ascending=False)
    return out.head(limit).reset_index(drop=True)


def error_sessions(chat_df: pd.DataFrame, session_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Return sessions containing one or more error turns."""
    if chat_df.empty:
        return pd.DataFrame(columns=["session_id", "error_turns", "turns", "session_start", "session_end"])

    if session_df is None:
        from .sessionize import build_session_summary

        session_df = build_session_summary(chat_df)

    out = session_df[session_df["error_turns"] > 0].copy()
    return out.sort_values(["error_turns", "turns"], ascending=[False, False]).reset_index(drop=True)
