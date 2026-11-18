"""Player backed by Claude Code headless mode (`claude -p`).

Calls go through the `claude` CLI, so they count against the Claude
subscription instead of requiring an API key.
"""

import json
import shutil
import subprocess
import tempfile

from langchain_core.runnables import Runnable, RunnableLambda

from consts import CLAUDE_BIN
from models.bidding.call import PlayerReply
from tracing import trace_llm_call


@trace_llm_call
def run_claude(cmd: list[str], timeout: float) -> dict:
    """Run a `claude -p` command (cmd: list[str], timeout: seconds)
    -> parsed JSON printed by the CLI.

    Runs in an empty temp directory, so no project CLAUDE.md is loaded.

    Raises:
        FileNotFoundError: If the CLI is not on PATH.
        RuntimeError: If the CLI fails or reports an error.
        subprocess.TimeoutExpired: If it runs longer than `timeout`.
        json.JSONDecodeError: If the output is not JSON.
    """
    binary = shutil.which(cmd[0])
    if binary is None:
        raise FileNotFoundError(
            f"'{cmd[0]}' not found on PATH. Set CLAUDE_BIN in consts "
            "to the full path (run `which claude` in a terminal)."
        )
    with tempfile.TemporaryDirectory() as workdir:
        proc = subprocess.run(
            [binary, *cmd[1:]],
            stdin=subprocess.DEVNULL,  # REPL/Jupyter stdin would block
            capture_output=True, text=True, timeout=timeout,
            cwd=workdir,
        )
    if proc.returncode != 0:
        raise RuntimeError(
            f"claude exited with {proc.returncode}:\n"
            f"{proc.stderr or proc.stdout}"
        )
    data = json.loads(proc.stdout)
    if data.get("is_error"):
        raise RuntimeError(f"Claude error: {data.get('result')}")

    return data


def ask_claude_json(
    prompt: str,
    schema: dict,
    system_prompt: str,
    model: str,
    timeout: float,
    max_retries: int,
) -> dict:
    """Ask Claude for a JSON answer (prompt, schema: JSON Schema,
    system_prompt, model: alias such as "sonnet", timeout: seconds,
    max_retries: reruns after a failed call) -> dict matching schema.

    Tools are disabled and the default Claude Code system prompt is
    replaced by `system_prompt`.
    """
    cmd = [
        CLAUDE_BIN, "-p", prompt,
        "--model", model,
        "--output-format", "json",
        "--json-schema", json.dumps(schema),
        "--system-prompt", system_prompt,
        "--tools", "",
        "--no-session-persistence",
    ]
    for attempt in range(max_retries + 1):
        try:
            data = run_claude(cmd, timeout)
            if "structured_output" in data:
                return data["structured_output"]
            return json.loads(data["result"])
        except (
            RuntimeError,
            subprocess.TimeoutExpired,
            json.JSONDecodeError,
            KeyError,
        ):
            if attempt == max_retries:
                raise


def create_claude_code_player(
    model: str,
    system_prompt: str,
    timeout: float,
    max_retries: int,
) -> Runnable[dict[str, str], PlayerReply]:
    """Build a Claude Code player (model: alias such as "sonnet",
    system_prompt, timeout: seconds per call, max_retries: int)
    -> runnable taking {"turn": str} and returning a PlayerReply."""
    schema = PlayerReply.model_json_schema()

    def answer(inputs: dict[str, str]) -> PlayerReply:
        """One turn (inputs: {"turn": str}) -> PlayerReply."""
        return PlayerReply.model_validate(
            ask_claude_json(
                inputs["turn"], schema, system_prompt,
                model, timeout, max_retries,
            )
        )

    return RunnableLambda(answer)
