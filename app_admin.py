"""
app_admin.py — Admin / debug interface for Barbara's Digital Twin
═══════════════════════════════════════════════════════════════════
Side-by-side chat + retrieval inspector with multi-provider support.

Provider architecture:
  - CHAT:       LiteLLM (OpenAI, Anthropic, Google, Ollama)
  - EMBEDDINGS: OpenAI SDK only (pinned to text-embedding-3-small)
  - COST:       LiteLLM completion_cost() + SessionTracker

Run locally:
    pip install litellm   # one new dependency
    python app_admin.py   # runs on :7861 (separate from prod :7860)
"""

import os
import json
import time
import html as html_lib
import random
import subprocess
from dataclasses import dataclass, field
from datetime import datetime

from openai import OpenAI
import litellm
import gradio as gr
import chromadb
import requests
from featured_projects import select_project_for_walkthrough, get_diagram_path, enrich_message_for_walkthrough


# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY is None:
    raise Exception("OPENAI_API_KEY is required (used for embeddings + OpenAI chat).")

# Provider API keys — set whichever ones you have.
# LiteLLM reads these automatically from env.
# ANTHROPIC_API_KEY, GEMINI_API_KEY are optional.
# Ollama needs no key, just a running server.

LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-4.1")
N_CHUNKS_RETRIEVE = 8
SERVER_PORT = int(os.getenv("ADMIN_PORT", 7861))

# OpenAI client — used ONLY for embeddings (not chat)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Pushover notifications
pushover_user = os.getenv("PUSHOVER_USER")
pushover_token = os.getenv("PUSHOVER_TOKEN")
pushover_url = "https://api.pushover.net/1/messages.json"

# ChromaDB
if not os.path.exists(".chroma_db_DT"):
    from db_sync import pull_db
    pull_db()

chroma_client = chromadb.PersistentClient(path=".chroma_db_DT")
collection = chroma_client.get_or_create_collection(name="barb-twin")

if collection.count() == 0:
    print("Knowledge base empty — running ingest...")
    subprocess.run(["python", "ingest.py", "--all"], check=True)

print(f"✅ Admin mode — collection ready: {collection.count()} chunks loaded")

# System prompt
with open("SYSTEM_PROMPT.md", "r", encoding="utf-8") as _f:
    system_message = _f.read()


# ═══════════════════════════════════════════════════════════════════
# MULTI-PROVIDER MODEL REGISTRY
# ═══════════════════════════════════════════════════════════════════

AVAILABLE_MODELS = [
    # OpenAI
    "openai/gpt-4.1",
    "openai/gpt-4.1-mini",
    "openai/gpt-4.1-nano",
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    # Anthropic
    "anthropic/claude-sonnet-4-20250514",
    "anthropic/claude-haiku-4-20250414",
    # Google
    "gemini/gemini-2.5-flash",
    "gemini/gemini-2.5-pro",
    # Ollama (local)
    "ollama/llama3.2",
    "ollama/mistral",
]

MODELS_WITHOUT_TOOL_SUPPORT = {
    "ollama/mistral",
}

def model_supports_tools(model_name: str) -> bool:
    return model_name not in MODELS_WITHOUT_TOOL_SUPPORT


# ═══════════════════════════════════════════════════════════════════
# TOOL DEFINITIONS (duplicated from app.py)
# ═══════════════════════════════════════════════════════════════════

def send_notification(message: str):
    payload = {
        "user": pushover_user, "token": pushover_token,
        "device": "oneplusnordn2005g", "message": message,
    }
    requests.post(pushover_url, data=payload)
    return f"Notification sent: {message}"

def dice_roll():
    return random.randint(1, 6)

tools = [
    {"type": "function", "function": {
        "name": "send_notification",
        "description": (
            "Sends a push notification to the real Barbara's phone via Pushover. "
            "Use when: 1) Someone wants to get in touch, hire, or collaborate. "
            "2) You don't know the answer — send AUTOMATICALLY with the question."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "The notification message"}
            },
            "required": ["message"],
        },
    }},
    {"type": "function", "function": {
        "name": "dice_roll",
        "description": "Simulates rolling a single six-sided die.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
]

def handle_tool_call(tool_calls):
    results = []
    for tc in tool_calls:
        name = tc.function.name
        args = json.loads(tc.function.arguments)
        if name == "send_notification":
            content = send_notification(args["message"])
        elif name == "dice_roll":
            content = f"Dice roll was: {dice_roll()}"
        else:
            content = f"Unknown function: {name}"
        results.append({"role": "tool", "content": content, "tool_call_id": tc.id})
    return results


# ═══════════════════════════════════════════════════════════════════
# SESSION COST TRACKER
# ═══════════════════════════════════════════════════════════════════

@dataclass
class CallRecord:
    timestamp: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    call_type: str  # "chat", "tool_loop", "chat_stream", "embedding"

@dataclass
class SessionTracker:
    """Tracks token usage and cost across messages in one admin session."""
    calls: list = field(default_factory=list)

    def log_chat(self, response, model: str, call_type: str = "chat"):
        """Log a LiteLLM completion response with auto cost calculation."""
        try:
            cost = litellm.completion_cost(completion_response=response)
        except Exception:
            cost = 0.0

        usage = getattr(response, "usage", None)
        prompt_tok = getattr(usage, "prompt_tokens", 0) if usage else 0
        completion_tok = getattr(usage, "completion_tokens", 0) if usage else 0

        self.calls.append(CallRecord(
            timestamp=datetime.now().isoformat(),
            model=model,
            prompt_tokens=prompt_tok,
            completion_tokens=completion_tok,
            cost_usd=cost,
            call_type=call_type,
        ))

    def log_embedding(self, response):
        """Log an OpenAI embedding call."""
        usage = getattr(response, "usage", None)
        tokens = getattr(usage, "total_tokens", 0) if usage else 0
        cost = tokens * 0.00000002  # text-embedding-3-small: $0.02/1M tokens
        self.calls.append(CallRecord(
            timestamp=datetime.now().isoformat(),
            model="openai/text-embedding-3-small",
            prompt_tokens=tokens,
            completion_tokens=0,
            cost_usd=cost,
            call_type="embedding",
        ))

    def log_stream(self, model: str, prompt_text: str, completion_text: str):
        """Log a streaming completion by estimating cost from text."""
        try:
            cost = litellm.completion_cost(
                model=model, prompt=prompt_text, completion=completion_text,
            )
        except Exception:
            cost = 0.0

        self.calls.append(CallRecord(
            timestamp=datetime.now().isoformat(),
            model=model,
            prompt_tokens=0,
            completion_tokens=0,
            cost_usd=cost,
            call_type="chat_stream",
        ))

    def summary(self) -> dict:
        total_prompt = sum(c.prompt_tokens for c in self.calls)
        total_completion = sum(c.completion_tokens for c in self.calls)
        total_cost = sum(c.cost_usd for c in self.calls)
        return {
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "total_tokens": total_prompt + total_completion,
            "total_cost_usd": round(total_cost, 6),
            "total_calls": len(self.calls),
        }

    def last_query_cost(self) -> float:
        """Sum cost of the most recent query (may span multiple calls)."""
        if not self.calls:
            return 0.0
        last_ts = self.calls[-1].timestamp
        return sum(c.cost_usd for c in self.calls if c.timestamp == last_ts)

    def history_for_json(self) -> list:
        return [
            {
                "timestamp": c.timestamp, "model": c.model, "type": c.call_type,
                "prompt_tokens": c.prompt_tokens,
                "completion_tokens": c.completion_tokens,
                "cost_usd": round(c.cost_usd, 8),
            }
            for c in self.calls
        ]


session_tracker = SessionTracker()


# ═══════════════════════════════════════════════════════════════════
# RETRIEVAL ENGINE (OpenAI embeddings, pinned)
# ═══════════════════════════════════════════════════════════════════

def retrieve_with_context(message, n_results=N_CHUNKS_RETRIEVE):
    start = time.time()

    resp = openai_client.embeddings.create(
        model="text-embedding-3-small", input=[message],
    )
    session_tracker.log_embedding(resp)
    query_embedding = resp.data[0].embedding

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["metadatas", "documents", "distances"],
    )

    return {
        "documents": results["documents"][0],
        "metadatas": results["metadatas"][0],
        "distances": results["distances"][0],
        "query_embedding": query_embedding,
        "retrieval_time_ms": (time.time() - start) * 1000,
        "n_results": n_results,
    }


def l2_to_cosine_sim(l2_distance):
    sim = 1.0 - (l2_distance ** 2) / 2.0
    return max(0.0, min(1.0, sim))


# ═══════════════════════════════════════════════════════════════════
# FORMATTING
# ═══════════════════════════════════════════════════════════════════

SOURCE_COLORS = {
    "github-readme":   ("#EEEDFE", "#3C3489"),
    "project-summary": ("#E1F5EE", "#085041"),
    "project-brief":   ("#E1F5EE", "#085041"),
    "mkdocs":          ("#E6F1FB", "#0C447C"),
    "kb-biosketch":    ("#FAEEDA", "#633806"),
    "biosketch":       ("#FAEEDA", "#633806"),
    "resume":          ("#EAF3DE", "#27500A"),
}
DEFAULT_SOURCE_COLOR = ("#F1EFE8", "#444441")


def _score_bar_color(sim):
    if sim >= 0.75:
        return "#1D9E75"
    elif sim >= 0.55:
        return "#EF9F27"
    return "#E24B4A"


def _card(value, label):
    return (
        '<div style="flex:1;background:var(--background-fill-secondary, #f7f7f5);'
        'border-radius:8px;padding:10px 12px;text-align:center;min-width:0;">'
        f'<div style="font-size:18px;font-weight:500;white-space:nowrap;'
        f'overflow:hidden;text-overflow:ellipsis;">{value}</div>'
        f'<div style="font-size:11px;color:var(--body-text-color-subdued, #888);margin-top:2px;">{label}</div>'
        '</div>'
    )


def format_metrics_html(ctx, active_config=None, query_cost=0.0, workflow="Standard"):
    n = len(ctx["documents"])
    sims = [l2_to_cosine_sim(d) for d in ctx["distances"]]
    avg_sim = sum(sims) / n if n else 0

    cfg = active_config or {}
    k = cfg.get("top_k", ctx["n_results"])
    temp = cfg.get("temperature", "—")
    model = cfg.get("model", LLM_MODEL)
    model_short = model.split("/")[-1] if "/" in model else model
    sess = session_tracker.summary()

    return (
        '<div style="display:flex;gap:8px;margin:4px 0;flex-wrap:wrap;">'
        + _card(workflow, "Workflow")
        + _card(str(n), "Chunks")
        + _card(f"{avg_sim:.2f}", "Avg sim")
        + _card(f"{ctx['retrieval_time_ms']:.0f}ms", "Retrieval")
        + _card(f"k={k}", "Top-K")
        + _card(str(temp), "Temp")
        + _card(model_short, "Model")
        + _card(f"${query_cost:.4f}", "Query cost")
        + _card(f"${sess['total_cost_usd']:.4f}", "Session total")
        + '</div>'
    )


def format_chunks_html(ctx):
    if not ctx["documents"]:
        return '<div style="padding:24px;text-align:center;color:#888;">No chunks retrieved.</div>'

    cards = []
    for i, (doc, meta, dist) in enumerate(
        zip(ctx["documents"], ctx["metadatas"], ctx["distances"])
    ):
        sim = l2_to_cosine_sim(dist)
        pct = max(0, min(100, sim * 100))
        bar_color = _score_bar_color(sim)
        raw_source = meta.get("source", "unknown:unknown")
        source_type, source_id = (raw_source.split(":", 1) if ":" in raw_source
                                   else (raw_source, ""))
        section = meta.get("section") or "—"
        chunk_idx = meta.get("chunk_index", "?")
        bg, fg = SOURCE_COLORS.get(source_type, DEFAULT_SOURCE_COLOR)
        text_display = html_lib.escape(doc[:800]) + (" …" if len(doc) > 800 else "")

        cards.append(f"""
        <div style="border:1px solid var(--border-color-primary, #ddd);border-radius:8px;
                    padding:10px 12px;margin-bottom:8px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
            <span style="font-size:11px;font-weight:500;padding:2px 10px;border-radius:99px;
                         background:{bg};color:{fg};">{html_lib.escape(source_type)}</span>
            <div style="display:flex;align-items:center;gap:8px;">
              <span style="font-size:11px;color:#888;">#{i+1}</span>
              <div style="width:80px;height:4px;border-radius:2px;
                          background:var(--border-color-primary, #e0e0e0);position:relative;">
                <div style="height:100%;border-radius:2px;position:absolute;left:0;top:0;
                            width:{pct:.0f}%;background:{bar_color};"></div>
              </div>
              <span style="font-size:12px;font-weight:500;min-width:32px;text-align:right;">{sim:.3f}</span>
            </div>
          </div>
          <div style="font-size:12px;font-family:monospace;padding:8px;
                      background:var(--background-fill-secondary, #f7f7f5);
                      border-radius:6px;line-height:1.5;max-height:140px;
                      overflow-y:auto;white-space:pre-wrap;word-break:break-word;">{text_display}</div>
          <div style="display:flex;flex-wrap:wrap;gap:6px 14px;margin-top:6px;font-size:11px;
                      color:var(--body-text-color-subdued, #999);">
            <span>doc: {html_lib.escape(source_id)}</span>
            <span>section: {html_lib.escape(str(section))}</span>
            <span>chars: {len(doc)}</span>
            <span>chunk: #{chunk_idx}</span>
          </div>
        </div>""")

    header = (
        f'<div style="font-size:13px;color:var(--body-text-color-subdued, #888);'
        f'margin-bottom:8px;padding:0 4px;">'
        f'{len(ctx["documents"])} chunks ranked by cosine similarity</div>'
    )
    return header + "\n".join(cards)


def format_metadata_json(ctx, active_config=None, walkthrough_info=None):
    cfg = active_config or {}
    chunks = []
    for i, (doc, meta, dist) in enumerate(
        zip(ctx["documents"], ctx["metadatas"], ctx["distances"])
    ):
        chunks.append({
            "rank": i + 1,
            "cosine_similarity": round(l2_to_cosine_sim(dist), 4),
            "l2_distance": round(dist, 4),
            "metadata": meta,
            "text_preview": doc[:200] + ("…" if len(doc) > 200 else ""),
            "char_count": len(doc),
        })
    return {
        "walkthrough": walkthrough_info or {"triggered": False},
        "retrieval": {
            "n_results": ctx["n_results"],
            "retrieval_time_ms": round(ctx["retrieval_time_ms"], 1),
            "embedding_model": "openai/text-embedding-3-small (pinned)",
        },
        "active_config": {
            "top_k": cfg.get("top_k", ctx["n_results"]),
            "temperature": cfg.get("temperature", "default"),
            "model": cfg.get("model", LLM_MODEL),
        },
        "session_cost": session_tracker.summary(),
        "call_log": session_tracker.history_for_json(),
        "chunks": chunks,
    }


EMBED_VIZ_PLACEHOLDER = """
<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
            min-height:320px;border:2px dashed var(--border-color-primary, #ccc);
            border-radius:12px;padding:32px;text-align:center;">
  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       stroke-width="1.5" style="opacity:0.4;margin-bottom:12px;">
    <circle cx="7" cy="17" r="2.5"/><circle cx="17" cy="7" r="2.5"/>
    <circle cx="12" cy="12" r="2"/><circle cx="5" cy="8" r="1.5"/>
    <circle cx="19" cy="16" r="1.5"/>
  </svg>
  <div style="font-weight:500;margin-bottom:8px;">Embedding visualization</div>
  <div style="font-size:13px;color:var(--body-text-color-subdued, #888);max-width:360px;">
    Phase 4: PCA/KMeans scatter plot showing query position
    relative to retrieved chunks in embedding space.
  </div>
</div>
"""


# ═══════════════════════════════════════════════════════════════════
# COLLECTION BROWSER
# Browse, search, and probe the full ChromaDB knowledge base.
# Designed for 300-500 chunk collections: loads all metadata once
# at startup, uses compact Dataframe for scanning, detail panel
# for reading, and semantic search for coverage probing.
# ═══════════════════════════════════════════════════════════════════

def load_full_collection():
    """Load all chunks from ChromaDB. Called once at startup, cached."""
    all_data = collection.get(include=["metadatas", "documents"])
    rows = []
    for i, (doc_id, doc, meta) in enumerate(
        zip(all_data["ids"], all_data["documents"], all_data["metadatas"])
    ):
        raw_source = meta.get("source", "unknown:unknown")
        if ":" in raw_source:
            source_type, source_id = raw_source.split(":", 1)
        else:
            source_type, source_id = raw_source, ""
        section = meta.get("section") or "—"
        chunk_idx = meta.get("chunk_index", "?")

        rows.append({
            "id": doc_id,
            "source_type": source_type,
            "source_id": source_id,
            "section": section,
            "chunk_index": chunk_idx,
            "chars": len(doc),
            "preview": doc[:120].replace("\n", " "),
            "full_text": doc,
        })
    return rows


# Cache at startup
_ALL_CHUNKS = load_full_collection()
print(f"   Collection browser: {len(_ALL_CHUNKS)} chunks cached")


def get_source_stats_html():
    """Build summary stats HTML cards for the collection browser header."""
    from collections import Counter
    source_counts = Counter(c["source_type"] for c in _ALL_CHUNKS)
    total = len(_ALL_CHUNKS)
    avg_chars = sum(c["chars"] for c in _ALL_CHUNKS) // max(total, 1)

    # Summary cards row
    cards = _card(str(total), "Total chunks")
    cards += _card(str(len(source_counts)), "Source types")
    cards += _card(str(avg_chars), "Avg chars")

    # Source distribution as a compact bar chart (inline HTML)
    max_count = max(source_counts.values()) if source_counts else 1
    bars = ""
    for src_type, count in source_counts.most_common():
        bg, fg = SOURCE_COLORS.get(src_type, DEFAULT_SOURCE_COLOR)
        pct = (count / max_count) * 100
        bars += (
            f'<div style="display:flex;align-items:center;gap:8px;margin:3px 0;">'
            f'<span style="font-size:11px;font-weight:500;padding:2px 8px;border-radius:99px;'
            f'background:{bg};color:{fg};min-width:110px;text-align:center;">{html_lib.escape(src_type)}</span>'
            f'<div style="flex:1;height:12px;background:var(--background-fill-secondary, #f5f5f3);'
            f'border-radius:4px;overflow:hidden;">'
            f'<div style="height:100%;width:{pct:.0f}%;background:{fg};opacity:0.6;border-radius:4px;"></div>'
            f'</div>'
            f'<span style="font-size:12px;font-weight:500;min-width:28px;text-align:right;">{count}</span>'
            f'</div>'
        )

    distribution = (
        '<div style="margin-top:10px;padding:12px;border:1px solid var(--border-color-primary, #ddd);'
        'border-radius:8px;">'
        '<div style="font-size:13px;font-weight:500;margin-bottom:8px;">Source distribution</div>'
        + bars +
        '</div>'
    )

    return (
        '<div style="display:flex;gap:8px;margin-bottom:8px;">'
        + cards + '</div>' + distribution
    )


def build_browse_dataframe(source_filter="All", text_search=""):
    """Build a Pandas-free list-of-lists for gr.Dataframe from cached chunks.

    Filters by source type and/or text search (case-insensitive substring
    match on full text, source, and section fields).
    """
    filtered = _ALL_CHUNKS
    if source_filter and source_filter != "All":
        filtered = [c for c in filtered if c["source_type"] == source_filter]
    if text_search and text_search.strip():
        q = text_search.strip().lower()
        filtered = [
            c for c in filtered
            if q in c["full_text"].lower()
            or q in c["source_type"].lower()
            or q in c["section"].lower()
            or q in c["source_id"].lower()
        ]

    headers = ["#", "Source type", "Source doc", "Section", "Chunk", "Chars", "Preview"]
    rows = [
        [
            i + 1,
            c["source_type"],
            c["source_id"],
            c["section"],
            c["chunk_index"],
            c["chars"],
            c["preview"],
        ]
        for i, c in enumerate(filtered)
    ]
    return {"headers": headers, "data": rows}


def do_browse(source_filter, text_search):
    """Gradio event handler: re-filter the browse table."""
    result = build_browse_dataframe(source_filter, text_search)
    status = f"{len(result['data'])} chunks shown"
    if source_filter != "All":
        status += f" (filtered: {source_filter})"
    if text_search:
        status += f" (search: \"{text_search}\")"
    return result, status, NO_CHUNK_SELECTED


def do_semantic_probe(query):
    """Embed a query and rank ALL chunks by similarity.

    This is the coverage probe — answers "does the KB even know about this?"
    without generating an LLM response. Returns a Dataframe with similarity
    scores, and a summary of what was found.
    """
    if not query or not query.strip():
        return build_browse_dataframe(), "Enter a topic to probe coverage.", NO_CHUNK_SELECTED

    resp = openai_client.embeddings.create(
        model="text-embedding-3-small", input=[query.strip()],
    )
    session_tracker.log_embedding(resp)
    query_embedding = resp.data[0].embedding

    n_all = collection.count()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_all,
        include=["metadatas", "documents", "distances"],
    )

    headers = ["Rank", "Similarity", "Source type", "Source doc", "Section", "Chars", "Preview"]
    rows = []
    for i, (doc, meta, dist) in enumerate(
        zip(results["documents"][0], results["metadatas"][0], results["distances"][0])
    ):
        sim = l2_to_cosine_sim(dist)
        raw_source = meta.get("source", "?:?")
        source_type = raw_source.split(":")[0] if ":" in raw_source else raw_source
        source_id = raw_source.split(":", 1)[1] if ":" in raw_source else ""
        section = meta.get("section") or "—"
        preview = doc[:120].replace("\n", " ")
        rows.append([i + 1, round(sim, 4), source_type, source_id, section, len(doc), preview])

    # Coverage summary
    top3_sim = [rows[i][1] for i in range(min(3, len(rows)))]
    avg_top3 = sum(top3_sim) / len(top3_sim) if top3_sim else 0
    if avg_top3 >= 0.75:
        verdict = "Strong coverage — top chunks are highly relevant."
    elif avg_top3 >= 0.55:
        verdict = "Moderate coverage — related content exists but may be indirect."
    else:
        verdict = "Weak coverage — consider adding content about this topic."

    status = f"Probed \"{query.strip()}\" across {n_all} chunks. Top-3 avg similarity: {avg_top3:.3f}. {verdict}"
    return {"headers": headers, "data": rows}, status, NO_CHUNK_SELECTED


def show_chunk_detail(evt: gr.SelectData, current_dataframe):
    """When a row is selected in the browse/probe table, show full chunk text."""
    if evt is None or current_dataframe is None:
        return NO_CHUNK_SELECTED
    try:
        row_idx = evt.index[0]
        row = current_dataframe["data"][row_idx] if isinstance(current_dataframe, dict) else current_dataframe.iloc[row_idx]

        # Find the matching chunk in the cache by preview text match
        # (works for both browse and probe results)
        preview_col = -1  # last column is always preview
        preview_text = str(row[preview_col]) if hasattr(row, '__getitem__') else ""

        matching = [c for c in _ALL_CHUNKS if c["preview"] == preview_text]
        if not matching:
            # Fallback: match by source_type + section + chars
            src_type = str(row[2]) if len(row) > 2 else ""
            for c in _ALL_CHUNKS:
                if c["source_type"] == src_type and c["chars"] == (row[5] if len(row) > 5 else row[-2]):
                    matching = [c]
                    break

        if matching:
            chunk = matching[0]
            bg, fg = SOURCE_COLORS.get(chunk["source_type"], DEFAULT_SOURCE_COLOR)
            escaped_text = html_lib.escape(chunk["full_text"])
            return (
                f'<div style="border:1px solid var(--border-color-primary, #ddd);'
                f'border-radius:8px;padding:14px;">'
                f'<div style="display:flex;gap:8px;align-items:center;margin-bottom:10px;">'
                f'<span style="font-size:11px;font-weight:500;padding:2px 10px;border-radius:99px;'
                f'background:{bg};color:{fg};">{html_lib.escape(chunk["source_type"])}</span>'
                f'<span style="font-size:12px;color:var(--body-text-color-subdued, #888);">'
                f'{html_lib.escape(chunk["source_id"])} — {html_lib.escape(str(chunk["section"]))}'
                f' — chunk #{chunk["chunk_index"]} — {chunk["chars"]} chars</span>'
                f'</div>'
                f'<div style="font-size:13px;font-family:monospace;padding:12px;'
                f'background:var(--background-fill-secondary, #f7f7f5);border-radius:6px;'
                f'line-height:1.6;white-space:pre-wrap;word-break:break-word;'
                f'max-height:400px;overflow-y:auto;">{escaped_text}</div>'
                f'</div>'
            )
    except Exception:
        pass
    return NO_CHUNK_SELECTED


NO_CHUNK_SELECTED = """
<div style="padding:24px;text-align:center;color:var(--body-text-color-subdued, #888);
            border:1px dashed var(--border-color-primary, #ddd);border-radius:8px;">
  <div style="font-size:13px;">Click a row in the table above to see the full chunk text.</div>
</div>
"""


# ═══════════════════════════════════════════════════════════════════
# INITIAL STATE
# ═══════════════════════════════════════════════════════════════════

def _initial_metrics():
    model_short = LLM_MODEL.split("/")[-1] if "/" in LLM_MODEL else LLM_MODEL
    return (
        '<div style="display:flex;gap:8px;margin:4px 0;flex-wrap:wrap;">'
        + _card("—", "Workflow")
        + _card("—", "Chunks") + _card("—", "Avg sim")
        + _card("—", "Retrieval") + _card(f"k={N_CHUNKS_RETRIEVE}", "Top-K")
        + _card("1.0", "Temp") + _card(model_short, "Model")
        + _card("$0.0000", "Query cost") + _card("$0.0000", "Session total")
        + '</div>'
    )

INITIAL_CHUNKS = """
<div style="padding:32px;text-align:center;color:var(--body-text-color-subdued, #888);">
  <div style="font-size:15px;margin-bottom:6px;">Ask the twin a question</div>
  <div style="font-size:13px;">Retrieved chunks and similarity scores will appear here.</div>
</div>
"""

INITIAL_METADATA = {"status": "Waiting for first query..."}


# ═══════════════════════════════════════════════════════════════════
# CHAT FUNCTION — LiteLLM multi-provider with cost tracking
# ═══════════════════════════════════════════════════════════════════

def respond_admin(message, history, top_k, temperature, model_name, system_prompt_edit):
    """
    Chat function with multi-provider support via LiteLLM.

    Tool calling: attempted if model supports it. On failure,
    falls back gracefully and notes it in the inspector.
    """
    k = int(top_k)
    temp = float(temperature)
    model = model_name or LLM_MODEL
    active_prompt = (
        system_prompt_edit.strip()
        if system_prompt_edit and system_prompt_edit.strip()
        else system_message
    )
    use_tools = model_supports_tools(model)

    # ── Walkthrough detection ──────────────────────────────────
    project = select_project_for_walkthrough(message)
    diagram_path = None
    walkthrough_info = {"triggered": False}
    workflow_label = "Standard"
    if project:
        enriched_message = enrich_message_for_walkthrough(message, project)
        diagram_path = get_diagram_path(project)
        walkthrough_info = {
            "triggered": True,
            "project_id": project["id"],
            "project_title": project["title"],
            "enriched_message": enriched_message,
        }
        workflow_label = "Walkthrough"
        message = enriched_message

    # ── Retrieve ────────────────────────────────────────────────
    ctx = retrieve_with_context(message, n_results=k)

    # ── Build LLM messages ──────────────────────────────────────
    context = "\n---------\n".join(ctx["documents"])
    system_enhanced = active_prompt + "\n\nContext:\n" + context
    msgs = (
        [{"role": "system", "content": system_enhanced}]
        + history
        + [{"role": "user", "content": message}]
    )

    # ── Tool handling loop (via LiteLLM) ────────────────────────
    tool_warning = ""
    if use_tools:
        try:
            response = litellm.completion(
                model=model, messages=msgs, tools=tools, temperature=temp,
            )
            session_tracker.log_chat(response, model, call_type="tool_loop")

            while response.choices[0].message.tool_calls:
                tool_result = handle_tool_call(response.choices[0].message.tool_calls)
                msgs.append(response.choices[0].message)
                msgs.extend(tool_result)
                response = litellm.completion(
                    model=model, messages=msgs, tools=tools, temperature=temp,
                )
                session_tracker.log_chat(response, model, call_type="tool_loop")

        except Exception as e:
            tool_warning = f" (tools failed: {type(e).__name__})"
            use_tools = False
    else:
        tool_warning = " (tools not supported)"

    # ── Console log ─────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"ADMIN QUERY: {message}")
    if project:
        print(f"WORKFLOW: Walkthrough → {project['title']}")
    print(f"CONFIG: model={model}  k={k}  temp={temp}{tool_warning}")
    print(f"Retrieved {len(ctx['documents'])} chunks in {ctx['retrieval_time_ms']:.0f}ms")
    for i, (doc, meta, dist) in enumerate(
        zip(ctx["documents"], ctx["metadatas"], ctx["distances"])
    ):
        sim = l2_to_cosine_sim(dist)
        print(f"  [{i+1}] sim={sim:.3f}  {meta.get('source','?')}  "
              f"section={meta.get('section','—')}  chars={len(doc)}")
    print(f"{'='*60}\n")

    # ── Stream the final answer ─────────────────────────────────
    active_config = {"top_k": k, "temperature": temp, "model": model}
    metrics_val = format_metrics_html(ctx, active_config, query_cost=0.0, workflow=workflow_label)
    chunks_val = format_chunks_html(ctx)
    metadata_val = format_metadata_json(ctx, active_config, walkthrough_info=walkthrough_info)
    embed_val = EMBED_VIZ_PLACEHOLDER

    stream = litellm.completion(
        model=model, messages=msgs, stream=True, temperature=temp,
    )
    collected = ""
    for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices[0].delta else None
        if delta:
            collected += delta
            yield collected, metrics_val, chunks_val, metadata_val, embed_val

    # ── Log cost after stream completes ─────────────────────────
    prompt_text = "\n".join(
        m.get("content", "") for m in msgs if isinstance(m.get("content"), str)
    )
    session_tracker.log_stream(model, prompt_text, collected)

    # Final yield with updated cost (+ diagram if walkthrough)
    query_cost = session_tracker.calls[-1].cost_usd if session_tracker.calls else 0.0
    metrics_val = format_metrics_html(ctx, active_config, query_cost=query_cost, workflow=workflow_label)
    metadata_val = format_metadata_json(ctx, active_config, walkthrough_info=walkthrough_info)

    # Gradio 6 MultimodalPostprocess format: {"text": ..., "files": [path_str]}
    chat_val = {"text": collected, "files": [diagram_path]} if diagram_path else collected
    yield chat_val, metrics_val, chunks_val, metadata_val, embed_val

    print(f"<<ADMIN RESPONSE>> model={model} cost=${query_cost:.6f}\n{collected[:200]}...\n")


# ═══════════════════════════════════════════════════════════════════
# GRADIO LAYOUT
# ═══════════════════════════════════════════════════════════════════

admin_css = """
.admin-badge {
    font-size: 11px; font-weight: 500;
    padding: 3px 10px; border-radius: 99px;
    background: #FAEEDA; color: #854F0B;
}
.admin-header { display: flex; align-items: center; gap: 12px; margin-bottom: 4px; }
.admin-header h2 { margin: 0; font-size: 1.3rem; }
.inspector-panel { min-height: 400px; }
.settings-accordion {
    border: 1px solid var(--border-color-primary, #ddd) !important;
    border-radius: 8px !important;
    margin-bottom: 4px !important;
}
.prompt-textbox textarea { font-family: monospace !important; font-size: 13px !important; }
/* Collection browser: tighter table rows + fixed height */
.browse-table table td { font-size: 12px !important; padding: 4px 8px !important; }
.browse-table table th { font-size: 12px !important; padding: 6px 8px !important; }
.browse-table { max-height: 420px; overflow-y: auto !important; }
"""


if __name__ == "__main__":

    # Pre-compute source filter choices from the cached collection
    _source_types = sorted(set(c["source_type"] for c in _ALL_CHUNKS))
    _source_filter_choices = ["All"] + _source_types
    _initial_browse = build_browse_dataframe()

    with gr.Blocks(title="Digital Twin — Admin") as demo:

        # ── Output components (render=False) ────────────────────
        metrics_display = gr.HTML(value=_initial_metrics(), render=False)
        chunks_display = gr.HTML(value=INITIAL_CHUNKS, render=False)
        metadata_display = gr.JSON(value=INITIAL_METADATA, render=False)
        embed_display = gr.HTML(value=EMBED_VIZ_PLACEHOLDER, render=False)

        # ── Config input components (render=False) ──────────────
        top_k_slider = gr.Slider(
            minimum=1, maximum=20, value=N_CHUNKS_RETRIEVE, step=1,
            label="Top-K (chunks to retrieve)",
            info="How many chunks ChromaDB returns.",
            render=False,
        )
        temp_slider = gr.Slider(
            minimum=0.0, maximum=2.0, value=1.0, step=0.05,
            label="Temperature",
            info="0 = deterministic, 2 = max creativity.",
            render=False,
        )
        model_dropdown = gr.Dropdown(
            choices=AVAILABLE_MODELS,
            value=LLM_MODEL,
            label="Model",
            info="provider/model — set API keys in env vars.",
            render=False,
        )
        prompt_textbox = gr.Textbox(
            value=system_message,
            label="System prompt",
            info="Edits are ephemeral — apply to next message only.",
            lines=8, max_lines=20,
            elem_classes=["prompt-textbox"],
            render=False,
        )

        # ── Header (always visible) ────────────────────────────
        gr.HTML(
            '<div class="admin-header">'
            "<h2>Barbara's Digital Twin</h2>"
            '<span class="admin-badge">Admin — multi-provider</span>'
            "</div>"
        )

        # ═══════════════════════════════════════════════════════
        # TOP-LEVEL TABS
        # ═══════════════════════════════════════════════════════
        with gr.Tabs():

            # ─── TAB 1: Chat + Inspector ────────────────────
            with gr.Tab("Chat + inspector"):

                metrics_display.render()

                with gr.Accordion(
                    "Settings — retrieval, generation, and provider config",
                    open=False,
                    elem_classes=["settings-accordion"],
                ):
                    with gr.Row():
                        with gr.Column(scale=1, min_width=140):
                            top_k_slider.render()
                        with gr.Column(scale=1, min_width=140):
                            temp_slider.render()
                        with gr.Column(scale=1, min_width=200):
                            model_dropdown.render()
                    prompt_textbox.render()

                with gr.Row(equal_height=False):
                    with gr.Column(scale=1):
                        chatbot = gr.Chatbot(
                            height="60vh", min_height=400,
                            placeholder=(
                                '<div style="text-align:center;padding:20px;">'
                                "<h3>Admin mode — multi-provider</h3>"
                                "<p>Ask a question. Switch providers in Settings to compare.</p>"
                                "</div>"
                            ),
                        )
                        example_questions = [
                            ["Walk me through a project", None, None, None, None],
                            ["What problems does Barbara solve?", None, None, None, None],
                            ["How was this digital twin built?", None, None, None, None],
                            ["Tell me about your knowledge graph work.", None, None, None, None],
                        ]
                        gr.ChatInterface(
                            fn=respond_admin,
                            chatbot=chatbot,
                            textbox=gr.Textbox(
                                placeholder="Ask the twin something...",
                                submit_btn=True, scale=7,
                            ),
                            examples=example_questions,
                            additional_inputs=[
                                top_k_slider, temp_slider,
                                model_dropdown, prompt_textbox,
                            ],
                            additional_outputs=[
                                metrics_display, chunks_display,
                                metadata_display, embed_display,
                            ],
                        )

                    with gr.Column(scale=1, elem_classes=["inspector-panel"]):
                        with gr.Tabs():
                            with gr.Tab("Chunks"):
                                chunks_display.render()
                            with gr.Tab("Raw metadata"):
                                metadata_display.render()
                            with gr.Tab("Embedding viz"):
                                embed_display.render()

            # ─── TAB 2: Collection Browser ──────────────────
            with gr.Tab("Collection browser"):

                # Stats summary
                gr.HTML(value=get_source_stats_html())

                # Browse controls
                with gr.Row():
                    browse_source_filter = gr.Dropdown(
                        choices=_source_filter_choices,
                        value="All",
                        label="Filter by source type",
                        scale=1,
                    )
                    browse_text_search = gr.Textbox(
                        placeholder="Search chunk text, source, section...",
                        label="Text search",
                        scale=2,
                    )
                    browse_btn = gr.Button("Filter", scale=0, min_width=80)

                # Semantic probe section
                with gr.Row():
                    probe_query = gr.Textbox(
                        placeholder="Type a topic to probe coverage (e.g. \"beekeeping\", \"knowledge graphs\")",
                        label="Coverage probe (semantic search across entire collection)",
                        scale=3,
                    )
                    probe_btn = gr.Button("Probe", scale=0, min_width=80, variant="primary")

                # Status bar
                browse_status = gr.Textbox(
                    value=f"{len(_ALL_CHUNKS)} chunks shown",
                    label="", show_label=False, interactive=False, max_lines=1,
                )

                # Results table
                browse_table = gr.Dataframe(
                    value=_initial_browse,
                    interactive=False,
                    wrap=True,
                    elem_classes=["browse-table"],
                )

                # Detail panel (updates on row select)
                chunk_detail = gr.HTML(value=NO_CHUNK_SELECTED)

                # ── Wire up events ──────────────────────────
                browse_btn.click(
                    fn=do_browse,
                    inputs=[browse_source_filter, browse_text_search],
                    outputs=[browse_table, browse_status, chunk_detail],
                )
                # Also trigger on Enter in the search box
                browse_text_search.submit(
                    fn=do_browse,
                    inputs=[browse_source_filter, browse_text_search],
                    outputs=[browse_table, browse_status, chunk_detail],
                )
                # Filter change triggers immediately
                browse_source_filter.change(
                    fn=do_browse,
                    inputs=[browse_source_filter, browse_text_search],
                    outputs=[browse_table, browse_status, chunk_detail],
                )

                # Semantic probe
                probe_btn.click(
                    fn=do_semantic_probe,
                    inputs=[probe_query],
                    outputs=[browse_table, browse_status, chunk_detail],
                )
                probe_query.submit(
                    fn=do_semantic_probe,
                    inputs=[probe_query],
                    outputs=[browse_table, browse_status, chunk_detail],
                )

                # Row select → detail
                browse_table.select(
                    fn=show_chunk_detail,
                    inputs=[browse_table],
                    outputs=[chunk_detail],
                )

    demo.launch(
        server_name="0.0.0.0",
        server_port=SERVER_PORT,
        show_error=True,
        css=admin_css,
    )
