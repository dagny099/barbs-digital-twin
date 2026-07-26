#!/usr/bin/env python3
"""
Render project diagrams from committed Mermaid sources.

Phase 0 of docs/VISUAL_SYSTEM_ROADMAP.md: the July 2026 diagrams were committed
as PNGs with no source, so they could not be re-themed or regenerated. This
script closes that gap — .mmd in, PNG out, one command.

Usage
-----
    python scripts/render_diagrams.py                 # render every source
    python scripts/render_diagrams.py --only twin     # render matching sources
    python scripts/render_diagrams.py --check         # verify, write nothing (CI)

Setup
-----
Requires the mermaid CLI. Install once at the repo root:

    npm install @mermaid-js/mermaid-cli

On Linux/CI a puppeteer config is usually needed so mmdc can find a browser and
run without a sandbox. Point MERMAID_PUPPETEER_CONFIG at a JSON file like:

    {"executablePath": "/path/to/chrome",
     "args": ["--no-sandbox", "--disable-dev-shm-usage"]}

On macOS with a normal Chrome install, no config is usually needed.
"""

from __future__ import annotations

import argparse
import os
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "assets" / "diagram_src"
OUT_DIR = REPO_ROOT / "assets" / "project_diagrams"
HEADER = SRC_DIR / "_header.mmd"

# Chat-safe aspect band for `hero` assets — see VISUAL_SYSTEM_ROADMAP.md Phase 1.
# The old card system was uniformly 1.75; the July Mermaid renders ranged 0.45–6.15,
# which is what produced both the scroll wall and the illegible strip in chat.
ASPECT_MIN = 1.2
ASPECT_MAX = 2.4

RENDER_WIDTH = 1400
BACKGROUND = "white"


def find_mmdc() -> list[str]:
    """Locate the mermaid CLI, preferring a repo-local install."""
    local = REPO_ROOT / "node_modules" / ".bin" / "mmdc"
    if local.exists():
        return [str(local)]
    from shutil import which

    if which("mmdc"):
        return ["mmdc"]
    sys.exit(
        "mermaid CLI not found.\n"
        "Install it at the repo root with:  npm install @mermaid-js/mermaid-cli"
    )


def png_size(path: Path) -> tuple[int, int]:
    """Read width/height from a PNG header without pulling in Pillow."""
    with path.open("rb") as fh:
        head = fh.read(33)
    width, height = struct.unpack(">II", head[16:24])
    return width, height


def compose_source(src: Path) -> str:
    """Return the source text, prepending the shared theme header when absent."""
    text = src.read_text(encoding="utf-8")
    if text.lstrip().startswith("---"):
        return text  # source declares its own frontmatter; leave it alone
    if not HEADER.exists():
        return text
    return HEADER.read_text(encoding="utf-8") + "\n" + text


def render_one(src: Path, mmdc: list[str], check: bool) -> tuple[bool, str]:
    """Render a single source. Returns (ok, message)."""
    out = OUT_DIR / f"{src.stem}.png"
    target = out if not check else Path(tempfile.mkdtemp()) / f"{src.stem}.png"

    with tempfile.NamedTemporaryFile("w", suffix=".mmd", delete=False) as tmp:
        tmp.write(compose_source(src))
        composed = Path(tmp.name)

    cmd = [*mmdc, "-i", str(composed), "-o", str(target),
           "-b", BACKGROUND, "-w", str(RENDER_WIDTH)]
    pptr = os.environ.get("MERMAID_PUPPETEER_CONFIG")
    if pptr:
        cmd += ["-p", pptr]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return False, f"{src.name}: render timed out"
    finally:
        composed.unlink(missing_ok=True)

    if proc.returncode != 0 or not target.exists():
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        return False, f"{src.name}: render failed — {detail[-1] if detail else 'unknown error'}"

    width, height = png_size(target)
    ratio = width / height
    shape = f"{width}x{height} ratio {ratio:.2f}"

    if not (ASPECT_MIN <= ratio <= ASPECT_MAX):
        return False, (
            f"{src.name}: {shape} outside chat-safe band "
            f"{ASPECT_MIN}–{ASPECT_MAX}. Either restructure the layout (stack rows "
            f"instead of one long line) or file this as an `architecture` asset "
            f"rather than a `hero` one."
        )

    return True, f"{src.name}: {shape} -> {target.name}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", help="substring filter on source filename")
    parser.add_argument("--check", action="store_true",
                        help="render to a temp dir and validate; write nothing")
    args = parser.parse_args()

    if not SRC_DIR.exists():
        sys.exit(f"No source directory at {SRC_DIR}")

    sources = sorted(p for p in SRC_DIR.glob("*.mmd") if not p.name.startswith("_"))
    if args.only:
        sources = [p for p in sources if args.only.lower() in p.name.lower()]
    if not sources:
        sys.exit("No matching .mmd sources found.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    mmdc = find_mmdc()

    failures = 0
    for src in sources:
        ok, message = render_one(src, mmdc, args.check)
        print(("  ok  " if ok else "  FAIL ") + message)
        failures += 0 if ok else 1

    print(f"\n{len(sources) - failures}/{len(sources)} rendered"
          + (" (check mode — nothing written)" if args.check else ""))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
