"""Pydantic models of what the auction traces record.

A trace holds one auction: the root span takes the deal and returns
an AuctionSummary; each `bid_decision` span takes a BidObservation
and returns a BidDecision. DecisionRecord joins them for export.
"""

from typing import Self

from pydantic import BaseModel

from consts.cards import SEAT_NAMES, VULNERABILITY_NAMES
from models.bidding import BiddingHistory, BiddingState, PlayerReply


class BidObservation(BaseModel):
    """What the player on turn knows when it chooses a call.

    Attributes:
        seat (SEAT_NAMES): Seat on turn.
        dealer (SEAT_NAMES): Dealer of the deal.
        vulnerability (VULNERABILITY_NAMES): Vulnerability.
        hand (str): Own hand in PBN, spades first, e.g.
            'AKQ.T98.J2.5432'.
        auction (list[str]): Calls so far in order, e.g.
            ['P', '1H'].
        try_nb (int): Rejected attempts before this one.
        rejected_call (str | None): Last rejected call on a retry,
            else None.
    """

    seat: SEAT_NAMES
    dealer: SEAT_NAMES
    vulnerability: VULNERABILITY_NAMES
    hand: str
    auction: list[str]
    try_nb: int = 0
    rejected_call: str | None = None

    @classmethod
    def from_state(cls, state: BiddingState) -> Self:
        """Observation of the seat on turn (BiddingState)
        -> BidObservation."""
        history = state.history
        seat = history.next_seat
        retry = state.proposed is not None and state.try_nb > 0
        return cls(
            seat=seat.name,
            dealer=history.dealer.name,
            vulnerability=history.vulnerability.name,
            hand=state.deal.hands[seat].pbn_segment(),
            auction=[str(call) for call in history.calls],
            try_nb=state.try_nb,
            rejected_call=state.proposed.call if retry else None,
        )


class BidDecision(BaseModel):
    """The player's answer to a BidObservation.

    Attributes:
        call (str): Proposed call, e.g. '1NT'.
        reasoning (str): The player's reasoning.
        legal (bool): Whether the call is legal in the auction.
    """

    call: str
    reasoning: str
    legal: bool

    @classmethod
    def from_reply(
        cls, history: BiddingHistory, reply: PlayerReply
    ) -> Self:
        """Decision of a reply in an auction (BiddingHistory,
        PlayerReply) -> BidDecision; legal if the call parses and
        is allowed after `history`."""
        try:
            legal = history.is_legal(reply.to_call())
        except ValueError:
            legal = False
        return cls(
            call=reply.call, reasoning=reply.reasoning, legal=legal
        )


class AuctionSummary(BaseModel):
    """Result of a finished auction.

    Attributes:
        auction (list[str]): All calls in order.
        contract (str | None): e.g. '4H X by NORTH'; None if passed
            out.
        declarer (SEAT_NAMES | None): Declarer; None if passed out.
    """

    auction: list[str]
    contract: str | None = None
    declarer: SEAT_NAMES | None = None

    @classmethod
    def from_state(cls, state: BiddingState) -> Self:
        """Summary of a finished auction (BiddingState)
        -> AuctionSummary."""
        contract = state.history.contract
        return cls(
            auction=[str(call) for call in state.history.calls],
            contract=None if contract is None else str(contract),
            declarer=None if contract is None else contract.declarer.name,
        )


class DecisionRecord(BaseModel):
    """One player decision, exported from a trace.

    Attributes:
        trace_id (str): Trace of the auction.
        observation (BidObservation): What the player saw.
        decision (BidDecision): What it answered.
        model (str | None): Model of the seat, from the trace tags.
        convention (str | None): Convention of the seat.
        deal (dict[str, str]): All hands, seat letter -> readable
            hand (Deal.to_dict form).
        finished (bool): Whether the auction reached its end (not
            stopped or failed).
        contract (str | None): Final contract; None if passed out or
            not finished.
    """

    trace_id: str
    observation: BidObservation
    decision: BidDecision
    model: str | None = None
    convention: str | None = None
    deal: dict[str, str]
    finished: bool
    contract: str | None = None
