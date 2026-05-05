"""
Test configuration: sets up the environment so app.py can be imported
without real API keys, a live OpenAI client, or a running Gradio server.

Module-level side effects in app.py that we must handle before import:
  1. Raises if OPENAI_API_KEY env var is missing
  2. Calls OpenAI(api_key=...) to create a module-level client
  3. Opens SYSTEM_PROMPT.md with a relative path (requires CWD = project root)
  4. Loads SVG assets for CATEGORY_ICONS (uses absolute paths, no special handling needed)
  5. If .chroma_db_DT is absent, calls db_sync.pull_db() to fetch from HF Hub
  6. Calls chromadb.PersistentClient() and collection.count(); if count==0, runs
     subprocess.run(["python", "scripts/ingest.py", "--all"]) to rebuild the DB

Items 5 and 6 only matter on CI where the DB directory does not exist.
We mock chromadb so count() returns 1 (skipping the ingest subprocess) and
mock db_sync.pull_db so no HF Hub token is needed.

The Gradio UI build and demo.launch() are inside `if __name__ == "__main__":`
so they never run during import.
"""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

os.environ.setdefault("OPENAI_API_KEY", "sk-test-placeholder")

_mock_collection = MagicMock()
_mock_collection.count.return_value = 1  # non-zero: prevents ingest subprocess

_mock_chroma_client = MagicMock()
_mock_chroma_client.get_or_create_collection.return_value = _mock_collection

with (
    patch("openai.OpenAI", return_value=MagicMock()),
    patch("chromadb.PersistentClient", return_value=_mock_chroma_client),
    patch("db_sync.pull_db"),  # prevents HF Hub pull when .chroma_db_DT is absent
):
    import app  # noqa: F401  (imported here so all test files share one import)
