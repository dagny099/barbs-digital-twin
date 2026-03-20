# MindMap Mastery

> **Interactive Knowledge Graph Visualization from Wikidata**

Transform any person, place, or creative work into an interactive network visualization by exploring their relationships in Wikidata's vast knowledge base.

[![Project Status](https://img.shields.io/badge/status-beta-yellow)](https://github.com)
[![Python Version](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## 🎯 What Does This Do?

MindMap Mastery lets you:

1. **Search** for any entity (musicians, authors, locations, organizations)
2. **Discover** their properties and relationships from Wikidata
3. **Visualize** the knowledge graph as an interactive network
4. **Explore** connections with configurable styling and filtering
5. **Export** data and visualizations for further analysis

### Example Query Flow

```
Input: "Gabriel Garcia Marquez"
  ↓
Wikidata Search → Finds Q5878 (Colombian novelist)
  ↓
SPARQL Queries → Retrieves 50+ properties (occupation, genre, birthplace, works...)
  ↓
Visualization → Interactive graph showing relationships
  ↓
Output: HTML graph + CSV data exports
```

---

## ✨ Features

### 🟢 Working Now
- ✅ **Entity Reconciliation**: Search Wikidata with fuzzy matching and confidence scores
- ✅ **SPARQL Integration**: Retrieve entity properties and relationships
- ✅ **Batch API Processing**: Efficiently fetch metadata for 50+ properties at once
- ✅ **Interactive Visualizations**: PyVis network graphs with physics-based layouts
- ✅ **Configurable Styling**: JSON-based node grouping (Critical/Location/Demographic)
- ✅ **Data Export**: Structured CSV exports for properties and values
- ✅ **Standalone Script**: Generate visualizations from pre-fetched Excel data

### 🟡 In Progress
- ⚠️ **Streamlit Web UI**: Basic search works, but selection and visualization not yet integrated
- ⚠️ **Session State**: Limited caching and state persistence

### 🔴 Planned
- ❌ **Multi-Source Integration**: Combine Wikidata with Discogs, Spotify, Last.fm, MusicBrainz
- ❌ **Schema Editor**: Real-time editing of visualization properties
- ❌ **Graph Database**: Persistent storage in Neo4j or DynamoDB
- ❌ **Multi-Hop Exploration**: Navigate beyond first-degree connections
- ❌ **AI-Powered Routing**: LLM-based data source selection

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- pip package manager

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd "Barb Wiki Viz"

# Activate virtual environment
source .llama-neo/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

#### Option 1: Streamlit Web UI (Partial)
```bash
streamlit run main.py
```

**Current Limitation:** The UI shows entity search results but doesn't yet fetch properties or render graphs. See [Contributing](#-contributing) to help complete it!

#### Option 2: Jupyter Notebooks (Full Workflow)
```bash
jupyter notebook
```

Open `Create_Web.ipynb` for a complete end-to-end example:
- Cell 1-2: Search for an entity
- Cell 3-4: Fetch properties via SPARQL
- Cell 5-6: Retrieve property values
- Cell 7-8: Generate interactive visualization

#### Option 3: Standalone Script
```bash
python build_network_viz.py
```

Requires input file: `TEMPLATE_VIZ.xlsx`

---

## 📖 Usage Examples

### Example 1: Basic Entity Search (Notebook)

```python
from helperFunc import reconcile_entity, evaluate_matches

# Search for an entity
results = reconcile_entity(
    service_url="https://wikidata.reconci.link/en/api",
    query_string="Les Claypool",
    limit_matches=5
)

# Filter by confidence score
matches = evaluate_matches(results, threshold=60)

# Output:
# [{'name': 'Les Claypool', 'id': 'Q312387', 'score': 100, ...}]
```

### Example 2: Fetch Entity Properties

```python
from helperFunc import fetch_related_properties, fetch_wikidata_entities
import pandas as pd

# Get all properties for the entity
entity_id = "Q312387"  # Les Claypool
df = fetch_related_properties(entity_id, qname="Les Claypool", score=100)

# Get human-readable labels
pids = list(set(df['prop_ID']))
df_labels = fetch_wikidata_entities(pids)

# Merge data
full_data = pd.merge(df, df_labels, on='prop_ID')
print(full_data[['prop_ID', 'label', 'description']].head())

# Output:
#   prop_ID  label              description
#   P106     occupation         occupation of a person
#   P136     genre              creative work's genre
#   P264     record label       brand and trademark...
```

### Example 3: Generate Visualization

```python
from helperFunc import wrap_fetch_related, etl_node_metadata, build_network_graph

# Fetch all property values (takes ~1 min per 50 properties due to rate limiting)
prop_values = wrap_fetch_related(entity_id, full_data)

# Transform for visualization
nodes_metadata = etl_node_metadata(prop_values)

# Build graph
net = build_network_graph(nodes_metadata)
net.show("les_claypool_knowledge_graph.html")

# Output: Interactive HTML file with graph visualization
```

### Example 4: Customize Visualization

Edit `conf_props2vis.csv` to control what appears in the graph:

```csv
TYPE,prop_ID,related_propertyLabel,group,description
NODE,P136,genre,Critical,"Music genre"
NODE,P264,record label,Critical,"Record label"
PROPERTY,P569,date of birth,,"Birth date (metadata only)"
```

- `NODE` = Shows as graph node
- `PROPERTY` = Attached as metadata to main node
- `group` = Visual styling (Critical/Location/Demographic)

---

## 🏗️ Architecture Overview

### Data Flow

```
User Input → Reconciliation API → SPARQL Queries → Wikidata API → DataFrame → PyVis Graph
```

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| **Web UI** | `main.py` | Streamlit interface (incomplete) |
| **Core Functions** | `helperFunc.py` | API integration, data processing |
| **Visualization** | `build_network_viz.py` | Standalone graph generator |
| **Configuration** | `conf_props2vis.csv` | Property → visualization mapping |
| **Styling** | `group_formatting.json` | Node/edge visual settings |
| **Database** | `init_db.py` | DynamoDB utilities (optional) |

### Technology Stack

- **Frontend**: Streamlit, PyVis (vis.js)
- **Data Sources**: Wikidata Reconciliation API, SPARQL, MediaWiki API
- **Data Processing**: Pandas, JSON/CSV
- **Visualization**: PyVis network graphs
- **Storage**: CSV exports, optional DynamoDB

For detailed architecture documentation, see [CLAUDE.md](CLAUDE.md).

---

## 📊 Project Status

**Completion:** ~45% (Core backend complete, UI needs integration)

### What Works
- Backend SPARQL/API integration: **100%**
- Data transformation pipeline: **100%**
- Visualization generation: **100%** (notebooks/scripts)
- Configuration system: **90%**

### What Needs Work
- Streamlit UI integration: **30%**
- Error handling: **20%**
- Session state management: **20%**
- Multi-source API integration: **5%**
- Testing: **0%**

### Known Issues

1. **Streamlit UI Incomplete**: Search works, but entity selection and graph rendering not integrated
2. **Code Duplication**: `init.py` and `helperFunc.py` have identical functions
3. **No Error Handling**: API failures will crash the app
4. **Rate Limiting Required**: Wikidata SPARQL requires 0.9s delays between requests
5. **No Automated Tests**: Manual testing only

See [CHANGELOG.md](CHANGELOG.md) for version history.

---

## 🤝 Contributing

Contributions welcome! The project needs help with:

### High Priority
1. **Complete Streamlit UI** (~9 hours)
   - Add entity selection dropdown/buttons
   - Integrate SPARQL fetching into UI flow
   - Render PyVis graphs with `st.components.v1.html()`
   - Add error handling and progress bars

2. **Consolidate Duplicate Code**
   - Merge `init.py` and `helperFunc.py` into single module
   - Update imports across notebooks

3. **Add Test Suite**
   - Unit tests for API functions
   - Integration tests for data pipeline
   - Mock Wikidata API for CI/CD

### Medium Priority
4. Schema editor UI (Streamlit data_editor)
5. Session state caching and persistence
6. Multi-entity comparison view
7. Graph database integration

### Development Setup

```bash
# Fork the repository
# Clone your fork
cd "Barb Wiki Viz"

# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and test
streamlit run main.py  # Test UI
jupyter notebook       # Test notebooks

# Commit with descriptive messages
git commit -m "feat: add entity selection UI"

# Push and create pull request
git push origin feature/your-feature-name
```

### Code Style
- Follow PEP 8 for Python code
- Add docstrings to all functions
- Include type hints where possible
- Test with real Wikidata entities before committing

---

## 📝 Configuration

### Essential Config Files

**`conf_props2vis.csv`** - Controls visualization
```csv
TYPE,prop_ID,related_propertyLabel,group,description
NODE,P136,genre,Critical,"Creative work genre"
PROPERTY,P569,date of birth,,"Birth date"
```

**`group_formatting.json`** - Visual styling
```json
{
  "Critical": {
    "shape": "hexagon",
    "color": {"background": "darkorange", "border": "orange"},
    "size": 30,
    "edge_width": 5
  }
}
```

**`.streamlit/config.toml`** - UI theme
```toml
[theme]
primaryColor = "#C0392B"
backgroundColor = "#F9EBEA"
```

---

## 🔗 API Documentation

### Wikidata Endpoints

| Endpoint | Purpose | Rate Limit |
|----------|---------|------------|
| [Reconciliation API](https://wikidata.reconci.link/en/api) | Entity search | ~5 req/sec |
| [SPARQL Endpoint](https://query.wikidata.org/sparql) | Property queries | 1 req/sec |
| [MediaWiki API](https://www.wikidata.org/w/api.php) | Batch metadata | 50 IDs/request |

### External APIs (Documented, Not Integrated)
- MusicBrainz: `docs/musicbrainz-api-guide.md`
- Spotify: `docs/spotify-api-guide.md`
- Last.fm: `docs/lastfm-api-guide.md`
- Discogs: `docs/discogs-api-guide.md`
- Genius: `docs/genius-api-guide.md`

---

## 📦 Output Examples

### CSV Export Format

**`Q312387-Les_Claypool-52_PROPERTIES.csv`**
```csv
entity_ID,name,score,prop_ID,label,description
Q312387,Les Claypool,100,P136,genre,"creative work's genre"
Q312387,Les Claypool,100,P264,record label,"brand and trademark"
```

**`Q312387-Les_Claypool-52_VALUES.csv`**
```csv
entity_ID,prop_ID,related_propertyLabel,related_value,related_valueLabel
Q312387,P136,genre,Q11399,rock music
Q312387,P264,record label,Q664167,Prawn Song Records
```

### HTML Visualization

Interactive network graph with:
- Central seed node (larger, box-shaped)
- First-degree nodes (styled by group: Critical/Location/Demographic)
- Labeled edges showing relationships
- Physics-based layout with hover tooltips
- Zoom/pan controls

---

## 🐛 Troubleshooting

### Common Issues

**Problem:** `streamlit run main.py` shows search but doesn't fetch properties

**Solution:** This is a known limitation. Use `Create_Web.ipynb` for full workflow. See [Contributing](#-contributing) to help fix the UI.

---

**Problem:** SPARQL queries timeout or return errors

**Solution:**
- Check internet connection
- Verify entity ID is valid (e.g., Q5878)
- Don't reduce the 0.9s delay in `wrap_fetch_related()` (rate limiting required)

---

**Problem:** `ModuleNotFoundError` when running scripts

**Solution:**
```bash
source .llama-neo/bin/activate
pip install -r requirements.txt
```

---

**Problem:** DynamoDB errors when running `init_db.py`

**Solution:** This module requires AWS profile 'Baba'. Either:
- Configure AWS credentials with that profile name
- Edit `init_db.py` line 39 to use your profile
- Skip DynamoDB (optional feature)

---

**Problem:** Missing images in `show_stylized_card.py`

**Solution:** This file has broken references. Not used in main workflow - safe to ignore.

---

## 📚 Documentation

- **[CLAUDE.md](CLAUDE.md)** - Comprehensive developer guide (architecture, functions, patterns)
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and release notes
- **Jupyter Notebooks** - Interactive examples and prototypes
  - `Create_Web.ipynb` - Full end-to-end workflow
  - `Build Network Viz.ipynb` - Visualization development
  - `Reconciliation Service API.ipynb` - API exploration

---

## 🙏 Acknowledgments

### Data Sources
- [Wikidata](https://www.wikidata.org/) - Primary knowledge base (CC0 license)
- [Wikidata SPARQL Service](https://query.wikidata.org/) - Query endpoint
- [W3C Reconciliation API](https://www.w3.org/community/reports/reconciliation/) - Standard specification

### Libraries
- [Streamlit](https://streamlit.io/) - Web UI framework
- [PyVis](https://pyvis.readthedocs.io/) - Network visualization
- [Pandas](https://pandas.pydata.org/) - Data manipulation
- [LlamaIndex](https://www.llamaindex.ai/) - LLM integration (planned)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Note:** Wikidata content is available under [CC0 1.0 Universal (Public Domain Dedication)](https://creativecommons.org/publicdomain/zero/1.0/).

---

## 📬 Contact & Support

### Questions or Issues?
- **GitHub Issues**: [Report bugs or request features](https://github.com/your-username/barb-wiki-viz/issues)
- **Documentation**: See [CLAUDE.md](CLAUDE.md) for detailed technical guidance

### Want to Contribute?
- Check open issues labeled `good first issue`
- Review [Contributing](#-contributing) section
- Join development discussions in pull requests

---

## 🎯 Roadmap

### v0.2.0 (Next Release)
- [ ] Complete Streamlit UI integration
- [ ] Add error handling and validation
- [ ] Implement session state caching
- [ ] Add progress indicators
- [ ] Consolidate duplicate code

### v0.3.0 (Future)
- [ ] Multi-source API integration (Spotify, Discogs, etc.)
- [ ] Schema editor UI
- [ ] Graph database persistence
- [ ] Multi-hop graph traversal
- [ ] User authentication and saved graphs

### v1.0.0 (Vision)
- [ ] Production-ready Streamlit Cloud deployment
- [ ] LLM-powered entity disambiguation
- [ ] Collaborative graph editing
- [ ] RESTful API for programmatic access
- [ ] Mobile-responsive UI

---

<p align="center">Made with ❤️ for knowledge explorers</p>
<p align="center">⭐ Star this repo if you find it useful!</p>
