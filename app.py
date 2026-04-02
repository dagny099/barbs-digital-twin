import os
import subprocess
import types
import datetime
from dotenv import load_dotenv
from openai import OpenAI
import gradio as gr
import chromadb
import json
import requests
import random
import base64
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
        "What are you working on these days that's lighting you up?",
        "How did you get into beekeeping, and does it influence your work?",
        "What's something you're learning right now just for fun?",
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
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1")

# Temperature for LLM completions. 0.7 is a reasonable default for personality+accuracy balance.
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))

N_CHUNKS_RETRIEVE = int(os.getenv("N_CHUNKS_RETRIEVE", 10))

# Local server port. HF Spaces ignores this and always uses 7860.
SERVER_PORT = int(os.getenv("PORT", 7860))

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
    print("Knowledge base is empty — running ingest.py --all ...")
    subprocess.run(["python", "ingest.py", "--all"], check=True)
    from db_sync import push_db
    push_db()
    print("Ingestion complete.")


#------ CUSTOM FUNCTIONS -------
"""
Chunk plain prose into overlapping segments for retrieval tasks.

Atomic unit: paragraph (double-newline delimited)
- Paragraphs are never split mid-sentence
- Overlap re-includes trailing paragraphs from the previous chunk
- No external dependencies
"""

def parse_paragraphs(raw_text: str) -> list[str]:
    """
    Split text on blank lines, strip whitespace, drop empties.
    Handles both \n\n and \r\n\r\n line endings.
    """
    paragraphs = raw_text.split("\n\n")
    # Collapse internal newlines within each paragraph into spaces
    cleaned = [" ".join(p.split()) for p in paragraphs]
    return [p for p in cleaned if p]


def chunk_prose(raw_text, chunk_size=500, overlap=50):
    """
    Chunk plain prose into overlapping segments.

    Args:
        raw_text:   Full text (paragraphs separated by blank lines).
        chunk_size: Target size in chars. May slightly exceed to keep
                    paragraphs intact.
        overlap:    Target overlap in chars. Backtracks whole paragraphs.

    Returns:
        List of dicts: {text, para_start, para_end, char_count}
    """
    paragraphs = parse_paragraphs(raw_text)

    if not paragraphs:
        return []

    chunks = []
    i = 0

    while i < len(paragraphs):
        # --- Accumulate paragraphs until we hit chunk_size ---
        chunk_paras, char_count, j = [], 0, i
        while j < len(paragraphs):
            para_len = len(paragraphs[j])

            # Always include at least one paragraph per chunk
            if char_count > 0 and (char_count + para_len) > chunk_size:
                break

            chunk_paras.append(paragraphs[j])
            char_count += para_len + 1
            j += 1

        # --- Store as a plain dict ---
        text = "\n\n".join(chunk_paras)
        chunks.append({
            "text": text,
            "para_start": i,
            "para_end": j - 1,
            "char_count": len(text),
        })

        # --- Stop if we've consumed everything ---
        if j >= len(paragraphs):
            break

        # --- Backtrack for overlap ---
        overlap_chars = 0
        backtrack = 0
        for k in range(j - 1, i, -1):
            if overlap_chars + len(paragraphs[k]) > overlap:
                break
            overlap_chars += len(paragraphs[k])
            backtrack += 1

        i = j - backtrack

    return chunks
#----------------------

# My favicon (local png)
with open("assets/bee_barb.png", "rb") as f:
      b64 = base64.b64encode(f.read()).decode()
FAVICON_HEAD = f'<link rel="icon" type="image/png" href="data:image/png;base64,{b64}">'

custom_css = """
/* ── Explore accordion: category label spacing ─────────────────── */
.sidebar-category {
    margin-top: 10px !important;
    margin-bottom: 4px !important;
    font-size: 13px !important;
}
/* ── Explore Topics question buttons ───────────────────────────── */
.sidebar-btn {
    width: 100% !important;
    text-align: left !important;
    padding: 5px 10px 5px 14px !important;
    border-radius: 6px !important;
    font-size: 14.5px !important;
    line-height: 1.35 !important;
    margin-bottom: 2px !important;
    white-space: normal !important;
    height: auto !important;
    min-height: unset !important;
    overflow: visible !important;
    border: 1px solid rgba(0,0,0,0.12) !important;
    transition: all 0.15s ease !important;
}
.sidebar-btn span {
    overflow: visible !important;
    display: block !important;
}
.sidebar-btn:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.12) !important;
}
/* ── Bold text — extra heavy so it reads clearly ───────────────── */
.chatbot .prose strong, .chatbot .prose b {
    font-weight: 900 !important;
    color: #1B2D3A !important;
}
.dark .chatbot .prose strong, .dark .chatbot .prose b {
    color: #D0E8F0 !important;
}
/* ── Chatbot area — pale steel blue (light) / deep steel blue (dark) */
/* Light: same hue family as barbhs.com hero, quieter/softer register  */
/* Dark:  deep version of that same hero — feels like the same "room"  */
/* Height uses viewport units so it adapts across screen sizes          */
div[role="log"][aria-label="chatbot conversation"] {
    background-color: #EEF4F7 !important;
    border-radius: 8px !important;
}
.dark div[role="log"][aria-label="chatbot conversation"] {
    background-color: #1B2D3A !important;
}
/* ── Global font ────────────────────────────────────────────────── */
* { font-family: 'IBM Plex Sans', sans-serif !important; }

/* ── Example question buttons ───────────────────────────────────── */
/* The real inner wrapper that controls icon/text alignment           */
.example-content {
    align-items: center !important;
}
.examples .example {
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
}
.examples .example img {
    width: 24px !important;
    height: 24px !important;
    display: block !important;
    margin: 0 auto 8px auto !important;
    opacity: 0.75 !important;
}
/* Center text, near-black to match icon color                       */
.examples button {
    text-align: center !important;
    justify-content: center !important;
    flex-direction: column !important;
    align-items: center !important;
    background: linear-gradient(135deg, #EEF4F7 0%, #DAE8F0 100%) !important;
    border: 1px solid #B2C8D8 !important;
    border-radius: 8px !important;
    color: #1a1f2e !important;
    font-size: 0.92rem !important;
    font-weight: 500 !important;
    line-height: 1.4 !important;
    padding: 12px 14px !important;
    white-space: normal !important;
    height: auto !important;
    min-height: 56px !important;
    transition: all 0.15s ease !important;
}
.examples button span {
    display: block !important;
    width: 100% !important;
    text-align: center !important;
}
.examples button:hover {
    background: linear-gradient(135deg, #DAE8F0 0%, #C4D9E8 100%) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.10) !important;
}
.dark .examples button {
    background: linear-gradient(135deg, #1B2D3A 0%, #213547 100%) !important;
    border: 1px solid rgba(144,184,212,0.3) !important;
    color: #90B8D4 !important;
}
.dark .examples button:hover {
    background: linear-gradient(135deg, #213547 0%, #2a4560 100%) !important;
}
/* ── Explore Topics accordion label — bold and prominent ────────── */
#explore-accordion .label-wrap span,
#explore-accordion > div:first-child span {
    font-weight: 600 !important;
    font-size: 1rem !important;
    letter-spacing: 0.01em !important;
}
/* ── Explore Topics accordion — tri-color gradient (light mode) ──── */
/* Teal · Steel Blue · Warm Amber — mirrors button palette            */
#explore-accordion {
    background: linear-gradient(
        135deg,
        rgba(224, 245, 248, 0.5) 0%,
        rgba(229, 237, 243, 0.5) 50%,
        rgba(254, 243, 226, 0.5) 100%
    ) !important;
    border-radius: 8px !important;
}
/* ── Explore accordion dark mode ───────────────────────────────── */
.dark #explore-accordion {
    background: linear-gradient(
        135deg,
        rgba(10, 32, 40, 0.6) 0%,
        rgba(27, 45, 58, 0.6) 50%,
        rgba(45, 32, 10, 0.6) 100%
    ) !important;
}
/* ── Title header with circular headshot ──────────────────────── */
.title-row {
    display: flex !important;
    align-items: center !important;
    gap: 16px !important;
    margin-bottom: 4px !important;
}
.title-row img {
    width: 64px !important;
    height: 64px !important;
    border-radius: 50% !important;
    object-fit: cover !important;
    border: 2px solid #B2E8EE !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.12) !important;
    flex-shrink: 0 !important;
}
.title-row h1 {
    margin: 0 !important;
    font-size: 1.6rem !important;
    font-weight: 700 !important;
}
.title-subtitle {
    margin: 0 0 8px 0 !important;
    color: #666 !important;
    font-size: 0.95rem !important;
}
.dark .title-subtitle {
    color: #aaa !important;
}
/* ── Hide Gradio footer (Use via API · Built with Gradio · Settings) */
footer {
    display: none !important;
}
/* ── Hide the "Chatbot" label in the top-left corner ───────────── */
.chatbot label, .chatbot .label-wrap {
    display: none !important;
}
/* ── Dark mode: invert black SVG icons → white ──────────────────── */
/* brightness(0) crushes all pixels to black; invert(1) flips to white */
/* Works for any monochrome Material Icon embedded as an <img> tag    */
.dark .examples .example img {
    filter: brightness(0) invert(1) !important;
    opacity: 0.82 !important;
}
.dark .sidebar-category img {
    filter: brightness(0) invert(1) !important;
    opacity: 0.75 !important;
}
/* ── "Get in touch" CTA — link-styled button below input ────────── */
.contact-cta-btn {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #3B7A8C !important;
    font-size: 0.84rem !important;
    font-weight: 400 !important;
    padding: 0 0 10px 0 !important;
    margin: 0 auto !important;
    display: block !important;
    width: auto !important;
    text-decoration: underline !important;
    text-underline-offset: 3px !important;
    text-decoration-color: rgba(59,122,140,0.4) !important;
    transition: color 0.15s ease !important;
}
.contact-cta-btn:hover {
    color: #1B5F6F !important;
    background: transparent !important;
    box-shadow: none !important;
    transform: none !important;
    text-decoration-color: rgba(27,95,111,0.7) !important;
}
.dark .contact-cta-btn {
    color: #7EC8D8 !important;
    text-decoration-color: rgba(126,200,216,0.4) !important;
}
.dark .contact-cta-btn:hover {
    color: #A8DDE8 !important;
    text-decoration-color: rgba(168,221,232,0.7) !important;
}
/* ── Hero avatar above the title ───────────────────────────────── */
.hero-avatar {
    display: block;
    margin: 0 auto 8px auto;
    width: 80px;
    height: 80px;
    border-radius: 50%;
    object-fit: cover;
    box-shadow: 0 2px 12px rgba(0,0,0,0.12);
}
/* ── Category button colors (light mode) ───────────────────────── */
/* Professional: teal — matches barbhs.com CTA button accent         */
.btn-professional {
    background: linear-gradient(135deg, #E0F5F8 0%, #B2E8EE 100%) !important;
    color: #0E7A8A !important;
}
/* Bridge: steel blue — matches barbhs.com hero background           */
.btn-bridge {
    background: linear-gradient(135deg, #E5EDF3 0%, #C4D9E8 100%) !important;
    color: #3B5978 !important;
}
/* Personal: warm amber — complements the cool blues, adds warmth    */
.btn-personal {
    background: linear-gradient(135deg, #FEF3E2 0%, #FDDBA1 100%) !important;
    color: #8B5E00 !important;
}
/* ── Sidebar buttons in dark mode ──────────────────────────────── */
.dark .btn-professional {
    background: linear-gradient(135deg, #0a2028 0%, #0e2e38 100%) !important;
    color: #4DD0E1 !important;
    border: 1px solid rgba(77,208,225,0.25) !important;
}
.dark .btn-bridge {
    background: linear-gradient(135deg, #1B2D3A 0%, #213547 100%) !important;
    color: #90B8D4 !important;
    border: 1px solid rgba(144,184,212,0.25) !important;
}
.dark .btn-personal {
    background: linear-gradient(135deg, #2d1f0a 0%, #3a2810 100%) !important;
    color: #FFCC80 !important;
    border: 1px solid rgba(255,204,128,0.25) !important;
}
"""

def vote(data: gr.LikeData):
    if data.liked:
        print("You upvoted this response: " + data.value["value"])
    else:
        print("You downvoted this response: " + data.value["value"])


print(f"✅ Collection ready: {collection.count()} chunks loaded")

#------ Tools -----------
# Function that sends notification via pushover app
def send_notification(message: str):
    payload = {'user': pushover_user, 'token': pushover_token, 'device': 'oneplusnordn2005g', 'message': message}
    requests.post(pushover_url, data=payload)
    return f"Notification message was sent: {message}"

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

def _log_query(message, project_title, walkthrough, tool_name, had_error):
    """Append one query record to the JSONL log. Fails silently — must never affect the user."""
    try:
        entry = {
            "ts":          datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "message":     message,
            "project":     project_title,
            "walkthrough": walkthrough,
            "tool_called": tool_name is not None,
            "tool_name":   tool_name,
            "had_error":   had_error,
        }
        with open(_QUERY_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # logging must NEVER break the app


def _assistant_message_dict(msg):
    """Convert an OpenAI SDK assistant message to a plain API payload dict."""
    payload = {"role": "assistant", "content": msg.content or ""}
    if msg.tool_calls:
        payload["tool_calls"] = [
            {
                "id": tc.id,
                "type": tc.type,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in msg.tool_calls
        ]
    return payload

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
def respond_ai(message, history):
    if not message or not message.strip():
        return

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
 
    # ── Step 3: RAG retrieval on the ORIGINAL message ───────────
    # (Not the enriched one — this is the key change for hybrid mode)
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=[message]   # ← user's actual question, unmodified
    )
    query_embedded = response.data[0].embedding
    results = collection.query(
        query_embeddings=[query_embedded],
        n_results=N_CHUNKS_RETRIEVE
    )
 
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
        stream = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            tools=tools,
            stream=True,
            temperature=LLM_TEMPERATURE,
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
    print(f"<<FILES:>>\n{diagram_path}\n")
 
    # ── Step 9: Append diagram if available ──────────────────────
    # Now fires for ANY project mention, not just walkthroughs
    if diagram_path:
        with open(diagram_path, "rb") as _img:
            _b64 = base64.b64encode(_img.read()).decode()
        _ext = diagram_path.rsplit(".", 1)[-1].lower()
        _data_url = f"data:image/{_ext};base64,{_b64}"
        _href = f"/diagrams/{os.path.basename(diagram_path)}"
        _style = "max-width:100%;width:740px;!important;display:block;margin:1.5rem auto 0;border-radius:8px;cursor:pointer;box-shadow:0 2px 12px rgba(0,0,0,0.15);border:1px solid rgba(0,0,0,0.08)"

        _img_tag = f'<img src="{_data_url}" style="{_style}" alt="Project diagram"/>'
        _tag = f'<a href="{_href}" target="_blank" rel="noopener noreferrer" style="display:block">{_img_tag}</a>'
        collected += f"\n\n{_tag}"
        yield collected

    _log_query(
        message       = message,
        project_title = (walkthrough_project or diagram_project or {}).get("title"),
        walkthrough   = bool(walkthrough_project),
        tool_name     = _tool_name_called,
        had_error     = False,
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
        '<div class="title-row">'
        '<h1>Barbara\'s Digital Twin</h1>'
        f'{img_tag}</div>'
        '<p class="title-subtitle">'
        'Ask about my professional background, technical projects, or personal interests</p>'
    )

if __name__ == "__main__":
    _assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

    with gr.Blocks(title="Barbara's Digital Twin") as demo:
        # ── TITLE with circular headshot ──────────────────────────
        gr.HTML(_build_title_html())

        # ── CHAT INTERFACE (restores animated thinking dots) ──────
        chatbot = gr.Chatbot(
            avatar_images=(None, "assets/bhs_forweb.png"),
            placeholder="<h3 style='text-align:center;color:#1a1f2e;margin-bottom:6px;'>Hola! I'm Barbara's Digital Twin.</h3><p style='text-align:center;color:#444;font-size:1.05rem;'>Ask me about her projects, background, or interests — or pick a topic below!</p>",
            height="65vh",
            min_height=320,
            max_height=700,
            autoscroll=True,
            render_markdown=True,
        )
        chat = gr.ChatInterface(
            fn=respond_ai,
            chatbot=chatbot,
            textbox=gr.Textbox(show_label=True, placeholder="Ask question", container=True, scale=7, submit_btn=True),
            examples=["What problems does Barbara solve?", "Walk me through a project", "How was this digital twin built?", "What does 'making meaning from messy data' actually mean?"],
            example_icons=[
                           os.path.join(_assets_dir, "want-shine.svg"),
                           os.path.join(_assets_dir, "communication-icon.svg"),
                           os.path.join(_assets_dir, "precision-icon.svg"),
                           os.path.join(_assets_dir, "psychology-icon.svg"),
                           ],
        )
        
        # ── "GET IN TOUCH" CTA — fills textbox with contact trigger ──
        # ── EXPLORE ACCORDION (always open on load, collapsible) ──
        with gr.Accordion("Explore Topics", open=False, elem_id="explore-accordion"):
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

        contact_btn = gr.Button(
            "📬 Want to reach Barbara directly? Get in touch →",
            elem_classes=["contact-cta-btn"],
        )
        contact_btn.click(
            fn=lambda: "I'd like to get in touch with Barbara",
            outputs=chat.textbox,
        )

    # On HF Spaces the reverse-proxy terminates SSL and forwards HTTP internally.
    # Gradio uses root_path to construct absolute URLs for theme.css, /config, etc.
    # Without the full https:// URL, Gradio generates http:// URLs which browsers
    # block as mixed content. Fix per gradio-app/gradio#9381: set root_path to
    # the full HTTPS URL so Gradio generates correct resource URLs.
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
