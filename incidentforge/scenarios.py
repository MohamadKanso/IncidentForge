from __future__ import annotations

from incidentforge.models import EvidenceSignal, RedHerring, ScenarioDefinition, TimelineEvent

SCENARIOS: tuple[ScenarioDefinition, ...] = (
    ScenarioDefinition(
        slug="kafka-consumer-lag",
        title="Kafka Checkout Consumer Lag",
        summary=(
            "Checkout events are delayed because the payments consumer group is stuck "
            "behind a poison message after a schema change."
        ),
        severity="SEV2",
        service="payments-consumer",
        root_cause=(
            "A backward-incompatible schema change introduced a poison message that "
            "repeatedly fails deserialization and stalls the payments consumer group."
        ),
        root_cause_terms=(
            "poison message",
            "schema change",
            "deserialization",
            "payments consumer group",
            "consumer lag",
        ),
        impact="Payment confirmation events are delayed by 18 to 24 minutes.",
        signals=(
            EvidenceSignal(
                "consumer_lag_spike",
                "metrics",
                'sum(kafka_consumer_lag{group="payments-consumer"})',
                "Lag rises from 180 to more than 52000 offsets after 10:08 UTC.",
            ),
            EvidenceSignal(
                "deserialize_errors",
                "logs",
                'service="payments-consumer" "SchemaRegistryDecodeError"',
                "Decode errors repeat for checkout.payment_authorized.v7.",
            ),
            EvidenceSignal(
                "stable_broker_cpu",
                "metrics",
                'avg(kafka_broker_cpu{cluster="orders-eu"})',
                "Broker CPU remains below 42 percent, reducing broker saturation likelihood.",
            ),
        ),
        red_herrings=(
            RedHerring(
                "A checkout-api deploy completed four minutes before the page fired.",
                "The deploy only changed frontend validation and request volume stayed flat.",
                ("checkout-api deploy", "frontend validation"),
            ),
            RedHerring(
                "A Kafka broker leader election occurred earlier in the hour.",
                "Partition ISR recovered before the lag spike and broker health is normal.",
                ("leader election", "broker outage"),
            ),
        ),
        remediation_terms=(
            "skip poison message",
            "rollback schema",
            "add dead letter queue",
            "restart consumer",
            "schema compatibility",
        ),
        timeline=(
            TimelineEvent(
                0,
                "schema-registry",
                "checkout.payment_authorized.v7 registered",
                "new schema",
            ),
            TimelineEvent(
                4,
                "payments-consumer",
                "first decode error",
                "SchemaRegistryDecodeError",
            ),
            TimelineEvent(8, "kafka", "lag crosses 10000 offsets", "consumer_lag_spike"),
            TimelineEvent(14, "pagerduty", "SEV2 alert triggered", "payments delayed"),
        ),
        runbook=(
            "Check consumer lag by group, inspect failed offsets, compare schema registry "
            "versions, and quarantine poison messages before restarting the consumer."
        ),
        tags=("kafka", "schema-registry", "payments", "observability"),
    ),
    ScenarioDefinition(
        slug="postgres-connection-exhaustion",
        title="Postgres Connection Pool Exhaustion",
        summary=(
            "API latency and 5xx errors rise because workers leak database connections "
            "after a retry path skips pool release."
        ),
        severity="SEV1",
        service="orders-api",
        root_cause=(
            "The orders-api retry path leaks Postgres connections when inventory lookups "
            "timeout, exhausting pgbouncer and causing request queuing."
        ),
        root_cause_terms=(
            "connection leak",
            "pgbouncer",
            "retry path",
            "inventory timeout",
            "connection pool exhausted",
        ),
        impact="Order creation p95 latency reaches 9.4 seconds and error rate reaches 11 percent.",
        signals=(
            EvidenceSignal(
                "pgbouncer_waiting_clients",
                "metrics",
                'max(pgbouncer_pools_cl_waiting{database="orders"})',
                "Waiting clients rise from 0 to 146 while active connections cap out.",
            ),
            EvidenceSignal(
                "retry_timeout_logs",
                "logs",
                'service="orders-api" "inventory timeout" "retry"',
                "Retries continue after inventory timeouts without a matching pool release log.",
            ),
            EvidenceSignal(
                "db_cpu_normal",
                "metrics",
                'avg(postgres_cpu_percent{cluster="orders-primary"})',
                "Database CPU remains under 55 percent, pointing away from query saturation.",
            ),
        ),
        red_herrings=(
            RedHerring(
                "A read replica reported replication lag.",
                "The failing write path uses the primary database, not the read replica.",
                ("replication lag", "read replica"),
            ),
            RedHerring(
                "CloudFront cache hit ratio dropped.",
                "Checkout order creation is not cacheable and bypasses CloudFront.",
                ("cloudfront", "cache hit"),
            ),
        ),
        remediation_terms=(
            "patch retry path",
            "release connection",
            "raise pool limit temporarily",
            "restart workers",
            "add regression test",
        ),
        timeline=(
            TimelineEvent(0, "orders-api", "inventory retries increase", "retry_timeout_logs"),
            TimelineEvent(6, "pgbouncer", "waiting clients rise", "pgbouncer_waiting_clients"),
            TimelineEvent(9, "orders-api", "5xx errors breach SLO", "error rate"),
            TimelineEvent(13, "pagerduty", "SEV1 alert triggered", "latency and errors"),
        ),
        runbook=(
            "Check pgbouncer pool state, compare active and waiting clients, inspect "
            "application retry paths, and verify release/finally blocks around database usage."
        ),
        tags=("postgres", "pgbouncer", "api", "latency"),
    ),
    ScenarioDefinition(
        slug="airflow-dag-backfill-storm",
        title="Airflow DAG Backfill Storm",
        summary=(
            "A data platform DAG floods the scheduler because a catchup flag was enabled "
            "during a deployment."
        ),
        severity="SEV2",
        service="revenue-etl",
        root_cause=(
            "The revenue-etl DAG was deployed with catchup enabled and an old start_date, "
            "creating a backfill storm that starves current scheduled runs."
        ),
        root_cause_terms=(
            "catchup enabled",
            "old start_date",
            "backfill storm",
            "scheduler queued",
            "revenue-etl",
        ),
        impact="Revenue freshness SLA misses by 47 minutes for the EU warehouse.",
        signals=(
            EvidenceSignal(
                "queued_dag_runs",
                "metrics",
                'max(airflow_dagrun_queued{dag_id="revenue-etl"})',
                "Queued DAG runs jump from 2 to 318 after the deployment.",
            ),
            EvidenceSignal(
                "catchup_config",
                "logs",
                'dag_id="revenue-etl" "catchup=True"',
                "Scheduler logs show catchup=True with start_date=2025-01-01.",
            ),
            EvidenceSignal(
                "worker_capacity_ok",
                "metrics",
                'avg(celery_worker_concurrency_used{queue="etl"})',
                "Workers have spare slots, so worker capacity is not the primary limiter.",
            ),
        ),
        red_herrings=(
            RedHerring(
                "Snowflake warehouse queue time briefly increased.",
                "Warehouse queueing starts after the Airflow backlog and is downstream impact.",
                ("snowflake queue", "warehouse queue"),
            ),
            RedHerring(
                "A dbt model emitted warnings.",
                "The warnings are non-fatal and appear in successful historical runs too.",
                ("dbt warning", "dbt model"),
            ),
        ),
        remediation_terms=(
            "disable catchup",
            "reset start_date",
            "clear queued backfills",
            "pause dag",
            "scheduler guardrail",
        ),
        timeline=(
            TimelineEvent(0, "gitlab", "DAG config deployed", "catchup=True"),
            TimelineEvent(3, "airflow-scheduler", "historical runs queued", "queued_dag_runs"),
            TimelineEvent(11, "revenue-etl", "freshness SLA warning", "stale partition"),
            TimelineEvent(18, "pagerduty", "SEV2 alert triggered", "freshness breach"),
        ),
        runbook=(
            "Inspect DAG config changes, queued run count, scheduler health, pool slots, "
            "and downstream warehouse queue time before clearing or pausing runs."
        ),
        tags=("airflow", "data-platform", "scheduler", "etl"),
    ),
    ScenarioDefinition(
        slug="redis-memory-fragmentation",
        title="Redis Memory Fragmentation Spiral",
        summary=(
            "Session reads intermittently fail because Redis memory fragmentation climbs "
            "after a burst of large temporary keys."
        ),
        severity="SEV2",
        service="session-cache",
        root_cause=(
            "A burst of oversized preview-session keys caused Redis memory fragmentation "
            "and eviction pressure, leading to session cache misses."
        ),
        root_cause_terms=(
            "redis memory fragmentation",
            "oversized keys",
            "eviction pressure",
            "session cache",
            "preview-session",
        ),
        impact="Authenticated users see intermittent logout loops for 7 percent of requests.",
        signals=(
            EvidenceSignal(
                "fragmentation_ratio",
                "metrics",
                'max(redis_mem_fragmentation_ratio{cluster="session-cache"})',
                "Fragmentation ratio climbs from 1.2 to 2.8 within twelve minutes.",
            ),
            EvidenceSignal(
                "evicted_keys",
                "metrics",
                'sum(rate(redis_evicted_keys_total{cluster="session-cache"}[5m]))',
                "Evictions begin immediately after preview-session key volume rises.",
            ),
            EvidenceSignal(
                "large_key_logs",
                "logs",
                'service="profile-preview" "preview-session" "payload_bytes"',
                "Profile preview writes payloads larger than the configured 64 KB budget.",
            ),
        ),
        red_herrings=(
            RedHerring(
                "A mobile app release increased login traffic.",
                "Login traffic increased only 3 percent and cannot explain the eviction slope.",
                ("mobile release", "login traffic"),
            ),
            RedHerring(
                "TLS handshakes had a small latency bump.",
                "Handshake latency is after the cache miss and is not causal.",
                ("tls handshake", "certificate"),
            ),
        ),
        remediation_terms=(
            "delete oversized keys",
            "restart redis",
            "cap payload size",
            "ttl preview-session",
            "memory fragmentation alert",
        ),
        timeline=(
            TimelineEvent(
                0,
                "profile-preview",
                "large preview-session keys written",
                "large_key_logs",
            ),
            TimelineEvent(7, "redis", "fragmentation ratio exceeds 2.0", "fragmentation_ratio"),
            TimelineEvent(10, "redis", "evicted keys rise", "evicted_keys"),
            TimelineEvent(15, "pagerduty", "SEV2 alert triggered", "logout loops"),
        ),
        runbook=(
            "Inspect Redis memory, fragmentation, key cardinality, largest keys, eviction "
            "counters, and recent writers before restarting or deleting keys."
        ),
        tags=("redis", "cache", "memory", "sessions"),
    ),
)


def list_scenarios() -> tuple[ScenarioDefinition, ...]:
    return SCENARIOS


def get_scenario(slug: str) -> ScenarioDefinition:
    normalized = slug.strip().lower()
    for scenario in SCENARIOS:
        if scenario.slug == normalized:
            return scenario
    available = ", ".join(s.slug for s in SCENARIOS)
    raise KeyError(f"Unknown scenario '{slug}'. Available scenarios: {available}")
