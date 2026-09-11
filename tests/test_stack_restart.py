"""Real shell-wrapper restarts refresh cached proxy routes after upstream success."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def stack(tmp_path):
    (tmp_path / "scripts").mkdir()
    shutil.copyfile(ROOT / "scripts/stack.sh", tmp_path / "scripts/stack.sh")
    (tmp_path / "app/infra").mkdir(parents=True)
    (tmp_path / "app/infra/docker-compose.observability.yml").touch()
    (tmp_path / "outputs").mkdir()
    binary = tmp_path / "fake-bin/docker"
    binary.parent.mkdir()
    binary.write_text(
        """#!/bin/sh
printf 'CALL\\n' >> "$VOICEUP_FIXTURE_CALLS"
printf '%s\\n' "$@" >> "$VOICEUP_FIXTURE_CALLS"
case " $* " in
 *" config --services "*) printf 'backend\\nworker\\nfrontend\\nnginx\\n' ;;
 *" restart "*) exit "$VOICEUP_FIXTURE_RESTART_STATUS" ;;
 *" exec -T nginx "*) exit "$VOICEUP_FIXTURE_RELOAD_STATUS" ;;
esac
""",
        newline="\n",
    )
    binary.chmod(0o755)
    return tmp_path


def run(stack, arguments, *, restart_status=0, reload_status=0):
    git_bash = Path("C:/Program Files/Git/bin/bash.exe")
    shell = str(git_bash) if git_bash.exists() else shutil.which("sh")
    assert shell
    result = subprocess.run(
        [shell, "-c", 'PATH="$PWD/fake-bin:$PATH" sh scripts/stack.sh "$@"', "test", *arguments],
        cwd=stack,
        env={
            **{key: value for key, value in os.environ.items() if not key.startswith("COMPOSE_")},
            "VOICEUP_FIXTURE_CALLS": str(stack / "calls.txt"),
            "VOICEUP_FIXTURE_RESTART_STATUS": str(restart_status),
            "VOICEUP_FIXTURE_RELOAD_STATUS": str(reload_status),
        },
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    calls = [entry.splitlines() for entry in (stack / "calls.txt").read_text().split("CALL\n")[1:]]
    return result, calls


@pytest.mark.parametrize("mode", ["local", "cpu", "spark"])
@pytest.mark.parametrize(
    "arguments",
    [
        ["restart", "backend", "worker"],
        ["restart", "frontend"],
        ["restart"],
        ["restart", "--timeout", "5"],
    ],
)
def test_successful_upstream_restart_reloads_same_mode_after_success(stack, mode, arguments):
    result, calls = run(stack, ["--mode", mode, *arguments])
    assert result.returncode == 0, result.stderr
    mutations = [call for call in calls if "--services" not in call]
    assert len(mutations) == 2
    assert mutations[0][-len(arguments) :] == arguments
    assert mutations[1][-6:-1] == ["exec", "-T", "nginx", "sh", "-c"]
    assert (
        mutations[0][: mutations[0].index("restart")] == mutations[1][: mutations[1].index("exec")]
    )
    command = mutations[1][-1]
    assert "nginx -t" in command and "nginx -s reload" in command
    assert ("/tmp/voiceup-spark.*/nginx.conf" in command) == (mode == "spark")
    assert "envsubst" not in command and "mktemp" not in command
    if mode == "spark":
        assert '[ "$#" -eq 1 ]' in command
        assert '[ ! -L "$1" ]' in command and '[ ! -L "${1%/*}" ]' in command


@pytest.mark.parametrize("mode", ["local", "cpu", "spark"])
@pytest.mark.parametrize(
    "arguments",
    [
        ["restart", "worker"],
        ["ps"],
        ["stop", "backend"],
        ["exec", "backend", "echo", "restart"],
        ["restart", "--help"],
    ],
)
def test_unrelated_commands_keep_single_execution(stack, mode, arguments):
    result, calls = run(stack, ["--mode", mode, *arguments])
    assert result.returncode == 0, result.stderr
    assert len([call for call in calls if "--services" not in call]) == 1


@pytest.mark.parametrize("mode", ["local", "cpu", "spark"])
def test_failed_restart_does_not_reload_and_preserves_failure(stack, mode):
    result, calls = run(stack, ["--mode", mode, "restart", "backend"], restart_status=7)
    assert result.returncode == 7
    assert not any("exec" in call for call in calls)


@pytest.mark.parametrize("mode", ["local", "cpu", "spark"])
def test_failed_reload_is_not_reported_as_successful_restart(stack, mode):
    result, calls = run(stack, ["--mode", mode, "restart", "backend"], reload_status=8)
    assert result.returncode == 8
    assert len([call for call in calls if "exec" in call]) == 1
