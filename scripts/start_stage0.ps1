# 阶段 0 本地启动（PowerShell）
# 用法：在项目根目录执行  .\scripts\start_stage0.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  阶段 0 验收环境启动" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "项目文件夹：" -ForegroundColor Yellow
Write-Host "  $Root"
Write-Host ""

# 1. 验收对照页（核心）
$Review = Join-Path $Root "project\trials\case-01\review.html"
if (-not (Test-Path $Review)) {
    Write-Host "[错误] 找不到 review.html" -ForegroundColor Red
    exit 1
}
Write-Host "[1/4] 正在用浏览器打开「验收对照页」..." -ForegroundColor Green
Start-Process $Review

Start-Sleep -Seconds 1

# 2. 图文预览
$Preview = Join-Path $Root "图文预览.html"
if (Test-Path $Preview) {
    Write-Host "[2/4] 正在打开「图文预览」（文档里的截图）..." -ForegroundColor Green
    Start-Process $Preview
}

Start-Sleep -Seconds 1

# 3. 验收手册（用系统默认方式打开 md）
$Manual = Join-Path $Root "阶段0验收操作手册.md"
if (Test-Path $Manual) {
    Write-Host "[3/4] 正在打开「验收操作手册」..." -ForegroundColor Green
    Start-Process $Manual
}

Write-Host ""
Write-Host "[4/4] 可选：跑自动检查（需要已安装 Python）" -ForegroundColor Green
Write-Host "  机器层： python scripts\verify_stage0.py"
Write-Host "  体验层： node scripts\verify_stage0_ux.mjs"
Write-Host ""

# 尝试跑机器层自测
$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    Write-Host "正在跑机器层自测..." -ForegroundColor DarkGray
    & python (Join-Path $Root "scripts\verify_stage0.py")
    Write-Host ""
} else {
    Write-Host "未检测到 Python，跳过自动检查。你仍可手动验收。" -ForegroundColor DarkYellow
}

Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host "接下来请你：" -ForegroundColor White
Write-Host "  1. 看浏览器里有没有打开「case-01 验收对照页」"
Write-Host "  2. 左边应能看到日志文字（不是「加载中」）"
Write-Host "  3. 跟着「阶段0验收操作手册」从【第 0 步】开始做"
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host ""
Write-Host "按任意键关闭本窗口..." -ForegroundColor DarkGray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
