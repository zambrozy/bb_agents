"""Export the player decisions recorded in MLflow traces as JSONL.

Usage: uv run python scripts/export_decisions.py [--out PATH]
       [--experiment NAME] [--max-traces N]
Reads MLFLOW_TRACKING_URI, or the default data/mlflow.db.
"""

import argparse

from consts.tracing import DEFAULT_EXPORT_PATH
from tracing import configure_store, load_decisions, write_jsonl


def main() -> None:
    """Parse arguments, export the decisions, print a count
    (-> None)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=DEFAULT_EXPORT_PATH)
    parser.add_argument("--experiment", default=None,
                        help="default: BB_AGENTS_EXPERIMENT or bidding")
    parser.add_argument("--max-traces", type=int, default=None,
                        help="newest N auctions only (default: all)")
    args = parser.parse_args()

    uri, experiment = configure_store()
    experiment = args.experiment or experiment
    records = load_decisions(experiment, args.max_traces)
    count = write_jsonl(records, args.out)
    print(f"{count} decisions from {uri} ({experiment}) -> {args.out}")


if __name__ == "__main__":
    main()
