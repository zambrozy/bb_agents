"""FastAPI app: deal endpoints, live bidding stream and the frontend.

Run from the project root: uv run uvicorn web.app:app --reload
"""

import os
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.sse import EventSourceResponse, ServerSentEvent
from fastapi.staticfiles import StaticFiles

from consts.web import (
    APP_TITLE,
    CONFIG_ENV_VAR,
    DEFAULT_CONFIG_FILE,
    INDEX_FILE,
    STATIC_DIR,
    STATIC_URL,
)
from models.bidding import BiddingConfig
from models.web import DealRecord, DealRequest, DealView
from web.bidding import bidding_events
from web.deals import DealStore, new_deal
from tracing import setup_tracing


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Server start-up: configure MLflow tracing (FastAPI)
    -> async iterator yielding once while the server runs."""
    setup_tracing()
    yield


app = FastAPI(title=APP_TITLE, lifespan=lifespan)
app.mount(STATIC_URL, StaticFiles(directory=STATIC_DIR), name="static")
store = DealStore()


def load_config() -> BiddingConfig:
    """Read the players config on each request, so edits apply
    without a restart (-> BiddingConfig).

    Raises:
        HTTPException: 500 if the file is missing or invalid.
    """
    path = os.environ.get(CONFIG_ENV_VAR, DEFAULT_CONFIG_FILE)
    try:
        return BiddingConfig.load(path)
    except (OSError, ValueError) as error:
        raise HTTPException(500, f"bad players config {path}: {error}")


def get_record(deal_id: str) -> DealRecord:
    """Stored deal by id (str) -> DealRecord.

    Raises:
        HTTPException: 404 if the deal is unknown or was dropped.
    """
    record = store.get(deal_id)
    if record is None:
        raise HTTPException(404, f"unknown deal {deal_id}")
    return record


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    """Serve the frontend page (-> FileResponse)."""
    return FileResponse(STATIC_DIR / INDEX_FILE)


@app.get("/api/config")
def get_config(
    config: Annotated[BiddingConfig, Depends(load_config)],
) -> BiddingConfig:
    """Players config: model and convention per seat
    (-> BiddingConfig)."""
    return config


@app.post("/api/deals")
def create_deal(request: DealRequest) -> DealView:
    """Sample, analyze and store a new deal (DealRequest)
    -> DealView."""
    record = new_deal(request)
    store.add(record)
    return record.to_view()


@app.get("/api/deals/{deal_id}")
def read_deal(
    record: Annotated[DealRecord, Depends(get_record)],
) -> DealView:
    """A stored deal (deal_id: str) -> DealView."""
    return record.to_view()


@app.get(
    "/api/deals/{deal_id}/bidding",
    response_class=EventSourceResponse,
)
def stream_deal_bidding(
    record: Annotated[DealRecord, Depends(get_record)],
    config: Annotated[BiddingConfig, Depends(load_config)],
) -> Iterator[ServerSentEvent]:
    """Play an auction and stream it as server-sent events
    (deal_id: str) -> event stream.

    Event names: proposal, accepted, rejected, done, error (see
    models.web.events). The stream ends after done or error. Runs in
    a thread pool; closing the connection stops the auction after
    the current model call.
    """
    for event in bidding_events(record, config):
        yield ServerSentEvent(event=event.type, data=event)
