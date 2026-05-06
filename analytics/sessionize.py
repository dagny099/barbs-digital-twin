"""Session reconstruction helpers."""

from __future__ import annotations

import pandas as pd


def build_session_summary(chat_df: pd.DataFrame) -> pd.DataFrame:
    """Build one row per reconstructed session.

    Best-effort fallback when session IDs are missing/inconsistent:
    - Rows with empty session_id are grouped under synthetic IDs: "__missing_session__:<row_index>".
    - This preserves rows for analysis instead of dropping them, but these synthetic
      sessions should not be interpreted as true user sessions.
    """
    if chat_df.empty:
        return pd.DataFrame(
            columns=[
                "session_id",
                "session_start",
                "session_end",
                "turns",
                "duration_seconds",
                "avg_latency_ms",
                "avg_similarity",
                "total_cost_usd",
                "error_turns",
                "first_message",
                "last_message",
            ]
        )

    work = chat_df.copy()
    work["session_key"] = work["session_id"]
    missing_mask = work["session_key"].isna() | (work["session_key"].astype(str).str.strip() == "")
    work.loc[missing_mask, "session_key"] = work.index[missing_mask].map(lambda i: f"__missing_session__:{i}")

    work = work.sort_values(["session_key", "ts", "turn_index"], na_position="last")

    grouped = work.groupby("session_key", dropna=False)
    session_df = grouped.agg(
        session_start=("ts", "min"),
        session_end=("ts", "max"),
        turns=("message", "count"),
        avg_latency_ms=("latency_ms", "mean"),
        avg_similarity=("chunk_similarity_avg", "mean"),
        total_cost_usd=("cost_usd", "sum"),
        error_turns=("had_error", lambda s: (s == True).sum()),
        first_message=("message", "first"),
        last_message=("message", "last"),
    ).reset_index().rename(columns={"session_key": "session_id"})

    session_df["duration_seconds"] = (
        session_df["session_end"] - session_df["session_start"]
    ).dt.total_seconds()

    return session_df.sort_values("session_start", na_position="last").reset_index(drop=True)
