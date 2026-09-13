"""Optional on-premise text inference only admits a same-namespace model peer."""

import importlib.util
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def renderer():
    path = Path(__file__).resolve().parents[1] / "scripts/render_charts.py"
    spec = importlib.util.spec_from_file_location("text_review_renderer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("enabled", [False, True])
def test_actual_chart_keeps_model_port_scoped_to_explicit_internal_peer(
    renderer, tmp_path, enabled
):
    overlay = renderer.load_overlay(renderer.FIXTURES, "lab")
    overlay["textReview"] = {"enabled": enabled}
    renderer.validate_overlay("text", overlay)
    documents = renderer.render_chart(renderer.CHARTS / "app-backend", overlay, tmp_path)
    renderer.validate_documents(documents, overlay["global"]["registry"])
    policy = next(item for item in documents if item["kind"] == "NetworkPolicy")
    ingress = next(item for item in documents if item["kind"] == "Ingress")
    timeout = ingress["metadata"]["annotations"].get(
        "nginx.ingress.kubernetes.io/proxy-read-timeout"
    )
    assert timeout == ("110" if enabled else None)
    assert "nginx.ingress.kubernetes.io/use-regex" not in ingress["metadata"]["annotations"]
    assert ingress["spec"]["rules"][0]["http"]["paths"][0]["pathType"] == "Prefix"
    model_rules = [
        rule
        for rule in policy["spec"]["egress"]
        if {"protocol": "TCP", "port": 11434} in rule.get("ports", [])
    ]
    assert len(model_rules) == int(enabled)
    if enabled:
        assert model_rules[0] == {
            "to": [
                {
                    "podSelector": {
                        "matchLabels": {
                            "app.kubernetes.io/part-of": "voiceup",
                            "app.kubernetes.io/component": "text-review",
                        }
                    }
                }
            ],
            "ports": [{"protocol": "TCP", "port": 11434}],
        }


@pytest.mark.parametrize(
    "value", ["true", 1, None, {}, {"enabled": "false"}, {"enabled": True, "namespace": "other"}]
)
def test_overlay_rejects_untyped_or_expanded_model_peer(renderer, value):
    overlay = renderer.load_overlay(renderer.FIXTURES, "lab")
    overlay["textReview"] = value
    with pytest.raises(renderer.PolicyError):
        renderer.validate_overlay("text", overlay)
