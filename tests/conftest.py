"""Shared test setup: no MLflow traces are written by default.

Tests that check tracing turn it on themselves, with a temporary
store (see test_tracing.py).
"""

import os

import mlflow

from consts.tracing import TRACING_ENV_VAR, TRACING_OFF

os.environ[TRACING_ENV_VAR] = TRACING_OFF
mlflow.tracing.disable()
