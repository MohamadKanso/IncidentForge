from incidentforge.generator import generate_bundle
from incidentforge.scoring import score_report


def test_score_rewards_root_cause_and_evidence() -> None:
    bundle = generate_bundle("airflow-dag-backfill-storm", seed=5)
    report = """
    The likely root cause is catchup enabled on revenue-etl with an old start_date,
    creating a backfill storm. Evidence includes queued_dag_runs and catchup_config.
    Remediation: disable catchup, reset start_date, and clear queued backfills.
    """

    score = score_report(report, bundle.ground_truth)

    assert score.overall > 0.72
    assert score.root_cause > 0.5
    assert "queued_dag_runs" not in score.missing_evidence


def test_score_penalizes_red_herring_blame() -> None:
    bundle = generate_bundle("postgres-connection-exhaustion", seed=8)
    report = "Root cause is replication lag from a read replica and CloudFront cache hit issues."

    score = score_report(report, bundle.ground_truth)

    assert score.overall < 0.35
    assert score.triggered_red_herrings
    assert score.red_herring_resistance < 1.0

