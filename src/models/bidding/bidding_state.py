from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from operator import add
from typing import TypedDict, Annotated
from copy import copy

from models.bidding import BiddingHistory, PlayerReply, Call
from consts import Seat


def update_history(
        left: BiddingHistory,
        right: Call) -> BiddingHistory:
    """Reducer: history with `right` appended
    (BiddingHistory, Call) -> BiddingHistory (new copy)."""

    left_copy = left.model_copy(deep=True)
    left_copy.calls.append(right)

    return left_copy


def update_player(
        left: Seat,
        right: str
) -> Seat:
    """Reducer: the seat after `left`; `right` is ignored
    (Seat, str) -> Seat."""

    next_seat = (left + 1) % len(Seat)

    return Seat(next_seat)


class BiddingState(BaseModel):
    """State of the bidding graph.

    Attributes:
        history (BiddingHistory): Auction so far; updated with a Call.
        proposed (PlayerReply | None): Reply awaiting validation.
        try_nb (int): Invalid replies of the current player.
        max_try_nb (int): Invalid replies before a forced pass.
        reasoning_history (list[PlayerReply]): Accepted replies, one
            per call in `history`.
        deal (dict[str, str]): Seat letter -> hand text.
        player_turn (Seat): Seat on turn; advances on update.
    """

    history: Annotated[BiddingHistory, update_history]
    proposed: PlayerReply | None = None
    try_nb: int = 0
    max_try_nb: int = 4
    reasoning_history: Annotated[list[PlayerReply], add] = []
    deal: dict[str, str]
    player_turn: Annotated[Seat, update_player]


class Context(TypedDict):
    """Runtime context passed to the graph nodes.

    Attributes:
        players (dict[Seat, CompiledStateGraph]): Player per seat.
    """

    players: dict[Seat, CompiledStateGraph]
    
    
