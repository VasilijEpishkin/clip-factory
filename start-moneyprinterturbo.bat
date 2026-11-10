@echo off
setlocal

start "MoneyPrinterTurbo" wsl.exe -d Ubuntu -- bash -lc "cd /home/vasilij/workspace/clip-factory && exec ./scripts/start_moneyprinterturbo.sh"
timeout /t 3 /nobreak >nul
start "" http://localhost:8501
