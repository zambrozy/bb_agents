"""Constants of the bidding agents: model requests and players config."""

# Model request limits: seconds to wait for a reply, retries after a
# failed request.
DEFAULT_TIMEOUT = 60.0
DEFAULT_MAX_RETRIES = 1

# Claude Code players: CLI binary and the model-string prefix that
# selects it, e.g. "claude_code:sonnet".
CLAUDE_BIN = "claude"
CLAUDE_CODE_PREFIX = "claude_code:"

# Default location of the players config, relative to the project root.
DEFAULT_CONFIG_PATH = "config/bidding.toml"
