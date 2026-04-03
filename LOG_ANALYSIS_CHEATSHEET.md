# 📋 Query Log Analysis Cheat Sheet

## Production Logs

```bash
# Full report
python analyze_logs.py

# Knowledge gaps only
python analyze_logs.py --knowledge-gaps

# Performance issues only
python analyze_logs.py --performance

# Last 100 queries
python analyze_logs.py --last 100

# Export to JSON
python analyze_logs.py --export summary.json
```

## Admin Logs (Model Testing)

```bash
# Full admin report (models + cost + quality)
python analyze_logs.py --log query_log_admin.jsonl --admin

# Compare models
python analyze_logs.py --log query_log_admin.jsonl --compare-models

# Cost vs quality (ROI)
python analyze_logs.py --log query_log_admin.jsonl --cost-analysis

# Compare providers
python analyze_logs.py --log query_log_admin.jsonl --compare-providers

# Config experiments (temp, top-k)
python analyze_logs.py --log query_log_admin.jsonl --config-experiments
```

## Quick jq Queries (Production)

```bash
# Count total queries
jq -s length query_log.jsonl

# Average latency
jq '.latency_ms' query_log.jsonl | awk '{sum+=$1; n++} END {print sum/n "ms"}'

# Average similarity
jq '.chunk_similarity_avg' query_log.jsonl | awk '{sum+=$1; n++} END {print sum/n}'

# Find queries with low similarity (<0.55)
jq 'select(.chunk_similarity_avg < 0.55)' query_log.jsonl

# Queries that triggered tools
jq 'select(.tool_called == true)' query_log.jsonl

# Top 10 slowest queries
jq -s 'sort_by(.latency_ms) | reverse | .[0:10] | .[] | {latency_ms, message}' query_log.jsonl

# Workflow distribution
jq -r '.workflow' query_log.jsonl | sort | uniq -c

# Model usage
jq -r '.model' query_log.jsonl | sort | uniq -c

# Queries from today
jq "select(.ts | startswith(\"$(date +%Y-%m-%d)\"))" query_log.jsonl

# Similarity distribution (histogram)
jq '.chunk_similarity_avg' query_log.jsonl | \
  awk '{bucket=int($1*10)/10; count[bucket]++} END {for(b in count) print b, count[b]}' | sort -n
```

## One-Liners for Monitoring

```bash
# Knowledge gap rate (%)
echo "scale=1; $(jq -s 'map(select(.chunk_similarity_avg < 0.55)) | length' query_log.jsonl) * 100 / $(jq -s length query_log.jsonl)" | bc

# P95 latency
jq -s 'sort_by(.latency_ms) | .[length*95/100 | floor].latency_ms' query_log.jsonl

# Tool call rate (%)
echo "scale=1; $(jq -s 'map(select(.tool_called)) | length' query_log.jsonl) * 100 / $(jq -s length query_log.jsonl)" | bc

# Average response length
jq '.response_chars' query_log.jsonl | awk '{sum+=$1; n++} END {print int(sum/n) " chars"}'

# Today's query count
jq "select(.ts | startswith(\"$(date +%Y-%m-%d)\"))" query_log.jsonl | wc -l
```

## Red Flags to Watch For

```bash
# 🚨 High knowledge gap rate (>20%)
# 🚨 Latency spike (P95 > 5000ms)
# 🚨 Frequent tool calls (>10%)
# 🚨 Low avg similarity (<0.60)
# 🚨 Many errors (had_error: true)
```

## Export for Analysis

```bash
# To CSV (for Excel/Google Sheets)
jq -r '[.ts, .message, .latency_ms, .chunk_similarity_avg, .workflow] | @csv' query_log.jsonl > queries.csv

# To pandas-friendly JSON
jq -s . query_log.jsonl > queries_array.json

# Python quick load
# import pandas as pd
# df = pd.read_json('query_log.jsonl', lines=True)
```

## Alerting Examples

```bash
# Alert if last 50 queries have >25% gaps
#!/bin/bash
GAPS=$(tail -n 50 query_log.jsonl | jq -s 'map(select(.chunk_similarity_avg < 0.55)) | length')
if [ "$GAPS" -gt 12 ]; then
  echo "⚠️  High knowledge gap rate: $GAPS/50"
  # Send notification, email, etc.
fi

# Alert on slow queries
#!/bin/bash
SLOW=$(tail -n 20 query_log.jsonl | jq -s 'map(select(.latency_ms > 5000)) | length')
if [ "$SLOW" -gt 2 ]; then
  echo "⚠️  Performance degradation detected"
fi
```

## Key Thresholds

| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| Avg similarity | >0.70 | 0.55-0.70 | <0.55 |
| P95 latency | <3s | 3-5s | >5s |
| Knowledge gaps | <10% | 10-25% | >25% |
| Tool call rate | <5% | 5-15% | >15% |

## Admin-Specific Queries

```bash
# Average cost per query by model
jq -r 'select(.cost_usd > 0) | "\(.model) \(.cost_usd)"' query_log_admin.jsonl | \
  awk '{sum[$1]+=$2; n[$1]++} END {for(m in n) print m, sum[m]/n[m]}'

# Total cost by provider
jq -r 'select(.cost_usd > 0) | "\(.provider) \(.cost_usd)"' query_log_admin.jsonl | \
  awk '{sum[$1]+=$2} END {for(p in sum) print p, sum[p]}'

# Model with best ROI (similarity per dollar)
jq -r 'select(.cost_usd > 0) | "\(.model) \(.chunk_similarity_avg) \(.cost_usd)"' query_log_admin.jsonl | \
  awk '{roi=$2/$3; print $1, roi}' | sort -k2 -rn | head -1

# Config override rate
echo "scale=1; $(jq -s 'map(select(.config_override)) | length' query_log_admin.jsonl) * 100 / $(jq -s length query_log_admin.jsonl)" | bc

# Average tokens by model
jq -r 'select(.prompt_tokens > 0) | "\(.model) \(.prompt_tokens) \(.completion_tokens)"' query_log_admin.jsonl | \
  awk '{p[$1]+=$2; c[$1]+=$3; n[$1]++} END {for(m in n) print m, "prompt:", p[m]/n[m], "completion:", c[m]/n[m]}'
```
