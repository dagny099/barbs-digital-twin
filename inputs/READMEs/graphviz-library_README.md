# 📊 Graphviz Library for Interactive Diagrams

This repository contains a collection of visual diagrams written in Graphviz's DOT language. It is designed to:

- Showcase data pipelines, ETL workflows, ML architectures, and knowledge systems.
- Provide reusable templates and inline-SVG-ready outputs.
- Serve as a portfolio and educational gallery that can be easily deployed on a personal website.

**Useful way to visualize instantly**: [http://www.webgraphviz.com/](http://www.webgraphviz.com/)

**Helpful Convo**: [love how this evolved]](https://chatgpt.com/c/6802c54d-97b0-8007-a7b4-7e04d0324a5a?model=gpt-4-5)

---

## 📁 Repository Structure

```
graphviz_library/
├── diagrams/              # .dot source files
│   ├── etl_flow.dot
│   └── ml_pipeline.dot
├── svgs/                  # Rendered SVGs (auto-generated)
├── html/                  # Inline HTML blocks from SVGs
│   └── inline_diagrams.html
├── render_all.py          # Renders .dot to .svg and .png
├── svg_to_html.py         # Converts .svg files into inline <div class="diagram"> blocks
└── index.html             # Standalone interactive diagram gallery
```

---

## 🔄 Workflow Summary

> **Goal**: Automatically regenerate SVG/PNG outputs and inline HTML blocks whenever you update a `.dot` file.

### 🧰 Step-by-step (manual)

```bash
# 1. Create or edit DOT files
vim diagrams/my_diagram.dot

# 2. Render diagrams
python render_all.py

# 3. Convert SVGs to inline HTML blocks
python svg_to_html.py

# 4. Open or copy from `html/inline_diagrams.html`
```

---

## ⚙️ GitHub Actions Workflow (Optional)

To automate this when you push to your repository:

### 1. Create `.github/workflows/build-diagrams.yml`

```yaml
name: Build Graphviz Diagrams

on:
  push:
    paths:
      - 'diagrams/*.dot'
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout repo
      uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install Graphviz
      run: sudo apt-get install graphviz

    - name: Install requirements
      run: pip install -r requirements.txt || true

    - name: Render Diagrams
      run: python render_all.py

    - name: Convert SVGs to HTML
      run: python svg_to_html.py

    - name: Commit outputs
      run: |
        git config user.name github-actions
        git config user.email github-actions@github.com
        git add svgs/ html/ || true
        git commit -m "🧾 Auto-update rendered diagrams" || echo "No changes"
        git push || true
```

> You can extend this to auto-deploy to GitHub Pages or Netlify if your `index.html` gallery is part of your site.

---

## ✍️ Notes on Design

- Each `.dot` file should represent a distinct concept or flow.
- Output files are named consistently for easy linkage.
- The gallery uses `inline SVG` so you can style nodes with CSS or add tooltips/interactivity.

---

## ✨ Prompting LLMs to Generate Graphviz Diagrams

You can use an LLM to generate Graphviz diagrams directly from a README, folder structure, or descriptive text. This works particularly well for generating dependency trees, ML pipelines, service maps, or system workflows.

### 🧠 Enhanced Core Prompt

```text
You are an expert software architect and technical diagram designer skilled in creating clear, aesthetically pleasing, and semantically meaningful diagrams. Given a structured or semi-structured input (e.g., GitHub README, codebase structure, file descriptions), your task is to create an informative Graphviz DOT diagram illustrating the key components, relationships, and hierarchies.

Follow these detailed guidelines:
1. Clearly identify and define logical groupings or subsystems and represent them as subgraphs (`cluster` blocks).
2. Use concise and meaningful labels on nodes to clearly communicate their purpose.
3. Establish directional edges that accurately depict the flow of data, control, or dependencies.
4. Apply visual enhancements such as distinct colors, node shapes (ellipse for endpoints, box for processes, diamond for decisions), and directional layout (`rankdir`) to maximize clarity and visual appeal.
5. Provide thoughtful inline comments if assumptions or interpretations were necessary due to incomplete information.
6. Output the diagram exclusively as DOT code ready for rendering.

Input context:
[Paste your README or code layout here]
```

### 🔄 Detailed Follow-Up Prompts and Rationales

- **"Can you simplify the labels and remove intermediate nodes?"**

  - Helps ensure the diagram is concise and easily digestible, ideal for high-level presentations or overviews.

- **"Please reorient the layout to be top-down instead of left-to-right."**

  - Useful when vertical space is preferred or when representing hierarchical structures clearly.

- **"Add one layer of detail by expanding subgraphs to include filenames."**

  - Provides additional context, particularly beneficial for documentation or technical references.

- **"Now include node attributes like config paths or script descriptions."**

  - Adds essential information directly into the diagram for greater usability and quicker reference during implementation.

- **"Render only the data flow path, and exclude control logic."**

  - Ideal for clarity when the primary interest is understanding how data moves through the system, minimizing cognitive overload.

### 💬 Tips for Human Collaboration with LLMs

- Keep your input structured: bullet lists, numbered workflows, or file trees work best.
- Provide filenames and what each script/module does.
- Let the LLM take a first pass, then ask for refinements iteratively.
- Once you like the structure, paste the DOT into a `.dot` file and commit it.
- Render it with `dot -Tsvg` or use the included `render_all.py`.

---

## 💡 Tips for Authoring Graphviz

- Use `rankdir=LR` for left-to-right pipelines
- Organize your graph into `subgraph cluster_*` blocks for clarity
- Use consistent colors to distinguish stages
- Try [Edotor](https://edotor.net/) or VS Code + Graphviz Preview for live feedback

---

## 📬 Contributions

Feel free to open an issue or PR if you'd like to:

- Add reusable templates (e.g., ML pipeline, API topology, ontology structure)
- Improve automation or visual theming

---

Made with 💡 and `dot -Tsvg`.

