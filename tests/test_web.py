"""Tests for the web service: deal endpoints and the bidding stream.

Players are scripted, so no LLM is called.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from langchain_core.runnables import RunnableLambda

import agents.player as player_module
from consts import CARDS_PER_HAND
from models.bidding import PlayerReply
from models.web import DealRequest
from web.app import app
from web.consts import CONFIG_ENV_VAR
from web.deals import DealStore, new_deal

SEATS = ("NORTH", "EAST", "SOUTH", "WEST")


@pytest.fixture
def client(tmp_path: Path, monkeypatch) -> TestClient:
    """Test client using a players config written to `tmp_path`."""
    lines = []
    for seat in SEATS:
        lines += [
            f"[players.{seat}]",
            'model = "p:m"',
            'convention = "SAYC"',
        ]
    path = tmp_path / "bidding.toml"
    path.write_text("\n".join(lines))
    monkeypatch.setenv(CONFIG_ENV_VAR, str(path))
    return TestClient(app)


class _ScriptedModel:
    """Stands in for a chat model; replies come from `calls`."""

    def __init__(self, calls: list[str]) -> None:
        self.calls = iter(calls)

    def with_structured_output(self, schema) -> RunnableLambda:
        """Runnable returning the next scripted reply."""
        return RunnableLambda(
            lambda _: PlayerReply(reasoning="why", call=next(self.calls))
        )


class _FailingModel:
    """Stands in for a chat model whose every request fails."""

    def with_structured_output(self, schema) -> RunnableLambda:
        """Runnable raising like a timed-out request."""
        def fail(_):
            raise TimeoutError("model did not answer")
        return RunnableLambda(fail)


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    """Parse an SSE body (str) -> list of (event name, data dict);
    keep-alive comments are skipped."""
    events = []
    for block in text.strip().split("\n\n"):
        fields = dict(
            line.split(": ", 1)
            for line in block.splitlines()
            if not line.startswith(":")
        )
        if fields:
            events.append((fields["event"], json.loads(fields["data"])))
    return events


def _bid(client: TestClient, model, **deal) -> tuple[dict, list]:
    """Create a deal and stream its auction with `model` players
    (client, model, **DealRequest fields) -> (deal json, events)."""
    created = client.post("/api/deals", json={"seed": 1, **deal}).json()
    with patch.object(
        player_module, "init_chat_model", return_value=model
    ):
        response = client.get(f"/api/deals/{created['id']}/bidding")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "text/event-stream"
    )
    return created, _parse_sse(response.text)


def test_frontend_is_served(client):
    """The page and its script and stylesheet are served."""
    page = client.get("/")
    assert page.status_code == 200
    assert "Bidding table" in page.text
    for name in ("app.js", "style.css"):
        assert client.get(f"/static/{name}").status_code == 200


def test_create_deal_returns_hands_and_analysis(client):
    """A new deal has 13 cards per seat, 40 HCP and a DD table."""
    response = client.post(
        "/api/deals",
        json={"seed": 7, "dealer": "EAST", "vulnerability": "NS"},
    )
    assert response.status_code == 200
    deal = response.json()
    assert deal["dealer"] == "EAST"
    assert deal["vulnerability"] == "NS"
    assert set(deal["hands"]) == set(SEATS)
    for hand in deal["hands"].values():
        assert len("".join(hand["suits"])) == CARDS_PER_HAND
    assert sum(h["hcp"] for h in deal["hands"].values()) == 40
    tricks = deal["analysis"]["tricks"]
    assert set(tricks) == {"S", "H", "D", "C", "NT"}
    assert set(tricks["NT"]) == {"N", "E", "S", "W"}
    assert deal["analysis"]["par_score"]


def test_same_seed_same_deal_new_id(client):
    """A seed reproduces the deal; every deal gets its own id."""
    first = client.post("/api/deals", json={"seed": 3}).json()
    second = client.post("/api/deals", json={"seed": 3}).json()
    assert first["pbn"] == second["pbn"]
    assert first["id"] != second["id"]


def test_create_deal_rejects_bad_input(client):
    """Unknown dealer or vulnerability is a validation error."""
    assert client.post(
        "/api/deals", json={"dealer": "NOBODY"}
    ).status_code == 422
    assert client.post(
        "/api/deals", json={"vulnerability": "ALL"}
    ).status_code == 422


def test_read_deal_and_unknown_ids(client):
    """A stored deal can be read back; unknown ids give 404."""
    created = client.post("/api/deals", json={"seed": 5}).json()
    read = client.get(f"/api/deals/{created['id']}")
    assert read.json() == created
    assert client.get("/api/deals/nope").status_code == 404
    assert client.get("/api/deals/nope/bidding").status_code == 404


def test_config_endpoint(client, monkeypatch, tmp_path):
    """The config lists every seat; a broken file gives 500."""
    players = client.get("/api/config").json()["players"]
    assert set(players) == set(SEATS)
    assert players["NORTH"]["convention"] == "SAYC"
    monkeypatch.setenv(CONFIG_ENV_VAR, str(tmp_path / "missing.toml"))
    assert client.get("/api/config").status_code == 500


def test_store_drops_oldest_deal():
    """Past its capacity the store forgets the oldest deal."""
    store = DealStore(capacity=2)
    records = [new_deal(DealRequest(seed=i)) for i in range(3)]
    for record in records:
        store.add(record)
    assert store.get(records[0].id) is None
    assert store.get(records[2].id) == records[2]


def test_stream_reports_proposals_rejections_and_result(client):
    """A scripted auction streams each step and ends with the
    contract compared to double dummy."""
    deal, events = _bid(
        client, _ScriptedModel(["1H", "1C", "2C", "P", "P", "P"])
    )
    names = [name for name, _ in events]
    assert names == [
        "proposal", "accepted",              # NORTH 1H
        "proposal", "rejected",              # EAST 1C, illegal
        "proposal", "accepted",              # EAST 2C
        "proposal", "accepted",              # SOUTH P
        "proposal", "accepted",              # WEST P
        "proposal", "accepted",              # NORTH P
        "done",
    ]
    assert events[0][1]["seat"] == "NORTH"
    assert events[0][1]["reasoning"] == "why"
    assert events[3][1] == {
        "type": "rejected", "seat": "EAST", "call": "1C", "try_nb": 1,
    }
    assert events[4][1]["try_nb"] == 1
    accepted = events[5][1]
    assert accepted["call"] == "2C" and accepted["index"] == 1
    assert accepted["forced"] is False

    done = events[-1][1]
    assert done["auction"] == ["1H", "2C", "P", "P", "P"]
    assert done["contract"] == "2C by EAST"
    assert done["strain"] == "C"
    assert done["needed"] == 8
    dd = deal["analysis"]["tricks"]["C"]["E"]
    assert done["dd_tricks"] == dd
    assert done["result"] == dd - 8


def test_stream_respects_dealer(client):
    """The dealer from the deal request makes the first call."""
    _, events = _bid(client, _ScriptedModel(["P"] * 4), dealer="WEST")
    assert events[0][1]["seat"] == "WEST"


def test_stream_marks_forced_pass(client):
    """After four illegal replies the pass is flagged as forced."""
    model = _ScriptedModel(["1S"] + ["1C"] * 4 + ["P"] * 3)
    _, events = _bid(client, model)
    forced = [data for name, data in events if name == "accepted"][1]
    assert forced == {
        "type": "accepted", "seat": "EAST", "call": "P",
        "index": 1, "forced": True,
    }
    assert events[-1][1]["contract"] == "1S by NORTH"


def test_stream_passed_out(client):
    """Four passes end with no contract."""
    _, events = _bid(client, _ScriptedModel(["P"] * 4))
    done = events[-1][1]
    assert done["auction"] == ["P"] * 4
    assert done["contract"] is None and done["dd_tricks"] is None


def test_stream_reports_model_failure(client):
    """A failing model ends the stream with an error event."""
    _, events = _bid(client, _FailingModel())
    assert events == [(
        "error",
        {"type": "error",
         "message": "TimeoutError: model did not answer"},
    )]
