# Naruto Character Network Analysis

> *Exploring messy narratives, character dynamics, and what it means to balance an ensemble cast—through the lens of network science applied to anime.*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: In Development](https://img.shields.io/badge/Status-In%20Development-orange)]()

## Table of Contents
- [Project Overview](#project-overview)
- [Current Status](#current-status-phase-2---subtitle-pipeline-integrated-)
- [Methodology](#methodology)
- [Repository Structure](#repository-structure)
- [Quick Start Guide](#quick-start-guide)
- [Key Design Decisions](#key-design-decisions)
- [Known Limitations](#known-limitations)
- [Frequently Asked Questions](#frequently-asked-questions)
- [Tech Stack](#tech-stack)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Inspiration & References](#inspiration--references)
- [Contact](#contact)

## Project Overview

This project applies network science to analyze character relationships across key story arcs in Naruto, revealing patterns in character balance, narrative centrality, and ensemble dynamics. Inspired by the viral ["Network of Thrones"](https://www.maa.org/sites/default/files/pdf/Mathhorizons/NetworkofThrones%20%281%29.pdf) analysis, we combine rigorous statistical methods with a unique Sketchnote-inspired aesthetic.

### The Questions We're Answering

**Character Balance & Evolution**
- At what point did side characters become irrelevant?
- Which arc gave the most characters their "moment to shine"?
- When did Naruto become *too* central to the story?

**Network Structure**
- Do the arcs form natural communities matching geography and allegiances?
- How "small world" is the Naruto universe?
- Who are the "bridge characters" connecting different storylines?

**Fan Debates**
- Is Sakura really as "useless" as fans claim?
- Which villain had the most presence despite minimal screen time?
- What percentage of the story is told through the top 5 characters?

## Current Status: Phase 2 Complete - All 3 Arcs Extracted ✅

### Completed
- ✅ **Neo4j schema finalized** - Hybrid approach with `:CONNECTED` relationships
- ✅ **Character database complete** - 87 unique characters across 3 arcs (150 character-arc records)
- ✅ **Manual test edges created** - 36 canonical relationships (72 bidirectional)
- ✅ **Import pipeline built** - Python scripts generate ready-to-paste Cypher
- ✅ **Analytical queries ready** - 7 queries for testing and exploration
- ✅ **Subtitle parsing pipeline built** - Custom .ass and .srt parsers, scene segmentation, character detection, co-appearance edges
- ✅ **All 3 arcs fully extracted** with arc-specific output files:

| Arc | Episodes | Characters | Edges | Total Weight |
|-----|----------|------------|-------|-------------|
| **Pain's Assault** | 22 (.ass) | 48 | 212 | 611 |
| **Sasuke Retrieval** | 29 (.srt) | 33 | 93 | 311 |
| **Chunin Exams** | 18 of 48 (.srt) | 32 | 129 | 271 |

- ✅ **Batch ingestion with aggregation** - `scripts/batch_ingest.py` processes episodes and aggregates arc-level edges with episode provenance
- ✅ **13 automated tests passing** - ASS/SRT parsers, text cleaning, scene segmentation, mention matching

### In Progress
- [ ] Import extracted edges into local Neo4j instance
- [ ] Begin network analysis (centrality, community detection, entropy)

### Next Steps
- [ ] Run analytical queries and validate network structure
- [ ] Design visualization mockups

### Scope (Version 1.0)
Analyzing three S-tier arcs from Naruto Kai (fan-edited for optimal pacing):
- **Chunin Exams** (18 episodes: 50-67) - Finals tournament + Konoha Crush invasion
- **Sasuke Retrieval Mission** (29 episodes: 107-135) - Team spotlight & fracture
- **Pain's Assault** (22 episodes: 152-175) - Naruto-centric contrast

**Total**: 69 episodes spanning early Naruto through peak Shippuden

> **Note**: Chunin Exams episodes 20-49 are excluded due to poor-quality Italian fansubs in the available SRT files. The 18 episodes we process cover the finals and Konoha Crush — the most network-interesting portion of the arc.

### Why Naruto Kai?
We use fan-edited versions that remove flashback padding while preserving all canonical story beats. This "lean" analysis:
- Focuses on narratively dense moments
- Matches manga pacing more closely  
- Respects viewer time (50% more coverage for same effort)
- Represents the version many fans recommend

All findings will be validated against original broadcast versions.

## Methodology

### Graph Database: Neo4j

We use Neo4j to store and analyze the character network. Our schema features:

**Nodes**: Characters with multi-label pattern
- Base label: `:Character` (all 87 characters)
- Arc labels: `:ChūninExams`, `:SasukeRetrieval`, `:PainsAssault`
- Properties: name, aliases, affiliation, role type, importance score

**Relationships**: `:CONNECTED` (bidirectional)
- Properties: arc, weight, source, relationship_types, episodes, confidence
- Supports both manual test edges and future subtitle-extracted edges
- Relationship types: team, rivals, enemies, mentors, siblings, parents

See `docs/schema_diagram.svg` for visual representation and `docs/schema_decisions.md` for complete design rationale.

### Data Collection (Tier 1: Scene Co-Appearance)
Two characters have a relationship edge if they appear in the same scene. Edge weight represents the number of scenes shared.

**Scene Detection** (Implemented):
- Extract from .ass (Advanced SubStation Alpha) and .srt (SubRip) subtitle files
- Scene boundaries detected via dialogue timing gaps (>3 seconds)
- Character names identified via alias matching in dialogue text (word-boundary regex, longest-first)
- Cross-validated against episode summaries

**Current Status**: Pipeline validated across all 3 arcs (69 episodes total). Arc-level edge files include episode provenance for each co-appearance.

### Network Analysis
We calculate multiple centrality measures to understand character importance:
- **Degree Centrality**: Number of connections (breadth of relationships)
- **Betweenness Centrality**: Bridge characters connecting storylines
- **Eigenvector Centrality**: Connections to important characters
- **Community Detection**: Natural groupings (Louvain algorithm)

### Validation Sanity Checks
✅ Naruto should have highest degree centrality  
✅ Rock Lee and Gaara connected in Chunin Exams (their famous fight)  
✅ Pain connects to most Konoha characters (village attack)  
✅ Sound Four cluster together (team affiliation)

## Repository Structure

```
naruto-network-graph/
├── src/naruto_net/                      # Subtitle parsing pipeline (installable package)
│   ├── io/subtitles.py                  # .ass and .srt file parsers
│   ├── normalize/                       # Text cleaning, utterance splitting
│   ├── segment/scenes.py               # Gap-based scene segmentation
│   ├── detect/mentions.py              # Character alias matching
│   ├── build/edges.py                  # Co-appearance edge construction
│   └── qc/reports.py                   # QC reports
├── data/
│   ├── naruto-subtitle-files/          # 426 HorribleSubs .ass files (gitignored)
│   ├── intermediate/                   # Pipeline intermediate datasets (gitignored)
│   ├── processed/                      # Final edges and scene-character data
│   ├── reports/                        # QC reports (gitignored)
│   ├── chunin_exams_characters.csv     # 50 characters with metadata
│   ├── sasuke_retrieval_characters.csv # 50 characters with metadata
│   ├── pains_assault_characters.csv    # 50 characters with metadata
│   └── canonical_relationships.csv     # 36 manual test edges
├── scripts/
│   ├── 00_ass_ingest_subset.py         # Single-episode subtitle ingestion (.ass or .srt)
│   ├── batch_ingest.py                 # Arc-level batch processing with episode registry
│   ├── import_characters_to_neo4j.py   # Character import (generates Cypher)
│   └── import_test_edges.py            # Edge import (generates Cypher)
├── outputs/
│   ├── cypher_import_characters.cypher # Ready-to-paste character import
│   ├── cypher_import_edges.cypher      # Ready-to-paste edge import
│   └── analytical_queries.cypher       # 7 test/validation queries
├── tests/
│   ├── fixtures/                       # ASS + SRT excerpts and expected outputs
│   ├── test_ass_reader_parsing.py      # ASS parser correctness
│   ├── test_srt_reader.py             # SRT parser correctness
│   ├── test_text_cleaning.py           # Tag/newline cleaning
│   ├── test_scene_segmentation.py      # Scene segmentation coverage
│   └── test_mentions_matching.py       # Alias word-boundary matching
├── docs/
│   ├── schema_decisions.md             # Neo4j schema design rationale
│   ├── schema_diagram.svg              # Visual schema representation
│   └── BACKGROUND_RESEARCH.md          # Research notes and inspiration
├── pyproject.toml                       # Package config
├── requirements.txt                     # Python dependencies
├── README.md                           # This file
└── CLAUDE.md                           # AI agent instructions
```

## Quick Start Guide

### Prerequisites
- Neo4j Desktop or Neo4j Community Edition
- Python 3.10+

### Step 1: Set Up Neo4j Database

1. **Install Neo4j** ([Download Neo4j Desktop](https://neo4j.com/download/))
2. **Create a new database** named `naruto-network`
3. **Start the database**
4. **Open Neo4j Browser** (usually at http://localhost:7474)

### Step 2: Import Character Data

1. **Generate Cypher script**:
   ```bash
   python scripts/import_characters_to_neo4j.py
   ```
   This creates `outputs/cypher_import_characters.cypher`

2. **Import characters**:
   - Copy contents of `outputs/cypher_import_characters.cypher`
   - Paste into Neo4j Browser
   - Execute

3. **Verify**:
   ```cypher
   MATCH (c:Character) RETURN count(c);
   // Should return: 87
   ```

### Step 3: Import Relationships

1. **Generate Cypher script**:
   ```bash
   python scripts/import_test_edges.py
   ```
   This creates `outputs/cypher_import_edges.cypher`

2. **Import edges**:
   - Copy contents of `outputs/cypher_import_edges.cypher`
   - Paste into Neo4j Browser
   - Execute

3. **Verify**:
   ```cypher
   MATCH ()-[r:CONNECTED]->() RETURN count(r);
   // Should return: 72 (36 relationships × 2 for bidirectionality)
   ```

### Step 4: Explore the Network

Use the queries in `outputs/analytical_queries.cypher` to:
- Find characters appearing in all 3 arcs
- Rank characters by connection count
- Compare centrality across arcs
- Analyze relationship types
- Find shortest paths between characters

**Visualization in Neo4j Browser**:
```cypher
MATCH (c:Character)-[r:CONNECTED]-(other:Character)
RETURN c, r, other
LIMIT 100;
```

**Tips**:
- Color nodes by `affiliation_primary`
- Size nodes by `estimated_importance`
- Show `relationship_types` as edge labels
- Filter by arc: `WHERE r.arc = 'Chunin Exams'`

### Step 5: Run Subtitle Pipeline

The subtitle pipeline extracts character co-appearance edges from subtitle files. It supports both `.ass` and `.srt` formats.

**Single episode (ASS file)**:
```bash
python scripts/00_ass_ingest_subset.py \
    --subtitle data/naruto-subtitle-files/[HorribleSubs]*/episode.ass \
    --episode-id 014 \
    --characters-csv data/pains_assault_characters.csv \
    --gap-ms 3000
```

**Single episode (SRT file)**:
```bash
python scripts/00_ass_ingest_subset.py \
    --subtitle data/naruto-subtitle-files/srt-folder/Naruto\ 060\ English.srt \
    --episode-id 060 \
    --characters-csv data/chunin_exams_characters.csv \
    --gap-ms 3000
```

**Flags**:
| Flag | Description |
|------|-------------|
| `--subtitle` | Path to a `.ass` or `.srt` subtitle file (format auto-detected from extension) |
| `--episode-id` | Episode identifier used to label output files (e.g., `014`) |
| `--characters-csv` | Path to character CSV for alias matching |
| `--gap-ms` | Scene gap threshold in milliseconds (default: 3000) |
| `--out` | Output directory for intermediate datasets (default: `data/intermediate`) |
| `--emit-processed` | Also write final `edges.csv` and `scene_character.csv` to `data/processed/` |

**Batch processing (entire arc)**:
```bash
# List available arcs
python scripts/batch_ingest.py --list-arcs

# Process an arc (processes all episodes, then aggregates arc-level outputs)
python scripts/batch_ingest.py --arc pains-assault
python scripts/batch_ingest.py --arc sasuke-retrieval
python scripts/batch_ingest.py --arc chunin-exams

# Preview without running
python scripts/batch_ingest.py --arc pains-assault --dry-run
```

Per-episode intermediates (Parquet + CSV mirrors) go to `data/intermediate/`. Arc-level aggregated outputs go to `data/processed/` as `edges_{arc}.csv` and `scene_character_{arc}.csv`. The `edges` column in each file tracks which episodes contributed to each edge.

## Key Design Decisions

### Why Neo4j?
- **Native graph queries**: Natural fit for network analysis
- **Built-in algorithms**: Centrality, community detection, pathfinding
- **Visualization**: Neo4j Browser for exploration, export to D3.js for final viz
- **Scalability**: Easy to add more arcs or relationship types

### Why These Arcs?
- **Universally beloved** (S-tier consensus across fandom)
- **Narrative diversity** (ensemble → ensemble → solo focus)
- **Series transition** (Part I → Shippuden bridge → Shippuden peak)
- **Manageable scope** (prove methodology before expansion)

### Why Scene Co-Appearance?
- **Objective & replicable** (analog to GoT's "within 15 words")
- **Computationally tractable** for solo researcher
- **Captures all relationship types** (allies, enemies, mentors, teams)
- **Defensible methodology** for academic/professional presentation

### Why Sketchnote Aesthetic?
- **Differentiation** from standard network visualizations
- **Accessibility** (inviting, not intimidating)
- **Personality** (reflects playful nature of anime analysis)
- **Shareability** (stands out in social media feeds)

## Known Limitations

### Current Phase Constraints
- **Neo4j not yet populated**: Import scripts and Cypher files ready, import being tested now
- **Chunin Exams partial coverage**: Only episodes 50-67 (18 of 48) — episodes 20-49 excluded due to poor-quality Italian fansubs
- **Analysis pending**: Centrality metrics and community detection await Neo4j import

### Subtitle Data Constraints
- **Formats supported**: Both .ass (Advanced SubStation Alpha) and .srt (SubRip) via custom parsers
- **Shippuden coverage**: HorribleSubs .ass files for episodes 1-426 (Chunin Exams is Part 1, not in this set)
- **Original Naruto coverage**: .srt files available but episodes 1-49 are poor-quality Italian fansubs
- **Source**: HorribleSubs Crunchyroll fansubs (2017) for Shippuden; English-subtitles.org for original Naruto
- **Character detection**: Text-based alias matching (no explicit speaker tags in .ass format)
- **Honorifics**: Japanese suffixes (-sensei, -chan, -kun) need manual alias entries for full coverage

### Methodology Limitations
- **Scene co-appearance simplification**: Doesn't distinguish between positive/negative interactions (allies vs enemies both create edges)
- **Naruto Kai vs Original**: Using fan-edited versions may affect results compared to broadcast versions (all findings will be validated)
- **Scene boundary detection**: Subtitle timing gaps are heuristic-based and may miss rapid scene cuts
- **Short alias ambiguity**: Short character names (e.g., "Lee", "Guy") may match common words; confidence heuristic partially mitigates this

### Scope Limitations (V1.0)
- **3 arcs only**: Not a complete series analysis
- **No filler arcs**: Canon story arcs only (Kai versions exclude filler)
- **Character-centric**: Doesn't analyze jutsu, themes, or narrative structure
- **Static analysis**: Temporal dynamics within arcs not yet modeled

These limitations are acknowledged and will be addressed in future versions or documented in the methodology.

## Frequently Asked Questions

### Why Naruto Kai instead of original broadcast versions?
Naruto Kai is a fan-edited version that removes filler episodes and flashback padding while preserving all canon story beats. This gives us:
- **Narrative density**: Analysis focuses on plot-relevant interactions
- **Better pacing**: Matches manga structure more closely
- **Efficiency**: 50% more coverage for the same analysis effort
- **Fan preference**: Many fans consider Kai the "definitive" viewing experience

All findings will be validated against original broadcast versions to ensure accuracy.

### Can this methodology be applied to other anime?
Yes! The scene co-appearance method is generalizable to any show with subtitle files. The Neo4j schema could be adapted for:
- Other shonen anime (One Piece, Bleach, Hunter x Hunter)
- Ensemble dramas (Game of Thrones model)
- Long-running series with evolving character dynamics

The key requirements are: subtitle files, character lists, and clearly defined story arcs.

### How accurate is scene co-appearance as a relationship measure?
Scene co-appearance is a **proxy metric** with known trade-offs:

**Strengths:**
- Objective and replicable (no subjective interpretation)
- Captures all relationship types (allies, enemies, mentors, teams)
- Proven methodology (used in Network of Thrones)
- Computationally tractable for solo researcher

**Weaknesses:**
- Doesn't distinguish interaction type (fight vs conversation)
- May miss important off-screen relationships (letters, flashbacks)
- Sensitive to scene boundary detection accuracy

We address this by:
1. Manual test edges validate the automated extraction
2. Relationship types are separately coded (team, rivals, enemies, etc.)
3. Cross-validation against episode summaries

### When will the full analysis be published?
**Roadmap timeline:**
- Phase 1 (Complete): Neo4j setup and schema design
- Phase 2 (Feb 2025): Data import and subtitle parsing pipeline
- Phase 3 (Mar 2025): Network analysis and findings
- Phase 4 (Mar 2025): Interactive visualization
- Phase 5 (Apr 2025): Public launch and writeup

Follow progress on [GitHub](https://github.com/yourusername/naruto-network-files) or connect on [LinkedIn](https://www.linkedin.com/in/barbara-hidalgo-sotelo).

### Is the dataset publicly available?
Not yet, but it will be! Once V1.0 is complete, we'll release:
- Character CSVs with metadata
- Edge lists with relationship types
- Neo4j import scripts
- Analytical query examples
- Visualization code

This project is MIT licensed - you're free to use, modify, and extend it.

## Tech Stack

**Graph Database**: Neo4j
- Native graph storage and querying
- Cypher query language
- Built-in graph algorithms

**Data Pipeline**: Python
- `naruto_net` - Custom .ass/.srt subtitle parsers, scene segmentation, character detection
- `pandas` - Data manipulation
- `pyarrow` - Parquet output for intermediate datasets
- `networkx` - Graph construction and analysis
- `matplotlib`/`seaborn` - Exploratory visualization

**Final Visualization**: Web-based
- D3.js - Interactive network layouts
- SVG - Hand-drawn annotation overlays
- Vanilla JS - No framework overhead
- GitHub Pages - Free hosting

## Roadmap

### Phase 1: Neo4j Setup ✅ (Completed Feb 2025)
- [x] Define Neo4j schema
- [x] Document design decisions
- [x] Create character database (87 characters)
- [x] Generate manual test edges (36 relationships)
- [x] Build Python import scripts
- [x] Create analytical test queries
- [x] Produce schema visualization

### Phase 2: Data Pipeline ✅ (Completed Feb 2026)
- [ ] Import data into Neo4j instance
- [ ] Validate network structure with test queries
- [x] Build subtitle parsing pipeline (`src/naruto_net/` + `scripts/00_ass_ingest_subset.py`)
- [x] Validate pipeline on test episode (Episode 014)
- [x] Add SRT subtitle support (`SrtReader` class in `src/naruto_net/io/subtitles.py`)
- [x] Build batch ingestion script with arc-level aggregation (`scripts/batch_ingest.py`)
- [x] Map episode numbers for all 3 arcs in arc registry
- [x] Extract scene co-appearance edges across all 3 target arcs (69 episodes, 434 edges total)
- [ ] Validate extracted edges against manual test edges

### Phase 3: Analysis (Feb-Mar 2025)
- [ ] Calculate centrality metrics per arc
- [ ] Run community detection algorithms
- [ ] Compute character balance entropy
- [ ] Answer core 3 research questions
- [ ] Create analysis notebooks

### Phase 4: Visualization (Mar 2025)
- [ ] Design Sketchnote-inspired mockups
- [ ] Build D3.js force-directed layout
- [ ] Add hand-drawn SVG annotations
- [ ] Implement interactive filtering
- [ ] Polish for shareability

### Phase 5: Launch (Apr 2025)
- [ ] Portfolio writeup
- [ ] Share on anime communities (r/anime, r/Naruto)
- [ ] Write blog post / Medium article
- [ ] Submit to data viz showcases
- [ ] Release dataset publicly

## Contributing

This is currently a solo portfolio project, but feedback and suggestions are welcome! Please open an issue if you:
- Spot data quality issues
- Have questions about methodology
- Want to replicate with different arcs/anime
- Find bugs in the code

## Inspiration & References

This project stands on the shoulders of giants:

**Academic Foundation**:
- Beveridge, A. & Shan, J. (2016). "Network of Thrones." *Math Horizons*, 23(4), 18-22.

**Visual Inspiration**:
- Network of Thrones visualizations
- Mike Rohde's Sketchnote work
- Flowing Data network examples
- The Pudding's data storytelling

**Technical References**:
- Neo4j Graph Data Science Library
- NetworkX documentation
- D3.js force-directed graph examples

## License

MIT License - See [LICENSE](LICENSE) for details

## Contact

**Barbara Hidalgo Sotelo** - Data Scientist & AI Consultant
- Portfolio: [barbhs.com](https://barbhs.com)
- LinkedIn: [linkedin.com/in/barbara-hidalgo-sotelo](https://www.linkedin.com/in/barbara-hidalgo-sotelo)
- Email: barbs@balex.com

---

*"Exploring messy data, intelligent systems, and what it means to make meaning—through the lens of a cognitive scientist who builds things people actually use."*

**Dattebayo!** 🍜

---

**Last Updated**: 2026-02-18
**Current Status**: All 3 arcs extracted (69 episodes, 434 edges), ready for network analysis
