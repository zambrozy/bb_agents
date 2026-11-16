"""Turn the bidding graph stream into events for the UI."""

import logging
from collections.abc import Iterator

from agents.run_bidding import stream_bidding
from models.bidding import BiddingConfig, BiddingState
from models.web import (
    AcceptedEvent,
    BidEvent,
    DealRecord,
    DoneEvent,
    ErrorEvent,
    ProposalEvent,
    RejectedEvent,
)

logger = logging.getLogger(__name__)


def update_events(
    update: dict, state: BiddingState | None
) -> Iterator[BidEvent]:
    """Events of one graph step (update: {node: state update},
    state: state before the step) -> iterator of BidEvent.

    The first step (no proposal yet) yields nothing.
    """
    for node, change in update.items():
        if not change or state is None:
            continue
        seat = state.history.next_seat.name
        if node == "player_bid":
            reply = change["proposed"]
            yield ProposalEvent(
                seat=seat,
                call=reply.call,
                reasoning=reply.reasoning,
                try_nb=state.try_nb,
            )
        elif "history" in change:
            reply = change["reasoning_history"][0]
            yield AcceptedEvent(
                seat=seat,
                call=str(change["history"]),
                index=len(state.history.calls),
                forced=reply != state.proposed,
            )
        else:
            yield RejectedEvent(
                seat=seat,
                call=state.proposed.call,
                try_nb=change["try_nb"],
            )


def bidding_events(
    record: DealRecord, config: BiddingConfig
) -> Iterator[BidEvent]:
    """Play an auction of a stored deal (DealRecord, BiddingConfig)
    -> iterator of BidEvent, ending with a DoneEvent or an
    ErrorEvent."""
    state = None
    try:
        for mode, chunk in stream_bidding(
            record.deal, config, record.dealer, record.vulnerability
        ):
            if mode == "values":
                state = BiddingState.model_validate(chunk)
            else:
                yield from update_events(chunk, state)
    except Exception as error:
        # Model or network failure: report it instead of a cut stream.
        logger.exception("auction of deal %s failed", record.id)
        yield ErrorEvent(message=f"{type(error).__name__}: {error}")
        return
    yield DoneEvent.from_state(state, record.analysis)
