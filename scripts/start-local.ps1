param()
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$infraPath = Join-Path $projectRoot 'app/infra'
if (-not (Test-Path -LiteralPath (Join-Path $infraPath '.env'))) {
    throw 'Yerel ayarlar eksik. docs/LOCAL_PILOT.md kurulum adımlarını uygulayın.'
}
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'models/speaker-pilot/manifest.json'))) {
    throw 'Doğrulanmış model paketi eksik. scripts/package-speaker-model.py komutunu çalıştırın.'
}
Push-Location -LiteralPath $projectRoot
try {
    $composeArgs = @('compose', '--project-directory', 'app/infra', '-p', 'voiceup',
        '-f', 'app/infra/docker-compose.local.yml', '-f', 'app/infra/docker-compose.observability.yml')
    # Capture resolved configuration without printing its secret-bearing environment blocks.
    $resolvedJson = (& docker @composeArgs config --format json | Out-String)
    if ($LASTEXITCODE -ne 0) { throw 'VoiceUp Compose ayarları çözümlenemedi.' }
    $resolved = $resolvedJson | ConvertFrom-Json
    $publishedPort = [int]$resolved.services.nginx.ports[0].published
    if ($publishedPort -lt 1 -or $publishedPort -gt 65535) { throw 'VoiceUp HTTP portu geçersiz.' }
    & docker @composeArgs up -d --no-build --pull never
    if ($LASTEXITCODE -ne 0) { throw 'VoiceUp servisleri başlatılamadı.' }
    Write-Output "VoiceUp: http://127.0.0.1:$publishedPort"
    Write-Output 'GPU durumunu kontrol etmek için: docker compose --project-directory app/infra -f app/infra/docker-compose.local.yml ps'
} finally {
    Pop-Location
}
