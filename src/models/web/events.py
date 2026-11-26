"""Pydantic models of the events streamed while players bid.

Each event is sent as one server-sent event whose name is its
`type` field and whose data is the event as JSON.
"""

from typing import Literal

from pydantic import BaseModel

from consts.cards import SEAT_NAMES
from models.tracing import AuctionSummary


class ProposalEvent(BaseModel):
    """A player proposed a call; validation follows.

    Attributes:
        seat (SEAT_NAMES): Seat that proposed.
        call (str): Proposed call, e.g. '1NT'.
        reasoning (str): The player's reasoning.
        try_nb (int): Rejected attempts before this one.
    """

    type: Literal["proposal"] = "proposal"
    seat: SEAT_NAMES
    call: str
    reasoning: str
    try_nb: int


class AcceptedEvent(BaseModel):
    """A call was added to the auction.

    Attributes:
        seat (SEAT_NAMES): Seat that made the call.
        call (str): The call, e.g. '1NT'.
        index (int): Position of the call in the auction.
        forced (bool): Pass forced after too many illegal attempts.
    """

    type: Literal["accepted"] = "accepted"
    seat: SEAT_NAMES
    call: str
    index: int
    forced: bool


class RejectedEvent(BaseModel):
    """A proposed call was illegal; the same player tries again.

    Attributes:
        seat (SEAT_NAMES): Seat whose call was rejected.
        call (str): The rejected call.
        try_nb (int): Rejected attempts of this player so far.
    """

    type: Literal["rejected"] = "rejected"
    seat: SEAT_NAMES
    call: str
    try_nb: int


class DoneEvent(AuctionSummary):
    """The auction is over: its calls and the contract played double
    dummy, scored and compared to par (AuctionSummary fields;
    `from_state(state, analysis)` builds it)."""

    type: Literal["done"] = "done"


class ErrorEvent(BaseModel):
    """The auction stopped because of an error (e.g. model timeout).

    Attributes:
        message (str): What went wrong.
    """

    type: Literal["error"] = "error"
    message: str


BidEvent = (
    ProposalEvent | AcceptedEvent | RejectedEvent | DoneEvent
    | ErrorEvent
)
