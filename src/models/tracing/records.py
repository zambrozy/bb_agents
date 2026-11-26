"""Pydantic models of what the auction traces record.

A trace holds one auction: the root span takes the deal and returns
an AuctionSummary; each `bid_decision` span takes a BidObservation
and returns a BidDecision. DecisionRecord joins them for export.
"""

from typing import Self

from pydantic import BaseModel

from consts.cards import SEAT_NAMES, VULNERABILITY_NAMES
from models.bidding import (
    BiddingHistory,
    BiddingState,
    ContractResult,
    PlayerReply,
)
from models.sampler import DealAnalysis


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


class AuctionSummary(ContractResult):
    """Result of a finished auction: its calls plus the contract
    played double dummy, scored and compared to par (ContractResult
    fields).

    Attributes:
        auction (list[str]): All calls in order.
    """

    auction: list[str]

    @classmethod
    def from_state(
        cls, state: BiddingState, analysis: DealAnalysis
    ) -> Self:
        """Summary of a finished auction (BiddingState, DealAnalysis
        of its deal and vulnerability) -> AuctionSummary."""
        result = ContractResult.from_history(state.history, analysis)
        return cls(
            auction=[str(call) for call in state.history.calls],
            **result.model_dump(),
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
        source (str | None): Where the auction was played (web,
            play, collect); None for traces without the tag.
        score_ns (int | None): Double-dummy score of the contract,
            NS view; None if not finished or traced before scoring.
        par_ns (int | None): Par score, NS view.
        vs_par (int | None): score_ns - par_ns.
    """

    trace_id: str
    observation: BidObservation
    decision: BidDecision
    model: str | None = None
    convention: str | None = None
    deal: dict[str, str]
    finished: bool
    contract: str | None = None
    source: str | None = None
    score_ns: int | None = None
    par_ns: int | None = None
    vs_par: int | None = None
