"""Constants of the MLflow tracing of auctions."""

from enum import StrEnum


class TraceSource(StrEnum):
    """Entry point that played a traced auction (value of the
    `source` tag)."""

    WEB = "web"
    PLAY = "play"
    COLLECT = "collect"


# Environment switch: tracing is on unless this is set to "0".
TRACING_ENV_VAR = "BB_AGENTS_TRACING"
TRACING_OFF = "0"

# Where traces go. MLflow's own variable wins over the default: a
# SQLite file, so no server is needed. Relative to the working
# directory (the project root for `make` targets).
TRACKING_URI_ENV_VAR = "MLFLOW_TRACKING_URI"
SQLITE_PREFIX = "sqlite:///"
DATA_DIR = "data"
DEFAULT_TRACKING_URI = f"{SQLITE_PREFIX}{DATA_DIR}/mlflow.db"
# Trace attachments; without it MLflow creates ./mlruns.
ARTIFACT_DIR = f"{DATA_DIR}/mlartifacts"

# Experiment that groups the auction traces.
EXPERIMENT_ENV_VAR = "BB_AGENTS_EXPERIMENT"
DEFAULT_EXPERIMENT = "bidding"

# Span names: root span of one auction, one player's decision.
AUCTION_SPAN = "auction"
DECISION_SPAN = "bid_decision"

# Trace tags (searchable, e.g. "tags.contract = '4H by NORTH'").
# Per seat model / convention tags get the seat name appended,
# e.g. "model.NORTH".
TAG_DEALER = "dealer"
TAG_VULNERABILITY = "vulnerability"
TAG_MODEL = "model."
TAG_CONVENTION = "convention."
TAG_CONTRACT = "contract"
TAG_DECLARER = "declarer"
# Where the auction was played (a TraceSource value) and, for batch
# runs, the id of the run, e.g. "tags.source = 'collect'".
TAG_SOURCE = "source"
TAG_BATCH = "batch"
# Tag value of a passed-out auction (no contract).
PASSED_OUT = "passed out"

# Exported decisions: one JSON object per line.
DEFAULT_EXPORT_PATH = f"{DATA_DIR}/decisions.jsonl"
