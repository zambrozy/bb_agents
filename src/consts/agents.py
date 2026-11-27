"""Constants of the bidding agents: model requests and players config."""

# Model request limits: seconds to wait for a reply, retries after a
# failed request.
DEFAULT_TIMEOUT = 60.0
DEFAULT_MAX_RETRIES = 3

# Google GenAI models: their `max_retries` counts all attempts, the
# first request included, so it gets one more than the configured
# retries.
GOOGLE_GENAI_PREFIX = "google_genai:"

# Rate limiter: calls go out evenly spaced, no bursts.
RATE_LIMIT_BUCKET_SIZE = 1
SECONDS_PER_MINUTE = 60

# Claude Code players: CLI binary and the model-string prefix that
# selects it, e.g. "claude_code:sonnet".
CLAUDE_BIN = "claude"
CLAUDE_CODE_PREFIX = "claude_code:"

# Default location of the players config, relative to the project root.
DEFAULT_CONFIG_PATH = "config/bidding.toml"
