from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from incidentforge import __version__
from incidentforge.exporters import export_opensre_payload, load_bundle_dir
from incidentforge.generator import generate_bundle, write_bundle
from incidentforge.render import render_markdown, write_html_report, write_markdown_report
from incidentforge.scenarios import list_scenarios
from incidentforge.scoring import load_ground_truth, score_report_file
from incidentforge.storage import list_scores, record_score


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    try:
        return int(args.func(args))
    except KeyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="incidentforge",
        description="Synthetic production incidents and RCA evaluation for AI SRE agents.",
    )
    parser.add_argument("--version", action="version", version=f"incidentforge {__version__}")
    sub = parser.add_subparsers(dest="command")

    list_parser = sub.add_parser("list", help="List built-in incident scenarios.")
    list_parser.set_defaults(func=_cmd_list)

    gen_parser = sub.add_parser("generate", help="Generate an incident bundle.")
    gen_parser.add_argument("scenario", help="Scenario slug, for example kafka-consumer-lag.")
    gen_parser.add_argument("--out", default="outputs/incident", help="Output directory.")
    gen_parser.add_argument("--seed", type=int, default=7, help="Deterministic seed.")
    gen_parser.set_defaults(func=_cmd_generate)

    inspect_parser = sub.add_parser("inspect", help="Summarize a generated bundle.")
    inspect_parser.add_argument("bundle", help="Path to an IncidentForge bundle directory.")
    inspect_parser.set_defaults(func=_cmd_inspect)

    score_parser = sub.add_parser("score", help="Score an RCA report against ground truth.")
    score_parser.add_argument(
        "--report",
        required=True,
        help="Path to an RCA markdown/text report.",
    )
    score_parser.add_argument(
        "--truth", required=True, help="Path to IncidentForge ground_truth.json."
    )
    score_parser.add_argument("--json", dest="json_out", help="Write score JSON to this path.")
    score_parser.add_argument("--html", dest="html_out", help="Write premium HTML report.")
    score_parser.add_argument("--md", dest="md_out", help="Write markdown score report.")
    score_parser.add_argument("--history", help="Record the score in a local SQLite history DB.")
    score_parser.set_defaults(func=_cmd_score)

    replay_parser = sub.add_parser("replay", help="Export a bundle for another investigation tool.")
    replay_parser.add_argument("bundle", help="Path to an IncidentForge bundle directory.")
    replay_parser.add_argument("--target", default="opensre", choices=["opensre"])
    replay_parser.add_argument("--out", default="outputs/opensre_alert.json")
    replay_parser.set_defaults(func=_cmd_replay)

    demo_parser = sub.add_parser("demo", help="Generate a complete demo bundle and score report.")
    demo_parser.add_argument("--out", default="examples/demo", help="Output directory.")
    demo_parser.add_argument("--scenario", default="kafka-consumer-lag")
    demo_parser.add_argument("--seed", type=int, default=11)
    demo_parser.set_defaults(func=_cmd_demo)

    history_parser = sub.add_parser("history", help="Show recent scores from a local DB.")
    history_parser.add_argument("--db", default="outputs/incidentforge.sqlite")
    history_parser.add_argument("--limit", type=int, default=10)
    history_parser.set_defaults(func=_cmd_history)

    return parser


def _cmd_list(_args: argparse.Namespace) -> int:
    for scenario in list_scenarios():
        tags = ", ".join(scenario.tags)
        print(f"{scenario.slug:32} {scenario.severity:5} {scenario.title} [{tags}]")
    return 0


def _cmd_generate(args: argparse.Namespace) -> int:
    bundle = generate_bundle(args.scenario, seed=args.seed)
    output = write_bundle(bundle, args.out)
    print(f"generated {bundle.incident_id} -> {output}")
    print(f"candidate report: {output / 'candidate_rca.md'}")
    return 0


def _cmd_inspect(args: argparse.Namespace) -> int:
    bundle = load_bundle_dir(args.bundle)
    alert = bundle["alert"]
    ground_truth = bundle["ground_truth"]
    print(f"incident: {alert['incident_id']}")
    print(f"scenario: {ground_truth['scenario']}")
    print(f"service:  {ground_truth['service']}")
    print(f"severity: {alert['severity']}")
    print(f"impact:   {ground_truth['impact']}")
    print("files:")
    for label, rel_path in alert["links"].items():
        print(f"  {label:8} {Path(args.bundle) / rel_path}")
    return 0


def _cmd_score(args: argparse.Namespace) -> int:
    score = score_report_file(args.report, args.truth)
    ground_truth = load_ground_truth(args.truth)
    print(render_markdown(score))
    if args.json_out:
        _write_json(Path(args.json_out), score.to_dict())
    if args.html_out:
        write_html_report(score, ground_truth, args.html_out)
        print(f"html report: {args.html_out}")
    if args.md_out:
        write_markdown_report(score, args.md_out)
    if args.history:
        record_score(args.history, score, ground_truth)
        print(f"history: {args.history}")
    return 0


def _cmd_replay(args: argparse.Namespace) -> int:
    output = export_opensre_payload(args.bundle, args.out)
    print(f"exported {args.target} payload -> {output}")
    return 0


def _cmd_demo(args: argparse.Namespace) -> int:
    out = Path(args.out)
    bundle_dir = out / "bundle"
    bundle = generate_bundle(args.scenario, seed=args.seed)
    write_bundle(bundle, bundle_dir)
    score = score_report_file(bundle_dir / "candidate_rca.md", bundle_dir / "ground_truth.json")
    _write_json(out / "score.json", score.to_dict())
    write_markdown_report(score, out / "score.md")
    write_html_report(score, bundle.ground_truth, out / "report.html")
    export_opensre_payload(bundle_dir, out / "opensre_alert.json")
    print(f"demo bundle: {bundle_dir}")
    print(f"score:       {out / 'score.json'}")
    print(f"report:      {out / 'report.html'}")
    return 0


def _cmd_history(args: argparse.Namespace) -> int:
    rows = list_scores(args.db, limit=args.limit)
    if not rows:
        print("No score history yet.")
        return 0
    for row in rows:
        print(
            f"{row['created_at']} {row['overall']:.2f} "
            f"{row['scenario']} {row['incident_id']} {row['service']}"
        )
    return 0


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
