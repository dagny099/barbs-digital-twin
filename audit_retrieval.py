# audit_retrieval.py — run once, no changes to prod
import os 
import chromadb
from openai import OpenAI
from collections import Counter                               
                                                                                                                                                                                                          
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
                                                                                        
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
chroma_client = chromadb.PersistentClient(path=".chroma_db_DT")
collection = chroma_client.get_collection("barb-twin")
                                                                                                                                                                                                          
source_hits = Counter()
section_hits = Counter()
short_chunk_retrievals = []  # chunks under 200 chars that got retrieved
                                                     
print(f"Auditing {len(RECRUITER_PROMPTS + FRIENDLY_PROMPTS)} questions...\n")

for question in RECRUITER_PROMPTS +  FRIENDLY_PROMPTS:
	resp = client.embeddings.create(model="text-embedding-3-small", input=[question])
	results = collection.query(query_embeddings=[resp.data[0].embedding], n_results=5, include=["metadatas", "documents"])

	for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
		src_type = meta["source"].split(":")[0]
		source_hits[src_type] += 1                           
		section = meta.get("section", "N/A")
		section_hits[section] += 1
		if len(doc) < 200:
			short_chunk_retrievals.append({
                  "question": question[:60],
                  "source": meta["source"],
                  "section": section,
                  "chunk_len": len(doc),
                  "preview": doc[:100]})

print("=== SOURCE TYPE HIT RATES (out of 100 retrieval slots) ===")
for src, count in source_hits.most_common():
	print(f"  {src:<25} {count:>3} hits")

print("\n=== TOP RETRIEVED SECTIONS ===")
for section, count in section_hits.most_common(20):
	print(f"  {count:>2}x  {section[:70]}")

print(f"\n=== SHORT CHUNKS RETRIEVED (< 200 chars) ===")
if short_chunk_retrievals:
	for r in short_chunk_retrievals:
		print(f"  Q: {r['question']}")
		print(f"     [{r['chunk_len']} chars] {r['source']} / {r['section']}")
		print(f"     → {r['preview']}")
		print()
else:
	print("  None — short chunks aren't being retrieved. ✅")