"""Run one auction with players built from a config."""

from collections.abc import Iterator
from typing import Any

from langchain_core.runnables import Runnable

from agents.player import create_player
from agents.supervisor import create_supervisor
from consts import Seat, Vulnerability
from models.bidding import BiddingConfig, BiddingHistory, BiddingState
from models.cards import Deal
from tracing import trace_auction


def create_players(
    config: BiddingConfig
) -> dict[Seat, Runnable]:
    """Build a player per seat (BiddingConfig)
    -> dict[Seat, Runnable]."""
    return {
        Seat[name]: create_player(
            player.model,
            name,
            player.convention,
            player.timeout,
            player.max_retries,
        )
        for name, player in config.players.items()
    }


def initial_state(
    deal: Deal,
    dealer: Seat,
    vulnerability: Vulnerability,
) -> BiddingState:
    """Empty auction for a deal (Deal, dealer: Seat,
    vulnerability: Vulnerability) -> BiddingState."""
    return BiddingState(
        history=BiddingHistory(
            dealer=dealer, vulnerability=vulnerability
        ),
        deal=deal,
    )


def run_bidding(
    deal: Deal,
    config: BiddingConfig,
    dealer: Seat = Seat.NORTH,
    vulnerability: Vulnerability = Vulnerability.NONE,
) -> BiddingState:
    """Play a whole auction (Deal, BiddingConfig, dealer: Seat,
    vulnerability: Vulnerability) -> final BiddingState.

    Consumes stream_bidding, so it is traced the same way.
    """
    result = None
    for mode, chunk in stream_bidding(
        deal, config, dealer, vulnerability
    ):
        if mode == "values":
            result = chunk

    return BiddingState.model_validate(result)


@trace_auction
def stream_bidding(
    deal: Deal,
    config: BiddingConfig,
    dealer: Seat = Seat.NORTH,
    vulnerability: Vulnerability = Vulnerability.NONE,
) -> Iterator[tuple[str, Any]]:
    """Play an auction step by step (same args as run_bidding)
    -> iterator of (mode, chunk).

    mode "updates": chunk is {node name: state update}.
    mode "values": chunk is the full state after a step; the last
    one is the final state. Traced as one `auction` trace.
    """
    yield from create_supervisor().stream(
        initial_state(deal, dealer, vulnerability),
        context={"players": create_players(config)},
        stream_mode=["updates", "values"],
    )
