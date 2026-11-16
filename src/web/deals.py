"""Sampling deals for the web service and keeping them in memory."""

import uuid
from collections import OrderedDict
from threading import Lock

from consts import Seat, Vulnerability
from models.web import DealRecord, DealRequest
from sampler import DealSampler
from web.consts import DEAL_ID_LENGTH, MAX_STORED_DEALS

# Endpoints run in a thread pool; DDS calls are serialized to be safe.
_DDS_LOCK = Lock()


def new_deal(request: DealRequest) -> DealRecord:
    """Sample and analyze a deal (DealRequest) -> DealRecord."""
    vulnerability = Vulnerability[request.vulnerability]
    with _DDS_LOCK:
        deal, analysis = DealSampler(request.seed).sample_and_analyze(
            vulnerability
        )
    return DealRecord(
        id=uuid.uuid4().hex[:DEAL_ID_LENGTH],
        deal=deal,
        analysis=analysis,
        dealer=Seat[request.dealer],
        vulnerability=vulnerability,
    )


class DealStore:
    """Thread-safe in-memory store of the latest deals.

    Args:
        capacity (int): Deals kept; the oldest is dropped beyond it.
    """

    def __init__(self, capacity: int = MAX_STORED_DEALS) -> None:
        self._capacity = capacity
        self._deals: OrderedDict[str, DealRecord] = OrderedDict()
        self._lock = Lock()

    def add(self, record: DealRecord) -> None:
        """Keep a deal (DealRecord) -> None."""
        with self._lock:
            self._deals[record.id] = record
            while len(self._deals) > self._capacity:
                self._deals.popitem(last=False)

    def get(self, deal_id: str) -> DealRecord | None:
        """Deal by id, None if unknown or dropped (str)
        -> DealRecord | None."""
        with self._lock:
            return self._deals.get(deal_id)
