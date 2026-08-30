$errors = $null
$null = [System.Management.Automation.Language.Parser]::ParseFile(
    (Join-Path $PSScriptRoot 'start_stage0.ps1'),
    [ref]$null,
    [ref]$errors
)
if ($errors.Count -gt 0) {
    $errors | ForEach-Object { Write-Host "SYNTAX ERROR: $_" }
    exit 1
}
Write-Host "start_stage0.ps1 syntax OK"
exit 0
