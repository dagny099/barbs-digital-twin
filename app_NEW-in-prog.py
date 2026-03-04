import os
from openai import OpenAI
import gradio as gr
import uuid
import chromadb
from pprint import pprint
import json
import requests
import random
from utils import chunk_prose, parse_paragraphs

#------ SETUP -------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if OPENAI_API_KEY is None:
    raise Exception("API key is missing")

client = OpenAI(api_key=OPENAI_API_KEY)

pushover_user = os.getenv("PUSHOVER_USER")
pushover_token = os.getenv("PUSHOVER_TOKEN")
pushover_url = "https://api.pushover.net/1/messages.json"

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
# NOTE: chunk_prose() and parse_paragraphs() are now imported from utils.py
#       to eliminate code duplication across ingestion scripts
#----------------------


#------ DATA INPUT ----
# NOTE: Biosketch, resume, READMEs, and MkDocs content are pre-embedded
#       via dedicated scripts (embed_biosketch.py, embed_resume.py, etc.).
#       This ensures proper section-aware metadata and avoids re-processing
#       on every app launch.
#
# To update knowledge base:
#   python embed_biosketch.py --force-reembed
#   python embed_resume.py --force-reembed
#   python embed_readmes.py
#   python embed_mkdocs.py
#
# The ChromaDB collection is persistent and pre-loaded with all sources.
#----------------------

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
                Sends a message to send as a push notification to the users phone via Pushover. 
                User this to alert the user about a new message.""",
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
If the context doesn't contain information to answer a question, say so directly:
"I don't have that information in my knowledge base" or "That's not something I can speak to based on what I know."
Do NOT speculate, make educated guesses, or search the web. It's better to admit uncertainty than to provide potentially incorrect information.

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
    for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
        section_info = f" >> {meta.get('section', 'N/A')}" if meta.get('section') else ""
        print(f"<<Document {meta['source']}{section_info} -- Chunk {meta['chunk_index']}>>\n{doc}\n")

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
        pprint(response.choices[0].message.tool_calls)
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

#TODO -- ADD PRINT STATMEMENTS TO SEE WHAT TOOLS ARE BEING CALLED

#------ LAUNCH GRADIO ----
gr.ChatInterface(fn=respond_ai).launch(inbrowser=True)

#-------------------------
