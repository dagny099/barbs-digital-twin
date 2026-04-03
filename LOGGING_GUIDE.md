# Query Log Analysis Guide

## 📊 What's Being Logged

Every user query now captures:

### Original Fields
- **ts**: ISO timestamp (UTC)
- **message**: User's question
- **project**: Featured project mentioned (if any)
- **walkthrough**: Boolean - walkthrough workflow triggered
- **tool_called**: Boolean - LLM called a function
- **tool_name**: Which tool was called
- **had_error**: Error occurred

### New Enhanced Fields (Phase 1 + 2)
- **model**: LLM model used (e.g., "gpt-4.1")
- **temperature**: Generation temperature
- **n_chunks_retrieved**: How many chunks returned
- **n_chunks_config**: Top-K config value
- **response_chars**: Response length
- **latency_ms**: Total response time
- **workflow**: "walkthrough" | "diagram_only" | "standard"
- **chunk_similarity_avg**: Average cosine similarity (0-1)
- **chunk_similarity_max**: Best chunk match (0-1)

---

## 🚀 Quick Start

### Run Full Report
```bash
python analyze_logs.py
```

Shows:
- Summary statistics
- Workflow breakdown
- Model usage
- Tool usage patterns
- Knowledge gaps (low similarity queries)
- Performance outliers (slow queries)

### Focus on Knowledge Gaps
```bash
python analyze_logs.py --knowledge-gaps
```

Lists queries where retrieval quality was poor (`similarity < 0.55`).
**These are your content addition priorities!**

### Focus on Performance
```bash
python analyze_logs.py --performance
```

Lists slow queries (`>5s latency`).
Good for debugging model/infrastructure issues.

### Analyze Recent Activity
```bash
python analyze_logs.py --last 100
```

Only analyze the last 100 queries (useful for focused debugging).

### Export to JSON
```bash
python analyze_logs.py --export summary.json
```

Machine-readable summary for dashboards or further analysis.

---

## 🔍 Key Metrics Explained

### Chunk Similarity (Most Important!)

Cosine similarity between query and retrieved chunks:

| Score | Meaning | Action |
|-------|---------|--------|
| **0.80+** | Excellent match | KB knows this well ✅ |
| **0.55-0.79** | Moderate match | Acceptable, monitor |
| **<0.55** | Poor match | **Content gap - add info!** 🚨 |

### Workflow Types

- **standard**: Regular Q&A
- **walkthrough**: Featured project deep-dive triggered
- **diagram_only**: Project diagram shown but no walkthrough

Workflows with consistently lower similarity may need better content structure.

### Tool Calls

**Tool call + low similarity = high-priority gap**

Example:
```json
{
  "message": "Tell me about your startup experience",
  "chunk_similarity_avg": 0.32,
  "tool_called": true,
  "tool_name": "send_notification"
}
```

Interpretation: KB has no good info about startups → LLM notified you → **add startup experience to KB**.

---

## 📈 Common Analysis Patterns

### Find Content Gaps
```bash
# Get all low-similarity queries
python analyze_logs.py --knowledge-gaps

# Or with jq:
jq 'select(.chunk_similarity_avg < 0.55)' query_log.jsonl
```

### Monitor Performance Trends
```bash
# Average latency over time
jq '.latency_ms' query_log.jsonl | awk '{sum+=$1; n++} END {print sum/n "ms"}'

# P95 latency
jq -s 'sort_by(.latency_ms) | .[length*95/100 | floor].latency_ms' query_log.jsonl
```

### Workflow Effectiveness
```bash
# Compare similarity by workflow
jq -r '"\(.workflow) \(.chunk_similarity_avg)"' query_log.jsonl | \
  awk '{sum[$1]+=$2; n[$1]++} END {for(w in sum) print w, sum[w]/n[w]}'
```

### Model Comparison
If you've tried different models:
```bash
jq -r '"\(.model) \(.latency_ms) \(.chunk_similarity_avg)"' query_log.jsonl | \
  awk '{latency[$1]+=$2; sim[$1]+=$3; n[$1]++}
       END {for(m in n) print m, latency[m]/n[m] "ms", sim[m]/n[m] "sim"}'
```

---

## 🎯 Action Plan Based on Logs

### Daily/Weekly Review
1. Run `python analyze_logs.py`
2. Check **knowledge gaps** section
3. Add top 3-5 missing topics to your KB

### Performance Regression
If latency spikes:
1. Run `python analyze_logs.py --performance`
2. Check if specific queries or models are slow
3. Investigate: model change? API issues? Complex queries?

### Quality Monitoring
Set up a simple alert:
```bash
# Alert if >20% of recent queries have low similarity
GAPS=$(jq -s 'map(select(.chunk_similarity_avg < 0.55)) | length' \
  <(tail -n 100 query_log.jsonl))
TOTAL=$(tail -n 100 query_log.jsonl | wc -l)
PERCENT=$((100 * GAPS / TOTAL))

if [ $PERCENT -gt 20 ]; then
  echo "⚠️  Warning: ${PERCENT}% knowledge gap rate!"
fi
```

---

## 🔧 Maintenance

### Archive Old Logs
```bash
# Keep logs manageable
mv query_log.jsonl query_log_archive_$(date +%Y%m%d).jsonl
touch query_log.jsonl
```

### Clean Legacy Entries
Your old 13 entries don't have the new fields. Options:
1. **Keep them**: Script handles mixed formats gracefully
2. **Archive them**: Start fresh with enhanced logging
```bash
tail -n 13 query_log.jsonl > query_log_legacy.jsonl
echo "" > query_log.jsonl  # Start fresh
```

---

## 💡 Pro Tips

1. **Tool calls are signals**: Every `send_notification` is a knowledge gap
2. **Similarity matters more than latency**: Fast wrong answers are worse than slow right ones
3. **Workflow patterns**: If walkthroughs have higher similarity, you've curated those projects well
4. **Response length**: Very long responses may indicate prompt engineering issues
5. **Temporal patterns**: Check if gaps correlate with new topics or user types

---

## 📚 Export Formats

### JSON Export Structure
```bash
python analyze_logs.py --export stats.json
```

Produces:
```json
{
  "total_queries": 150,
  "date_range": {"first": "...", "last": "..."},
  "latency_ms": {"mean": 2341, "median": 2100, "p95": 4500},
  "chunk_similarity": {"mean": 0.723, "median": 0.741},
  "workflows": {
    "standard": {"count": 120, "avg_similarity": 0.71},
    "walkthrough": {"count": 30, "avg_similarity": 0.82}
  },
  "knowledge_gaps": [
    {"message": "...", "similarity": 0.32, "tool_called": true}
  ]
}
```

Use for:
- Dashboards (Grafana, Streamlit)
- Automated reports
- Trend tracking

---

## 🤝 Integration Ideas

### Slack/Email Alerts
```bash
#!/bin/bash
# daily_kb_review.sh
REPORT=$(python analyze_logs.py --last 50 --knowledge-gaps)
echo "$REPORT" | mail -s "Daily KB Gaps" your@email.com
```

### Gradio Dashboard
Add a "Stats" tab to your admin interface that calls `analyze_logs.py --export`.

### Continuous Improvement Loop
1. Logs reveal gaps
2. Add content to KB
3. Re-embed with `ingest.py`
4. Monitor if similarity improves
5. Repeat

---

## 📞 Questions?

The script is self-documenting:
```bash
python analyze_logs.py --help
```

For custom analysis, the JSONL format is standard - use `jq`, pandas, or any JSON tool.
