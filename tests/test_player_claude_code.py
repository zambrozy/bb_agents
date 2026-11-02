"""Tests for the Claude Code player (subprocess is mocked)."""

import json
import subprocess
from unittest.mock import patch

import pytest

import agents.player as player_module
import agents.player_claude_code as cc
from agents.player import create_player
from models.bidding import PlayerReply

ANSWER = {"reasoning": "balanced 15 HCP", "call": "1NT"}


def _proc(stdout: str, returncode: int = 0):
    """Fake CompletedProcess."""
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr="boom"
    )


def _ok(answer: dict = ANSWER):
    """Fake process whose output holds a structured answer."""
    return _proc(json.dumps({"structured_output": answer}))


@pytest.fixture(autouse=True)
def _cli_on_path():
    """Pretend the `claude` binary exists."""
    with patch.object(cc.shutil, "which", return_value="/bin/claude"):
        yield


def test_command_disables_tools_and_sets_prompts():
    """Tools off, own system prompt, schema, no saved session."""
    with patch.object(cc.subprocess, "run", return_value=_ok()) as run:
        answer = cc.ask_claude_json(
            "my turn", {"type": "object"}, "be a player",
            "sonnet", timeout=5, max_retries=0,
        )
    cmd = run.call_args.args[0]
    assert answer == ANSWER
    assert cmd[:3] == ["/bin/claude", "-p", "my turn"]
    assert cmd[cmd.index("--model") + 1] == "sonnet"
    assert cmd[cmd.index("--system-prompt") + 1] == "be a player"
    assert cmd[cmd.index("--tools") + 1] == ""
    assert "--no-session-persistence" in cmd
    assert run.call_args.kwargs["timeout"] == 5


def test_runs_outside_the_project_directory():
    """The CLI starts in a temp dir so CLAUDE.md is not picked up."""
    with patch.object(cc.subprocess, "run", return_value=_ok()) as run:
        cc.ask_claude_json("t", {}, "s", "sonnet", 5, 0)
    assert "bb_agents" not in run.call_args.kwargs["cwd"]


def test_text_result_is_parsed_when_no_structured_output():
    """Falls back to the JSON text in `result`."""
    out = _proc(json.dumps({"result": json.dumps(ANSWER)}))
    with patch.object(cc.subprocess, "run", return_value=out):
        assert cc.ask_claude_json("t", {}, "s", "sonnet", 5, 0) == ANSWER


def test_failed_call_is_rerun_up_to_max_retries():
    """A failure followed by a success is hidden by one retry."""
    results = [_proc("", returncode=1), _ok()]
    with patch.object(cc.subprocess, "run", side_effect=results) as run:
        assert cc.ask_claude_json("t", {}, "s", "sonnet", 5, 1) == ANSWER
    assert run.call_count == 2


def test_error_is_raised_when_retries_run_out():
    """Errors, timeouts and bad output surface after the last try."""
    failures = [
        _proc("", returncode=1),
        _proc(json.dumps({"is_error": True, "result": "overloaded"})),
        _proc("not json"),
    ]
    for bad in failures:
        with patch.object(cc.subprocess, "run", return_value=bad) as run:
            with pytest.raises((RuntimeError, json.JSONDecodeError)):
                cc.ask_claude_json("t", {}, "s", "sonnet", 5, 2)
        assert run.call_count == 3

    timeout = subprocess.TimeoutExpired(cmd="claude", timeout=5)
    with patch.object(cc.subprocess, "run", side_effect=timeout):
        with pytest.raises(subprocess.TimeoutExpired):
            cc.ask_claude_json("t", {}, "s", "sonnet", 5, 0)


def test_missing_cli_is_not_retried():
    """No binary on PATH fails at once with a clear message."""
    with patch.object(cc.shutil, "which", return_value=None):
        with patch.object(cc.subprocess, "run") as run:
            with pytest.raises(FileNotFoundError, match="not on PATH|not found"):
                cc.ask_claude_json("t", {}, "s", "sonnet", 5, 3)
    run.assert_not_called()


def test_create_player_routes_claude_code_prefix():
    """`claude_code:<alias>` skips init_chat_model and returns a
    PlayerReply with the seat's system prompt."""
    with patch.object(cc.subprocess, "run", return_value=_ok()) as run:
        with patch.object(player_module, "init_chat_model") as init:
            player = create_player(
                "claude_code:haiku", "EAST", "SAYC", 5, 0
            )
            reply = player.invoke({"turn": "your turn"})
    init.assert_not_called()
    assert reply == PlayerReply(**ANSWER)
    cmd = run.call_args.args[0]
    assert cmd[cmd.index("--model") + 1] == "haiku"
    system = cmd[cmd.index("--system-prompt") + 1]
    assert "seat EAST" in system and "partner is WEST" in system
