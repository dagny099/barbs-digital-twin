import os
import sys
import subprocess
import types
import datetime
import time
from dotenv import load_dotenv
from openai import OpenAI
import gradio as gr
import litellm
import chromadb
import json
import re
import requests
import random
import base64
from dataclasses import dataclass, field
from datetime import datetime as dt
from featured_projects import (
      select_project_for_walkthrough,
      find_mentioned_project,
      get_diagram_path,
      build_walkthrough_context_block,
  )

#------ EXAMPLE PROMPTS -------
# Curated questions shown in the Explore Topics accordion, grouped by category.
CURATED_EXAMPLES = {
    "Professional": [
        "What led you from cognitive science to AI engineering?",
        "Can you explain how RAG works in simple terms?",
        "What kinds of problems get you most excited to solve?",
    ],
    "Bridge": [
        
        "What's a project you built that you're really proud of?",
        "How do you think about the connection between cognition and AI?",
        "What are you hoping to work on next in your career?",
    ],
    "Personal": [
        "How was this digital twin built?",
        "How did you get into beekeeping, and does it influence your work?",
        "What are you working on these days that's lighting you up?",
#        "What's something you're learning right now just for fun?",
    ],
}

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

load_dotenv(override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY is None:
    raise Exception("API key is missing")

# Model used for all LLM completions. Override via env to switch without code changes.
# Auto-prefixes "openai/" if no provider specified (backward compatibility).
_raw_model = os.getenv("LLM_MODEL", "gpt-4.1")
LLM_MODEL = _raw_model if "/" in _raw_model else f"openai/{_raw_model}"

# Temperature for LLM completions. 0.7 is a reasonable default for personality+accuracy balance.
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))

N_CHUNKS_RETRIEVE = int(os.getenv("N_CHUNKS_RETRIEVE", 10))

# Controls visibility of settings panel in UI (default: hidden for production)
SHOW_SETTINGS_PANEL = os.getenv("SHOW_SETTINGS_PANEL", "false").lower() == "true"

MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", 14))  # Last 14 turns (7 user + 7 assistant)

# Local server port. HF Spaces ignores this and always uses 7860.
SERVER_PORT = int(os.getenv("PORT", 7860))

# ═══════════════════════════════════════════════════════════════════
# SENSITIVITY GATING — Passphrase-based audience detection
# ═══════════════════════════════════════════════════════════════════
#
# These phrases, when detected in the conversation, unlock progressively
# more personal content from the knowledge base. Detection is
# case-insensitive and checks the ENTIRE conversation history (not just
# the current message), so a phrase said in turn 1 keeps content
# unlocked for the rest of the session.
#
# Tier escalation: public → personal → inner_circle
# Once a tier is unlocked, it stays unlocked for the session.

# Inner circle: phrases that indicate close personal connection.
# These unlock ALL content (public + personal + inner_circle).
INNER_CIRCLE_PHRASES = [
    "somos un equipo",
    "ni casada, ni con hijos",
    "baba",                        # family nickname
    # Add more as needed — family sayings, insider references, etc.
]

# Personal: phrases that suggest familiarity (but not inner circle).
# These unlock public + personal content.
PERSONAL_PHRASES = [
    "cvcl",
    "easy button",
    "bilingual lady communicators",
    "daisy 5k",
    "science academy",
    "deans scholars",
    "toastmasters"
    # Add more — labmate names, Toastmasters references, etc.
]


def detect_audience_tier(message: str, history: list) -> str:
    """Scan current message + conversation history for passphrase signals.

    Returns the highest tier detected: 'inner_circle', 'personal', or 'public'.

    The detection is deliberately simple: case-insensitive substring match.
    This is NOT security — it's a content-appropriateness gate. A determined
    person could guess the phrases, but the failure mode (seeing personal
    content) is low-stakes compared to, say, authentication.

    Args:
        message: Current user message
        history: Gradio conversation history (list of dicts with 'role' and 'content')

    Returns:
        One of 'public', 'personal', or 'inner_circle'
    """
    # Build a single lowercase string from all user messages in the conversation
    all_user_text = message.lower()
    for turn in history:
        if turn.get("role") == "user":
            content = turn.get("content", "")
            if isinstance(content, str):
                all_user_text += " " + content.lower()

    # Check inner circle first (highest tier)
    for phrase in INNER_CIRCLE_PHRASES:
        if phrase.lower() in all_user_text:
            return "inner_circle"

    # Then personal
    for phrase in PERSONAL_PHRASES:
        if phrase.lower() in all_user_text:
            return "personal"

    return "public"


def build_sensitivity_filter(tier: str) -> dict | None:
    """Build a ChromaDB `where` filter for the given audience tier.

    Tier escalation:
        'public'       → only chunks with sensitivity='public'
        'personal'     → chunks with sensitivity='public' OR 'personal'
        'inner_circle' → all chunks (no filter needed)

    Args:
        tier: One of 'public', 'personal', 'inner_circle'

    Returns:
        A ChromaDB `where` dict, or None if no filtering is needed.
    """
    if tier == "inner_circle":
        return None  # No filter — retrieve from everything
    elif tier == "personal":
        return {"sensitivity": {"$in": ["public", "personal"]}}
    else:
        return {"sensitivity": {"$eq": "public"}}

# ═══════════════════════════════════════════════════════════════════
# MULTI-PROVIDER MODEL REGISTRY
# ═══════════════════════════════════════════════════════════════════

AVAILABLE_MODELS = [
    # OpenAI
    "openai/gpt-5.4-mini",  # Input: $0.75, Output $4.50    (short-context, <270K tokens; mini-version for simpler tasks)
    "openai/gpt-5.4-nano",  # Input: $0.20, Output $1.25    (short-context, <270K tokens; nano-version, low cost model)
    "openai/gpt-5.1",       # Input: $1.25, Output $10.00
    "openai/gpt-5-mini",    # Input: $0.25, Output $2.00
    "openai/gpt-5-nano",    # Input: $0.005, Output $0.40
    "openai/gpt-4.1",      # Input: $2.00, Output $8.00   (128K tokens; High‑quality 128K‑context model; widely used)
    #"openai/gpt-4.1-mini",  # Input: $0.40, Output $1.60
    #"openai/gpt-o4-mini",   # Input: $1.10, Output $4.40
    # Anthropic
    "anthropic/claude-haiku-4.5",    # Input: $1.00, Output $5.00  (cost-efficient for high-volume work-loads)
    "anthropic/claude-haiku-3.5",    # Input: $0.80, Output $5.00
    "anthropic/claude-haiku-3",      # Input: $0.25, Output $1.25
    # Google
    "gemini/gemini-3.1-flash-lite-preview",  # Input: $0.25, Output $1.50
    "gemini/gemini-2.5-flash",               # Input: $0.30, Output $2.50   (multi-modal)
    "gemini/gemini-2.5-flash-lite",          # Input: $0.10, Output $0.40   (multi-modal)
    # Ollama (local)
    "ollama/llama3.2",
    "ollama/mistral",
]

MODELS_WITHOUT_TOOL_SUPPORT = {
    "ollama/mistral",
}

def model_supports_tools(model_name: str) -> bool:
    """Check if a model supports tool/function calling."""
    return model_name not in MODELS_WITHOUT_TOOL_SUPPORT

# OpenAI client — used ONLY for embeddings (not chat)
client = OpenAI(api_key=OPENAI_API_KEY)

# Pushover notifications
pushover_user = os.getenv("PUSHOVER_USER")
pushover_token = os.getenv("PUSHOVER_TOKEN")
pushover_url = "https://api.pushover.net/1/messages.json"


# IBM Plex Sans — modern, science-forward, friendly. Loaded from Google Fonts.
font_head = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">'
)


# Google Analytics tracking code
ga_head = """
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-8QPFV58YYL"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());

  gtag('config', 'G-8QPFV58YYL');
</script>
"""

# Startup: restore DB from HF Hub if the directory is missing entirely.
# Must happen before ChromaDB opens the path, or the pull would conflict.
if not os.path.exists(".chroma_db_DT"):
    from db_sync import pull_db
    pull_db()

chroma_client = chromadb.PersistentClient(path=".chroma_db_DT")
collection = chroma_client.get_or_create_collection(name="barb-twin")

# If still empty (pull failed or very first run), build from scratch then cache.
if collection.count() == 0:
    print("Knowledge base is empty — running scripts/ingest.py --all ...")
    subprocess.run([sys.executable, "scripts/ingest.py", "--all"], check=True)
    from db_sync import push_db
    push_db()
    print("Ingestion complete.")



def handle_vote(data: gr.LikeData, history, request: gr.Request = None):
    """Called when a visitor clicks thumbs up or thumbs down.

    Logs to the same query_log.jsonl as _log_query, enriched with:
      - The user message that produced the voted-on response
      - Model, temperature, and cost from the session tracker
    """
    try:
        # Find the user message that preceded this assistant response.
        # data.index is the position in the history list.
        user_message = None
        if history and isinstance(data.index, int):
            # Walk backward from the voted message to find the preceding user turn
            for i in range(data.index - 1, -1, -1):
                msg = history[i]
                if isinstance(msg, dict) and msg.get("role") == "user":
                    user_message = msg.get("content", "")[:300]
                    break

        # Pull model/cost from the most recent session tracker entry
        last_call = session_tracker.calls[-1] if session_tracker.calls else None

        entry = {
            "ts":               datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "event":            "vote",
            "session_id":       _get_session_id(request),
            "liked":            data.liked,
            "message_index":    data.index,
            "user_message":     _redact_log_text(user_message),
            "response_snippet": _build_response_preview(_redact_log_text(str(data.value)), n=300),
            "model":            last_call.model if last_call else _current_settings.get("model"),
            "temperature":      _current_settings.get("temperature"),
            "cost_usd":         last_call.cost_usd if last_call else None,
            "is_owner_traffic": _get_owner_flag(request),
        }
        with open(_QUERY_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        print(f"{'👍' if data.liked else '👎'} message #{data.index}")
    except Exception:
        pass  # logging must NEVER break the app

#----------------------


# My favicon (local png)
with open("assets/bee_barb.png", "rb") as f:
      b64 = base64.b64encode(f.read()).decode()
FAVICON_HEAD = f'<link rel="icon" type="image/png" href="data:image/png;base64,{b64}">'

custom_css = """
/* ── Soft intelligent warmth palette ──────────────────────────── */
:root {
    --bg-card: #FFFDF9;
    --bg-card-soft: #FCF7F0;
    --bg-chat-top: #E8F2EE;
    --bg-chat-bottom: #F3E8DA;
    --bg-mid: #EDF2EC;
    --bg-tint: #F3ECE2;
    --text-main: #24313A;
    --text-muted: #61707A;
    --text-soft: #7D8B94;
    --border-soft: #D9DDD6;
    --border-strong: #BEC9C4;
    --accent: #ff5e00;
    --accent-strong: #256B68;
    --accent-deep: #1F565B;
    --accent-soft: #E2F0EC;
    --warm: #C88B4A;
    --warm-soft: #F6E6D2;
    --warm-glow: rgba(200, 139, 74, 0.14);
    --teal-glow: rgba(47, 127, 123, 0.14);
    --shadow-soft: 0 10px 28px rgba(40, 49, 56, 0.08);
    --shadow-md: 0 14px 36px rgba(40, 49, 56, 0.12);
    --shadow-hover: 0 16px 36px rgba(34, 42, 48, 0.14);
    --radius-xl: 22px;
    --radius-lg: 18px;
    --radius-md: 14px;
    --radius-sm: 12px;
}

.dark {
    --bg-card: #22313A;
    --bg-card-soft: #2A3A44;
    --bg-chat-top: #204845;
    --bg-chat-bottom: #314037;
    --bg-mid: #243532;
    --bg-tint: #2A3942;
    --text-main: #EAF0EE;
    --text-muted: #B5C4C0;
    --text-soft: #97AAA5;
    --border-soft: rgba(226, 236, 232, 0.12);
    --border-strong: rgba(226, 236, 232, 0.18);
    --accent: #7DC7BC;
    --accent-strong: #9AD9CF;
    --accent-deep: #C1ECE5;
    --accent-soft: rgba(125, 199, 188, 0.12);
    --warm: #E0A86A;
    --warm-soft: rgba(224, 168, 106, 0.14);
    --warm-glow: rgba(224, 168, 106, 0.16);
    --teal-glow: rgba(114, 184, 175, 0.18);
    --shadow-soft: 0 10px 28px rgba(0, 0, 0, 0.28);
    --shadow-md: 0 14px 36px rgba(0, 0, 0, 0.34);
    --shadow-hover: 0 16px 36px rgba(0, 0, 0, 0.42);
}

* { font-family: 'IBM Plex Sans', sans-serif !important; }
html, body {
    margin: 0 !important;
    padding: 0 !important;
    min-height: 100% !important;
    background-color: var(--bg-chat-top) !important;
    background-image: linear-gradient(180deg, var(--bg-chat-top) 0%, var(--bg-mid) 34%, var(--bg-chat-bottom) 100%) !important;
    background-repeat: no-repeat !important;
    background-attachment: fixed !important;
    color: var(--text-main) !important;
}

.gradio-container {
    min-height: 100vh !important;
    background: transparent !important;
    margin: 0 auto !important;
    padding: 20px 16px 24px !important;
    position: relative;
    z-index: 1;
    width: 100% !important;
    max-width: 100% !important;
}

body::before {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    background:
        radial-gradient(circle at 12% 8%, var(--warm-glow) 0%, transparent 32%),
        radial-gradient(circle at 88% 10%, var(--teal-glow) 0%, transparent 28%);
    z-index: 0;
}

.gr-block,
.gr-box,
.gr-panel,
.block,
.contain,
#explore-accordion,
.settings-accordion {
    border-radius: var(--radius-xl) !important;
}

/* ── Header ───────────────────────────────────────────────────── */
.title-row {
    display: flex !important;
    align-items: center !important;
    gap: 16px !important;
    margin: 0 !important;
}
.title-row img {
    width: 70px !important;
    height: 70px !important;
    border-radius: 50% !important;
    object-fit: cover !important;
    border: 3px solid rgba(47, 127, 123, 0.24) !important;
    box-shadow: 0 8px 18px rgba(36, 49, 58, 0.18) !important;
    flex-shrink: 0 !important;
}
.title-row h2 {
    margin: 0 !important;
    font-size: 1.75rem !important;
    line-height: 1.0 !important;
    font-weight: 700 !important;
    letter-spacing: -0.025em !important;
    color: var(--text-main) !important;
}
.title-subtitle {
    margin: 0px !important;
    color: var(--text-muted) !important;
    font-size: 1.03rem !important;
}

/* ── Hide leftover chrome ─────────────────────────────────────── */
.chatbot label,
.chatbot .label-wrap,
footer {
    display: none !important;
}

/* ── Chatbot shell ────────────────────────────────────────────── */
.chatbot {
    position: relative !important;
    overflow: hidden !important;
    background: transparent !important;
}
.chatbot .message,
.chatbot .wrap,
.chatbot .bubble-wrap,
.chatbot .prose,
.chatbot .prose p,
.chatbot .prose li,
.chatbot .prose span {
    color: var(--text-main) !important;
}
.chatbot .prose strong,
.chatbot .prose b {
    font-weight: 800 !important;
    color: var(--text-main) !important;
}

.chatbot.block {
    padding-top: 0px !important;
    margin-top: 0px !important;
    border: none !important;
    background: transparent !important;
}
.chatbot .wrapper,
.chatbot > div {
    background: transparent !important;
}


/* Main chat panel: this should own the cream background and the single border */
div[role="log"][aria-label="chatbot conversation"] {
    background: #FBF7F1 !important;
    border: 1px solid rgba(190, 201, 196, 0.88) !important;
    border-radius: 22px !important;
    padding: 0 !important;
    margin: 0 !important;
    box-shadow: none !important;
}

/* Flatten inner conversation wrappers so they do not create a second card */
div[role="log"][aria-label="chatbot conversation"] .bubble-wrap,
div[role="log"][aria-label="chatbot conversation"] .message-wrap {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin: 0 !important;
}

.dark div[role="log"][aria-label="chatbot conversation"] {
    background: #F3EFE8 !important;
    border-color: rgba(112, 135, 132, 0.38) !important;
}

/* Individual message bubbles */
.chatbot .message-row .message {
    border-radius: var(--radius-lg) !important;
}
/* Bot message bubble */
.chatbot .bot.message-row .message {
    background: rgba(255, 253, 249, 0.72) !important;
    border: 1px solid var(--border-soft) !important;
}
.dark .chatbot .bot.message-row .message {
    background: rgba(37, 49, 58, 0.58) !important;
    border: 1px solid rgba(138, 164, 160, 0.18) !important;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12) !important;
}

/* User message bubble */
.chatbot .user.message-row .message {
    background: var(--accent-soft) !important;
    border: 1px solid rgba(47, 127, 123, 0.18) !important;
}
.dark .chatbot .user.message-row .message {
    background: rgba(125, 199, 188, 0.10) !important;
    border: 1px solid rgba(125, 199, 188, 0.18) !important;
}

.chatbot-header {
    text-align: center;
    margin-bottom: 10px;
    color: var(--text-main);
    font-size: 1.65rem;
    line-height: 1.14;
    font-weight: 700;
    letter-spacing: -0.025em;
}
.chatbot-subtitle {
    text-align: center;
    font-size: 1.15rem;
    line-height: 1.68;
    color: var(--text-muted);
    max-width: 630px;
    margin: 0 auto;
}

.dark .chatbot-header {
    color: #2A3942 !important;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.18) !important;
}

.dark .chatbot-subtitle {
    color: #61707A !important;
    max-width: 580px !important;
}

/* ── Clean Consolidated Input Row ── */

/* 1. The Parent "Pill" Container */
.gradio-container form > div {
    display: flex !important;
    align-items: center !important;
    background: rgba(255, 253, 249, 0.96) !important;
    border-radius: 28px !important;
    padding: 2px 14px 2px 4px !important;
    border: 1px solid var(--border-strong) !important;
    box-shadow: 0 6px 18px rgba(36, 49, 58, 0.06) !important;
    gap: 0px !important;
}

/* 2. The Textarea Reset */
.gradio-container textarea,
.gradio-container input[type="text"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: var(--text-main) !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 16px !important;
    font-weight: 400 !important;    
    flex-grow: 1 !important;
    padding-top: 16px !important;
    padding-bottom: 12px !important;
    padding-left: 16px !important;
    min-height: 56px !important;
    line-height: 1.5 !important;
}

/* Placeholder color */
.gradio-container textarea::placeholder {
    color: rgba(47, 127, 123, 0.65) !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 16px !important;
    font-weight: 500 !important;
    letter-spacing: 0.01em !important;
}
.dark .gradio-container textarea::placeholder {
    color: rgba(154, 217, 207, 0.66) !important;
}

/* 3. The Submit Button */
button[aria-label="Submit"],
button.submit-button {
    background: transparent !important;
    border: none !important;
    color: var(--accent-strong) !important;
    border-radius: 50% !important;
    height: 42px !important;
    width: 42px !important;
    min-width: 42px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    transition: transform 0.15s ease, color 0.15s ease !important;
    box-shadow: none !important;
}

button[aria-label="Submit"]:hover {
    transform: scale(1.1) !important;
    color: var(--accent-strong) !important;
}

/* 4. Global Wrappers Reset */
.gradio-container .gr-form,
.gradio-container form {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0px !important;
    margin-top: 16px !important;
}

/* 5. Dark Mode — input pill */
.dark .gradio-container form > div {
    background: linear-gradient(180deg, rgba(34, 47, 56, 0.96) 0%, rgba(29, 41, 49, 0.96) 100%) !important;
    border: 1px solid rgba(125, 199, 188, 0.18) !important;
    box-shadow: 0 8px 22px rgba(0, 0, 0, 0.18) !important;
}

.dark .gradio-container form > div:focus-within {
    border-color: rgba(154, 217, 207, 0.44) !important;
    box-shadow: 0 0 0 4px rgba(125, 199, 188, 0.10), 0 10px 26px rgba(0, 0, 0, 0.22) !important;
}

.dark .gradio-container textarea {
    color: #E8F1EE !important;
}

.dark button[aria-label="Submit"] {
    color: #8FD0C7 !important;
}

.dark button[aria-label="Submit"]:hover {
    color: #B3E2DA !important;
}

/* ── Example cards ────────────────────────────────────────────── */
.example-content {
    align-items: center !important;
}
.examples {
    font-family: 'IBM Plex Sans', sans-serif !important;
    gap: 13px !important;
}
.examples .example {
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
}
.examples .example img {
    width: 34px !important;
    height: 34px !important;
    display: block !important;
    margin: 0 auto 10px auto !important;
    opacity: 0.84 !important;
}
.examples button {
    text-align: center !important;
    justify-content: center !important;
    flex-direction: column !important;
    align-items: center !important;
    background: linear-gradient(180deg, rgba(255,253,249,0.96) 0%, rgba(250,244,236,0.96) 100%) !important;
    border: 1px solid rgba(190, 201, 196, 0.95) !important;
    border-radius: 18px !important;
    color: var(--text-main) !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 1.1rem !important;
    font-weight: 500 !important;
    line-height: 1.45 !important;
    padding: 16px !important;
    margin-bottom: 64px;
    white-space: normal !important;
    height: auto !important;
    min-height: 85px !important;
    box-shadow: 0 6px 14px rgba(44, 52, 57, 0.06) !important;
    transition: all 0.16s ease !important;
}
.examples button span {
    display: block !important;
    width: 100% !important;
    text-align: center !important;
}
.examples button:hover {
    border-color: rgba(47, 127, 123, 0.68) !important;
    background: linear-gradient(180deg, #FFFDF9 0%, #F6EEE4 100%) !important;
    transform: translateY(-2px) !important;
    box-shadow: var(--shadow-hover) !important;
}
/* Dark mode example cards */
.dark .examples button {
    background: linear-gradient(180deg, var(--bg-card) 0%, var(--bg-card-soft) 100%) !important;
    border-color: var(--border-strong) !important;
    color: var(--accent) !important;
}
.dark .examples button:hover {
    border-color: var(--accent) !important;
    background: linear-gradient(180deg, var(--bg-card-soft) 0%, var(--bg-card) 100%) !important;
}

/* ── Explore topics ───────────────────────────────────────────── */
#explore-accordion {
    background: linear-gradient(180deg, rgba(255,253,249,0.96) 0%, rgba(250,246,240,0.96) 100%) !important;
    border: 1px solid var(--border-soft) !important;
    box-shadow: var(--shadow-soft) !important;
    overflow: hidden !important;
    min-width: 100% !important;
    width: 100% !important;
}
/* Dark mode explore accordion */
.dark #explore-accordion {
    background: linear-gradient(180deg, var(--bg-card) 0%, var(--bg-card-soft) 100%) !important;
}
/* Force accordion content row to maintain width even when collapsed */
#explore-accordion .gr-row,
#explore-accordion > div > div {
    width: 100% !important;
    min-width: 100% !important;
}
#explore-accordion .label-wrap span,
#explore-accordion > div:first-child span {
    font-weight: 700 !important;
    font-size: 1.03rem !important;
    color: var(--text-main) !important;
    letter-spacing: -0.01em !important;
}
.sidebar-category {
    margin-top: 10px !important;
    margin-bottom: 8px !important;
    font-size: 13px !important;
    color: var(--text-muted) !important;
}
.sidebar-btn {
    width: 100% !important;
    text-align: left !important;
    padding: 11px 12px 11px 14px !important;
    border-radius: 14px !important;
    font-size: 14.5px !important;
    line-height: 1.42 !important;
    margin-bottom: 8px !important;
    white-space: normal !important;
    height: auto !important;
    min-height: unset !important;
    overflow: visible !important;
    border: 1px solid rgba(190, 201, 196, 0.86) !important;
    background: rgba(255,253,249,0.96) !important;
    color: var(--text-main) !important;
    box-shadow: 0 4px 12px rgba(44, 52, 57, 0.045) !important;
    transition: all 0.15s ease !important;
}
.sidebar-btn span {
    overflow: visible !important;
    display: block !important;
}
.sidebar-btn:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 10px 20px rgba(44, 52, 57, 0.09) !important;
}
/* Dark mode sidebar buttons */
.dark .sidebar-btn {
    background: var(--bg-card-soft) !important;
    border-color: var(--border-soft) !important;
}
.btn-professional {
    border-left: 4px solid rgba(47, 127, 123, 0.55) !important;
}
.btn-professional:hover {
    border-color: rgba(47, 127, 123, 0.80) !important;
    background: linear-gradient(90deg, rgba(226,240,236,0.92) 0%, rgba(255,253,249,0.98) 16%) !important;
}
.dark .btn-professional:hover {
    background: linear-gradient(90deg, rgba(47,127,123,0.15) 0%, var(--bg-card-soft) 16%) !important;
}
.btn-bridge {
    border-left: 4px solid rgba(70, 112, 128, 0.40) !important;
}
.btn-bridge:hover {
    border-color: rgba(70, 112, 128, 0.65) !important;
    background: linear-gradient(90deg, rgba(231,238,241,0.95) 0%, rgba(255,253,249,0.98) 16%) !important;
}
.dark .btn-bridge:hover {
    background: linear-gradient(90deg, rgba(70,112,128,0.15) 0%, var(--bg-card-soft) 16%) !important;
}
.btn-personal {
    border-left: 4px solid rgba(200, 139, 74, 0.55) !important;
}
.btn-personal:hover {
    border-color: rgba(200, 139, 74, 0.82) !important;
    background: linear-gradient(90deg, rgba(246,230,210,0.96) 0%, rgba(255,253,249,0.98) 16%) !important;
}
.dark .btn-personal:hover {
    background: linear-gradient(90deg, rgba(200,139,74,0.15) 0%, var(--bg-card-soft) 16%) !important;
}

/* ── Contact CTA ─────────────────────────────────────────────── */
.title-header-wrap {
    position: relative !important;
}
.contact-cta-link {
    display: inline-block !important;
    color: var(--accent-strong) !important;
    font-size: 0.9rem !important;
    font-weight: 500 !important;
    text-decoration: underline !important;
    text-underline-offset: 3px !important;
    text-decoration-color: rgba(47,127,123,0.42) !important;
    transition: all 0.15s ease !important;
    white-space: nowrap !important;
    padding: 5px 12px 0px 12px !important;
    border-radius: 8px !important;
}
.contact-cta-link:hover {
    color: var(--accent) !important;
    text-decoration-color: rgba(47,127,123,0.82) !important;
    background: rgba(47,127,123,0.06) !important;
}
.dark .contact-cta-link {
    color: var(--accent-lighter) !important;
    text-decoration-color: rgba(125,199,188,0.48) !important;
}
.dark .contact-cta-link:hover {
    color: var(--accent-light) !important;
    text-decoration-color: rgba(125,199,188,0.88) !important;
    background: rgba(125,199,188,0.08) !important;
}

.owner-traffic-row {
    display: flex !important;
    justify-content: flex-end !important;
    margin-top: 16px !important;
    opacity: 0.18 !important;
    transition: opacity 0.16s ease !important;
}

.owner-traffic-toggle {
    padding: 0 !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    min-height: unset !important;
}

.owner-traffic-toggle label,
.owner-traffic-toggle .wrap {
    gap: 6px !important;
}

.owner-traffic-toggle span,
.owner-traffic-toggle label {
    color: var(--text-soft) !important;
    font-size: 0.72rem !important;
    line-height: 1.2 !important;
    text-decoration: underline !important;
    text-underline-offset: 2px !important;
    text-decoration-color: rgba(97, 112, 122, 0.35) !important;
}

.owner-traffic-toggle input[type="checkbox"] {
    accent-color: var(--accent) !important;
    width: 12px !important;
    height: 12px !important;
    opacity: 0.68 !important;
}

.owner-traffic-row:hover,
.owner-traffic-row:focus-within {
    opacity: 0.52 !important;
}

.dark .owner-traffic-toggle span,
.dark .owner-traffic-toggle label {
    text-decoration-color: rgba(181, 196, 192, 0.3) !important;
}

.settings-accordion {
    border: 1px solid var(--border-soft) !important;
    margin: 8px 0 !important;
    background: linear-gradient(180deg, rgba(255,253,249,0.96) 0%, rgba(248,243,236,0.96) 100%) !important;
    box-shadow: 0 4px 12px rgba(44, 52, 57, 0.04) !important;
}
.dark .settings-accordion {
    background: linear-gradient(180deg, var(--bg-card) 0%, var(--bg-card-soft) 100%) !important;
}
#cost-display {
    opacity: 0.84;
    transition: opacity 0.2s ease;
}
#cost-display:hover {
    opacity: 1.0;
}

/* Dark mode icon inversion */
.dark .examples .example img,
.dark .sidebar-category img {
    filter: brightness(0) invert(1) !important;
    opacity: 0.84 !important;
}

@media (max-width: 768px) {
    .gradio-container {
        padding: 0px 12px 22px !important;
    }
    .title-row h1 {
        font-size: 1.75rem !important;
    }
    .title-row img {
        width: 58px !important;
        height: 58px !important;
    }
    .chatbot-header {
        font-size: 1.42rem;
    }
    .chatbot-subtitle {
        font-size: 0.98rem;
    }
    .examples button {
        min-height: 84px !important;
        padding: 16px 12px !important;
    }
}
"""


print(f"✅ Collection ready: {collection.count()} chunks loaded")

#------ Tools -----------
# Function that sends notification via pushover app
def send_notification(message: str):
    """Send a Pushover notification and return an observable tool result.

    The optional PUSHOVER_DEVICE env var can target one device. If it is not
    set, Pushover delivers to the user's active/default devices. Returning a
    structured success/failure string lets the LLM continue gracefully and lets
    the app mark tool-related failures in the query log via `_tool_error`.
    """
    if not pushover_user or not pushover_token:
        return "Notification failed: missing PUSHOVER_USER or PUSHOVER_TOKEN"

    payload = {
        "user": pushover_user,
        "token": pushover_token,
        "message": message,
    }

    pushover_device = os.getenv("PUSHOVER_DEVICE")
    if pushover_device:
        payload["device"] = pushover_device

    try:
        resp = requests.post(pushover_url, data=payload, timeout=10)
        try:
            data = resp.json()
        except ValueError:
            return f"Notification failed: HTTP {resp.status_code}; non-JSON response"

        if not resp.ok or data.get("status") != 1:
            return f"Notification failed: HTTP {resp.status_code}; errors={data.get('errors', [])}"

        return f"Notification message was sent. Pushover request_id={data.get('request')}"
    except requests.RequestException as e:
        return f"Notification failed: {type(e).__name__}: {e}"

# Function simulating roling a single six-sided die
def dice_roll():
    return random.randint(1,6)

# DESCRIBE THE FUNCTIONS TO THE LLM

dice_roll_function = {
    'name': 'dice_roll',
    'description': 'Simulates rolling a single six-sided die and returns the result of that roll. Use this when the user wants to roll a die for games, decisions, or random numbers.',
    'parameters': {
        'type': 'object',
        'properties': {},
        'required': []
    }
}

send_notification_function = {
    'name': 'send_notification',
    'description': """
                Sends a message to send as a push notification to the real Barbara's phone via Pushover. 
                Use this when: 1) Someone wants to get in touch, hire, or collaborate - ask for their name and contact details.
                2) You don't know the answer to a question about Barbara -- send AUTOMATICALLY without asking, include the question
                so the real Barbara can consider adding this information to the twin knowledge base later.
                """,
    'parameters': {
        'type': 'object',
        'properties': {
            'message': {
                'type': 'string',
                'description': 'The notification message to send to the users device'
            }
        },
        "required": ["message"]
    }
}


tools = [
    {"type":"function", "function": send_notification_function},
    {"type":"function", "function": dice_roll_function}
]
#------------------------


_QUERY_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "query_log.jsonl")
_session_owner_flags: dict[str, bool] = {}

def _get_session_id(request: gr.Request | None) -> str | None:
    """
    Anonymous Gradio session identifier.
    Good enough for grouping turns from the same browser session/tab.
    It is lightweight, but not meant to identify a real person.
    """
    return getattr(request, "session_hash", None) if request else None


def _get_turn_index(history) -> int:
    """
    Current user turn number.

    Gradio passes prior chat history into respond_ai(), but the current
    user message is NOT in history yet, so this is:
        (# prior user messages) + 1
    """
    history = history or []
    return sum(
        1
        for msg in history
        if isinstance(msg, dict) and msg.get("role") == "user"
    ) + 1


def _set_owner_flag(value, request: gr.Request | None = None):
    """Persist the current session's owner-traffic flag in server memory."""
    owner_flag = bool(value)
    session_id = _get_session_id(request)
    if session_id:
        _session_owner_flags[session_id] = owner_flag
    return owner_flag


def _reset_owner_flag(request: gr.Request | None = None):
    """Reset the current session's owner-traffic flag on page load."""
    return _set_owner_flag(False, request)


def _get_owner_flag(request: gr.Request | None = None) -> bool:
    """Return the owner-traffic flag for the current Gradio session."""
    session_id = _get_session_id(request)
    if not session_id:
        return False
    return bool(_session_owner_flags.get(session_id, False))


def _compute_similarity_stats(distances):
    """Convert L2 distances to cosine similarity scores. Returns avg and max."""
    if not distances:
        return {"avg": 0.0, "max": 0.0}
    # L2 to cosine similarity: sim = 1 - (dist^2 / 2)
    # Clamp to [0, 1] to handle floating point edge cases
    sims = [max(0.0, min(1.0, 1.0 - (d * d / 2.0))) for d in distances]
    return {
        "avg": round(sum(sims) / len(sims), 3),
        "max": round(max(sims), 3),
    }


def _redact_log_text(text: str | None) -> str:
    """Lightweight redaction for log storage: emails and phone numbers."""
    if not text:
        return ""
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[EMAIL]', text)
    text = re.sub(
        r'\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b',
        '[PHONE]',
        text,
    )
    return text


def _build_response_preview(text: str | None, n: int = 300) -> str:
    """Compact preview stored with the log row for quick scanning."""
    if not text:
        return ""
    text = text.replace("\n", " ").strip()
    return text if len(text) <= n else text[: n - 1] + "…"

def _log_query(message, project_title, walkthrough, tool_name, had_error, 
               model, temperature, n_chunks_retrieved, response_chars,
               workflow_type, latency_ms, chunk_similarity_avg, chunk_similarity_max,
               provider, cost_usd, prompt_tokens, completion_tokens,
               audience_tier="public", session_id=None, turn_index=None, empty_response=False,
               is_owner_traffic=False, assistant_response=None):
    """Append one query record to the JSONL log. Fails silently — must never affect the user."""
    try:
        entry = {
            # Original fields
            "ts":          datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "session_id":  session_id,
            "turn_index":  turn_index,
            "message":     _redact_log_text(message),
            "assistant_response": _redact_log_text(assistant_response),
            "assistant_response_preview": _build_response_preview(_redact_log_text(assistant_response)),
            "project":     project_title,
            "walkthrough": walkthrough,
            "audience_tier":  audience_tier,
            "is_owner_traffic": bool(is_owner_traffic),
            "tool_called": tool_name is not None,
            "tool_name":   tool_name,
            "had_error":   had_error,
            "empty_response": bool(empty_response),

            # Phase 1: Model & config
            "model":       model,
            "temperature": temperature,

            # Phase 1: RAG metrics
            "n_chunks_retrieved": n_chunks_retrieved,
            "n_chunks_config":    N_CHUNKS_RETRIEVE,

            # Phase 1: Response metrics
            "response_chars": response_chars,
            "latency_ms":     latency_ms,
            "workflow":       workflow_type,

            # Phase 2: Quality metrics
            "chunk_similarity_avg": chunk_similarity_avg,
            "chunk_similarity_max": chunk_similarity_max,

            # Provider and cost tracking
            "provider": provider,
            "cost_usd": cost_usd,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }
        with open(_QUERY_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # logging must NEVER break the app


# ═══════════════════════════════════════════════════════════════════
# SESSION COST TRACKER
# ═══════════════════════════════════════════════════════════════════

@dataclass
class CallRecord:
    timestamp: str
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    cost_usd: float
    call_type: str  # "chat", "tool_loop", "chat_stream", "embedding"

@dataclass
class SessionTracker:
    """Tracks token usage and cost across messages in one session."""
    calls: list = field(default_factory=list)

    def log_stream(self, model: str, prompt_text: str, completion_text: str):
        """Log a streaming completion by estimating cost from text."""
        try:
            cost = litellm.completion_cost(
                model=model, prompt=prompt_text, completion=completion_text,
            )
        except Exception:
            cost = 0.0

        self.calls.append(CallRecord(
            timestamp=dt.now().isoformat(),
            model=model,
            prompt_tokens=None,
            completion_tokens=None,
            cost_usd=cost,
            call_type="chat_stream",
        ))

    def summary(self) -> dict:
        # Streamed LiteLLM calls currently have unknown token counts, represented
        # as None. Treat them as zero for display-only session totals.
        total_prompt = sum(c.prompt_tokens or 0 for c in self.calls)
        total_completion = sum(c.completion_tokens or 0 for c in self.calls)
        total_cost = sum(c.cost_usd for c in self.calls)
        return {
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "total_tokens": total_prompt + total_completion,
            "total_cost_usd": round(total_cost, 6),
            "total_calls": len(self.calls),
        }



session_tracker = SessionTracker()


#------ Tool Handler -----------
def handle_tool_call(tool_calls):
    tool_results = []
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        #print(f"Calling fucnction {function_name}") #For future debuggins

        if function_name == 'send_notification':
            content = send_notification(args['message'])
        elif function_name == 'dice_roll':
            content = f"Dice roll was: {dice_roll()}"
        else:
            content = f"Unknown function: {function_name}"

        tool_call_result = {
            "role": "tool",
            "content": content,
            "tool_call_id": tool_call.id
        }
        tool_results.append(tool_call_result)
    return tool_results

#-------------------------------


#------ SYSTEM MESSAGE ----
with open("SYSTEM_PROMPT.md", "r", encoding="utf-8") as _f:
    system_message = _f.read()


#------ MAIN RESPONSE FUNCTION ----
def respond_ai(message, history, top_k=None, temperature=None, model_name=None, request: gr.Request = None):
    if not message or len(message.strip()) == 0:
        raise gr.Error("Chat messages cannot be empty")


    history = history or []

    # Lightweight anonymous tracking for grouping turns into sessions
    session_id = _get_session_id(request)
    turn_index = _get_turn_index(history)
    is_owner_traffic = _get_owner_flag(request)

    # Useful for quick EC2 log inspection while you're testing
    print(f"SESSION: {session_id} | TURN: {turn_index} | OWNER: {is_owner_traffic}")

    # Use UI values if provided, otherwise read from current settings or env vars
    if SHOW_SETTINGS_PANEL:
        actual_top_k = int(_current_settings["top_k"])
        actual_temp = float(_current_settings["temperature"])
        actual_model = _current_settings["model"]
    else:
        actual_top_k = int(top_k) if top_k is not None else N_CHUNKS_RETRIEVE
        actual_temp = float(temperature) if temperature is not None else LLM_TEMPERATURE
        actual_model = model_name if model_name else LLM_MODEL

    # Validate API key for selected provider
    provider = actual_model.split("/")[0] if "/" in actual_model else "openai"
    if provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        yield "⚠️ Anthropic API key not configured. Please set ANTHROPIC_API_KEY in .env"
        return
    elif provider == "gemini" and not os.getenv("GEMINI_API_KEY"):
        yield "⚠️ Google API key not configured. Please set GEMINI_API_KEY in .env"
        return

    # Start latency timer (Phase 1 logging)
    _start_time = time.time()

    # ── Step 1: Detect walkthrough intent (narrow) ──────────────
    walkthrough_project = select_project_for_walkthrough(message)
    walkthrough_block = None
    if walkthrough_project:
        walkthrough_block = build_walkthrough_context_block(walkthrough_project)
        print(f"WORKFLOW: Walkthrough → {walkthrough_project['title']}")
 
    # ── Step 2: Detect project mention for diagram (broad) ──────
    # Walkthrough project takes priority; otherwise check for any mention
    diagram_project = walkthrough_project or find_mentioned_project(message)
    diagram_path = get_diagram_path(diagram_project) if diagram_project else None
    if diagram_path and not walkthrough_project:
        print(f"WORKFLOW: Diagram only → {diagram_project['title']}")
 
    # ── Step 2.5: Detect audience tier from conversation signals ──
    audience_tier = detect_audience_tier(message, history)
    sensitivity_filter = build_sensitivity_filter(audience_tier)
    if audience_tier != "public":
        print(f"SENSITIVITY: Tier escalated to '{audience_tier}'")

    # ── Step 3: RAG retrieval on the ORIGINAL message ───────────
    # (Not the enriched one — this is the key change for hybrid mode)
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=[message]   # ← user's actual question, unmodified
    )
    query_embedded = response.data[0].embedding

    query_kwargs = {
        "query_embeddings": [query_embedded],
        "n_results": actual_top_k,
    }
    if sensitivity_filter:
        query_kwargs["where"] = sensitivity_filter

    results = collection.query(**query_kwargs)

    # ── Compute retrieval quality metrics (Phase 2 logging) ─────
    similarity_stats = _compute_similarity_stats(results.get('distances', [[]])[0])

    # ── Step 4: Build context from RAG chunks ───────────────────
    context_parts = []
    for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
        src     = meta.get('source', '')
        section = meta.get('section', '')
        project = meta.get('project_name', '')
        if project and section:
            prefix = f"[{project} — {section}]"
        elif section:
            prefix = f"[{src} — {section}]"
        else:
            prefix = f"[{src}]"
        context_parts.append(f"{prefix}\n{doc}")
    context = "\n---\n".join(context_parts)
 
    print(f"Retrieved chunks:")
    for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
        section_info = f" >> {meta.get('section', 'N/A')}" if meta.get('section') else ""
        print(f"<<Document {meta['source']}{section_info} -- Chunk {meta['chunk_index']}>>\n{doc}\n")
 
    # ── Step 5: Assemble system message (HYBRID) ────────────────
    # RAG context is always included.
    # Walkthrough context is added as a SEPARATE block when present,
    # so the LLM has both the curated walkthrough notes AND whatever
    # ChromaDB retrieved for the user's actual question.
    system_message_enhanced = system_message + "\n\nContext:\n" + context
 
    if walkthrough_block:
        system_message_enhanced += (
            "\n\n---\n"
            "[WALKTHROUGH MODE — The visitor asked for a project walkthrough. "
            "Use the walkthrough notes below as your primary source for this response. "
            "The retrieved context above may contain additional relevant details — "
            "incorporate them if they add value, but the walkthrough notes are your "
            "main guide for structure and content.]\n\n"
            + walkthrough_block
        )
 
    # ── Step 6: Clean history, build messages ───────────────────
    def _clean_content(msg):
        c = msg.get("content")
        if isinstance(c, dict):
            return {**msg, "content": c.get("text", "")}
        if isinstance(c, list):
            texts = [p.get("text", "") for p in c if p.get("type") == "text"]
            return {**msg, "content": " ".join(texts)}
        return msg
 
    clean_history = [_clean_content(m) for m in history]

    # Truncate history to prevent token overflow
    # Keep only last N conversation turns (N turns = 2N messages: user + assistant)
    # This prevents hitting the 272k token limit on long conversations
    if len(clean_history) > MAX_HISTORY_MESSAGES:
        clean_history = clean_history[-MAX_HISTORY_MESSAGES:]

    msgs = (
        [{"role": "system", "content": system_message_enhanced}]
        + clean_history
        + [{"role": "user", "content": message}]  # ← original message, not enriched
    )
 
    # ── Steps 7+8: Stream with tools (single-pass) ─────────────
    # Start streaming immediately. Content deltas are yielded to the user
    # as they arrive. Tool-call deltas are accumulated silently.
    # If the model calls a tool (finish_reason=="tool_calls"), we resolve
    # it and stream again. No-tool messages (the common case) skip the
    # non-streaming round-trip entirely, cutting TTFT by ~1–2s.
    def _stream_and_accumulate(messages):
        """Stream one LLM turn. Yield content to caller; return (collected, tool_calls_acc, finish_reason)."""
        tool_calls_acc = []
        collected = ""
        finish_reason = None
        stream = litellm.completion(
            model=actual_model,
            messages=messages,
            tools=tools if model_supports_tools(actual_model) else None,
            stream=True,
            temperature=actual_temp,
        )
        for chunk in stream:
            choice = chunk.choices[0]
            finish_reason = choice.finish_reason or finish_reason
            delta = choice.delta
            if delta.content:
                collected += delta.content
                yield ("content", delta.content)
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    while len(tool_calls_acc) <= tc.index:
                        tool_calls_acc.append({"id": "", "type": "function",
                                               "function": {"name": "", "arguments": ""}})
                    acc = tool_calls_acc[tc.index]
                    if tc.id:   acc["id"] = tc.id
                    if tc.type: acc["type"] = tc.type
                    if tc.function:
                        if tc.function.name:      acc["function"]["name"]      += tc.function.name
                        if tc.function.arguments: acc["function"]["arguments"] += tc.function.arguments
        yield ("done", (collected, tool_calls_acc, finish_reason))


    collected = ""
    finish_reason = None
    tool_calls_acc = []
    _tool_name_called = None   # tracks first tool fired this turn (for logging)
    _tool_error = False

    # ── Easter egg greeting for inner circle ───────────────────
    if audience_tier == "inner_circle":
        collected = "🎉✨💛 ¡Familia! 💛✨🎉\n\n"
        yield collected

    for event, payload in _stream_and_accumulate(msgs):
        if event == "content":
            collected += payload
            yield collected
        else:  # "done"
            collected, tool_calls_acc, finish_reason = payload

    # Tool loop — only runs when the model actually called a tool
    while finish_reason == "tool_calls":
        if _tool_name_called is None and tool_calls_acc:
            _tool_name_called = tool_calls_acc[0]["function"]["name"]
        wrapped = [
            types.SimpleNamespace(
                id=tc["id"], type=tc["type"],
                function=types.SimpleNamespace(
                    name=tc["function"]["name"],
                    arguments=tc["function"]["arguments"],
                ),
            )
            for tc in tool_calls_acc
        ]
        tool_results = handle_tool_call(wrapped)
        if any(str(t.get("content", "")).startswith("Notification failed") for t in tool_results):
            _tool_error = True

        msgs.append({"role": "assistant", "content": collected or "",
                     "tool_calls": tool_calls_acc})
        msgs.extend(tool_results)

        collected = ""
        tool_calls_acc = []
        finish_reason = None
        for event, payload in _stream_and_accumulate(msgs):
            if event == "content":
                collected += payload
                yield collected
            else:
                collected, tool_calls_acc, finish_reason = payload
 
    print(f"<<LLM RESPONSE RAW>>\n{collected}\n")

    # ── Step 8.5: Smart diagram filtering (Option C: Intent + Prominence) ──
    # Only show diagrams when user asked about projects AND project is prominent in response
    def find_prominent_project(response_text: str):
        """
        Find project if prominently featured in response.
        Prominence = mentioned in first 300 chars OR mentioned 2+ times.
        """
        from featured_projects import load_featured_projects

        first_part = response_text[:300].lower()
        full_text_lower = response_text.lower()

        for project in load_featured_projects():
            title_lower = project['title'].lower()

            # Check if mentioned in opening (high prominence)
            if title_lower in first_part:
                return project

            # Or mentioned 2+ times throughout (clearly focused on it)
            if full_text_lower.count(title_lower) >= 2:
                return project

        return None

    # Intent check: Did user ask about projects?
    user_asked_about_projects = (
        walkthrough_project is not None or  # Walkthrough request detected
        find_mentioned_project(message) is not None  # User mentioned specific project
    )

    # Only override diagram if user intended to discuss projects AND project is prominent
    if user_asked_about_projects:
        response_project = find_prominent_project(collected)
        if response_project:
            diagram_project = response_project
            diagram_path = get_diagram_path(diagram_project)
            print(f"DIAGRAM: Prominent in response → {diagram_project['title']}")
        elif diagram_project:
            print(f"DIAGRAM: Query-based (no prominent match) → {diagram_project['title']}")
    else:
        # User didn't ask about projects - clear any diagram
        if diagram_project:
            print(f"DIAGRAM: Suppressed (no project intent)")
        diagram_project = None
        diagram_path = None

    print(f"<<FILES:>>\n{diagram_path}\n")

    # Capture the plain-text assistant response before any diagram HTML is appended.
    # This makes the log more analytically useful while still preserving response_chars
    # for the final rendered output shown to the visitor.
    logged_response_text = collected

    # ── Log cost after streaming completes ──────────────────────
    prompt_text = "\n".join(
        m.get("content", "") for m in msgs if isinstance(m.get("content"), str)
    )
    session_tracker.log_stream(actual_model, prompt_text, collected)

    # ── Step 9: Append diagram if available ──────────────────────
    # Now fires for ANY project mention, not just walkthroughs
    # OPTIMIZATION: Serve diagram via URL instead of base64 encoding
    # Saves ~82k tokens per diagram response (99% reduction in diagram overhead)
    if diagram_path:
        _href = f"/diagrams/{os.path.basename(diagram_path)}"
        _style = "max-width:100%;width:740px;!important;display:block;margin:1.5rem auto 0;border-radius:8px;cursor:pointer;box-shadow:0 2px 12px rgba(0,0,0,0.15);border:1px solid rgba(0,0,0,0.08)"

        # Use URL instead of base64 data URI - eliminates 82k tokens per response
        _img_tag = f'<img src="{_href}" style="{_style}" alt="Project diagram"/>'
        _tag = f'<a href="{_href}" target="_blank" rel="noopener noreferrer" style="display:block">{_img_tag}</a>'
        collected += f"\n\n{_tag}"
        yield collected

    # ── Determine workflow type for logging ─────────────────────
    if walkthrough_project:
        workflow_type = "walkthrough"
    elif diagram_path:
        workflow_type = "diagram_only"
    else:
        workflow_type = "standard"

    # ── Extract provider and cost info for logging ──────────────
    provider = actual_model.split("/")[0] if "/" in actual_model else "openai"
    last_call = session_tracker.calls[-1] if session_tracker.calls else None
    query_cost = last_call.cost_usd if last_call else 0.0
    prompt_toks = last_call.prompt_tokens if last_call else None
    completion_toks = last_call.completion_tokens if last_call else None

    empty_response = not bool((logged_response_text or "").strip())

    _log_query(
        message       = message,
        project_title = (walkthrough_project or diagram_project or {}).get("title"),
        walkthrough   = bool(walkthrough_project),
        tool_name     = _tool_name_called,
        had_error     = bool(empty_response or _tool_error),
        # Phase 1: Model & config
        model            = actual_model,
        temperature      = actual_temp,
        # Phase 1: RAG metrics
        n_chunks_retrieved = len(results['documents'][0]),
        # Phase 1: Response metrics
        response_chars   = len(collected),
        workflow_type    = workflow_type,
        latency_ms       = int((time.time() - _start_time) * 1000),
        # Phase 2: Quality metrics
        chunk_similarity_avg = similarity_stats["avg"],
        chunk_similarity_max = similarity_stats["max"],
        # # Audience tier
        # audience_tier
        # Provider and cost tracking
        provider         = provider,
        cost_usd         = query_cost,
        prompt_tokens    = prompt_toks,
        completion_tokens = completion_toks,
        audience_tier     = audience_tier,
        session_id       = session_id,
        turn_index       = turn_index,
        empty_response=empty_response,        
        is_owner_traffic = is_owner_traffic,
        assistant_response = logged_response_text,
    )
#----------------------------------


CSS_CLASS = {
    "Professional": "btn-professional",
    "Bridge":       "btn-bridge",
    "Personal":     "btn-personal",
}

def _svg_b64(filename: str) -> str:
    """Return a base64 data URI for a local SVG asset."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", filename)
    with open(path, "rb") as f:
        return "data:image/svg+xml;base64," + base64.b64encode(f.read()).decode()

CATEGORY_ICONS = {
    "Professional": _svg_b64("business-center.svg"),
    "Bridge":       _svg_b64("schema.svg"),
    "Personal":     _svg_b64("self-improvement.svg"),
}

# Module-level storage for current UI settings (used when SHOW_SETTINGS_PANEL=True)
_current_settings = {
    "top_k": N_CHUNKS_RETRIEVE,
    "temperature": LLM_TEMPERATURE,
    "model": LLM_MODEL,
}

def _build_title_html() -> str:
    """Build HTML header with circular headshot + title."""
    img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "assets", "bhs_forweb.png")
    try:
        with open(img_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        img_tag = f'<img src="data:image/png;base64,{b64}" alt="Barbara">'
    except FileNotFoundError:
        img_tag = ""
    return (
        '<div class="title-header-wrap">'
        '<div class="title-row">'
        '<h2>Barbara\'s Digital Twin</h2>'
        f'{img_tag}</div>'
        '<p class="title-subtitle">I\'m a conversational guide to explore her work, research and the way she thinks</p>'
        '</div>'
    )

def _build_contact_cta_html() -> str:
    """Build the 'Get in touch' CTA that fills the textbox with a contact template."""
    return (
        '<div style="text-align:center;">'
        '<p style="font-size:13px;color:var(--text-muted);">Want to reach Barbara directly?</p>'
        '<a class="contact-cta-link" href="#" '
        'onclick="var tb=document.querySelector(\'textarea\');'
        'if(tb){tb.value=\'I\\u2019d like to get in touch with Barbara - Here is my name, email, and message: \';'
        'tb.dispatchEvent(new Event(\'input\',{bubbles:true}));}return false;">'
        '📬 Get in touch →</a>'
        '</div>'
    )

if __name__ == "__main__":
    _assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

    with gr.Blocks(title="Barbara's Digital Twin", fill_width=True) as demo:
        # ── TITLE with circular headshot ──────────────────────────
        gr.HTML(_build_title_html())
        owner_toggle = gr.Checkbox(
            label="exclude my traffic",
            value=False,
            container=False,
            elem_classes=["owner-traffic-toggle"],
            render=False,
        )

        # ── CHAT INTERFACE (restores animated thinking dots) ──────
        chatbot = gr.Chatbot(
            show_label=False,
            avatar_images=(None, "assets/bhs_forweb.png"),
            placeholder="<h3 class='chatbot-header'>My portfolio, in conversation form</h3><p class='chatbot-subtitle'>Ask question or start with a prompt below ⬇</p>",
            height="60vh",
            min_height=320,
            max_height=625,
            autoscroll=True,
            render_markdown=True,
            container=False
        )

        # ── SETTINGS PANEL (conditionally rendered) ──────────────────
        if SHOW_SETTINGS_PANEL:
            with gr.Accordion("Settings", open=False, elem_classes=["settings-accordion"]):
                with gr.Row():
                    with gr.Column(scale=1, min_width=140):
                        top_k_slider = gr.Slider(
                            minimum=1, maximum=20, value=N_CHUNKS_RETRIEVE, step=1,
                            label="Top-K", info="Number of chunks to retrieve",
                        )
                    with gr.Column(scale=1, min_width=140):
                        temp_slider = gr.Slider(
                            minimum=0.0, maximum=2.0, value=LLM_TEMPERATURE, step=0.05,
                            label="Temperature", info="0 = deterministic, 2 = creative",
                        )
                    with gr.Column(scale=1, min_width=200):
                        model_dropdown = gr.Dropdown(
                            choices=AVAILABLE_MODELS, value=LLM_MODEL,
                            label="Model", info="Select provider/model",
                        )

            # Update module-level settings when sliders change
            def update_top_k(value):
                _current_settings["top_k"] = value
            def update_temp(value):
                _current_settings["temperature"] = value
            def update_model(value):
                _current_settings["model"] = value

            top_k_slider.change(fn=update_top_k, inputs=top_k_slider)
            temp_slider.change(fn=update_temp, inputs=temp_slider)
            model_dropdown.change(fn=update_model, inputs=model_dropdown)

        chat = gr.ChatInterface(
            fn=respond_ai,
            chatbot=chatbot,
            textbox=gr.Textbox(show_label=False, placeholder="Ask me a question", container=False, scale=7, submit_btn=True),
            #examples=["What problems does Barbara solve?", "Walk me through a project", "How was this digital twin built?", "What does 'making meaning from messy data' actually mean?"],
            # other idea = What's the case for knowledge graphs in 2026?
            examples=["What does 'making data legible' actually mean?", "How do you make a RAG system you'd actually trust?", "What would you build for an enterprise drowning in documents?", "How did a vision scientist end up shipping AI systems?"],
            example_icons=[
                           os.path.join(_assets_dir, "local_library_28dp_2A3BBD_FILL0_wght400_GRAD0_opsz24.svg"),#"want-shine.svg"),
                           os.path.join(_assets_dir, "handshake_28dp_A9472D_FILL0_wght400_GRAD0_opsz24.svg"),  #communication-icon.svg
                           os.path.join(_assets_dir, "precision_manufacturing_28dp_4B2E5A_FILL0_wght400_GRAD0_opsz24.svg"),  #precision-icon.svg
                           os.path.join(_assets_dir, "psychology_28dp_D96A32_FILL0_wght400_GRAD0_opsz24.svg"),  #psychology-icon.svg
                           ],
        )
        demo.load(_reset_owner_flag, outputs=owner_toggle)
        owner_toggle.change(_set_owner_flag, inputs=owner_toggle, outputs=owner_toggle)
        chatbot.like(handle_vote, [chatbot], None)  # passes history so vote logs can map to the current session

        # ── "GET IN TOUCH" CTA — positioned between chat and explore topics for better user flow ──
        gr.HTML(_build_contact_cta_html())

        # ── EXPLORE ACCORDION (collapsible example questions) ──
        with gr.Accordion("Ask Me Something Like…", open=False, elem_id="explore-accordion"):
            with gr.Row():
                for category, questions in CURATED_EXAMPLES.items():
                    with gr.Column():
                        gr.HTML(
                            f'<div class="sidebar-category" style="display:flex;flex-direction:column;align-items:center;text-align:center;">'
                            f'<img src="{CATEGORY_ICONS[category]}" width="24" height="24" '
                            f'style="opacity:0.7;margin-bottom:4px;">'
                            f'<strong>{category}</strong></div>'
                        )
                        for q in questions:
                            btn = gr.Button(
                                q,
                                size="sm",
                                elem_classes=["sidebar-btn", CSS_CLASS[category]],
                            )
                            btn.click(lambda q=q: q, outputs=chat.textbox)

        with gr.Row(elem_classes=["owner-traffic-row"]):
            owner_toggle.render()

        # ── COST DISPLAY (conditionally shown with settings panel) ──
        if SHOW_SETTINGS_PANEL:
            with gr.Row():
                cost_display = gr.HTML(
                    value='<div style="text-align:center;font-size:12px;color:#666;padding:8px;">'
                          'Session cost: $0.0000</div>',
                    elem_id="cost-display"
                )

            def update_cost_display():
                summary = session_tracker.summary()
                return (
                    f'<div style="text-align:center;font-size:12px;color:#666;padding:8px;">'
                    f'Session cost: ${summary["total_cost_usd"]:.4f} | '
                    f'{summary["total_tokens"]} tokens | '
                    f'{summary["total_calls"]} calls</div>'
                )

            chat.chatbot.change(fn=update_cost_display, outputs=cost_display)

    # Gradio uses root_path to construct absolute URLs for theme.css, /config, etc.
    # Without the full https:// URL, Gradio generates http:// URLs which browsers
    # block as mixed content. Fix per gradio-app/gradio#9381: set root_path to
    # the full HTTPS URL so Gradio generates correct resource URLs.
    # On HF Spaces the reverse-proxy terminates SSL and forwards HTTP internally.
    # Only set root_path when actually running inside HuggingFace Spaces.
    # SPACE_ID is present in .env for deploy config but shouldn't affect local dev.
    # HF Spaces always sets SYSTEM=spaces; local .env does not.
    running_on_hf = os.getenv("SYSTEM") == "spaces"
    if running_on_hf:
        custom_domain = os.getenv("CUSTOM_DOMAIN", "twin.barbhs.com")
        root = f"https://{custom_domain}"
    else:
        root = ""

    from fastapi.staticfiles import StaticFiles
    _diagrams_dir = os.path.join(_assets_dir, "project_diagrams")

    _app, _, _ = demo.launch(
        root_path=root,
        head=FAVICON_HEAD + ga_head + font_head,
        server_name="0.0.0.0",
        server_port=SERVER_PORT,
        show_error=True,
        css=custom_css,
        allowed_paths=[_assets_dir],
        prevent_thread_lock=True,
    )
    _app.mount("/diagrams", StaticFiles(directory=_diagrams_dir), name="diagrams")
    demo.server.thread.join()
