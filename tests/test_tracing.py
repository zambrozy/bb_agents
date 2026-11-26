"""Tests for the MLflow tracing of auctions and the JSONL export.

Players are scripted; traces go to a temporary SQLite store.
"""

import json
from pathlib import Path
from unittest.mock import patch

import mlflow
import pytest
from fastapi.testclient import TestClient
from langchain_core.runnables import RunnableLambda

import agents.player as player_module
import agents.run_bidding as run_module
from consts.cards import Seat, Vulnerability
from consts.tracing import (
    AUCTION_SPAN,
    DECISION_SPAN,
    EXPERIMENT_ENV_VAR,
    TRACING_ENV_VAR,
    TRACKING_URI_ENV_VAR,
    TraceSource,
)
from consts.web import CONFIG_ENV_VAR
from models.bidding import (
    BiddingConfig,
    BiddingHistory,
    BiddingState,
    Call,
    PlayerReply,
)
from models.tracing import BidDecision, BidObservation
from sampler import DealSampler
from tracing import (
    load_decisions,
    setup_tracing,
    trace_filter,
    write_jsonl,
)
from web.app import app

DEAL = DealSampler(seed=1).sample_deal()
SEATS = ("NORTH", "EAST", "SOUTH", "WEST")
EXPERIMENT = "test-bidding"
BATCH = "collect-test"
# EAST's 1C is illegal after 1H and is retried as 2C.
SCRIPT = ["1H", "1C", "2C", "P", "P", "P"]


class _ScriptedModel:
    """Stands in for a chat model; replies come from `calls`."""

    def __init__(self, calls: list[str]) -> None:
        self.calls = iter(calls)

    def with_structured_output(self, schema) -> RunnableLambda:
        """Runnable returning the next scripted reply."""
        return RunnableLambda(
            lambda _: PlayerReply(reasoning="why", call=next(self.calls))
        )


def _config() -> BiddingConfig:
    """All seats play model "p:m" with SAYC (-> BiddingConfig)."""
    return BiddingConfig.model_validate({"players": {
        seat: {"model": "p:m", "convention": "SAYC"} for seat in SEATS
    }})


def _history(*calls: str) -> BiddingHistory:
    """Auction dealt by NORTH, nobody vulnerable, with `calls` made
    (*calls: str) -> BiddingHistory."""
    history = BiddingHistory(
        dealer=Seat.NORTH, vulnerability=Vulnerability.NONE
    )
    for text in calls:
        history.add(Call.from_str(text))
    return history


def _auction_traces() -> list:
    """Traces of the test experiment, oldest first (-> list[Trace])."""
    mlflow.flush_trace_async_logging()
    experiment = mlflow.get_experiment_by_name(EXPERIMENT)
    return mlflow.search_traces(
        locations=[experiment.experiment_id],
        order_by=["timestamp_ms ASC"],
        return_type="list",
    )


@pytest.fixture
def traced(tmp_path: Path, monkeypatch) -> Path:
    """Tracing on, into a SQLite store in `tmp_path` (-> tmp_path).

    Turned off again afterwards, as conftest.py leaves it.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(TRACING_ENV_VAR, raising=False)
    monkeypatch.setenv(
        TRACKING_URI_ENV_VAR, f"sqlite:///{tmp_path}/mlflow.db"
    )
    monkeypatch.setenv(EXPERIMENT_ENV_VAR, EXPERIMENT)
    assert setup_tracing(TraceSource.COLLECT, BATCH)
    yield tmp_path
    setup_tracing()  # clears the process tags
    mlflow.langchain.autolog(disable=True)
    mlflow.tracing.disable()


def test_observation_of_seat_on_turn():
    """The observation holds the seat on turn, its PBN hand and the
    auction; a retry also names the rejected call."""
    state = BiddingState(history=_history("1H"), deal=DEAL)

    observation = BidObservation.from_state(state)
    assert observation.seat == "EAST"
    assert observation.dealer == "NORTH"
    assert observation.vulnerability == "NONE"
    assert observation.hand == DEAL.hands[Seat.EAST].pbn_segment()
    assert observation.auction == ["1H"]
    assert observation.rejected_call is None

    retry = state.model_copy(update={
        "proposed": PlayerReply(reasoning="r", call="1C"), "try_nb": 1,
    })
    observation = BidObservation.from_state(retry)
    assert observation.try_nb == 1
    assert observation.rejected_call == "1C"


def test_decision_legality():
    """A call below the last bid is illegal, a higher one legal."""
    history = _history("1H")
    low = PlayerReply(reasoning="r", call="1C")
    high = PlayerReply(reasoning="r", call="2C")
    assert BidDecision.from_reply(history, low).legal is False
    assert BidDecision.from_reply(history, high).legal is True


def test_tracing_off_writes_nothing(tmp_path, monkeypatch):
    """With BB_AGENTS_TRACING=0 an auction leaves no trace store."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(TRACING_ENV_VAR, "0")
    assert setup_tracing() is False
    with patch.object(
        player_module, "init_chat_model",
        return_value=_ScriptedModel(["P"] * 4),
    ):
        run_module.run_bidding(DEAL, _config())
    assert list(tmp_path.iterdir()) == []


def test_auction_trace_spans_and_tags(traced):
    """One auction is one trace: root span with the deal and the
    result, a decision span per attempt, searchable tags."""
    with patch.object(
        player_module, "init_chat_model",
        return_value=_ScriptedModel(SCRIPT),
    ):
        run_module.run_bidding(DEAL, _config())

    [trace] = _auction_traces()
    root = next(s for s in trace.data.spans if s.parent_id is None)
    assert root.name == AUCTION_SPAN
    assert root.inputs["deal"] == DEAL.to_dict()
    assert root.outputs["contract"] == "2C by EAST"

    decisions = trace.search_spans(name=DECISION_SPAN)
    assert len(decisions) == len(SCRIPT)
    legal = [span.outputs["legal"] for span in decisions]
    assert legal.count(False) == 1

    analysis = DealSampler().analyze(DEAL)
    par = analysis.par_ns
    assert root.outputs["par_ns"] == par
    assert root.outputs["vs_par"] == root.outputs["score_ns"] - par

    tags = trace.info.tags
    assert tags["contract"] == "2C by EAST"
    assert tags["declarer"] == "EAST"
    assert tags["score"] == str(root.outputs["score_ns"])
    assert tags["par"] == str(par)
    assert tags["vs_par"] == str(root.outputs["vs_par"])
    assert tags["model.NORTH"] == "p:m"
    assert tags["convention.WEST"] == "SAYC"
    assert tags["source"] == "collect"
    assert tags["batch"] == BATCH


def test_export_decisions_to_jsonl(traced):
    """Every attempt becomes a record; the retry knows the rejected
    call; the JSONL file has one record per line."""
    with patch.object(
        player_module, "init_chat_model",
        return_value=_ScriptedModel(SCRIPT),
    ):
        run_module.run_bidding(DEAL, _config())

    records = load_decisions(EXPERIMENT)
    assert [r.decision.call for r in records] == SCRIPT
    assert [r.observation.seat for r in records] == [
        "NORTH", "EAST", "EAST", "SOUTH", "WEST", "NORTH",
    ]
    rejected, retry = records[1], records[2]
    assert rejected.decision.legal is False
    assert retry.observation.rejected_call == "1C"
    assert all(r.finished and r.contract == "2C by EAST"
               for r in records)
    assert records[0].model == "p:m"
    assert all(r.source == "collect" for r in records)
    par = DealSampler().analyze(DEAL).par_ns
    assert all(r.par_ns == par for r in records)
    assert all(r.vs_par == r.score_ns - par for r in records)

    path = traced / "out" / "decisions.jsonl"
    assert write_jsonl(records, path) == len(SCRIPT)
    lines = path.read_text().splitlines()
    assert json.loads(lines[2])["observation"]["try_nb"] == 1


def test_trace_filter():
    """Tags become backticked equality clauses, ANDed with the raw
    filter; nothing to filter gives None."""
    assert trace_filter({}) is None
    assert trace_filter({"source": "collect", "model.NORTH": "p:m"},
                        "tags.contract LIKE '%NT%'") == (
        "tags.`source` = 'collect' AND tags.`model.NORTH` = 'p:m'"
        " AND tags.contract LIKE '%NT%'"
    )


def test_export_filtered_by_tags(traced):
    """Only the traces matching the filter are exported."""
    for batch in ("b1", "b2"):
        setup_tracing(TraceSource.COLLECT, batch)
        with patch.object(
            player_module, "init_chat_model",
            return_value=_ScriptedModel(SCRIPT),
        ):
            run_module.run_bidding(DEAL, _config())

    assert len(load_decisions(EXPERIMENT)) == 2 * len(SCRIPT)
    only_b2 = trace_filter({"batch": "b2", "model.NORTH": "p:m"})
    records = load_decisions(EXPERIMENT, filter_string=only_b2)
    assert len(records) == len(SCRIPT)
    assert len({r.trace_id for r in records}) == 1
    none = trace_filter({"source": "web"})
    assert load_decisions(EXPERIMENT, filter_string=none) == []


def test_web_stream_trace_gets_result_tags(traced, monkeypatch):
    """Through the SSE endpoint (generator resumed in copied
    contexts) the trace still gets the contract tag."""
    lines = []
    for seat in SEATS:
        lines += [f"[players.{seat}]", 'model = "p:m"',
                  'convention = "SAYC"']
    config = traced / "bidding.toml"
    config.write_text("\n".join(lines))
    monkeypatch.setenv(CONFIG_ENV_VAR, str(config))

    client = TestClient(app)
    deal = client.post("/api/deals", json={"seed": 1}).json()
    with patch.object(
        player_module, "init_chat_model",
        return_value=_ScriptedModel(SCRIPT),
    ):
        response = client.get(f"/api/deals/{deal['id']}/bidding")
    assert "event: done" in response.text

    [trace] = _auction_traces()
    assert trace.info.tags["contract"] == "2C by EAST"
    assert len(trace.search_spans(name=DECISION_SPAN)) == len(SCRIPT)
    done = json.loads(
        response.text.split("event: done\ndata: ")[1].splitlines()[0]
    )
    assert trace.info.tags["vs_par"] == str(done["vs_par"])
