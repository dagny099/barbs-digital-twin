# Digital Twin: Barbara Hidalgo-Sotelo

A conversational AI digital twin powered by RAG (Retrieval-Augmented Generation) that embodies Barbara Hidalgo-Sotelo's professional knowledge, project portfolio, and personal expertise. Built with Python, Gradio, ChromaDB, and OpenAI's GPT models.

## Overview

This digital twin serves as an intelligent interface to explore Barbara's professional background, technical projects, and expertise. It uses vector embeddings and semantic search to retrieve relevant context from multiple knowledge sources, then generates responses in Barbara's voice and personality.

**Live Demo:** [Hugging Face Spaces](https://huggingface.co/spaces/YOUR-USERNAME/digital-twin) *(Update with your actual URL)*

## Features

- **Multi-Source Knowledge Base**: Integrates biographical information, GitHub project READMEs, and MkDocs documentation
- **Semantic Search & RAG**: ChromaDB vector store with OpenAI embeddings for intelligent context retrieval
- **Conversational Interface**: Gradio ChatInterface for natural conversations
- **Tool Integration**: Function calling capabilities (notifications via Pushover, interactive features)
- **First-Person Perspective**: Responds as Barbara, maintaining her voice and personality
- **Persistent Memory**: ChromaDB enables incremental knowledge base updates without reprocessing

## Tech Stack

| Component | Technology |
|-----------|------------|
| **LLM** | OpenAI GPT-4.1-mini |
| **Embeddings** | OpenAI text-embedding-3-small (1536 dimensions) |
| **Vector Database** | ChromaDB (persistent local storage) |
| **UI Framework** | Gradio |
| **Language** | Python 3.11 |
| **Deployment** | Hugging Face Spaces |

## Architecture

```
User Query
    ↓
Gradio Interface
    ↓
Query Embedding (OpenAI)
    ↓
Semantic Search (ChromaDB) → Retrieve top 3 chunks
    ↓
Context + System Prompt + Query → LLM
    ↓
[Optional] Tool Calls (notifications, dice roll)
    ↓
Final Response (as Barbara)
```

### Data Processing Pipeline

1. **Chunking**: Text split into ~500-character chunks with 50-character overlap
2. **Embedding**: Each chunk embedded via OpenAI API
3. **Storage**: Chunks + embeddings + metadata stored in ChromaDB
4. **Retrieval**: Query embedded → top-k semantic search → context injection

## Installation & Setup

### Prerequisites

- Python 3.11+
- OpenAI API key
- (Optional) Pushover API credentials for notifications

### Local Setup

1. **Clone the repository**
```bash
git clone https://github.com/YOUR-USERNAME/digital-twin.git
cd digital-twin
```

2. **Create and activate virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set environment variables**
```bash
export OPENAI_API_KEY="your-openai-key"
export PUSHOVER_USER="your-pushover-user"  # Optional
export PUSHOVER_TOKEN="your-pushover-token"  # Optional
```

Or create a `.env` file:
```
OPENAI_API_KEY=your-openai-key
PUSHOVER_USER=your-pushover-user
PUSHOVER_TOKEN=your-pushover-token
```

5. **Run the application**
```bash
python app.py
```

The Gradio interface will launch at `http://localhost:7860`

## Usage

### For Recruiters & Employers

Ask the digital twin about:
- Barbara's technical skills and certifications
- Specific projects and their technical implementations
- Professional experience and achievements
- Educational background (UT Austin, MIT PhD)
- Research publications and contributions

**Example queries:**
- "What experience do you have with data governance?"
- "Tell me about your fitness dashboard project"
- "What certifications do you hold?"
- "Describe your work at Inflective"

### For Developers

The digital twin can explain:
- Technical architecture of specific projects
- Code implementations and design decisions
- Tech stack choices and trade-offs
- Development workflows and best practices

**Example queries:**
- "How does the beehive tracker handle metadata?"
- "What graph database technologies have you used?"
- "Explain the architecture of your fitness dashboard"

### For General Users

Learn about:
- Barbara's journey from cognitive science to data science
- Her research on visual attention and eye movements
- Personal projects and hobbies (beekeeping, running, etc.)
- Philosophy and approach to learning/building

## Project Structure

```
digital-twin/
├── app.py                          # Main Gradio application
├── embed_readmes.py                # Script to embed GitHub READMEs
├── embed_mkdocs.py                 # Script to embed MkDocs sites
├── requirements.txt                # Python dependencies
├── barbara-hidalgo-sotelo-biosketch.md  # Biographical source (authoritative)
├── .chroma_db_DT/                  # ChromaDB vector store (gitignored)
├── READMEs/                        # GitHub project README files
│   ├── fitness-dashboard_README.md
│   ├── beehive-tracker_README.md
│   └── ...
├── RESUME-EXPLORER/                # Additional project documentation
├── .venv/                          # Virtual environment (gitignored)
└── README.md                       # This file
```

## Data Sources

The digital twin's knowledge base uses **section-aware metadata** to track document structure and improve retrieval accuracy.

### Metadata Schema
Each chunk includes:
```python
{
    'source': 'source-type:identifier',  # e.g., 'resume:2026.txt', 'biosketch:barbara.md'
    'section': 'Section Name' or None,   # e.g., 'Professional Experience', 'Education'
    'chunk_index': 0                     # position within section (resets per section)
}
```

### 1. Biographical Sketch (Authoritative) ⭐
- **File**: `barbara-hidalgo-sotelo-biosketch.md`
- **Priority**: Highest - source of truth for identity, background, values, personality
- **Sections**: 18 sections (Personal Information, Family, Education, Professional Career, etc.)
- **Chunks**: ~52 chunks with section metadata
- **Parsing**: Markdown headers (## level 2)

### 2. Resume
- **File**: `Hidalgo-Sotelo_Barbara_RESUME_AI-Engineering_2026.txt`
- **Sections**: 8 sections (Summary, Core Strengths, Professional Experience, Education, etc.)
- **Chunks**: ~20 chunks with section metadata
- **Parsing**: Text delimiter (`======`)

### 3. GitHub Project READMEs
- **Folder**: `READMEs/`
- **Count**: 39 repositories
- **Chunks**: ~700 chunks (no section metadata yet)
- **Content**: Technical project descriptions, implementations, usage guides
- **Future**: Will add section parsing by numbered headers (# 1., # 2., etc.)

### 4. MkDocs Documentation Sites
- **Sites**: 8 documentation sites hosted at docs.barbhs.com
- **Chunks**: ~8,600 chunks with section metadata (using page titles)
- **Content**: Detailed project documentation, user guides, technical deep-dives
- **Examples**: fitness-dashboard, beehive-tracker, chronoscope, convoscope

### Total Collection Stats
- **Total chunks**: ~9,400
- **With sections**: 92.5% (biosketch, resume, MkDocs)
- **Without sections**: 7.5% (READMEs)

### Adding New Knowledge

All embedding is now handled by dedicated scripts with section-aware parsing:

**Initial setup:**
```bash
python embed_biosketch.py      # Authoritative source first
python embed_resume.py         # Resume with sections
python embed_readmes.py        # Project READMEs
python embed_mkdocs.py         # Documentation sites
```

**Re-embed after updates:**
```bash
python embed_biosketch.py --force-reembed
python embed_resume.py --force-reembed
python embed_readmes.py        # Skips already-embedded files
python embed_mkdocs.py         # Skips already-embedded pages
```

**Test parsing without embedding:**
```bash
python embed_resume.py --dry-run
python embed_biosketch.py --dry-run
```

**Verify collection:**
```bash
python verify_collection.py --show-sources --show-sections
```

## Shared Utilities (utils.py)

The project now uses a centralized `utils.py` module to eliminate code duplication:

### Core Functions
- **`chunk_prose()`**: Paragraph-aware text chunking with overlap
- **`parse_paragraphs()`**: Split text on blank lines
- **`parse_sections_by_delimiter()`**: Parse TXT files by delimiter (e.g., `======`)
- **`parse_markdown_sections()`**: Parse markdown files by headers (e.g., `##`)
- **`build_metadata()`**: Construct standardized metadata dicts

All ingestion scripts (`app.py`, `embed_biosketch.py`, `embed_resume.py`, `embed_readmes.py`, `embed_mkdocs.py`) import from `utils.py` to ensure consistency.

## Chunking Strategy

- **Chunk Size**: ~500 characters (configurable)
- **Overlap**: 50 characters (configurable)
- **Atomic Unit**: Paragraphs (double-newline delimited)
- **Principle**: Never split mid-sentence; overlap re-includes trailing paragraphs
- **chunk_index semantics**: Resets to 0 for each section (not global)

This approach balances:
- Semantic coherence (paragraphs as natural units)
- Retrieval granularity (500 chars ≈ 1-2 paragraphs)
- Context continuity (overlap prevents boundary issues)
- Section awareness (chunks know their parent section)

## Deployment

### Hugging Face Spaces

The app is deployed on Hugging Face Spaces. To deploy your own:

1. Create a Space at [huggingface.co/spaces](https://huggingface.co/spaces)
2. Add these files to your Space:
   - `app.py`
   - `requirements.txt`
   - `barbara-hidalgo-sotelo-biosketch.md` (and other data sources)
3. Set Secrets in Space settings:
   - `OPENAI_API_KEY`
   - `PUSHOVER_USER` (optional)
   - `PUSHOVER_TOKEN` (optional)
4. Push to deploy

**Note**: The ChromaDB database (`.chroma_db_DT/`) will be recreated on first run. For faster startup, you can include the pre-built database in your deployment.

## Roadmap

- [ ] **Multi-modal support**: Integrate image understanding for project screenshots
- [ ] **Citation tracking**: Return source documents with responses
- [ ] **Conversation memory**: Implement session-based memory across conversations
- [ ] **Analytics dashboard**: Track query patterns and popular topics
- [ ] **Voice interface**: Add speech-to-text/text-to-speech capabilities
- [ ] **Fine-tuning**: Train a custom model on Barbara's writing style
- [ ] **Knowledge graph integration**: Neo4j backend for relationship-rich queries
- [ ] **Automated updates**: GitHub Actions to re-embed on repo changes
- [ ] **Evaluation suite**: Automated testing of response quality and accuracy

## Key Design Decisions

### Why ChromaDB?
- **Persistent storage**: No re-embedding on restart
- **Lightweight**: Runs locally without external dependencies
- **Python-native**: Seamless integration with OpenAI SDK
- **Metadata filtering**: Supports source-based filtering and priority rules

### Why GPT-4.1-mini?
- **Cost-effective**: Lower API costs for a personal project
- **Fast**: Quick response times for interactive chat
- **Tool-calling**: Native function calling support
- **Sufficient capability**: Adequate for RAG + personality emulation

### Why 500-character chunks?
- **Context window**: Fits 3 chunks comfortably in context with room for conversation
- **Semantic unit**: Aligns with paragraph-level ideas
- **Retrieval quality**: Small enough for precision, large enough for coherence

## Contributing

This is a personal project, but suggestions and ideas are welcome! Feel free to:
- Open issues for bugs or feature requests
- Submit PRs for improvements (especially documentation)
- Fork the repo to create your own digital twin

## License

This project is open-source under the MIT License. See `LICENSE` file for details.

The biographical content and project descriptions are © Barbara Hidalgo-Sotelo. Reuse of the *code/architecture* is encouraged; reuse of the *personal content* should be adapted to your own story.

## Contact & Links

- **Personal Site**: [barbhs.com](https://www.barbhs.com/)
- **LinkedIn**: [barbara-hidalgo-sotelo](https://www.linkedin.com/in/barbara-hidalgo-sotelo)
- **GitHub**: [dagny099](https://github.com/dagny099)
- **Google Scholar**: [Barbara Hidalgo-Sotelo](https://scholar.google.com/citations?hl=en&user=nQG25vkAAAAJ)

---

**Built with curiosity, engineered with precision.**
*"I can, I will, and I shall!"* - Barbara's mantra
