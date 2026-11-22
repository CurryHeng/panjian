@echo off
cd /d "%~dp0"
set "PANJIAN_DATA=%~dp0data"
set "PANJIAN_START_BACKTRACK=1"
echo Panjian: http://127.0.0.1:8765/powershell -NoProfile -ExecutionPolicy Bypass -Command "$listener = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue; if ($listener) { exit 0 } else { exit 1 }"if not errorlevel 1 (    echo 盘见已经在运行，正在打开现有页面。    start "" "http://127.0.0.1:8765/"    pause    exit /b 0)
echo Keep this window open while using Panjian.
python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8765
pause
