# 🔬 Admin Logging Guide

## Overview

Admin logs are **separate from production** to keep your production analytics clean. Use admin mode for:
- 🧪 Testing different models/providers
- 💰 Comparing cost vs quality
- ⚙️ Experimenting with temperature/top-k settings
- 🎯 Validating config changes before deploying

---

## 📊 What's Logged (Admin-Specific)

### All Production Fields, Plus:

| Field | Description | Example |
|-------|-------------|---------|
| **provider** | Provider name | `"openai"`, `"anthropic"`, `"gemini"`, `"ollama"` |
| **cost_usd** | Query cost in USD | `0.00234` |
| **prompt_tokens** | Input tokens | `1847` |
| **completion_tokens** | Output tokens | `512` |
| **config_override** | User changed defaults? | `true` / `false` |

### Token & Cost Tracking

Unlike production, admin logs capture **exact costs and tokens** from LiteLLM's `SessionTracker`:
```json
{
  "cost_usd": 0.00234,
  "prompt_tokens": 1847,
  "completion_tokens": 512
}
```

This enables precise ROI analysis: *"Is GPT-4 worth 20x the cost of GPT-4-mini?"*

---

## 🚀 Quick Start

### 1. Run Admin Interface
```bash
python app_admin.py
# Visit http://localhost:7862
# Login with credentials from .env (if set)
```

### 2. Test Multiple Models
In the admin UI:
- Change **Model** dropdown to test different providers
- Adjust **Temperature** slider
- Modify **Top-K** value
- Ask the same question with different configs

### 3. Analyze Results
```bash
# Full admin report
python analyze_logs.py --log query_log_admin.jsonl --admin

# Just model comparison
python analyze_logs.py --log query_log_admin.jsonl --compare-models

# ROI analysis
python analyze_logs.py --log query_log_admin.jsonl --cost-analysis
```

---

## 📈 Admin Analysis Reports

### 1. Model Comparison
**Shows:** Quality, cost, and latency by model

```bash
python analyze_logs.py --log query_log_admin.jsonl --compare-models
```

**Example output:**
```
Model                           Queries  Avg Sim   Avg Cost    $/Query   Latency
───────────────────────────────────────────────────────────────────────────────────
openai/gpt-4.1                        3    0.680 $   0.0069 $  0.00230   2,429ms
anthropic/claude-sonnet-4.6           2    0.800 $   0.0039 $  0.00194   2,045ms
openai/gpt-4.1-mini                   2    0.780 $   0.0002 $  0.00011   1,489ms
gemini/gemini-2.5-flash               1    0.812 $   0.0001 $  0.00008   1,234ms
```

**Insights:**
- Claude Sonnet: Best similarity (0.800) but pricey ($0.00194/query)
- GPT-4.1-mini: Great balance (0.780 similarity, $0.00011/query)
- Gemini Flash: Fastest, cheapest, excellent quality

### 2. Cost vs Quality (ROI)
**Shows:** Which model gives best similarity-per-dollar

```bash
python analyze_logs.py --log query_log_admin.jsonl --cost-analysis
```

**Example output:**
```
Model                           Queries  Avg Sim    Total $      Sim/$   Rating
───────────────────────────────────────────────────────────────────────────────────
gemini/gemini-2.5-flash               1    0.812 $   0.0001    10150.0    ⭐⭐⭐⭐⭐
openai/gpt-4.1-mini                   2    0.780 $   0.0002     3714.3        ⭐
anthropic/claude-sonnet-4.6           2    0.800 $   0.0039      206.6        ⭐
openai/gpt-4.1                        3    0.680 $   0.0069       98.4        ⭐

💡 Top pick: gemini/gemini-2.5-flash (10150.0 similarity per dollar)
```

**Decision:** Gemini Flash is **100x more cost-effective** than GPT-4!

### 3. Provider Comparison
**Shows:** Aggregate stats by provider (OpenAI, Anthropic, Google)

```bash
python analyze_logs.py --log query_log_admin.jsonl --compare-providers
```

**Example output:**
```
Provider         Models  Queries  Avg Sim    Total $  Avg Latency
────────────────────────────────────────────────────────────────────
anthropic             1        2    0.800 $   0.0039     2,045ms
gemini                1        1    0.812 $   0.0001     1,234ms
openai                2        5    0.720 $   0.0071     2,053ms
```

**Insights:**
- Gemini: Fastest + cheapest
- Anthropic: Best quality
- OpenAI: Most tested (5 queries)

### 4. Config Experiments
**Shows:** Impact of temperature and top-k changes

```bash
python analyze_logs.py --log query_log_admin.jsonl --config-experiments
```

**Example output:**
```
Temperature Impact:
    Temp  Queries  Avg Sim  Std Dev
────────────────────────────────────
     0.0        5    0.801    0.012
     0.4        2    0.823    0.016
     0.7        4    0.694    0.181
     1.0        1    0.771    0.089

Top-K Impact:
   Top-K  Queries  Avg Sim  Avg Latency
───────────────────────────────────────
       5       12    0.763      1.4s
       7       25    0.798      1.7s
      10        8    0.811      2.1s
      15        3    0.819      2.8s
```

**Insights:**
- Lower temp (0.4) = better, more consistent results
- Higher top-k (15) = better similarity but slower

---

## 🧪 Common Admin Workflows

### A. Find Best Model for Production

**Goal:** Test 4 models on same question, pick winner

1. Ask the same question 4 times with different models:
   ```
   Query: "What problems does Barbara solve?"

   Try:
   - openai/gpt-4.1
   - openai/gpt-4.1-mini
   - anthropic/claude-sonnet-4.6
   - gemini/gemini-2.5-flash
   ```

2. Analyze:
   ```bash
   python analyze_logs.py --log query_log_admin.jsonl --cost-analysis
   ```

3. Decision matrix:
   - **Production default:** Balance of cost + quality (likely GPT-4.1-mini)
   - **High-stakes queries:** Best quality (Claude Sonnet or Gemini Flash)
   - **High-volume/low-budget:** Cheapest (Gemini Flash)

### B. Tune Temperature

**Goal:** Find optimal temperature for consistency

1. Test same question at temps: 0.0, 0.4, 0.7, 1.0
2. Run config analysis:
   ```bash
   python analyze_logs.py --log query_log_admin.jsonl --config-experiments
   ```
3. Look for lowest `Std Dev` (most consistent)

### C. Optimize Top-K

**Goal:** Balance retrieval quality vs latency

1. Test same question with top-k: 5, 7, 10, 15
2. Run config analysis
3. Find sweet spot where similarity plateaus (diminishing returns)

---

## 💡 Pro Tips

### 1. A/B Testing Pattern

Create controlled experiments:

```bash
# Test 1: Same query, different models
for model in "openai/gpt-4.1-mini" "gemini/gemini-2.5-flash"; do
  echo "Testing: $model"
  # Run query in admin UI with this model
  # Wait for response
done

# Analyze
python analyze_logs.py --log query_log_admin.jsonl --compare-models
```

### 2. Cost Projection

Estimate monthly costs based on admin tests:

```python
# From cost analysis output
avg_cost_per_query = 0.00011  # GPT-4.1-mini
queries_per_month = 1000

monthly_cost = avg_cost_per_query * queries_per_month
print(f"Projected monthly cost: ${monthly_cost:.2f}")
# Output: Projected monthly cost: $0.11
```

### 3. Knowledge Gap Crosscheck

Compare admin vs production knowledge gaps:

```bash
# Production gaps
python analyze_logs.py --knowledge-gaps > prod_gaps.txt

# Admin gaps
python analyze_logs.py --log query_log_admin.jsonl --knowledge-gaps > admin_gaps.txt

# If admin tests reveal gaps, they'll show in production too
```

### 4. Multi-Model Ensemble Strategy

Use admin logs to design a routing strategy:

```
IF query is knowledge_gap (similarity < 0.55):
  → Use send_notification tool
ELIF query is high-stakes (e.g., "walkthrough"):
  → Use best model (Claude Sonnet) despite cost
ELSE:
  → Use cheapest model (Gemini Flash)
```

---

## 📂 File Locations

```
/digital-twin/
├── query_log.jsonl              ← Production logs
├── query_log_admin.jsonl        ← Admin logs (new)
├── app.py                       ← Production app
├── app_admin.py                 ← Admin app (updated)
└── analyze_logs.py              ← Unified analyzer (updated)
```

---

## 🔐 Security Note

**Admin logs may contain:**
- System prompt experiments (if you edit the prompt)
- Config changes that reveal business logic
- Cost data

**Best practice:** Keep `query_log_admin.jsonl` in `.gitignore` or store separately from production logs.

---

## 🎯 Decision Framework

Use this matrix to decide on production model:

| Priority | Choose | Example Use Case |
|----------|--------|------------------|
| **Quality** | Highest similarity regardless of cost | Investor demo, portfolio walkthrough |
| **Cost** | Highest Sim/$ (ROI) | High-volume public chatbot |
| **Latency** | Fastest model with acceptable quality | Real-time conversational UI |
| **Balance** | Top 2-3 on all metrics | General production default |

---

## 📊 Sample Analysis Session

```bash
# 1. Run admin app, test 3 models
python app_admin.py

# 2. Ask same question with each:
#    - openai/gpt-4.1
#    - openai/gpt-4.1-mini
#    - gemini/gemini-2.5-flash

# 3. Full admin report
python analyze_logs.py --log query_log_admin.jsonl --admin

# 4. Focus on ROI
python analyze_logs.py --log query_log_admin.jsonl --cost-analysis

# 5. Make decision
# Result: Gemini Flash is 100x cheaper with 0.812 similarity!
# Decision: Switch production to gemini/gemini-2.5-flash

# 6. Update .env
echo 'LLM_MODEL=gemini/gemini-2.5-flash' >> .env

# 7. Restart production
python app.py
```

---

## 🆚 Admin vs Production Logs

| Aspect | Production | Admin |
|--------|-----------|-------|
| **File** | `query_log.jsonl` | `query_log_admin.jsonl` |
| **Purpose** | Find KB gaps | Compare models/configs |
| **Cost tracking** | ❌ (not available) | ✅ Precise via LiteLLM |
| **Queries** | Real user traffic | Your experiments |
| **Analytics** | Knowledge gaps, usage | ROI, model comparison |
| **Action items** | Add content to KB | Choose best model/config |

---

## 📚 Next Steps

1. **Run a test:** Ask 3 questions with different models
2. **Analyze:** `python analyze_logs.py --log query_log_admin.jsonl --admin`
3. **Decide:** Pick the best model for your use case
4. **Deploy:** Update `LLM_MODEL` in `.env` and restart production

Your admin logging is now enterprise-grade! 🎉
