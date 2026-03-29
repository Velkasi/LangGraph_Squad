@echo off
setlocal

set ROOT=%~dp0
set VENV=%ROOT%.venv
set NODE=%VENV%\node\Scripts\node.exe
set NPM=%VENV%\node\Scripts\npm.cmd
set UVICORN=%VENV%\Scripts\uvicorn.exe
set UI=%ROOT%App\team_agent\ui

echo Starting Team Agent...

:: Backend FastAPI (Python venv) — no --reload to avoid restarting on workspace writes
start "Team Agent - API" cmd /k "cd /d %ROOT% && %VENV%\Scripts\activate.bat && %UVICORN% App.team_agent.server:app --host 0.0.0.0 --port 8000"

:: Wait for backend to be ready (poll /docs until it responds)
echo Waiting for backend...
:wait_loop
timeout /t 2 /nobreak >nul
curl -s -o nul -w "%%{http_code}" http://127.0.0.1:8000/docs | find "200" >nul 2>&1
if errorlevel 1 goto wait_loop
echo Backend ready.

:: Frontend React (Node venv)
start "Team Agent - UI" cmd /k "cd /d %UI% && set PATH=%VENV%\node\Scripts;%PATH% && %NPM% run dev"

echo.
echo Backend : http://localhost:8000
echo Frontend: http://localhost:5173
echo.
echo Use stop.bat to shut everything down.
