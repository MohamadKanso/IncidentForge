from __future__ import annotations

import csv
import hashlib
import json
import random
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from incidentforge.models import IncidentBundle, ScenarioDefinition
from incidentforge.scenarios import get_scenario


def generate_bundle(scenario: ScenarioDefinition | str, seed: int = 7) -> IncidentBundle:
    """Generate a deterministic synthetic incident bundle."""

    definition = get_scenario(scenario) if isinstance(scenario, str) else scenario
    rng = random.Random(seed)
    started = datetime(2026, 1, 15, 10, 0, tzinfo=UTC) + timedelta(minutes=rng.randint(0, 240))
    incident_id = _incident_id(definition.slug, seed)

    alert = _alert(definition, incident_id, started)
    metrics = _metrics(definition, started, rng)
    logs = _logs(definition, started, rng)
    traces = _traces(definition, started, rng)
    ground_truth = _ground_truth(definition, incident_id)

    return IncidentBundle(
        incident_id=incident_id,
        scenario=definition,
        seed=seed,
        started_at=started.isoformat(),
        alert=alert,
        metrics=metrics,
        logs=logs,
        traces=traces,
        runbook=definition.runbook,
        ground_truth=ground_truth,
    )


def write_bundle(bundle: IncidentBundle, output_dir: str | Path) -> Path:
    """Write an incident bundle to disk and return the output directory."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    _write_json(output / "manifest.json", bundle.manifest())
    _write_json(output / "alert.json", bundle.alert)
    _write_json(output / "traces.json", bundle.traces)
    _write_json(output / "ground_truth.json", bundle.ground_truth)
    (output / "ground_truth.yaml").write_text(
        _to_simple_yaml(bundle.ground_truth),
        encoding="utf-8",
    )
    (output / "logs.jsonl").write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in bundle.logs) + "\n",
        encoding="utf-8",
    )
    _write_metrics_csv(output / "metrics.csv", bundle.metrics)
    (output / "runbook.md").write_text(_runbook_markdown(bundle), encoding="utf-8")
    (output / "candidate_rca.md").write_text(_candidate_report(bundle), encoding="utf-8")
    return output


def _incident_id(slug: str, seed: int) -> str:
    digest = hashlib.sha1(f"{slug}:{seed}".encode()).hexdigest()[:10]
    return f"ifg-{digest}"


def _alert(
    definition: ScenarioDefinition,
    incident_id: str,
    started: datetime,
) -> dict[str, object]:
    return {
        "schema_version": "incidentforge.alert.v1",
        "incident_id": incident_id,
        "title": definition.title,
        "severity": definition.severity,
        "service": definition.service,
        "summary": definition.summary,
        "started_at": started.isoformat(),
        "labels": {
            "team": "platform",
            "environment": "production",
            "scenario": definition.slug,
            "source": "incidentforge",
        },
        "links": {
            "runbook": "runbook.md",
            "metrics": "metrics.csv",
            "logs": "logs.jsonl",
            "traces": "traces.json",
        },
    }


def _metrics(
    definition: ScenarioDefinition, started: datetime, rng: random.Random
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    signal_names = [signal.name for signal in definition.signals]
    for minute in range(0, 31, 2):
        timestamp = (started + timedelta(minutes=minute)).isoformat()
        phase = min(1.0, minute / 16)
        rows.append(
            {
                "timestamp": timestamp,
                "metric": "service_error_rate",
                "service": definition.service,
                "value": round(0.01 + phase * rng.uniform(0.07, 0.13), 4),
                "unit": "ratio",
                "signal": "impact",
            }
        )
        rows.append(
            {
                "timestamp": timestamp,
                "metric": "service_p95_latency_ms",
                "service": definition.service,
                "value": int(180 + phase * rng.randint(1700, 9400)),
                "unit": "milliseconds",
                "signal": "impact",
            }
        )
        for index, name in enumerate(signal_names):
            baseline = 10 + index * 5
            spike = rng.randint(80, 180) * (index + 1)
            rows.append(
                {
                    "timestamp": timestamp,
                    "metric": name,
                    "service": definition.service,
                    "value": round(baseline + (spike * phase) + rng.random() * 3, 2),
                    "unit": "score",
                    "signal": "expected_evidence",
                }
            )
    return rows


def _logs(
    definition: ScenarioDefinition, started: datetime, rng: random.Random
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for event in definition.timeline:
        rows.append(
            {
                "timestamp": (started + timedelta(minutes=event.minute)).isoformat(),
                "level": "WARN" if event.minute < 10 else "ERROR",
                "service": event.service,
                "message": event.event,
                "evidence": event.evidence,
                "trace_id": _trace_id(definition.slug, event.minute),
            }
        )

    for signal in definition.signals:
        rows.append(
            {
                "timestamp": (started + timedelta(minutes=rng.randint(3, 17))).isoformat(),
                "level": "ERROR",
                "service": definition.service,
                "message": f"{signal.name}: {signal.expected}",
                "query_hint": signal.query,
                "source": signal.source,
            }
        )

    for red_herring in definition.red_herrings:
        rows.append(
            {
                "timestamp": (started + timedelta(minutes=rng.randint(0, 12))).isoformat(),
                "level": "INFO",
                "service": "change-feed",
                "message": red_herring.clue,
                "why_not_root_cause": red_herring.reason,
            }
        )

    rows.extend(
        {
            "timestamp": (started + timedelta(minutes=rng.randint(0, 30))).isoformat(),
            "level": rng.choice(["INFO", "INFO", "WARN"]),
            "service": rng.choice([definition.service, "edge-router", "worker-pool"]),
            "message": rng.choice(
                [
                    "health check passed",
                    "request sample accepted",
                    "background refresh completed",
                    "rate limiter budget healthy",
                ]
            ),
        }
        for _ in range(12)
    )
    return sorted(rows, key=lambda row: str(row["timestamp"]))


def _traces(
    definition: ScenarioDefinition, started: datetime, rng: random.Random
) -> list[dict[str, object]]:
    traces: list[dict[str, object]] = []
    for index in range(6):
        trace_id = _trace_id(definition.slug, index)
        root_duration = rng.randint(800, 3600) if index > 2 else rng.randint(120, 420)
        traces.append(
            {
                "trace_id": trace_id,
                "span_id": f"span-{index}-0",
                "parent_span_id": None,
                "timestamp": (started + timedelta(minutes=index * 3)).isoformat(),
                "service": definition.service,
                "operation": "handle_request",
                "duration_ms": root_duration,
                "status": "ERROR" if index > 2 else "OK",
            }
        )
        traces.append(
            {
                "trace_id": trace_id,
                "span_id": f"span-{index}-1",
                "parent_span_id": f"span-{index}-0",
                "timestamp": (started + timedelta(minutes=index * 3, seconds=1)).isoformat(),
                "service": _dependency_service(definition.slug),
                "operation": "dependency_call",
                "duration_ms": int(root_duration * rng.uniform(0.42, 0.79)),
                "status": "ERROR" if index > 3 else "OK",
            }
        )
    return traces


def _ground_truth(definition: ScenarioDefinition, incident_id: str) -> dict[str, object]:
    return {
        "schema_version": "incidentforge.ground_truth.v1",
        "incident_id": incident_id,
        "scenario": definition.slug,
        "service": definition.service,
        "severity": definition.severity,
        "root_cause": definition.root_cause,
        "root_cause_terms": list(definition.root_cause_terms),
        "evidence_terms": [signal.name for signal in definition.signals]
        + [signal.expected for signal in definition.signals],
        "remediation_terms": list(definition.remediation_terms),
        "red_herring_terms": [
            term for red_herring in definition.red_herrings for term in red_herring.penalty_terms
        ],
        "impact": definition.impact,
        "expected_signals": [signal.__dict__ for signal in definition.signals],
        "red_herrings": [red_herring.__dict__ for red_herring in definition.red_herrings],
    }


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_metrics_csv(path: Path, rows: Iterable[dict[str, object]]) -> None:
    rows = list(rows)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["timestamp", "metric", "service", "value", "unit", "signal"],
        )
        writer.writeheader()
        writer.writerows(rows)


def _runbook_markdown(bundle: IncidentBundle) -> str:
    signals = "\n".join(
        f"- {signal.name}: `{signal.query}` -> {signal.expected}"
        for signal in bundle.scenario.signals
    )
    red_herrings = "\n".join(
        f"- {red.clue} Reason to verify: {red.reason}" for red in bundle.scenario.red_herrings
    )
    return f"""# {bundle.scenario.title} Runbook

Incident: `{bundle.incident_id}`

## First Checks

{bundle.runbook}

## Expected Evidence

{signals}

## Known Red Herrings

{red_herrings}
"""


def _candidate_report(bundle: IncidentBundle) -> str:
    first_signal = bundle.scenario.signals[0]
    second_signal = bundle.scenario.signals[1]
    remediation = ", ".join(bundle.scenario.remediation_terms[:3])
    return f"""# RCA Candidate Report

The incident is most likely caused by {bundle.scenario.root_cause}

Evidence:
- {first_signal.name}: {first_signal.expected}
- {second_signal.name}: {second_signal.expected}
- The affected service is {bundle.scenario.service}.

Recommended response:
- {remediation}.
- Add a regression test and alert so this class of incident is caught earlier.
"""


def _to_simple_yaml(payload: dict[str, object], indent: int = 0) -> str:
    lines: list[str] = []
    pad = " " * indent
    for key, value in payload.items():
        if isinstance(value, dict):
            lines.append(f"{pad}{key}:")
            lines.append(_to_simple_yaml(value, indent + 2).rstrip())
        elif isinstance(value, list):
            lines.append(f"{pad}{key}:")
            for item in value:
                if isinstance(item, dict):
                    lines.append(f"{pad}  -")
                    lines.append(_to_simple_yaml(item, indent + 4).rstrip())
                else:
                    lines.append(f"{pad}  - {json.dumps(item)}")
        else:
            lines.append(f"{pad}{key}: {json.dumps(value)}")
    return "\n".join(lines) + "\n"


def _dependency_service(slug: str) -> str:
    if "kafka" in slug:
        return "schema-registry"
    if "postgres" in slug:
        return "pgbouncer"
    if "airflow" in slug:
        return "airflow-scheduler"
    if "redis" in slug:
        return "redis-primary"
    return "dependency"


def _trace_id(slug: str, index: int) -> str:
    return hashlib.md5(f"{slug}:{index}".encode(), usedforsecurity=False).hexdigest()[:16]
