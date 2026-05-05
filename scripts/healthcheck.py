#!/usr/bin/env python3
"""
Integration healthcheck for Barb's Digital Twin.

Verifies that all external service connections are live and credentials are
valid without running the full app. Designed to be run manually before any
deploy that touches credentials, environment config, or the ChromaDB collection.

Usage:
    python scripts/healthcheck.py            # validate everything (no notification sent)
    python scripts/healthcheck.py --notify   # also send a real Pushover notification
    python scripts/healthcheck.py --checks openai chroma  # run specific checks only

Checks:
    env      Required and optional environment variables are present
    openai   OpenAI API key is valid and the configured LLM model resolves
    embed    Embedding endpoint responds correctly
    chroma   ChromaDB collection exists and is non-empty
    pushover Pushover credentials are accepted (--notify sends a real notification)

Exit codes:
    0  All checks passed
    1  One or more checks failed
"""

import argparse
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)

# ── Mirror app.py configuration exactly ──────────────────────────────────────

CHROMA_PATH = str(ROOT / ".chroma_db_DT")
COLLECTION_NAME = "barb-twin"
EMBED_MODEL = "text-embedding-3-small"
PUSHOVER_VALIDATE_URL = "https://api.pushover.net/1/users/validate.json"
PUSHOVER_SEND_URL = "https://api.pushover.net/1/messages.json"

_raw_model = os.getenv("LLM_MODEL", "gpt-4.1")
LLM_MODEL = _raw_model if "/" in _raw_model else f"openai/{_raw_model}"

REQUIRED_ENV_VARS = ["OPENAI_API_KEY"]
OPTIONAL_ENV_VARS = ["PUSHOVER_USER", "PUSHOVER_TOKEN", "PUSHOVER_DEVICE", "LLM_MODEL"]

ALL_CHECKS = ["env", "openai", "embed", "chroma", "pushover"]

# ── Result tracking ───────────────────────────────────────────────────────────

results = []


def _record(status: str, name: str, detail: str):
    """Print and store a check result."""
    icon = {"PASS": "✓", "FAIL": "✗", "SKIP": "⚠"}.get(status, "?")
    print(f"  {icon} {status:<4}  {name:<22}  {detail}")
    results.append((status, name, detail))


# ── Individual checks ─────────────────────────────────────────────────────────

def check_env():
    all_ok = True
    for var in REQUIRED_ENV_VARS:
        val = os.getenv(var)
        if val:
            display = val[:6] + "..." if len(val) > 6 else "***"
            _record("PASS", f"env:{var}", f"present ({display})")
        else:
            _record("FAIL", f"env:{var}", "MISSING — required")
            all_ok = False
    for var in OPTIONAL_ENV_VARS:
        val = os.getenv(var)
        if val:
            display = val[:6] + "..." if len(val) > 6 else "***"
            _record("PASS", f"env:{var}", f"present ({display})")
        else:
            _record("SKIP", f"env:{var}", "not set (optional)")
    return all_ok


def check_openai():
    try:
        import litellm
        litellm.suppress_debug_info = True

        start = time.time()
        resp = litellm.completion(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=1,
        )
        elapsed = round((time.time() - start) * 1000)
        content = resp.choices[0].message.content or ""
        _record("PASS", "openai:llm", f"model={LLM_MODEL} | {elapsed}ms | reply={repr(content[:30])}")
        return True
    except Exception as e:
        _record("FAIL", "openai:llm", f"{type(e).__name__}: {e}")
        return False


def check_embed():
    try:
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            _record("SKIP", "openai:embed", "no OPENAI_API_KEY")
            return True

        client = OpenAI(api_key=api_key)
        start = time.time()
        resp = client.embeddings.create(input="healthcheck", model=EMBED_MODEL)
        elapsed = round((time.time() - start) * 1000)
        dims = len(resp.data[0].embedding)
        _record("PASS", "openai:embed", f"model={EMBED_MODEL} | {dims}d vector | {elapsed}ms")
        return True
    except Exception as e:
        _record("FAIL", "openai:embed", f"{type(e).__name__}: {e}")
        return False


def check_chroma():
    try:
        import chromadb

        if not os.path.exists(CHROMA_PATH):
            _record("FAIL", "chroma:collection", f"path not found: {CHROMA_PATH}")
            return False

        client = chromadb.PersistentClient(path=CHROMA_PATH)
        col = client.get_or_create_collection(name=COLLECTION_NAME)
        count = col.count()

        if count == 0:
            _record("FAIL", "chroma:collection", f"collection '{COLLECTION_NAME}' is empty")
            return False

        _record("PASS", "chroma:collection", f"'{COLLECTION_NAME}' | {count} chunks")
        return True
    except Exception as e:
        _record("FAIL", "chroma:collection", f"{type(e).__name__}: {e}")
        return False


def check_pushover(send_notification: bool = False):
    import requests as req

    user = os.getenv("PUSHOVER_USER")
    token = os.getenv("PUSHOVER_TOKEN")

    if not user or not token:
        _record("SKIP", "pushover", "PUSHOVER_USER or PUSHOVER_TOKEN not set")
        return True  # not a failure — Pushover is optional

    if send_notification:
        # Full end-to-end: send a labeled notification to confirm delivery
        payload = {
            "user": user,
            "token": token,
            "message": "[healthcheck] Digital Twin connectivity check passed",
            "title": "Healthcheck",
        }
        device = os.getenv("PUSHOVER_DEVICE")
        if device:
            payload["device"] = device
        try:
            resp = req.post(PUSHOVER_SEND_URL, data=payload, timeout=10)
            data = resp.json()
            if resp.ok and data.get("status") == 1:
                _record("PASS", "pushover:send", f"notification delivered | request={data.get('request', '')[:12]}")
                return True
            else:
                _record("FAIL", "pushover:send", f"HTTP {resp.status_code} | errors={data.get('errors', [])}")
                return False
        except Exception as e:
            _record("FAIL", "pushover:send", f"{type(e).__name__}: {e}")
            return False
    else:
        # Credential validation only — no notification sent
        try:
            resp = req.post(
                PUSHOVER_VALIDATE_URL,
                data={"token": token, "user": user},
                timeout=10,
            )
            data = resp.json()
            if resp.ok and data.get("status") == 1:
                devices = data.get("devices", [])
                _record("PASS", "pushover:creds", f"valid | devices={devices}")
                return True
            else:
                _record("FAIL", "pushover:creds", f"HTTP {resp.status_code} | errors={data.get('errors', [])}")
                return False
        except Exception as e:
            _record("FAIL", "pushover:creds", f"{type(e).__name__}: {e}")
            return False


# ── Runner ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Healthcheck: verify all external service connections are live.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--notify",
        action="store_true",
        help="Send a real Pushover notification (confirms end-to-end delivery)",
    )
    parser.add_argument(
        "--checks",
        nargs="+",
        choices=ALL_CHECKS,
        default=ALL_CHECKS,
        metavar="CHECK",
        help=f"Run only these checks (choices: {', '.join(ALL_CHECKS)})",
    )
    args = parser.parse_args()

    print(f"\nHealthcheck — {ROOT.name}")
    print(f"  LLM model : {LLM_MODEL}")
    print(f"  ChromaDB  : {CHROMA_PATH}")
    print(f"  Mode      : {'--notify (will send Pushover notification)' if args.notify else 'validate only (no notification sent)'}")
    print()

    check_map = {
        "env": check_env,
        "openai": check_openai,
        "embed": check_embed,
        "chroma": check_chroma,
        "pushover": lambda: check_pushover(send_notification=args.notify),
    }

    all_passed = True
    for name in args.checks:
        passed = check_map[name]()
        if not passed:
            all_passed = False

    passed_count = sum(1 for s, _, _ in results if s == "PASS")
    failed_count = sum(1 for s, _, _ in results if s == "FAIL")
    skipped_count = sum(1 for s, _, _ in results if s == "SKIP")

    print()
    print(f"  {passed_count} passed  {failed_count} failed  {skipped_count} skipped")

    if all_passed:
        print("  All checks passed — safe to deploy.\n")
        sys.exit(0)
    else:
        print("  One or more checks failed — do not deploy.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
