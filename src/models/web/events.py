"""Pydantic models of the events streamed while players bid.

Each event is sent as one server-sent event whose name is its
`type` field and whose data is the event as JSON.
"""

from typing import Literal, Self

from pydantic import BaseModel

from consts import BOOK_TRICKS, SEAT_NAMES, STRAIN_TO_CHAR
from models.bidding import BiddingState
from models.sampler import DealAnalysis


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


class DoneEvent(BaseModel):
    """The auction is over.

    Attributes:
        auction (list[str]): All calls in order.
        contract (str | None): e.g. '4H X by NORTH'; None if passed
            out.
        declarer (SEAT_NAMES | None): Declarer; None if passed out.
        strain (str | None): Contract strain label, e.g. 'H'.
        dd_tricks (int | None): Tricks the declarer takes double
            dummy.
        needed (int | None): Tricks the contract needs.
        result (int | None): dd_tricks - needed; >= 0 makes.
    """

    type: Literal["done"] = "done"
    auction: list[str]
    contract: str | None = None
    declarer: SEAT_NAMES | None = None
    strain: str | None = None
    dd_tricks: int | None = None
    needed: int | None = None
    result: int | None = None

    @classmethod
    def from_state(
        cls, state: BiddingState, analysis: DealAnalysis
    ) -> Self:
        """Summarize a finished auction against double dummy
        (BiddingState, DealAnalysis) -> DoneEvent."""
        auction = [str(call) for call in state.history.calls]
        contract = state.history.contract
        if contract is None:
            return cls(auction=auction)
        dd_tricks = analysis.tricks_for(
            contract.strain, contract.declarer
        )
        needed = contract.level + BOOK_TRICKS
        return cls(
            auction=auction,
            contract=str(contract),
            declarer=contract.declarer.name,
            strain=STRAIN_TO_CHAR[contract.strain],
            dd_tricks=dd_tricks,
            needed=needed,
            result=dd_tricks - needed,
        )


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
