# PyMesh: An Intuitive, Visual Dependency Mapper for Python Projects

A **Streamlit-based** tool to analyze Python project dependencies at the function level, visualize them interactively with PyVis, and export structured graph data for further analysis (e.g., Neo4j ingestion).

[![CI](https://github.com/dagny099/pymesh/actions/workflows/ci.yml/badge.svg?branch=)](https://github.com/dagny099/pymesh/actions/workflows/ci.yaml)

[![codecov](https://codecov.io/gh/dagny099/pymesh/branch/main/graph/badge.svg)](https://codecov.io/gh/dagny099/pymesh)

---

## 🚀 Features

- **Recursive module discovery**—walks your project directory, ignoring common folders (`__pycache__`, `.git`, virtual environments) to build a map of Python modules.
- **AST-based analysis**—extracts function definitions and actual function call usage across files (`import x`, `from x import y`, `x.y()` patterns).
- **Function-level dependency graph**—differentiates between `defines` (function → module) and `calls` (function → importing module) relationships.
- **Interactive visualization**—renders an embedded PyVis network in Streamlit with customizable node shapes, colors, and edge styles.
- **Flexible entry points**—select one or more scripts to serve as roots for the dependency analysis.
- **Export outputs**:
  - **HTML**: interactive graph with title, project path, and timestamp metadata.
  - **JSON**: enriched structure (`nodes` & `edges`) ready for graph databases like Neo4j.

---

## 📂 Project Structure

```
.
├── LICENSE.md
├── README.md                # This documentation
├── app.py                   # Streamlit entry-point
├── data/                    # Sample CSV data files
├── dependency_mapper_outputs/  # Generated HTML & JSON exports
├── json_to_csv.py           # Utility script for data conversion
├── notebooks/               # Demo or exploratory notebooks
│   └── Project Dependency Mapper.ipynb
├── poetry.lock              # Poetry lock file
├── pymesh/                  # Core library package
│   ├── __init__.py
│   ├── dependency_mapper.py # Module/file discovery logic
│   └── load_json_dep_map.cypher  # Cypher code to load JSON into Neo4j
├── pyproject.toml           # Poetry-managed dependencies & scripts
├── style_config.py          # UI text & styling constants
└── tests/                   # Unit tests for each component
    ├── __init__.py
    ├── test_discover.py     # Test discover_modules
    ├── test_graph.py        # Test graph_dependencies
    └── test_parsing.py      # Test parse_internal_deps
```

Helpful Note: Run this command at the command prompt to generate a tree of your project:  
```bash
tree -I '__pycache__|.DS_Store|*.pyc' -L 3
```

---

## 🛠️ Installation

This project uses [Poetry](https://python-poetry.org/) for dependency management and packaging.

```bash
# Clone the repo
git clone https://github.com/dagny099/pymesh.git
cd pymesh

# Install dependencies
poetry install
```

> **Note:** The default Python compatibility is `>=3.11`.

---

## ⚡ Usage

### 1. Run the Streamlit App

```bash
poetry run streamlit run app.py
```

1. **Project Directory**: Enter the path to your Python project root.
2. **Scan Modules**: Click **Scan for Modules** to detect all `.py` files.
3. **Select Entry Points**: Use the sidebar multiselect to choose one or more scripts as graph roots.
4. **Toggle Visibility**: Control which modules appear via checkboxes in the sidebar.
5. **Output Settings**: Customize HTML/JSON filenames and enable “Save outputs” to persist results.

The interactive graph will render inline, showing:

- **Star nodes** for entry scripts
- **Box nodes** for other modules
- **Ellipse nodes** for functions
- **Gray arrows** (solid) for `defines`
- **Yellow arrows** (dashed) for `calls`

### 2. Generated Files

By default, when **Save outputs** is checked, a folder `dependency_mapper_outputs/` will be created under your project root, containing:

- `<project_name>_dependency_map.html` — interactive PyVis graph with metadata header.
- `<project_name>_dependency_graph.json` — enriched JSON with:
  - `nodes`: list of `{ id, label, type, path, module }` objects
  - `edges`: list of `{ source, target, relationship }` objects

You can directly ingest this JSON into Neo4j or any other graph datastore.

---

## 🧪 Testing

Run unit tests with:

```bash
poetry run pytest
```

Tests are organized under the `tests/` directory, mirroring the `pymesh/` package.

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/awesome`).
3. Commit your changes (`git commit -m 'Add awesome feature'`).
4. Push to your branch (`git push origin feature/awesome`).
5. Open a Pull Request.

Ensure code is formatted with [Black](https://github.com/psf/black) (`poetry run black .`) and tests pass before submitting.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE.md).

---

*Happy graphing!* 🎉

