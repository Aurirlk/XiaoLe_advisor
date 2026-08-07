$env:HF_ENDPOINT = "https://hf-mirror.com"
$env:PYTHONUNBUFFERED = "1"

# ===== 模型下载缓存 =====
$modelDir = Join-Path $PSScriptRoot "data\models\paraphrase-multilingual-MiniLM-L12-v2"
$markerFile = Join-Path $PSScriptRoot "data\models\.model_downloaded"

if (-not (Test-Path $modelDir) -and -not (Test-Path $markerFile)) {
    Write-Host "[1/3] 首次启动，下载 SentenceTransformer 模型（约 420MB）..." -ForegroundColor Yellow
    $python = "D:\Anaconda\envs\zxf\python.exe"
    & $python scripts/download_model.py
    if ($LASTEXITCODE -eq 0) {
        New-Item -ItemType File -Path $markerFile -Force | Out-Null
    }
} else {
    Write-Host "[1/3] 模型已就绪，跳过" -ForegroundColor Gray
}

# ===== 日志目录 =====
$logDir = Join-Path $PSScriptRoot "logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$logFile = Join-Path $logDir "server_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
$python = "D:\Anaconda\envs\zxf\python.exe"

Write-Host "[2/3] Starting 小乐AI 高考志愿填报助手..." -ForegroundColor Cyan
Write-Host "  Log:   $logFile" -ForegroundColor Gray
Write-Host "  UI:    http://127.0.0.1:5000" -ForegroundColor Green
Write-Host "  API:   http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "  Health:http://127.0.0.1:8000/healthz" -ForegroundColor Green
Write-Host ""
Write-Host "[3/3] 测试模式：已绕过登录，直接进入学生端" -ForegroundColor Yellow

Set-Location $PSScriptRoot

& $python -u -m api.main 2>&1 | ForEach-Object { $_; $_ | Out-File -FilePath $logFile -Append -Encoding UTF8 }
