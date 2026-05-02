from __future__ import annotations

import html
import json
from datetime import UTC, datetime
from pathlib import Path

from incidentforge.models import ScoreBreakdown

FAVICON_DATA = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
    "viewBox='0 0 32 32'%3E%3Crect width='32' height='32' "
    "fill='%23050505'/%3E%3Ccircle cx='9' cy='9' r='3' "
    "fill='%23f4f4f0'/%3E%3Ccircle cx='16' cy='9' r='3' "
    "fill='%23f4f4f0'/%3E%3Ccircle cx='23' cy='9' r='3' "
    "fill='%23f4f4f0'/%3E%3Ccircle cx='9' cy='16' r='3' "
    "fill='%23f4f4f0'/%3E%3Ccircle cx='23' cy='23' r='3' "
    "fill='%23ff2a2a'/%3E%3C/svg%3E"
)


def render_markdown(score: ScoreBreakdown) -> str:
    missing_evidence = "\n".join(f"- {item}" for item in score.missing_evidence) or "- None"
    missing_remediation = "\n".join(f"- {item}" for item in score.missing_remediation) or "- None"
    red_herrings = "\n".join(f"- {item}" for item in score.triggered_red_herrings) or "- None"
    return f"""# IncidentForge RCA Score

Overall: {score.overall:.2f}

| Dimension | Score |
| --- | ---: |
| Root cause | {score.root_cause:.2f} |
| Evidence | {score.evidence:.2f} |
| Remediation | {score.remediation:.2f} |
| Service identification | {score.service_identification:.2f} |
| Red-herring resistance | {score.red_herring_resistance:.2f} |

## Missing Evidence

{missing_evidence}

## Missing Remediation

{missing_remediation}

## Triggered Red Herrings

{red_herrings}
"""


def render_html(score: ScoreBreakdown, ground_truth: dict[str, object]) -> str:
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    missing_evidence = _list_items(score.missing_evidence)
    missing_remediation = _list_items(score.missing_remediation)
    red_herrings = _list_items(score.triggered_red_herrings)
    scenario = html.escape(str(ground_truth.get("scenario", "unknown")))
    service = html.escape(str(ground_truth.get("service", "unknown")))
    root_cause = html.escape(str(ground_truth.get("root_cause", "unknown")))
    score_json = html.escape(json.dumps(score.to_dict(), indent=2, sort_keys=True))

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="{FAVICON_DATA}">
  <title>IncidentForge RCA Score</title>
  <style>
    :root {{
      --bg: #050505;
      --panel: rgba(255, 255, 255, 0.075);
      --panel-strong: rgba(255, 255, 255, 0.12);
      --text: #f4f4f0;
      --muted: #a7a7a0;
      --line: rgba(255, 255, 255, 0.18);
      --red: #ff2a2a;
      --red-soft: rgba(255, 42, 42, 0.16);
      --good: #f4f4f0;
      --warn: #ff2a2a;
      --shadow: 0 24px 80px rgba(0, 0, 0, 0.55);
      color-scheme: dark;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system,
        BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at 1px 1px, rgba(255,255,255,0.2) 1px,
          transparent 0) 0 0 / 18px 18px,
        linear-gradient(120deg, rgba(255,42,42,0.12), transparent 34%),
        var(--bg);
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background:
        linear-gradient(90deg, rgba(255,255,255,0.05), transparent 18%,
          transparent 82%, rgba(255,255,255,0.04)),
        repeating-linear-gradient(90deg, transparent 0 119px, rgba(255,255,255,0.035) 120px);
      mix-blend-mode: screen;
    }}
    .shell {{
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 40px 0 56px;
    }}
    header {{
      display: grid;
      grid-template-columns: 96px 1fr auto;
      gap: 24px;
      align-items: center;
      padding: 22px 0 42px;
    }}
    .mark {{
      width: 82px;
      height: 82px;
      border: 1px solid var(--line);
      background: rgba(0,0,0,0.42);
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 5px;
      padding: 12px;
      box-shadow: var(--shadow);
    }}
    .dot {{ border-radius: 50%; background: rgba(255,255,255,0.16); }}
    .dot.on {{ background: var(--text); box-shadow: 0 0 18px rgba(255,255,255,0.34); }}
    .dot.red {{ background: var(--red); box-shadow: 0 0 22px rgba(255,42,42,0.7); }}
    h1 {{
      margin: 0;
      font-size: 88px;
      line-height: 0.86;
      letter-spacing: 0;
      text-transform: uppercase;
    }}
    .meta {{
      color: var(--muted);
      font-family: "SFMono-Regular", Consolas, monospace;
      font-size: 13px;
      line-height: 1.35;
      overflow-wrap: anywhere;
      text-transform: uppercase;
    }}
    .hero {{
      display: grid;
      grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.65fr);
      gap: 22px;
      align-items: stretch;
    }}
    .panel {{
      border: 1px solid var(--line);
      background: var(--panel);
      box-shadow: var(--shadow);
      backdrop-filter: blur(18px);
    }}
    .summary {{
      padding: clamp(24px, 4vw, 44px);
      min-height: 420px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}
    .kicker {{
      color: var(--red);
      font-family: "SFMono-Regular", Consolas, monospace;
      font-size: 13px;
      text-transform: uppercase;
    }}
    .root {{
      margin: 24px 0 0;
      font-size: 48px;
      line-height: 1;
      letter-spacing: 0;
      max-width: 920px;
    }}
    .score {{
      display: grid;
      align-content: center;
      justify-items: center;
      padding: 36px;
      min-height: 420px;
      position: relative;
      overflow: hidden;
    }}
    .score::after {{
      content: "";
      position: absolute;
      inset: auto -30px -56px auto;
      width: 220px;
      height: 220px;
      border-radius: 50%;
      border: 1px solid rgba(255,255,255,0.12);
      background: radial-gradient(circle, rgba(255,42,42,0.2), transparent 60%);
    }}
    .score-number {{
      font-family: "SFMono-Regular", Consolas, monospace;
      font-size: 142px;
      line-height: 0.8;
      color: var(--text);
    }}
    .score-label {{
      margin-top: 18px;
      color: var(--muted);
      text-transform: uppercase;
      font-family: "SFMono-Regular", Consolas, monospace;
      font-size: 13px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 12px;
      margin: 22px 0;
    }}
    .metric {{
      min-height: 150px;
      padding: 18px;
      border: 1px solid var(--line);
      background: rgba(0,0,0,0.28);
    }}
    .metric strong {{
      display: block;
      font-family: "SFMono-Regular", Consolas, monospace;
      font-size: 28px;
      margin-bottom: 10px;
    }}
    .metric span {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      line-height: 1.35;
    }}
    .details {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 14px;
      margin-top: 22px;
    }}
    .detail {{
      padding: 22px;
      min-height: 260px;
    }}
    h2 {{
      margin: 0 0 18px;
      text-transform: uppercase;
      font-size: 18px;
      letter-spacing: 0;
    }}
    ul {{
      margin: 0;
      padding: 0;
      list-style: none;
      color: var(--muted);
      line-height: 1.6;
      font-size: 14px;
    }}
    li {{
      border-top: 1px solid rgba(255,255,255,0.1);
      padding: 10px 0;
    }}
    pre {{
      margin: 22px 0 0;
      padding: 22px;
      overflow: auto;
      border: 1px solid var(--line);
      background: rgba(0,0,0,0.42);
      color: #e8e8df;
      font-size: 12px;
    }}
    footer {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      margin-top: 28px;
      color: var(--muted);
      font-family: "SFMono-Regular", Consolas, monospace;
      font-size: 12px;
      text-transform: uppercase;
    }}
    @media (max-width: 900px) {{
      header, .hero, .details {{ grid-template-columns: 1fr; }}
      .grid {{ grid-template-columns: repeat(2, 1fr); }}
      h1 {{ font-size: 64px; }}
      .root {{ font-size: 34px; }}
      .score-number {{ font-size: 112px; }}
    }}
    @media (max-width: 560px) {{
      .shell {{ width: min(100vw - 20px, 1180px); padding-top: 20px; }}
      header {{ gap: 12px; padding-bottom: 24px; }}
      .mark {{
        width: 54px;
        height: 54px;
        gap: 3px;
        padding: 8px;
      }}
      h1 {{ font-size: 36px; }}
      .meta {{ font-size: 10px; }}
      .summary {{ padding: 18px; }}
      .root {{ font-size: 22px; line-height: 1.06; }}
      .score-number {{ font-size: 78px; }}
      .grid {{ grid-template-columns: 1fr; }}
      .summary, .score {{ min-height: auto; }}
      footer {{ flex-direction: column; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <header>
      <div class="mark" aria-label="IncidentForge mark">{_mark_dots()}</div>
      <div>
        <h1>IncidentForge</h1>
        <div class="meta">Synthetic incident benchmark / {scenario} / {service}</div>
      </div>
      <div class="meta">Generated {html.escape(generated_at)}</div>
    </header>

    <section class="hero">
      <div class="panel summary">
        <div>
          <div class="kicker">Expected root cause</div>
          <p class="root">{root_cause}</p>
        </div>
        <div class="meta">
          RCA reports are scored for cause, evidence, remediation,
          and red-herring resistance.
        </div>
      </div>
      <div class="panel score">
        <div class="score-number">{score.overall:.2f}</div>
        <div class="score-label">Overall RCA score</div>
      </div>
    </section>

    <section class="grid" aria-label="Score dimensions">
      {_metric("Root", score.root_cause)}
      {_metric("Evidence", score.evidence)}
      {_metric("Fix", score.remediation)}
      {_metric("Service", score.service_identification)}
      {_metric("Noise", score.red_herring_resistance)}
    </section>

    <section class="details">
      <div class="panel detail">
        <h2>Missing Evidence</h2>
        <ul>{missing_evidence}</ul>
      </div>
      <div class="panel detail">
        <h2>Missing Remediation</h2>
        <ul>{missing_remediation}</ul>
      </div>
      <div class="panel detail">
        <h2>Triggered Red Herrings</h2>
        <ul>{red_herrings}</ul>
      </div>
    </section>

    <pre>{score_json}</pre>
    <footer>
      <span>IncidentForge report v1</span>
      <span>Not affiliated with any phone or OS brand</span>
    </footer>
  </main>
</body>
</html>
"""


def write_html_report(
    score: ScoreBreakdown, ground_truth: dict[str, object], output_path: str | Path
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_html(score, ground_truth), encoding="utf-8")
    return output


def write_markdown_report(score: ScoreBreakdown, output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown(score), encoding="utf-8")
    return output


def _metric(label: str, value: float) -> str:
    return (
        f'<div class="metric"><strong>{value:.2f}</strong>'
        f"<span>{html.escape(label)}</span></div>"
    )


def _list_items(items: tuple[str, ...]) -> str:
    if not items:
        return "<li>None</li>"
    return "".join(f"<li>{html.escape(item)}</li>" for item in items[:8])


def _mark_dots() -> str:
    active = {0, 1, 2, 5, 10, 11, 12, 15, 20, 22, 24}
    red = {18}
    dots = []
    for index in range(25):
        cls = "dot"
        if index in active:
            cls += " on"
        if index in red:
            cls += " red"
        dots.append(f'<span class="{cls}"></span>')
    return "".join(dots)
