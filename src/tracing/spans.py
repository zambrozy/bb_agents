"""Decorators that trace the bidding with MLflow.

They keep MLflow out of the agent code: the graph node, the auction
stream and the Claude Code call are only decorated. With tracing off
the spans are no-ops and the decorated code runs unchanged.
"""

import functools
import inspect
from collections.abc import Callable, Iterator
from typing import Any

import mlflow
from mlflow.entities import SpanType

from consts.tracing import (
    AUCTION_SPAN,
    DECISION_SPAN,
    PASSED_OUT,
    TAG_CONTRACT,
    TAG_CONVENTION,
    TAG_DEALER,
    TAG_DECLARER,
    TAG_MODEL,
    TAG_VULNERABILITY,
)
from models.bidding import BiddingConfig, BiddingState
from models.tracing import AuctionSummary, BidDecision, BidObservation
from tracing.setup import is_recording, tag_trace

# A graph node: (state, runtime) -> state update.
Node = Callable[[BiddingState, Any], dict]
# stream_bidding: (deal, config, dealer, vulnerability) -> (mode, chunk).
AuctionStream = Callable[..., Iterator[tuple[str, Any]]]


def trace_decision(node: Node) -> Node:
    """Trace a player node as a `bid_decision` span (Node) -> Node.

    The node must return {"proposed": PlayerReply}. The span input is
    the BidObservation of the seat on turn, its output the
    BidDecision; the player's own spans nest inside.
    """

    @functools.wraps(node)
    def wrapper(state: BiddingState, runtime: Any) -> dict:
        """Run the node inside the span (BiddingState, Runtime)
        -> the node's state update."""
        with mlflow.start_span(
            name=DECISION_SPAN, span_type=SpanType.AGENT
        ) as span:
            observation = BidObservation.from_state(state)
            span.set_inputs(observation.model_dump())
            update = node(state, runtime)
            decision = BidDecision.from_reply(
                state.history, update["proposed"]
            )
            span.set_outputs(decision.model_dump())
        return update

    return wrapper


def start_tags(
    config: BiddingConfig, dealer: str, vulnerability: str
) -> dict[str, str]:
    """Tags known before the auction (BiddingConfig, dealer: seat
    name, vulnerability: name) -> dict[str, str]."""
    tags = {TAG_DEALER: dealer, TAG_VULNERABILITY: vulnerability}
    for seat, player in config.players.items():
        tags[TAG_MODEL + seat] = player.model
        tags[TAG_CONVENTION + seat] = player.convention
    return tags


def result_tags(summary: AuctionSummary) -> dict[str, str]:
    """Tags of a finished auction (AuctionSummary)
    -> dict[str, str]."""
    return {
        TAG_CONTRACT: summary.contract or PASSED_OUT,
        TAG_DECLARER: summary.declarer or PASSED_OUT,
    }


def trace_auction(stream: AuctionStream) -> AuctionStream:
    """Trace an auction stream as one `auction` trace
    (AuctionStream) -> AuctionStream.

    The stream must take deal, config, dealer and vulnerability and
    yield (mode, chunk) with "values" chunks holding the state.
    Chunks pass through unchanged. Result tags are set by trace id:
    the stream may be resumed in another context (web SSE), where
    MLflow no longer sees the trace as the current one.
    """
    signature = inspect.signature(stream)

    @functools.wraps(stream)
    def wrapper(*args: Any, **kwargs: Any) -> Iterator[tuple[str, Any]]:
        """Yield the stream's chunks inside the span (same args as
        the stream) -> iterator of (mode, chunk)."""
        bound = signature.bind(*args, **kwargs)
        bound.apply_defaults()
        deal = bound.arguments["deal"]
        config = bound.arguments["config"]
        dealer = bound.arguments["dealer"].name
        vulnerability = bound.arguments["vulnerability"].name

        with mlflow.start_span(
            name=AUCTION_SPAN, span_type=SpanType.CHAIN
        ) as span:
            span.set_inputs({
                "deal": deal.to_dict(),
                "dealer": dealer,
                "vulnerability": vulnerability,
                "players": config.model_dump(mode="json")["players"],
            })
            recording = is_recording(span)
            if recording:
                mlflow.update_current_trace(
                    tags=start_tags(config, dealer, vulnerability)
                )
            last = None
            for mode, chunk in stream(*bound.args, **bound.kwargs):
                if mode == "values":
                    last = chunk
                yield mode, chunk
            summary = AuctionSummary.from_state(
                BiddingState.model_validate(last)
            )
            span.set_outputs(summary.model_dump())
        if recording:
            tag_trace(span.trace_id, result_tags(summary))

    return wrapper


def trace_llm_call(func: Callable) -> Callable:
    """Trace a function as an LLM span with its arguments and result
    (Callable) -> Callable."""
    return mlflow.trace(func, span_type=SpanType.LLM)
