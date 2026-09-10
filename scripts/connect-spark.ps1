#requires -Version 5.1
param(
    [string]$ConfigPath = (Join-Path $PSScriptRoot '../outputs/spark-access/connection.json'),
    [switch]$NoBrowser
)

$script:ConnectionProjectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
. (Join-Path $PSScriptRoot 'spark-tunnel.ps1') -ConfigPath $ConfigPath

function Invoke-StartupNative {
    param([string]$FilePath, [string[]]$Arguments, [string]$InputText = '', [int]$TimeoutSeconds = 15)
    $process = [Diagnostics.Process]::new()
    $launched = $false
    try {
        $info = [Diagnostics.ProcessStartInfo]::new()
        $info.FileName = $FilePath
        $info.Arguments = (($Arguments | ForEach-Object { ConvertTo-SparkNativeArgument $_ }) -join ' ')
        $info.UseShellExecute = $false
        $info.CreateNoWindow = $true
        $info.RedirectStandardInput = $true
        $info.RedirectStandardOutput = $true
        $info.RedirectStandardError = $true
        $info.WorkingDirectory = $script:ConnectionProjectRoot
        $process.StartInfo = $info
        $utf8 = [Text.UTF8Encoding]::new($false)
        if ($null -ne $info.PSObject.Properties['StandardInputEncoding']) {
            $info.StandardInputEncoding = $utf8
            $null = $process.Start()
            $launched = $true
        } else {
            # .NET Framework creates stdin with Console.InputEncoding and flushes its BOM immediately.
            $previousInputEncoding = [Console]::InputEncoding
            try {
                [Console]::InputEncoding = $utf8
                $null = $process.Start()
                $launched = $true
            } finally { [Console]::InputEncoding = $previousInputEncoding }
        }
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        if ($InputText -and -not $process.StandardInput.WriteAsync($InputText).Wait(5000)) {
            throw 'spark_start_native_timeout'
        }
        $process.StandardInput.Close()
        if (-not $process.WaitForExit($TimeoutSeconds * 1000)) { throw 'spark_start_native_timeout' }
        if (-not [Threading.Tasks.Task]::WaitAll([Threading.Tasks.Task[]]@($stdout, $stderr), 1000)) {
            throw 'spark_start_native_timeout'
        }
        return [pscustomobject]@{ExitCode=$process.ExitCode; Stdout=$stdout.Result}
    } catch {
        # Keep the owned process handle while terminating this invocation's tree.
        if ($launched -and -not $process.HasExited) {
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
            if (-not $process.HasExited) { $process.Kill() }
        }
        throw 'spark_start_native_failed'
    } finally { $process.Dispose() }
}

function Wait-SparkEthernet {
    param([string]$HostAddress, [int]$TimeoutSeconds = 30)
    $timer = [Diagnostics.Stopwatch]::StartNew()
    do {
        try {
            $selection = @(Find-NetRoute -RemoteIPAddress $HostAddress -ErrorAction Stop)
            $route = @($selection | Where-Object { $_.DestinationPrefix })
            $source = @($selection | Where-Object { $_.IPAddress })
            if ($route.Count -eq 1 -and $source.Count -eq 1 -and $route[0].NextHop -eq '0.0.0.0' -and
                $route[0].InterfaceIndex -eq $source[0].InterfaceIndex) {
                $adapter = Get-NetAdapter -InterfaceIndex $route[0].InterfaceIndex -ErrorAction Stop
                if ($adapter.Status -eq 'Up' -and $adapter.HardwareInterface -eq $true -and
                    $adapter.Virtual -eq $false -and [string]$adapter.PhysicalMediaType -eq '802.3') { return }
            }
        } catch { }
        if ($timer.Elapsed.TotalSeconds -ge $TimeoutSeconds) { break }
        Start-Sleep -Milliseconds 500
    } while ($true)
    throw 'spark_start_ethernet'
}

function Ensure-LocalDockerDesktop {
    param([int]$TimeoutSeconds = 120)
    if ($env:DOCKER_HOST) { throw 'spark_start_docker_endpoint' }
    $docker = (Get-Command docker.exe -CommandType Application -ErrorAction Stop).Source
    $context = Invoke-StartupNative -FilePath $docker -Arguments @('context', 'inspect', '--format', '{{.Endpoints.docker.Host}}')
    if ($context.ExitCode -ne 0 -or $context.Stdout.Trim() -cnotin @('npipe:////./pipe/dockerDesktopLinuxEngine', 'npipe:////./pipe/docker_engine')) {
        throw 'spark_start_docker_endpoint'
    }
    $launched = $false
    $timer = [Diagnostics.Stopwatch]::StartNew()
    do {
        $result = $null
        try { $result = Invoke-StartupNative -FilePath $docker -Arguments @('info', '--format', '{{.OSType}}') -TimeoutSeconds 5 } catch { }
        if ($null -ne $result -and $result.ExitCode -eq 0) {
            if ($result.Stdout.Trim() -cne 'linux') { throw 'spark_start_docker_engine' }
            return
        }
        if (-not $launched) {
            # The installed Desktop CLI launches asynchronously without resetting or switching engines.
            $started = Invoke-StartupNative -FilePath $docker -Arguments @('desktop', 'start', '--detach', '--timeout', '15') -TimeoutSeconds 20
            if ($started.ExitCode -ne 0) { throw 'spark_start_docker_launch' }
            $launched = $true
        }
        if ($timer.Elapsed.TotalSeconds -ge $TimeoutSeconds) { break }
        Start-Sleep -Milliseconds 1000
    } while ($true)
    throw 'spark_start_docker_timeout'
}

function Start-PreparedSparkRuntime {
    param($Connection)
    $source = Join-Path $script:ConnectionProjectRoot 'scripts/ensure-spark-runtime.py'
    $null = Get-SparkSafePath -Path $source -RequireFile
    $ssh = (Get-Command ssh.exe -CommandType Application -ErrorAction Stop).Source
    $arguments = @('-F', 'none', '-T', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
        '-o', 'StrictHostKeyChecking=yes', '-o', "HostKeyAlias=$($Connection.host_key_alias)",
        '-o', "UserKnownHostsFile=$($Connection.known_hosts)", '-o', 'ConnectTimeout=8',
        '-o', 'ServerAliveInterval=10', '-o', 'ServerAliveCountMax=3', '-o', 'ForwardAgent=no',
        '-i', $Connection.identity_file, "$($Connection.user)@$($Connection.host)", '/usr/bin/python3 -')
    $result = Invoke-StartupNative -FilePath $ssh -Arguments $arguments -InputText ([IO.File]::ReadAllText($source)) -TimeoutSeconds 260
    if ($result.ExitCode -ne 0) { throw 'spark_start_remote' }
    try { $ready = $result.Stdout | ConvertFrom-Json -ErrorAction Stop } catch { throw 'spark_start_remote' }
    if ($ready.status -cne 'ready') { throw 'spark_start_remote' }
}

function Start-SparkWebApplication {
    param([string]$ConfigPath)
    $output = @(& (Join-Path $script:ConnectionProjectRoot 'scripts/start-local.ps1') -Mode Spark -SparkConfigPath $ConfigPath)
    $urls = @($output | ForEach-Object { if ($_ -cmatch '^VoiceUp: (http://127\.0\.0\.1:[0-9]{1,5})$') { $Matches[1] } })
    if ($urls.Count -ne 1) { throw 'spark_start_application' }
    return $urls[0]
}

function Wait-SparkWebReady {
    param([string]$Url, [int]$TimeoutSeconds = 45)
    $uri = [Uri]$Url
    if ($uri.Scheme -cne 'http' -or $uri.Host -cne '127.0.0.1' -or $uri.UserInfo -or $uri.AbsolutePath -ne '/' -or $uri.Query -or $uri.Fragment) {
        throw 'spark_start_web'
    }
    Add-Type -AssemblyName System.Net.Http
    $handler = [Net.Http.HttpClientHandler]::new()
    $handler.UseProxy = $false
    $handler.AllowAutoRedirect = $false
    $client = [Net.Http.HttpClient]::new($handler)
    $client.Timeout = [TimeSpan]::FromSeconds(3)
    $client.MaxResponseContentBufferSize = 65536
    $timer = [Diagnostics.Stopwatch]::StartNew()
    try {
        do {
            try {
                $web = $client.GetAsync($Url).GetAwaiter().GetResult()
                try { $webReady = [int]$web.StatusCode -eq 200 } finally { $web.Dispose() }
                $api = $client.GetAsync($Url + '/api/voiceup/v1/readiness').GetAwaiter().GetResult()
                try {
                    $body = $api.Content.ReadAsStringAsync().GetAwaiter().GetResult() | ConvertFrom-Json
                    if ($webReady -and [int]$api.StatusCode -eq 200 -and $body.status -ceq 'ready') { return }
                } finally { $api.Dispose() }
            } catch { }
            if ($timer.Elapsed.TotalSeconds -ge $TimeoutSeconds) { break }
            Start-Sleep -Milliseconds 500
        } while ($true)
    } finally { $client.Dispose(); $handler.Dispose() }
    throw 'spark_start_web'
}

function Open-SparkApplication {
    param([string]$Url)
    Start-Process -FilePath $Url | Out-Null
}

function Invoke-SparkConnection {
    param([string]$ConfigPath, [switch]$NoBrowser)
    $ErrorActionPreference = 'Stop'
    $stage = 'spark_start_config'
    $lock = $null
    try {
        $connection = Get-SparkConnection -ConfigPath $ConfigPath
        $lockPath = Get-SparkSafePath -Path ([IO.Path]::ChangeExtension($ConfigPath, 'start.lock'))
        $stage = 'spark_start_already_running'
        $lock = [IO.File]::Open($lockPath, [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
        $stage = 'spark_start_ethernet'
        Write-Host '[1/5] Ethernet bağlantısı kontrol ediliyor...'
        Wait-SparkEthernet -HostAddress $connection.host -TimeoutSeconds 30
        $stage = 'spark_start_docker'
        Write-Host '[2/5] Docker Desktop hazırlanıyor...'
        Ensure-LocalDockerDesktop -TimeoutSeconds 120
        $stage = 'spark_start_remote'
        Write-Host '[3/5] Spark model servisleri hazırlanıyor...'
        Start-PreparedSparkRuntime -Connection $connection
        $stage = 'spark_start_tunnel'
        Write-Host '[4/5] Güvenli bağlantı kuruluyor...'
        $status = Get-SparkTunnelStatus -ConfigPath $ConfigPath
        if ($status.status -ceq 'unavailable') { $null = Stop-SparkTunnel -ConfigPath $ConfigPath }
        $tunnel = Start-SparkTunnel -ConfigPath $ConfigPath
        if ($tunnel.status -cne 'ready') { throw 'spark_start_tunnel' }
        $stage = 'spark_start_application'
        Write-Host '[5/5] VoiceUp başlatılıyor...'
        $url = Start-SparkWebApplication -ConfigPath $ConfigPath
        $stage = 'spark_start_web'
        Wait-SparkWebReady -Url $url -TimeoutSeconds 45
        if (-not $NoBrowser) {
            $stage = 'spark_start_browser'
            Write-Host ("VoiceUp: " + $url)
            Open-SparkApplication -Url $url
        }
        return [pscustomobject]@{status='ready'; url=$url; host=$connection.host}
    } catch { throw [InvalidOperationException]::new($stage) }
    finally { if ($null -ne $lock) { $lock.Dispose() } }
}

if ($MyInvocation.InvocationName -ne '.') {
    try {
        [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
        $result = Invoke-SparkConnection -ConfigPath $ConfigPath -NoBrowser:$NoBrowser
        Write-Host ("VoiceUp hazır: " + $result.url)
        exit 0
    } catch {
        $messages = @{
            spark_start_config='Bu bilgisayarın bağlantı ayarları eksik veya geçersiz. docs/SPARK_RUNTIME.md dosyasını kontrol edin.'
            spark_start_already_running='Başka bir VoiceUp başlatıcısı çalışıyor. Tamamlanmasını bekleyin.'
            spark_start_ethernet='Ethernet bağlantısı hazır değil. Kabloyu ve açık Spark cihazını kontrol edip tekrar çalıştırın.'
            spark_start_docker='Yerel Linux Docker motoru hazırlanamadı. Docker Desktop durumunu ve seçili bağlantıyı kontrol edin.'
            spark_start_remote='Spark erişimi veya hazırlanmış model servisi doğrulanamadı. Spark açık olmalı; SSH, Docker ve ilk kurulum dosyalarını kontrol edin.'
            spark_start_tunnel='Güvenli tünel kurulamadı. Bağlantı veya sahiplik kaydını kontrol edin; başka süreçler durdurulmadı.'
            spark_start_application='Uygulama başlatılamadı. Yerel ayarları kontrol edip tekrar çalıştırın; Spark seçimi korundu.'
            spark_start_web='Web uygulaması veya veritabanı hazır yanıtı vermedi. Servisleri kontrol edip tekrar çalıştırın.'
            spark_start_browser='VoiceUp hazır, ancak tarayıcı açılamadı. Ekrandaki uygulama adresini tarayıcıya yazın.'
        }
        $code = $_.Exception.Message
        if (-not $messages.ContainsKey($code)) { $code = 'spark_start_config' }
        Write-Host ($messages[$code]) -ForegroundColor Red
        Write-Host ("Tanı kodu: " + $code)
        exit 1
    }
}
