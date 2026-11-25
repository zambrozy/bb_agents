"""Read auction traces back and export their decisions as JSONL."""

from pathlib import Path

import mlflow
from mlflow.entities import Trace

from consts.tracing import (
    AUCTION_SPAN,
    DECISION_SPAN,
    TAG_CONVENTION,
    TAG_MODEL,
    TAG_SOURCE,
)
from models.tracing import BidDecision, BidObservation, DecisionRecord


def decision_records(trace: Trace) -> list[DecisionRecord]:
    """Decisions of one auction trace, in order (Trace)
    -> list[DecisionRecord]; [] if it is not an auction trace.

    Decision spans without output (failed model call) are skipped.
    """
    roots = [s for s in trace.data.spans if s.parent_id is None]
    if not roots or roots[0].name != AUCTION_SPAN:
        return []
    root = roots[0]
    summary = root.outputs  # None: stopped or failed auction
    tags = trace.info.tags
    spans = sorted(
        trace.search_spans(name=DECISION_SPAN),
        key=lambda span: span.start_time_ns,
    )
    records = []
    for span in spans:
        if span.outputs is None:
            continue
        observation = BidObservation.model_validate(span.inputs)
        records.append(DecisionRecord(
            trace_id=trace.info.trace_id,
            observation=observation,
            decision=BidDecision.model_validate(span.outputs),
            model=tags.get(TAG_MODEL + observation.seat),
            convention=tags.get(TAG_CONVENTION + observation.seat),
            deal=root.inputs["deal"],
            finished=summary is not None,
            contract=summary["contract"] if summary else None,
            source=tags.get(TAG_SOURCE),
        ))
    return records


def trace_filter(
    tags: dict[str, str], extra: str | None = None
) -> str | None:
    """MLflow filter string matching all `tags` and `extra`
    (tags: key -> exact value, extra: raw filter string or None)
    -> str | None; None when there is nothing to filter.

    Conditions are joined with AND (MLflow has no OR). Keys are
    backticked, so dotted ones like `model.NORTH` work.
    """
    clauses = [f"tags.`{key}` = '{value}'" for key, value in tags.items()]
    if extra:
        clauses.append(extra)
    return " AND ".join(clauses) or None


def load_decisions(
    experiment: str,
    max_traces: int | None = None,
    filter_string: str | None = None,
) -> list[DecisionRecord]:
    """Decisions of the auction traces of an experiment
    (experiment: name, max_traces: newest N matching traces or all,
    filter_string: MLflow trace filter or None for all)
    -> list[DecisionRecord]; [] if the experiment does not exist.

    Reads from the current MLflow tracking URI, after writing the
    traces still queued by this process.
    """
    found = mlflow.get_experiment_by_name(experiment)
    if found is None:
        return []
    traces = mlflow.search_traces(
        locations=[found.experiment_id],
        filter_string=filter_string,
        max_results=max_traces,
        order_by=["timestamp_ms DESC"],
        return_type="list",
        include_spans=True,
        flush=True,  # traces are logged asynchronously
    )
    return [
        record for trace in traces for record in decision_records(trace)
    ]


def write_jsonl(records: list[DecisionRecord], path: str | Path) -> int:
    """Write records, one JSON object per line (list[DecisionRecord],
    path: str | Path) -> number of records written.

    Creates the parent directory if needed.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        for record in records:
            file.write(record.model_dump_json() + "\n")
    return len(records)
