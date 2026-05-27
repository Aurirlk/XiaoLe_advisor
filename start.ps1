$env:HF_ENDPOINT = "https://hf-mirror.com"
$env:PYTHONUNBUFFERED = "1"

$logDir = Join-Path $PSScriptRoot "logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

$logFile = Join-Path $logDir "server_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
$python = "D:\Anaconda\envs\zxf\python.exe"

Write-Host "Starting ZX AI Advisor..." -ForegroundColor Cyan
Write-Host "Log: $logFile" -ForegroundColor Gray
Write-Host "UI:  http://127.0.0.1:5000" -ForegroundColor Green
Write-Host "API: http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "Health:http://127.0.0.1:8000/healthz" -ForegroundColor Green

Set-Location $PSScriptRoot

& $python -u -m api.main 2>&1 | ForEach-Object { $_; $_ | Out-File -FilePath $logFile -Append -Encoding UTF8 }
