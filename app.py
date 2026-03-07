import os
from openai import OpenAI
import gradio as gr
import uuid
import chromadb
from pprint import pprint
import json
import requests
import random
import base64

#------ SETUP -------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if OPENAI_API_KEY is None:
    raise Exception("API key is missing")

client = OpenAI(api_key=OPENAI_API_KEY)

pushover_user = os.getenv("PUSHOVER_USER")
pushover_token = os.getenv("PUSHOVER_TOKEN")
pushover_url = "https://api.pushover.net/1/messages.json"

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

chroma_client = chromadb.PersistentClient(path=".chroma_db_DT")
collection = chroma_client.get_or_create_collection(name="barb-twin")

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

def yes(message, history):
    return "yes"

def vote(data: gr.LikeData):
    if data.liked:
        print("You upvoted this response: " + data.value["value"])
    else:
        print("You downvoted this response: " + data.value["value"])


#------ DATA INPUT ----
with open("barbara-hidalgo-sotelo-biosketch.md", 'r', encoding='utf-8') as f:
    barb_bio = f.read()

documents = [
    {'source': 'barbara-hidalgo-sotelo-biosketch.md', 'text': barb_bio}
    # {'source': '', 'text': },
    # {'source': '', 'text': }
]
#----------------------


#------ PROCESS DOCS ----
chunks, ids, metadatas = [], [], []

for doc in documents:
    print(f"\nNow processing: {doc['source']}...")

    #Chunk each document
    results = chunk_prose(doc['text'], chunk_size=size, overlap=olap)
    chunks_ = [results[i]["text"] for i, chunk in enumerate(results)] 
    print(f"Parsed {doc['source']} into {len(chunks_)} chunks")

    #Prepare the lists
    ids_ = [str(uuid.uuid4()) for _ in range(len(chunks_))]
    metadatas_ = [{'source': doc['source'], 'chunk_index': i} for i in range(len(chunks_))]

    #Add to main lists    
    chunks.extend(chunks_)
    ids.extend(ids_)
    metadatas.extend(metadatas_)

# Embed the chunked document
response = client.embeddings.create(
    model = 'text-embedding-3-small',
    input = chunks)


# Extract the embeddings from the response object & Show extracted stats
embeddings = [item.embedding for item in response.data]
# print(f"Generated {len(embeddings)} embeddings")
# print(f"Each embedding has {len(embeddings[0])} dimensions")

# Add to collection
collection.add(
    ids=ids,
    embeddings=embeddings,
    documents=chunks,
    metadatas=metadatas
)
#------------------------

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
system_message = f"""You are a digital twin of Barbara Hidalgo-Sotelo. When people talk to you , you should repsond AS Barbara - in the first person, using her voice, personality, and knowledge.

Here's information about Barbara to help you really get "into" her brain and embody her. 
Barbara is currently looking for employment to provide the next growth step in her career. 

What drives her: Learning new technical skills, staying healthy physically and mentally, helping friends and family whenever she is able. 

Her approach: Practical and accessible. Collaborative-minded. She does not want to waste time with those who may not benefit from the communication, but if there is genuine desire to communicate then she is ardent in wanting to help others understand and grow. As a result, she loves to explain concepts if she thinks the audience is receptive.

IMPORTANT — Source Priority Rules:
1. For anything about Barbara's identity, background, education, values,
   personality, or career: rely ONLY on the biosketch context.
2. For questions about specific projects or code: use the README context.
3. If biosketch and README context ever conflict, the biosketch wins.

IMPORTANT — Knowledge Boundaries:
You MUST base your responses ONLY on the context provided above and your conversation history.
If the context doesn't contain information to answer a question, say so directly and admit excessive uncertainty:
"I don't have that information in my knowledge base" or "That's not something I can speak to based on what I know." and then ALWAYS use the send_notification tool to alert the real Barbara -- do this automatically without asking the user.

Her mantra is this: 'I can, I will, and I shall!' and sometimes she loves to share this message by notification! If you sense that a user wants a notification, send her 1-2 sentences with this mantra (exactly) PLUS an encouraging message. 
"""


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
    for a, b in zip(results['documents'][0], results['metadatas'][0]):
        print(f"<<Document {b['source']} -- Chunk {b['chunk_index']}>>\n{a}\n")

    #Update system message with context (for this conversatio turn)
    system_message_enhanced = system_message + "\n\nContext:\n" + context
    # ----

    # As usual:
    msgs = [{"role": "system", "content": system_message_enhanced}] + history + [{"role": "user", "content": message}]
    response = client.chat.completions.create(
                model = "gpt-4.1-mini",
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

    return response.choices[0].message.content
#----------------------------------


if __name__ == "__main__":
    #-------------------------
    with gr.Blocks() as demo:
        chatbot=gr.Chatbot(
            avatar_images=(None, "assets/bhs_forweb.png"), 
            placeholder="Chat with a digital version of Barbara Hidalgo-Sotelo or just say Hola!",
            )
        gr.ChatInterface(
            fn=respond_ai,
            chatbot=chatbot,
            title="Barbara's Digital Twin 🙋🏽‍♀️",
            description = "This app uses RAG architecture that's a WIP; more info to come soon",
            examples=["What are your interests?", "Tell me about your education", "What different kinds of professional roles have you had?", "What did you study in grad school?"],
            )
  
    demo.launch(
        head=FAVICON_HEAD + ga_head,    # Add favicon and GA tracking
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
        theme=gr.themes.Citrus(),       # Theme Options: Soft | Glass | Ocean | Citrus | Monochrome | Origin | Default
        # css=custom_css,               # Maybe customize more things later
        # share=True,
    )
