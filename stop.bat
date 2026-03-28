@echo off
echo Stopping Team Agent...

taskkill /FI "WINDOWTITLE eq Team Agent - API*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Team Agent - UI*"  /T /F >nul 2>&1

for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000 " ^| findstr LISTENING 2^>nul') do taskkill /PID %%p /T /F >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":5173 " ^| findstr LISTENING 2^>nul') do taskkill /PID %%p /T /F >nul 2>&1

echo Done.
