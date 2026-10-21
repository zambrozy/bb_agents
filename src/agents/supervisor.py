from langgraph.runtime import Runtime

from agents.player import NO_REASONING, REJECTED_PROMPT, TURN_PROMPT
from consts import SEAT_TO_PBN, Seat
from sampler import DealSampler
from models.bidding import (BiddingState,
                            Context,
                            PlayerReply,
                            BiddingHistory,
                            Call)


def sample_deal(state: BiddingState) -> dict[str, str]:
    sampler = DealSampler()
    deal = sampler.sample_deal()
    deal = sampler.dict_deal_format(deal)

    return {"deal": deal}


def route_bid_turn(state: BiddingState) -> dict:
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
                    "reasoning_history": forced,
                    "try_nb": 0,
                    "proposed": None,
                    "player_turn": "next"
                }

            else:
                return {"try_nb": state.try_nb + 1}


def validate_proposed_bid(
    history: BiddingHistory,
    proposed: PlayerReply
) -> (Call | None):
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
        seat=seat.name,
        hand=state.deal[SEAT_TO_PBN[seat]],
        auction=state.history.to_table(),
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
    result = player.invoke(
        {"messages": [
            {"role": "user", "content": build_turn_prompt(state)}
        ]}
    )
    return {"proposed": result["structured_response"]}
