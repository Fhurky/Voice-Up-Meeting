"""Contextual text review requires an explicit local model identity."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def isolated_review_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    for suffix in ("ENABLED", "URL", "MODEL", "MODEL_DIGEST"):
        monkeypatch.delenv(f"VOICEUP_TEXT_REVIEW_{suffix}", raising=False)


def settings(**values: object) -> Settings:
    return Settings(jwt_secret="fixture-secret-with-at-least-32-bytes", _env_file=None, **values)


def test_text_review_defaults_are_disabled_and_do_not_pin_a_model() -> None:
    value = settings()
    assert value.text_review_enabled is False
    assert value.text_review_url == "http://nginx:9081"
    assert value.text_review_model == "qwen3.5:27b"
    assert value.text_review_model_digest == ""


def test_text_review_requires_pinned_digest_when_enabled() -> None:
    with pytest.raises(ValidationError, match="text_review_model_digest"):
        settings(text_review_enabled=True)
    value = settings(text_review_enabled=True, text_review_model_digest="a" * 64)
    assert value.text_review_enabled is True


@pytest.mark.parametrize("digest", ["a" * 63, "g" * 64, "A" * 64, "sha256:" + "a" * 64])
def test_text_review_rejects_noncanonical_digest(digest: str) -> None:
    with pytest.raises(ValidationError, match="text_review_model_digest"):
        settings(text_review_model_digest=digest)


@pytest.mark.parametrize(
    "url",
    [
        "file:///tmp/model",
        "http://user:secret@model:11434",
        "http://model:11434/api/chat",
        "http://model:11434?x=1",
        "http://model:11434#secret",
        "http://model:invalid",
        "http://model:0",
        "http://model:65536",
        "http://model:11434\n",
    ],
)
def test_text_review_rejects_ambiguous_or_nonorigin_urls(url: str) -> None:
    with pytest.raises(ValidationError, match="text_review_url"):
        settings(text_review_url=url)


@pytest.mark.parametrize(
    "name", ["", " qwen3.5:27b", "qwen3.5:27b ", "qwen\n3", "https://model", "a" * 201]
)
def test_text_review_rejects_unsafe_model_names(name: str) -> None:
    with pytest.raises(ValidationError, match="text_review_model"):
        settings(text_review_model=name)
