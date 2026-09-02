@echo off
title Neonatal Care - Launcher
echo ============================================================
echo   Neonatal Care System - starting all services...
echo ============================================================
echo.
echo   Requires: backend/.env configured, backend deps installed (venv)
echo   and web deps installed (npm). PostgreSQL is started below.
echo.

REM %~dp0 = folder of this .bat (repo root), so paths stay portable.

REM ---- 0. Node.js -- must be reachable on PATH ----
REM npx (used for the dashboard below) shells out to bare "node". If Node is
REM not installed system-wide, point NODE_HOME at a portable Node folder
REM before running this script -- no machine-specific path is baked in here.
if defined NODE_HOME if exist "%NODE_HOME%\node.exe" set "PATH=%NODE_HOME%;%PATH%"
where node >nul 2>nul
if errorlevel 1 echo   [!] Node.js not found on PATH - the Dashboard window will fail (install Node 22+ or set NODE_HOME).

REM ---- 0b. PostgreSQL -- the backend cannot start without it ----
REM Skipped when something already listens on 5432 (e.g. a normal service
REM install). Otherwise a portable cluster is started: set PGSQL_HOME, or rely
REM on the default below, which looks for a pgsql folder two levels above the
REM repo. Guarded by "if exist", so this is a no-op on machines without one.
if not defined PGSQL_HOME set "PGSQL_HOME=%~dp0..\..\pgsql"
netstat -an | findstr /c:":5432" | findstr /i "LISTENING" >nul 2>nul
if not errorlevel 1 goto pg_ready
if not exist "%PGSQL_HOME%\bin\pg_ctl.exe" goto pg_missing
echo   Starting PostgreSQL from %PGSQL_HOME% ...
"%PGSQL_HOME%\bin\pg_ctl.exe" -D "%PGSQL_HOME%\data" -l "%PGSQL_HOME%\server.log" -o "-p 5432" -w -t 30 start >nul 2>nul
netstat -an | findstr /c:":5432" | findstr /i "LISTENING" >nul 2>nul
if not errorlevel 1 goto pg_ready
:pg_missing
echo   [!] PostgreSQL is not listening on 5432 - the Backend window will fail.
echo       Start it manually, or set PGSQL_HOME to a portable pgsql folder.
goto pg_done
:pg_ready
echo   PostgreSQL is up on :5432
:pg_done

REM ---- 1. Backend (FastAPI) -- must start first; the dashboard proxies to it ----
start "NeoNatal Backend :8000" cmd /k "cd /d %~dp0backend && venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload"

REM give the backend a few seconds to come up
timeout /t 5 /nobreak >nul

REM ---- 2. Web Dashboard (Next.js) ----
start "NeoNatal Dashboard :3000" cmd /k "cd /d %~dp0web && npx next dev -H 0.0.0.0"

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
