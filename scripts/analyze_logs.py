#!/usr/bin/env python3
"""
Query Log Analyzer for Digital Twin
====================================
Analyzes query_log.jsonl to surface knowledge gaps, performance issues,
usage patterns, and visitor satisfaction (thumbs up/down).

Usage:
    python analyze_logs.py                    # Full report
    python analyze_logs.py --knowledge-gaps   # Only show knowledge gaps
    python analyze_logs.py --exclude-owner    # Ignore Barbara's own sessions
    python analyze_logs.py --last 100         # Analyze last N queries
    python analyze_logs.py --votes            # Vote / satisfaction analysis
    python analyze_logs.py --export summary.json  # Export to JSON
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import Counter, defaultdict
from dataclasses import dataclass, fields
from typing import List, Dict, Optional
import statistics


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
    # New fields (optional for backward compatibility)
    model: str = "unknown"
    temperature: float = 0.0
    n_chunks_retrieved: int = 0
    n_chunks_config: int = 0
    response_chars: int = 0
    latency_ms: int = 0
    workflow: str = "unknown"
    chunk_similarity_avg: float = 0.0
    chunk_similarity_max: float = 0.0
    # Admin-specific fields (optional)
    provider: str = "unknown"
    cost_usd: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    config_override: bool = False

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
    """Parsed vote log entry (thumbs up/down from visitors)."""
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


class LogAnalyzer:
    """Analyzes query logs and generates insights."""

    def __init__(self, log_path: str = "query_log.jsonl"):
        self.log_path = Path(log_path)
        self.records: List[QueryRecord] = []
        self.votes: List[VoteRecord] = []
        self.owner_filter_summary: Optional[Dict] = None
        self._load_logs()

    def _load_logs(self):
        """Load and parse JSONL log file, splitting queries from votes."""
        if not self.log_path.exists():
            print(f"❌ Log file not found: {self.log_path}")
            print("   Run the app first to generate logs.")
            sys.exit(1)

        legacy_count = 0
        skipped = 0
        with open(self.log_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)

                    # Route by record type
                    if data.get("event") == "vote":
                        self.votes.append(_parse_dataclass(VoteRecord, data))
                    else:
                        if 'model' not in data:
                            legacy_count += 1
                        self.records.append(_parse_dataclass(QueryRecord, data))

                except (json.JSONDecodeError, TypeError) as e:
                    skipped += 1
                    print(f"⚠️  Skipping malformed entry at line {line_num}: {e}")

        print(f"✅ Loaded {len(self.records)} query records, {len(self.votes)} vote records")
        if legacy_count:
            print(f"   ℹ️  {legacy_count} legacy entries (pre-enhanced logging)")
        if skipped:
            print(f"   ⚠️  {skipped} entries skipped (malformed)")
        print()

    def filter_last_n(self, n: int):
        """Keep only the last N query records."""
        self.records = self.records[-n:]
        print(f"📊 Analyzing last {len(self.records)} queries\n")

    def exclude_owner_traffic(self):
        """Exclude Barbara-marked traffic, expanding to the whole session when possible."""
        owner_session_ids = {
            record.session_id
            for record in self.records
            if record.is_owner_traffic and record.session_id
        }

        original_query_count = len(self.records)
        original_vote_count = len(self.votes)

        self.records = [
            record
            for record in self.records
            if not record.is_owner_traffic and record.session_id not in owner_session_ids
        ]
        self.votes = [
            vote
            for vote in self.votes
            if not vote.is_owner_traffic and vote.session_id not in owner_session_ids
        ]

        removed_queries = original_query_count - len(self.records)
        removed_votes = original_vote_count - len(self.votes)
        self.owner_filter_summary = {
            "removed_queries": removed_queries,
            "removed_votes": removed_votes,
            "owner_sessions": len(owner_session_ids),
        }

        print(
            f"🚫 Excluded {removed_queries} owner-marked queries "
            f"across {len(owner_session_ids)} session(s)"
        )
        if removed_votes:
            print(f"   Also excluded {removed_votes} vote record(s)")
        print()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ANALYSIS REPORTS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def summary_stats(self) -> Dict:
        """Compute overall summary statistics."""
        if not self.records:
            return {}

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
                "p95": int(statistics.quantiles(latencies, n=20)[18]) if len(latencies) > 20 else max(latencies),
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
                "tool_calls": sum(1 for r in self.records if r.tool_called),
                "errors": sum(1 for r in self.records if r.had_error),
            },
        }

        # Add vote summary if votes exist
        if self.votes:
            likes = sum(1 for v in self.votes if v.liked)
            dislikes = len(self.votes) - likes
            stats["votes"] = {
                "total": len(self.votes),
                "likes": likes,
                "dislikes": dislikes,
                "satisfaction_rate": round(100 * likes / len(self.votes), 1) if self.votes else 0,
            }

        return stats

    def print_summary(self):
        """Print high-level summary statistics."""
        stats = self.summary_stats()
        if not stats:
            print("❌ No data to analyze")
            return

        print("╔═══════════════════════════════════════════════════════════╗")
        print("║              QUERY LOG SUMMARY STATISTICS                 ║")
        print("╚═══════════════════════════════════════════════════════════╝\n")

        print(f"📊 Total queries: {stats['total_queries']}")
        print(f"📅 Date range: {stats['date_range']['first'][:10]} → {stats['date_range']['last'][:10]}")
        owner_queries = sum(1 for r in self.records if r.is_owner_traffic)
        if owner_queries:
            print(f"🙋 Owner-marked queries: {owner_queries} ({100 * owner_queries / stats['total_queries']:.1f}%)")
        if "votes" in stats:
            v = stats["votes"]
            print(f"👍 Votes: {v['likes']} likes / {v['dislikes']} dislikes "
                  f"({v['satisfaction_rate']}% satisfaction)")
        if self.owner_filter_summary:
            print(
                f"🚫 Owner filter removed {self.owner_filter_summary['removed_queries']} queries "
                f"across {self.owner_filter_summary['owner_sessions']} session(s)"
            )
        print()

        print("⚡ LATENCY")
        print(f"   Mean:   {stats['latency_ms']['mean']:,}ms")
        print(f"   Median: {stats['latency_ms']['median']:,}ms")
        print(f"   P95:    {stats['latency_ms']['p95']:,}ms")
        print(f"   Max:    {stats['latency_ms']['max']:,}ms\n")

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
        print(f"   Slow queries:   {stats['flags']['slow_queries']} "
              f"({100*stats['flags']['slow_queries']/stats['total_queries']:.1f}%)")
        print(f"   Tool calls:     {stats['flags']['tool_calls']} "
              f"({100*stats['flags']['tool_calls']/stats['total_queries']:.1f}%)")
        print(f"   Errors:         {stats['flags']['errors']}\n")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # VOTE ANALYSIS (new)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def print_vote_analysis(self):
        """Analyze thumbs up/down patterns."""
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║                  VOTE ANALYSIS                            ║")
        print("╚═══════════════════════════════════════════════════════════╝\n")

        if not self.votes:
            print("   No votes recorded yet.\n")
            return

        likes = [v for v in self.votes if v.liked]
        dislikes = [v for v in self.votes if not v.liked]
        total = len(self.votes)

        print(f"👍 Likes:    {len(likes):>4}  ({100*len(likes)/total:.1f}%)")
        print(f"👎 Dislikes: {len(dislikes):>4}  ({100*len(dislikes)/total:.1f}%)")
        print(f"   Total:    {total:>4}\n")

        # Satisfaction by model
        by_model = defaultdict(lambda: {"likes": 0, "dislikes": 0})
        for v in self.votes:
            model = v.model or "unknown"
            if v.liked:
                by_model[model]["likes"] += 1
            else:
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

        # Show disliked responses (most actionable)
        if dislikes:
            print("👎 Disliked responses (action items):\n")
            for i, v in enumerate(dislikes[:10], 1):
                user_msg = (v.user_message or "unknown")[:70]
                snippet = (v.response_snippet or "")[:100]
                print(f"  {i}. User asked: \"{user_msg}\"")
                print(f"     Response: \"{snippet}...\"")
                if v.model:
                    print(f"     Model: {v.model}")
                print()

        # Show liked responses (what's working)
        if likes and len(likes) <= 20:
            print("👍 Liked responses (what's working):\n")
            for i, v in enumerate(likes[:5], 1):
                user_msg = (v.user_message or "unknown")[:70]
                print(f"  {i}. \"{user_msg}\"")
            print()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # EXISTING REPORTS (unchanged)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def print_knowledge_gaps(self, top_n: int = 20):
        """Identify queries with poor retrieval quality."""
        gaps = [r for r in self.records if r.is_knowledge_gap]
        gaps.sort(key=lambda r: r.chunk_similarity_avg)

        print("╔═══════════════════════════════════════════════════════════╗")
        print("║                    KNOWLEDGE GAPS                         ║")
        print("║  (Low similarity = KB doesn't know the answer well)       ║")
        print("╚═══════════════════════════════════════════════════════════╝\n")

        if not gaps:
            print("✅ No knowledge gaps detected! (all queries had similarity ≥ 0.55)\n")
            return

        print(f"Found {len(gaps)} queries with weak retrieval (similarity < 0.55)\n")
        print("Top issues to address:\n")

        for i, r in enumerate(gaps[:top_n], 1):
            tool_marker = " 🔧 TOOL" if r.tool_called else ""
            print(f"{i:2d}. [{r.chunk_similarity_avg:.3f}] {r.message[:70]}{tool_marker}")
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
            print(f"{i:2d}. [{r.latency_ms/1000:.1f}s] {r.message[:60]}")
            print(f"    └─ Model: {r.model}, Response: {r.response_chars} chars")
            print()

    def print_workflow_breakdown(self):
        """Analyze usage by workflow type."""
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║                  WORKFLOW BREAKDOWN                       ║")
        print("╚═══════════════════════════════════════════════════════════╝\n")

        by_workflow = defaultdict(list)
        for r in self.records:
            by_workflow[r.workflow].append(r)

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

        print(f"{'Model':<25} {'Count':>8} {'%':>6} {'Avg Latency':>12}")
        print("─" * 60)

        total = len(self.records)
        for model in sorted(by_model.keys(), key=lambda m: len(by_model[m]), reverse=True):
            records = by_model[model]
            count = len(records)
            pct = 100 * count / total
            avg_lat = statistics.mean([r.latency_ms for r in records])

            print(f"{model:<25} {count:>8} {pct:>5.1f}% {int(avg_lat):>9,}ms")
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
        print("💡 Low similarity + tool call = knowledge gap to address\n")

    def export_summary(self, output_path: str):
        """Export summary statistics to JSON."""
        stats = self.summary_stats()

        # Add detailed breakdowns
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
            }

        # Knowledge gaps
        gaps = [r for r in self.records if r.is_knowledge_gap]
        stats["knowledge_gaps"] = [
            {
                "message": r.message,
                "similarity": r.chunk_similarity_avg,
                "tool_called": r.tool_called,
                "tool_name": r.tool_name,
            }
            for r in sorted(gaps, key=lambda r: r.chunk_similarity_avg)[:20]
        ]

        # Disliked responses (actionable feedback)
        if self.votes:
            stats["disliked_responses"] = [
                {
                    "user_message": v.user_message,
                    "response_snippet": v.response_snippet,
                    "model": v.model,
                    "ts": v.ts,
                }
                for v in self.votes if not v.liked
            ]

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2)

        print(f"✅ Exported summary to {output_path}\n")

    def print_model_comparison(self):
        """Compare models on quality, cost, and latency (admin only)."""
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

        # Build satisfaction lookup by model from votes
        vote_by_model = defaultdict(lambda: {"likes": 0, "total": 0})
        for v in self.votes:
            model = v.model or "unknown"
            vote_by_model[model]["total"] += 1
            if v.liked:
                vote_by_model[model]["likes"] += 1

        has_votes = any(d["total"] > 0 for d in vote_by_model.values())
        sat_header = "  Satisf" if has_votes else ""

        print(f"{'Model':<30} {'Queries':>8} {'Avg Sim':>8} {'Avg Cost':>10} {'$/Query':>10} {'Latency':>9}{sat_header}")
        print("─" * (95 + (9 if has_votes else 0)))

        for model in sorted(by_model.keys(), key=lambda m: len(by_model[m]), reverse=True):
            records = by_model[model]
            count = len(records)
            avg_sim = statistics.mean([r.chunk_similarity_avg for r in records])
            total_cost = sum([r.cost_usd for r in records])
            avg_cost_per_query = total_cost / count if count > 0 else 0
            avg_lat = statistics.mean([r.latency_ms for r in records])

            sat_col = ""
            if has_votes and vote_by_model[model]["total"] > 0:
                vd = vote_by_model[model]
                sat_col = f"  {100*vd['likes']/vd['total']:>5.0f}%"

            print(f"{model:<30} {count:>8} {avg_sim:>8.3f} ${total_cost:>9.4f} "
                  f"${avg_cost_per_query:>9.5f} {int(avg_lat):>7,}ms{sat_col}")
        print()

    def print_cost_analysis(self):
        """Analyze cost vs quality (ROI) for each model."""
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║              COST vs QUALITY ANALYSIS (ROI)               ║")
        print("╚═══════════════════════════════════════════════════════════╝\n")

        by_model = defaultdict(list)
        for r in self.records:
            if r.model != "unknown" and r.cost_usd > 0:
                by_model[r.model].append(r)

        if not by_model:
            print("❌ No cost data available\n")
            return

        # Calculate similarity per dollar
        roi_data = []
        for model, records in by_model.items():
            avg_sim = statistics.mean([r.chunk_similarity_avg for r in records])
            total_cost = sum([r.cost_usd for r in records])
            if total_cost > 0:
                sim_per_dollar = avg_sim / total_cost
                roi_data.append((model, avg_sim, total_cost, sim_per_dollar, len(records)))

        # Sort by ROI (similarity per dollar)
        roi_data.sort(key=lambda x: x[3], reverse=True)

        print(f"{'Model':<30} {'Queries':>8} {'Avg Sim':>8} {'Total $':>10} {'Sim/$':>10} {'Rating':>8}")
        print("─" * 95)

        for model, avg_sim, total_cost, sim_per_dollar, count in roi_data:
            # Rating: 5 stars for best ROI, scale down
            stars = "⭐" * min(5, max(1, int(sim_per_dollar / roi_data[0][3] * 5)))
            print(f"{model:<30} {count:>8} {avg_sim:>8.3f} ${total_cost:>9.4f} "
                  f"{sim_per_dollar:>10.1f} {stars:>8}")

        print(f"\n💡 Higher 'Sim/$' = better bang for buck")
        print(f"   Top pick: {roi_data[0][0]} ({roi_data[0][3]:.1f} similarity per dollar)\n")

    def print_provider_comparison(self):
        """Compare providers (OpenAI, Anthropic, Google, Ollama)."""
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

    def print_config_experiments(self):
        """Analyze impact of temperature and top-k settings."""
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║              CONFIGURATION EXPERIMENTS                    ║")
        print("╚═══════════════════════════════════════════════════════════╝\n")

        # Temperature analysis
        by_temp = defaultdict(list)
        for r in self.records:
            if r.temperature > 0:
                # Round to nearest 0.1
                temp_bucket = round(r.temperature * 10) / 10
                by_temp[temp_bucket].append(r)

        if by_temp:
            print("Temperature Impact:")
            print(f"{'Temp':>8} {'Queries':>8} {'Avg Sim':>8} {'Std Dev':>8}")
            print("─" * 40)
            for temp in sorted(by_temp.keys()):
                records = by_temp[temp]
                avg_sim = statistics.mean([r.chunk_similarity_avg for r in records])
                std_dev = statistics.stdev([r.chunk_similarity_avg for r in records]) if len(records) > 1 else 0
                print(f"{temp:>8.1f} {len(records):>8} {avg_sim:>8.3f} {std_dev:>8.3f}")
            print()

        # Top-K analysis
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

    def admin_report(self):
        """Print admin-specific comprehensive analysis."""
        self.print_summary()
        print()
        self.print_vote_analysis()
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

    def full_report(self):
        """Print comprehensive analysis."""
        self.print_summary()
        print()
        self.print_vote_analysis()
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


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyze query logs from Digital Twin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Production logs
  python analyze_logs.py                           # Full report
  python analyze_logs.py --exclude-owner          # Drop Barbara's own sessions
  python analyze_logs.py --knowledge-gaps          # Only knowledge gaps
  python analyze_logs.py --last 100                # Last 100 queries
  python analyze_logs.py --votes                   # Vote / satisfaction analysis

  # Admin logs
  python analyze_logs.py --log query_log_admin.jsonl --admin
  python analyze_logs.py --log query_log_admin.jsonl --compare-models
  python analyze_logs.py --log query_log_admin.jsonl --cost-analysis
  python analyze_logs.py --log query_log_admin.jsonl --compare-providers
        """,
    )
    parser.add_argument("--log", default="query_log.jsonl", help="Path to JSONL log file")
    parser.add_argument("--exclude-owner", action="store_true", help="Exclude Barbara-marked traffic and any sessions containing it")
    parser.add_argument("--last", type=int, metavar="N", help="Analyze only last N queries")
    parser.add_argument("--export", metavar="FILE", help="Export summary to JSON")
    parser.add_argument("--knowledge-gaps", action="store_true", help="Show only knowledge gaps")
    parser.add_argument("--performance", action="store_true", help="Show only performance issues")
    parser.add_argument("--votes", action="store_true", help="Show vote / satisfaction analysis")
    # Admin-specific reports
    parser.add_argument("--admin", action="store_true", help="Admin mode: full report with model/cost analysis")
    parser.add_argument("--compare-models", action="store_true", help="Compare models on quality, cost, latency")
    parser.add_argument("--cost-analysis", action="store_true", help="Cost vs quality (ROI) analysis")
    parser.add_argument("--compare-providers", action="store_true", help="Compare providers (OpenAI, Anthropic, etc)")
    parser.add_argument("--config-experiments", action="store_true", help="Analyze temperature/top-k experiments")

    args = parser.parse_args()

    analyzer = LogAnalyzer(args.log)

    if args.exclude_owner:
        analyzer.exclude_owner_traffic()

    if args.last:
        analyzer.filter_last_n(args.last)

    if args.export:
        analyzer.export_summary(args.export)
    elif args.admin:
        analyzer.admin_report()
    elif args.votes:
        analyzer.print_vote_analysis()
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
