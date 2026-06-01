---
title: HuggingFace Spaces
tags:
  - deployment
  - huggingface
---

# Hugging Face Spaces (Secondary)

A secondary mirror of the app runs on Hugging Face Spaces. It's useful for redundancy and sharing but has limitations compared to the EC2 primary.

---

## How It Works

On every push to `main`, GitHub Actions syncs app code and input data to the HF Space repo. The Space runs the app in a Docker container.

!!! warning "Ephemeral ChromaDB"
    ChromaDB storage is ephemeral on HF Spaces — the app rebuilds the entire vector database from scratch on every container restart. This means:
    - Cold starts are significantly slower than EC2
    - The database is only as fresh as the last restart
    - Do not use HF Spaces for latency-sensitive use cases

---

## Required Secret

Configure in **Settings → Secrets and variables → Actions**:

| Secret | Value |
|---|---|
| `HF_TOKEN` | Your Hugging Face API token with write access to the Space |

---

## Limitations vs EC2

| Feature | EC2 Primary | HF Spaces |
|---|---|---|
| ChromaDB persistence | Persistent storage | Ephemeral (rebuilds on restart) |
| Cold start speed | Fast (DB pre-loaded) | Slow (DB rebuilt from scratch) |
| Neo4j connectivity | Yes (via `.env`) | Depends on secrets config |
| Admin interface | Local only | Not deployed |
| Resources | Configurable instance type | Free tier limits apply |
| Unit test gate | Yes (blocks deploy) | No test gate |

---

## Manual Sync

If you need to sync manually:

```bash
# Install HF CLI
pip install huggingface_hub

# Login
huggingface-cli login

# Push ChromaDB to HF Hub (for seeding the Space on restart)
python db_sync.py --push

# Pull from HF Hub to local (for restoring from backup)
python db_sync.py --pull

# Use a different repo
python db_sync.py --push --repo username/repo-name
```

Default repo: `dagny099/barb-digital-twin-db`

---

## When to Use HF Spaces

- **Sharing a demo link** — when you want a stable URL that doesn't require EC2
- **Backup / redundancy** — if EC2 is unavailable
- **Forking for your own twin** — the simplest deployment path for a fork

For production use, EC2 is the correct primary. The HF Space is a convenience mirror, not a replacement.

---

## Quick Deploy Reference

### For these MkDocs docs

```bash
# Install dependencies
pip install mkdocs-material

# Local preview
mkdocs serve          # http://localhost:8000

# Build for publishing
mkdocs build          # outputs to site/

# Deploy to GitHub Pages (if configured)
mkdocs gh-deploy
```

The `site/` directory is the static build. Copy it to the appropriate path on `docs.barbhs.com/barbs-digital-twin/` to publish.
