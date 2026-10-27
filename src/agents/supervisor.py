from typing import Literal

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime

from agents.player import (
    NO_CALLS,
    NO_REASONING,
    REJECTED_PROMPT,
    TURN_PROMPT,
)
from consts import SEAT_TO_PBN, VULNERABILITY_TEXT, Seat
from sampler import DealSampler
from models.bidding import (BiddingState,
                            Context,
                            PlayerReply,
                            BiddingHistory,
                            Call)


def sample_deal(state: BiddingState) -> dict[str, str]:
    """Sample a random deal (BiddingState) -> {"deal": dict[str, str]}.

    The deal maps a seat letter (N, E, S, W) to its hand text.
    """
    sampler = DealSampler()
    deal = sampler.sample_deal()
    deal = sampler.dict_deal_format(deal)

    return {"deal": deal}


def route_bid_turn(state: BiddingState) -> dict | None:
    """Handle the proposed call (BiddingState) -> state update | None.

    No proposal (first turn): no update. Legal proposal: add the call
    and its reasoning, reset retries, pass the turn. Illegal proposal:
    count a retry, or after `max_try_nb` failures force a pass.
    """
    if state.proposed is not None:
        call = validate_proposed_bid(
           state.history,
           state.proposed
        )
        if call is not None:
            return {"history": call,
                    "reasoning_history": [state.proposed],
                    "try_nb": 0,
                    "proposed": None,
                    "player_turn": "next"
            }
        else:
            try_nb = state.try_nb + 1
            if try_nb >= state.max_try_nb:
                call = Call.make_pass()
                forced = PlayerReply(
                    reasoning=f"Forced pass after {state.max_try_nb} invalid replies.",
                    call="P"
                )
                return {
                    "history": call,
                    "reasoning_history": [forced],
                    "try_nb": 0,
                    "proposed": None,
                    "player_turn": "next"
                }

            else:
                return {"try_nb": state.try_nb + 1}


def after_route_bid_turn(
    state: BiddingState
) -> Literal["player_bid", "__end__"]:
    """Pick the node after route_bid_turn (BiddingState) -> str.

    Ends the graph once the auction is over; otherwise the player on
    turn bids (first turn, retry after a rejection, or next player).
    """
    if state.history.is_over:
        return END
    return "player_bid"


def validate_proposed_bid(
    history: BiddingHistory,
    proposed: PlayerReply
) -> (Call | None):
    """Parse and check a proposal (BiddingHistory, PlayerReply)
    -> Call if it is valid and legal, else None."""
    try:
        call = Call.from_str(proposed.call)

        if history.is_legal(call):
            return call
        else:
            return None
         
    except ValueError as e:
        return None

    
def own_reasoning(state: BiddingState, seat: Seat) -> str:
    """Earlier reasoning of `seat` as text (BiddingState, Seat) -> str.

    reasoning_history[i] belongs to the call number i of the history.
    """
    lines = [
        f"- Your call {state.history.calls[i]}: {reply.reasoning}"
        for i, reply in enumerate(state.reasoning_history)
        if state.history.seat_of(i) == seat
    ]
    return "\n".join(lines) or NO_REASONING


def build_turn_prompt(state: BiddingState) -> str:
    """Message for the player on turn (BiddingState) -> str.

    Holds the hand, the auction, the player's own earlier reasoning
    and, after a failed validation, the rejected call with its
    reasoning.
    """
    seat = state.history.next_seat
    prompt = TURN_PROMPT.format(
        dealer=state.history.dealer.name,
        vulnerability=VULNERABILITY_TEXT[state.history.vulnerability],
        hand=state.deal[SEAT_TO_PBN[seat]],
        auction="\n".join(state.history.to_list()) or NO_CALLS,
        reasoning=own_reasoning(state, seat),
    )
    if state.proposed is not None and state.try_nb > 0:
        prompt += REJECTED_PROMPT.format(
            call=state.proposed.call,
            reasoning=state.proposed.reasoning,
        )
    return prompt


def player_bid(
    state: BiddingState,
    runtime: Runtime[Context]
) -> dict[str, PlayerReply]:
    """Ask the player on turn for a call (BiddingState, Runtime)
    -> {"proposed": PlayerReply}."""
    player = runtime.context["players"][state.history.next_seat]
    reply = player.invoke({"turn": build_turn_prompt(state)})

    return {"proposed": reply}


def create_supervisor() -> CompiledStateGraph:
    """Build the bidding graph (-> CompiledStateGraph).

    route_bid_turn validates the proposal and updates the auction,
    player_bid asks the player on turn. The deal is expected in the
    input state; players are passed through the runtime context.
    """
    builder = StateGraph(BiddingState, context_schema=Context)
    builder.add_node("route_bid_turn", route_bid_turn)
    builder.add_node("player_bid", player_bid)
    builder.add_edge(START, "route_bid_turn")
    builder.add_conditional_edges("route_bid_turn", after_route_bid_turn)
    builder.add_edge("player_bid", "route_bid_turn")

    return builder.compile()
