# Plex Knowledge Graph

Transform your Plex media library into an interactive knowledge graph using Neo4j, with rich visualizations and an intuitive web dashboard.

## Overview

This project extracts movie data from your Plex server and builds a comprehensive knowledge graph in Neo4j. The graph connects movies with actors, directors, genres, studios, and more, enabling powerful queries and visualizations.

### Key Features

- **Resilient Extraction**: Checkpoint-based extraction with automatic resume capability
- **Transparent Tracking**: SQLite database + CSV exports for full visibility into processing
- **Network Interruption Handling**: Safe to stop and resume at any point
- **Interactive Dashboard**: Streamlit-based web UI for exploring your graph
- **Sample Visualizations**: Auto-generated NetworkX and PyVis visualizations
- **Scalable**: Handles large libraries (tested with 18,000+ movies)

## Architecture

```
Plex Server → Extract → Transform → Neo4j → Visualize
                ↓          ↓          ↓         ↓
            Checkpoint  SQLite    GraphDB   Dashboard
                       Tracking
```

### Data Model

**Node Types:**
- `Movie`: Films with metadata (title, year, rating, summary, etc.)
- `Person`: Actors, directors, writers, producers
- `Genre`: Movie genres
- `Studio`: Production studios
- `Country`: Countries of origin
- `Collection`: Movie collections/franchises

**Relationship Types:**
- `ACTED_IN`: Person → Movie
- `DIRECTED`: Person → Movie
- `WROTE`: Person → Movie
- `PRODUCED`: Person → Movie
- `HAS_GENRE`: Movie → Genre
- `PRODUCED_BY`: Movie → Studio
- `FROM_COUNTRY`: Movie → Country
- `IN_COLLECTION`: Movie → Collection

## Prerequisites

1. **Plex Media Server** with a Movies library
2. **Python 3.9+**
3. **Neo4j Database** (local or cloud)
   - Local: Download from [neo4j.com](https://neo4j.com/download/)
   - Cloud: Use [Neo4j Aura](https://neo4j.com/cloud/aura/) (free tier available)

## Installation

### 1. Clone or Download Project

```bash
cd ~/PROJECTS/Plex-Project
```

### 1b. Push the `work` branch to your remote

If you do not yet see the `work` branch in your remote repository, create and push it after cloning:

```bash
git checkout work        # switch to the local work branch
git push -u origin work  # publish the branch for collaborators
```

The `-u` flag configures upstream tracking so future `git push` or `git pull` commands automatically target `origin/work`.

### 2. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Credentials

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```bash
# Plex Credentials
PLEX_USERNAME=your_plex_username
PLEX_PASSWORD=your_plex_password

# Neo4j Credentials
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password
```

> **Tip:** The CLI, loaders, and dashboard call `load_dotenv(override=True)`, so any values you place in `.env` automatically replace previously exported environment variables the next time you run a command. If you prefer to clear the old shell variables manually, run `unset PLEX_USERNAME PLEX_PASSWORD NEO4J_URI NEO4J_USERNAME NEO4J_PASSWORD` before restarting your session.

### 5. Configure Settings (Optional)

Edit `config.yaml` to customize:
- Which Plex server to use (`plex.server_index`)
- Batch sizes for processing
- Checkpoint intervals
- Visualization preferences
- See comments in `config.yaml` for all options

## Usage

### Quick Start (Complete Pipeline)

Run the entire pipeline with one command:

```bash
python src/cli.py run-all
```

This will:
1. Extract movies from Plex
2. Transform to graph format
3. Setup Neo4j schema
4. Load into Neo4j
5. Generate sample visualizations

### Step-by-Step Usage

For more control, run each stage individually:

#### 1. Extract from Plex

```bash
python src/cli.py extract
```

**What it does:**
- Connects to your Plex server
- Extracts movie metadata (title, year, actors, genres, etc.)
- Saves to `data/raw/movies_batch_*.json`
- Checkpoints every 100 movies (configurable)
- **Safe to interrupt** - will resume from last checkpoint

**Output:**
- Raw JSON files in `data/raw/`
- Progress tracking in `data/tracking.db`
- CSV exports in `data/exports/`

#### 2. Transform to Graph Format

```bash
python src/cli.py transform
```

**What it does:**
- Reads raw movie data
- Extracts unique entities (actors, genres, etc.)
- Creates node and relationship mappings
- Deduplicates entities across movies
- Saves to `data/processed/nodes.json` and `data/processed/edges.json`

#### 3. Setup Neo4j Schema

```bash
python src/cli.py setup-schema
```

**What it does:**
- Creates uniqueness constraints
- Creates performance indexes
- Prepares database for data import

**First time only** - run with `--clear` to start fresh:
```bash
python src/schema.py --clear
```

#### 4. Load into Neo4j

```bash
python src/cli.py load
```

**What it does:**
- Loads nodes in batches (idempotent MERGE operations)
- Creates relationships
- Verifies data integrity
- Updates tracking database

**Safe to re-run** - uses MERGE to avoid duplicates

#### 5. Generate Visualizations

```bash
python src/cli.py visualize
```

**What it does:**
- Generates sample actor collaboration networks
- Creates genre-movie visualizations
- Builds director filmography graphs
- Saves as PNG images and interactive HTML

**Output:** `outputs/visualizations/`

#### 6. Launch Dashboard

```bash
python src/cli.py dashboard
```

**What it does:**
- Launches Streamlit web dashboard
- Opens in your browser automatically
- Provides interactive exploration of your graph

**Dashboard Features:**
- Search movies and people
- View detailed information
- Explore relationships
- Generate custom visualizations
- Genre analysis and statistics

### Other Commands

**View Statistics:**
```bash
python src/cli.py stats
```

Shows current pipeline progress and entity counts.

**Get Help:**
```bash
python src/cli.py --help
```

## Configuration Guide

### Key Configuration Options

Edit `config.yaml` to customize behavior:

#### Testing with Subset

```yaml
plex:
  max_movies: 50  # Process only 50 movies for testing
```

Set to `null` for full library.

#### Batch Sizes

```yaml
plex:
  batch_size: 100  # Plex extraction batch size

neo4j:
  batch_size: 100  # Neo4j import batch size
```

Increase for speed, decrease if hitting memory limits.

#### Checkpoint Frequency

```yaml
resilience:
  checkpoint_interval: 100  # Checkpoint every N movies
  csv_export_interval: 500  # Export CSV every N movies
```

#### Visualization Limits

```yaml
visualization:
  filters:
    max_nodes: 500  # Maximum nodes in visualization
    max_edges: 1000
```

Prevents overwhelming visualizations.

## Resilience & Recovery

### Network Interruptions

The pipeline is designed to handle interruptions gracefully:

1. **Extraction**: Checkpoints every N movies (default: 100)
   - Press `Ctrl+C` to stop
   - Run `python src/cli.py extract` to resume
   - Skips already-extracted movies

2. **Transformation**: Tracks processed movies in SQLite
   - Safe to re-run
   - Deduplicates entities automatically

3. **Loading**: Idempotent MERGE operations
   - Safe to re-run
   - Won't create duplicate nodes

### Tracking & Transparency

**SQLite Database** (`data/tracking.db`):
- Tracks each movie's status
- Logs all errors with full context
- Enables resume capability

**CSV Exports** (`data/exports/`):
- `movies_status.csv`: All movies and their processing status
- `entities_summary.csv`: All unique entities created
- `errors_log.csv`: Detailed error log
- `processing_stats.csv`: Summary statistics

**Human-readable and Excel-compatible!**

### Error Handling

Errors are logged but don't stop processing:

```yaml
resilience:
  skip_errors: true  # Continue processing on error
  max_retries: 3
  retry_delay: 60  # seconds
```

Check `data/exports/errors_log.csv` for details.

## Example Queries

Once data is loaded, you can query Neo4j directly.

### Find Actor Collaborations

```cypher
MATCH (a1:Person)-[:ACTED_IN]->(m:Movie)<-[:ACTED_IN]-(a2:Person)
WHERE a1.name = 'Tom Hanks'
RETURN a2.name as costar, count(m) as movies_together
ORDER BY movies_together DESC
LIMIT 10
```

### Find Highly Rated Movies by Genre

```cypher
MATCH (m:Movie)-[:HAS_GENRE]->(g:Genre {name: 'Sci-Fi'})
WHERE m.rating > 7.0
RETURN m.title, m.year, m.rating
ORDER BY m.rating DESC
```

### Find Director's Filmography

```cypher
MATCH (d:Person {name: 'Christopher Nolan'})-[:DIRECTED]->(m:Movie)
RETURN m.title, m.year, m.rating
ORDER BY m.year DESC
```

### Find Movies with Specific Actors

```cypher
MATCH (a1:Person {name: 'Leonardo DiCaprio'})-[:ACTED_IN]->(m:Movie)
      <-[:ACTED_IN]-(a2:Person {name: 'Tom Hardy'})
RETURN m.title, m.year
```

## Project Structure

```
Plex-Project/
├── config.yaml              # Main configuration
├── .env                     # Credentials (gitignored)
├── .env.example             # Credentials template
├── requirements.txt         # Python dependencies
├── README.md                # This file
│
├── src/
│   ├── tracking_db.py       # SQLite tracking database
│   ├── extract_plex.py      # Plex extraction with checkpointing
│   ├── transform.py         # Data transformation to graph format
│   ├── schema.py            # Neo4j schema setup
│   ├── neo4j_loader.py      # Batch loading into Neo4j
│   ├── visualize.py         # Sample visualization generator
│   ├── streamlit_app.py     # Interactive dashboard
│   └── cli.py               # Command-line interface
│
├── data/
│   ├── raw/                 # Raw Plex data (JSON batches)
│   ├── processed/           # Transformed graph data
│   ├── exports/             # CSV exports for transparency
│   └── tracking.db          # SQLite tracking database
│
└── outputs/
    └── visualizations/      # Generated graphs (PNG & HTML)
```

## Troubleshooting

### "No Plex servers found"

- Check PLEX_USERNAME and PLEX_PASSWORD in `.env`
- Verify Plex account has access to servers
- Check `plex.server_index` in `config.yaml`

### "Connection refused" (Neo4j)

- Ensure Neo4j is running
- Check NEO4J_URI in `.env`
- Default local: `bolt://localhost:7687`
- For Neo4j Desktop, use `neo4j://localhost:7687`

### "Out of memory" during processing

- Reduce batch sizes in `config.yaml`
- Process subset first with `max_movies: 100`
- Increase available system memory

### Extraction is slow

- Normal for large libraries (18k movies = ~1-2 hours)
- Increase `batch_size` for speed
- Use checkpoint/resume if interrupted

### Dashboard won't start

```bash
# Install streamlit if missing
pip install streamlit

# Check port isn't in use
lsof -i :8501

# Run directly
streamlit run src/streamlit_app.py
```

## Extending the Project

### Adding TV Shows

1. Create `src/extract_plex_tv.py` (similar to `extract_plex.py`)
2. Add `Episode` and `Season` node types
3. Update `transform.py` for TV-specific relationships
4. Modify dashboard for TV show views

### Adding More Attributes

Edit `config.yaml`:

```yaml
extraction:
  include_attributes:
    - title
    - year
    - your_new_attribute  # Add here
```

### Custom Visualizations

Edit `src/visualize.py` to add new visualization types:

```python
def create_my_custom_viz(self):
    query = """
    // Your Cypher query here
    """
    # Build graph and visualize
```

## Performance Tips

### For Large Libraries (10k+ movies)

1. **Increase batch sizes:**
   ```yaml
   plex:
     batch_size: 500
   neo4j:
     batch_size: 500
   ```

2. **Test with subset first:**
   ```yaml
   plex:
     max_movies: 100  # Test first
   ```

3. **Use SSD for Neo4j data**

4. **Allocate more memory to Neo4j:**
   Edit `neo4j.conf`:
   ```
   dbms.memory.heap.initial_size=2g
   dbms.memory.heap.max_size=4g
   ```

### For Slow Networks

1. **Reduce checkpoint interval:**
   ```yaml
   resilience:
     checkpoint_interval: 50
   ```

2. **Enable Plex local access** if on same network

## FAQ

**Q: Can I run this on cloud Neo4j (Aura)?**
A: Yes! Just update NEO4J_URI in `.env` to your Aura connection string.

**Q: Will this modify my Plex library?**
A: No, extraction is read-only. Your Plex library remains unchanged.

**Q: Can I process multiple Plex libraries?**
A: Yes, but run separately. Change `plex.library_name` in config.yaml.

**Q: How do I reset and start over?**
A:
```bash
# Clear Neo4j
python src/schema.py --clear

# Delete tracking and data
rm -rf data/
```

**Q: Can I use this without Neo4j?**
A: The transformed graph data (`data/processed/nodes.json` and `edges.json`) is database-agnostic. You could load it into any graph database.

## Credits

Built with:
- [PlexAPI](https://github.com/pkkid/python-plexapi) - Plex Python bindings
- [Neo4j](https://neo4j.com/) - Graph database
- [NetworkX](https://networkx.org/) - Graph analysis
- [PyVis](https://pyvis.readthedocs.io/) - Interactive visualizations
- [Streamlit](https://streamlit.io/) - Dashboard framework

## License

MIT License - feel free to use and modify for your own Plex library!

## Support

For issues or questions:
1. Check the Troubleshooting section above
2. Review CSV exports in `data/exports/` for errors
3. Check SQLite tracking database: `data/tracking.db`

---

**Happy graphing! 🎬 → 📊**
