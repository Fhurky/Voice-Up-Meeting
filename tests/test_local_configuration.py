"""Local setup preserves dotenv values and never selects an unrelated Compose project."""

import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_existing_quoted_exported_values_are_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.syspath_prepend(str(SCRIPTS))
    prepare = load_script("prepare-local-config")
    path = tmp_path / ".env"
    token = "existing_fixture_secret_" + "x" * 32
    original = f'\ufeff  export JWT_SECRET = "{token}" # preserve\nAPP_HTTP_PORT=8173\n'
    path.write_text(original, encoding="utf-8")
    prepare.prepare_config(path)
    updated = path.read_text(encoding="utf-8-sig")
    assert updated.count("JWT_SECRET") == 1
    assert token in updated and "APP_HTTP_PORT=8173" in updated
    assert "INFERENCE_INTERNAL_KEY=" in updated
    prepare.prepare_config(path)
    assert path.read_text(encoding="utf-8-sig") == updated


def test_invalid_existing_secret_fails_without_rewriting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.syspath_prepend(str(SCRIPTS))
    prepare = load_script("prepare-local-config")
    path = tmp_path / ".env"
    original = "JWT_SECRET=\n"
    path.write_text(original)
    with pytest.raises(ValueError, match="JWT_SECRET"):
        prepare.prepare_config(path)
    assert path.read_text() == original


def test_runtime_provisioning_parses_quotes_and_pins_project(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.syspath_prepend(str(SCRIPTS))
    provision = load_script("provision-local-runtime")
    env_path = tmp_path / "app/infra/.env"
    env_path.parent.mkdir(parents=True)
    env_path.write_text('export RUNTIME_DATABASE_PASSWORD = "' + "x" * 40 + '"\n')
    calls = []

    def fake_run(command, **kwargs):
        from types import SimpleNamespace

        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(provision.subprocess, "run", fake_run)
    provision.provision_runtime(tmp_path)
    command, options = calls[0]
    assert command[command.index("-p") + 1] == "voiceup"
    assert "x" * 40 not in " ".join(command)
    assert "BEGIN;" in options["input"] and "COMMIT;" in options["input"]
    assert "pg_auth_members" in options["input"]
    assert "NOSUPERUSER NOCREATEDB NOCREATEROLE" in options["input"]


def test_startup_uses_resolved_port_and_cannot_pull_images(tmp_path: Path) -> None:
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if shell is None:
        pytest.skip("PowerShell is required for the Windows startup entry point")
    root = tmp_path
    (root / "scripts").mkdir()
    (root / "scripts/start-local.ps1").write_text(
        (SCRIPTS / "start-local.ps1").read_text(), encoding="utf-8"
    )
    (root / "app/infra").mkdir(parents=True)
    (root / "app/infra/.env").write_text("# test-only local configuration\n")
    (root / "models/speaker-pilot").mkdir(parents=True)
    (root / "models/speaker-pilot/manifest.json").write_text("{}")
    # This test replaces Docker with a function. No service, configuration or password is changed.
    code = r"""
$global:voiceupTestComposeCalls = @()
function docker {
    $global:voiceupTestComposeCalls += ,$args
    $global:LASTEXITCODE = 0
    if ($args -contains 'config') {
        '{"services":{"nginx":{"ports":[{"published":"8173"}]}}}'
    }
}
$output = & ./scripts/start-local.ps1
if ($output -notcontains 'VoiceUp: http://127.0.0.1:8173') { throw 'Resolved port was not displayed' }
$up = @($global:voiceupTestComposeCalls | Where-Object { $_ -contains 'up' })
if ($up.Count -ne 1) { throw 'Expected one mocked startup call' }
$words = $up[0]
if ($words[$words.IndexOf('--pull') + 1] -ne 'never') { throw 'Runtime pull was not disabled' }
if ($words[$words.IndexOf('-p') + 1] -ne 'voiceup') { throw 'Project was not pinned' }
"""
    result = subprocess.run(
        [shell, "-NoProfile", "-NonInteractive", "-Command", code],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
