"""Both supported launchers preserve the explicit optional text-review overlay."""

import pytest

from test_spark_startup import calls, native_docker, run_stack, run_startup, startup

__all__ = ["native_docker", "startup"]


@pytest.mark.parametrize("mode", ["local", "cpu", "spark"])
def test_stack_keeps_text_review_after_mode_overlay_without_bypassing_guards(startup, mode):
    root, _ = startup
    (root / "outputs/local-text-review-enabled.txt").write_text("enabled\n")
    (root / "app/infra/docker-compose.text-review.yml").write_text("services: {}\n")
    result = run_stack(root, ["--mode", mode, "ps"])
    assert result.returncode == 0, result.stderr
    assert "docker-compose.text-review.yml" in result.stdout
    if mode != "local":
        assert result.stdout.index(f"docker-compose.{mode}.yml") < result.stdout.index(
            "docker-compose.text-review.yml"
        )
        rejected = run_stack(root, ["--mode", mode, "-f", "unsafe.yml", "up"])
        assert rejected.returncode != 0


@pytest.mark.parametrize("mode", ["Local", "Spark"])
def test_windows_startup_uses_text_review_and_retains_active_reload(startup, mode):
    root, _ = startup
    (root / "models/speaker-pilot").mkdir(parents=True)
    (root / "models/speaker-pilot/manifest.json").write_text("{}")
    (root / "outputs/local-text-review-enabled.txt").write_text("enabled\n")
    (root / "app/infra/docker-compose.text-review.yml").write_text("services: {}\n")
    result = run_startup(startup, "powershell", arguments=f"-Mode {mode}")
    assert result.returncode == 0, result.stderr
    actual = calls(startup)
    assert actual
    assert all("app/infra/docker-compose.text-review.yml" in call for call in actual)
    reload = next(call[-1] for call in actual if call[-1].startswith("set -eu;"))
    assert ("/tmp/voiceup-spark." if mode == "Spark" else "/tmp/voiceup-text.") in reload
