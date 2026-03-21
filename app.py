import os
import subprocess
from openai import OpenAI
import gradio as gr
import uuid
import chromadb
from pprint import pprint
import json
import requests
import random
import base64

#------ EXAMPLE PROMPTS -------
# Full question sets for different visitor personas (also useful for evaluation testing)

RECRUITER_PROMPTS = [
    "What led you from cognitive science to AI engineering?",
    "Can you explain how RAG works in simple terms?",
    "What's a project you built that you're really proud of?",
    "How do you approach collaborating with non-technical stakeholders?",
    "What kinds of problems get you most excited to solve?",
    "Tell me about your background in knowledge graphs.",
    "What's your working style like on a team?",
    "What are you hoping to work on next in your career?",
    "What's your superpower as an AI consultant?",
    "Why did you transition from academia to industry?",
]

FRIENDLY_PROMPTS = [
    "What are you working on these days that's lighting you up?",
    "How did you get into beekeeping, and does it influence your work?",
    "What's the most surprising thing you've learned about yourself lately?",
    "Do you still run? How does that fit into your routine now?",
    "What's your favorite sci-fi book and why does it resonate with you?",
    "How has your Toastmasters experience shaped how you communicate about AI?",
    "What's something you're learning right now just for fun?",
    "How do you think about the connection between cognition and AI?",
    "What's a recent win you're proud of, big or small?",
    "If you could work on any problem tomorrow, what would it be?",
]

# Curated subset shown in the UI: mix of professional and personal to demonstrate range
# 3 professional (💼), 3 bridge (🔗), 3 personal (💭) - balanced for visual clarity
CURATED_EXAMPLES = [
    "💼 What led you from cognitive science to AI engineering?",
    "💼 Can you explain how RAG works in simple terms?",
    "💼 What kinds of problems get you most excited to solve?",
    "🔗 What's a project you built that you're really proud of?",
    "🔗 How do you think about the connection between cognition and AI?",
    "🔗 What are you hoping to work on next in your career?",
    "💭 What are you working on these days that's lighting you up?",
    "💭 How did you get into beekeeping, and does it influence your work?",
    "💭 What's something you're learning right now just for fun?",
]

#------ SETUP -------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if OPENAI_API_KEY is None:
    raise Exception("API key is missing")

client = OpenAI(api_key=OPENAI_API_KEY)

pushover_user = os.getenv("PUSHOVER_USER")
pushover_token = os.getenv("PUSHOVER_TOKEN")
pushover_url = "https://api.pushover.net/1/messages.json"

# Fix Gradio's label[for=FORM_ELEMENT] accessibility bug
fix_label_head = """
<script>
(function() {
    function patchLabels() {
        document.querySelectorAll('label[for="FORM_ELEMENT"]').forEach(function(el) {
            el.removeAttribute('for');
        });
    }
    document.addEventListener('DOMContentLoaded', patchLabels);
    var obs = new MutationObserver(patchLabels);
    document.addEventListener('DOMContentLoaded', function() {
        obs.observe(document.body, { childList: true, subtree: true });
    });
})();
</script>
"""

# Google Analytics tracking code
ga_head = """
<!-- Google tag (gtag.js) -->                                                                                                                       
<script async src="https://www.googletagmanager.com/gtag/js?id=G-489875302">
</script>                                                               
<script>
window.dataLayer = window.dataLayer || [];                                                                                                        
function gtag(){dataLayer.push(arguments);}                                                                                                       
gtag('js', new Date());                                                                                                                           
gtag('config', 'G-489875302');                                                                                                                    
</script>
"""

# FOR CHUNKING, TEXT PROCESSING & STORING EMBEDDINGS:
size, olap = 500, 50

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

#If there are already existing items, delete 'em
# if collection.get()['ids']:
#     collection.delete(collection.get['ids'])
# pprint(collection.get())
#--------------------------

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

def build_favicon_head() -> str:
    """
    Deployment-proof favicon:
    - Reads a local icon from ./assets/
    - Embeds it as a base64 data URI in the <head>, so it works on Gradio share links,
      reverse proxies, and most static hosting setups without extra routing.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "assets", "favicon.png"),
        os.path.join(base_dir, "assets", "bee_barb.png"),
        os.path.join(base_dir, "assets", "icon.png"),
        os.path.join(base_dir, "assets", "icon.ico"),
    ]
    for path in candidates:
        try:
            if os.path.exists(path):
                with open(path, "rb") as f:
                    raw = f.read()
                b64 = base64.b64encode(raw).decode("ascii")
                mime = "image/png" if path.lower().endswith(".png") else "image/x-icon"
                return f'<link rel="icon" type="{mime}" href="data:{mime};base64,{b64}">'
        except Exception:
            # If anything goes wrong, silently fall back to no favicon rather than crashing the app
            pass
    return ""

FAVICON_HEAD = build_favicon_head()

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
div[role="log"][aria-label="chatbot conversation"] {
    background-color: #EEF4F7 !important;
    border-radius: 8px !important;
}
.dark div[role="log"][aria-label="chatbot conversation"] {
    background-color: #1B2D3A !important;
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


#------ COLD-START FALLBACK ----
# Embed biosketch only if the collection is empty (e.g. fresh HF Spaces deployment).
# For normal use, populate the DB with: python ingest.py
if collection.count() == 0:
    print("⚠️  Collection is empty — running cold-start biosketch embed...")

    with open("inputs/barbara-hidalgo-sotelo-biosketch.md", 'r', encoding='utf-8') as f:
        barb_bio = f.read()

    documents = [{'source': 'barbara-hidalgo-sotelo-biosketch.md', 'text': barb_bio}]
    chunks, ids, metadatas = [], [], []

    for doc in documents:
        print(f"\nNow processing: {doc['source']}...")
        results = chunk_prose(doc['text'], chunk_size=size, overlap=olap)
        chunks_ = [results[i]["text"] for i, chunk in enumerate(results)]
        print(f"Parsed {doc['source']} into {len(chunks_)} chunks")
        ids_ = [str(uuid.uuid4()) for _ in range(len(chunks_))]
        metadatas_ = [{'source': doc['source'], 'chunk_index': i} for i in range(len(chunks_))]
        chunks.extend(chunks_)
        ids.extend(ids_)
        metadatas.extend(metadatas_)

    embeddings = [item.embedding for item in client.embeddings.create(
        model='text-embedding-3-small', input=chunks).data]
    collection.add(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)
    print(f"✅ Cold-start embed complete: {len(chunks)} biosketch chunks added")
else:
    print(f"✅ Collection ready: {collection.count()} chunks loaded")
#-------------------------------

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
    # ----
    # RAG
    response = client.embeddings.create(model="text-embedding-3-small", 
                                        input=[message])
    query_embedded = response.data[0].embedding    
    results = collection.query(
        query_embeddings=[query_embedded],
        n_results=3)

    #Stich retreieved chunks together to create the context for the response
    context = "\n---------\n".join(results['documents'][0])

    print(f"Retrieved chunks:")
    for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
        section_info = f" >> {meta.get('section', 'N/A')}" if meta.get('section') else ""
        print(f"<<Document {meta['source']}{section_info} -- Chunk {meta['chunk_index']}>>\n{doc}\n")

    #Update system message with context (for this conversatio turn)
    system_message_enhanced = system_message + "\n\nContext:\n" + context
    # ----

    # As usual:
    msgs = [{"role": "system", "content": system_message_enhanced}] + history + [{"role": "user", "content": message}]
    response = client.chat.completions.create(
                model = "gpt-4.1", #"gpt-4.1-mini",
                messages = msgs,
                tools = tools
            )

    while response.choices[0].message.tool_calls:
        tool_result = handle_tool_call(response.choices[0].message.tool_calls)
        msgs.append(response.choices[0].message) #i dont get why this   
        msgs.extend(tool_result)

        response = client.chat.completions.create(
            model='gpt-4.1-mini',
            messages = msgs,
            tools=tools
        )        

    final_response = response.choices[0].message.content
    print(f"<<LLM RESPONSE RAW>>\n{final_response}\n")
    return final_response
#----------------------------------


# Question data: split CURATED_EXAMPLES by emoji prefix for sidebar
SIDEBAR_QUESTIONS = {
    "💼 Professional": [q[2:] for q in CURATED_EXAMPLES if q.startswith("💼")],
    "🔗 Bridge":       [q[2:] for q in CURATED_EXAMPLES if q.startswith("🔗")],
    "💭 Personal":     [q[2:] for q in CURATED_EXAMPLES if q.startswith("💭")],
}
CSS_CLASS = {
    "💼 Professional": "btn-professional",
    "🔗 Bridge":       "btn-bridge",
    "💭 Personal":     "btn-personal",
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
        f'<div class="title-row">{img_tag}'
        '<h1>Barbara\'s Digital Twin 🙋🏽‍♀️</h1></div>'
        '<p class="title-subtitle">'
        'Ask about my professional background, technical projects, or personal interests</p>'
    )

if __name__ == "__main__":
    with gr.Blocks() as demo:
        # ── TITLE with circular headshot ──────────────────────────
        gr.HTML(_build_title_html())

        # ── CHAT INTERFACE (restores animated thinking dots) ──────
        chatbot = gr.Chatbot(
            avatar_images=(None, "assets/bhs_forweb.png"),
            placeholder="Chat with a digital version of Barbara Hidalgo-Sotelo or just say Hola!",
            height=420,
            autoscroll=True,
            render_markdown=True,
        )
        chat = gr.ChatInterface(
            fn=respond_ai,
            chatbot=chatbot,
            textbox=gr.Textbox(show_label=True, placeholder="Ask question", container=True, scale=7, submit_btn=True),
        )

        # ── EXPLORE ACCORDION (always open on load, collapsible) ──
        with gr.Accordion("💡 Explore Topics", open=True, elem_id="explore-accordion"):
            with gr.Row():
                for category, questions in SIDEBAR_QUESTIONS.items():
                    with gr.Column():
                        gr.Markdown(f"**{category}**", elem_classes=["sidebar-category"])
                        for q in questions:
                            btn = gr.Button(
                                q,
                                size="sm",
                                elem_classes=["sidebar-btn", CSS_CLASS[category]],
                            )
                            btn.click(lambda q=q: q, outputs=chat.textbox)

    # On HF Spaces the reverse-proxy terminates SSL and forwards HTTP internally.
    # Gradio uses root_path to construct absolute URLs for theme.css, /config, etc.
    # Without the full https:// URL, Gradio generates http:// URLs which browsers
    # block as mixed content. Fix per gradio-app/gradio#9381: set root_path to
    # the full HTTPS URL so Gradio generates correct resource URLs.
    space_id = os.getenv("SPACE_ID")
    if space_id:
        custom_domain = os.getenv("CUSTOM_DOMAIN", "twin.barbhs.com")
        root = f"https://{custom_domain}"
    else:
        root = ""

    demo.launch(
#        theme=gr.themes.Citrus(),
        root_path=root,
        head=FAVICON_HEAD + ga_head + fix_label_head,
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
        css=custom_css,
    )
