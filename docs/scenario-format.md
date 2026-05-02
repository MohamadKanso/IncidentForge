# Scenario Format

Built-in scenarios are Python dataclasses for now because that keeps the MVP easy to
test and refactor. A future release can add external YAML scenario packs.

Each scenario defines:

- `slug` - stable CLI identifier
- `title` - human-readable incident name
- `severity` - `SEV1`, `SEV2`, or similar
- `service` - primary affected service
- `root_cause` - canonical explanation
- `root_cause_terms` - phrases the scorer expects to find
- `signals` - metrics, logs, and traces the investigator should cite
- `red_herrings` - misleading evidence with penalty terms
- `remediation_terms` - expected response actions
- `timeline` - ordered incident events
- `runbook` - operator guidance bundled with the incident

## Generated Bundle Contract

```text
bundle/
  manifest.json
  alert.json
  metrics.csv
  logs.jsonl
  traces.json
  runbook.md
  ground_truth.json
  ground_truth.yaml
  candidate_rca.md
```

The machine-readable scoring contract is `ground_truth.json`. The YAML file is
generated for readability and review.

## Contribution Checklist

- The root cause must be specific, not just "latency increased."
- At least three evidence signals should be required.
- At least two red herrings should be present.
- Remediation terms should include both immediate mitigation and prevention.
- The generated candidate RCA should score above 0.65 but below perfect.

