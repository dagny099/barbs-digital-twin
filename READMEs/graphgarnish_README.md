# 🍸 GraphGarnish

**Transform podcast metadata into interactive network visualizations**

GraphGarnish is a web-based tool for visualizing podcast episode networks. See which guests return, which organizations dominate the conversation, and how your podcast has evolved over time—all through an interactive, filterable network graph.

🔗 **Live Demo:** [graph-gist.com](https://graph-gist.com) | [graphgist.studio](https://graphgist.studio)

---

## 🎯 What It Does

GraphGarnish takes podcast metadata (episodes, guests, organizations) and creates an **interactive force-directed network visualization** where you can:

- **Filter by year** to see how your network evolved
- **Search** for specific people or organizations
- **Click nodes** to focus on their immediate connections
- **Adjust thresholds** to show only repeat guests or major organizations
- **Export insights** about your podcast's guest network

Perfect for podcast producers, researchers, or anyone who wants to understand the social graph hiding in their episode list.

---

## ✨ Features

### 🎛️ **Smart Filtering**
- Year range slider (e.g., "show only 2024 episodes")
- Minimum connection thresholds (e.g., "guests with 3+ episodes")
- Node type toggles (show/hide episodes, guests, orgs)
- Real-time search across all node names

### 👆 **Interactive Exploration**
- Click any node to highlight its network
- Drag nodes to rearrange the layout
- Zoom and pan to explore dense clusters
- Hover for detailed tooltips

### 📊 **Real-Time Stats**
- Live counts as you filter (X episodes, Y guests, Z orgs)
- Connection metrics in tooltips
- Network density visualization

### 🎨 **Beautiful Defaults**
- D3.js force-directed physics
- Color-coded node types (episodes=red, guests=cyan, orgs=yellow)
- Smooth animations and transitions
- Responsive design (works on mobile)

---

## 🚀 Quick Start

### Option 1: Try the Demo
1. Visit **[graph-gist.com](https://graph-gist.com)**
2. The demo loads with 203 episodes from *Catalog & Cocktails*
3. Use filters and search to explore

### Option 2: Use Your Own Data
1. Download `explore.html` from this repo
2. Prepare your network JSON (see [Data Format](#-data-format) below)
3. Open `explore.html` in a browser
4. Click **"Load Network Data"** and select your JSON file
5. Explore!

### Option 3: Clone & Customize
```bash
git clone https://github.com/dagny099/graphgarnish.git
cd graphgarnish
# Open index.html in your browser
```

---

## 📁 Data Format

GraphGarnish expects a JSON file with two arrays: `nodes` and `links`.

### Example Structure

```json
{
  "nodes": [
    {
      "id": "ep_1",
      "name": "Episode Title Here",
      "type": "episode",
      "date": "2024-01-15",
      "is_full": true
    },
    {
      "id": "person_juan_sequeda",
      "name": "Juan Sequeda",
      "type": "person"
    },
    {
      "id": "org_dataworld",
      "name": "data.world",
      "type": "organization"
    }
  ],
  "links": [
    {
      "source": "person_juan_sequeda",
      "target": "ep_1",
      "type": "GUEST_ON"
    },
    {
      "source": "person_juan_sequeda",
      "target": "org_dataworld",
      "type": "AFFILIATED_WITH"
    }
  ]
}
```

### Node Types

**Episode:**
- `id`: Unique identifier (e.g., `ep_1`)
- `name`: Episode title
- `type`: `"episode"`
- `date`: Publication date (YYYY-MM-DD format)
- `is_full`: Boolean (true for full episodes, false for shorts/takeaways)

**Person (Guest):**
- `id`: Unique identifier (e.g., `person_juan_sequeda`)
- `name`: Guest's full name
- `type`: `"person"`

**Organization:**
- `id`: Unique identifier (e.g., `org_dataworld`)
- `name`: Organization name
- `type`: `"organization"`

### Link Types

- `GUEST_ON`: Connects a person to an episode
- `AFFILIATED_WITH`: Connects a person to an organization

---

## 🛠️ Creating Your Network JSON

We provide a Python script to transform podcast metadata from a spreadsheet into network JSON.

### From a Spreadsheet

**Required columns:**
- `Episode` - Episode title
- `Release Date` - Publication date
- `Guest` - Guest name
- `Role & Company` - Guest's role and organization (format: "Role at Company")

**Example:**
| Episode | Release Date | Guest | Role & Company |
|---------|--------------|-------|----------------|
| Data Mesh Explained | 2024-01-15 | Juan Sequeda | Principal Scientist at data.world |

**Run the generator:**
```bash
python generate_network.py your_episodes.xlsx
# Outputs: network.json
```

See `examples/` folder for sample spreadsheets and generated JSON.

---

## 📊 Use Cases

### 1. **Guest Network Analysis**
- Which guests return most frequently?
- Which organizations are most represented?
- Are there clusters of guests from the same industry?

### 2. **Content Planning**
- Identify gaps in your guest diversity
- Find one-time guests worth inviting back
- Track organizational representation over time

### 3. **Social Proof**
- Showcase the breadth of your guest network
- Highlight prominent organizations you've featured
- Demonstrate growth and evolution of your show

### 4. **Research & Discovery**
- Find connections between guests and organizations
- Track career movements (guests changing companies)
- Identify influential nodes in your podcast network

---

## 🎨 Customization

### Colors
Edit the `colorMap` in `explore.html`:
```javascript
const colorMap = {
    'episode': '#ff6b6b',      // Red
    'person': '#4ecdc4',        // Cyan
    'organization': '#ffe66d'   // Yellow
};
```

### Node Sizes
Edit the `sizeMap`:
```javascript
const sizeMap = {
    'episode': 7,
    'person': 11,
    'organization': 15
};
```

### Physics
Adjust force simulation parameters:
```javascript
.force('charge', d3.forceManyBody()
    .strength(d => {
        if (d.type === 'organization') return -1200;  // Org repulsion
        if (d.type === 'person') return -500;         // Guest repulsion
        return -200;                                  // Episode repulsion
    }))
```

---

## 🧰 Tech Stack

- **D3.js v7** - Force-directed graph layout
- **Vanilla JavaScript** - No frameworks, no build step
- **HTML5 + CSS3** - Modern, responsive design
- **JSON** - Simple, portable data format

**Why no backend?**
- Runs entirely in the browser
- No server needed
- Easy to host on GitHub Pages, Netlify, etc.
- Privacy-friendly (your data never leaves your machine)

---

## 📖 Documentation

### Filter Logic

Filters cascade intelligently:

1. **Episode filters** (year, search, visibility) apply first
2. **Guest filters** only show guests connected to visible episodes
3. **Organization filters** only show orgs connected to visible guests

This prevents orphaned nodes and maintains network coherence.

**Connection thresholds** (e.g., "min 2 episodes per guest") use the **full dataset**, not the filtered view. This ensures consistent filtering behavior.

### Performance

GraphGarnish handles networks with:
- ✅ Up to 500 episodes
- ✅ Up to 300 guests
- ✅ Up to 150 organizations

For larger networks (1000+ nodes), consider:
- Reducing physics iterations
- Disabling labels on episodes
- Pre-filtering data before loading

---

## 🤝 Contributing

Contributions welcome! Here's how:

1. **Fork** the repo
2. **Create a branch**: `git checkout -b feature/your-feature`
3. **Commit changes**: `git commit -m 'Add some feature'`
4. **Push**: `git push origin feature/your-feature`
5. **Open a Pull Request**

### Ideas for Contributions

- [ ] CSV export functionality
- [ ] Timeline slider (animate growth over time)
- [ ] Community detection algorithms
- [ ] Dark mode toggle
- [ ] Mobile gesture controls
- [ ] Embed code generator
- [ ] Multi-dataset comparison view

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details

**TL;DR:** Use it, modify it, share it. Just keep the license notice.

---

## 🙏 Acknowledgments

- **D3.js** for the incredible force simulation library
- **Catalog & Cocktails** podcast for the demo dataset
- The data visualization community for inspiration

---

## 📬 Contact

**Built by:** Dagny Taggart  
**Website:** [yourwebsite.com](https://yourwebsite.com)  
**GitHub:** [@dagny099](https://github.com/dagny099)

**Questions? Ideas? Found a bug?**  
Open an issue on GitHub or reach out on LinkedIn.

---

## 🎯 Roadmap

### v1.0 (Current)
- ✅ Interactive network visualization
- ✅ Smart filtering system
- ✅ File upload interface
- ✅ Responsive design

### v1.1 (Next)
- [ ] Export filtered network as image
- [ ] Save/load filter presets
- [ ] Keyboard shortcuts
- [ ] Tutorial overlay for first-time users

### v2.0 (Future)
- [ ] Backend API for automatic network generation
- [ ] Multi-podcast comparison mode
- [ ] Statistical analysis dashboard
- [ ] Integration with podcast hosting platforms

---

**⭐ If you find GraphGarnish useful, please star the repo!**

---

*"The perfect garnish for your podcast knowledge graph."*
