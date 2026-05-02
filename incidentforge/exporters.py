from __future__ import annotations

import json
from pathlib import Path


def load_bundle_dir(path: str | Path) -> dict[str, object]:
    bundle = Path(path)
    manifest = _load_json(bundle / "manifest.json")
    return {
        "manifest": manifest,
        "alert": _load_json(bundle / "alert.json"),
        "ground_truth": _load_json(bundle / "ground_truth.json"),
        "traces": _load_json(bundle / "traces.json"),
        "logs_path": str(bundle / "logs.jsonl"),
        "metrics_path": str(bundle / "metrics.csv"),
        "runbook_path": str(bundle / "runbook.md"),
    }


def export_opensre_payload(bundle_dir: str | Path, output_path: str | Path) -> Path:
    """Write an OpenSRE-friendly alert payload from a generated bundle."""

    bundle = load_bundle_dir(bundle_dir)
    alert = dict(bundle["alert"])
    ground_truth = dict(bundle["ground_truth"])
    payload = {
        "title": alert["title"],
        "severity": alert["severity"],
        "source": "incidentforge",
        "service": alert["service"],
        "description": alert["summary"],
        "labels": alert["labels"],
        "annotations": {
            "incidentforge_incident_id": alert["incident_id"],
            "expected_root_cause": ground_truth["root_cause"],
            "bundle_manifest": str(Path(bundle_dir) / "manifest.json"),
        },
        "links": alert["links"],
    }
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))

