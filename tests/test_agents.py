"""Tests for the bidding graph, prompts and config (no LLM calls)."""

from unittest.mock import patch

import pytest
from langchain_core.runnables import RunnableLambda
from langgraph.graph import END

import agents.player as player_module
import agents.run_bidding as run_module
from agents.supervisor import (
    after_route_bid_turn,
    build_turn_prompt,
    own_reasoning,
    route_bid_turn,
)
from consts.cards import Seat, Vulnerability
from models.bidding import (
    BiddingConfig,
    BiddingHistory,
    BiddingState,
    Call,
    PlayerReply,
)
from sampler import DealSampler

DEAL = DealSampler(seed=1).sample_deal()


def _state(
    dealer: Seat = Seat.NORTH,
    calls: list[str] = (),
    vulnerability: Vulnerability = Vulnerability.NONE,
    **fields,
) -> BiddingState:
    """State with `calls` already made."""
    history = BiddingHistory(dealer=dealer, vulnerability=vulnerability)
    for text in calls:
        history.add(Call.from_str(text))
    return BiddingState(
        history=history, deal=DEAL, **fields,
    )


def _reply(call: str, reasoning: str = "because") -> PlayerReply:
    """Player reply for `call`."""
    return PlayerReply(reasoning=reasoning, call=call)


def _config(**conventions: str) -> dict:
    """Config dict; seats default to SAYC unless overridden."""
    return {"players": {
        seat: {
            "model": "p:m",
            "convention": conventions.get(seat, "SAYC"),
        }
        for seat in ("NORTH", "EAST", "SOUTH", "WEST")
    }}


def test_seat_partner_and_opponents():
    """Partner sits across; opponents are the other partnership."""
    assert Seat.NORTH.partner == Seat.SOUTH
    assert Seat.WEST.partner == Seat.EAST
    assert Seat.NORTH.opponents == (Seat.EAST, Seat.WEST)
    assert Seat.EAST.opponents == (Seat.NORTH, Seat.SOUTH)
    assert Seat.EAST.is_same_side(Seat.WEST)
    assert not Seat.EAST.is_same_side(Seat.SOUTH)


def test_turn_prompt_has_deal_facts_and_auction_list():
    """Dealer, vulnerability, hand and calls appear; no seat line."""
    state = _state(
        dealer=Seat.EAST,
        calls=["1S", "X"],
        vulnerability=Vulnerability.NS,
    )
    prompt = build_turn_prompt(state)
    assert "Dealer: EAST" in prompt
    assert "Vulnerability: North-South vulnerable" in prompt
    # West is next after East, South
    assert DEAL.hands[Seat.WEST].to_str() in prompt
    assert "EAST: 1S\nSOUTH: X" in prompt
    assert "Your seat" not in prompt
    assert "REJECTED" not in prompt


def test_turn_prompt_with_no_calls():
    """An empty auction is stated explicitly."""
    assert "(no calls yet)" in build_turn_prompt(_state())


def test_turn_prompt_shows_own_reasoning_only():
    """Reasoning of other seats is not shown to the player."""
    state = _state(
        calls=["1H", "P", "P", "P"],
        reasoning_history=[
            _reply("1H", "north opens"), _reply("P", "east passes"),
            _reply("P", "south passes"), _reply("P", "west passes"),
        ],
    )
    text = own_reasoning(state, Seat.NORTH)
    assert "north opens" in text
    assert "east passes" not in text
    assert own_reasoning(_state(), Seat.NORTH) == "(none yet)"


def test_turn_prompt_shows_rejected_attempt():
    """After a failed validation the call and reasoning come back."""
    state = _state(
        calls=["1H"],
        proposed=_reply("1C", "wrong level"),
        try_nb=1,
    )
    prompt = build_turn_prompt(state)
    assert "REJECTED" in prompt
    assert "Rejected call: 1C" in prompt
    assert "wrong level" in prompt


def test_route_without_proposal_changes_nothing():
    """First turn: no proposal, so no update."""
    assert route_bid_turn(_state()) is None


def test_route_accepts_legal_call():
    """A legal proposal is applied and the retry counter reset."""
    reply = _reply("1H")
    update = route_bid_turn(_state(proposed=reply, try_nb=2))
    assert update["history"] == Call.from_str("1H")
    assert update["reasoning_history"] == [reply]
    assert update["try_nb"] == 0
    assert update["proposed"] is None


def test_route_counts_illegal_call_as_retry():
    """An illegal proposal only bumps the retry counter."""
    state = _state(calls=["1H"], proposed=_reply("1C"), try_nb=0)
    assert route_bid_turn(state) == {"try_nb": 1}


def test_route_forces_pass_after_max_tries():
    """After max_try_nb illegal replies the player passes."""
    state = _state(
        calls=["1H"], proposed=_reply("1C"), try_nb=3, max_try_nb=4
    )
    update = route_bid_turn(state)
    assert update["history"] == Call.make_pass()
    assert update["reasoning_history"][0].call == "P"
    assert update["try_nb"] == 0


def test_graph_ends_when_auction_is_over():
    """After the last pass the graph ends, otherwise a player bids."""
    assert after_route_bid_turn(_state()) == "player_bid"
    over = _state(calls=["P", "P", "P", "P"])
    assert after_route_bid_turn(over) == END


def test_config_requires_all_seats():
    """A config with a missing seat is rejected."""
    data = _config()
    del data["players"]["WEST"]
    with pytest.raises(ValueError, match="missing players"):
        BiddingConfig.model_validate(data)


def test_config_partners_share_a_convention():
    """Partners must agree; the two sides may differ."""
    with pytest.raises(ValueError, match="one convention"):
        BiddingConfig.model_validate(_config(EAST="2/1 Force Game"))
    both = _config(EAST="2/1 Force Game", WEST="2/1 Force Game")
    assert BiddingConfig.model_validate(both)


def test_config_rejects_unknown_convention():
    """A typo in the convention is caught on load."""
    with pytest.raises(ValueError):
        BiddingConfig.model_validate(_config(NORTH="SYAC", SOUTH="SYAC"))


def test_config_requests_per_minute_is_optional_and_positive():
    """No limit by default; a limit must be above zero."""
    config = BiddingConfig.model_validate(_config())
    assert config.players["NORTH"].requests_per_minute is None
    data = _config()
    data["players"]["NORTH"]["requests_per_minute"] = 0
    with pytest.raises(ValueError):
        BiddingConfig.model_validate(data)


def _init_kwargs(model_name: str, **options) -> dict:
    """Keyword arguments create_player passes to init_chat_model."""
    with patch.object(player_module, "init_chat_model") as init:
        player_module.create_player(model_name, "NORTH", "SAYC", **options)
    return init.call_args.kwargs


def test_seats_of_one_model_share_a_rate_limiter():
    """Same model: one limiter (first limit wins); other model or no
    limit: its own limiter or none."""
    first = _init_kwargs("p:m", requests_per_minute=15)["rate_limiter"]
    second = _init_kwargs("p:m", requests_per_minute=30)["rate_limiter"]
    other = _init_kwargs("p:other", requests_per_minute=15)["rate_limiter"]
    assert first is second
    assert first.requests_per_second == 15 / 60
    assert other is not first
    assert _init_kwargs("p:m")["rate_limiter"] is None


def test_google_genai_retries_count_the_first_attempt():
    """Google counts attempts, so it gets one more than the retries;
    other providers get the retries as they are."""
    google = _init_kwargs("google_genai:gemini", max_retries=3)
    assert google["max_retries"] == 4
    assert _init_kwargs("p:m", max_retries=3)["max_retries"] == 3


class _ScriptedModel:
    """Stands in for a chat model; replies come from `calls`."""

    def __init__(self, calls: list[str]) -> None:
        self.calls = iter(calls)
        self.seen = []

    def with_structured_output(self, schema):
        def answer(prompt_value):
            self.seen.append(prompt_value.to_messages())
            return _reply(next(self.calls))
        return RunnableLambda(answer)


def test_full_auction_with_retry_and_prompts():
    """A scripted auction ends correctly, a rejected call is retried
    and each player gets its own system prompt."""
    model = _ScriptedModel(["1H", "1C", "2C", "P", "P", "P"])
    config = BiddingConfig.model_validate(_config())
    with patch.object(
        player_module, "init_chat_model", return_value=model
    ):
        state = run_module.run_bidding(DEAL, config)

    assert state.history.to_list() == [
        "NORTH: 1H", "EAST: 2C", "SOUTH: P", "WEST: P", "NORTH: P",
    ]
    assert len(state.reasoning_history) == 5
    # call 2 was East's rejected 1C, call 3 its retry
    retry_human = model.seen[2][1].content
    assert "Rejected call: 1C" in retry_human
    system = model.seen[1][0].content
    assert "seat EAST" in system and "partner is WEST" in system


def test_stream_ends_with_the_final_state():
    """The last `values` chunk of the stream is the final state."""
    model = _ScriptedModel(["P"] * 4)
    config = BiddingConfig.model_validate(_config())
    with patch.object(
        player_module, "init_chat_model", return_value=model
    ):
        chunks = list(run_module.stream_bidding(DEAL, config))

    modes = {mode for mode, _ in chunks}
    assert modes == {"updates", "values"}
    values = [chunk for mode, chunk in chunks if mode == "values"]
    assert BiddingState.model_validate(values[-1]).history.is_over
