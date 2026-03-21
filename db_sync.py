"""
db_sync.py
──────────────────────────────────────────────────────────────────────────
Sync the ChromaDB vector store to/from a private HuggingFace Hub dataset.

Repo: dagny099/digital-twin-db  (created automatically on first push)
File: chroma_db.tar.gz

Usage:
    from db_sync import pull_db, push_db

    pull_db()   # download + extract → .chroma_db_DT/
    push_db()   # tar .chroma_db_DT/ + upload to HF Hub
"""

import os
import tarfile
import tempfile

HF_REPO_ID  = "dagny099/digital-twin-db"
HF_FILENAME = "chroma_db.tar.gz"
CHROMA_PATH = ".chroma_db_DT"


def _token() -> str | None:
    return os.getenv("HF_TOKEN")


def push_db() -> bool:
    """
    Tar .chroma_db_DT/ and upload to the HF Hub dataset repo.
    Creates the repo automatically if it doesn't exist yet.
    Returns True on success, False on any failure (non-fatal).
    """
    token = _token()
    if not token:
        print("db_sync: HF_TOKEN not set — skipping push.")
        return False

    if not os.path.exists(CHROMA_PATH):
        print(f"db_sync: {CHROMA_PATH}/ not found — nothing to push.")
        return False

    try:
        from huggingface_hub import HfApi
        api = HfApi(token=token)

        api.create_repo(
            repo_id=HF_REPO_ID,
            repo_type="dataset",
            private=True,
            exist_ok=True,
        )

        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
            tmp_path = tmp.name

        with tarfile.open(tmp_path, "w:gz") as tar:
            tar.add(CHROMA_PATH, arcname=CHROMA_PATH)

        api.upload_file(
            path_or_fileobj=tmp_path,
            path_in_repo=HF_FILENAME,
            repo_id=HF_REPO_ID,
            repo_type="dataset",
        )
        os.unlink(tmp_path)

        print(f"db_sync: pushed {CHROMA_PATH}/ → {HF_REPO_ID}/{HF_FILENAME}")
        return True

    except Exception as e:
        print(f"db_sync: push failed — {e}")
        return False


def pull_db() -> bool:
    """
    Download chroma_db.tar.gz from HF Hub and extract to .chroma_db_DT/.
    Returns True on success, False if not found or any error (non-fatal).
    """
    token = _token()
    if not token:
        print("db_sync: HF_TOKEN not set — skipping pull.")
        return False

    try:
        from huggingface_hub import hf_hub_download
        from huggingface_hub.utils import EntryNotFoundError, RepositoryNotFoundError

        local_path = hf_hub_download(
            repo_id=HF_REPO_ID,
            filename=HF_FILENAME,
            repo_type="dataset",
            token=token,
        )

        with tarfile.open(local_path, "r:gz") as tar:
            tar.extractall(".")

        print(f"db_sync: pulled {HF_REPO_ID}/{HF_FILENAME} → {CHROMA_PATH}/")
        return True

    except (EntryNotFoundError, RepositoryNotFoundError):
        print("db_sync: no cached DB on HF Hub — will run full ingestion.")
        return False
    except Exception as e:
        print(f"db_sync: pull failed — {e}")
        return False
