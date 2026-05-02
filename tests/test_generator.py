import json
from pathlib import Path

from incidentforge.generator import generate_bundle, write_bundle


def test_generate_bundle_is_deterministic() -> None:
    first = generate_bundle("kafka-consumer-lag", seed=42)
    second = generate_bundle("kafka-consumer-lag", seed=42)

    assert first.incident_id == second.incident_id
    assert first.metrics == second.metrics
    assert first.logs == second.logs


def test_write_bundle_creates_expected_files(tmp_path: Path) -> None:
    bundle = generate_bundle("postgres-connection-exhaustion", seed=3)
    write_bundle(bundle, tmp_path)

    expected = {
        "manifest.json",
        "alert.json",
        "metrics.csv",
        "logs.jsonl",
        "traces.json",
        "runbook.md",
        "ground_truth.json",
        "ground_truth.yaml",
        "candidate_rca.md",
    }
    assert expected.issubset({path.name for path in tmp_path.iterdir()})
    truth = json.loads((tmp_path / "ground_truth.json").read_text(encoding="utf-8"))
    assert truth["incident_id"] == bundle.incident_id

