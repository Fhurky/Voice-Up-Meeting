param(
    [ValidateSet('Auto', 'Local', 'Spark')][string]$Mode = 'Auto',
    [string]$SparkConfigPath = (Join-Path $PSScriptRoot '../outputs/spark-access/connection.json')
)

function Invoke-LocalDocker {
    param([string[]]$Arguments, [ValidateRange(1, 180)][int]$TimeoutSeconds = 15)
    # Capture both native streams directly: PowerShell 5.1 promotes redirected
    # native stderr to terminating errors even when the caller needs to retry.
    $process = [Diagnostics.Process]::new()
    try {
        $info = [Diagnostics.ProcessStartInfo]::new()
        $info.FileName = (Get-Command docker -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
        $info.Arguments = (($Arguments | ForEach-Object {
            $escaped = [regex]::Replace($_, '(\\*)"', '$1$1\"')
            '"' + [regex]::Replace($escaped, '(\\+)$', '$1$1') + '"'
        }) -join ' ')
        $info.UseShellExecute = $false
        $info.CreateNoWindow = $true
        $info.RedirectStandardOutput = $true
        $info.RedirectStandardError = $true
        $info.WorkingDirectory = $PWD.ProviderPath
        # Prevent Compose's project-name fallback, including values in dotenv.
        $info.EnvironmentVariables['COMPOSE_PROJECT_NAME'] = ''
        $process.StartInfo = $info
        $null = $process.Start()
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
            # Docker CLI may own a Compose plugin child; terminate only this tree.
            if ($env:OS -eq 'Windows_NT') {
                $killer = [Diagnostics.Process]::new()
                try {
                    $killer.StartInfo = [Diagnostics.ProcessStartInfo]::new()
                    $killer.StartInfo.FileName = Join-Path $env:SystemRoot 'System32/taskkill.exe'
                    $killer.StartInfo.Arguments = "/PID $($process.Id) /T /F"
                    $killer.StartInfo.UseShellExecute = $false
                    $killer.StartInfo.CreateNoWindow = $true
                    $killer.StartInfo.RedirectStandardOutput = $true
                    $killer.StartInfo.RedirectStandardError = $true
                    $null = $killer.Start()
                    if (-not $killer.WaitForExit(3000)) { $killer.Kill() }
                } finally { $killer.Dispose() }
            }
            if (-not $process.HasExited) { $process.Kill() }
            throw 'voiceup_docker_timeout'
        }
        if (-not [Threading.Tasks.Task]::WaitAll([Threading.Tasks.Task[]]@($stdout, $stderr), 1000)) {
            throw 'voiceup_docker_timeout'
        }
        return [pscustomobject]@{ExitCode=$process.ExitCode; Stdout=$stdout.Result}
    } catch {
        if ($_.Exception.Message -eq 'voiceup_docker_timeout') { throw }
        throw 'voiceup_docker_invocation_failed'
    } finally { $process.Dispose() }
}

$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$infraPath = Join-Path $projectRoot 'app/infra'
$modePath = Join-Path $projectRoot 'outputs/local-runtime-mode.txt'
if ($Mode -eq 'Auto') {
    $Mode = 'Local'
    if (Test-Path -LiteralPath $modePath) {
        $savedMode = [IO.File]::ReadAllText($modePath).Trim()
        if ($savedMode -notin @('local', 'spark')) { throw 'Kayıtlı çalışma modu geçersiz.' }
        $Mode = $savedMode
    }
}
if (-not (Test-Path -LiteralPath (Join-Path $infraPath '.env'))) {
    throw 'Yerel ayarlar eksik. docs/LOCAL_PILOT.md kurulum adımlarını uygulayın.'
}
if ($Mode -eq 'Local' -and -not (Test-Path -LiteralPath (Join-Path $projectRoot 'models/speaker-pilot/manifest.json'))) {
    throw 'Doğrulanmış model paketi eksik. scripts/package-speaker-model.py komutunu çalıştırın.'
}
if ($Mode -eq 'Spark') {
    if ($env:COMPOSE_PROFILES) { throw 'Spark modunda COMPOSE_PROFILES boş olmalıdır.' }
    if ($env:COMPOSE_PROJECT_NAME) { throw 'Spark modunda COMPOSE_PROJECT_NAME boş olmalıdır.' }
    $tunnel = & (Join-Path $PSScriptRoot 'spark-tunnel.ps1') -Action Start -ConfigPath $SparkConfigPath
    if ($tunnel.status -ne 'ready') { throw 'Spark model tüneli hazır değil.' }
}
Push-Location -LiteralPath $projectRoot
try {
    $composeArgs = @('compose', '--project-directory', 'app/infra', '-p', 'voiceup',
        '-f', 'app/infra/docker-compose.local.yml', '-f', 'app/infra/docker-compose.observability.yml')
    if ($Mode -eq 'Spark') { $composeArgs += @('-f', 'app/infra/docker-compose.spark.yml') }
    # Capture resolved configuration without printing its secret-bearing environment blocks.
    $configuration = Invoke-LocalDocker -Arguments ($composeArgs + @('config', '--format', 'json'))
    if ($configuration.ExitCode -ne 0) { throw 'VoiceUp Compose ayarları çözümlenemedi.' }
    try { $resolved = $configuration.Stdout | ConvertFrom-Json } catch { throw 'VoiceUp Compose ayarları geçersiz.' }
    if ($Mode -eq 'Spark' -and $resolved.services.PSObject.Properties.Name -contains 'inference') {
        throw 'Spark ayarlarında yerel model etkin; Compose profil ayarlarını kaldırın.'
    }
    $publishedPort = [int]$resolved.services.nginx.ports[0].published
    if ($publishedPort -lt 1 -or $publishedPort -gt 65535) { throw 'VoiceUp HTTP portu geçersiz.' }
    # Persist selected intent after preflight, before any partial Compose change.
    # Readiness is checked below; a failed cutover must never select Local next time.
    [IO.Directory]::CreateDirectory((Split-Path $modePath -Parent)) | Out-Null
    [IO.File]::WriteAllText($modePath, ($Mode.ToLowerInvariant() + "`n"), [Text.UTF8Encoding]::new($false))
    $started = Invoke-LocalDocker -Arguments ($composeArgs + @('up', '-d', '--no-build', '--pull', 'never')) -TimeoutSeconds 180
    if ($started.ExitCode -ne 0) { throw 'VoiceUp servisleri başlatılamadı; seçili çalışma modu korundu.' }
    if ($Mode -eq 'Spark') {
        # The unpublished proxy must reach the expected GPU model before stopping local inference.
        $proxyReady = $false
        $timer = [Diagnostics.Stopwatch]::StartNew()
        do {
            $remaining = [Math]::Min(5, [Math]::Floor(30 - $timer.Elapsed.TotalSeconds))
            if ($remaining -lt 1) { break }
            $probe = $null
            try {
                $probe = Invoke-LocalDocker -Arguments ($composeArgs + @('exec', '-T', 'nginx', 'wget', '-qO-', '-T', '3', 'http://127.0.0.1:9080/ready')) -TimeoutSeconds $remaining
            } catch { $probe = $null }
            if ($null -ne $probe -and $probe.ExitCode -eq 0) {
                try {
                    $ready = $probe.Stdout | ConvertFrom-Json
                    $proxyReady = ($ready.ready -is [bool] -and $ready.ready -eq $true -and $ready.device -ceq 'cuda:0' -and
                        ($ready.dimensions -is [int] -or $ready.dimensions -is [long]) -and
                        $ready.dimensions -eq 192 -and $ready.model_id -ceq 'speechbrain/spkrec-ecapa-voxceleb' -and
                        $ready.model_revision -ceq '0f99f2d0ebe89ac095bcc5903c4dd8f72b367286')
                } catch { $proxyReady = $false }
            }
            if (-not $proxyReady) { Start-Sleep -Milliseconds 500 }
        } until ($proxyReady -or $timer.Elapsed.TotalSeconds -ge 30)
        if (-not $proxyReady) { throw 'Spark özel bağlantısı doğrulanamadı; Spark seçimi korundu, yerel modele dönüş yapılmadı.' }
        # Compose can replace backend/frontend while nginx retains their old resolved IPs.
        # Validate the active Spark config, including its private listener, before a graceful reload.
        $nginxReloadCommand = 'set -eu; set -- /tmp/voiceup-spark.*/nginx.conf; [ "$#" -eq 1 ]; [ -f "$1" ]; nginx -t -c "$1"; nginx -s reload -c "$1"'
        $reloaded = Invoke-LocalDocker -Arguments ($composeArgs + @('exec', '-T', 'nginx', 'sh', '-c', $nginxReloadCommand)) -TimeoutSeconds 15
        if ($reloaded.ExitCode -ne 0) { throw 'VoiceUp nginx ayarları yeniden yüklenemedi; Spark seçimi korundu.' }
        $stopped = Invoke-LocalDocker -Arguments ($composeArgs + @('stop', 'inference')) -TimeoutSeconds 30
        if ($stopped.ExitCode -ne 0) { throw 'Yerel model servisi durdurulamadı; Spark seçimi korundu.' }
    }
    Write-Output "VoiceUp: http://127.0.0.1:$publishedPort"
    Write-Output ("Model modu: " + $Mode.ToLowerInvariant())
    Write-Output 'Servis durumunu kontrol etmek için: bash scripts/stack.sh ps'
} finally {
    Pop-Location
}
