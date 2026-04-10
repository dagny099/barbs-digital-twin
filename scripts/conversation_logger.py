"""
Digital Twin v2 — Conversation Logger
Logs conversation turns to a HuggingFace private dataset.

Setup:
  1. Create a private dataset on HuggingFace: huggingface.co/new-dataset
     Name it something like: dagny099/dt-conversation-logs
  2. Set HF_TOKEN env var (write-access token)
  3. Set HF_LOG_DATASET env var (e.g. "dagny099/dt-conversation-logs")

Usage:
  from conversation_logger import ConversationLogger
  logger = ConversationLogger()

  # On each chatbot turn:
  logger.log_turn(
      user_message="What problems does Dagny solve?",
      bot_response="I'm a consultant who codes...",
      response_time_ms=1230
  )
"""

import json
import os
import time
import uuid
import threading
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
HF_LOG_DATASET = os.getenv("HF_LOG_DATASET", "dagny099/dt-conversation-logs")
HF_TOKEN = os.getenv("HF_TOKEN", "")
FLUSH_EVERY_N_TURNS = 10
FLUSH_INTERVAL_SECONDS = 300  # 5 minutes
LOCAL_BUFFER_PATH = Path("/tmp/dt_log_buffer.jsonl")

# The four example questions — used for classification
EXAMPLE_QUESTIONS = {
    "Q1": "What problems does Dagny solve?",
    "Q2": "Walk me through a project",
    "Q3": "How was this digital twin built?",
    "Q4": "What does 'making meaning from messy data' actually mean?",
}

# Fuzzy match threshold (ratio of matching words)
MATCH_THRESHOLD = 0.7


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _classify_example_question(message: str) -> tuple[bool, str]:
    """Check if a message matches one of the example questions.

    Returns (is_example, which_example) e.g. (True, "Q1") or (False, "none").
    Uses simple word-overlap matching to handle minor rephrasing.
    """
    msg_words = set(message.lower().split())
    best_match = "none"
    best_score = 0.0

    for qid, question in EXAMPLE_QUESTIONS.items():
        q_words = set(question.lower().split())
        if not q_words:
            continue
        overlap = len(msg_words & q_words) / len(q_words)
        if overlap > best_score:
            best_score = overlap
            best_match = qid

    is_example = best_score >= MATCH_THRESHOLD
    return is_example, best_match if is_example else "none"


def _push_to_hf(records: list[dict]) -> bool:
    """Push buffered records to HuggingFace dataset as a JSONL file.

    Each flush creates a new file partitioned by date so appends don't conflict.
    Returns True on success, False on failure (records stay in local buffer).
    """
    if not HF_TOKEN or not HF_LOG_DATASET:
        return False

    try:
        from huggingface_hub import HfApi
        api = HfApi(token=HF_TOKEN)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"logs/{timestamp}_{uuid.uuid4().hex[:8]}.jsonl"

        content = "\n".join(json.dumps(r, default=str) for r in records)
        content_bytes = content.encode("utf-8")

        api.upload_file(
            path_or_fileobj=content_bytes,
            path_in_repo=filename,
            repo_id=HF_LOG_DATASET,
            repo_type="dataset",
        )
        return True

    except Exception as e:
        print(f"[ConversationLogger] HF push failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
class ConversationLogger:
    """Lightweight conversation logger for the Digital Twin chatbot.

    Tracks:
      - Session ID and turn number (session depth analysis)
      - Whether the user clicked an example question (click rate)
      - Response time (latency monitoring)
      - Notification fires (KB gap detection)
      - Message content (for eval harness comparison)

    Buffers in memory and flushes to HuggingFace every N turns
    or every M seconds, whichever comes first. Falls back to
    local JSONL if HF push fails.
    """

    def __init__(self):
        self.session_id = uuid.uuid4().hex[:12]
        self.turn_number = 0
        self.buffer: list[dict] = []
        self._lock = threading.Lock()

        # Start background flush timer
        self._start_flush_timer()

    def _start_flush_timer(self):
        """Periodic flush in case turns are infrequent."""
        def _timer():
            self.flush()
            self._start_flush_timer()

        self._timer = threading.Timer(FLUSH_INTERVAL_SECONDS, _timer)
        self._timer.daemon = True
        self._timer.start()

    def new_session(self):
        """Call when a new conversation session starts (e.g. page refresh)."""
        self.flush()  # flush any remaining turns from previous session
        self.session_id = uuid.uuid4().hex[:12]
        self.turn_number = 0

    def log_turn(
        self,
        user_message: str,
        bot_response: str,
        response_time_ms: int = 0,
        notification_fired: bool = False,
    ):
        """Log a single conversation turn."""
        self.turn_number += 1
        is_example, which_example = _classify_example_question(user_message)

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": self.session_id,
            "turn_number": self.turn_number,
            "user_message": user_message,
            "bot_response_length": len(bot_response),
            "bot_response": bot_response,  # Remove this line if storage is a concern
            "was_example_q": is_example,
            "which_example": which_example,
            "notification_fired": notification_fired,
            "response_time_ms": response_time_ms,
        }

        with self._lock:
            self.buffer.append(record)

            if len(self.buffer) >= FLUSH_EVERY_N_TURNS:
                self._flush_locked()

    def flush(self):
        """Force flush buffered records to HF (or local fallback)."""
        with self._lock:
            self._flush_locked()

    def _flush_locked(self):
        """Internal flush — must be called with self._lock held."""
        if not self.buffer:
            return

        records = list(self.buffer)
        self.buffer.clear()

        success = _push_to_hf(records)

        if not success:
            # Fallback: append to local JSONL file
            try:
                with open(LOCAL_BUFFER_PATH, "a") as f:
                    for r in records:
                        f.write(json.dumps(r, default=str) + "\n")
                print(f"[ConversationLogger] Saved {len(records)} turns to local buffer")
            except Exception as e:
                print(f"[ConversationLogger] Local save also failed: {e}")


# ---------------------------------------------------------------------------
# Integration example for Gradio chatbot
# ---------------------------------------------------------------------------
"""
# In your Gradio app:

from conversation_logger import ConversationLogger

logger = ConversationLogger()

def respond(message, history):
    start = time.time()

    # ... your existing RAG retrieval + LLM generation ...
    bot_response = generate_response(message, history)

    elapsed_ms = int((time.time() - start) * 1000)

    # Log the turn
    logger.log_turn(
        user_message=message,
        bot_response=bot_response,
        response_time_ms=elapsed_ms,
        notification_fired=False,  # set True if send_notification was called
    )

    return bot_response

# If Gradio exposes a session/clear event, reset the session:
# demo.load(fn=lambda: logger.new_session())
"""
