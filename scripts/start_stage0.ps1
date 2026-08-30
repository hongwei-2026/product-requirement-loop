# Stage 0 launcher - reads Chinese paths from launcher-files.json (UTF-8)
# Run: powershell -File scripts\start_stage0.ps1

$ErrorActionPreference = 'Continue'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Root

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

Write-Host ''
Write-Host '========================================' -ForegroundColor Cyan
Write-Host ' Stage 0 launcher' -ForegroundColor Cyan
Write-Host " Root: $Root"
Write-Host '========================================' -ForegroundColor Cyan

$manifestPath = Join-Path $Root 'launcher-files.json'
if (-not (Test-Path -LiteralPath $manifestPath)) {
    Write-Host '[FAIL] launcher-files.json missing' -ForegroundColor Red
    exit 1
}

$json = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json

$reviewOk = Open-RelPath -RelPath $json.review_html -Label 'review.html' -Required
Start-Sleep -Milliseconds 500
$null = Open-RelPath -RelPath $json.preview_html -Label 'image-preview.html'
Start-Sleep -Milliseconds 500
$null = Open-RelPath -RelPath $json.acceptance_manual_md -Label 'acceptance-manual.md'

Write-Host ''
if (Get-Command python -ErrorAction SilentlyContinue) {
    Write-Host 'verify_stage0.py ...' -ForegroundColor DarkGray
    & python (Join-Path $Root 'scripts\verify_stage0.py')
}

Write-Host ''
if ($reviewOk) {
    Write-Host '[DONE] Check browser: review.html' -ForegroundColor Green
    exit 0
}
Write-Host '[FAIL] Run open-review.bat as fallback' -ForegroundColor Red
exit 1
