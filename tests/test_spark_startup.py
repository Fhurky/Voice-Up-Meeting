"""Spark startup tests use real inert native processes and temporary files."""

import base64
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
SHELLS = [name for name in ("powershell", "pwsh") if shutil.which(name)]
READY = {
    "ready": True,
    "device": "cuda:0",
    "dimensions": 192,
    "model_id": "speechbrain/spkrec-ecapa-voxceleb",
    "model_revision": "0f99f2d0ebe89ac095bcc5903c4dd8f72b367286",
}
MEETING_READY = {
    "ready": True,
    "device": "cuda:0",
    "model_identity": {
        "diarization": {
            "model_id": "pyannote/speaker-diarization-community-1",
            "revision": "3533c8cf8e369892e6b79ff1bf80f7b0286a54ee",
        },
        "asr": {
            "model_id": "Systran/faster-whisper-large-v3",
            "revision": "edaa852ec7e145841d8ffdb056a99866b5f0a478",
        },
        "embedding": {
            "model_id": READY["model_id"],
            "revision": READY["model_revision"],
            "dimensions": 192,
        },
    },
}


def build_native_docker(directory):
    compiler = (
        Path(os.environ.get("WINDIR", "C:/Windows"))
        / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
    )
    if not compiler.exists():
        pytest.skip("Windows native fixture compiler is required")
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / "fixture.cs"
    source.write_text(r"""
using System;
using System.IO;
using System.Linq;
using System.Threading;
class Fixture {
    static string Env(string key) { return Environment.GetEnvironmentVariable("VOICEUP_FIXTURE_" + key); }
    static int Main(string[] args) {
        File.AppendAllText(Env("CALLS"), String.Join("\t", args) + "\n");
        File.WriteAllText(Env("CALLS") + ".pid", System.Diagnostics.Process.GetCurrentProcess().Id.ToString());
        if (args.Contains("hang")) { Console.Error.Write("fixture-private-error"); Thread.Sleep(60000); }
        if (args.Contains("echo")) { Console.Write(String.Join("\n", args.Skip(1))); return 0; }
        string command = new[] {"config", "up", "exec", "stop"}.FirstOrDefault(args.Contains);
        if (command == "up") File.WriteAllText(Env("CALLS") + ".mode", File.ReadAllText("outputs/local-runtime-mode.txt").Trim());
        bool reload = command == "exec" && args.Contains("sh") && args.Last().Contains("nginx -s reload");
        if (reload) {
            if (Env("FAIL") == "reload") { Console.Error.Write("fixture-private-error"); return 1; }
            File.WriteAllText(Env("CALLS") + ".reloaded", "1"); return 0;
        }
        if (command == "exec" && args.Contains("python") && args.Last().Contains("/meeting-ready")) {
            if (Env("RETRY") == "1" && !File.Exists(Env("CALLS") + ".retry")) {
                File.WriteAllText(Env("CALLS") + ".retry", "1"); Console.Error.Write("fixture-private-error"); return 1;
            }
            Console.Write(Env("MEETING_READY")); return 0;
        }
        if (command == "exec" && Env("RETRY") == "1" && !File.Exists(Env("CALLS") + ".retry")) {
            File.WriteAllText(Env("CALLS") + ".retry", "1"); Console.Error.Write("fixture-private-error"); return 1;
        }
        if (command == Env("FAIL")) { Console.Error.Write("fixture-private-error"); return 1; }
        if (command == "config") Console.Write(Env("CONFIG"));
        if (command == "exec") Console.Write(Env("READY"));
        return 0;
    }
}""")
    binary = directory / "docker.exe"
    result = subprocess.run(
        [str(compiler), "/nologo", "/out:" + str(binary), str(source)],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return binary


@pytest.fixture(scope="session")
def native_docker(tmp_path_factory):
    return build_native_docker(tmp_path_factory.mktemp("native-docker"))


def make_startup(root, binary):
    (root / "scripts").mkdir()
    for name in ("start-local.ps1", "stack.sh"):
        shutil.copyfile(SCRIPTS / name, root / "scripts" / name)
    (root / "app/infra").mkdir(parents=True)
    (root / "app/infra/.env").write_text("# fixture only\n")
    (root / "outputs").mkdir()
    (root / "outputs/local-runtime-mode.txt").write_text("local\n")
    (root / "scripts/spark-tunnel.ps1").write_text(
        "param($Action, $ConfigPath)\nif ($env:VOICEUP_FIXTURE_TUNNEL_FAIL) { throw 'fixture_tunnel_unavailable' }\n[pscustomobject]@{status='ready';pid=123}\n",
        encoding="utf-8",
    )
    return root, binary


@pytest.fixture
def startup(tmp_path, native_docker):
    return make_startup(tmp_path, native_docker)


def run_startup(
    startup,
    shell=None,
    *,
    arguments="-Mode Spark",
    extra=None,
    code=None,
    timeout=40,
    file_mode=False,
):
    if shell is None:
        if not SHELLS:
            raise RuntimeError("An installed PowerShell engine is required")
        shell = SHELLS[0]
    root, binary = startup
    env = {**os.environ, "PATH": str(binary.parent) + os.pathsep + os.environ["PATH"]}
    for key in ("COMPOSE_PROFILES", "COMPOSE_PROJECT_NAME"):
        env.pop(key, None)
    env.update(
        {
            "VOICEUP_FIXTURE_CALLS": str(root / "calls.txt"),
            "VOICEUP_FIXTURE_CONFIG": json.dumps(
                {"services": {"nginx": {"ports": [{"published": "8173"}]}}}
            ),
            "VOICEUP_FIXTURE_READY": json.dumps(READY),
            "VOICEUP_FIXTURE_MEETING_READY": json.dumps(MEETING_READY),
            **(extra or {}),
        }
    )
    command = "$ErrorActionPreference='Stop'; " + (
        code or f"& ./scripts/start-local.ps1 {arguments}"
    )
    invocation = [shutil.which(shell), "-NoProfile", "-NonInteractive"]
    invocation += (
        ["-File", str(root / "scripts/start-local.ps1"), "-Mode", "Spark"]
        if file_mode
        else ["-EncodedCommand", base64.b64encode(command.encode("utf-16-le")).decode()]
    )
    return subprocess.run(
        invocation,
        check=False,
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8" if file_mode else None,
        timeout=timeout,
    )


def calls(startup):
    path = startup[0] / "calls.txt"
    return [line.split("\t") for line in path.read_text().splitlines()] if path.exists() else []


@pytest.mark.parametrize("shell", SHELLS)
def test_startup_default_runs_installed_native_engine(startup, monkeypatch, shell):
    monkeypatch.setitem(run_startup.__globals__, "SHELLS", [shell])
    result = run_startup(startup)
    assert result.returncode == 0, result.stderr
    assert (startup[0] / "outputs/local-runtime-mode.txt").read_text() == "spark\n"
    assert calls(startup)


@pytest.mark.parametrize("enabled", [True, False])
def test_local_meeting_selection_adds_only_the_explicit_overlay(startup, enabled):
    root, _ = startup
    (root / "models/speaker-pilot").mkdir(parents=True)
    (root / "models/speaker-pilot/manifest.json").write_text("{}")
    (root / "app/infra/docker-compose.meeting.yml").write_text("services: {}\n")
    if enabled:
        (root / "outputs/local-meeting-enabled.txt").write_text("enabled\n")
    result = run_startup(startup, "powershell", arguments="-Mode Local")
    assert result.returncode == 0, result.stderr
    assert calls(startup)
    for call in calls(startup):
        assert ("app/infra/docker-compose.meeting.yml" in call) is enabled
    up = next(call for call in calls(startup) if "up" in call)
    assert "--no-build" in up and "never" in up


def test_invalid_meeting_selection_stops_before_compose(startup):
    root, _ = startup
    (root / "models/speaker-pilot").mkdir(parents=True)
    (root / "models/speaker-pilot/manifest.json").write_text("{}")
    (root / "outputs/local-meeting-enabled.txt").write_text("anything\n")
    result = run_startup(startup, "powershell", arguments="-Mode Local")
    assert result.returncode != 0 and not calls(startup)


def test_local_meeting_startup_retries_private_model_readiness_before_ready_url(
    startup,
):
    root, _ = startup
    (root / "models/speaker-pilot").mkdir(parents=True)
    (root / "models/speaker-pilot/manifest.json").write_text("{}")
    (root / "app/infra/docker-compose.meeting.yml").write_text("services: {}\n")
    (root / "outputs/local-meeting-enabled.txt").write_text("enabled\n")
    result = run_startup(
        startup,
        "powershell",
        arguments="-Mode Local",
        extra={"VOICEUP_FIXTURE_RETRY": "1"},
    )
    assert result.returncode == 0, result.stderr
    probes = [call for call in calls(startup) if "python" in call]
    assert len(probes) == 2
    assert all(
        call[call.index("exec") : -1] == ["exec", "-T", "inference", "python", "-c"]
        for call in probes
    )
    assert all(
        "/meeting-ready" in call[-1] and "VOICEUP_INFERENCE_INTERNAL_KEY" in call[-1]
        for call in probes
    )
    assert "fixture-private-error" not in result.stdout + result.stderr
    assert "VoiceUp: http://127.0.0.1:8173" in result.stdout
    assert (root / "outputs/local-runtime-mode.txt").read_text() == "local\n"


def meeting_helper_code():
    return (
        helper_code()
        + r"""
foreach ($name in @('Test-LocalMeetingIdentity', 'Wait-LocalMeetingReady')) {
    $helper=$ast.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name},$false)
    if (-not $helper) { throw 'missing meeting readiness helper' }
    Invoke-Expression $helper.Extent.Text
}
"""
    )


@pytest.mark.parametrize(
    "payload",
    [
        {**MEETING_READY, "ready": "true"},
        {**MEETING_READY, "device": "cpu"},
        {
            **MEETING_READY,
            "model_identity": {
                **MEETING_READY["model_identity"],
                "asr": {
                    "model_id": "wrong",
                    "revision": MEETING_READY["model_identity"]["asr"]["revision"],
                },
            },
        },
        {
            **MEETING_READY,
            "model_identity": {
                **MEETING_READY["model_identity"],
                "diarization": {
                    "model_id": MEETING_READY["model_identity"]["diarization"]["model_id"],
                    "revision": "wrong",
                },
            },
        },
        {
            **MEETING_READY,
            "model_identity": {
                **MEETING_READY["model_identity"],
                "embedding": {
                    **MEETING_READY["model_identity"]["embedding"],
                    "dimensions": "192",
                },
            },
        },
        READY,
        [],
    ],
)
def test_local_meeting_readiness_rejects_wrong_model_or_shape(startup, payload):
    result = run_startup(
        startup,
        "powershell",
        code=meeting_helper_code()
        + r"""
$value=$env:VOICEUP_FIXTURE_MEETING_READY | ConvertFrom-Json
if (Test-LocalMeetingIdentity -Ready $value) { throw 'invalid identity accepted' }
'rejected'
""",
        extra={"VOICEUP_FIXTURE_MEETING_READY": json.dumps(payload)},
    )
    assert result.returncode == 0, result.stderr
    assert "rejected" in result.stdout


def test_local_meeting_readiness_deadline_hides_raw_error_and_preserves_mode(startup):
    begin = time.monotonic()
    result = run_startup(
        startup,
        "powershell",
        code=meeting_helper_code()
        + r"""
Wait-LocalMeetingReady -ComposeArguments @('compose') -TimeoutSeconds 2
'unexpected-ready'
""",
        extra={"VOICEUP_FIXTURE_MEETING_READY": "fixture-private-error"},
        timeout=10,
    )
    assert result.returncode != 0
    assert "voiceup_local_meeting_not_ready" in result.stderr
    assert any("python" in call for call in calls(startup))
    assert "fixture-private-error" not in result.stdout + result.stderr
    assert "unexpected-ready" not in result.stdout
    assert time.monotonic() - begin < 8
    assert (startup[0] / "outputs/local-runtime-mode.txt").read_text() == "local\n"


def test_spark_ignores_local_meeting_selection(startup):
    (startup[0] / "outputs/local-meeting-enabled.txt").write_text("enabled\n")
    result = run_startup(startup, "powershell", arguments="-Mode Spark")
    assert result.returncode == 0, result.stderr
    assert all("app/infra/docker-compose.meeting.yml" not in call for call in calls(startup))


def test_powershell_file_invocation_preserves_turkish_console_output(startup):
    # The actual -File loader in Windows PowerShell 5.1 needs a UTF-8 BOM.
    # This Windows test environment uses a UTF-8 console; decode that wire format explicitly.
    result = run_startup(startup, "powershell", file_mode=True)
    assert result.returncode == 0, result.stderr
    assert "Servis durumunu kontrol etmek için: bash scripts/stack.sh ps" in result.stdout
    assert "Model modu: spark" in result.stdout


@pytest.mark.parametrize("shell", SHELLS)
def test_spark_intent_precedes_mutation_and_native_stderr_is_retried(startup, shell):
    result = run_startup(startup, shell, extra={"VOICEUP_FIXTURE_RETRY": "1"})
    assert result.returncode == 0, result.stderr
    assert "VoiceUp: http://127.0.0.1:8173" in result.stdout
    assert "fixture-private-error" not in result.stdout + result.stderr
    recorded = calls(startup)
    up = next(call for call in recorded if "up" in call)
    assert "app/infra/docker-compose.spark.yml" in up and "inference" not in up
    assert up[up.index("--pull") + 1] == "never"
    assert len([call for call in recorded if "wget" in call]) == 2
    assert recorded[-1][-2:] == ["stop", "inference"]
    assert (startup[0] / "calls.txt.mode").read_text() == "spark"
    assert (startup[0] / "outputs/local-runtime-mode.txt").read_text() == "spark\n"


@pytest.mark.parametrize("shell", SHELLS)
def test_spark_refreshes_nginx_upstream_addresses_after_compose_replacement(startup, shell):
    result = run_startup(startup, shell)
    assert result.returncode == 0, result.stderr
    recorded = calls(startup)
    reloads = [call for call in recorded if "exec" in call and "sh" in call]
    assert len(reloads) == 1
    command = reloads[0]
    assert command[command.index("-p") + 1] == "voiceup"
    assert command[command.index("exec") : -1] == ["exec", "-T", "nginx", "sh", "-c"]
    assert command[-1].index("nginx -t") < command[-1].index("nginx -s reload")
    assert "/tmp/voiceup-spark.*/nginx.conf" in command[-1]
    assert recorded.index(command) > next(
        index for index, call in enumerate(recorded) if "up" in call
    )
    assert (startup[0] / "calls.txt.reloaded").read_text() == "1"
    assert recorded[-1][-2:] == ["stop", "inference"]


@pytest.mark.parametrize("shell", SHELLS)
def test_nginx_reload_failure_does_not_report_ready_or_stop_local_inference(startup, shell):
    result = run_startup(startup, shell, extra={"VOICEUP_FIXTURE_FAIL": "reload"})
    assert result.returncode != 0
    assert "VoiceUp: http://" not in result.stdout
    assert "fixture-private-error" not in result.stdout + result.stderr
    assert not any("stop" in call for call in calls(startup))
    assert (startup[0] / "outputs/local-runtime-mode.txt").read_text() == "spark\n"


@pytest.mark.parametrize("failure", ["up", "stop"])
@pytest.mark.parametrize("shell", SHELLS)
def test_partial_activation_cannot_revert_to_local(startup, failure, shell):
    result = run_startup(startup, shell, extra={"VOICEUP_FIXTURE_FAIL": failure})
    assert result.returncode != 0
    assert "fixture-private-error" not in result.stdout + result.stderr
    assert (startup[0] / "outputs/local-runtime-mode.txt").read_text() == "spark\n"
    assert (startup[0] / "calls.txt.mode").read_text() == "spark"
    result = run_startup(startup, shell, arguments="")
    assert result.returncode == 0, result.stderr
    assert all("app/infra/docker-compose.spark.yml" in call for call in calls(startup))


@pytest.mark.parametrize(
    "failure", ["tunnel", "config", "inference", "ambient_profiles", "ambient_project"]
)
def test_failed_preflight_never_mutates_or_changes_mode(startup, failure):
    overrides = {
        "tunnel": {"VOICEUP_FIXTURE_TUNNEL_FAIL": "1"},
        "config": {"VOICEUP_FIXTURE_FAIL": "config"},
        "inference": {
            "VOICEUP_FIXTURE_CONFIG": json.dumps(
                {
                    "services": {
                        "inference": {},
                        "nginx": {"ports": [{"published": "8173"}]},
                    }
                }
            )
        },
        "ambient_profiles": {"COMPOSE_PROFILES": "*"},
        "ambient_project": {"COMPOSE_PROJECT_NAME": "unrelated-project"},
    }
    result = run_startup(startup, extra=overrides[failure])
    assert result.returncode != 0
    assert all("config" in call for call in calls(startup))
    assert (startup[0] / "outputs/local-runtime-mode.txt").read_text() == "local\n"
    assert "fixture-private-error" not in result.stdout + result.stderr


@pytest.mark.parametrize("saved", ["unknown\n", "spark\nlocal\n"])
def test_invalid_saved_mode_fails_before_docker(startup, saved):
    (startup[0] / "outputs/local-runtime-mode.txt").write_text(saved)
    result = run_startup(startup, arguments="")
    assert result.returncode != 0 and calls(startup) == []


@pytest.mark.parametrize("shell", SHELLS)
def test_explicit_local_override_preserves_local_contract(startup, shell):
    root = startup[0]
    (root / "outputs/local-runtime-mode.txt").write_text("spark\n")
    (root / "models/speaker-pilot").mkdir(parents=True)
    (root / "models/speaker-pilot/manifest.json").write_text("{}")
    result = run_startup(startup, shell, arguments="-Mode Local")
    assert result.returncode == 0, result.stderr
    assert all("app/infra/docker-compose.spark.yml" not in call for call in calls(startup))
    assert (root / "outputs/local-runtime-mode.txt").read_text() == "local\n"


@pytest.mark.parametrize("shell", SHELLS)
@pytest.mark.parametrize("failure", [False, True])
def test_local_refreshes_nginx_after_replacement_and_fails_closed(startup, shell, failure):
    root = startup[0]
    (root / "models/speaker-pilot").mkdir(parents=True)
    (root / "models/speaker-pilot/manifest.json").write_text("{}")
    result = run_startup(
        startup,
        shell,
        arguments="-Mode Local",
        extra={"VOICEUP_FIXTURE_FAIL": "reload" if failure else ""},
    )
    recorded = calls(startup)
    reloads = [call for call in recorded if "exec" in call and "sh" in call]
    assert len(reloads) == 1
    command = reloads[0]
    assert command[command.index("-p") + 1] == "voiceup"
    assert command[-1].index("nginx -t") < command[-1].index("nginx -s reload")
    assert "/tmp/voiceup-spark" not in command[-1]
    assert recorded.index(command) > next(
        index for index, call in enumerate(recorded) if "up" in call
    )
    assert not any("stop" in call for call in recorded)
    assert (root / "outputs/local-runtime-mode.txt").read_text() == "local\n"
    assert "fixture-private-error" not in result.stdout + result.stderr
    if failure:
        assert result.returncode != 0 and "VoiceUp: http://" not in result.stdout
    else:
        assert result.returncode == 0 and "VoiceUp: http://" in result.stdout


def helper_code():
    # Extract the actual private helper without evaluating startup/tunnel code.
    return r"""
$tokens=$null; $errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PWD 'scripts/start-local.ps1'),[ref]$tokens,[ref]$errors)
if ($errors.Count) { throw 'invalid script' }
$helper=$ast.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Invoke-LocalDocker'},$false)
if (-not $helper) { throw 'missing bounded helper' }
Invoke-Expression $helper.Extent.Text
"""


@pytest.mark.parametrize("shell", SHELLS)
def test_native_timeout_is_bounded_and_does_not_echo_stderr(startup, shell):
    begin = time.monotonic()
    result = run_startup(
        startup,
        shell,
        code=helper_code()
        + r"""
try { Invoke-LocalDocker -Arguments @('hang') -TimeoutSeconds 1; throw 'timeout ignored' }
catch { if ($_.Exception.Message -ne 'voiceup_docker_timeout') { throw }; 'bounded-timeout' }
$ownedId=[int](Get-Content ($env:VOICEUP_FIXTURE_CALLS+'.pid'))
if (Get-Process -Id $ownedId -ErrorAction SilentlyContinue) { throw 'timed-out child survived' }
""",
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert "bounded-timeout" in result.stdout
    assert "fixture-private-error" not in result.stdout + result.stderr
    assert time.monotonic() - begin < 8


@pytest.mark.parametrize("shell", SHELLS)
def test_native_arguments_preserve_spaces_quotes_and_trailing_slashes(startup, shell):
    result = run_startup(
        startup,
        shell,
        code=helper_code()
        + r"""
$value=Invoke-LocalDocker -Arguments @('echo', 'path with spaces\', 'literal"quote', '')
if ($value.ExitCode -ne 0 -or $value.Stdout -cne "path with spaces\`nliteral`"quote`n") { throw 'argv changed' }
""",
    )
    assert result.returncode == 0, result.stderr


def run_stack(
    root,
    arguments,
    *,
    profiles="",
    project="",
    services="backend\nworker\nnginx",
    fail=False,
):
    git_bash = Path("C:/Program Files/Git/bin/bash.exe")
    bash = str(git_bash) if git_bash.exists() else shutil.which("bash")
    binary = root / "fake-bin/docker"
    binary.parent.mkdir(exist_ok=True)
    binary.write_text(
        """#!/bin/sh
printf '%s\\n' "$*" >> "$VOICEUP_FIXTURE_CALLS"
case " $* " in
  *" config "*) [ "$VOICEUP_FIXTURE_CONFIG_FAIL" = 0 ] || { echo fixture-private-error >&2; exit 1; }
    printf '%s\\n' "$VOICEUP_FIXTURE_SERVICES" ;;
  *) printf '%s\\n' "$@" ;;
esac
""",
        newline="\n",
    )
    binary.chmod(0o755)
    return subprocess.run(
        [
            bash,
            "-c",
            'PATH="$PWD/fake-bin:$PATH" bash scripts/stack.sh "$@"',
            "test",
            *arguments,
        ],
        check=False,
        cwd=root,
        env={
            **os.environ,
            "COMPOSE_PROFILES": profiles,
            "COMPOSE_PROJECT_NAME": project,
            "VOICEUP_FIXTURE_CALLS": str(root / "shell-calls.txt"),
            "VOICEUP_FIXTURE_SERVICES": services,
            "VOICEUP_FIXTURE_CONFIG_FAIL": "1" if fail else "0",
        },
        capture_output=True,
        text=True,
        timeout=20,
    )


def test_stack_remembers_remote_mode_and_explicit_local_override(startup):
    root = startup[0]
    (root / "outputs/local-runtime-mode.txt").write_text("spark\n")
    result = run_stack(root, ["ps"])
    assert result.returncode == 0 and "docker-compose.spark.yml" in result.stdout
    result = run_stack(root, ["--mode", "local", "ps"])
    assert result.returncode == 0 and "docker-compose.spark.yml" not in result.stdout


@pytest.mark.parametrize(
    "arguments",
    [
        ["up", "inference"],
        ["restart", "inference"],
        ["run", "inference"],
        ["--profile", "local-inference", "up"],
        ["--profile=*", "up"],
        ["unpause", "inference"],
        ["up", "--scale", "inference=1"],
        ["-f", "unsafe.yml", "up"],
        ["--env-file", "unsafe.env", "restart"],
        ["-pother", "start"],
    ],
)
def test_stack_blocks_local_activation_and_model_overrides(startup, arguments):
    result = run_stack(startup[0], ["--mode", "spark", *arguments])
    assert result.returncode != 0 and result.stdout == ""
    assert not (startup[0] / "shell-calls.txt").exists()


@pytest.mark.parametrize("command", ["start", "restart", "up"])
@pytest.mark.parametrize("unsafe", ["profiles", "project", "config_error", "effective_inference"])
def test_stack_general_activation_fails_closed(startup, command, unsafe):
    result = run_stack(
        startup[0],
        ["--mode", "spark", command],
        profiles="*" if unsafe == "profiles" else "",
        project="voiceup" if unsafe == "project" else "",
        fail=unsafe == "config_error",
        services=(
            "backend\nworker\nnginx\ninference"
            if unsafe == "effective_inference"
            else "backend\nworker\nnginx"
        ),
    )
    assert result.returncode != 0 and result.stdout == ""
    assert "fixture-private-error" not in result.stderr
    call_log = startup[0] / "shell-calls.txt"
    if call_log.exists():
        assert all(" config --services" in line for line in call_log.read_text().splitlines())


def test_stack_allows_safe_general_restart_and_explicit_local_stop(startup):
    for arguments in (["restart"], ["stop", "inference"]):
        result = run_stack(startup[0], ["--mode", "spark", *arguments])
        assert result.returncode == 0, result.stderr
        lines = result.stdout.splitlines()
        assert any(
            lines[index : index + len(arguments)] == arguments for index in range(len(lines))
        )


def test_terminal_readiness_failure_preserves_spark_and_never_stops_local(startup):
    begin = time.monotonic()
    result = run_startup(
        startup,
        "powershell",
        extra={"VOICEUP_FIXTURE_READY": json.dumps({**READY, "device": "cpu"})},
    )
    assert result.returncode != 0
    assert time.monotonic() - begin < 38
    assert (startup[0] / "outputs/local-runtime-mode.txt").read_text() == "spark\n"
    recorded = calls(startup)
    assert len([call for call in recorded if "exec" in call]) > 1
    assert not any("stop" in call for call in recorded)
    assert all("app/infra/docker-compose.spark.yml" in call for call in recorded)


@pytest.mark.parametrize("profile", ["local-inference", "*"])
def test_dotenv_profile_is_detected_from_real_compose_before_any_mutation(startup, profile):
    # Only Compose's parser runs. Its real unsafe model is then fed to the inert native fixture.
    infra = SCRIPTS.parent / "app/infra"
    dotenv = startup[0] / "profile.env"
    dotenv.write_text(f"COMPOSE_PROFILES={profile}\nCOMPOSE_PROJECT_NAME=unrelated\n")
    env = {
        **os.environ,
        "POSTGRES_PASSWORD": "fixture-only-postgres",
        "JWT_SECRET": "fixture-private-config-secret-" + "x" * 32,
        "RUNTIME_DATABASE_PASSWORD": "fixture-only-runtime-" + "x" * 32,
        "INFERENCE_INTERNAL_KEY": "fixture-only-inference-" + "x" * 32,
        "GRAFANA_ADMIN_PASSWORD": "fixture-only-grafana",
    }
    env.pop("COMPOSE_PROFILES", None)
    env.pop("COMPOSE_PROJECT_NAME", None)
    command = [
        "docker",
        "compose",
        "--project-directory",
        str(infra),
        "-p",
        "voiceup-parser-fixture",
        "--env-file",
        str(dotenv),
    ]
    for name in (
        "docker-compose.local.yml",
        "docker-compose.observability.yml",
        "docker-compose.spark.yml",
    ):
        command.extend(["-f", str(infra / name)])
    config = subprocess.run(
        command + ["config", "--format", "json"],
        check=False,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert config.returncode == 0, "Real Compose parser failed; output withheld"
    model = json.loads(config.stdout)
    assert "inference" in model["services"]
    result = run_startup(startup, extra={"VOICEUP_FIXTURE_CONFIG": config.stdout})
    assert result.returncode != 0 and all("config" in call for call in calls(startup))
    assert "fixture-private-config-secret" not in result.stdout + result.stderr
    result = run_stack(
        startup[0],
        ["--mode", "spark", "restart"],
        services="\n".join(model["services"]),
    )
    assert result.returncode != 0 and result.stdout == ""
    assert (startup[0] / "outputs/local-runtime-mode.txt").read_text() == "local\n"
