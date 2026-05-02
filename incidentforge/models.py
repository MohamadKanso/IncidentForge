from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

JsonDict = dict[str, Any]


@dataclass(frozen=True)
class EvidenceSignal:
    """A signal the agent should discover and cite in the investigation."""

    name: str
    source: str
    query: str
    expected: str
    weight: float = 1.0


@dataclass(frozen=True)
class RedHerring:
    clue: str
    reason: str
    penalty_terms: tuple[str, ...]
    weight: float = 1.0


@dataclass(frozen=True)
class TimelineEvent:
    minute: int
    service: str
    event: str
    evidence: str


@dataclass(frozen=True)
class ScenarioDefinition:
    slug: str
    title: str
    summary: str
    severity: str
    service: str
    root_cause: str
    root_cause_terms: tuple[str, ...]
    impact: str
    signals: tuple[EvidenceSignal, ...]
    red_herrings: tuple[RedHerring, ...]
    remediation_terms: tuple[str, ...]
    timeline: tuple[TimelineEvent, ...]
    runbook: str
    tags: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(frozen=True)
class IncidentBundle:
    incident_id: str
    scenario: ScenarioDefinition
    seed: int
    started_at: str
    alert: JsonDict
    metrics: list[JsonDict]
    logs: list[JsonDict]
    traces: list[JsonDict]
    runbook: str
    ground_truth: JsonDict

    def manifest(self) -> JsonDict:
        return {
            "schema_version": "incidentforge.bundle.v1",
            "incident_id": self.incident_id,
            "scenario": self.scenario.slug,
            "title": self.scenario.title,
            "seed": self.seed,
            "started_at": self.started_at,
            "files": {
                "alert": "alert.json",
                "metrics": "metrics.csv",
                "logs": "logs.jsonl",
                "traces": "traces.json",
                "runbook": "runbook.md",
                "ground_truth": "ground_truth.json",
                "ground_truth_yaml": "ground_truth.yaml",
            },
        }


@dataclass(frozen=True)
class ScoreBreakdown:
    root_cause: float
    evidence: float
    remediation: float
    red_herring_resistance: float
    service_identification: float
    overall: float
    missing_evidence: tuple[str, ...]
    missing_remediation: tuple[str, ...]
    triggered_red_herrings: tuple[str, ...]

    def to_dict(self) -> JsonDict:
        return asdict(self)

