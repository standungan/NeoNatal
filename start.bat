@echo off
title Neonatal Care - Launcher
echo ============================================================
echo   Neonatal Care System - starting all services...
echo ============================================================
echo.
echo   Requires: PostgreSQL running, backend/.env configured,
echo   backend deps installed (venv) and web deps installed (npm).
echo.

REM %~dp0 = folder of this .bat (repo root), so paths stay portable.

REM ---- 1. Backend (FastAPI) -- must start first; the dashboard proxies to it ----
start "NeoNatal Backend :8000" cmd /k "cd /d %~dp0backend && venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload"

REM give the backend a few seconds to come up
timeout /t 5 /nobreak >nul

REM ---- 2. Web Dashboard (Next.js) ----
start "NeoNatal Dashboard :3000" cmd /k "cd /d %~dp0web && npm run dev"

timeout /t 3 /nobreak >nul

REM ---- 3. Mobile app (Flutter, opens in Chrome) ----
start "NeoNatal Mobile :5000" cmd /k "cd /d %~dp0frontend && flutter run -d chrome --web-port 5000"

echo.
echo   Backend   : http://localhost:8000/docs
echo   Dashboard : http://localhost:3000     (login: admin@neonatal.rs / Password123!)
echo   Mobile    : http://localhost:5000
echo.
echo   Each service runs in its own window. Close a window to stop that service.
echo.
pause
