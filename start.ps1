$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PANJIAN_DATA = Join-Path $PSScriptRoot 'data'
$listener = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    Write-Host '盘见已经在 http://127.0.0.1:8765/ 运行。'
    Start-Process 'http://127.0.0.1:8765/'
    exit 0
}
python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8765
