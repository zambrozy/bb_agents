"""Turn MLflow tracing on or off and write trace tags."""

import logging
import os
from pathlib import Path

import mlflow
from mlflow.entities import NoOpSpan
from mlflow.entities.span import Span

from tracing.consts import (
    ARTIFACT_DIR,
    DEFAULT_EXPERIMENT,
    DEFAULT_TRACKING_URI,
    EXPERIMENT_ENV_VAR,
    SQLITE_PREFIX,
    TRACKING_URI_ENV_VAR,
    TRACING_ENV_VAR,
    TRACING_OFF,
)

logger = logging.getLogger(__name__)


def tracing_requested() -> bool:
    """Whether tracing is on: BB_AGENTS_TRACING is not "0" (-> bool)."""
    return os.environ.get(TRACING_ENV_VAR) != TRACING_OFF


def setup_tracing() -> bool:
    """Configure MLflow tracing for the auctions (-> bool: on/off).

    Off (BB_AGENTS_TRACING=0): spans become no-ops. On: traces go to
    the store of configure_store and LangChain / LangGraph calls are
    traced automatically.
    """
    if not tracing_requested():
        mlflow.tracing.disable()
        return False

    uri, name = configure_store()
    mlflow.langchain.autolog()
    mlflow.tracing.enable()
    logger.info("MLflow tracing to %s, experiment %r", uri, name)
    return True


def configure_store() -> tuple[str, str]:
    """Point MLflow at the trace store (-> (tracking URI,
    experiment name)).

    URI: MLFLOW_TRACKING_URI, or the SQLite file data/mlflow.db.
    Experiment: BB_AGENTS_EXPERIMENT, default "bidding"; created on
    first use, with SQLite artifacts kept in data/mlartifacts.
    """
    uri = os.environ.get(TRACKING_URI_ENV_VAR, DEFAULT_TRACKING_URI)
    is_sqlite = uri.startswith(SQLITE_PREFIX)
    if is_sqlite:
        db_path = Path(uri.removeprefix(SQLITE_PREFIX))
        db_path.parent.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(uri)

    name = os.environ.get(EXPERIMENT_ENV_VAR, DEFAULT_EXPERIMENT)
    if is_sqlite and mlflow.get_experiment_by_name(name) is None:
        # Keep artifacts next to the database instead of ./mlruns.
        artifacts = Path(ARTIFACT_DIR).resolve().as_uri()
        mlflow.create_experiment(name, artifact_location=artifacts)
    mlflow.set_experiment(name)
    return uri, name


def is_recording(span: Span) -> bool:
    """Whether a span is really recorded, not the no-op span of
    disabled tracing (Span) -> bool."""
    return not isinstance(span, NoOpSpan)


def tag_trace(trace_id: str, tags: dict[str, str]) -> None:
    """Set tags on a trace by its id (trace_id: str,
    tags: dict[str, str]) -> None.

    Unlike mlflow.update_current_trace it does not need the trace to
    be the current one, so it works after a generator resumed in
    another context (as in the web SSE stream).
    """
    client = mlflow.MlflowClient()
    for key, value in tags.items():
        client.set_trace_tag(trace_id, key, value)
