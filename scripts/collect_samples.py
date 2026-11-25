"""Play many random auctions to collect eval samples as MLflow traces.

Each auction (random deal, dealer and vulnerability) is stored as one
trace tagged source=collect and batch=collect-<start time>; turn them
into JSONL afterwards with `make export`.

Usage: uv run python scripts/collect_samples.py [--count N]
       [--seed N] [--config PATH] [--max-failures N]
"""

import argparse
import random
from datetime import datetime

from agents.run_bidding import run_bidding
from consts.agents import DEFAULT_CONFIG_PATH
from consts.cards import Seat, Vulnerability
from consts.tracing import PASSED_OUT, TraceSource
from models.bidding import BiddingConfig
from sampler import DealSampler
from tracing import setup_tracing


def play_one(
    sampler: DealSampler,
    rng: random.Random,
    config: BiddingConfig,
) -> str:
    """Play one random auction (DealSampler, Random, BiddingConfig)
    -> one-line summary (str)."""
    deal = sampler.sample_deal()
    dealer = rng.choice(list(Seat))
    vulnerability = rng.choice(list(Vulnerability))
    state = run_bidding(deal, config, dealer, vulnerability)
    contract = state.history.contract
    result = str(contract) if contract else PASSED_OUT
    return f"dealer {dealer.name}, vul {vulnerability.name}: {result}"


def main() -> None:
    """Parse arguments, play the auctions, print a summary (-> None)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--max-failures", type=int, default=3,
                        help="stop after this many failures in a row")
    args = parser.parse_args()
    batch = f"collect-{datetime.now():%Y%m%d-%H%M%S}"
    setup_tracing(TraceSource.COLLECT, batch)
    print(f"batch {batch}", flush=True)

    config = BiddingConfig.load(args.config)
    sampler = DealSampler(args.seed)
    rng = random.Random(args.seed)

    ended = 0
    failed = 0
    in_a_row = 0
    while ended < args.count and in_a_row < args.max_failures:
        try:
            summary = play_one(sampler, rng, config)
            ended += 1
            in_a_row = 0
        except Exception as error:  # keep collecting on model errors
            failed += 1
            in_a_row += 1
            summary = f"failed: {error!r}"
        print(f"[{ended}/{args.count}] {summary}", flush=True)

    if in_a_row >= args.max_failures:
        print(f"\nstopped after {in_a_row} failures in a row")
    print(f"\n{ended} auctions collected, {ended + failed} played, "
          f"{failed} failed")


if __name__ == "__main__":
    main()
