# Contributing

Thanks for wanting to improve IncidentForge.

## Local Setup

```bash
python3 -m pip install -e ".[dev]"
python3 -m pytest
```

## Good First Contributions

- Add a new incident scenario
- Improve the scorer's term matching
- Add an exporter for another incident tool
- Improve docs or example RCA reports
- Add regression tests for generated fixtures

## Scenario Quality Bar

A useful scenario should include:

- one precise root cause
- at least three evidence signals
- at least two red herrings
- concrete remediation terms
- deterministic output under a fixed seed
- tests for generation or scoring behavior

## Pull Requests

Please include:

- what changed
- why it changed
- how you tested it
- screenshots if the generated HTML report changed

