@echo off
REM PhishGuard AI - starts the backend (port 8000) and frontend (port 5173) in two windows.
setlocal
cd /d "%~dp0"

if not exist "backend\.venv\Scripts\python.exe" (
  echo [ERROR] Backend environment not found. Run setup.bat first.
  exit /b 1
)
if not exist "frontend\node_modules" (
  echo [ERROR] Frontend packages not found. Run setup.bat first.
  exit /b 1
)

REM Warn (do not kill anything) if a port is already in use.
netstat -ano | findstr /R /C:":8000 .*LISTENING" >nul && echo [WARNING] Port 8000 is already in use. See README Troubleshooting.
netstat -ano | findstr /R /C:":5173 .*LISTENING" >nul && echo [WARNING] Port 5173 is already in use. See README Troubleshooting.

start "PhishGuard backend (port 8000)" cmd /k "cd /d %~dp0backend && .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
start "PhishGuard frontend (port 5173)" cmd /k "cd /d %~dp0frontend && npm run dev -- --host 127.0.0.1"

echo.
echo Backend:  http://127.0.0.1:8000/api/health   (API docs: http://127.0.0.1:8000/docs)
echo Frontend: http://127.0.0.1:5173
echo Close the two new windows to stop the app.
timeout /t 6 >nul
start "" http://127.0.0.1:5173
endlocal
