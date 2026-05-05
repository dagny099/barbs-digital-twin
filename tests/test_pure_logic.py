"""
Tier 1 unit tests: pure logic functions in app.py.

All tests here are deterministic, have zero external dependencies (no API
calls, no filesystem I/O beyond what happens at import), and run in <1s.
"""
import json
from unittest.mock import MagicMock, patch

import pytest
import app


# ── dice_roll ─────────────────────────────────────────────────────────────────

class TestDiceRoll:
    def test_returns_int(self):
        assert isinstance(app.dice_roll(), int)

    def test_range_over_many_calls(self):
        results = {app.dice_roll() for _ in range(200)}
        assert results <= {1, 2, 3, 4, 5, 6}

    def test_never_below_one(self):
        assert all(app.dice_roll() >= 1 for _ in range(100))

    def test_never_above_six(self):
        assert all(app.dice_roll() <= 6 for _ in range(100))


# ── detect_audience_tier ──────────────────────────────────────────────────────

class TestDetectAudienceTier:
    def test_public_by_default(self):
        assert app.detect_audience_tier("hello there", []) == "public"

    def test_inner_circle_phrase_in_message(self):
        assert app.detect_audience_tier("somos un equipo", []) == "inner_circle"

    def test_personal_phrase_in_message(self):
        assert app.detect_audience_tier("I remember the daisy 5k", []) == "personal"

    def test_inner_circle_phrase_in_history(self):
        history = [{"role": "user", "content": "somos un equipo"}]
        assert app.detect_audience_tier("what's new?", history) == "inner_circle"

    def test_personal_phrase_in_history(self):
        history = [{"role": "user", "content": "easy button times"}]
        assert app.detect_audience_tier("what's new?", history) == "personal"

    def test_inner_circle_beats_personal_when_both_present(self):
        history = [{"role": "user", "content": "easy button"}]
        assert app.detect_audience_tier("somos un equipo", history) == "inner_circle"

    def test_case_insensitive_inner_circle(self):
        assert app.detect_audience_tier("SOMOS UN EQUIPO", []) == "inner_circle"

    def test_case_insensitive_personal(self):
        assert app.detect_audience_tier("EASY BUTTON", []) == "personal"

    def test_ignores_assistant_turns_in_history(self):
        # Phrases spoken by the assistant should not elevate tier
        history = [{"role": "assistant", "content": "somos un equipo"}]
        assert app.detect_audience_tier("hi", history) == "public"

    def test_empty_history(self):
        assert app.detect_audience_tier("tell me about yourself", []) == "public"

    def test_phrase_embedded_in_longer_message(self):
        assert app.detect_audience_tier("oh yes the daisy 5k was great", []) == "personal"


# ── build_sensitivity_filter ──────────────────────────────────────────────────

class TestBuildSensitivityFilter:
    def test_public_returns_eq_filter(self):
        assert app.build_sensitivity_filter("public") == {"sensitivity": {"$eq": "public"}}

    def test_personal_returns_in_filter(self):
        result = app.build_sensitivity_filter("personal")
        assert result == {"sensitivity": {"$in": ["public", "personal"]}}

    def test_inner_circle_returns_none(self):
        assert app.build_sensitivity_filter("inner_circle") is None

    def test_unknown_tier_falls_back_to_public(self):
        # Unrecognized tier should be treated as public (most restrictive)
        assert app.build_sensitivity_filter("unknown_tier") == {"sensitivity": {"$eq": "public"}}


# ── model_supports_tools ──────────────────────────────────────────────────────

class TestModelSupportsTools:
    def test_known_capable_model(self):
        assert app.model_supports_tools("openai/gpt-4.1") is True

    def test_known_incapable_model(self):
        assert app.model_supports_tools("ollama/mistral") is False

    def test_unlisted_model_defaults_to_true(self):
        # New models are assumed capable until explicitly blocklisted
        assert app.model_supports_tools("some-future-model/xyz") is True

    def test_anthropic_model_supports_tools(self):
        assert app.model_supports_tools("anthropic/claude-haiku-4.5") is True


# ── _compute_similarity_stats ─────────────────────────────────────────────────

class TestComputeSimilarityStats:
    def test_empty_returns_zeros(self):
        assert app._compute_similarity_stats([]) == {"avg": 0.0, "max": 0.0}

    def test_perfect_match_distance_zero(self):
        result = app._compute_similarity_stats([0.0])
        assert result["avg"] == 1.0
        assert result["max"] == 1.0

    def test_known_distance_one(self):
        # dist=1.0 → sim = 1 - (1²/2) = 0.5
        result = app._compute_similarity_stats([1.0])
        assert result["avg"] == 0.5
        assert result["max"] == 0.5

    def test_multiple_distances_avg_and_max(self):
        # [0.0, 1.0] → sims [1.0, 0.5] → avg=0.75, max=1.0
        result = app._compute_similarity_stats([0.0, 1.0])
        assert result["avg"] == 0.75
        assert result["max"] == 1.0

    def test_large_distance_clamped_to_zero(self):
        # dist=2.0 → 1-(4/2)=-1.0 → clamped to 0.0
        result = app._compute_similarity_stats([2.0])
        assert result["avg"] == 0.0
        assert result["max"] == 0.0

    def test_returns_rounded_values(self):
        result = app._compute_similarity_stats([0.1, 0.2, 0.3])
        assert isinstance(result["avg"], float)
        assert len(str(result["avg"]).split(".")[-1]) <= 3


# ── _redact_log_text ──────────────────────────────────────────────────────────

class TestRedactLogText:
    def test_redacts_email(self):
        assert app._redact_log_text("reach me at foo@bar.com please") == "reach me at [EMAIL] please"

    def test_redacts_us_phone_dashes(self):
        result = app._redact_log_text("call 512-555-1234 anytime")
        assert "[PHONE]" in result
        assert "512" not in result

    def test_redacts_us_phone_dots(self):
        result = app._redact_log_text("try 512.555.1234")
        assert "[PHONE]" in result

    def test_redacts_us_phone_no_separator(self):
        result = app._redact_log_text("number is 5125551234")
        assert "[PHONE]" in result

    def test_leaves_normal_text_unchanged(self):
        text = "I love machine learning and RAG pipelines"
        assert app._redact_log_text(text) == text

    def test_none_returns_empty_string(self):
        assert app._redact_log_text(None) == ""

    def test_empty_string_returns_empty_string(self):
        assert app._redact_log_text("") == ""

    def test_multiple_emails_all_redacted(self):
        result = app._redact_log_text("a@b.com and c@d.org")
        assert "[EMAIL]" in result
        assert "@" not in result


# ── _build_response_preview ───────────────────────────────────────────────────

class TestBuildResponsePreview:
    def test_short_text_returned_unchanged(self):
        text = "Hello there"
        assert app._build_response_preview(text) == text

    def test_long_text_truncated_with_ellipsis(self):
        text = "x" * 400
        result = app._build_response_preview(text)
        assert len(result) <= 300
        assert result.endswith("…")

    def test_exact_limit_not_truncated(self):
        text = "x" * 300
        result = app._build_response_preview(text)
        assert not result.endswith("…")

    def test_custom_n_respected(self):
        text = "x" * 50
        result = app._build_response_preview(text, n=20)
        assert len(result) <= 20
        assert result.endswith("…")

    def test_none_returns_empty_string(self):
        assert app._build_response_preview(None) == ""

    def test_newlines_collapsed(self):
        result = app._build_response_preview("line one\nline two")
        assert "\n" not in result

    def test_leading_trailing_whitespace_stripped(self):
        result = app._build_response_preview("  hello  ")
        assert result == "hello"


# ── handle_tool_call ──────────────────────────────────────────────────────────

def _make_tool_call(name, arguments="{}"):
    """Build a minimal mock tool call object matching the OpenAI SDK shape."""
    tc = MagicMock()
    tc.function.name = name
    tc.function.arguments = arguments
    tc.id = "call_test_001"
    return tc


class TestHandleToolCall:
    def test_dice_roll_dispatched_correctly(self):
        tc = _make_tool_call("dice_roll")
        results = app.handle_tool_call([tc])
        assert len(results) == 1
        content = results[0]["content"]
        assert content.startswith("Dice roll was: ")
        value = int(content.split(": ")[1])
        assert 1 <= value <= 6

    def test_dice_roll_result_role_is_tool(self):
        tc = _make_tool_call("dice_roll")
        results = app.handle_tool_call([tc])
        assert results[0]["role"] == "tool"

    def test_send_notification_dispatched_with_correct_arg(self):
        tc = _make_tool_call("send_notification", json.dumps({"message": "hello Barbara"}))
        with patch.object(app, "send_notification", return_value="Notification message was sent. Pushover request_id=abc123") as mock_notify:
            results = app.handle_tool_call([tc])
        mock_notify.assert_called_once_with("hello Barbara")
        assert "sent" in results[0]["content"]

    def test_unknown_function_returns_error_message(self):
        tc = _make_tool_call("launch_rockets")
        results = app.handle_tool_call([tc])
        assert "Unknown function" in results[0]["content"]

    def test_tool_call_id_preserved_in_result(self):
        tc = _make_tool_call("dice_roll")
        tc.id = "call_xyz_999"
        results = app.handle_tool_call([tc])
        assert results[0]["tool_call_id"] == "call_xyz_999"

    def test_multiple_tool_calls_returns_multiple_results(self):
        tc1 = _make_tool_call("dice_roll")
        tc2 = _make_tool_call("dice_roll")
        tc1.id = "call_001"
        tc2.id = "call_002"
        results = app.handle_tool_call([tc1, tc2])
        assert len(results) == 2
        assert results[0]["tool_call_id"] == "call_001"
        assert results[1]["tool_call_id"] == "call_002"

    def test_empty_tool_call_list(self):
        results = app.handle_tool_call([])
        assert results == []
