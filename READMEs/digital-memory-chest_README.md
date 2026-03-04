# Digital Memory Chest 💜

A respectful, AI-powered digital memorial application that helps families and friends create beautiful, lasting tributes to loved ones. The application automatically organizes memories, creates timelines, and generates meaningful narratives using AI.

## ✨ Key Features

- **Professional Memorial Interface**: Respectful, elegant Gallery with memorial-appropriate design
- **Enhanced Visual Experience**: Beautiful card layouts, hover effects, and dignified interactions
- **Rich Media Support**: Photos, videos, audio recordings, and text memories with elegant presentation
- **AI Processing**: Automatic transcription (Whisper) and image tagging (CLIP)  
- **Story Generation**: AI-created narratives using OpenAI/Anthropic APIs
- **Advanced Memory Organization**: Smart filtering, search, and chronological organization
- **Privacy-First**: Local processing options, minimal PII storage
- **Collaborative Sharing**: Secure contribution links for family and friends
- **Production Ready**: SQLite for development, PostgreSQL for production

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- At least one AI API key (OpenAI or Anthropic recommended, but optional)

### One-Command Demo Setup
```bash
git clone <repository-url>
cd digital-memory-chest
pip install -r requirements.txt
python run_demo.py
```

This creates a complete demo memorial for "Eleanor Thompson" with enhanced Gallery interface and launches the web interface at `http://localhost:8501`.

### Manual Installation
```bash
# Setup environment
cp .env.example .env
# Edit .env with your API keys (optional)

# Run application  
python run_app.py
# or: streamlit run app.py
```

### Essential Commands
```bash
# Demo with sample data (recommended for first time)
python run_demo.py

# Clean app startup (production/development)
python run_app.py

# Seed demo data separately
python scripts/seed_demo_data.py
```

## 📚 Documentation

For complete documentation including detailed setup, usage guides, architecture details, and deployment instructions:

**➡️ [View Full Documentation](https://your-docs-site.com)**

Quick links:
- [Installation & Setup](docs/getting-started/installation.md)
- [Demo Setup](docs/getting-started/demo-setup.md)
- [User Guide](docs/user-guide/creating-chests.md)
- [Gallery Guide](docs/user-guide/gallery.md)
- [Adding Memories](docs/user-guide/adding-memories.md)
- [Configuration](docs/getting-started/configuration.md)
- [Developer Guide](docs/developer/setup.md)
- [API Reference](docs/developer/api-reference.md)
- [Privacy & Security](docs/user-guide/privacy.md)
- [Troubleshooting](docs/troubleshooting.md)

## 🔧 Development & Testing

```bash
# Run tests
python test_setup.py

# Code quality
ruff check src/ tests/
black src/ tests/
mypy src/

# Build documentation
mkdocs build
mkdocs serve
```

## 🚀 Production Ready

- **Database**: SQLite → PostgreSQL migration support
- **Storage**: Local files → S3-compatible storage  
- **AI**: OpenAI/Anthropic APIs + local processing fallbacks
- **Security**: Token-based sharing, privacy-first design

## 📜 License & Contributing

MIT License - Built with respect for those using this during difficult times.

Contributions welcome - see [Contributing Guide](docs/developer/contributing.md) for guidelines on maintaining the respectful, privacy-focused nature of this memorial application.

---

*This application handles sensitive memorial content. Please ensure appropriate privacy controls and respectful usage in all deployments.*