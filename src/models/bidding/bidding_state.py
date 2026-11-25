from langchain_core.runnables import Runnable
from pydantic import BaseModel

from operator import add
from typing import TypedDict, Annotated

from models.bidding import BiddingHistory, PlayerReply, Call
from models.cards import Deal
from consts.cards import Seat


def update_history(
        left: BiddingHistory,
        right: Call) -> BiddingHistory:
    """Reducer: history with `right` appended
    (BiddingHistory, Call) -> BiddingHistory (new copy)."""

    left_copy = left.model_copy(deep=True)
    left_copy.calls.append(right)

    return left_copy


class BiddingState(BaseModel):
    """State of the bidding graph.

    Attributes:
        history (BiddingHistory): Auction so far; updated with a Call.
        proposed (PlayerReply | None): Reply awaiting validation.
        try_nb (int): Invalid replies of the current player.
        max_try_nb (int): Invalid replies before a forced pass.
        reasoning_history (list[PlayerReply]): Accepted replies, one
            per call in `history`.
        deal (Deal): The hands being bid. The seat on turn is
            `history.next_seat`.
    """

    history: Annotated[BiddingHistory, update_history]
    proposed: PlayerReply | None = None
    try_nb: int = 0
    max_try_nb: int = 4
    reasoning_history: Annotated[list[PlayerReply], add] = []
    deal: Deal

    def reasoning_of(self, seat: Seat) -> list[tuple[Call, PlayerReply]]:
        """Accepted calls of `seat` with their replies, in order
        (Seat) -> list[tuple[Call, PlayerReply]].

        reasoning_history[i] belongs to call number i of the history.
        """
        return [
            (self.history.calls[i], reply)
            for i, reply in enumerate(self.reasoning_history)
            if self.history.seat_of(i) == seat
        ]


class Context(TypedDict):
    """Runtime context passed to the graph nodes.

    Attributes:
        players (dict[Seat, Runnable]): Player per seat; takes
            {"turn": str} and returns a PlayerReply.
    """

    players: dict[Seat, Runnable]
    
    
