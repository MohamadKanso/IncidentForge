# Roadmap

## 0.1 - Public Portfolio MVP

- Deterministic scenario generator
- Built-in Kafka, Postgres, Airflow, and Redis incidents
- Transparent RCA scoring
- Markdown, JSON, and HTML score reports
- OpenSRE-style alert export
- SQLite score history
- CI and contribution docs

## 0.2 - Scenario Authoring

- External YAML scenario packs
- Scenario validator CLI
- Fixture diff command
- More observability sources: Prometheus, Loki, Datadog, CloudWatch

## 0.3 - Agent Evaluation

- LangGraph evaluator workflow
- Optional LLM judge comparison mode
- Batch benchmark runner
- Leaderboard JSON format

## 0.4 - Infrastructure Lab

- Docker Compose lab with Grafana, Loki, Prometheus, Kafka, and Postgres
- OpenTelemetry trace generation
- ClickHouse-backed benchmark history

## 0.5 - High-Volume Engine

- Rust log mutation engine
- Million-event fixture generation
- Streaming bundle writer

