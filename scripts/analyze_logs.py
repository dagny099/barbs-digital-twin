#!/usr/bin/env python3
"""
Query Log Analyzer for Digital Twin
====================================

Analyzes query_log.jsonl to surface knowledge gaps, performance issues,
usage patterns, visitor satisfaction, owner/test traffic, and empty-message
logging artifacts.

Usage:
    python analyze_logs.py
    python analyze_logs.py --cutoff-date 2026-04-10
    python analyze_logs.py --exclude-owner
    python analyze_logs.py --owner-filter row
    python analyze_logs.py --owner-filter session
    python analyze_logs.py --empty-turns
    python analyze_logs.py --votes
    python analyze_logs.py --export summary.json
"""

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, fields
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data classes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class QueryRecord:
    """Parsed query log entry with computed fields."""
    ts: str
    message: str
    project: Optional[str]
    walkthrough: bool
    session_id: Optional[str] = None
    turn_index: Optional[int] = None
    audience_tier: str = "public"
    is_owner_traffic: bool = False
    tool_called: bool = False
    tool_name: Optional[str] = None
    had_error: bool = False
    empty_response: bool = False
    model: str = "unknown"
    temperature: float = 0.0
    n_chunks_retrieved: int = 0
    n_chunks_config: int = 0
    response_chars: int = 0
    latency_ms: int = 0
    workflow: str = "unknown"
    chunk_similarity_avg: float = 0.0
    chunk_similarity_max: float = 0.0
    provider: str = "unknown"
    cost_usd: float = 0.0
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    config_override: bool = False
    assistant_response: Optional[str] = None
    assistant_response_preview: Optional[str] = None

    @property
    def is_knowledge_gap(self) -> bool:
        """Flag queries with weak retrieval quality."""
        return self.chunk_similarity_avg < 0.55

    @property
    def is_slow(self) -> bool:
        """Flag slow queries (>5s)."""
        return self.latency_ms > 5000

    @property
    def is_verbose(self) -> bool:
        """Flag unusually long responses."""
        return self.response_chars > 2000


@dataclass
class VoteRecord:
    """Parsed vote log entry."""
    ts: str
    event: str
    liked: bool
    message_index: int
    session_id: Optional[str] = None
    user_message: Optional[str] = None
    response_snippet: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    cost_usd: Optional[float] = None
    is_owner_traffic: bool = False


def _parse_dataclass(cls, data: dict):
    """Ignore unexpected keys so the analyzer survives schema evolution."""
    allowed_fields = {field.name for field in fields(cls)}
    filtered = {k: v for k, v in data.items() if k in allowed_fields}
    return cls(**filtered)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Analyzer
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class LogAnalyzer:
    """Analyzes query logs and generates insights."""

    def __init__(self, log_path: str = "query_log.jsonl"):
        self.log_path = Path(log_path)
        self.records: List[QueryRecord] = []
        self.votes: List[VoteRecord] = []
        self.empty_or_malformed_turns: List[Dict] = []
        self.owner_filter_summary: Optional[Dict] = None
        self.cutoff_filter_summary: Optional[Dict] = None
        self._load_logs()

    @staticmethod
    def parse_ts(ts_str: str) -> datetime:
        """Parse ISO timestamp, including trailing Z if present."""
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))

    def _load_logs(self):
        """Load and parse JSONL log file, splitting queries, votes, and artifacts."""
        if not self.log_path.exists():
            raise FileNotFoundError(self.log_path)

        legacy_count = 0
        malformed_json_count = 0

        with open(self.log_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                except json.JSONDecodeError as e:
                    malformed_json_count += 1
                    self.empty_or_malformed_turns.append({
                        "line_num": line_num,
                        "ts": None,
                        "session_id": None,
                        "turn_index": None,
                        "is_owner_traffic": False,
                        "reason": f"json_decode_error: {e}",
                    })
                    continue

                is_vote = data.get("event") == "vote"
                message = data.get("message")

                # Track the empty-message/null-row bug as an analytic signal.
                # Do not parse these as QueryRecord because missing required fields
                # can crash dataclass initialization.
                looks_like_empty_or_null_turn = (
                    not is_vote
                    and (
                        not data.get("ts")
                        or message is None
                        or (isinstance(message, str) and not message.strip())
                    )
                )

                if looks_like_empty_or_null_turn:
                    self.empty_or_malformed_turns.append({
                        "line_num": line_num,
                        "ts": data.get("ts"),
                        "session_id": data.get("session_id"),
                        "turn_index": data.get("turn_index"),
                        "is_owner_traffic": bool(data.get("is_owner_traffic", False)),
                        "reason": "missing_ts_or_empty_message",
                    })
                    continue

                try:
                    if is_vote:
                        self.votes.append(_parse_dataclass(VoteRecord, data))
                    else:
                        if "model" not in data:
                            legacy_count += 1
                        self.records.append(_parse_dataclass(QueryRecord, data))
                except TypeError as e:
                    self.empty_or_malformed_turns.append({
                        "line_num": line_num,
                        "ts": data.get("ts"),
                        "session_id": data.get("session_id"),
                        "turn_index": data.get("turn_index"),
                        "is_owner_traffic": bool(data.get("is_owner_traffic", False)),
                        "reason": f"dataclass_parse_error: {e}",
                    })

        print(f"✅ Loaded {len(self.records)} query records, {len(self.votes)} vote records")
        if legacy_count:
            print(f"   ℹ️  {legacy_count} legacy entries (pre-enhanced logging)")
        if malformed_json_count:
            print(f"   ⚠️  {malformed_json_count} malformed JSON entries")
        if self.empty_or_malformed_turns:
            print(f"   🕳️  {len(self.empty_or_malformed_turns)} empty/malformed turn artifact(s)")
        print()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Filtering
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def filter_last_n(self, n: int):
        """Keep only the last N query records."""
        self.records = self.records[-n:]
        print(f"📊 Analyzing last {len(self.records)} queries\n")

    def apply_cutoff_date(self, cutoff_date: str, timezone_str: str = "America/Chicago"):
        """Exclude records before cutoff_date at local midnight in timezone_str."""
        if not cutoff_date:
            return

        tz = ZoneInfo(timezone_str)
        cutoff_dt = datetime.fromisoformat(f"{cutoff_date}T00:00:00").replace(tzinfo=tz)

        def keep_ts(ts: Optional[str]) -> bool:
            if not ts:
                # Keep no-timestamp empty-turn artifacts so the bug remains visible.
                return True
            return self.parse_ts(ts).astimezone(tz) >= cutoff_dt

        original_query_count = len(self.records)
        original_vote_count = len(self.votes)
        original_empty_count = len(self.empty_or_malformed_turns)

        self.records = [r for r in self.records if keep_ts(r.ts)]
        self.votes = [v for v in self.votes if keep_ts(v.ts)]
        self.empty_or_malformed_turns = [
            r for r in self.empty_or_malformed_turns
            if keep_ts(r.get("ts"))
        ]

        self.cutoff_filter_summary = {
            "cutoff_date": cutoff_date,
            "timezone": timezone_str,
            "removed_queries": original_query_count - len(self.records),
            "removed_votes": original_vote_count - len(self.votes),
            "removed_empty_or_malformed": original_empty_count - len(self.empty_or_malformed_turns),
        }

        print(
            f"📅 Applied cutoff date {cutoff_date} ({timezone_str}); "
            f"removed {self.cutoff_filter_summary['removed_queries']} query record(s), "
            f"{self.cutoff_filter_summary['removed_votes']} vote record(s), and "
            f"{self.cutoff_filter_summary['removed_empty_or_malformed']} empty/malformed turn(s)"
        )
        print()

    def exclude_owner_traffic(self, mode: str = "session"):
        """Exclude Barbara-marked traffic.

        Modes:
            row     = drop only rows where is_owner_traffic == True
            session = drop any session containing owner-marked rows
        """
        if mode not in {"row", "session"}:
            raise ValueError("mode must be 'row' or 'session'")

        original_query_count = len(self.records)
        original_vote_count = len(self.votes)

        if mode == "row":
            self.records = [r for r in self.records if not r.is_owner_traffic]
            self.votes = [v for v in self.votes if not v.is_owner_traffic]
            removed_sessions = 0
        else:
            owner_session_ids = {
                record.session_id
                for record in self.records
                if record.is_owner_traffic and record.session_id
            }
            owner_session_ids.update({
                vote.session_id
                for vote in self.votes
                if vote.is_owner_traffic and vote.session_id
            })

            self.records = [
                record
                for record in self.records
                if not record.is_owner_traffic
                and (not record.session_id or record.session_id not in owner_session_ids)
            ]
            self.votes = [
                vote
                for vote in self.votes
                if not vote.is_owner_traffic
                and (not vote.session_id or vote.session_id not in owner_session_ids)
            ]
            removed_sessions = len(owner_session_ids)

        removed_queries = original_query_count - len(self.records)
        removed_votes = original_vote_count - len(self.votes)
        self.owner_filter_summary = {
            "mode": mode,
            "removed_queries": removed_queries,
            "removed_votes": removed_votes,
            "owner_sessions": removed_sessions,
        }

        print(
            f"🚫 Excluded {removed_queries} owner-marked query record(s) "
            f"using owner filter mode '{mode}'"
        )
        if mode == "session":
            print(f"   Removed owner-touched sessions: {removed_sessions}")
        if removed_votes:
            print(f"   Also excluded {removed_votes} vote record(s)")
        print()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Summary
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def summary_stats(self) -> Dict:
        """Compute overall summary statistics."""
        if not self.records:
            return {
                "total_queries": 0,
                "total_votes": len(self.votes),
                "empty_or_malformed_turns": {
                    "total": len(self.empty_or_malformed_turns),
                    "owner_marked": sum(1 for r in self.empty_or_malformed_turns if r.get("is_owner_traffic")),
                },
            }

        latencies = [r.latency_ms for r in self.records]
        similarities = [r.chunk_similarity_avg for r in self.records]
        response_lens = [r.response_chars for r in self.records]

        stats = {
            "total_queries": len(self.records),
            "total_votes": len(self.votes),
            "date_range": {
                "first": self.records[0].ts,
                "last": self.records[-1].ts,
            },
            "latency_ms": {
                "mean": int(statistics.mean(latencies)),
                "median": int(statistics.median(latencies)),
                **(
                    {"p95": int(statistics.quantiles(latencies, n=20)[18])}
                    if len(latencies) >= 20
                    else {"p95_note": f"sample too small ({len(latencies)} rows); use max"}
                ),
                "max": max(latencies),
            },
            "chunk_similarity": {
                "mean": round(statistics.mean(similarities), 3),
                "median": round(statistics.median(similarities), 3),
                "min": round(min(similarities), 3),
            },
            "response_chars": {
                "mean": int(statistics.mean(response_lens)),
                "median": int(statistics.median(response_lens)),
            },
            "flags": {
                "knowledge_gaps": sum(1 for r in self.records if r.is_knowledge_gap),
                "slow_queries": sum(1 for r in self.records if r.is_slow),
                "verbose_queries": sum(1 for r in self.records if r.is_verbose),
                "tool_calls": sum(1 for r in self.records if r.tool_called),
                "errors": sum(1 for r in self.records if r.had_error),
                "zero_retrieval": sum(1 for r in self.records if r.n_chunks_retrieved == 0),
                "empty_responses": sum(1 for r in self.records if r.empty_response),
            },
            "empty_or_malformed_turns": {
                "total": len(self.empty_or_malformed_turns),
                "owner_marked": sum(1 for r in self.empty_or_malformed_turns if r.get("is_owner_traffic")),
            },
        }

        if self.cutoff_filter_summary:
            stats["cutoff_filter"] = self.cutoff_filter_summary

        if self.owner_filter_summary:
            stats["owner_filter"] = self.owner_filter_summary

        if self.votes:
            likes = sum(1 for v in self.votes if v.liked is True)
            dislikes = sum(1 for v in self.votes if v.liked is False)
            stats["votes"] = {
                "total": len(self.votes),
                "likes": likes,
                "dislikes": dislikes,
                "other": len(self.votes) - likes - dislikes,
                "satisfaction_rate": round(100 * likes / (likes + dislikes), 1) if (likes + dislikes) else 0,
            }

        return stats

    def print_summary(self):
        """Print high-level summary statistics."""
        stats = self.summary_stats()
        if not stats or stats.get("total_queries", 0) == 0:
            print("❌ No query data to analyze")
            if self.empty_or_malformed_turns:
                self.print_empty_or_malformed_turns()
            return

        print("╔═══════════════════════════════════════════════════════════╗")
        print("║              QUERY LOG SUMMARY STATISTICS                 ║")
        print("╚═══════════════════════════════════════════════════════════╝\n")

        print(f"📊 Total queries: {stats['total_queries']}")
        print(f"📅 Date range: {stats['date_range']['first'][:10]} → {stats['date_range']['last'][:10]}")

        owner_queries = sum(1 for r in self.records if r.is_owner_traffic)
        if owner_queries:
            print(f"🙋 Owner-marked queries still included: {owner_queries} ({100 * owner_queries / stats['total_queries']:.1f}%)")

        if self.cutoff_filter_summary:
            print(
                f"📅 Cutoff filter: {self.cutoff_filter_summary['cutoff_date']} "
                f"({self.cutoff_filter_summary['timezone']}); removed "
                f"{self.cutoff_filter_summary['removed_queries']} queries"
            )

        if self.owner_filter_summary:
            print(
                f"🚫 Owner filter removed {self.owner_filter_summary['removed_queries']} queries "
                f"using mode '{self.owner_filter_summary['mode']}'"
            )

        if self.empty_or_malformed_turns:
            print(f"🕳️ Empty/malformed chat turns tracked: {len(self.empty_or_malformed_turns)}")

        if "votes" in stats:
            v = stats["votes"]
            print(f"👍 Votes: {v['likes']} likes / {v['dislikes']} dislikes "
                  f"({v['satisfaction_rate']}% satisfaction)")
        print()

        print("⚡ LATENCY")
        lm = stats['latency_ms']
        print(f"   Mean:   {lm['mean']:,}ms")
        print(f"   Median: {lm['median']:,}ms")
        if 'p95' in lm:
            print(f"   P95:    {lm['p95']:,}ms")
        else:
            print(f"   P95:    n/a ({lm.get('p95_note', 'sample too small')})")
        print(f"   Max:    {lm['max']:,}ms\n")

        print("🎯 RETRIEVAL QUALITY (Cosine Similarity)")
        print(f"   Mean:   {stats['chunk_similarity']['mean']:.3f}")
        print(f"   Median: {stats['chunk_similarity']['median']:.3f}")
        print(f"   Min:    {stats['chunk_similarity']['min']:.3f}\n")

        print("📝 RESPONSE LENGTH")
        print(f"   Mean:   {stats['response_chars']['mean']:,} chars")
        print(f"   Median: {stats['response_chars']['median']:,} chars\n")

        print("🚨 FLAGS")
        print(f"   Knowledge gaps: {stats['flags']['knowledge_gaps']} "
              f"({100*stats['flags']['knowledge_gaps']/stats['total_queries']:.1f}%)")
        print(f"   Errors:         {stats['flags']['errors']}\n")
        print(f"   Empty responses: {stats['flags']['empty_responses']} "
              f"({100*stats['flags']['empty_responses']/stats['total_queries']:.1f}%)")
        print(f"   Zero retrieval: {stats['flags']['zero_retrieval']} "
              f"({100*stats['flags']['zero_retrieval']/stats['total_queries']:.1f}%)")
        print(f"   Slow queries:   {stats['flags']['slow_queries']} "
              f"({100*stats['flags']['slow_queries']/stats['total_queries']:.1f}%)")
        print(f"   Verbose queries:{stats['flags']['verbose_queries']} "
              f"({100*stats['flags']['verbose_queries']/stats['total_queries']:.1f}%)")
        print(f"   Tool calls:     {stats['flags']['tool_calls']} "
              f"({100*stats['flags']['tool_calls']/stats['total_queries']:.1f}%)")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Reports
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def print_empty_or_malformed_turns(self, top_n: int = 20):
        """Report empty-message/null-turn logging artifacts."""
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║             EMPTY / MALFORMED TURN ARTIFACTS              ║")
        print("╚═══════════════════════════════════════════════════════════╝\n")

        total = len(self.empty_or_malformed_turns)
        if total == 0:
            print("✅ No empty or malformed chat-turn artifacts detected.\n")
            return

        owner_marked = sum(1 for r in self.empty_or_malformed_turns if r.get("is_owner_traffic"))
        missing_ts = sum(1 for r in self.empty_or_malformed_turns if not r.get("ts"))
        with_session = sum(1 for r in self.empty_or_malformed_turns if r.get("session_id"))

        print(f"Detected:          {total}")
        print(f"Owner-marked:      {owner_marked}")
        print(f"Missing timestamp: {missing_ts}")
        print(f"With session_id:   {with_session}\n")

        print("Recent examples:")
        for row in self.empty_or_malformed_turns[-top_n:]:
            print(
                f"  line={row.get('line_num')} ts={row.get('ts')} "
                f"session={row.get('session_id')} turn={row.get('turn_index')} "
                f"reason={row.get('reason')}"
            )
        print()

    def print_vote_analysis(self):
        """Analyze thumbs up/down patterns."""
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║                  VOTE ANALYSIS                            ║")
        print("╚═══════════════════════════════════════════════════════════╝\n")

        if not self.votes:
            print("   No votes recorded yet.\n")
            return

        likes = [v for v in self.votes if v.liked is True]
        dislikes = [v for v in self.votes if v.liked is False]
        other = [v for v in self.votes if v.liked not in (True, False)]
        rated_total = len(likes) + len(dislikes)

        print(f"👍 Likes:       {len(likes):>4}")
        print(f"👎 Dislikes:    {len(dislikes):>4}")
        print(f"❔ Other/blank: {len(other):>4}")
        if rated_total:
            print(f"   Satisfaction: {100*len(likes)/rated_total:.1f}%")
        print(f"   Total votes:  {len(self.votes)}\n")

        by_model = defaultdict(lambda: {"likes": 0, "dislikes": 0})
        for v in self.votes:
            model = v.model or "unknown"
            if v.liked is True:
                by_model[model]["likes"] += 1
            elif v.liked is False:
                by_model[model]["dislikes"] += 1

        if any(m != "unknown" for m in by_model):
            print("Satisfaction by model:")
            print(f"{'Model':<30} {'Likes':>6} {'Dislikes':>9} {'Rate':>8}")
            print("─" * 60)
            for model in sorted(by_model.keys()):
                d = by_model[model]
                t = d["likes"] + d["dislikes"]
                rate = 100 * d["likes"] / t if t else 0
                print(f"{model:<30} {d['likes']:>6} {d['dislikes']:>9} {rate:>6.1f}%")
            print()

        if dislikes:
            print("👎 Disliked responses (action items):\n")
            for i, v in enumerate(dislikes[:10], 1):
                user_msg = str(v.user_message or "unknown")[:90]
                snippet = str(v.response_snippet or "")[:120]
                print(f"  {i}. User asked: \"{user_msg}\"")
                print(f"     Response: \"{snippet}...\"")
                if v.model:
                    print(f"     Model: {v.model}")
                print()

    def print_knowledge_gaps(self, top_n: int = 20):
        """Identify queries with poor retrieval quality."""
        gaps = [r for r in self.records if r.is_knowledge_gap]
        gaps.sort(key=lambda r: r.chunk_similarity_avg)

        print("╔═══════════════════════════════════════════════════════════╗")
        print("║                    KNOWLEDGE GAPS                         ║")
        print("║  (Low similarity = KB may not know the answer well)       ║")
        print("╚═══════════════════════════════════════════════════════════╝\n")

        if not gaps:
            print("✅ No knowledge gaps detected! (all queries had similarity ≥ 0.55)\n")
            return

        print(f"Found {len(gaps)} queries with weak retrieval (similarity < 0.55)\n")
        for i, r in enumerate(gaps[:top_n], 1):
            tool_marker = " 🔧 TOOL" if r.tool_called else ""
            owner_marker = " 🙋 OWNER" if r.is_owner_traffic else ""
            print(f"{i:2d}. [{r.chunk_similarity_avg:.3f}] {r.message[:80]}{tool_marker}{owner_marker}")
            if r.tool_called:
                print(f"    └─ Tool: {r.tool_name}")
            print(f"    └─ Workflow: {r.workflow}, Retrieved: {r.n_chunks_retrieved} chunks")
            print()

    def print_performance_issues(self, top_n: int = 10):
        """Identify slow queries and outliers."""
        slow = [r for r in self.records if r.is_slow]
        slow.sort(key=lambda r: r.latency_ms, reverse=True)

        print("╔═══════════════════════════════════════════════════════════╗")
        print("║                 PERFORMANCE OUTLIERS                      ║")
        print("╚═══════════════════════════════════════════════════════════╝\n")

        if not slow:
            print("✅ No slow queries detected! (all queries < 5s)\n")
            return

        print(f"Found {len(slow)} slow queries (>5s)\n")
        for i, r in enumerate(slow[:top_n], 1):
            print(f"{i:2d}. [{r.latency_ms/1000:.1f}s] {r.message[:70]}")
            print(f"    └─ Model: {r.model}, Response: {r.response_chars} chars, Workflow: {r.workflow}")
            print()

    def print_response_outliers(self, top_n: int = 10):
        """Show largest responses by character count."""
        verbose = sorted(self.records, key=lambda r: r.response_chars, reverse=True)

        print("╔═══════════════════════════════════════════════════════════╗")
        print("║                 RESPONSE SIZE OUTLIERS                    ║")
        print("╚═══════════════════════════════════════════════════════════╝\n")

        if not verbose:
            print("No response rows found.\n")
            return

        for i, r in enumerate(verbose[:top_n], 1):
            print(f"{i:2d}. [{r.response_chars:,} chars] {r.message[:70]}")
            print(f"    └─ Workflow: {r.workflow}, Project: {r.project}, Model: {r.model}")
            print()

    def print_workflow_breakdown(self):
        """Analyze usage by workflow type."""
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║                  WORKFLOW BREAKDOWN                       ║")
        print("╚═══════════════════════════════════════════════════════════╝\n")

        by_workflow = defaultdict(list)
        for r in self.records:
            by_workflow[r.workflow].append(r)

        if not self.records:
            print("No records.\n")
            return

        print(f"{'Workflow':<20} {'Count':>8} {'%':>6} {'Avg Sim':>8} {'Avg Latency':>12}")
        print("─" * 70)

        total = len(self.records)
        for workflow in sorted(by_workflow.keys()):
            records = by_workflow[workflow]
            count = len(records)
            pct = 100 * count / total
            avg_sim = statistics.mean([r.chunk_similarity_avg for r in records])
            avg_lat = statistics.mean([r.latency_ms for r in records])
            print(f"{workflow:<20} {count:>8} {pct:>5.1f}% {avg_sim:>8.3f} {int(avg_lat):>9,}ms")
        print()

    def print_model_usage(self):
        """Show breakdown by model."""
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║                     MODEL USAGE                           ║")
        print("╚═══════════════════════════════════════════════════════════╝\n")

        by_model = defaultdict(list)
        for r in self.records:
            by_model[r.model].append(r)

        if not self.records:
            print("No records.\n")
            return

        print(f"{'Model':<30} {'Count':>8} {'%':>6} {'Avg Latency':>12} {'Avg Sim':>8}")
        print("─" * 75)

        total = len(self.records)
        for model in sorted(by_model.keys(), key=lambda m: len(by_model[m]), reverse=True):
            records = by_model[model]
            count = len(records)
            pct = 100 * count / total
            avg_lat = statistics.mean([r.latency_ms for r in records])
            avg_sim = statistics.mean([r.chunk_similarity_avg for r in records])
            print(f"{model:<30} {count:>8} {pct:>5.1f}% {int(avg_lat):>9,}ms {avg_sim:>8.3f}")
        print()

    def print_tool_usage(self):
        """Analyze tool calling patterns."""
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║                     TOOL USAGE                            ║")
        print("╚═══════════════════════════════════════════════════════════╝\n")

        tool_calls = [r for r in self.records if r.tool_called]
        if not tool_calls:
            print("✅ No tool calls recorded\n")
            return

        print(f"Total tool calls: {len(tool_calls)} ({100*len(tool_calls)/len(self.records):.1f}% of queries)\n")

        by_tool = Counter([r.tool_name for r in tool_calls])
        print(f"{'Tool':<25} {'Count':>8} {'Avg Similarity':>15}")
        print("─" * 50)

        for tool_name, count in by_tool.most_common():
            tool_records = [r for r in tool_calls if r.tool_name == tool_name]
            avg_sim = statistics.mean([r.chunk_similarity_avg for r in tool_records])
            print(f"{tool_name:<25} {count:>8} {avg_sim:>15.3f}")
        print()

    def print_model_comparison(self):
        """Compare models on quality, cost, and latency."""
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║                   MODEL COMPARISON                        ║")
        print("╚═══════════════════════════════════════════════════════════╝\n")

        by_model = defaultdict(list)
        for r in self.records:
            if r.model != "unknown":
                by_model[r.model].append(r)

        if not by_model:
            print("❌ No model data available\n")
            return

        vote_by_model = defaultdict(lambda: {"likes": 0, "dislikes": 0})
        for v in self.votes:
            model = v.model or "unknown"
            if v.liked is True:
                vote_by_model[model]["likes"] += 1
            elif v.liked is False:
                vote_by_model[model]["dislikes"] += 1

        print(f"{'Model':<30} {'Queries':>8} {'Avg Sim':>8} {'Total $':>10} {'$/Query':>10} {'Latency':>9} {'Satisf':>8}")
        print("─" * 95)

        for model in sorted(by_model.keys(), key=lambda m: len(by_model[m]), reverse=True):
            records = by_model[model]
            count = len(records)
            avg_sim = statistics.mean([r.chunk_similarity_avg for r in records])
            total_cost = sum([r.cost_usd for r in records])
            avg_cost_per_query = total_cost / count if count else 0
            avg_lat = statistics.mean([r.latency_ms for r in records])

            vd = vote_by_model[model]
            vote_total = vd["likes"] + vd["dislikes"]
            sat = f"{100*vd['likes']/vote_total:.0f}%" if vote_total else "—"

            print(f"{model:<30} {count:>8} {avg_sim:>8.3f} ${total_cost:>9.4f} "
                  f"${avg_cost_per_query:>9.5f} {int(avg_lat):>7,}ms {sat:>8}")
        print()

    def print_provider_comparison(self):
        """Compare providers."""
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║                 PROVIDER COMPARISON                       ║")
        print("╚═══════════════════════════════════════════════════════════╝\n")

        by_provider = defaultdict(list)
        for r in self.records:
            if r.provider != "unknown":
                by_provider[r.provider].append(r)

        if not by_provider:
            print("❌ No provider data available\n")
            return

        print(f"{'Provider':<15} {'Models':>7} {'Queries':>8} {'Avg Sim':>8} {'Total $':>10} {'Avg Latency':>12}")
        print("─" * 80)

        for provider in sorted(by_provider.keys()):
            records = by_provider[provider]
            unique_models = len(set(r.model for r in records))
            count = len(records)
            avg_sim = statistics.mean([r.chunk_similarity_avg for r in records])
            total_cost = sum([r.cost_usd for r in records])
            avg_lat = statistics.mean([r.latency_ms for r in records])

            print(f"{provider:<15} {unique_models:>7} {count:>8} {avg_sim:>8.3f} "
                  f"${total_cost:>9.4f} {int(avg_lat):>9,}ms")
        print()

    def print_cost_analysis(self):
        """Analyze cost vs quality."""
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║              COST vs QUALITY ANALYSIS                     ║")
        print("╚═══════════════════════════════════════════════════════════╝\n")

        by_model = defaultdict(list)
        for r in self.records:
            if r.model != "unknown" and r.cost_usd > 0:
                by_model[r.model].append(r)

        if not by_model:
            print("❌ No cost data available\n")
            return

        print(f"{'Model':<30} {'Queries':>8} {'Avg Sim':>8} {'Total $':>10} {'Avg $/Query':>12}")
        print("─" * 80)

        for model, records in sorted(by_model.items(), key=lambda item: len(item[1]), reverse=True):
            count = len(records)
            avg_sim = statistics.mean([r.chunk_similarity_avg for r in records])
            total_cost = sum(r.cost_usd for r in records)
            avg_cost = total_cost / count if count else 0
            print(f"{model:<30} {count:>8} {avg_sim:>8.3f} ${total_cost:>9.4f} ${avg_cost:>11.5f}")
        print()

    def print_config_experiments(self):
        """Analyze temperature and top-k settings."""
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║              CONFIGURATION EXPERIMENTS                    ║")
        print("╚═══════════════════════════════════════════════════════════╝\n")

        by_temp = defaultdict(list)
        for r in self.records:
            if r.temperature > 0:
                temp_bucket = round(r.temperature * 10) / 10
                by_temp[temp_bucket].append(r)

        if by_temp:
            print("Temperature Impact:")
            print(f"{'Temp':>8} {'Queries':>8} {'Avg Sim':>8} {'Avg Latency':>12}")
            print("─" * 45)
            for temp in sorted(by_temp.keys()):
                records = by_temp[temp]
                avg_sim = statistics.mean([r.chunk_similarity_avg for r in records])
                avg_lat = statistics.mean([r.latency_ms for r in records])
                print(f"{temp:>8.1f} {len(records):>8} {avg_sim:>8.3f} {int(avg_lat):>9,}ms")
            print()

        by_topk = defaultdict(list)
        for r in self.records:
            if r.n_chunks_config > 0:
                by_topk[r.n_chunks_config].append(r)

        if by_topk:
            print("Top-K Impact:")
            print(f"{'Top-K':>8} {'Queries':>8} {'Avg Sim':>8} {'Avg Latency':>12}")
            print("─" * 45)
            for k in sorted(by_topk.keys()):
                records = by_topk[k]
                avg_sim = statistics.mean([r.chunk_similarity_avg for r in records])
                avg_lat = statistics.mean([r.latency_ms for r in records])
                print(f"{k:>8} {len(records):>8} {avg_sim:>8.3f} {int(avg_lat):>9,}ms")
            print()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Export
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def export_summary(self, output_path: str):
        """Export summary statistics to JSON."""
        stats = self.summary_stats()

        stats["workflows"] = {}
        by_workflow = defaultdict(list)
        for r in self.records:
            by_workflow[r.workflow].append(r)

        for workflow, records in by_workflow.items():
            stats["workflows"][workflow] = {
                "count": len(records),
                "avg_similarity": round(statistics.mean([r.chunk_similarity_avg for r in records]), 3),
                "avg_latency_ms": int(statistics.mean([r.latency_ms for r in records])),
            }

        stats["models"] = {}
        by_model = defaultdict(list)
        for r in self.records:
            by_model[r.model].append(r)

        for model, records in by_model.items():
            stats["models"][model] = {
                "count": len(records),
                "avg_latency_ms": int(statistics.mean([r.latency_ms for r in records])),
                "avg_similarity": round(statistics.mean([r.chunk_similarity_avg for r in records]), 3),
                "total_cost_usd": round(sum(r.cost_usd for r in records), 6),
            }

        gaps = [r for r in self.records if r.is_knowledge_gap]
        stats["knowledge_gaps"] = [
            {
                "message": r.message,
                "similarity": r.chunk_similarity_avg,
                "tool_called": r.tool_called,
                "tool_name": r.tool_name,
                "is_owner_traffic": r.is_owner_traffic,
            }
            for r in sorted(gaps, key=lambda r: r.chunk_similarity_avg)[:20]
        ]

        stats["empty_or_malformed_turn_examples"] = self.empty_or_malformed_turns[-20:]

        if self.votes:
            stats["disliked_responses"] = [
                {
                    "user_message": v.user_message,
                    "response_snippet": v.response_snippet,
                    "model": v.model,
                    "ts": v.ts,
                    "is_owner_traffic": v.is_owner_traffic,
                }
                for v in self.votes if v.liked is False
            ]

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)

        print(f"✅ Exported summary to {output_path}\n")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Report bundles
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def admin_report(self):
        """Print admin-specific comprehensive analysis."""
        self.print_summary()
        print()
        self.print_vote_analysis()
        print()
        self.print_empty_or_malformed_turns()
        print()
        self.print_model_comparison()
        print()
        self.print_cost_analysis()
        print()
        self.print_provider_comparison()
        print()
        self.print_config_experiments()
        print()
        self.print_workflow_breakdown()
        print()
        self.print_tool_usage()
        print()
        self.print_knowledge_gaps(top_n=10)
        print()
        self.print_performance_issues(top_n=5)
        print()
        self.print_response_outliers(top_n=5)

    def full_report(self):
        """Print comprehensive analysis."""
        self.print_summary()
        print()
        self.print_vote_analysis()
        print()
        self.print_empty_or_malformed_turns()
        print()
        self.print_workflow_breakdown()
        print()
        self.print_model_usage()
        print()
        self.print_tool_usage()
        print()
        self.print_knowledge_gaps()
        print()
        self.print_performance_issues()
        print()
        self.print_response_outliers(top_n=5)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _validated_date(date_str: str) -> str:
    """Exit with a clear message if date_str is not strictly YYYY-MM-DD."""
    try:
        parsed = datetime.strptime(date_str, "%Y-%m-%d")
        if parsed.strftime("%Y-%m-%d") != date_str:
            raise ValueError
    except ValueError:
        sys.exit(f"❌ Invalid --cutoff-date '{date_str}'. Expected format: YYYY-MM-DD")
    return date_str


def main():
    parser = argparse.ArgumentParser(
        description="Analyze query logs from Digital Twin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python analyze_logs.py
  python analyze_logs.py --cutoff-date 2026-04-10
  python analyze_logs.py --exclude-owner
  python analyze_logs.py --owner-filter row
  python analyze_logs.py --owner-filter session
  python analyze_logs.py --knowledge-gaps
  python analyze_logs.py --empty-turns
  python analyze_logs.py --votes
  python analyze_logs.py --export summary.json

Admin:
  python analyze_logs.py --admin --cutoff-date 2026-04-10 --exclude-owner
  python analyze_logs.py --compare-models
  python analyze_logs.py --cost-analysis
  python analyze_logs.py --compare-providers
        """,
    )
    parser.add_argument("--log", default="query_log.jsonl", help="Path to JSONL log file")
    parser.add_argument("--cutoff-date", metavar="YYYY-MM-DD", help="Exclude rows before this local date")
    parser.add_argument("--timezone", default="America/Chicago", help="Timezone for --cutoff-date")
    parser.add_argument("--exclude-owner", action="store_true", help="Exclude Barbara-marked owner traffic")
    parser.add_argument(
        "--owner-filter",
        choices=["row", "session"],
        default="session",
        help="Owner traffic mode used with --exclude-owner. Default: session",
    )
    parser.add_argument("--last", type=int, metavar="N", help="Analyze only last N query records")
    parser.add_argument("--export", metavar="FILE", help="Export summary to JSON")
    parser.add_argument("--knowledge-gaps", action="store_true", help="Show only knowledge gaps")
    parser.add_argument("--performance", action="store_true", help="Show only performance issues")
    parser.add_argument("--votes", action="store_true", help="Show vote / satisfaction analysis")
    parser.add_argument("--empty-turns", action="store_true", help="Show empty/malformed turn artifacts")
    parser.add_argument("--response-outliers", action="store_true", help="Show largest responses")
    parser.add_argument("--admin", action="store_true", help="Admin mode: full report with model/cost analysis")
    parser.add_argument("--compare-models", action="store_true", help="Compare models on quality, cost, latency")
    parser.add_argument("--cost-analysis", action="store_true", help="Cost vs quality analysis")
    parser.add_argument("--compare-providers", action="store_true", help="Compare providers")
    parser.add_argument("--config-experiments", action="store_true", help="Analyze temperature/top-k experiments")

    args = parser.parse_args()

    if args.cutoff_date:
        _validated_date(args.cutoff_date)

    try:
        analyzer = LogAnalyzer(args.log)
    except FileNotFoundError as e:
        print(f"❌ Log file not found: {e}")
        print("   Run the app first to generate logs.")
        sys.exit(1)

    if args.cutoff_date:
        analyzer.apply_cutoff_date(args.cutoff_date, args.timezone)

    if args.exclude_owner:
        print(f"ℹ️  Owner filter active: mode='{args.owner_filter}'")
        analyzer.exclude_owner_traffic(mode=args.owner_filter)

    if args.last:
        analyzer.filter_last_n(args.last)

    if args.export:
        analyzer.export_summary(args.export)
    elif args.admin:
        analyzer.admin_report()
    elif args.votes:
        analyzer.print_vote_analysis()
    elif args.empty_turns:
        analyzer.print_empty_or_malformed_turns()
    elif args.response_outliers:
        analyzer.print_response_outliers()
    elif args.compare_models:
        analyzer.print_model_comparison()
    elif args.cost_analysis:
        analyzer.print_cost_analysis()
    elif args.compare_providers:
        analyzer.print_provider_comparison()
    elif args.config_experiments:
        analyzer.print_config_experiments()
    elif args.knowledge_gaps:
        analyzer.print_knowledge_gaps()
    elif args.performance:
        analyzer.print_performance_issues()
    else:
        analyzer.full_report()


if __name__ == "__main__":
    main()
