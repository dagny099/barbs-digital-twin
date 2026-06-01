---
title: Quick Start
tags:
  - getting-started
  - visitor
---

# Quick Start

Whether you're a recruiter, a technical collaborator, or just curious — here's how to get the most out of your conversation with Barbara's digital twin in under five minutes.

---

## Option A — Just Chat

The fastest path. No setup, no account.

**1.** Open [twin.barbhs.com](https://twin.barbhs.com) in your browser.

**2.** Type a question in the chat box. A few ideas to get you started:

!!! tip "Good first questions"
    - *"Tell me about yourself"* — a solid overview of Barbara's background and current work
    - *"Walk me through the Resume Explorer project"* — one of Barbara's flagship portfolio pieces
    - *"What's Barbara's experience with generative AI?"* — good for a hiring context
    - *"How does this chatbot actually work?"* — the system will describe its own architecture (you're using the live demo right now)

**3.** Follow up naturally. The twin maintains conversation context, so follow-ups like *"tell me more about the Neo4j piece"* or *"which project would be most relevant to a data engineering role?"* work well.

**4.** Rate responses with 👍 or 👎 — this feedback feeds directly into quality analytics.

---

## Option B — Run It Locally

For developers who want to explore the codebase or build their own twin.

```bash
# 1. Clone the repo
git clone https://github.com/dagny099/barbs-digital-twin.git
cd barbs-digital-twin

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Open .env and set at minimum: OPENAI_API_KEY=sk-...

# 5. Launch the app
python app.py
```

Open [http://localhost:7860](http://localhost:7860) and you're live.

!!! note "Minimum requirement"
    Only `OPENAI_API_KEY` is required to run the app. Neo4j and Pushover credentials are optional — the app falls back gracefully to ChromaDB if Neo4j isn't configured.

---

## What Happens on First Query

When you send a message, the pipeline runs in milliseconds:

1. Your query is embedded using `text-embedding-3-small`
2. Neo4j hybrid retrieval finds the top candidates (vector + graph signals)
3. A composite scoring formula reranks them
4. The top-K sections are injected into the system prompt alongside Barbara's persona instructions
5. LiteLLM calls the configured LLM provider and streams the response back to Gradio

See [System Overview](../architecture/system-overview.md) for the full pipeline diagram.

---

## Next Steps

<div class="grid cards" markdown>

-   :lock:{ .lg } **Passphrase & Tiers**

    Unlock deeper personal content by entering a passphrase.

    [:octicons-arrow-right-24: Learn more](tiers.md)

-   :question:{ .lg } **Asking Good Questions**

    Tips for getting rich, specific answers from the twin.

    [:octicons-arrow-right-24: User Guide](../user-guide/asking-good-questions.md)

-   :wrench:{ .lg } **Local Setup**

    Full installation guide with environment variables and optional services.

    [:octicons-arrow-right-24: Developer Docs](../developer-docs/local-setup.md)

</div>
