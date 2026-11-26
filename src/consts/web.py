"""Constants of the web service."""

from pathlib import Path

from consts.agents import DEFAULT_CONFIG_PATH

APP_TITLE = "bb_agents bidding table"

# Source and project roots: src/consts/web.py -> src/ -> project root.
SRC_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SRC_DIR.parent

# Players config; the environment variable overrides the default.
CONFIG_ENV_VAR = "BB_AGENTS_CONFIG"
DEFAULT_CONFIG_FILE = PROJECT_ROOT / DEFAULT_CONFIG_PATH

# Frontend files and the URL prefix they are served under.
STATIC_DIR = SRC_DIR / "web" / "static"
STATIC_URL = "/static"
INDEX_FILE = "index.html"
# Frontend responses: the browser must revalidate (ETag) before
# reusing a cached copy, so edited files show on a plain reload.
CACHE_CONTROL_HEADER = "Cache-Control"
NO_CACHE = "no-cache"

# Deals kept in memory; the oldest is dropped beyond this.
MAX_STORED_DEALS = 200

# Length of the hex deal ids.
DEAL_ID_LENGTH = 12
