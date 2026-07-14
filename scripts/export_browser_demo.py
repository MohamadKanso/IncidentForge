"""Export deterministic IncidentForge fixtures for the zero-install browser lab."""

from __future__ import annotations

import json
from pathlib import Path

from incidentforge.generator import generate_bundle
from incidentforge.scenarios import list_scenarios


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "data" / "scenarios.json"


def strong_report(bundle) -> str:
    truth = bundle.ground_truth
    signals = truth["expected_signals"]
    return (
        f"The root cause is {truth['root_cause']} "
        f"The affected service is {truth['service']}. "
        f"Evidence: {signals[0]['name']} — {signals[0]['expected']} "
        f"Also, {signals[1]['name']} — {signals[1]['expected']} "
        f"Finally, {signals[2]['name']} — {signals[2]['expected']} "
        f"Remediation: {truth['remediation_terms'][0]}, "
        f"{truth['remediation_terms'][1]}, and {truth['remediation_terms'][2]}."
    )


def fooled_report(bundle) -> str:
    truth = bundle.ground_truth
    red_herrings = truth["red_herrings"]
    terms = truth["red_herring_terms"]
    return (
        f"The likely cause is {terms[0]} and {terms[-1]}. "
        f"The clue was: {red_herrings[0]['clue']} "
        "We should roll back the most recent unrelated change and keep monitoring."
    )


def main() -> None:
    payload = []
    for index, scenario in enumerate(list_scenarios(), start=1):
        bundle = generate_bundle(scenario, seed=7 + index)
        payload.append(
            {
                "definition": scenario.to_dict(),
                "manifest": bundle.manifest(),
                "alert": bundle.alert,
                "metrics": bundle.metrics,
                "logs": bundle.logs,
                "traces": bundle.traces,
                "runbook": bundle.runbook,
                "ground_truth": bundle.ground_truth,
                "examples": {
                    "strong": strong_report(bundle),
                    "fooled": fooled_report(bundle),
                },
            }
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {len(payload)} scenarios to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
