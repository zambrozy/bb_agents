"""Shared test setup: no MLflow traces are written by default.

Tests that check tracing turn it on themselves, with a temporary
store (see test_tracing.py).
"""

import os

import mlflow
import pytest

from agents.player import reset_rate_limiters
from consts.tracing import TRACING_ENV_VAR, TRACING_OFF

os.environ[TRACING_ENV_VAR] = TRACING_OFF
mlflow.tracing.disable()


@pytest.fixture(autouse=True)
def _fresh_rate_limiters():
    """Each test starts without shared rate limiters (-> None)."""
    reset_rate_limiters()
    yield
    reset_rate_limiters()
