"""Constants of the web service."""

from pathlib import Path

from consts import DEFAULT_CONFIG_PATH

APP_TITLE = "bb_agents bidding table"

# Project root: src/web/consts.py -> two levels up from src/.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Players config; the environment variable overrides the default.
CONFIG_ENV_VAR = "BB_AGENTS_CONFIG"
DEFAULT_CONFIG_FILE = PROJECT_ROOT / DEFAULT_CONFIG_PATH

# Frontend files and the URL prefix they are served under.
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_URL = "/static"
INDEX_FILE = "index.html"

# Deals kept in memory; the oldest is dropped beyond this.
MAX_STORED_DEALS = 200

# Length of the hex deal ids.
DEAL_ID_LENGTH = 12
