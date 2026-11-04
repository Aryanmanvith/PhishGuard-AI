@echo off
REM PhishGuard AI - one-time setup for Windows.
REM Creates backend\.venv, installs Python + Node packages, trains the offline DEMO model.
REM Safe to re-run: it never deletes or overwrites your files.
setlocal
cd /d "%~dp0"

echo.
echo === PhishGuard AI setup ===

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python was not found. Install Python 3.10 or newer from https://www.python.org/downloads/
  echo         and tick "Add python.exe to PATH" in the installer. Then re-run setup.bat.
  goto :fail
)
python -c "import sys; sys.exit(0 if sys.version_info[:2] >= (3,10) else 1)"
if errorlevel 1 (
  echo [ERROR] Unsupported Python version. Python 3.10 or newer is required.
  echo         Install a newer Python from https://www.python.org/downloads/ ^(you can keep your other version^).
  goto :fail
)
where node >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Node.js was not found. Install the LTS version from https://nodejs.org/ and re-run setup.bat.
  goto :fail
)
where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] npm was not found. Reinstall Node.js LTS from https://nodejs.org/ and re-run setup.bat.
  goto :fail
)

echo.
echo [1/4] Python virtual environment
if exist "backend\.venv\Scripts\python.exe" (
  python -c "import subprocess, sys; result=subprocess.run([r'backend\.venv\Scripts\python.exe', '-c', 'import sys; raise SystemExit(0 if sys.version_info[:2] == tuple(map(int, sys.argv[1:])) else 1)', str(sys.version_info.major), str(sys.version_info.minor)]); sys.exit(result.returncode)"
  if errorlevel 1 (
    echo [ERROR] backend\.venv uses a different Python version than Python on PATH.
    echo         Setup will not replace your existing environment. Rename or remove backend\.venv, then re-run setup.bat.
    goto :fail
  )
) else (
  python -m venv backend\.venv
  if errorlevel 1 goto :fail
)
if exist "backend\.venv\Scripts\python.exe" echo       backend\.venv is ready.

echo.
echo [2/4] Installing backend packages (this can take a few minutes)
"backend\.venv\Scripts\python.exe" -m pip install --upgrade pip
"backend\.venv\Scripts\python.exe" -m pip install -r backend\requirements-dev.txt
if errorlevel 1 (
  echo [ERROR] pip install failed. See Troubleshooting in README.md ^(Python version, network, proxy^).
  goto :fail
)

echo.
echo [3/4] Installing frontend packages
pushd frontend
call npm install
if errorlevel 1 (
  popd
  echo [ERROR] npm install failed. See Troubleshooting in README.md.
  goto :fail
)
popd

echo.
echo [4/4] Offline demo model
if exist "backend\ml\artifacts\model.joblib" (
  echo       A trained model already exists, leaving it untouched.
  "backend\.venv\Scripts\python.exe" -c "import json, sklearn, sys; from pathlib import Path; metadata=json.loads(Path(r'backend\ml\artifacts\metrics.json').read_text(encoding='utf-8')); sys.exit(metadata.get('sklearn_version') != sklearn.__version__)" 2>nul
  if errorlevel 1 (
    echo [WARNING] The existing model was trained with a different scikit-learn version.
    echo           From backend, run .venv\Scripts\python.exe -m ml.train --demo to retrain it.
  )
) else (
  pushd backend
  ".venv\Scripts\python.exe" -m ml.train --demo
  popd
)

echo.
echo === Setup finished. Start the app with run.bat ===
endlocal
exit /b 0

:fail
echo.
echo Setup did not complete. Fix the problem above and run setup.bat again.
endlocal
exit /b 1
