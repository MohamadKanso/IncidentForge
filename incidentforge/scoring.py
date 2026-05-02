from __future__ import annotations

import json
import re
from pathlib import Path

from incidentforge.models import ScoreBreakdown

WORD_RE = re.compile(r"[a-z0-9]+")


def score_report(report_text: str, ground_truth: dict[str, object]) -> ScoreBreakdown:
    """Score an RCA report against an IncidentForge ground truth document."""

    normalized = _normalize(report_text)
    root_terms = _as_str_list(ground_truth.get("root_cause_terms"))
    evidence_items = _evidence_items(ground_truth)
    remediation_terms = _as_str_list(ground_truth.get("remediation_terms"))
    red_herring_terms = _as_str_list(ground_truth.get("red_herring_terms"))
    service = str(ground_truth.get("service", ""))

    root_cause = _term_score(normalized, root_terms)
    evidence = _evidence_score(normalized, evidence_items)
    remediation = _term_score(normalized, remediation_terms)
    service_identification = 1.0 if _contains(normalized, service) else 0.0

    triggered_red_herrings = tuple(
        term for term in red_herring_terms if _contains(normalized, term)
    )
    red_herring_penalty = min(0.28, 0.09 * len(triggered_red_herrings))
    red_herring_resistance = max(0.0, 1.0 - red_herring_penalty)

    overall = (
        root_cause * 0.42
        + evidence * 0.34
        + remediation * 0.14
        + service_identification * 0.10
        - red_herring_penalty
    )
    overall = round(max(0.0, min(1.0, overall)), 4)

    return ScoreBreakdown(
        root_cause=round(root_cause, 4),
        evidence=round(evidence, 4),
        remediation=round(remediation, 4),
        red_herring_resistance=round(red_herring_resistance, 4),
        service_identification=round(service_identification, 4),
        overall=overall,
        missing_evidence=tuple(
            name
            for name, terms in evidence_items
            if not any(_contains(normalized, term) for term in terms)
        ),
        missing_remediation=tuple(
            term for term in remediation_terms if not _contains(normalized, term)
        ),
        triggered_red_herrings=triggered_red_herrings,
    )


def load_ground_truth(path: str | Path) -> dict[str, object]:
    truth_path = Path(path)
    if truth_path.suffix not in {".json", ""}:
        raise ValueError("IncidentForge currently scores against ground_truth.json files.")
    return json.loads(truth_path.read_text(encoding="utf-8"))


def score_report_file(report_path: str | Path, ground_truth_path: str | Path) -> ScoreBreakdown:
    report_text = Path(report_path).read_text(encoding="utf-8")
    return score_report(report_text, load_ground_truth(ground_truth_path))


def _term_score(normalized_text: str, terms: list[str]) -> float:
    if not terms:
        return 0.0
    scored = [_contains(normalized_text, term) for term in terms]
    return sum(1 for value in scored if value) / len(scored)


def _evidence_score(normalized_text: str, items: list[tuple[str, list[str]]]) -> float:
    if not items:
        return 0.0
    matches = 0
    for _name, terms in items:
        if any(_contains(normalized_text, term) for term in terms):
            matches += 1
    return matches / len(items)


def _evidence_items(ground_truth: dict[str, object]) -> list[tuple[str, list[str]]]:
    expected_signals = ground_truth.get("expected_signals")
    if isinstance(expected_signals, list):
        items: list[tuple[str, list[str]]] = []
        for raw_signal in expected_signals:
            if not isinstance(raw_signal, dict):
                continue
            name = str(raw_signal.get("name", "unknown_signal"))
            terms = [
                name,
                str(raw_signal.get("expected", "")),
                str(raw_signal.get("query", "")),
            ]
            items.append((name, terms))
        if items:
            return items

    return [(term, [term]) for term in _as_str_list(ground_truth.get("evidence_terms"))]


def _contains(normalized_text: str, term: str) -> bool:
    if not term:
        return False
    normalized_term = _normalize(term)
    if normalized_term in normalized_text:
        return True
    term_words = WORD_RE.findall(normalized_term)
    if not term_words:
        return False
    matches = sum(1 for word in term_words if f" {word} " in f" {normalized_text} ")
    return matches / len(term_words) >= 0.72


def _normalize(text: str) -> str:
    return " ".join(WORD_RE.findall(text.lower()))


def _as_str_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    return []
