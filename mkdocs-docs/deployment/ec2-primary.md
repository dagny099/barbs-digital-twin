---
title: EC2 Primary
tags:
  - deployment
  - ec2
  - aws
---

# EC2 Primary Deployment

The production app runs at [twin.barbhs.com](https://twin.barbhs.com) on an AWS EC2 instance (Amazon Linux 2), managed as a `systemd` service. Deployments are fully automated via GitHub Actions.

---

## Deploy Pipeline

```
push to main → unit tests (pytest) → SSH deploy → smoke test (HTTP 200)
```

If any unit test fails, the deploy is blocked. The EC2 instance is not touched.

### Full pipeline steps

1. GitHub Actions runner (ubuntu-latest) checks out code
2. Installs `requirements.txt` with pip cache
3. Runs `pytest tests/ -v` with a dummy `OPENAI_API_KEY` (no real API calls)
4. On pass: SSHes into EC2, runs `git pull`, `pip install -r requirements.txt`, `systemctl restart digital-twin`
5. Smoke tests the endpoint (HTTP 200 check)

---

## Required GitHub Secrets

Configure these in **Settings → Secrets and variables → Actions**:

| Secret | Value |
|---|---|
| `EC2_HOST` | Public IP or hostname of your EC2 instance |
| `EC2_USER` | `ec2-user` |
| `EC2_SSH_KEY` | Private key of the dedicated deploy keypair |
| `EC2_APP_DIR` | Path to the app on the instance, e.g. `/home/ec2-user/barbs-digital-twin` |
| `EC2_SERVICE_NAME` | systemd service name, e.g. `digital-twin` |

---

## Manual Deploy

If you need to deploy without GitHub Actions:

```bash
ssh ec2-user@<EC2_HOST>
cd /path/to/barbs-digital-twin
git pull
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart digital-twin
sudo systemctl status digital-twin
```

---

## Pre-Deploy Validation

Before pushing any deploy that touches credentials, environment config, or ChromaDB, run the integration healthcheck manually:

```bash
# Validate all external service connections (no notification sent)
python scripts/healthcheck.py

# Full end-to-end: also sends a Pushover notification
python scripts/healthcheck.py --notify
```

---

## Monitoring

### Service health

```bash
ssh ec2-user@<host>
sudo systemctl status digital-twin
journalctl -u digital-twin -n 50
```

### Query logs

```bash
# Check for errors or low satisfaction
python scripts/analyze_logs.py --votes --last 50

# Weekly: what are users asking that we can't answer?
python scripts/analyze_logs.py --knowledge-gaps

# Cost trends
python scripts/analyze_logs.py --cost-analysis
```

### Disk space

```bash
du -sh .chroma_db_DT/    # ChromaDB can grow over time
```

---

## Dual-Backend Deployment

Both `twin.barbhs.com` and `graphy.twin.barbhs.com` run from the same `main` branch — same codebase, different `.env` files. The `RETRIEVAL_BACKEND` variable in each server's `.env` selects the active backend:

```
push to main → unit tests (pytest) → deploy-ec2.yml (ChromaDB) + deploy-ec2-feature.yml (Neo4j)
```

The second service runs on port 7861 in its own app directory with its own `.env`. Both services are deployed on every push to `main`.

| Deployment | Domain | `RETRIEVAL_BACKEND` | Workflow |
|---|---|---|---|
| Primary | `twin.barbhs.com` | `chromadb` | `deploy-ec2.yml` |
| Graphy preview | `graphy.twin.barbhs.com` | `neo4j` | `deploy-ec2-feature.yml` |

**Additional secrets required for graphy preview:**

| Secret | Example value |
|---|---|
| `EC2_FEATURE_APP_DIR` | `/home/ec2-user/barbs-digital-twin-neo4j` |
| `EC2_FEATURE_SERVICE_NAME` | `barbs-digital-twin-neo4j` |
| `EC2_FEATURE_APP_PORT` | `7861` |

See `.github/workflows/deploy-ec2-feature.yml` for the one-time EC2 setup instructions (systemd unit file, Nginx server block, TLS cert expansion, DNS A record).

---

## Quick Deploy Reference

```bash
# Install MkDocs Material (for these docs)
pip install mkdocs-material

# Preview docs locally
mkdocs serve      # http://localhost:8000

# Build static site for publishing
mkdocs build      # outputs to site/
```

The `site/` directory can be published to any static host (GitHub Pages, Netlify, S3) or synced to the appropriate path on the docs server.
