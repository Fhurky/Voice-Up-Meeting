"""PowerShell orchestration tests use real files and signature-constrained OS/HTTP doubles."""

import base64
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "spark-tunnel.ps1"
SHELLS = [path for name in ("powershell.exe", "pwsh") if (path := shutil.which(name))]
SHELL = None
REVISION = "0f99f2d0ebe89ac095bcc5903c4dd8f72b367286"


@pytest.fixture(
    params=SHELLS or [None],
    ids=lambda value: Path(value).stem if value else "missing",
    autouse=True,
)
def powershell_engine(request, monkeypatch):
    monkeypatch.setitem(globals(), "SHELL", request.param)


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def invoke(code):
    assert SHELL, "PowerShell is required for the tunnel's Windows process boundary tests"
    command = (
        "$ErrorActionPreference='Stop'; [Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); "
        + code
    )
    result = subprocess.run(
        [
            SHELL,
            "-NoProfile",
            "-NonInteractive",
            "-EncodedCommand",
            base64.b64encode(command.encode("utf-16-le")).decode(),
        ],
        cwd=ROOT,
        capture_output=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    return json.loads(result.stdout.decode("utf-8-sig"))


@pytest.fixture
def connection(tmp_path):
    folder = tmp_path / "keys with spaces"
    folder.mkdir()
    identity = folder / "identity file"
    identity.write_text("unused test private-key placeholder")
    known = folder / "known hosts"
    known.write_text(
        "10.19.57.150 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGR1bW15Zml4dHVyZWtleWJ5dGVzYW5kdGVzdHMxMjM0NTY=\n"
    )
    config = {
        "host": "192.168.137.2",
        "user": "lab_nvidia1",
        "identity_file": str(identity),
        "known_hosts": str(known),
        "host_key_alias": "10.19.57.150",
        "local_port": 18090,
        "remote_port": 8090,
    }
    path = tmp_path / "connection.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return path, config


def harness(connection, extra=""):
    path, _ = connection
    return (
        f". {quote(SCRIPT)}; $configPath={quote(path)}; "
        + r"""
$script:Launches=0; $script:Kills=0; $script:Ticks=0; $script:Alive=$false
$script:Occupied=$false; $script:Ready=$true; $script:Mismatch=''; $script:LaunchError=$false
$script:FixtureProcess=$null; $script:CapturedArguments=''; $script:ExitAfterLaunch=$false
$script:InspectionError=$false
function Get-SparkPortOwners { param([int]$LocalPort)
    if($LocalPort -ne 18090){throw 'unexpected_port'}
    if($script:Occupied){return 999999}
    if($script:Alive){return 246810}
}
function Get-SparkProcess { param([int]$ProcessId)
    if($ProcessId -ne 246810){throw 'unexpected_pid'}
    if($script:InspectionError){throw 'spark_tunnel_process_inspection_failed'}
    if($script:ExitAfterLaunch -and $script:Launches -gt 0 -and $script:FixtureProcess){
        $script:ExitAfterLaunch=$false; $script:Alive=$false; return $null
    }
    if(-not $script:Alive){return $null}
    $copy=[pscustomobject]@{
        pid=$script:FixtureProcess.pid; start_utc=$script:FixtureProcess.start_utc
        executable_path=$script:FixtureProcess.executable_path; command_line=$script:FixtureProcess.command_line
    }
    switch($script:Mismatch){
        'path' {$copy.executable_path='C:\unrelated\ssh.exe'}
        'time' {$copy.start_utc='2026-09-09T00:00:01.0000000Z'}
        'command' {$copy.command_line += ' "unexpected"'}
    }
    return $copy
}
function Start-Process { [CmdletBinding()]param([string]$FilePath,[string]$ArgumentList,[string]$WindowStyle,[switch]$PassThru)
    if($WindowStyle -ne 'Hidden' -or -not $PassThru){throw 'visible_launch'}
    if($script:LaunchError){throw 'private-secret-must-not-escape'}
    $script:Launches++; $script:Alive=$true; $script:CapturedArguments=$ArgumentList
    $script:FixtureProcess=[pscustomobject]@{pid=246810; start_utc='2026-09-09T00:00:00.0000000Z'; executable_path=$FilePath; command_line=('"'+$FilePath+'" '+$ArgumentList)}
    $launched=[pscustomobject]@{Id=246810; Handle=1234}
    $launched | Add-Member -MemberType ScriptMethod -Name Dispose -Value {}
    return $launched
}
function Stop-SparkLaunchedProcess { param($Launched)
    if($Launched.Id -ne 246810 -or $Launched.Handle -ne 1234){throw 'unexpected_launch_handle'}
    $script:Kills++; $script:Alive=$false
}
function Stop-SparkOwnedProcess { param($Context,$State)
    if($State.pid -ne 246810 -or $State.start_utc -ne '2026-09-09T00:00:00.0000000Z'){throw 'unexpected_stop'}
    $script:Kills++; $script:Alive=$false
}
function Invoke-SparkReadyRequest { param([string]$Uri,[int]$TimeoutMilliseconds)
    if($Uri -ne 'http://127.0.0.1:18090/ready' -or $TimeoutMilliseconds -gt 2000 -or $TimeoutMilliseconds -le 0){throw 'unexpected_http_request'}
    if(-not $script:Ready){return $null}
    return [pscustomobject]@{ready=$true; model_id='speechbrain/spkrec-ecapa-voxceleb'; model_revision='0f99f2d0ebe89ac095bcc5903c4dd8f72b367286'; dimensions=192; device='cuda:0'}
}
function Get-SparkMonotonicMilliseconds {$script:Ticks += 5000; return $script:Ticks}
function Start-Sleep { param([int]$Milliseconds) }
function Seed-OwnedTunnel {
    $context=Get-SparkTunnelContext -ConfigPath $configPath
    $null=Start-Process -FilePath $context.SshPath -ArgumentList $context.ArgumentString -WindowStyle Hidden -PassThru
    $script:Launches=0
    $state=[pscustomobject]@{schema_version=1; pid=246810; start_utc=$script:FixtureProcess.start_utc; ssh_path=$context.SshPath; config_sha256=$context.ConfigDigest}
    [IO.File]::WriteAllText($context.StatePath,($state|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
}
"""
        + extra
    )


def test_dot_source_is_inert_and_returns_validated_connection(connection):
    result = invoke(
        harness(
            connection, "Get-SparkConnection -ConfigPath $configPath | ConvertTo-Json -Compress"
        )
    )
    assert result == connection[1]
    assert not connection[0].with_name("connection.tunnel-state.json").exists()


def test_json_state_preserves_exact_timestamp_string_for_process_ownership(connection):
    result = invoke(
        harness(
            connection,
            "Seed-OwnedTunnel; $context=Get-SparkTunnelContext -ConfigPath $configPath; "
            "$state=Read-SparkTunnelState -Context $context; "
            "@{timestamp=$state.start_utc;type=$state.start_utc.GetType().FullName;"
            "status=(Get-SparkTunnelStatus -ConfigPath $configPath).status;"
            "launches=$script:Launches;kills=$script:Kills}|ConvertTo-Json -Compress",
        )
    )
    assert result == {
        "timestamp": "2026-09-09T00:00:00.0000000Z",
        "type": "System.String",
        "status": "ready",
        "launches": 0,
        "kills": 0,
    }


@pytest.mark.parametrize(
    "timestamp",
    [
        123,
        None,
        "2026-09-09T00:00:00Z",
        "2026-09-09T00:00:00.0000000+00:00",
        "2026-02-30T00:00:00.0000000Z",
        "2026-09-09T00:00:00.0000001Z",
    ],
)
def test_noncanonical_or_foreign_state_timestamp_is_never_reused_or_stopped(connection, timestamp):
    literal = (
        quote(timestamp)
        if isinstance(timestamp, str)
        else "$null"
        if timestamp is None
        else str(timestamp)
    )
    result = invoke(
        harness(
            connection,
            "Seed-OwnedTunnel; $context=Get-SparkTunnelContext -ConfigPath $configPath; "
            "$document=Get-Content -LiteralPath $context.StatePath -Raw | ConvertFrom-Json; "
            f"$document.start_utc={literal}; "
            "[IO.File]::WriteAllText($context.StatePath,($document|ConvertTo-Json),[Text.UTF8Encoding]::new($false)); "
            "try{Stop-SparkTunnel -ConfigPath $configPath}catch{"
            "@{error=$_.Exception.Message;kills=$script:Kills;launches=$script:Launches}|ConvertTo-Json -Compress}",
        )
    )
    assert result == {
        "error": "spark_tunnel_state_mismatch",
        "kills": 0,
        "launches": 0,
    }
    assert connection[0].with_name("connection.tunnel-state.json").exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("host", "8.8.8.8"),
        ("host", "127.0.0.1"),
        ("host", "10.1"),
        ("user", "--other"),
        ("identity_file", "relative-key"),
        ("known_hosts", "C:\\missing-spark-test-known-hosts"),
        ("host_key_alias", "unknown-host"),
        ("local_port", 18091),
        ("remote_port", 22),
        ("local_port", "18090"),
    ],
)
def test_invalid_config_fails_before_launch(connection, field, value):
    path, config = connection
    config[field] = value
    path.write_text(json.dumps(config), encoding="utf-8")
    result = invoke(
        harness(
            connection,
            "try{Start-SparkTunnel -ConfigPath $configPath}catch{[pscustomobject]@{error=$_.Exception.Message; launches=$script:Launches}|ConvertTo-Json -Compress}",
        )
    )
    assert result["error"].startswith("spark_tunnel_") and result["launches"] == 0


def test_unknown_config_fields_and_duplicate_fields_are_rejected(connection):
    path, config = connection
    config["password"] = "private-secret-must-not-escape"
    path.write_text(json.dumps(config), encoding="utf-8")
    result = invoke(
        harness(
            connection,
            "try{Get-SparkConnection -ConfigPath $configPath}catch{@{error=$_.Exception.Message}|ConvertTo-Json -Compress}",
        )
    )
    assert result == {"error": "spark_tunnel_invalid_config"}
    del config["password"]
    path.write_text(json.dumps(config)[:-1] + ',"host":"192.168.137.2"}', encoding="utf-8")
    assert (
        invoke(
            harness(
                connection,
                "try{Get-SparkConnection -ConfigPath $configPath}catch{@{error=$_.Exception.Message}|ConvertTo-Json -Compress}",
            )
        )
        == result
    )


def test_start_publishes_owned_state_and_quotes_native_arguments(connection):
    result = invoke(
        harness(
            connection,
            "$result=Start-SparkTunnel -ConfigPath $configPath; @{result=$result; launches=$script:Launches; args=@(Split-SparkCommandLine ('ssh.exe '+$script:CapturedArguments))}|ConvertTo-Json -Depth 5 -Compress",
        )
    )
    assert result["result"] == {"status": "ready", "pid": 246810}
    assert result["launches"] == 1
    argv = result["args"][1:]
    for option in [
        "BatchMode=yes",
        "IdentitiesOnly=yes",
        "StrictHostKeyChecking=yes",
        "HostKeyAlias=10.19.57.150",
        "ExitOnForwardFailure=yes",
        "ConnectTimeout=8",
        "ServerAliveInterval=10",
        "ServerAliveCountMax=3",
        "ForwardAgent=no",
    ]:
        assert option in argv and argv[argv.index(option) - 1] == "-o"
    assert argv[argv.index("-i") + 1] == connection[1]["identity_file"]
    assert "UserKnownHostsFile=" + connection[1]["known_hosts"] in argv
    assert argv[argv.index("-L") + 1] == "127.0.0.1:18090:127.0.0.1:8090"
    assert argv[-1] == "lab_nvidia1@192.168.137.2" and "-N" in argv and "-T" in argv
    state = json.loads(connection[0].with_name("connection.tunnel-state.json").read_text())
    assert set(state) == {"schema_version", "pid", "start_utc", "ssh_path", "config_sha256"}
    assert state["config_sha256"] == hashlib.sha256(connection[0].read_bytes()).hexdigest()


def test_owned_ready_process_is_reused_and_stop_removes_only_its_state(connection):
    result = invoke(
        harness(
            connection,
            "Seed-OwnedTunnel; $start=Start-SparkTunnel -ConfigPath $configPath; $status=Get-SparkTunnelStatus -ConfigPath $configPath; $stop=Stop-SparkTunnel -ConfigPath $configPath; @{start=$start;status=$status;stop=$stop;launches=$script:Launches;kills=$script:Kills}|ConvertTo-Json -Depth 5 -Compress",
        )
    )
    assert result["start"]["status"] == result["status"]["status"] == "ready"
    assert result["stop"]["status"] == "stopped" and result["kills"] == 1
    assert result["launches"] == 0
    assert (
        connection[0].exists()
        and not connection[0].with_name("connection.tunnel-state.json").exists()
    )


@pytest.mark.parametrize("mismatch", ["path", "time", "command"])
def test_unrelated_process_identity_is_never_reused_or_stopped(connection, mismatch):
    code = f"Seed-OwnedTunnel; $script:Mismatch={quote(mismatch)}; try{{Stop-SparkTunnel -ConfigPath $configPath}}catch{{@{{error=$_.Exception.Message;kills=$script:Kills}}|ConvertTo-Json -Compress}}"
    result = invoke(harness(connection, code))
    assert result == {"error": "spark_tunnel_state_mismatch", "kills": 0}
    assert connection[0].with_name("connection.tunnel-state.json").exists()


def test_occupied_port_without_owned_state_is_refused(connection):
    result = invoke(
        harness(
            connection,
            "$script:Occupied=$true; try{Start-SparkTunnel -ConfigPath $configPath}catch{@{error=$_.Exception.Message;launches=$script:Launches;kills=$script:Kills}|ConvertTo-Json -Compress}",
        )
    )
    assert result == {"error": "spark_tunnel_port_occupied", "launches": 0, "kills": 0}


def test_dead_state_is_removed_without_killing_reused_pids(connection):
    result = invoke(
        harness(
            connection,
            "Seed-OwnedTunnel; $script:Alive=$false; $status=Get-SparkTunnelStatus -ConfigPath $configPath; $stop=Stop-SparkTunnel -ConfigPath $configPath; @{status=$status;stop=$stop;kills=$script:Kills}|ConvertTo-Json -Depth 5 -Compress",
        )
    )
    assert result["status"]["status"] == result["stop"]["status"] == "stopped"
    assert result["kills"] == 0
    assert not connection[0].with_name("connection.tunnel-state.json").exists()


def test_readiness_timeout_cleans_only_new_owned_process(connection):
    result = invoke(
        harness(
            connection,
            "$script:Ready=$false; try{Start-SparkTunnel -ConfigPath $configPath}catch{@{error=$_.Exception.Message;kills=$script:Kills;ticks=$script:Ticks}|ConvertTo-Json -Compress}",
        )
    )
    assert result["error"] == "spark_tunnel_readiness_timeout" and result["kills"] == 1
    assert result["ticks"] <= 40000
    assert not connection[0].with_name("connection.tunnel-state.json").exists()


def test_existing_unready_process_is_not_killed_by_start_timeout(connection):
    result = invoke(
        harness(
            connection,
            "Seed-OwnedTunnel; $script:Ready=$false; try{Start-SparkTunnel -ConfigPath $configPath}catch{@{error=$_.Exception.Message;kills=$script:Kills}|ConvertTo-Json -Compress}",
        )
    )
    assert result == {"error": "spark_tunnel_readiness_timeout", "kills": 0}
    assert connection[0].with_name("connection.tunnel-state.json").exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("ready", "true"),
        ("model_id", "other"),
        ("model_revision", "other"),
        ("dimensions", 191),
        ("dimensions", "192"),
        ("device", "cpu"),
        ("device", "cuda:1"),
    ],
)
def test_readiness_requires_exact_spark_contract(connection, field, value):
    payload = {
        "ready": True,
        "model_id": "speechbrain/spkrec-ecapa-voxceleb",
        "model_revision": REVISION,
        "dimensions": 192,
        "device": "cuda:0",
    }
    payload[field] = value
    code = (
        "Seed-OwnedTunnel; function Invoke-SparkReadyRequest {param([string]$Uri,[int]$TimeoutMilliseconds) "
        + quote(json.dumps(payload))
        + " | ConvertFrom-Json }; Get-SparkTunnelStatus -ConfigPath $configPath | ConvertTo-Json -Compress"
    )
    assert invoke(harness(connection, code)) == {"status": "unavailable", "pid": 246810}


def test_launch_exception_is_sanitized(connection):
    result = invoke(
        harness(
            connection,
            "$script:LaunchError=$true; try{Start-SparkTunnel -ConfigPath $configPath}catch{@{error=$_.Exception.Message;kills=$script:Kills}|ConvertTo-Json -Compress}",
        )
    )
    assert result == {"error": "spark_tunnel_start_failed", "kills": 0}


@pytest.mark.parametrize("failure", ["$script:InspectionError=$true", "$script:Mismatch='command'"])
def test_initial_inspection_failure_closes_only_the_new_process_handle(connection, failure):
    code = (
        failure
        + "; try{Start-SparkTunnel -ConfigPath $configPath}catch{@{error=$_.Exception.Message;kills=$script:Kills;alive=$script:Alive}|ConvertTo-Json -Compress}"
    )
    result = invoke(harness(connection, code))
    assert result["error"] in {
        "spark_tunnel_process_inspection_failed",
        "spark_tunnel_state_mismatch",
    }
    assert result["kills"] == 1 and result["alive"] is False
    assert not connection[0].with_name("connection.tunnel-state.json").exists()
