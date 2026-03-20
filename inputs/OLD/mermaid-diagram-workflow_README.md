# Mermaid Diagram Workflow (Meta Example)

This repo accompanies the blog post **"Taming Mermaid Diagrams Across Projects"**.

It contains:

- `blog/mermaid-diagram-workflow.md` – the full tutorial
- `diagrams/` – example Mermaid diagrams used in the post
- `diagram_index/index.yaml` – a small cross-project diagram index
- `diagram_hub/` – early code for scanning diagrams and metadata
- `streamlit_app/app.py` – a small Streamlit app to explore the index
- `scripts/render_diagrams.sh` – script to render all `.mmd` → `.svg`

## Quickstart

```bash
# 1. Render example diagrams
./scripts/render_diagrams.sh

# 2. Install Python deps (example)
pip install streamlit pyyaml python-frontmatter

# 3. Run Streamlit app
streamlit run streamlit_app/app.py
