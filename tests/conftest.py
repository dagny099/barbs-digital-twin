"""
Test configuration: sets up the environment so app.py can be imported
without real API keys, a live OpenAI client, or a running Gradio server.

Module-level side effects in app.py that we must handle before import:
  1. Raises if OPENAI_API_KEY env var is missing
  2. Calls OpenAI(api_key=...) to create a module-level client
  3. Opens SYSTEM_PROMPT.md with a relative path (requires CWD = project root)
  4. Loads SVG assets for CATEGORY_ICONS (uses absolute paths, no special handling needed)

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

with patch("openai.OpenAI", return_value=MagicMock()):
    import app  # noqa: F401  (imported here so all test files share one import)
