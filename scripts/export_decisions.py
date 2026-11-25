"""Export the player decisions recorded in MLflow traces as JSONL.

Usage: uv run python scripts/export_decisions.py [--out PATH]
       [--experiment NAME] [--max-traces N] [--tag KEY=VALUE ...]
       [--filter "MLflow filter"]
Reads MLFLOW_TRACKING_URI, or the default data/mlflow.db.

Examples: --tag source=collect --tag batch=collect-20261125-1402
          --filter "tags.contract LIKE '%NT%'"
          --filter "tags.source IS NULL"   (traces before tagging)
"""

import argparse

from consts.tracing import DEFAULT_EXPORT_PATH
from tracing import (
    configure_store,
    load_decisions,
    trace_filter,
    write_jsonl,
)


def parse_tag(text: str) -> tuple[str, str]:
    """Split a KEY=VALUE argument (str) -> (key, value)."""
    key, sep, value = text.partition("=")
    if not sep or not key:
        raise argparse.ArgumentTypeError(f"expected KEY=VALUE: {text!r}")
    return key, value


def main() -> None:
    """Parse arguments, export the decisions, print a count
    (-> None)."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--out", default=DEFAULT_EXPORT_PATH)
    parser.add_argument("--experiment", default=None,
                        help="default: BB_AGENTS_EXPERIMENT or bidding")
    parser.add_argument("--max-traces", type=int, default=None,
                        help="newest N matching auctions (default: all)")
    parser.add_argument("--tag", type=parse_tag, action="append",
                        default=[], metavar="KEY=VALUE",
                        help="only traces with this tag value; "
                             "repeat to require several")
    parser.add_argument("--filter", default=None,
                        help="raw MLflow trace filter, ANDed with --tag "
                             "(no OR in MLflow filters)")
    args = parser.parse_args()

    uri, experiment = configure_store()
    experiment = args.experiment or experiment
    filter_string = trace_filter(dict(args.tag), args.filter)
    records = load_decisions(experiment, args.max_traces, filter_string)
    count = write_jsonl(records, args.out)
    matched = f", filter: {filter_string}" if filter_string else ""
    print(f"{count} decisions from {uri} ({experiment}{matched}) "
          f"-> {args.out}")


if __name__ == "__main__":
    main()
