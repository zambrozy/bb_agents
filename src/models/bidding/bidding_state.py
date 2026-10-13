from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from typing import TypedDict

from models.bidding import BiddingHistory
from models.bidding import PlayerReply
from consts import Seat


class BiddingState(BaseModel):
    history: BiddingHistory
    proposed: PlayerReply | None = None
    try_nb: int = 0
    max_try_nb: int = 5
    reasoning_history: list[PlayerReply] = []
    deal: dict[str, str]
    player_turn: Seat | None


class Context(TypedDict):
    """Runtime context passed to the graph nodes.

    Attributes:
        players (dict[Seat, CompiledStateGraph]): Player per seat.
    """

    players: dict[Seat, CompiledStateGraph]
