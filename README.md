# Digital Twin: Barbara Hidalgo-Sotelo

A conversational AI digital twin powered by RAG (Retrieval-Augmented Generation) that embodies Barbara Hidalgo-Sotelo's professional knowledge, project portfolio, and personal expertise. Built with Python, Gradio, ChromaDB, and OpenAI's GPT models.

## Overview

This digital twin serves as an intelligent interface to explore Barbara's professional background, technical projects, and expertise. It uses vector embeddings and semantic search to retrieve relevant context from multiple knowledge sources, then generates responses in Barbara's voice and personality.

**Live Demo:** [Hugging Face Spaces](https://huggingface.co/spaces/YOUR-USERNAME/digital-twin) *(Update with your actual URL)*

## Features

- **Multi-Source Knowledge Base**: Integrates biographical sketch, resume, publications, project summaries, MkDocs documentation, and the live website
- **Semantic Search & RAG**: ChromaDB vector store with OpenAI embeddings for intelligent context retrieval
- **Section-Aware Ingestion**: Each data source is parsed into named sections, giving the LLM precise provenance for every retrieved chunk
- **Conversational Interface**: Gradio ChatInterface for natural conversations
- **Tool Integration**: Function calling capabilities (notifications via Pushover, interactive features)
- **First-Person Perspective**: Responds as Barbara, maintaining her voice and personality
- **Persistent Memory**: ChromaDB enables incremental knowledge base updates without reprocessing
- **Ingestion Manager**: Single `ingest.py` script orchestrates all data sources with an interactive status-first menu

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

## Customizing Suggested Questions

The example questions shown in the Gradio interface can be easily customized in `app.py`.

### Quick Edit

Edit the `CURATED_EXAMPLES` list (around line 43 in `app.py`):

```python
CURATED_EXAMPLES = [
    "💼 Your professional question here",
    "🔗 Your bridge question here",
    "💭 Your personal question here",
]
```

### Question Categories

The interface uses three visual categories with color-coding:

| Icon | Category | Color | Purpose |
|------|----------|-------|---------|
| 💼 | Professional | Soft Blue | Career, technical skills, work experience |
| 🔗 | Bridge | Soft Teal | Questions connecting personal and professional |
| 💭 | Personal | Soft Purple | Interests, hobbies, philosophy, learning |

**Current distribution:** 3 professional + 3 bridge + 3 personal = 9 questions total

### Full Question Banks

Two complete question sets are stored as constants for reference and evaluation testing:

- **`RECRUITER_PROMPTS`** (10 questions): Professional/hiring-focused questions
- **`FRIENDLY_PROMPTS`** (10 questions): Casual/personal questions from friends

You can pull questions from these banks or write your own.

### Updating Colors

If you change the number of questions or reorder them, update the CSS selectors in `custom_css` (around line 205 in `app.py`) to match:

```python
/* Professional questions (positions 1-3) */
.examples button:nth-child(1),
.examples button:nth-child(2),
.examples button:nth-child(3) { ... }

/* Bridge questions (positions 4-6) */
.examples button:nth-child(4),
.examples button:nth-child(5),
.examples button:nth-child(6) { ... }

/* Personal questions (positions 7-9) */
.examples button:nth-child(7),
.examples button:nth-child(8),
.examples button:nth-child(9) { ... }
```

The `:nth-child(N)` numbers must match the position of each question in the list.

## Project Structure

```
digital-twin/
├── app.py                              # Main Gradio application
├── ingest.py                           # Master ingestion manager (start here)
├── embed_biosketch.py                  # Embed biographical sketch
├── embed_resume.py                     # Embed resume with section parsing
├── embed_publications.py               # Embed academic publications
├── embed_project_summaries.py          # Embed one-page project summary PDFs
├── embed_mkdocs.py                     # Embed MkDocs documentation sites
├── embed_jekyll.py                     # Embed Jekyll website via sitemap
├── utils.py                            # Shared text processing utilities
├── verify_collection.py                # Inspect ChromaDB contents
├── clear_collection.py                 # Wipe ChromaDB collection
├── requirements.txt                    # Python dependencies
├── inputs/
│   ├── barbara-hidalgo-sotelo-biosketch.md   # Biographical source (authoritative)
│   ├── barbara-publications.md               # Academic publications + URLs
│   ├── Hidalgo-Sotelo_Barbara_RESUME_AI-Engineering_2026.txt
│   ├── publications.md                       # Source Jekyll page for publications
│   ├── READMEs/                              # GitHub project README files (archived)
│   └── project-summaries/                    # One-page PDF summaries (20 projects)
├── .chroma_db_DT/                      # ChromaDB vector store (gitignored)
├── .venv/                              # Virtual environment (gitignored)
└── README.md                           # This file
```

## Knowledge Base Management

### Ingestion Manager (`ingest.py`)

The recommended way to manage all data sources. Run it with no arguments for an interactive menu that shows current DB status before asking you to do anything:

```bash
python ingest.py
```

The menu displays a live status table — chunk counts per source, so you can see at a glance what's embedded and what isn't:

```
  #   Source                 Description                                Status
  1   biosketch ⭐            inputs/barbara-hidalgo-sotelo-...          ✅  42 chunks
  2   resume                 inputs/Hidalgo-Sotelo_Barbara_...           ✅  31 chunks
  3   publications           inputs/barbara-publications.md             ✅  12 chunks
  4   project-summaries      inputs/project-summaries/ (20 PDFs)        ✅  98 chunks
  5   jekyll                 https://barbhs.com (via sitemap)           ✅  210 chunks
  6   mkdocs                 8 sites at docs.barbhs.com                 ✅  963 chunks
```

Select a source by number → choose "Embed", "Force re-embed", or "Dry run".

**Non-interactive flags** (for scripting or CI/CD):
```bash
python ingest.py --status                          # Show DB status and exit
python ingest.py --all                             # Embed all sources
python ingest.py --all --force                     # Force re-embed everything
python ingest.py --source biosketch                # Embed one source
python ingest.py --source biosketch --force        # Force re-embed one source
python ingest.py --source project-summaries --dry-run  # Preview without embedding
```

**Source keys**: `biosketch`, `resume`, `publications`, `project-summaries`, `jekyll`, `mkdocs`

### Checking DB Contents

```bash
python ingest.py --status                          # Quick chunk counts per source
python verify_collection.py                        # Detailed stats + sample chunks
python verify_collection.py --show-sources         # Per-source breakdown
python verify_collection.py --show-sections        # All unique section names
```

### Wiping the DB

```bash
python clear_collection.py                         # Interactive confirmation required
```

---

## Data Sources

The knowledge base uses **section-aware metadata** so the LLM knows exactly where each retrieved chunk came from within a document.

### Metadata Schema
```python
{
    'source': 'source-type:identifier',  # e.g., 'resume:2026.txt', 'publication:barbara-publications.md'
    'section': 'Section Name' or None,   # e.g., 'Professional Experience', 'Published Papers'
    'chunk_index': 0                     # position within section (resets per section)
}
```

### 1. Biographical Sketch (Authoritative) ⭐
- **File**: `inputs/barbara-hidalgo-sotelo-biosketch.md`
- **Priority**: Highest — source of truth for identity, background, values, personality
- **Parsing**: Markdown `##` headers → named sections
- **Wins over**: all other sources in any conflict

### 2. Resume
- **File**: `inputs/Hidalgo-Sotelo_Barbara_RESUME_AI-Engineering_2026.txt`
- **Parsing**: `======` delimiters → named sections (Summary, Experience, Education, etc.)

### 3. Publications
- **File**: `inputs/barbara-publications.md`
- **Content**: Academic papers and conference posters with absolute PDF URLs
- **Parsing**: Markdown `##` headers → Overview, Research Focus, Published Papers, Conference Posters
- **Note**: URLs point to `barbhs.com/assets/docs/`. Full-text ingestion planned for a future version.

### 4. Project Summaries
- **Folder**: `inputs/project-summaries/` (20 one-page PDFs)
- **Content**: Curated one-pagers following a consistent template: What it is / Who it's for / What it does / How it works
- **Parsing**: Template-aware section detection (fuzzy prefix matching on known section labels)
- **Special**: Each document also gets a synthetic "overview" chunk combining the title + What it is + Who it's for, optimized for portfolio-style queries
- **Metadata extras**: `project_name`, `tech_stack` (comma-joined list of detected technologies)

### 5. Jekyll Website
- **URL**: `https://barbhs.com` (fetched live via sitemap.xml)
- **Tool**: `trafilatura` for main-content extraction (strips nav/footer automatically)
- **Parsing**: Page title used as section name; each page is one document

### 6. MkDocs Documentation Sites
- **Sites**: 8 sites at `docs.barbhs.com`
- **Fetched via**: `search_index.json` endpoint (pre-extracted clean text, no HTML parsing)
- **Content**: Detailed project docs, user guides, architecture notes

## Shared Utilities (utils.py)

The project now uses a centralized `utils.py` module to eliminate code duplication:

### Core Functions
- **`chunk_prose()`**: Paragraph-aware text chunking with overlap
- **`parse_paragraphs()`**: Split text on blank lines
- **`parse_sections_by_delimiter()`**: Parse TXT files by delimiter (e.g., `======`)
- **`parse_markdown_sections()`**: Parse markdown files by headers (e.g., `##`)
- **`build_metadata()`**: Construct standardized metadata dicts

All ingestion scripts import from `utils.py` to ensure consistent chunking behavior across all sources.

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
   - `inputs/` folder (all data sources)
   - Pre-built `.chroma_db_DT/` (recommended — avoids cold-start re-embedding)
3. Set Secrets in Space settings:
   - `OPENAI_API_KEY`
   - `PUSHOVER_USER` (optional)
   - `PUSHOVER_TOKEN` (optional)
4. Push to deploy

**Note**: The ChromaDB database (`.chroma_db_DT/`) will be recreated on first run. For faster startup, you can include the pre-built database in your deployment.

## Evaluation

The project includes an offline evaluation harness for systematically testing response quality. See `EVAL_QUICKSTART.md` for the 5-minute getting started guide and `EVAL_WORKFLOW.md` for full documentation.

### Two-axis question design

**92 seed questions** in `eval_questions.csv` organized around two perspectives:

| Type | Categories | Purpose |
|------|------------|---------|
| **Coverage** | `bio`, `projects`, `technical`, `personality`, `tool`, `publication` | Does the system retrieve and answer correctly? Run after knowledge base changes. |
| **Visitor** | `recruiter`, `friendly` | Does the system satisfy real visitors? Mirrors `RECRUITER_PROMPTS` / `FRIENDLY_PROMPTS` in `app.py`. |

### Quick commands

```bash
# Full evaluation (~$0.21, ~5 min)
python run_evals.py

# Coverage only — fast regression check after re-embedding
python run_evals.py --category bio
python run_evals.py --category publication

# Visitor experience check after prompt changes
python run_evals.py --category recruiter
python run_evals.py --category friendly

# Analyze and export for manual grading
python analyze_evals.py --export
```

## Roadmap

- [ ] **Multi-modal support**: Integrate image understanding for project screenshots
- [ ] **Citation tracking**: Return source documents with responses
- [ ] **Conversation memory**: Implement session-based memory across conversations
- [ ] **Analytics dashboard**: Track query patterns and popular topics
- [ ] **Voice interface**: Add speech-to-text/text-to-speech capabilities
- [ ] **Fine-tuning**: Train a custom model on Barbara's writing style
- [ ] **Knowledge graph integration**: Neo4j backend for relationship-rich queries
- [ ] **Automated updates**: GitHub Actions to re-embed on repo changes
- [x] **Evaluation suite**: 91-question offline eval harness across 8 categories (see `EVAL_QUICKSTART.md`)

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
