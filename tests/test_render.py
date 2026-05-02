from incidentforge.generator import generate_bundle
from incidentforge.render import render_html
from incidentforge.scoring import score_report


def test_render_html_contains_premium_report_shell() -> None:
    bundle = generate_bundle("kafka-consumer-lag", seed=11)
    score = score_report(
        "poison message schema change payments consumer group",
        bundle.ground_truth,
    )
    html = render_html(score, bundle.ground_truth)

    assert "IncidentForge" in html
    assert "dot" in html
    assert "Overall RCA score" in html
    assert bundle.scenario.slug in html
