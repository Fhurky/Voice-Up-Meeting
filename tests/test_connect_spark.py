"""One-click Spark orchestration uses real PowerShell and an exclusive file lock."""

import base64
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/connect-spark.ps1"
SHELL = shutil.which("powershell.exe")


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def invoke(code, shell=SHELL):
    assert shell, "PowerShell is required for the connection launcher"
    source = (
        "$ErrorActionPreference='Stop'; "
        "[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); " + code
    )
    result = subprocess.run(
        [
            shell,
            "-NoProfile",
            "-NonInteractive",
            "-EncodedCommand",
            base64.b64encode(source.encode("utf-16-le")).decode(),
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
    path = tmp_path / "connection with spaces.json"
    path.write_text("{}\n", encoding="utf-8")
    return path


def harness(connection, extra):
    return (
        f". {quote(SCRIPT)}; $configPath={quote(connection)}; "
        + r"""
$script:Calls=[Collections.Generic.List[string]]::new()
$script:State='ready'; $script:Failure=''; $script:ExpectedConfig=$configPath
function Write-Host { param([Parameter(ValueFromRemainingArguments=$true)]$Object) }
function Record-Step { param([string]$Step)
    $script:Calls.Add($Step)
    if($script:Failure -ceq $Step){throw 'private-fixture-value-must-not-escape'}
}
function Get-SparkConnection { param([string]$ConfigPath)
    if($ConfigPath -cne $script:ExpectedConfig){throw 'unexpected_config'}
    Record-Step 'config'
    return [pscustomobject]@{host='192.168.137.2';user='lab_nvidia1';identity_file='C:\fixture\identity';known_hosts='C:\fixture\known';host_key_alias='10.19.57.150';local_port=18090;remote_port=8090}
}
function Wait-SparkEthernet { param([string]$HostAddress,[int]$TimeoutSeconds=30)
    if($HostAddress -cne '192.168.137.2' -or $TimeoutSeconds -ne 30){throw 'unexpected_ethernet_arguments'}
    Record-Step 'ethernet'
}
function Ensure-LocalDockerDesktop { param([int]$TimeoutSeconds=120)
    if($TimeoutSeconds -ne 120){throw 'unexpected_docker_arguments'}
    Record-Step 'docker'
}
function Start-PreparedSparkRuntime { param($Connection)
    if($Connection.host -cne '192.168.137.2' -or $Connection.user -cne 'lab_nvidia1' -or @($Connection.PSObject.Properties.Name).Count -ne 7){throw 'unexpected_remote_arguments'}
    Record-Step 'remote'
}
function Get-SparkTunnelStatus { param([string]$ConfigPath)
    if($ConfigPath -cne $script:ExpectedConfig){throw 'unexpected_config'}
    Record-Step 'status'
    return [pscustomobject]@{status=$script:State;pid=246810}
}
function Stop-SparkTunnel { param([string]$ConfigPath)
    if($ConfigPath -cne $script:ExpectedConfig){throw 'unexpected_config'}
    Record-Step 'stop'
    return [pscustomobject]@{status='stopped';pid=$null}
}
function Start-SparkTunnel { param([string]$ConfigPath)
    if($ConfigPath -cne $script:ExpectedConfig){throw 'unexpected_config'}
    Record-Step 'start'
    return [pscustomobject]@{status='ready';pid=246810}
}
function Start-SparkWebApplication { param([string]$ConfigPath)
    if($ConfigPath -cne $script:ExpectedConfig){throw 'unexpected_config'}
    Record-Step 'app'
    return 'http://127.0.0.1:8081'
}
function Wait-SparkWebReady { param([string]$Url,[int]$TimeoutSeconds=45)
    if($Url -cne 'http://127.0.0.1:8081' -or $TimeoutSeconds -ne 45){throw 'unexpected_http_arguments'}
    Record-Step 'http'
}
function Open-SparkApplication { param([string]$Url)
    if($Url -cne 'http://127.0.0.1:8081'){throw 'unexpected_browser_arguments'}
    Record-Step 'browser'
}
"""
        + extra
    )


def test_dot_source_is_inert_and_has_no_result():
    assert SCRIPT.exists(), "connection launcher is missing"
    result = invoke(
        "function Start-Process { throw 'unexpected_process' }; "
        "function Get-SparkConnection { throw 'unexpected_connection' }; "
        f"$result=@(. {quote(SCRIPT)}); "
        "@{count=$result.Count;controller=[bool](Get-Command Invoke-SparkConnection -ErrorAction SilentlyContinue)}|ConvertTo-Json -Compress"
    )
    assert result == {"count": 0, "controller": True}


def test_source_is_utf8_bom_for_windows_powershell_file_execution():
    assert SCRIPT.read_bytes().startswith(b"\xef\xbb\xbf")


@pytest.mark.parametrize("state", ["ready", "stopped", "unavailable"])
def test_full_flow_order_and_owned_reconnect(connection, state):
    result = invoke(
        harness(
            connection,
            f"$script:State={quote(state)}; "
            "$result=@(Invoke-SparkConnection -ConfigPath $configPath); "
            "@{calls=@($script:Calls);result=$result}|ConvertTo-Json -Depth 5 -Compress",
        )
    )
    expected = ["config", "ethernet", "docker", "remote", "status"]
    if state == "unavailable":
        expected.append("stop")
    assert result["calls"] == expected + ["start", "app", "http", "browser"]
    assert result["result"] == [
        {"status": "ready", "url": "http://127.0.0.1:8081", "host": "192.168.137.2"}
    ]


def test_no_browser_returns_ready_and_does_not_open_application(connection):
    result = invoke(
        harness(
            connection,
            "$result=Invoke-SparkConnection -ConfigPath $configPath -NoBrowser; "
            "@{calls=@($script:Calls);result=$result}|ConvertTo-Json -Depth 5 -Compress",
        )
    )
    assert result["result"]["status"] == "ready"
    assert result["calls"][-1] == "http"
    assert "browser" not in result["calls"]


@pytest.mark.parametrize(
    ("stage", "error"),
    [
        ("config", "spark_start_config"),
        ("ethernet", "spark_start_ethernet"),
        ("docker", "spark_start_docker"),
        ("remote", "spark_start_remote"),
        ("status", "spark_start_tunnel"),
        ("start", "spark_start_tunnel"),
        ("app", "spark_start_application"),
        ("http", "spark_start_web"),
        ("browser", "spark_start_browser"),
    ],
)
def test_failed_stage_is_sanitized_and_stops_all_dependent_work(connection, stage, error):
    result = invoke(
        harness(
            connection,
            f"$script:Failure={quote(stage)}; "
            "try{Invoke-SparkConnection -ConfigPath $configPath}catch{"
            "@{error=$_.Exception.Message;calls=@($script:Calls)}|ConvertTo-Json -Compress}",
        )
    )
    assert result["calls"][-1] == stage
    assert result["error"] == error
    assert "private-fixture" not in result["error"]
    assert "stop" not in result["calls"]
    assert "browser" not in result["calls"] or stage == "browser"


def test_foreign_tunnel_state_is_never_stopped_or_replaced(connection):
    result = invoke(
        harness(
            connection,
            "function Get-SparkTunnelStatus { param([string]$ConfigPath) Record-Step 'status'; throw 'spark_tunnel_state_mismatch' }; "
            "try{Invoke-SparkConnection -ConfigPath $configPath}catch{"
            "@{error=$_.Exception.Message;calls=@($script:Calls)}|ConvertTo-Json -Compress}",
        )
    )
    assert result["calls"] == ["config", "ethernet", "docker", "remote", "status"]
    assert result["error"] == "spark_start_tunnel"


def test_existing_lock_prevents_starting_runtime(connection):
    result = invoke(
        harness(
            connection,
            "$lockPath=[IO.Path]::ChangeExtension($configPath,'start.lock'); "
            "$held=[IO.File]::Open($lockPath,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None); "
            "try{try{Invoke-SparkConnection -ConfigPath $configPath}catch{"
            "@{error=$_.Exception.Message;calls=@($script:Calls)}|ConvertTo-Json -Compress}}finally{$held.Dispose()}",
        )
    )
    assert result["error"] == "spark_start_already_running"
    assert result["calls"] == ["config"]


@pytest.mark.parametrize("failure", ["", "http"])
def test_lock_is_released_after_success_and_failure(connection, failure):
    result = invoke(
        harness(
            connection,
            f"$script:Failure={quote(failure)}; "
            "try{$null=Invoke-SparkConnection -ConfigPath $configPath -NoBrowser}catch{}; "
            "$lockPath=[IO.Path]::ChangeExtension($configPath,'start.lock'); "
            "$held=[IO.File]::Open($lockPath,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None); "
            "try{@{length=$held.Length;calls=@($script:Calls)}|ConvertTo-Json -Compress}finally{$held.Dispose()}",
        )
    )
    assert result["length"] == 0
    assert result["calls"][-1] == "http"


def test_lock_remains_exclusive_through_all_side_effects(connection):
    result = invoke(
        harness(
            connection,
            "function Record-Step { param([string]$Step) "
            "$script:Calls.Add($Step); if($Step -ne 'config'){"
            "$lockPath=[IO.Path]::ChangeExtension($script:ExpectedConfig,'start.lock'); "
            "$unexpected=$null; try{$unexpected=[IO.File]::Open($lockPath,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)}catch [IO.IOException]{}; "
            "if($unexpected){$unexpected.Dispose();throw 'lock_not_held'} }}; "
            "$result=Invoke-SparkConnection -ConfigPath $configPath; "
            "@{status=$result.status;calls=@($script:Calls)}|ConvertTo-Json -Compress",
        )
    )
    assert result["status"] == "ready"
    assert result["calls"][-1] == "browser"


def test_owned_tunnel_stop_failure_prevents_replacement(connection):
    result = invoke(
        harness(
            connection,
            "$script:State='unavailable'; $script:Failure='stop'; "
            "try{Invoke-SparkConnection -ConfigPath $configPath}catch{"
            "@{error=$_.Exception.Message;calls=@($script:Calls)}|ConvertTo-Json -Compress}",
        )
    )
    assert result["calls"] == ["config", "ethernet", "docker", "remote", "status", "stop"]
    assert result["error"] == "spark_start_tunnel"


@pytest.mark.parametrize(
    ("override", "expected"),
    [
        ("", "ready"),
        ("$script:Route.NextHop='192.168.137.254'", "spark_start_ethernet"),
        ("$script:Source.InterfaceIndex=20", "spark_start_ethernet"),
        ("$script:Adapter.Status='Disconnected'", "spark_start_ethernet"),
        ("$script:Adapter.PhysicalMediaType='802.11'", "spark_start_ethernet"),
        ("$script:Adapter.HardwareInterface=$false", "spark_start_ethernet"),
        ("$script:Adapter.Virtual=$true", "spark_start_ethernet"),
    ],
)
def test_real_route_guard_requires_on_link_physical_ethernet(override, expected):
    result = invoke(
        f". {quote(SCRIPT)}; "
        + r"""
$script:Route=[pscustomobject]@{DestinationPrefix='192.168.137.0/24';NextHop='0.0.0.0';InterfaceIndex=8}
$script:Source=[pscustomobject]@{IPAddress='192.168.137.1';InterfaceIndex=8}
$script:Adapter=[pscustomobject]@{Status='Up';HardwareInterface=$true;Virtual=$false;PhysicalMediaType='802.3'}
function Find-NetRoute { [CmdletBinding()]param([string]$RemoteIPAddress)
    if($RemoteIPAddress -cne '192.168.137.2'){throw 'unexpected_destination'}
    return @($script:Route,$script:Source)
}
function Get-NetAdapter { [CmdletBinding()]param([int]$InterfaceIndex)
    if($InterfaceIndex -ne 8){throw 'unexpected_adapter'}
    return $script:Adapter
}
function Start-Sleep { param([int]$Milliseconds) throw 'unexpected_sleep' }
"""
        + override
        + "; try{Wait-SparkEthernet -HostAddress '192.168.137.2' -TimeoutSeconds 0; @{status='ready'}|ConvertTo-Json -Compress}catch{@{status=$_.Exception.Message}|ConvertTo-Json -Compress}"
    )
    assert result["status"] == expected


def docker_harness(extra):
    return (
        f". {quote(SCRIPT)}; "
        + r"""
$env:DOCKER_HOST=''
$script:Calls=[Collections.Generic.List[string]]::new()
$script:Endpoint='npipe:////./pipe/dockerDesktopLinuxEngine'
$script:Engine='linux'; $script:Failures=0; $script:StartExitCode=0; $script:ProbeTimeouts=0
function Invoke-StartupNative { param([string]$FilePath,[string[]]$Arguments,[string]$InputText='',[int]$TimeoutSeconds=15)
    if($FilePath -notlike '*docker.exe' -or $InputText){throw 'unexpected_native_call'}
    $command=$Arguments -join ' '
    $script:Calls.Add($command)
    switch($command){
        'context inspect --format {{.Endpoints.docker.Host}}' {return [pscustomobject]@{ExitCode=0;Stdout=$script:Endpoint}}
        'info --format {{.OSType}}' {
            if($TimeoutSeconds -ne 5){throw 'unbounded_probe'}
            if($script:ProbeTimeouts -gt 0){$script:ProbeTimeouts--;throw 'spark_start_native_failed'}
            if($script:Failures -gt 0){$script:Failures--;return [pscustomobject]@{ExitCode=1;Stdout=''}}
            return [pscustomobject]@{ExitCode=0;Stdout=$script:Engine}
        }
        'desktop start --detach --timeout 15' {
            if($TimeoutSeconds -ne 20){throw 'unbounded_desktop_start'}
            return [pscustomobject]@{ExitCode=$script:StartExitCode;Stdout=''}
        }
        default {throw 'unexpected_docker_operation'}
    }
}
function Start-Sleep { param([int]$Milliseconds)
    if($Milliseconds -ne 1000){throw 'unexpected_poll_interval'}
}
"""
        + extra
    )


@pytest.mark.parametrize(
    "endpoint",
    ["tcp://192.168.137.2:2375", "ssh://lab_nvidia1@192.168.137.2", "npipe:////./pipe/otherEngine"],
)
def test_docker_endpoint_guard_never_starts_desktop_for_another_daemon(endpoint):
    result = invoke(
        docker_harness(
            f"$script:Endpoint={quote(endpoint)}; "
            "try{Ensure-LocalDockerDesktop -TimeoutSeconds 0}catch{"
            "@{error=$_.Exception.Message;calls=@($script:Calls)}|ConvertTo-Json -Compress}"
        )
    )
    assert result == {
        "error": "spark_start_docker_endpoint",
        "calls": ["context inspect --format {{.Endpoints.docker.Host}}"],
    }


def test_docker_host_override_is_rejected_before_native_calls():
    result = invoke(
        docker_harness(
            "$env:DOCKER_HOST='tcp://192.168.137.2:2375'; "
            "try{Ensure-LocalDockerDesktop -TimeoutSeconds 0}catch{"
            "@{error=$_.Exception.Message;calls=@($script:Calls)}|ConvertTo-Json -Compress}"
        )
    )
    assert result == {"error": "spark_start_docker_endpoint", "calls": []}


def test_running_linux_docker_does_not_restart_or_launch_desktop():
    result = invoke(
        docker_harness(
            "Ensure-LocalDockerDesktop; @{calls=@($script:Calls)}|ConvertTo-Json -Compress"
        )
    )
    assert result["calls"] == [
        "context inspect --format {{.Endpoints.docker.Host}}",
        "info --format {{.OSType}}",
    ]


def test_stopped_docker_is_started_once_then_polled_without_reset():
    result = invoke(
        docker_harness(
            "$script:Failures=2; Ensure-LocalDockerDesktop; "
            "@{calls=@($script:Calls)}|ConvertTo-Json -Compress"
        )
    )
    assert result["calls"] == [
        "context inspect --format {{.Endpoints.docker.Host}}",
        "info --format {{.OSType}}",
        "desktop start --detach --timeout 15",
        "info --format {{.OSType}}",
        "info --format {{.OSType}}",
    ]


def test_slow_docker_probe_does_not_abort_the_desktop_startup_window():
    result = invoke(
        docker_harness(
            "$script:ProbeTimeouts=1; Ensure-LocalDockerDesktop; "
            "@{calls=@($script:Calls)}|ConvertTo-Json -Compress"
        )
    )
    assert result["calls"] == [
        "context inspect --format {{.Endpoints.docker.Host}}",
        "info --format {{.OSType}}",
        "desktop start --detach --timeout 15",
        "info --format {{.OSType}}",
    ]


def test_failed_desktop_launch_does_not_attempt_reset_or_engine_switch():
    result = invoke(
        docker_harness(
            "$script:Failures=1; $script:StartExitCode=1; try{Ensure-LocalDockerDesktop}catch{"
            "@{error=$_.Exception.Message;calls=@($script:Calls)}|ConvertTo-Json -Compress}"
        )
    )
    assert result["error"] == "spark_start_docker_launch"
    assert result["calls"][-1] == "desktop start --detach --timeout 15"
    assert len(result["calls"]) == 3


def test_wrong_docker_engine_is_rejected_without_switching_it():
    result = invoke(
        docker_harness(
            "$script:Engine='windows'; try{Ensure-LocalDockerDesktop}catch{"
            "@{error=$_.Exception.Message;calls=@($script:Calls)}|ConvertTo-Json -Compress}"
        )
    )
    assert result["error"] == "spark_start_docker_engine"
    assert len(result["calls"]) == 2


def test_docker_readiness_is_bounded_when_desktop_does_not_come_up():
    result = invoke(
        docker_harness(
            "$script:Failures=10; try{Ensure-LocalDockerDesktop -TimeoutSeconds 0}catch{"
            "@{error=$_.Exception.Message;calls=@($script:Calls)}|ConvertTo-Json -Compress}"
        )
    )
    assert result["error"] == "spark_start_docker_timeout"
    assert result["calls"][-1] == "desktop start --detach --timeout 15"
    assert len(result["calls"]) == 3


def test_native_process_preserves_arguments_stdin_and_hides_stderr():
    binary = ROOT / "app/backend/.venv/Scripts/python.exe"
    arguments = ["C:\\path with spaces\\", 'embedded "quote"', "a&b", "$name"]
    code = "import json,sys; print(json.dumps({'args':sys.argv[1:],'input':sys.stdin.read()})); sys.stderr.write('private-native-error')"
    result = invoke(
        f". {quote(SCRIPT)}; "
        f"$result=Invoke-StartupNative -FilePath {quote(binary)} -Arguments @('-c',{quote(code)},"
        + ",".join(quote(argument) for argument in arguments)
        + ") -InputText 'fixture input' -TimeoutSeconds 3; "
        "$result | ConvertTo-Json -Compress"
    )
    assert result["ExitCode"] == 0
    assert json.loads(result["Stdout"]) == {"args": arguments, "input": "fixture input"}
    assert set(result) == {"ExitCode", "Stdout"}


def test_native_process_timeout_terminates_only_the_launched_process(tmp_path):
    binary = ROOT / "app/backend/.venv/Scripts/python.exe"
    pid_path = tmp_path / "launched.pid"
    code = "import os,pathlib,sys,time; pathlib.Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(30)"
    result = invoke(
        f". {quote(SCRIPT)}; "
        f"try{{Invoke-StartupNative -FilePath {quote(binary)} -Arguments @('-c',{quote(code)},{quote(pid_path)}) -TimeoutSeconds 1}}catch{{"
        "$errorCode=$_.Exception.Message; "
        f"$ownedPid=[int][IO.File]::ReadAllText({quote(pid_path)}); "
        "@{error=$errorCode;alive=[bool](Get-Process -Id $ownedPid -ErrorAction SilentlyContinue)}|ConvertTo-Json -Compress}"
    )
    assert result == {"error": "spark_start_native_failed", "alive": False}


@pytest.mark.parametrize(
    "shell", [value for name in ("powershell.exe", "pwsh.exe") if (value := shutil.which(name))]
)
@pytest.mark.parametrize(
    "encoding", ["[Text.UTF8Encoding]::new($true)", "[Text.Encoding]::GetEncoding(857)"]
)
def test_native_stdin_is_utf8_without_bom_independent_of_console_encoding(
    shell, encoding, tmp_path
):
    binary = ROOT / "app/backend/.venv/Scripts/python.exe"
    payload = "Türkçe ses: ıİşŞğĞ\n"
    code = "import sys; print(sys.stdin.buffer.read().hex())"
    result = invoke(
        f". {quote(SCRIPT)}; $original=[Console]::InputEncoding; try {{ "
        f"[Console]::InputEncoding={encoding}; "
        "$expected=[Console]::InputEncoding; "
        "function Assert-EncodingRestored { "
        "if ([Console]::InputEncoding.CodePage -ne $expected.CodePage -or "
        "[Convert]::ToBase64String([Console]::InputEncoding.GetPreamble()) -cne "
        "[Convert]::ToBase64String($expected.GetPreamble())) { throw 'console_encoding_changed' } }; "
        f"$result=Invoke-StartupNative -FilePath {quote(binary)} -Arguments @('-c',{quote(code)}) "
        f"-InputText {quote(payload)} -TimeoutSeconds 3; "
        "Assert-EncodingRestored; "
        f"try {{ Invoke-StartupNative -FilePath {quote(tmp_path / 'absent.exe')} }} "
        "catch { if ($_.Exception.Message -cne 'spark_start_native_failed') { throw } }; "
        "Assert-EncodingRestored; "
        "$result | ConvertTo-Json -Compress } finally { [Console]::InputEncoding=$original }",
        shell=shell,
    )
    assert result == {"ExitCode": 0, "Stdout": payload.encode("utf-8").hex() + "\r\n"}
