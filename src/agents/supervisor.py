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

    
def player_bid(
    state: BiddingState,
    context: Context
) -> dict[str, str]:
    pass