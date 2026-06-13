@echo off
echo Starting Neonatal Care System...

start "Backend - FastAPI" cmd /k "cd /d D:\_CODE26\portfolio\NeoNatal\backend && venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 3 /nobreak >nul

start "Frontend - Flutter" cmd /k "cd /d D:\_CODE26\portfolio\NeoNatal\frontend && flutter run -d chrome --web-port 5000"

echo.
echo Backend  : http://localhost:8000
echo Frontend : http://localhost:5000
echo.
echo Both windows are running. Close them to stop the servers.
