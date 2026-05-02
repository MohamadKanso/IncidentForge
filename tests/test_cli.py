from pathlib import Path

from incidentforge.cli import main


def test_demo_command_creates_report(tmp_path: Path) -> None:
    exit_code = main(["demo", "--out", str(tmp_path), "--scenario", "redis-memory-fragmentation"])

    assert exit_code == 0
    assert (tmp_path / "bundle" / "manifest.json").exists()
    assert (tmp_path / "score.json").exists()
    assert (tmp_path / "report.html").exists()


def test_list_command(capsys) -> None:  # type: ignore[no-untyped-def]
    exit_code = main(["list"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "kafka-consumer-lag" in captured.out

