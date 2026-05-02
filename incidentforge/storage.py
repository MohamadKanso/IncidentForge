from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from incidentforge.models import ScoreBreakdown

SCHEMA = """
CREATE TABLE IF NOT EXISTS rca_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    incident_id TEXT NOT NULL,
    scenario TEXT NOT NULL,
    service TEXT NOT NULL,
    overall REAL NOT NULL,
    payload TEXT NOT NULL
);
"""


def record_score(
    db_path: str | Path, score: ScoreBreakdown, ground_truth: dict[str, object]
) -> Path:
    """Record a score in a local SQLite history database."""

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(SCHEMA)
        conn.execute(
            """
            INSERT INTO rca_scores (
                created_at, incident_id, scenario, service, overall, payload
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(UTC).isoformat(),
                str(ground_truth.get("incident_id", "unknown")),
                str(ground_truth.get("scenario", "unknown")),
                str(ground_truth.get("service", "unknown")),
                score.overall,
                json.dumps(score.to_dict(), sort_keys=True),
            ),
        )
    return path


def list_scores(db_path: str | Path, limit: int = 10) -> list[dict[str, object]]:
    path = Path(db_path)
    if not path.exists():
        return []
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT created_at, incident_id, scenario, service, overall, payload
            FROM rca_scores
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]

