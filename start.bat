@echo off
setlocal

set ROOT=%~dp0
set VENV=%ROOT%.venv
set NODE=%VENV%\node\Scripts\node.exe
set NPM=%VENV%\node\Scripts\npm.cmd
set UVICORN=%VENV%\Scripts\uvicorn.exe
set UI=%ROOT%App\team_agent\ui

echo Starting Team Agent...

:: Backend FastAPI (Python venv)
start "Team Agent - API" cmd /k "cd /d %ROOT% && %VENV%\Scripts\activate.bat && %UVICORN% App.team_agent.server:app --host 0.0.0.0 --port 8000 --reload"

:: Wait for backend to boot
timeout /t 3 /nobreak >nul

:: Frontend React (Node venv)
start "Team Agent - UI" cmd /k "cd /d %UI% && set PATH=%VENV%\node\Scripts;%PATH% && %NPM% run dev"

echo.
echo Backend : http://localhost:8000
echo Frontend: http://localhost:5173
echo.
echo Use stop.bat to shut everything down.
