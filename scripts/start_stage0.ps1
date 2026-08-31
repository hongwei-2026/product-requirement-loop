# Stage 0 launcher - starts local AI server + opens acceptance page
# Run: powershell -File scripts\start_stage0.ps1

$ErrorActionPreference = 'Continue'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Root

$Port = 8765
$ReviewUrl = "http://127.0.0.1:${Port}/review.html"
$HealthUrl = "http://127.0.0.1:${Port}/api/ping"

function Open-RelPath {
    param(
        [Parameter(Mandatory)][string]$RelPath,
        [Parameter(Mandatory)][string]$Label,
        [switch]$Required
    )
    $full = [System.IO.Path]::GetFullPath((Join-Path $Root ($RelPath -replace '/', '\')))
    if (-not (Test-Path -LiteralPath $full)) {
        $tag = if ($Required) { 'FAIL' } else { 'SKIP' }
        Write-Host "[$tag] $Label : $full" -ForegroundColor $(if ($Required) { 'Red' } else { 'Yellow' })
        return $false
    }
    try {
        Start-Process -FilePath $full | Out-Null
        Write-Host "[OK]   $Label" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "[WARN] $Label : $($_.Exception.Message)" -ForegroundColor Yellow
        return (-not $Required)
    }
}

function Test-AiServer {
    try {
        $r = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 2
        if ($r.StatusCode -ne 200) { return $false }
        $body = $r.Content | ConvertFrom-Json
        return ($body.service -eq 'stage0_server')
    }
    catch {
        return $false
    }
}

function Start-AiServer {
    $serverScript = Join-Path $Root 'scripts\stage0_server.py'
    if (-not (Test-Path -LiteralPath $serverScript)) {
        Write-Host '[FAIL] scripts\stage0_server.py missing' -ForegroundColor Red
        return $false
    }
    $runBat = Join-Path $Root 'scripts\run_ai_server.bat'
    if (-not (Test-Path -LiteralPath $runBat)) {
        Write-Host '[FAIL] scripts\run_ai_server.bat missing' -ForegroundColor Red
        return $false
    }
    Write-Host "[...]  Starting AI server (new window, keep it open)..." -ForegroundColor Cyan
    Start-Process -FilePath $runBat -WorkingDirectory $Root | Out-Null
    for ($i = 0; $i -lt 15; $i++) {
        Start-Sleep -Seconds 1
        if (Test-AiServer) {
            Write-Host "[OK]   AI server ready: $ReviewUrl" -ForegroundColor Green
            return $true
        }
    }
    Write-Host '[WARN] Server not responding yet. Check the new black window for errors.' -ForegroundColor Yellow
    return $false
}

Write-Host ''
Write-Host '========================================' -ForegroundColor Cyan
Write-Host ' Stage 0 launcher (with AI server)' -ForegroundColor Cyan
Write-Host " Root: $Root"
Write-Host '========================================' -ForegroundColor Cyan

$manifestPath = Join-Path $Root 'launcher-files.json'
if (-not (Test-Path -LiteralPath $manifestPath)) {
    Write-Host '[FAIL] launcher-files.json missing' -ForegroundColor Red
    exit 1
}

$json = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json

if (-not (Test-AiServer)) {
    $null = Start-AiServer
}
else {
    Write-Host "[OK]   AI server already running" -ForegroundColor Green
}

try {
    Start-Process $ReviewUrl | Out-Null
    Write-Host "[OK]   review.html via $ReviewUrl" -ForegroundColor Green
    $reviewOk = $true
}
catch {
    Write-Host "[FAIL] Cannot open browser: $ReviewUrl" -ForegroundColor Red
    $reviewOk = $false
}

Start-Sleep -Milliseconds 500
$null = Open-RelPath -RelPath $json.preview_html -Label 'image-preview.html'
Start-Sleep -Milliseconds 500
$null = Open-RelPath -RelPath $json.acceptance_manual_md -Label 'acceptance-manual.md'

Write-Host ''
if (Get-Command python -ErrorAction SilentlyContinue) {
    Write-Host 'Optional: run scripts\verify_stage0.py manually' -ForegroundColor DarkGray
}

Write-Host ''
if ($reviewOk) {
    Write-Host '[DONE] Browser should show http://127.0.0.1:8765/review.html' -ForegroundColor Green
    Write-Host '       Keep the AI server window open. AI draft takes 30-90 seconds.' -ForegroundColor DarkGray
    exit 0
}
Write-Host '[FAIL] Try start-with-ai.bat manually' -ForegroundColor Red
exit 1
