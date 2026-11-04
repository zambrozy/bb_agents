"""Play one random auction and print it with the players' reasoning.

Usage: uv run python scripts/play_bidding.py [--config PATH] [--seed N]
"""

import argparse

from agents.run_bidding import stream_bidding
from consts import DEFAULT_CONFIG_PATH
from models.bidding import BiddingConfig, BiddingState
from sampler import DealSampler


def print_update(update: dict, state: BiddingState) -> None:
    """Print one graph step as it happens (update: {node: state
    update}, state: state before the step) -> None."""
    for node, change in update.items():
        if node == "player_bid":
            seat = state.history.next_seat.name
            reply = change["proposed"]
            print(f"\n{seat} proposes {reply.call}: {reply.reasoning}",
                  flush=True)
        elif change and "history" in change:
            print(f"  -> accepted {change['history']}", flush=True)
        elif change:
            print(f"  -> rejected (try {change['try_nb']})", flush=True)


def main() -> None:
    """Parse arguments, run an auction and print it (-> None)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    sampler = DealSampler(args.seed)
    deal = sampler.sample_deal()
    config = BiddingConfig.load(args.config)

    print(deal.format())

    state = None
    for mode, chunk in stream_bidding(deal, config):
        if mode == "values":
            state = BiddingState.model_validate(chunk)
        else:
            print_update(chunk, state)

    print(f"\n{state.history.to_table()}")


if __name__ == "__main__":
    main()
