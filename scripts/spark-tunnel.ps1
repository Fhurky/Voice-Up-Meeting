#requires -Version 5.1
param(
    [ValidateSet('Start', 'Stop', 'Status')][string]$Action,
    [string]$ConfigPath
)

$script:SparkDefaultConfig = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../outputs/spark-access/connection.json'))

function Get-SparkSafePath {
    param([string]$Path, [switch]$RequireFile)
    if (-not $Path -or $Path -notmatch '^[A-Za-z]:[\\/]') { throw 'spark_tunnel_invalid_config' }
    $full = [IO.Path]::GetFullPath($Path)
    $current = $full
    while ($current) {
        if (Test-Path -LiteralPath $current) {
            $item = Get-Item -LiteralPath $current -Force -ErrorAction Stop
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'spark_tunnel_unsafe_path' }
        }
        $current = [IO.Path]::GetDirectoryName($current)
    }
    if ($RequireFile -and -not [IO.File]::Exists($full)) { throw 'spark_tunnel_invalid_config' }
    return $full
}

function Read-SparkJson {
    param([string]$Path, [int]$MaximumBytes)
    $safe = Get-SparkSafePath -Path $Path -RequireFile
    if ((Get-Item -LiteralPath $safe).Length -gt $MaximumBytes) { throw 'spark_tunnel_invalid_config' }
    $bytes = [IO.File]::ReadAllBytes($safe)
    try {
        $text = [Text.UTF8Encoding]::new($false, $true).GetString($bytes).TrimStart([char]0xFEFF)
        $jsonArguments = @{ErrorAction='Stop'}
        # Preserve the exact timestamp used to prove process ownership across PowerShell engines.
        if ((Get-Command ConvertFrom-Json -CommandType Cmdlet).Parameters.ContainsKey('DateKind')) {
            $jsonArguments.DateKind = 'String'
        }
        $value = $text | ConvertFrom-Json @jsonArguments
    } catch { throw 'spark_tunnel_invalid_config' }
    return [pscustomobject]@{Bytes=$bytes; Text=$text; Value=$value}
}

function Get-SparkDigest {
    param([byte[]]$Bytes)
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($algorithm.ComputeHash($Bytes))).Replace('-', '').ToLowerInvariant() }
    finally { $algorithm.Dispose() }
}

function ConvertTo-SparkNativeArgument {
    param([string]$Value)
    $escaped = [regex]::Replace($Value, '(\\*)"', '$1$1\"')
    return '"' + [regex]::Replace($escaped, '(\\+)$', '$1$1') + '"'
}

function Split-SparkCommandLine {
    param([string]$CommandLine)
    if (-not ('VoiceUp.SparkCommandLine' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
namespace VoiceUp {
    public static class SparkCommandLine {
        [DllImport("shell32.dll", SetLastError=true)]
        static extern IntPtr CommandLineToArgvW([MarshalAs(UnmanagedType.LPWStr)] string text, out int count);
        [DllImport("kernel32.dll")] static extern IntPtr LocalFree(IntPtr memory);
        public static string[] Split(string text) {
            int count; IntPtr memory = CommandLineToArgvW(text, out count);
            if (memory == IntPtr.Zero) throw new InvalidOperationException();
            try {
                string[] result = new string[count];
                for (int i=0; i<count; i++) result[i] = Marshal.PtrToStringUni(Marshal.ReadIntPtr(memory, i*IntPtr.Size));
                return result;
            } finally { LocalFree(memory); }
        }
    }
}
'@ -ErrorAction Stop
    }
    return [VoiceUp.SparkCommandLine]::Split($CommandLine)
}

function Get-SparkTunnelContext {
    param([string]$ConfigPath)
    try {
        if (-not $ConfigPath) { $ConfigPath = $script:SparkDefaultConfig }
        $path = Get-SparkSafePath -Path $ConfigPath -RequireFile
        $document = Read-SparkJson -Path $path -MaximumBytes 16384
        $config = $document.Value
        $required = @('host', 'user', 'identity_file', 'known_hosts', 'host_key_alias', 'local_port', 'remote_port')
        $names = @($config.PSObject.Properties.Name)
        if ($names.Count -ne 7 -or @($names | Where-Object { $required -cnotcontains $_ }).Count) { throw 'spark_tunnel_invalid_config' }
        $keys = @([regex]::Matches($document.Text, '(?<!\\)"([a-z_]+)"\s*:') | ForEach-Object { $_.Groups[1].Value })
        if ($keys.Count -ne 7 -or @($keys | Select-Object -Unique).Count -ne 7) { throw 'spark_tunnel_invalid_config' }
        if ($config.host -isnot [string] -or $config.user -isnot [string] -or $config.host_key_alias -isnot [string]) { throw 'spark_tunnel_invalid_config' }
        $address = $null
        if (-not [Net.IPAddress]::TryParse($config.host, [ref]$address) -or $address.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork -or $address.ToString() -cne $config.host) { throw 'spark_tunnel_invalid_config' }
        $octets = $address.GetAddressBytes()
        if (-not ($octets[0] -eq 10 -or ($octets[0] -eq 172 -and $octets[1] -ge 16 -and $octets[1] -le 31) -or ($octets[0] -eq 192 -and $octets[1] -eq 168))) { throw 'spark_tunnel_invalid_config' }
        if ($config.user -cnotmatch '^[a-z_][a-z0-9_-]{0,31}$' -or $config.host_key_alias -cnotmatch '^[A-Za-z0-9][A-Za-z0-9._:-]{0,252}$') { throw 'spark_tunnel_invalid_config' }
        if (($config.local_port -isnot [int] -and $config.local_port -isnot [long]) -or $config.local_port -ne 18090 -or ($config.remote_port -isnot [int] -and $config.remote_port -isnot [long]) -or $config.remote_port -ne 8090) { throw 'spark_tunnel_invalid_config' }
        foreach ($field in @('identity_file', 'known_hosts')) {
            if ($config.$field -isnot [string]) { throw 'spark_tunnel_invalid_config' }
            $config.$field = Get-SparkSafePath -Path $config.$field -RequireFile
        }
        if ((Get-Item -LiteralPath $config.known_hosts).Length -gt 1048576) { throw 'spark_tunnel_invalid_config' }
        $pinned = $false
        foreach ($line in [IO.File]::ReadAllLines($config.known_hosts)) {
            $parts = $line.Trim() -split '\s+'
            if ($parts.Count -ge 3 -and (@($parts[0] -split ',') -ccontains $config.host_key_alias) -and ($parts[1] -cmatch '^(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp(256|384|521))$') -and ($parts[2] -cmatch '^[A-Za-z0-9+/]+={0,2}$')) {
                $pinned = ([Convert]::FromBase64String($parts[2]).Length -ge 32)
                if ($pinned) { break }
            }
        }
        if (-not $pinned) { throw 'spark_tunnel_host_pin_missing' }
        $sshPath = (Get-Command ssh.exe -CommandType Application -ErrorAction Stop).Source
        $sshPath = Get-SparkSafePath -Path $sshPath -RequireFile
        $arguments = @('-F', 'none', '-N', '-T', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes', '-o', 'StrictHostKeyChecking=yes', '-o', "HostKeyAlias=$($config.host_key_alias)", '-o', "UserKnownHostsFile=$($config.known_hosts)", '-o', 'ExitOnForwardFailure=yes', '-o', 'ConnectTimeout=8', '-o', 'ServerAliveInterval=10', '-o', 'ServerAliveCountMax=3', '-o', 'ForwardAgent=no', '-i', $config.identity_file, '-L', '127.0.0.1:18090:127.0.0.1:8090', "$($config.user)@$($config.host)")
        return [pscustomobject]@{
            Connection=$config; ConfigPath=$path; ConfigDigest=(Get-SparkDigest $document.Bytes)
            StatePath=([IO.Path]::Combine([IO.Path]::GetDirectoryName($path), [IO.Path]::GetFileNameWithoutExtension($path)+'.tunnel-state.json'))
            SshPath=$sshPath; Arguments=$arguments
            ArgumentString=(($arguments | ForEach-Object { ConvertTo-SparkNativeArgument $_ }) -join ' ')
        }
    } catch {
        if ($_.Exception.Message -match '^spark_tunnel_[a-z_]+$') { throw }
        throw 'spark_tunnel_invalid_config'
    }
}

function Get-SparkConnection {
    param([string]$ConfigPath)
    return (Get-SparkTunnelContext -ConfigPath $ConfigPath).Connection
}

function Read-SparkTunnelState {
    param($Context)
    $path = Get-SparkSafePath -Path $Context.StatePath
    if (-not [IO.File]::Exists($path)) {
        if (Test-Path -LiteralPath $path) { throw 'spark_tunnel_state_mismatch' }
        return $null
    }
    try {
        $state = (Read-SparkJson -Path $path -MaximumBytes 4096).Value
        $keys = @($state.PSObject.Properties.Name)
        $expected = @('schema_version', 'pid', 'start_utc', 'ssh_path', 'config_sha256')
        if ($keys.Count -ne 5 -or @($keys | Where-Object { $expected -cnotcontains $_ }).Count -or $state.schema_version -ne 1) { throw 'invalid' }
        if (($state.pid -isnot [int] -and $state.pid -isnot [long]) -or $state.pid -le 0 -or $state.pid -gt [int]::MaxValue) { throw 'invalid' }
        if ($state.start_utc -isnot [string] -or $state.start_utc -notmatch '^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{7}Z$') { throw 'invalid' }
        $null = [DateTime]::ParseExact($state.start_utc, "yyyy-MM-ddTHH:mm:ss.fffffff'Z'", [Globalization.CultureInfo]::InvariantCulture)
        if ($state.config_sha256 -cne $Context.ConfigDigest -or -not [string]::Equals($state.ssh_path, $Context.SshPath, [StringComparison]::OrdinalIgnoreCase)) { throw 'invalid' }
        return $state
    } catch { throw 'spark_tunnel_state_mismatch' }
}

function Get-SparkProcess {
    param([int]$ProcessId)
    try {
        $process = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $ProcessId" -OperationTimeoutSec 2 -ErrorAction Stop
        if (-not $process) { return $null }
        return [pscustomobject]@{pid=[int]$process.ProcessId; start_utc=$process.CreationDate.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffffff'Z'"); executable_path=$process.ExecutablePath; command_line=$process.CommandLine}
    } catch { throw 'spark_tunnel_process_inspection_failed' }
}

function Get-SparkOwnedProcess {
    param($Context, $State)
    $process = Get-SparkProcess -ProcessId $State.pid
    if (-not $process) { return $null }
    if ($process.pid -ne $State.pid -or $process.start_utc -cne $State.start_utc -or -not [string]::Equals($process.executable_path, $Context.SshPath, [StringComparison]::OrdinalIgnoreCase) -or -not $process.command_line) { throw 'spark_tunnel_state_mismatch' }
    $parts = @(Split-SparkCommandLine $process.command_line)
    if ($parts.Count -ne ($Context.Arguments.Count + 1) -or -not [string]::Equals($parts[0], $Context.SshPath, [StringComparison]::OrdinalIgnoreCase)) { throw 'spark_tunnel_state_mismatch' }
    for ($index=0; $index -lt $Context.Arguments.Count; $index++) {
        if ($parts[$index+1] -cne $Context.Arguments[$index]) { throw 'spark_tunnel_state_mismatch' }
    }
    return $process
}

function Get-SparkPortOwners {
    param([int]$LocalPort)
    try { return @(Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object LocalPort -eq $LocalPort | Select-Object -ExpandProperty OwningProcess -Unique) }
    catch { throw 'spark_tunnel_port_inspection_failed' }
}

function Invoke-SparkReadyRequest {
    param([string]$Uri, [int]$TimeoutMilliseconds)
    Add-Type -AssemblyName System.Net.Http -ErrorAction Stop
    $handler = [Net.Http.HttpClientHandler]::new()
    $handler.UseProxy = $false
    $handler.AllowAutoRedirect = $false
    $client = [Net.Http.HttpClient]::new($handler)
    $client.Timeout = [TimeSpan]::FromMilliseconds($TimeoutMilliseconds)
    $client.MaxResponseContentBufferSize = 16384
    try {
        $response = $client.GetAsync($Uri).GetAwaiter().GetResult()
        try {
            if ([int]$response.StatusCode -ne 200) { return $null }
            return ($response.Content.ReadAsStringAsync().GetAwaiter().GetResult() | ConvertFrom-Json -ErrorAction Stop)
        } finally { $response.Dispose() }
    } catch { return $null }
    finally { $client.Dispose(); $handler.Dispose() }
}

function Test-SparkReady {
    param([int]$LocalPort, [int]$TimeoutMilliseconds=2000)
    $value = Invoke-SparkReadyRequest -Uri "http://127.0.0.1:$LocalPort/ready" -TimeoutMilliseconds $TimeoutMilliseconds
    return ($null -ne $value -and $value.ready -is [bool] -and $value.ready -eq $true -and $value.model_id -ceq 'speechbrain/spkrec-ecapa-voxceleb' -and $value.model_revision -ceq '0f99f2d0ebe89ac095bcc5903c4dd8f72b367286' -and ($value.dimensions -is [int] -or $value.dimensions -is [long]) -and $value.dimensions -eq 192 -and $value.device -ceq 'cuda:0')
}

function Get-SparkMonotonicMilliseconds {
    return [double][Diagnostics.Stopwatch]::GetTimestamp() * 1000 / [Diagnostics.Stopwatch]::Frequency
}

function Stop-SparkOwnedProcess {
    param($Context, $State)
    # Keep an actual process handle while rechecking identity, preventing PID-reuse kills.
    $process = Get-Process -Id $State.pid -ErrorAction SilentlyContinue
    if (-not $process) { return }
    try {
        $null = $process.Handle
        if (-not (Get-SparkOwnedProcess -Context $Context -State $State)) { return }
        if (-not $process.HasExited) {
            $process.Kill()
            if (-not $process.WaitForExit(5000)) { throw 'spark_tunnel_stop_failed' }
        }
    } finally { $process.Dispose() }
}

function Stop-SparkLaunchedProcess {
    param($Launched)
    # This retained handle comes only from this invocation's successful Start-Process.
    if (-not $Launched.HasExited) {
        $Launched.Kill()
        if (-not $Launched.WaitForExit(5000)) { throw 'spark_tunnel_stop_failed' }
    }
}

function Remove-SparkOwnedState {
    param($Context, $State)
    $current = Read-SparkTunnelState -Context $Context
    if ($current -and $current.pid -eq $State.pid -and $current.start_utc -ceq $State.start_utc) {
        Remove-Item -LiteralPath $Context.StatePath -Force -ErrorAction Stop
    }
}

function Get-SparkTunnelStatus {
    param([string]$ConfigPath)
    $context = Get-SparkTunnelContext -ConfigPath $ConfigPath
    $state = Read-SparkTunnelState -Context $context
    if (-not $state -or -not (Get-SparkOwnedProcess -Context $context -State $state)) { return [pscustomobject]@{status='stopped'; pid=$null} }
    $owners = @(Get-SparkPortOwners -LocalPort $context.Connection.local_port)
    $ready = $owners.Count -eq 1 -and $owners[0] -eq $state.pid -and (Test-SparkReady -LocalPort $context.Connection.local_port)
    return [pscustomobject]@{status=$(if ($ready) {'ready'} else {'unavailable'}); pid=$state.pid}
}

function Start-SparkTunnel {
    param([string]$ConfigPath)
    $context = Get-SparkTunnelContext -ConfigPath $ConfigPath
    $state = Read-SparkTunnelState -Context $context
    $newProcess = $false
    $wroteState = $false
    $launched = $null
    if ($state -and -not (Get-SparkOwnedProcess -Context $context -State $state)) {
        Remove-SparkOwnedState -Context $context -State $state
        $state = $null
    }
    try {
        if (-not $state) {
            if (@(Get-SparkPortOwners -LocalPort $context.Connection.local_port).Count) { throw 'spark_tunnel_port_occupied' }
            try { $launched = Start-Process -FilePath $context.SshPath -ArgumentList $context.ArgumentString -WindowStyle Hidden -PassThru -ErrorAction Stop }
            catch { throw 'spark_tunnel_start_failed' }
            # Retain the returned process handle before any fallible CIM inspection.
            $null = $launched.Handle
            $newProcess = $true
            $process = Get-SparkProcess -ProcessId $launched.Id
            if (-not $process) { throw 'spark_tunnel_process_exited' }
            $state = [pscustomobject]@{schema_version=1; pid=[int]$launched.Id; start_utc=$process.start_utc; ssh_path=$context.SshPath; config_sha256=$context.ConfigDigest}
            $null = Get-SparkOwnedProcess -Context $context -State $state
        }
        if ($newProcess) {
            $bytes = [Text.UTF8Encoding]::new($false).GetBytes(($state | ConvertTo-Json -Compress) + "`n")
            $stream = [IO.File]::Open($context.StatePath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
            try { $stream.Write($bytes, 0, $bytes.Length); $stream.Flush() }
            finally { $stream.Dispose() }
            $wroteState = $true
        }
        $deadline = (Get-SparkMonotonicMilliseconds) + 30000
        while ((Get-SparkMonotonicMilliseconds) -lt $deadline) {
            if (-not (Get-SparkOwnedProcess -Context $context -State $state)) { throw 'spark_tunnel_process_exited' }
            $owners = @(Get-SparkPortOwners -LocalPort $context.Connection.local_port)
            if (@($owners | Where-Object { $_ -ne $state.pid }).Count) { throw 'spark_tunnel_port_occupied' }
            $remaining = [int][Math]::Min(2000, [Math]::Max(1, $deadline - (Get-SparkMonotonicMilliseconds)))
            if ($owners.Count -eq 1 -and (Test-SparkReady -LocalPort $context.Connection.local_port -TimeoutMilliseconds $remaining)) { return [pscustomobject]@{status='ready'; pid=$state.pid} }
            Start-Sleep -Milliseconds 200
        }
        throw 'spark_tunnel_readiness_timeout'
    } catch {
        $failure = if ($_.Exception.Message -match '^spark_tunnel_[a-z_]+$') {$_.Exception.Message} else {'spark_tunnel_start_failed'}
        if ($newProcess) {
            Stop-SparkLaunchedProcess -Launched $launched
            if ($wroteState) { Remove-SparkOwnedState -Context $context -State $state }
        }
        throw $failure
    } finally {
        if ($launched) { $launched.Dispose() }
    }
}

function Stop-SparkTunnel {
    param([string]$ConfigPath)
    $context = Get-SparkTunnelContext -ConfigPath $ConfigPath
    $state = Read-SparkTunnelState -Context $context
    if ($state) {
        if (Get-SparkOwnedProcess -Context $context -State $state) { Stop-SparkOwnedProcess -Context $context -State $state }
        Remove-SparkOwnedState -Context $context -State $state
    }
    return [pscustomobject]@{status='stopped'; pid=$null}
}

if ($MyInvocation.InvocationName -ne '.') {
    switch ($Action) {
        'Start' { Start-SparkTunnel -ConfigPath $ConfigPath }
        'Stop' { Stop-SparkTunnel -ConfigPath $ConfigPath }
        'Status' { Get-SparkTunnelStatus -ConfigPath $ConfigPath }
        default { throw 'spark_tunnel_action_required' }
    }
}
